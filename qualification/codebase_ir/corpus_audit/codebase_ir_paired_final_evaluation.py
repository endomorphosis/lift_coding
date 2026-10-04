#!/usr/bin/env python3
"""Compare explicitly pinned locked FINAL exports without selecting a model."""
from __future__ import annotations

import argparse
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import codebase_ir_corpus_audit as audit
import codebase_ir_final_evaluation as final
import codebase_ir_final_lock as lock_tool
import codebase_ir_locked_final_evaluation as locked

INPUT_SCHEMA = "codebase-ir-paired-final-evaluation-input@1"
REPORT_SCHEMA = "codebase-ir-paired-final-evaluation@1"
MODES = ("learned", "model_off", "zero_head")
STAGES = ("raw", "constrained")
TRANSITIONS = ("gain", "regression", "unchanged_correct", "unchanged_incorrect")
CLAIMS = {**lock_tool.CLAIMS, "learned_quality_improvement_verified": False,
          "independent_samples_established": False, "paired_records_are_independent_samples": False}
SCOPE = "paired recorded output transitions under one selected unsigned FINAL byte lock"


@dataclass(frozen=True)
class Limits:
    # Each underlying lock capture remains limited to 256 files/16 MiB.
    # Six outer first reads, including the spec, have a separate 1 MiB ceiling.
    max_files: int = 518
    max_total_bytes: int = 38 * 1024 * 1024
    max_json_bytes: int = 1024 * 1024

    def __post_init__(self):
        audit._require(all(type(value) is int and value > 0 for value in asdict(self).values()),
                       "positive exact paired evaluation bounds required")


DEFAULT_LIMITS = Limits()


class Pins:
    def __init__(self, limits):
        self.limits, self.files, self.total = limits, {}, 0

    def read(self, path, maximum):
        if path not in self.files:
            audit._require(len(self.files) < self.limits.max_files, "paired input file budget exceeded")
            maximum = min(maximum, self.limits.max_json_bytes, self.limits.max_total_bytes - self.total)
            audit._require(maximum >= 0, "paired input byte budget exceeded")
            raw = final.Capture.regular(path, maximum)
            self.files[path] = raw
            self.total += len(raw)
        audit._require(len(self.files[path]) <= maximum, "paired descriptor budget exceeded")
        return self.files[path]

    def descriptor(self, value):
        audit._closed(value, {"path", "sha256", "size_bytes"}, "paired external descriptor")
        path = Path(audit._text(value["path"], "paired external path"))
        audit._require(path.is_absolute() and str(path) == value["path"], "canonical absolute paired input required")
        audit._digest(value["sha256"], "paired external SHA")
        size = value["size_bytes"]
        audit._require(type(size) is int and 0 <= size <= self.limits.max_json_bytes,
                       "exact bounded paired descriptor size required")
        raw = self.read(path, size)
        audit._require(len(raw) == size and audit._sha(raw) == value["sha256"], "paired external pin mismatch")
        return path, raw

    def recheck(self):
        for path, raw in self.files.items():
            audit._require(final.Capture.regular(path, len(raw)) == raw, "paired selected input drifted")


def _transition(before, after):
    if before == after:
        return "unchanged_correct" if before else "unchanged_incorrect"
    return "gain" if after else "regression"


def _relevant(metric, case):
    if metric == "source_binding":
        return True
    if metric == "unsupported_disposition":
        return case["status"] == "unsupported"
    if case["status"] != "supported":
        return False
    if metric in {"references", "operators", "literals"}:
        return bool(final.validate_target(case["target"])[metric])
    return True


