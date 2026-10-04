#!/usr/bin/env python3
"""Bounded offline scoring of raw and constrained final prediction exports.

Successful report generation authenticates captured byte bindings, not numerical
producer truth, parent pretraining independence, source semantics or authority.
"""
from __future__ import annotations

import argparse
import os
import stat
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import codebase_ir_corpus_audit as audit
from codebase_ir_final_targets import PROFILE, derive_source, validate_target

INPUT_SCHEMA = "codebase-ir-final-evaluation-input@1"
REPORT_SCHEMA = "codebase-ir-final-evaluation@1"
PROTOCOL_SCHEMA = "codebase-ir-final-protocol@1"
COHORT_SCHEMA = "codebase-ir-final-cohort@1"
TARGETS_SCHEMA = "codebase-ir-final-targets@1"
PREDICTIONS_SCHEMA = "codebase-ir-final-predictions@1"
METRICS = ["source_binding", "types", "references", "operators", "literals", "exact_reconstruction", "unsupported_disposition"]
FALSE_FLAGS = {"native_execution_performed", "training_executed", "current_authority_claimed",
               "model_selection_performed", "promotion_performed"}
SOURCE_BINDING_FIELDS = {"source_sha256", "function_name", "start_byte", "end_byte", "source_slice_sha256"}


@dataclass(frozen=True)
class Limits:
    max_files: int = 128
    max_total_bytes: int = 8 * 1024 * 1024
    max_json_bytes: int = 1024 * 1024
    max_source_bytes: int = 64 * 1024
    max_cases: int = 32
    max_units: int = 128
    max_predictions: int = 128
    max_expression_nodes: int = 256
    max_expression_depth: int = 32

    def __post_init__(self):
        audit._require(all(type(value) is int and value > 0 for value in asdict(self).values()), "positive exact evaluation bounds required")


DEFAULT_LIMITS = Limits()


def _json(raw: bytes, limits: Limits) -> dict:
    return audit._load_json(raw, audit.Limits(max_json_bytes=limits.max_json_bytes))


def _write(path: Path, value: dict) -> None:
    with path.open("xb") as stream:
        stream.write(audit._canonical(value) + b"\n")


def _identifier(value, label):
    value = audit._text(value, label)
    audit._require(value.isidentifier(), "Python identifier required: " + label)
    return value


class Capture:
    def __init__(self, manifest: Path, limits: Limits):
        self.limits, self.files, self.total = limits, {}, 0
        self.manifest = manifest
        audit._require(manifest.is_absolute() and manifest.resolve(strict=True) == manifest
                       and not any(part.is_symlink() for part in (manifest, *manifest.parents)), "canonical nonsymlink manifest required")
        self.root = manifest.parent
        self.raw = self._read(manifest, limits.max_json_bytes)
        self.document = _json(self.raw, limits)

    @staticmethod
    def regular(path: Path, maximum: int) -> bytes:
        audit._require(path.resolve(strict=True) == path and not any(part.is_symlink() for part in (path, *path.parents)),
                       "canonical nonsymlink input required")
        fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
        with os.fdopen(fd, "rb") as stream:
            before = os.fstat(stream.fileno())
            audit._require(stat.S_ISREG(before.st_mode) and before.st_size <= maximum, "bounded regular evaluation input required")
            raw = stream.read(maximum + 1)
            after = os.fstat(stream.fileno())
            current = path.stat(follow_symlinks=False)
        def identity(value):
            return value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns
        audit._require(identity(before) == identity(after) == identity(current) and len(raw) == before.st_size
                       and len(raw) <= maximum and path.resolve(strict=True) == path, "evaluation input changed during read")
        return raw

    def _read(self, path: Path, maximum: int) -> bytes:
        if path not in self.files:
            audit._require(len(self.files) < self.limits.max_files, "evaluation input file budget exceeded")
            remaining = self.limits.max_total_bytes - self.total
            audit._require(remaining >= 0, "evaluation aggregate budget exceeded")
            raw = self.regular(path, min(maximum, remaining))
            self.total += len(raw)
            self.files[path] = raw
        raw = self.files[path]
        audit._require(len(raw) <= maximum, "evaluation input byte budget exceeded")
        return raw

    def descriptor(self, descriptor, *, source=False) -> tuple[Path, bytes]:
        audit._closed(descriptor, {"path", "sha256", "size_bytes"}, "input descriptor")
        relative = audit._relative_path(descriptor["path"], "evaluation input path")
        audit._require(not any(part.startswith(".") for part in Path(relative).parts), "hidden/dot input selector refused")
        expected = audit._digest(descriptor["sha256"], "input descriptor")
        size = descriptor["size_bytes"]
        cap = self.limits.max_source_bytes if source else self.limits.max_json_bytes
        audit._require(type(size) is int and 0 <= size <= cap, "exact bounded descriptor size required")
        path = self.root / relative
        raw = self._read(path, size)
        audit._require(len(raw) == size and audit._sha(raw) == expected, "evaluation artifact differs from exact descriptor")
        return path, raw

    def recheck(self):
        for path, raw in self.files.items():
            audit._require(self.regular(path, len(raw)) == raw, "evaluation input drifted after capture")

    def retain(self, output: Path):
        for path, raw in sorted(self.files.items()):
            retained = output / "inputs" / path.relative_to(self.root)
            retained.parent.mkdir(parents=True, exist_ok=True)
            with retained.open("xb") as stream:
                stream.write(raw)


