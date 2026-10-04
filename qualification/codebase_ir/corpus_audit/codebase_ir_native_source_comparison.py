#!/usr/bin/env python3
"""Compare retained native expression fragments with exact public source bytes.

This source-only qualification adapter never executes source or an owner module.
Annotations are assumptions; returned fragment matches are not runtime semantics,
numerical provenance, weight dependence, or held-out model quality evidence.
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import codebase_ir_corpus_audit as audit
import codebase_ir_final_evaluation as final
import codebase_ir_final_lock as lock_tool
import codebase_ir_final_targets as targets
import codebase_ir_native_source384_diagnostics as native

INPUT_SCHEMA = "codebase-ir-native-source-comparison-input@1"
REPORT_SCHEMA = "codebase-ir-native-source-comparison@1"
REPORT_NAME = "native_source_comparison.json"
ROLES = ("diagnostics_input", "diagnostics", "source_replay", "public_manifest")
REPLAY_SELECTOR = "public/replay-identity.json"
REPLAY_FIELDS = {"archived_owner_open_mode", "artifact", "authority", "checkpoint_sha256", "child_id", "embedding_assets",
                 "parent_id", "producer", "promotion_performed", "rows", "source_head", "training_executed"}
HEAD_FIELDS = {"schema", "repository_id", "generation", "manifest_cid", "receipt_cid", "snapshot_cid", "ast_revision_id"}
OPERATORS = {"Add": "+", "Sub": "-", "Mult": "*", "Eq": "==", "NotEq": "!=", "Lt": "<", "LtE": "<=", "Gt": ">", "GtE": ">="}
TRUE_FLAGS = {"source_structural_comparison_available", "source_labels_rederived", "source_only_byte_bindings_verified",
              "raw_native_outputs_retained_unmodified", "native_source_diagnostics_independently_rederived",
              "source_label_baseline_separate", "input_files_unchanged", "unknown_pretraining_exposure"}
FALSE_FLAGS = {"native_execution_performed", "training_executed", "current_authority_claimed", "model_selection_performed",
               "promotion_performed", "candidate_model_qualified", "producer_authentication_verified", "numerical_provenance_verified",
               "source_semantics_verified", "source_runtime_equivalence_verified", "heldout_independence_verified",
               "independent_samples_established", "learned_weight_dependence_verified", "learned_quality_improvement_verified",
               "preconstraint_raw_output_available", "source_head_authority_verified", "model_head_state_validated",
               "native_execution_admission_qualified"}


@dataclass(frozen=True)
class Limits:
    # Five outer inputs, six prior retained copies, six unchanged diagnostic inputs.
    max_files: int = 17
    max_file_bytes: int = 1024 * 1024
    max_total_bytes: int = 16 * 1024 * 1024
    max_rows: int = 32
    max_source_bytes: int = 64 * 1024
    max_total_source_bytes: int = 2 * 1024 * 1024

    def __post_init__(self):
        audit._require(all(type(value) is int and value > 0 for value in asdict(self).values()), "positive exact source comparison limits required")


DEFAULT_LIMITS = Limits()


def _json(raw, limits):
    return audit._load_json(raw, audit.Limits(max_json_bytes=limits.max_file_bytes, max_json_nodes=100_000))


def _descriptor(value, limits):
    audit._closed(value, {"path", "sha256", "size_bytes"}, "source comparison descriptor")
    path = Path(audit._text(value["path"], "source comparison path", 4096))
    audit._require(path.is_absolute() and str(path) == value["path"], "canonical absolute comparison path required")
    audit._digest(value["sha256"], "comparison SHA")
    audit._require(type(value["size_bytes"]) is int and 0 <= value["size_bytes"] <= limits.max_file_bytes,
                   "exact bounded comparison size required")
    return path


def _expected_fragment(target):
    """Closed two-Int-parameter binary reference fragment, not a full function IR."""
    if target is None:
        return None, "unsupported_source_projection"
    targets.validate_target(target)
    parameters, body = target["function"]["parameters"], target["body"]
    if len(parameters) != 2 or any(param["sort"] != "Int" for param in parameters):
        return None, "native_fragment_requires_two_integer_parameters"
    if body["kind"] not in {"binary", "compare"} or any(body[key]["kind"] != "reference" for key in ("left", "right")):
        return None, "native_fragment_requires_one_binary_operation_over_parameter_references"
    if {body[key]["name"] for key in ("left", "right")} != {param["name"] for param in parameters}:
        return None, "native_fragment_requires_both_distinct_parameters"
    operands = ["expr:" + body[key]["name"] for key in ("left", "right")]
    return {"kind": "program_expression", "document": {"attributes": {}, "evaluation_order": operands,
            "expression_id": "expr:result", "kind": "binary", "operand_ids": operands, "operator": OPERATORS[body["operator"]],
            "source_ref_ids": ["source"], "span_ids": [], "symbol_ids": [],
            "type_ref": "integer" if target["function"]["returns"] == "Int" else "boolean"}}, None


def _comparison(expected, row):
    if row is None:
        return {"status": "missing_mode", "exact_fragment_match": None, "checks": None}
    if expected is None or row["candidate_codec"]["status"] != "recognized_binary_codec":
        return {"status": "unsupported_source_or_native_codec", "exact_fragment_match": None, "checks": None}
    returned = row["returned_candidate"]
    checks = {key + "_match": returned["document"][key] == value for key, value in expected["document"].items()}
    checks["envelope_kind_match"] = returned["kind"] == expected["kind"]
    matched = returned == expected
    return {"status": "matched" if matched else "mismatch", "exact_fragment_match": matched, "checks": checks}


def _replay(value, old_spec, documents, limits):
    audit._closed(value, REPLAY_FIELDS, "public source replay")
    audit._require(value["archived_owner_open_mode"] == "read_only", "read-only archived replay required")
    authority = audit._closed(value["authority"], {"admitted", "behavioral_satisfaction", "promotion_performed", "proof_authority",
                                                "source_runtime_semantics_verified"}, "replay authority")
    audit._require(all(item is False for item in authority.values()) and value["promotion_performed"] is False
                   and value["training_executed"] is False, "replay authority or training claim outside source-only profile")
    head = audit._closed(value["source_head"], HEAD_FIELDS, "captured source head")
    audit._require(head["schema"] == "codebase-head@1" and type(head["generation"]) is int and head["generation"] > 0,
                   "typed captured source head required")
    for key in HEAD_FIELDS - {"schema", "generation"}:
        audit._text(head[key], "captured source head " + key, 4096)
    audit._require(head == documents["source_label_baseline"]["source_head"], "replay/baseline captured source head mismatch")
    checkpoint = documents["qualification"]["checkpoint"]
    for key in ("artifact", "checkpoint_sha256", "child_id", "parent_id"):
        audit._require(value[key] == checkpoint[key], "replay/qualification claimed checkpoint metadata mismatch")
    audit._digest(value["checkpoint_sha256"], "replay claimed checkpoint")
    for role in native.ROLES[:2]:
        result = documents[role]["result"]
        audit._require(value["producer"] == result["producer"] and value["embedding_assets"] == result["embedding_assets"],
                       "replay/native captured producer or embedding asset metadata mismatch")
    rows = value["rows"]
    audit._require(type(rows) is list and 0 < len(rows) <= limits.max_rows, "bounded nonempty source replay rows required")
    sources, total = {}, 0
    for row in rows:
        audit._closed(row, {"id", "source_text"}, "source-only replay row")
        name = audit._digest(row["id"], "replay native ID")
        audit._require(name not in sources, "duplicate source replay ID")
        audit._require(type(row["source_text"]) is str and len(row["source_text"]) <= limits.max_source_bytes,
                       "bounded source-only text required")
        try:
            raw = row["source_text"].encode("utf-8", errors="strict")
        except UnicodeError as exc:
            raise audit.AuditInputError("exact UTF-8 source bytes required") from exc
        total += len(raw)
        audit._require(len(raw) <= limits.max_source_bytes and total <= limits.max_total_source_bytes,
                       "source-only byte budget exceeded")
        sources[name] = raw
    return sources, {"captured_source_head": head, "captured_source_head_canonical_sha256": audit._sha(audit._canonical(head)),
                     "claimed_checkpoint_sha256": value["checkpoint_sha256"], "release_provenance_claim": old_spec["release"],
                     "producer_metadata_canonical_sha256": audit._sha(audit._canonical(value["producer"])),
                     "producer_metadata_identity_verified": True, "producer_authentication_verified": False}


def _source_records(sources, diagnostic, limits):
    records, source_files = [], {}
    audit._require(set(sources) == {row["id"] for row in diagnostic["paired_records"]}, "source replay/native ID population mismatch")
    for record in diagnostic["paired_records"]:
        name, raw = record["id"], sources[record["id"]]
        audit._require(audit._sha(raw) == record["source_sha256"], "exact replay bytes/native source digest mismatch")
        verified_spans = {}
        for role, row in record["rows"].items():
            spans = row["recorded_source_contract"]["recorded_spans"]
            audit._require(len({span["span_id"] for span in spans}) == len(spans), "duplicate recorded source span ID")
            for span in spans:
                start, end = span["start_byte"], span["end_byte"]
                audit._require(0 <= start < end <= len(raw) and audit._sha(raw[start:end]) == span["sha256"],
                               "recorded source span differs from exact source-only bytes")
            verified_spans[role] = spans
        binding, target, reason = targets.derive_source(raw, audit.Limits(max_source_bytes=limits.max_source_bytes))
        expected, codec_reason = _expected_fragment(target)
        comparisons = {role: _comparison(expected, record["rows"].get(role)) for role in native.ROLES[:2]}
        baseline = record["rows"].get("source_label_baseline")
        expected_sha = audit._sha(audit._canonical(expected)) if expected else None
        source_path = "sources/" + name + ".py"
        source_files[source_path] = raw
        records.append({"native_id": name, "source_sha256": record["source_sha256"], "source_export": source_path,
            "source_bytes": len(raw), "function_binding": binding, "source_target": target,
            "source_projection_status": "supported" if target else "unsupported", "source_projection_reason": reason,
            "native_fragment_projection_status": "supported" if expected else "unsupported", "native_fragment_projection_reason": codec_reason,
            "expected_native_fragment": expected, "expected_native_fragment_sha256": expected_sha,
            "verified_recorded_spans_by_role": verified_spans, "present_roles": record["present_roles"], "missing_roles": record["missing_roles"],
            "returned_mode_comparisons": comparisons,
            "returned_mode_identity": {role: {"claimed_model_head_sha256": row["head_sha256"],
                "claimed_model_projection_sha256": row["projection_sha256"], "returned_candidate_sha256": row["candidate_sha256"],
                "returned_candidate": row["returned_candidate"], "target_access": row["metadata"]["target_access"],
                "teacher_forcing": row["metadata"]["teacher_forcing"], "weight_ablation": row["ablation"]}
                for role, row in record["rows"].items() if role in native.ROLES[:2]},
            "source_label_baseline": {"status": "missing_mode" if baseline is None else "source_derived_fragment_unsupported" if expected is None else "compared_digest_only",
                "candidate_digest_matches_source_fragment": baseline["candidate_sha256"] == expected_sha if baseline and expected else None,
                "baseline_meaning": "deterministic_source_label_not_model_inference", "mapped_to_final_scorer_model_off": False},
            "native_output_stage": "returned_native_candidate; preconstraint/postconstraint boundary unknown",
            "unencoded_features": ["function name and signature", "literal or guard structures outside closed codec", "general source effects and runtime semantics"],
            "independent_sample_verified": False, "exposure_disposition": "unknown"})
    return records, source_files


def _copy(path, raw):
    with path.open("xb") as stream:
        stream.write(raw)
    path.chmod(0o600)


def evaluate(manifest: Path, output: Path, limits: Limits = DEFAULT_LIMITS):
    manifest, output = manifest.absolute(), output.absolute()
    pins = native.Pins(limits)
    raw = pins.read(manifest, limits.max_file_bytes)
    spec = audit._closed(_json(raw, limits), {"schema", *ROLES}, "native source comparison input")
    audit._require(spec["schema"] == INPUT_SCHEMA, "versioned native source comparison input required")
    selected = {role: pins.descriptor(spec[role]) for role in ROLES}
    old_spec = audit._closed(_json(selected["diagnostics_input"][1], limits), {"schema", "release", "public_manifest", "exports"}, "prior diagnostics input")
    audit._require(old_spec["schema"] == native.INPUT_SCHEMA and old_spec["public_manifest"] == spec["public_manifest"],
                   "comparison/prior diagnostics public manifest binding mismatch")
    audit._closed(old_spec["exports"], set(native.ROLES), "prior selected native roles")
    inner = {"manifest": spec["diagnostics_input"], "public_manifest": spec["public_manifest"], **old_spec["exports"]}
    for descriptor in inner.values():
        _descriptor(descriptor, limits)
        audit._require(descriptor["size_bytes"] <= native.DEFAULT_LIMITS.max_file_bytes, "prior diagnostics per-file budget exceeded")
    inner_bytes = sum(desc["size_bytes"] for desc in inner.values())
    audit._require(inner_bytes <= native.DEFAULT_LIMITS.max_total_bytes and len(pins.files) + 2 * len(inner) <= limits.max_files
                   and pins.total + 2 * inner_bytes <= limits.max_total_bytes, "nested diagnostics and retained copy aggregate budget exceeded")
    prior = _json(selected["diagnostics"][1], limits)
    audit._require(prior.get("schema") == native.REPORT_SCHEMA and prior.get("status") == "passed"
                   and prior.get("manifest_sha256") == spec["diagnostics_input"]["sha256"]
                   and prior.get("public_manifest_sha256") == spec["public_manifest"]["sha256"], "prior diagnostics raw input/report binding mismatch")
    prior_copies = [{"path": "inputs/" + role + ".json", "sha256": desc["sha256"], "size_bytes": desc["size_bytes"]}
                    for role, desc in sorted(inner.items())]
    audit._require(prior.get("retained_files") == prior_copies, "prior retained copy declarations differ from exact input pins")
    for copy in prior_copies:
        pins.descriptor({**copy, "path": str(selected["diagnostics"][0].parent / copy["path"])})
    public = _json(selected["public_manifest"][1], limits)
    audit._require(public.get("schema") == "codebase-source384-acceptance-evidence@1" and type(public.get("files")) is list
                   and len(public["files"]) <= native.DEFAULT_LIMITS.max_manifest_children, "bounded public source replay commitment required")
    declarations = [item for item in public["files"] if type(item) is dict and item.get("path") == REPLAY_SELECTOR]
    audit._require(declarations == [{"path": REPLAY_SELECTOR, "sha256": spec["source_replay"]["sha256"], "bytes": spec["source_replay"]["size_bytes"]}],
                   "source replay differs from public child commitment")
    documents = {role: _json(pins.files[selected["diagnostics"][0].parent / ("inputs/" + role + ".json")], limits) for role in native.ROLES}
    raw_rows = {role: native._inference(documents[role], role, limits)[0] for role in native.ROLES[:2]}
    raw_rows["source_label_baseline"] = native._baseline(documents["source_label_baseline"], limits)[0]
    paired = native._pair(raw_rows)
    audit._require(len(paired) <= limits.max_rows and prior.get("paired_records") == paired,
                   "prior diagnostic records differ from independently parsed native bodies")
    sources, identities = _replay(_json(selected["source_replay"][1], limits), old_spec, documents, limits)
    # These records remain provisional until the complete prior report is rederived.
    records, source_files = _source_records(sources, prior, limits)
    protected = [path.parent for path in pins.files] + [_descriptor(desc, limits).parent for desc in inner.values()]
    lock_tool._preflight_output(output, protected)
    pins.recheck()
    output.mkdir(mode=0o700)
    report = {"schema": REPORT_SCHEMA, "status": "refused", **dict.fromkeys(FALSE_FLAGS, False), **dict.fromkeys(TRUE_FLAGS, False),
              "manifest_sha256": audit._sha(raw), "diagnostics_input_sha256": spec["diagnostics_input"]["sha256"],
              "diagnostics_report_sha256": spec["diagnostics"]["sha256"], "source_replay_sha256": spec["source_replay"]["sha256"],
              "public_manifest_sha256": spec["public_manifest"]["sha256"], "limits": asdict(limits)}
    report["unknown_pretraining_exposure"] = True
    copies = {}
    try:
        rederived_output = output / "native-diagnostics-rederived"
        rederived = native.evaluate(selected["diagnostics_input"][0], rederived_output)
        rederived_raw = final.Capture.regular(rederived_output / "native_source384_diagnostics.json", limits.max_file_bytes)
        audit._require(rederived["status"] == "passed" and rederived == prior and rederived_raw == selected["diagnostics"][1],
                       "prior diagnostics do not exactly reproduce from declared raw native inputs")
        # Original native bodies, new rederived copies, and prior retained copies
        # are all bound separately; a re-pinned counterparty report is insufficient.
        original_native = {}
        for role, desc in inner.items():
            original = _descriptor(desc, limits)
            retained = rederived_output / "inputs" / (role + ".json")
            body = final.Capture.regular(retained, desc["size_bytes"])
            audit._require(len(body) == desc["size_bytes"] and audit._sha(body) == desc["sha256"], "rederived retained native copy pin mismatch")
            original_native[original] = body
            copies[retained] = body
        copies[rederived_output / "native_source384_diagnostics.json"] = rederived_raw
        (output / "inputs").mkdir(mode=0o700)
        (output / "sources").mkdir(mode=0o700)
        outer_roles = {manifest: "manifest", **{path: role for role, (path, _) in selected.items()}}
        for path, body in pins.files.items():
            role = outer_roles.get(path, "prior_copy_" + path.stem)
            destination = output / "inputs" / (role + ".json")
            _copy(destination, body)
            copies[destination] = body
        for relative, body in source_files.items():
            destination = output / relative
            _copy(destination, body)
            copies[destination] = body
        pins.recheck()
        for path, body in original_native.items():
            audit._require(final.Capture.regular(path, len(body)) == body, "original native body drifted after diagnostic rederivation")
        for path, body in copies.items():
            audit._require(final.Capture.regular(path, len(body)) == body, "retained comparison copy drifted")
        pins.recheck()
        report.update(status="passed", **dict.fromkeys(TRUE_FLAGS, True), **identities,
            scope="historical returned native expression structure compared with exact source-only bytes under declared annotation assumptions",
            native_output_stage="returned_native_candidate; preconstraint/postconstraint boundary unknown",
            historical_case_count=len(records), source_byte_count=sum(map(len, sources.values())), records=records,
            source_only_replay_selector=REPLAY_SELECTOR,
            exposure={"status": "unknown", "complete_ancestral_training_tuning_canary_inventory_supplied": False, "final_partition_assignment_performed": False},
            head_identity_policy="row head/projection SHA claims identify numerical state metadata; captured_source_head identifies separate replay source metadata",
            mode_metrics={role: {"present_count": sum(role in row["present_roles"] for row in records),
                "supported_comparison_count": sum(row["returned_mode_comparisons"][role]["exact_fragment_match"] is not None for row in records),
                "matched_fragment_count": sum(row["returned_mode_comparisons"][role]["exact_fragment_match"] is True for row in records),
                "missing_mode_count": sum(row["returned_mode_comparisons"][role]["status"] == "missing_mode" for row in records),
                "unsupported_comparison_count": sum(row["returned_mode_comparisons"][role]["status"] == "unsupported_source_or_native_codec" for row in records)}
                for role in native.ROLES[:2]},
            source_label_baseline_metrics={"candidate_digest_match_count": sum(row["source_label_baseline"]["candidate_digest_matches_source_fragment"] is True for row in records),
                "model_inference_performed": False, "mapped_to_final_scorer_model_off": False},
            training_cost={"new_training_executed": False, "new_training_seconds": 0,
                "historical_claimed_training_executed": prior["recorded_qualification"]["claimed_training_executed"],
                "historical_recorded_qualification_seconds": prior["recorded_qualification"]["recorded_seconds"]},
            input_bytes=pins.total + inner_bytes,
            counted_input_reads=len(pins.files) + len(inner),
            input_files=[{"path": str(path), "sha256": audit._sha(body), "size_bytes": len(body)}
                         for path, body in sorted({**pins.files, **original_native}.items())],
            retained_files=[{"path": path.relative_to(output).as_posix(), "sha256": audit._sha(body), "size_bytes": len(body)} for path, body in sorted(copies.items())])
        report["source_structural_comparison_available"] = any(row["expected_native_fragment"] is not None for row in records)
    except (audit.AuditInputError, OSError, ValueError, TypeError, KeyError, RecursionError) as exc:
        report.update(error=f"{type(exc).__name__}: {exc}")
    final._write(output / REPORT_NAME, report)
    (output / REPORT_NAME).chmod(0o600)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = evaluate(args.manifest, args.output)
    except (audit.AuditInputError, OSError, ValueError, TypeError, KeyError, RecursionError) as exc:
        parser.exit(3, f"native source comparison refused: {type(exc).__name__}: {exc}\n")
    print(audit._canonical({key: report[key] for key in ("status", "manifest_sha256", "source_replay_sha256", "diagnostics_report_sha256")}).decode())
    return 0 if report["status"] == "passed" else 3


if __name__ == "__main__":
    sys.exit(main())
