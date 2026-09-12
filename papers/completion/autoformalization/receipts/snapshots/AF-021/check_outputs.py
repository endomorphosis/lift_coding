#!/usr/bin/env python3
"""Independent AF-021 output checks against the four acceptance criteria."""
from __future__ import annotations

import json
import sys
from pathlib import Path

FORBIDDEN = ("[TBD]", "[TODO]", "[To complete")
ARMS6 = ("A", "B", "C", "D", "E")
ARMS11 = ("T0", "T1", "T2", "T3", "T4", "T5")
COLS6 = ("sources_covered", "fidelity_uncertainty", "correct_transfers", "cost_latency")
COLS11 = ("source_split_counts", "held_out_fidelity", "proof_route_benefit", "total_cost")


def find_repo_root(start: Path) -> Path:
    marker = Path("papers/completion/autoformalization/config/environment_manifest.json")
    for path in (start, *start.parents):
        if (path / marker).is_file():
            return path
    raise SystemExit("cannot locate repository root from check_outputs.py")


HERE = Path(__file__).resolve().parent
REPO_ROOT = find_repo_root(HERE)
PAPER = REPO_ROOT / "papers/completion/autoformalization"
RESULTS = PAPER / "results"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    errors: list[str] = []
    summary_path = RESULTS / "summary.json"
    table6 = RESULTS / "table6_pipeline.tex"
    table11 = RESULTS / "table11_training.tex"
    table13 = RESULTS / "table13_assistance.tex"
    hypothesis = RESULTS / "hypothesis_report.md"
    for path in (summary_path, table6, table11, table13, hypothesis):
        if not path.is_file():
            errors.append(f"missing {path}")
    if errors:
        print("AF-021 check failed:\n- " + "\n- ".join(errors))
        return 1
    summary = load_json(summary_path)
    texts = {
        "table6": table6.read_text(encoding="utf-8"),
        "table11": table11.read_text(encoding="utf-8"),
        "table13": table13.read_text(encoding="utf-8"),
        "hypothesis": hypothesis.read_text(encoding="utf-8"),
        "summary": summary_path.read_text(encoding="utf-8"),
    }
    for name, text in texts.items():
        for token in FORBIDDEN:
            if token in text:
                errors.append(f"{name} still contains {token}")

    if summary.get("original_placeholder_cells") != 44:
        errors.append("summary does not account for 44 original placeholder cells")
    if summary.get("remaining_placeholder_cells") != 0:
        errors.append("placeholder cells remain")
    cells6 = summary.get("table6", {}).get("cells") or []
    cells11 = summary.get("table11", {}).get("cells") or []
    if len(cells6) != 20:
        errors.append(f"Table 6 has {len(cells6)} cells, expected 20")
    if len(cells11) != 24:
        errors.append(f"Table 11 has {len(cells11)} cells, expected 24")
    expected6 = [f"{arm}:{col}" for arm in ARMS6 for col in COLS6]
    expected11 = [f"{arm}:{col}" for arm in ARMS11 for col in COLS11]
    if [c.get("cell_id") for c in cells6] != expected6:
        errors.append("Table 6 cell order drifted")
    if [c.get("cell_id") for c in cells11] != expected11:
        errors.append("Table 11 cell order drifted")

    for cell in cells6 + cells11:
        cid = cell.get("cell_id")
        if not str(cell.get("definition") or "").strip():
            errors.append(f"{cid} missing definition")
        if not str(cell.get("narrowed_claim") or "").strip():
            errors.append(f"{cid} missing narrowed claim")
        if not str(cell.get("display") or "").strip():
            errors.append(f"{cid} missing display")
        if cell.get("column") in {"fidelity_uncertainty", "held_out_fidelity"}:
            if cell.get("status") != "unmeasured" or cell.get("value") is not None:
                errors.append(f"{cid} fidelity is not an explicit unmeasured null")
            interval = cell.get("interval") or {}
            if interval.get("low") is not None or interval.get("high") is not None:
                errors.append(f"{cid} invented a fidelity interval")
        if cell.get("column") != "source_split_counts" and cell.get("denominator") != 1913:
            errors.append(f"{cid} denominator is not 1913")
        if cell.get("status") in {"unrun", "unavailable", "unmeasured"} and cell.get("value") is not None:
            errors.append(f"{cid} inserted a numeric value under {cell.get('status')}")

    for key in ("raw_counts", "denominators", "seeds", "grouping", "missingness", "confidence_interval_method"):
        if key not in summary:
            errors.append(f"summary missing {key}")
    if summary.get("seeds") != [104729, 130363, 155921]:
        errors.append("frozen seeds drifted")
    grouping = summary.get("grouping") or {}
    if grouping.get("final_test_groups") != 20:
        errors.append("final-test grouping is not 20 source-family/time groups")
    missing = summary.get("missingness") or {}
    if missing.get("independent_gold_present") is not False:
        errors.append("independent gold was claimed present")
    if (missing.get("human_review_seconds") or {}).get("table_status") != "unmeasured":
        errors.append("human review was not kept unmeasured")
    ci = summary.get("confidence_interval_method") or {}
    if "cluster bootstrap" not in str(ci.get("prespecified") or "").lower():
        errors.append("CI method is not the prespecified cluster bootstrap")
    if ci.get("computed_on_final_test_primary_metrics") is not False:
        errors.append("CI was claimed computed on unrun final-test metrics")

    false_transfer = summary.get("false_transfer") or {}
    if false_transfer.get("generalized_to_universal_soundness") is not False:
        errors.append("zero observed false transfers was generalized to universal soundness")
    statement = str(false_transfer.get("statement") or "")
    if "not generalized" not in statement.lower() or "universal soundness" not in statement.lower():
        errors.append("false-transfer non-generalization statement missing")
    if "Zero observed false transfers is not generalized to universal soundness." not in texts["hypothesis"]:
        errors.append("hypothesis report missing false-transfer guardrail")

    if summary.get("negative_and_inconclusive_retained") is not True:
        errors.append("negative/inconclusive results were not retained")
    if summary.get("post_hoc_selection_represented_as_prespecified") is not False:
        errors.append("post-hoc test selection was represented as prespecified")
    if "not represented as prespecified" not in texts["hypothesis"]:
        errors.append("hypothesis report missing post-hoc guardrail")
    statuses = {item.get("id"): item.get("status") for item in summary.get("hypotheses") or []}
    for hid in ("C1", "C2", "C3", "C4", "C5", "C6"):
        if statuses.get(hid) == "supported":
            errors.append(f"{hid} is marked supported without independent/final-test evidence")
    if statuses.get("C7") not in {"inconclusive", "unrun", "unsupported"}:
        errors.append("C7 must remain inconclusive, unrun, or unsupported")
    if statuses.get("H-T2-shared-learner") == "supported":
        errors.append("T2 generalization was marked supported")
    if missing.get("arm_E_activated") is not False:
        errors.append("Arm E was promoted")

    report = {
        "ok": not errors,
        "errors": errors,
        "original_placeholder_cells": summary.get("original_placeholder_cells"),
        "replaced_placeholder_cells": summary.get("replaced_placeholder_cells"),
        "remaining_placeholder_cells": summary.get("remaining_placeholder_cells"),
        "hypothesis_status_counts": summary.get("hypothesis_status_counts"),
        "false_transfer_generalized": false_transfer.get("generalized_to_universal_soundness"),
        "post_hoc_as_prespecified": summary.get("post_hoc_selection_represented_as_prespecified"),
        "ci_method": ci.get("prespecified"),
        "seeds": summary.get("seeds"),
        "final_test_groups": grouping.get("final_test_groups"),
        "denominator": summary.get("denominators", {}).get("table6_final_test"),
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