def _binding(value):
    audit._closed(value, SOURCE_BINDING_FIELDS, "source binding")
    for key in ("source_sha256", "source_slice_sha256"):
        audit._digest(value[key], key)
    _identifier(value["function_name"], "bound function")
    audit._require(type(value["start_byte"]) is int and type(value["end_byte"]) is int
                   and 0 <= value["start_byte"] < value["end_byte"] <= 64 * 1024, "exact bounded byte span required")


def _protocol(value):
    audit._closed(value, {"schema", "protocol_id", "scope", "source_profile", "metrics", "unknown_pretraining_exposure",
        "final_selection_forbidden", "promotion_forbidden", "authoring_training_absence_certified",
        "native_decoder_compatibility_verified", "teacher_semantics_certified", "producer_authentication_verified"}, "final protocol")
    audit._require(value["schema"] == PROTOCOL_SCHEMA and value["source_profile"] == PROFILE
                   and value["scope"] == "authored_qualification_protocol" and value["metrics"] == METRICS, "fixed qualification protocol required")
    audit._text(value["protocol_id"], "protocol ID")
    for key in ("unknown_pretraining_exposure", "final_selection_forbidden", "promotion_forbidden"):
        audit._require(value[key] is True, "final isolation policy required: " + key)
    for key in ("authoring_training_absence_certified", "native_decoder_compatibility_verified", "teacher_semantics_certified", "producer_authentication_verified"):
        audit._require(value[key] is False, "unverified protocol claim must remain false: " + key)


