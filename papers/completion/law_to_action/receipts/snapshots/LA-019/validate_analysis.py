#!/usr/bin/python3.12
"""Validate LA-019 analysis outputs against raw records and the snapshot copy."""

from __future__ import annotations

import hashlib
import json
import re
import runpy
import sys
from pathlib import Path

SNAP = Path(__file__).resolve().parent
ROOT = SNAP.parents[5]
LIVE = ROOT / "papers" / "completion" / "law_to_action"
ANALYZE = LIVE / "analysis" / "analyze.py"
BANNED = (
    "universal legal correctness",
    "universal prevention",
    "universally correct",
    "universally safe",
    "universally prevent",
    "legal correctness rate",
    "prevents all forbidden",
    "guarantees legal",
)
DENIAL = "not universal legal correctness or universal prevention"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def iter_files(directory: Path):
    return sorted(path for path in directory.rglob("*") if path.is_file())


def main() -> int:
    require(ANALYZE.is_file(), f"missing {ANALYZE}")
    require((SNAP / "analyze.py").is_file(), "missing snapshot analyze.py")
    require(ANALYZE.read_bytes() == (SNAP / "analyze.py").read_bytes(), "live analyze.py differs from snapshot")

    sys.path.insert(0, str(ANALYZE.parent))
    module = runpy.run_path(str(ANALYZE), run_name="la019_analyze")
    check = module["check_outputs"]
    check(ROOT)

    live_tables = LIVE / "results" / "tables"
    live_figures = LIVE / "results" / "figures"
    snap_tables = SNAP / "outputs" / "results" / "tables"
    snap_figures = SNAP / "outputs" / "results" / "figures"
    require(live_tables.is_dir() and snap_tables.is_dir(), "tables directories missing")
    require(live_figures.is_dir() and snap_figures.is_dir(), "figures directories missing")

    live_table_files = {path.relative_to(live_tables): path for path in iter_files(live_tables)}
    snap_table_files = {path.relative_to(snap_tables): path for path in iter_files(snap_tables)}
    require(live_table_files.keys() == snap_table_files.keys(), "live/snapshot table set mismatch")
    for rel, path in live_table_files.items():
        require(path.read_bytes() == snap_table_files[rel].read_bytes(), f"table mismatch: {rel}")

    for name in ("statistical_report.md", "failure_taxonomy.json"):
        live_path = LIVE / "results" / name
        snap_path = SNAP / "outputs" / "results" / name
        require(live_path.is_file() and snap_path.is_file(), f"missing {name}")
        require(live_path.read_bytes() == snap_path.read_bytes(), f"live/snapshot mismatch: {name}")

    live_figure_files = {path.relative_to(live_figures): path for path in iter_files(live_figures)}
    snap_figure_files = {path.relative_to(snap_figures): path for path in iter_files(snap_figures)}
    require(live_figure_files.keys() == snap_figure_files.keys(), "live/snapshot figure set mismatch")
    for rel, path in live_figure_files.items():
        require(path.read_bytes() == snap_figure_files[rel].read_bytes(), f"figure mismatch: {rel}")

    required_stems = (
        "fig01_arm_forbidden_effects",
        "fig02_arm_allowed_utility",
        "fig03_ablation_deltas",
        "fig04_efficiency_phases",
        "fig05_failure_taxonomy",
        "fig06_family_sensitivity",
        "fig07_mutation_by_arm",
    )
    for stem in required_stems:
        require((live_figures / f"{stem}.svg").is_file(), f"missing figure {stem}.svg")
        require((live_figures / f"{stem}.pdf").is_file() or (live_figures / f"{stem}.svg").is_file(), f"missing figure {stem}")
    require((live_figures / "source_to_effect_trace.pdf").is_file(), "LA-020 source_to_effect_trace.pdf missing from figures/")

    report = (LIVE / "results" / "statistical_report.md").read_text(encoding="utf-8")
    taxonomy = load_json(LIVE / "results" / "failure_taxonomy.json")
    claims = load_json(live_tables / "headline_claims.json")
    arms = load_json(live_tables / "arm_safety_utility.json")
    inventory = load_json(live_tables / "analysis_inventory.json")
    leakage = load_json(live_tables / "leakage_audit.json")

    lowered = report.lower()
    for phrase in BANNED:
        start = 0
        while True:
            idx = lowered.find(phrase, start)
            if idx < 0:
                break
            window = lowered[max(0, idx - 48) : idx + len(phrase) + 16]
            require(
                any(marker in window for marker in ("not ", "never ", "no observed", "treated as", "without claiming")),
                f"report uses banned phrase without denial: {phrase}",
            )
            start = idx + len(phrase)
    require("hand-entered" in report.lower() or "not hand-entered" in report.lower(), "report must state values are not hand-entered")
    require(taxonomy["independent_human_gold"] is False, "taxonomy claims human gold")
    require(taxonomy["schema"] == "law-to-action-failure-taxonomy/v1", "taxonomy schema")
    require(len(taxonomy["stages"]) >= 6, "taxonomy stages missing")
    require(len(claims) >= 6, "headline claims missing")
    for claim in claims:
        require(claim.get("id"), "claim missing id")
        require(claim.get("raw_source", "").startswith("papers/completion/law_to_action/results/"), f"{claim.get('id')} raw_source")
        require(claim.get("wilson_95") or claim.get("cluster_bootstrap_95"), f"{claim.get('id')} missing interval")
        require(
            claim.get("evidence_attempt_ids") or claim.get("residual_attempt_ids") or claim.get("failed_case_ids") or claim.get("unsupported_case_ids"),
            f"{claim.get('id')} missing case/run IDs",
        )
        blob = json.dumps(claim).lower()
        if "universal legal correctness" in blob or "universal prevention" in blob:
            require("not universal" in blob, f"{claim.get('id')} describes a bounded rate as universal")

    a4 = next(row for row in arms if row["arm_id"] == "A4")
    require(a4["forbidden_wilson_low"] is not None and a4["forbidden_wilson_high"] is not None, "A4 missing Wilson interval")
    require(a4["forbidden_den"] > 0, "A4 forbidden denominator vanished")
    if a4["forbidden_num"] == 0:
        require(a4["forbidden_rule_of_3_upper"] is not None, "zero-event A4 missing rule-of-3 bound")

    source_text = ANALYZE.read_text(encoding="utf-8")
    require("hand-entered" in source_text and "are not" in source_text, "analyze.py must state it does not hand-enter results")
    require(leakage["atomic_family_assignment"] is True, "leakage audit failed")
    require(inventory["inputs"]["fixed_raw"]["present"], "inventory missing fixed_raw pin")
    require(re.fullmatch(r"[0-9a-f]{64}", inventory["inputs"]["fixed_raw"]["sha256"] or ""), "fixed_raw hash")

    print("LA-019 validator: analysis recreates tables/figures from raw IDs with uncertainty")
    print(f"tables={len(live_table_files)} figures={len(live_figure_files)} claims={len(claims)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