def _comparison(before, after, cases):
    raw = [{row["prediction_id"]: row for row in side["predictions"]["rows"]} for side in (before, after)]
    scored = [{row["prediction_id"]: row for row in side["report"]["prediction_results"]} for side in (before, after)]
    counts = {mode + "/" + stage: {metric: dict.fromkeys(TRANSITIONS, 0) for metric in final.METRICS}
              for mode in MODES for stage in STAGES}
    rows = []
    for prediction_id in sorted(set(raw[0]) | set(raw[1])):
        left, right = raw[0].get(prediction_id), raw[1].get(prediction_id)
        selected = left or right
        case, mode = cases[selected["case_id"]], selected["mode"]
        row = {"prediction_id": prediction_id, "case_id": selected["case_id"], "mode": mode,
               "source_status": case["status"], "source_binding_before": left["source_binding"] if left else None,
               "source_binding_after": right["source_binding"] if right else None,
               "pair_status": "paired" if left and right else "missing_after" if left else "missing_before"}
        if left and right:
            audit._require((left["case_id"], left["mode"]) == (right["case_id"], right["mode"]),
                           "prediction ID changes case or mode across exports")
        for stage in STAGES:
            old = scored[0].get(prediction_id, {}).get(stage)
            new = scored[1].get(prediction_id, {}).get(stage)
            metrics = {}
            for metric in final.METRICS:
                relevant = _relevant(metric, case)
                disposition = _transition(old["correct"][metric], new["correct"][metric]) if old and new and relevant else None
                metrics[metric] = {"relevant": relevant, "before_correct": old["correct"][metric] if old else None,
                                   "after_correct": new["correct"][metric] if new else None, "transition": disposition}
                if disposition:
                    counts[mode + "/" + stage][metric][disposition] += 1
            row[stage] = {"before": left[stage] if left else None, "after": right[stage] if right else None,
                          "output_changed": audit._canonical(left[stage]) != audit._canonical(right[stage]) if left and right else None,
                          "metrics": metrics, "findings_before": old["findings"] if old else None,
                          "findings_after": new["findings"] if new else None,
                          "findings_added": sorted(set(new["findings"]) - set(old["findings"])) if old and new else None,
                          "findings_resolved": sorted(set(old["findings"]) - set(new["findings"])) if old and new else None}
        rows.append(row)

    populations = []
    unique = {}
    for mode in MODES:
        mode_populations = []
        for case_id in sorted(cases):
            selected = [[row for row in side.values() if row["case_id"] == case_id and row["mode"] == mode] for side in raw]
            left_ids, right_ids = ([row["prediction_id"] for row in group] for group in selected)
            left_ids, right_ids = sorted(left_ids), sorted(right_ids)
            problems = []
            if len(left_ids) != 1 or len(right_ids) != 1:
                problems.append("multiple_controls" if len(left_ids) > 1 or len(right_ids) > 1 else "missing_mode")
            if left_ids != right_ids:
                problems.append("unpaired_prediction_ids")
            population = {"case_id": case_id, "mode": mode, "source_status": cases[case_id]["status"],
                          "before_prediction_ids": left_ids, "after_prediction_ids": right_ids,
                          "before_count": len(left_ids), "after_count": len(right_ids),
                          "unique_paired_case": not problems, "unknown_reasons": problems}
            populations.append(population)
            mode_populations.append(population)
        available = all(row["unique_paired_case"] for row in mode_populations)
        unique[mode] = {"status": "available" if available else "unknown", "case_count": len(cases),
                        "unknown_case_ids": [row["case_id"] for row in mode_populations if not row["unique_paired_case"]],
                        "metric_transitions": {stage: counts[mode + "/" + stage] for stage in STAGES} if available else None,
                        "independence_verified": False}
    paired = [row for row in rows if row["pair_status"] == "paired"]
    return {"pairing_policy": "exact prediction ID with unchanged case/mode; no matching by output or best score",
            "row_count": len(rows), "paired_record_count": len(paired),
            "missing_before_prediction_ids": [row["prediction_id"] for row in rows if row["pair_status"] == "missing_before"],
            "missing_after_prediction_ids": [row["prediction_id"] for row in rows if row["pair_status"] == "missing_after"],
            "changed_output_counts": {stage: sum(row[stage]["output_changed"] for row in paired) for stage in STAGES},
            "record_metric_transitions": counts,
            "metric_count_scope": "paired exported records, never independent samples; missing records contribute no success",
            "case_mode_populations": populations, "unique_case_summaries": unique, "prediction_pairs": rows}