def _cohort(capture: Capture, value: dict, limits: Limits) -> tuple[dict, dict, list]:
    audit._closed(value, {"schema", "scope", "ancestry_complete", "native_exposure_inventory_complete", "units"}, "final cohort")
    audit._require(value["schema"] == COHORT_SCHEMA and value["scope"] == "explicit_supplied_source_scope"
                   and value["ancestry_complete"] is False and value["native_exposure_inventory_complete"] is False,
                   "unknown ancestry/native exposure must be preserved")
    rows = value["units"]
    audit._require(type(rows) is list and 0 < len(rows) <= limits.max_units, "bounded complete cohort rows required")
    units, sources, families, identities = [], {}, {}, set()
    for row in rows:
        audit._closed(row, {"id", "role", "repository_id", "path", "revision", "source", "dependencies",
            "dependencies_complete", "related_revisions", "revision_relations_complete", "template_family"}, "cohort unit")
        unit_id = audit._text(row["id"], "cohort ID")
        audit._require(unit_id not in sources, "duplicate cohort ID")
        audit._require(type(row["role"]) is str and row["role"] in audit.ROLES, "explicit known cohort role required")
        _, raw = capture.descriptor(row["source"], source=True)
        audit.normalized_ast_digest(raw)
        key = (row["repository_id"], row["path"], row["revision"])
        audit._require(all(type(part) is str for part in key) and key not in identities, "ambiguous repeated source identity")
        identities.add(key)
        unit = {key: row[key] for key in audit.UNIT_FIELDS - {"content_sha256", "source"}}
        unit.update(content_sha256=audit._sha(raw), source={"bytes_hex": raw.hex()})
        units.append(unit)
        sources[unit_id] = raw
        families.setdefault(audit._text(row["template_family"], "template family"), []).append(unit_id)
    roles = {unit["id"]: unit["role"] for unit in units}
    family_leaks = [{"template_family": family, "unit_ids": sorted(ids), "roles": sorted({roles[name] for name in ids})}
                    for family, ids in sorted(families.items()) if "final" in {roles[name] for name in ids}
                    and len({roles[name] for name in ids}) > 1]
    return {"schema": audit.INPUT_SCHEMA, "units": units, "native_records": [], "ancestral_training": [], "ancestry_complete": False}, sources, family_leaks


def _targets(value, units, sources, limits):
    audit._closed(value, {"schema", "profile", "provenance", "cases"}, "target inventory")
    audit._require(value["schema"] == TARGETS_SCHEMA and value["profile"] == PROFILE, "qualification target inventory required")
    provenance = audit._closed(value["provenance"], {"origin", "derived_from_desired_intent", "independently_checked_source_semantics", "native_teacher_compatibility_verified"}, "target provenance")
    audit._require(provenance["origin"] == "authored_source_projection" and all(provenance[key] is False for key in provenance if key != "origin"),
                   "source-only authored labels with unverified semantics required")
    rows = value["cases"]
    audit._require(type(rows) is list and 0 < len(rows) <= limits.max_cases, "bounded final cases required")
    final_ids = {unit["id"] for unit in units if unit["role"] == "final"}
    cases, seen = {}, set()
    for row in rows:
        audit._closed(row, {"case_id", "unit_id", "source_binding", "status", "target", "unsupported_reason", "desired_intent", "intent_used_as_label"}, "final case")
        case_id, unit_id = audit._text(row["case_id"], "case ID"), audit._text(row["unit_id"], "case unit ID")
        audit._require(case_id not in cases and unit_id in final_ids and unit_id not in seen, "duplicate, missing or nonfinal target unit")
        _binding(row["source_binding"])
        audit._text(row["desired_intent"], "separate desired intent", 2048)
        audit._require(row["intent_used_as_label"] is False, "desired intent cannot supply source label")
        binding, target, reason = derive_source(sources[unit_id])
        audit._require(audit._canonical(binding) == audit._canonical(row["source_binding"]), "target byte/span/source binding drift")
        audit._require(type(row["status"]) is str and row["status"] in {"supported", "unsupported"}, "explicit target disposition required")
        if target is None:
            audit._require(row["status"] == "unsupported" and row["target"] is None and row["unsupported_reason"] == reason,
                           "unsupported source cannot receive a manufactured target")
        else:
            audit._require(row["status"] == "supported" and row["unsupported_reason"] is None
                           and audit._canonical(row["target"]) == audit._canonical(target), "target differs from independent source projection")
            validate_target(target, max_nodes=limits.max_expression_nodes, max_depth=limits.max_expression_depth)
        seen.add(unit_id)
        cases[case_id] = row
    audit._require(seen == final_ids, "every final source requires an explicit target disposition")
    return cases


def _output(value, *, constrained: bool, simulation: bool):
    fields = {"state", "origin", "target"} | ({"mechanism"} if constrained else set())
    audit._closed(value, fields, "prediction output")
    audit._require(type(value["state"]) is str and value["state"] in {"candidate", "abstained", "unsupported"}, "explicit prediction state required")
    origins = {"authored_simulation", "teacher", "no_output"} if simulation else {"model_output", "teacher", "no_output"}
    audit._require(type(value["origin"]) is str and value["origin"] in origins, "prediction origin incompatible with export provenance")
    if value["state"] == "candidate":
        audit._require(value["target"] is not None and value["origin"] != "no_output", "candidate origin/target required")
    else:
        audit._require(value["target"] is None and value["origin"] == "no_output", "abstention cannot contain a hidden target")
    if constrained:
        audit._require(type(value["mechanism"]) is str and value["mechanism"] in {"none", "grammar_constraints", "teacher_substitution"}, "explicit constrained mechanism required")


def _score(output, case, binding, mode, stage, limits):
    supported = case["status"] == "supported"
    bound = audit._canonical(binding) == audit._canonical(case["source_binding"])
    findings = []
    if not bound:
        findings.append("wrong_source_binding")
    teacher = output["origin"] == "teacher" or output.get("mechanism") == "teacher_substitution"
    if teacher:
        findings.append("teacher_substitution")
    if mode == "model_off" and output["state"] == "candidate":
        findings.append("model_off_emitted_candidate")
    details, error = None, None
    if output["state"] == "candidate":
        try:
            details = validate_target(output["target"], max_nodes=limits.max_expression_nodes, max_depth=limits.max_expression_depth)
        except (audit.AuditInputError, RecursionError) as exc:
            error = str(exc)
            findings.append("malformed_or_mistyped_candidate")
    expected = validate_target(case["target"]) if supported else None
    eligible = bound and not teacher and mode != "model_off" and details is not None and supported
    correct = {"source_binding": bound, "types": False, "references": False, "operators": False,
               "literals": False, "exact_reconstruction": False,
               "unsupported_disposition": not supported and bound and output["state"] in {"abstained", "unsupported"}}
    if eligible:
        target = output["target"]
        correct["types"] = audit._canonical(target["function"]) == audit._canonical(case["target"]["function"])
        for metric in ("references", "operators", "literals"):
            correct[metric] = audit._canonical(details[metric]) == audit._canonical(expected[metric])
        correct["exact_reconstruction"] = audit._canonical(target) == audit._canonical(case["target"])
    if not supported and output["state"] == "candidate":
        findings.append("candidate_for_unsupported_source")
    if supported and not correct["exact_reconstruction"] and mode != "model_off":
        findings.append("source_reconstruction_not_established")
    return {"stage": stage, "state": output["state"], "valid_typed_candidate": details is not None,
            "candidate_error": error, "correct": correct, "findings": findings,
            "numerical_origin_verified": False, "learned_weight_dependence_verified": False}