def evaluate(manifest: Path, output: Path, limits: Limits = DEFAULT_LIMITS):
    manifest, output = manifest.absolute(), output.absolute()
    pins = Pins(limits)
    raw = pins.read(manifest, limits.max_json_bytes)
    spec = audit._closed(final._json(raw, final.DEFAULT_LIMITS), {"schema", "lock", "before", "after"}, "paired evaluation input")
    audit._require(spec["schema"] == INPUT_SCHEMA, "versioned paired evaluation input required")
    lock_path, lock_raw = pins.descriptor(spec["lock"])
    sides = []
    for name in ("before", "after"):
        side = audit._closed(spec[name], {"manifest", "report"}, "paired side")
        source, source_raw = pins.descriptor(side["manifest"])
        report_path, report_raw = pins.descriptor(side["report"])
        sides.append({"name": name, "manifest": source, "manifest_raw": source_raw,
                      "report_path": report_path, "report_raw": report_raw,
                      "report": final._json(report_raw, final.DEFAULT_LIMITS)})
    protected = [manifest.parent, lock_path.parent, *(side[key].parent for side in sides for key in ("manifest", "report_path"))]
    lock_tool._preflight_output(output, protected)
    total_files, total_bytes = len(pins.files), pins.total
    for side in sides:
        remaining_files, remaining_bytes = limits.max_files - total_files, limits.max_total_bytes - total_bytes
        audit._require(remaining_files > 0 and remaining_bytes > 0, "paired shared capture budget exceeded")
        bounds = lock_tool.Limits(min(lock_tool.DEFAULT_LIMITS.max_total_bytes, remaining_bytes),
                                  min(lock_tool.DEFAULT_LIMITS.max_files, remaining_files))
        receipt, captures, budget = lock_tool.validate_locked(side["manifest"], lock_path, spec["lock"]["sha256"], bounds)
        audit._require(captures[0].raw == lock_raw and captures[-1].raw == side["manifest_raw"], "paired first capture differs from external pins")
        side.update(captures=captures, receipt=receipt, capture_budget=budget)
        total_files += budget.files
        total_bytes += budget.bytes
    audit._require(sides[0]["receipt"] == sides[1]["receipt"], "paired exports use different lock identities")
    # The fixed baseline excludes the mutable prediction body. The current
    # capture already includes it, so re-running _material there would mistake
    # that separately captured body for a protected fixed selector.
    _, cases, _, _ = lock_tool._material(sides[0]["captures"][1])
    lock_tool._preflight_output(output, [*protected, *(capture.root for side in sides for capture in side["captures"])])
    pins.recheck()
    for side in sides:
        for capture in side["captures"]:
            capture.recheck()
    output.mkdir(exist_ok=False)
    report = {"schema": REPORT_SCHEMA, "status": "refused", "scope": SCOPE, **CLAIMS,
              "manifest_sha256": audit._sha(raw), "lock_sha256": spec["lock"]["sha256"],
              "locked_identity_sha256": sides[0]["receipt"]["locked_identity_sha256"],
              "protocol_id": sides[0]["receipt"]["protocol_id"], "lock_enforced": True,
              "input_files_unchanged": False, "raw_outputs_retained_unmodified": False,
              "source_reports_independently_rederived": False}
    try:
        retained = {output / "comparison_input.json": raw}
        with (output / "comparison_input.json").open("xb") as stream:
            stream.write(raw)
        for side in sides:
            base = output / ("captured-" + side["name"])
            base.mkdir()
            lock_root = base / "lock"
            lock_root.mkdir()
            with (lock_root / lock_path.name).open("xb") as stream:
                stream.write(lock_raw)
            retained[lock_root / lock_path.name] = lock_raw
            side["captures"][1].retain(lock_root)
            side["captures"][-1].retain(base / "evaluation")
            for capture, prefix in ((side["captures"][1], lock_root),
                                    (side["captures"][-1], base / "evaluation")):
                retained.update({prefix / "inputs" / path.relative_to(capture.root): body
                                 for path, body in capture.files.items()})
            with (base / "pinned_report.json").open("xb") as stream:
                stream.write(side["report_raw"])
            retained[base / "pinned_report.json"] = side["report_raw"]
            rederived = output / ("rederived-" + side["name"])
            reconstructed = locked.evaluate(base / "evaluation/inputs" / side["manifest"].name,
                                             lock_root / lock_path.name, spec["lock"]["sha256"],
                                             rederived)
            audit._require(reconstructed["status"] == "passed"
                           and audit._canonical(reconstructed) == audit._canonical(side["report"]),
                           "pinned scoring report differs from full independently reconstructed report")
            retained[rederived / "final_evaluation.json"] = audit._canonical(reconstructed) + b"\n"
            for capture, prefix in ((side["captures"][0], rederived / "lock_receipt"),
                                    (side["captures"][1], rederived / "lock_baseline"),
                                    (side["captures"][-1], rederived / "evaluation"),
                                    (side["captures"][-1], rederived / "scored")):
                retained.update({prefix / "inputs" / path.relative_to(capture.root): body
                                 for path, body in capture.files.items()})
            _, prediction_raw = side["captures"][-1].descriptor(side["captures"][-1].document["predictions"])
            side["predictions"] = final._json(prediction_raw, final.DEFAULT_LIMITS)
        report.update(_comparison(*sides, cases))
        all_files = dict(pins.files)
        for side in sides:
            for capture in side["captures"]:
                for path, body in capture.files.items():
                    audit._require(path not in all_files or all_files[path] == body, "paired captures disagree on selected bytes")
                    all_files[path] = body
        pins.recheck()
        for side in sides:
            for capture in side["captures"]:
                capture.recheck()
        for path, body in retained.items():
            audit._require(final.Capture.regular(path, len(body)) == body,
                           "paired retained raw copy changed before report publication")
        report.update(status="passed", input_files_unchanged=True, raw_outputs_retained_unmodified=True,
                      source_reports_independently_rederived=True, case_count=len(cases),
                      before_prediction_count=len(sides[0]["predictions"]["rows"]),
                      after_prediction_count=len(sides[1]["predictions"]["rows"]),
                      prediction_origins={side["name"]: side["predictions"]["producer"]["origin"] for side in sides},
                      producer_before=sides[0]["predictions"]["producer"], producer_after=sides[1]["predictions"]["producer"],
                      source_report_sha256={side["name"]: audit._sha(side["report_raw"]) for side in sides},
                      source_manifest_sha256={side["name"]: audit._sha(side["manifest_raw"]) for side in sides},
                      input_files=[{"path": str(path), "sha256": audit._sha(body), "size_bytes": len(body)} for path, body in sorted(all_files.items())],
                      captured_read_count=total_files, captured_read_bytes=total_bytes, limits=asdict(limits))
    except (audit.AuditInputError, OSError, ValueError, TypeError, KeyError, RecursionError) as exc:
        report.update(status="refused", input_files_unchanged=False, error=f"paired evaluation refusal: {type(exc).__name__}: {exc}")
    final._write(output / "paired_final_evaluation.json", report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = evaluate(args.manifest, args.output)
    except (audit.AuditInputError, OSError, ValueError, TypeError, KeyError, RecursionError) as exc:
        parser.exit(3, f"paired FINAL evaluation refused: {type(exc).__name__}: {exc}\n")
    print(audit._canonical({key: report.get(key) for key in ("status", "manifest_sha256", "lock_sha256", "paired_record_count", "changed_output_counts")}).decode())
    return 0 if report["status"] == "passed" else 3


if __name__ == "__main__":
    sys.exit(main())