def _predictions(value, cases, protocol_sha, limits):
    audit._closed(value, {"schema", "protocol_sha256", "producer", "rows"}, "prediction export")
    audit._require(value["schema"] == PREDICTIONS_SCHEMA and value["protocol_sha256"] == protocol_sha, "prediction/protocol pin mismatch")
    producer = audit._closed(value["producer"], {"origin", "producer_id", "checkpoint_sha256", "numerical_provenance_verified"}, "prediction producer")
    audit._require(type(producer["origin"]) is str and producer["origin"] in {"authored_simulation", "unverified_export"}
                   and producer["numerical_provenance_verified"] is False, "unverified numerical provenance required")
    audit._text(producer["producer_id"], "producer ID")
    simulation = producer["origin"] == "authored_simulation"
    if producer["checkpoint_sha256"] is not None:
        audit._digest(producer["checkpoint_sha256"], "claimed checkpoint")
    audit._require(not simulation or producer["checkpoint_sha256"] is None, "simulation cannot claim a numerical checkpoint")
    rows = value["rows"]
    audit._require(type(rows) is list and 0 < len(rows) <= limits.max_predictions, "bounded prediction population required")
    if not simulation and any(type(row) is dict and row.get("mode") in ("learned", "zero_head") for row in rows):
        audit._require(producer["checkpoint_sha256"] is not None, "exported learned/zero-head output requires a claimed checkpoint digest")
    results, seen, covered = [], set(), set()
    for row in rows:
        audit._closed(row, {"prediction_id", "case_id", "mode", "source_binding", "raw", "constrained"}, "prediction row")
        prediction_id = audit._text(row["prediction_id"], "prediction ID")
        audit._require(prediction_id not in seen and type(row["case_id"]) is str and row["case_id"] in cases, "duplicate prediction or foreign case")
        audit._require(type(row["mode"]) is str and row["mode"] in {"learned", "model_off", "zero_head"}, "explicit prediction mode required")
        _binding(row["source_binding"])
        for stage in ("raw", "constrained"):
            _output(row[stage], constrained=stage == "constrained", simulation=simulation)
        if row["constrained"]["mechanism"] == "none":
            unchanged = {key: row["constrained"][key] for key in row["raw"]}
            audit._require(audit._canonical(unchanged) == audit._canonical(row["raw"]), "none constraint must preserve raw output exactly")
        seen.add(prediction_id)
        covered.add(row["case_id"])
        results.append({"prediction_id": prediction_id, "case_id": row["case_id"], "mode": row["mode"],
                        **{stage: _score(row[stage], cases[row["case_id"]], row["source_binding"], row["mode"], stage, limits)
                           for stage in ("raw", "constrained")}})
    audit._require(covered == set(cases), "missing final case predictions")
    return results, producer


def _summaries(rows, cases):
    summaries = {}
    for mode in ("learned", "model_off", "zero_head"):
        for stage in ("raw", "constrained"):
            selected = [row for row in rows if row["mode"] == mode]
            scores = {}
            for metric in METRICS:
                relevant = selected if metric == "source_binding" else [row for row in selected
                    if (cases[row["case_id"]]["status"] == "unsupported") == (metric == "unsupported_disposition")]
                if metric in {"references", "operators", "literals"}:
                    relevant = [row for row in relevant if validate_target(cases[row["case_id"]]["target"])[metric]]
                scores[metric] = {"correct": sum(row[stage]["correct"][metric] for row in relevant), "total": len(relevant)}
            summaries[mode + "/" + stage] = {"rows": len(selected), "metrics": scores,
                "findings": sum(bool(row[stage]["findings"]) for row in selected)}
    return summaries


def _coverage(rows, cases):
    by_mode = {}
    per_case = []
    for mode in ("learned", "model_off", "zero_head"):
        present = {row["case_id"] for row in rows if row["mode"] == mode}
        by_mode[mode] = {"case_count": len(present), "total_cases": len(cases),
                         "present_case_ids": sorted(present), "missing_case_ids": sorted(set(cases) - present),
                         "complete_case_coverage": present == set(cases)}
    for case_id in sorted(cases):
        counts = {mode: sum(row["case_id"] == case_id and row["mode"] == mode for row in rows) for mode in by_mode}
        per_case.append({"case_id": case_id, "mode_prediction_counts": counts,
                         "missing_modes": [mode for mode, count in counts.items() if count == 0]})
    return {"modes": by_mode, "cases": per_case, "all_case_modes_present": all(value["complete_case_coverage"] for value in by_mode.values()),
            "scope": "recorded export row coverage; multiple authored controls for one case are separate rows"}


def evaluate(manifest: Path, output: Path, limits: Limits = DEFAULT_LIMITS) -> dict:
    manifest, output = manifest.absolute(), output.absolute()
    audit._require(output.parent.resolve(strict=True) == output.parent and not any(part.is_symlink() for part in (output.parent, *output.parent.parents)),
                   "canonical nonsymlink output parent required")
    audit._require(not output.is_relative_to(manifest.parent.resolve(strict=True)), "output must be outside immutable input bundle")
    output.mkdir(exist_ok=False)
    report = {"schema": REPORT_SCHEMA, "status": "refused", **dict.fromkeys(FALSE_FLAGS, False),
              "unknown_pretraining_exposure": True, "independence_verified": False, "native_closure_certified": False,
              "producer_authentication_verified": False, "teacher_semantics_certified": False,
              "input_files_unchanged": False, "raw_outputs_retained_unmodified": False,
              "manifest_sha256": None, "limits": asdict(limits)}
    capture = None
    try:
        capture = Capture(manifest, limits)
        report["manifest_sha256"] = audit._sha(capture.raw)
        spec = audit._closed(capture.document, {"schema", "protocol", "cohort", "targets", "predictions"}, "final evaluation manifest")
        audit._require(spec["schema"] == INPUT_SCHEMA, "versioned final evaluation input required")
        documents = {}
        for name in ("protocol", "cohort", "targets", "predictions"):
            _, raw = capture.descriptor(spec[name])
            documents[name] = _json(raw, limits)
        _protocol(documents["protocol"])
        scope, sources, family_leaks = _cohort(capture, documents["cohort"], limits)
        scope_path = output / "supplied_scope.json"
        _write(scope_path, scope)
        screen = audit.audit_manifest(scope_path)
        _write(output / "split_screen.json", screen)
        cases = _targets(documents["targets"], scope["units"], sources, limits)
        rows, producer = _predictions(documents["predictions"], cases, spec["protocol"]["sha256"], limits)
        _write(output / "raw_outputs.json", {"scope": "canonical extracts; original prediction input bytes retained separately",
            "rows": [{"prediction_id": row["prediction_id"], "raw": row["raw"]} for row in documents["predictions"]["rows"]]})
        _write(output / "constrained_outputs.json", {"rows": [{"prediction_id": row["prediction_id"], "constrained": row["constrained"]} for row in documents["predictions"]["rows"]]})
        capture.recheck()
        capture.retain(output)
        # Check originals once more after retaining copies, before publishing status.
        capture.recheck()
        report.update(status="passed", scope="offline authored protocol scoring; no independent final/generalization or numerical claim",
            protocol_sha256=spec["protocol"]["sha256"], protocol_id=documents["protocol"]["protocol_id"],
            input_files_unchanged=True, raw_outputs_retained_unmodified=True,
            prediction_input_sha256=spec["predictions"]["sha256"], prediction_origin=producer["origin"],
            numerical_provenance_verified=False, learned_weight_dependence_verified=False,
            native_decoder_compatibility_verified=False, candidate_model_qualified=False,
            case_count=len(cases), supported_case_count=sum(case["status"] == "supported" for case in cases.values()),
            unsupported_case_count=sum(case["status"] == "unsupported" for case in cases.values()),
            source_unit_count=len(scope["units"]), prediction_count=len(rows), scores=_summaries(rows, cases),
            prediction_coverage=_coverage(rows, cases),
            prediction_results=rows, finding_count=sum(len(row[stage]["findings"]) for row in rows for stage in ("raw", "constrained")),
            split_audit_status=screen["status"], split_issue_count=len(screen["issues"]), split_leaks=screen["leaks"],
            template_family_leaks=family_leaks, final_exposure_observed=bool(family_leaks or any("final" in leak["roles"] for leak in screen["leaks"])),
            screen_scope="only exact supplied comparator/final sources; complete native/parent exposure unavailable",
            input_files=[{"path": path.relative_to(capture.root).as_posix(), "sha256": audit._sha(raw), "size_bytes": len(raw)}
                         for path, raw in sorted(capture.files.items())], input_bytes=capture.total)
    except (audit.AuditInputError, OSError, RecursionError, ValueError, TypeError, KeyError) as exc:
        report["error"] = f"{type(exc).__name__}: {exc}"
    _write(output / "final_evaluation.json", report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = evaluate(args.manifest, args.output)
    except (audit.AuditInputError, OSError) as exc:
        parser.exit(3, f"final evaluation refused: {exc}\n")
    print(audit._canonical({key: report.get(key) for key in ("status", "manifest_sha256", "prediction_count", "finding_count", "split_audit_status")}).decode())
    return 0 if report["status"] == "passed" else 3


if __name__ == "__main__":
    sys.exit(main())
