#!/usr/bin/python3.12
"""Ordinary NS-019 rendered-analysis check. No grants, providers, scorers, or reruns."""
from __future__ import annotations

import ast
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve()
while not (ROOT / "scripts" / "paper_supervisors.py").is_file():
    if ROOT.parent == ROOT:
        raise SystemExit("repository root not found")
    ROOT = ROOT.parent

P = ROOT / "papers/completion/neurosymbolic_supervision"
SNAP = P / "receipts/snapshots/NS-019"
RENDER = SNAP / "rendered_final32"
MAIN = P / "runs/main"
ABLATIONS = P / "runs/ablations"
POLICY = P / "pilot/recovery/final_input_source/analysis_policy.json"

ANALYZER_SHA = "16da76bbe3fe032cde70599790ad8ad1e52d9eb1baf4ea799cf4856d23410251"
RESULTS_SHA = "6b07e88ff02ad6674fd5979b361f4de4f121ec6b58906927d8cbfafca86b972e"
STATS_SHA = "24e978ad64e73f2c4485e641f3b162b170c5a76c8d71c874b60fba9a21346826"
COST_SHA = "3fdd110eaf153cc6290f06861873928118fe507768959a6358f822a0f1ec7ed2"
TABLE17_SHA = "ffbb7f2e6aecefb0e4a65fe2da32cc43e87601e01eb7ab97715e516a22cc0b79"
ABLATIONS_TEX_SHA = "8c57477902aba200e9a2228d6a316ec06f14859f7894fa1f534f16e8b19d8ccf"
PDF_SHA = "8ea081bca5d5e309cc5659628b7ceea5e053089b3adfd1d5ae11a7f5c163e4a5"
SVG_SHA = "e1503343b198855975b3136e44efbe5330791945435bfabf99b53ea9a400cc90"
MAIN_MANIFEST_SHA = "0891bee6e3a556f5448250bbf11815ac255958a2f02add848d4e0934f23aeeac"
ABLATION_MANIFEST_SHA = "15c8fb2d05ffcd02ecb105f6498288f43ef2717ea3db5605d95d277c0195e5d0"
POLICY_SHA = "a0edbc1cdf13f1d5aab4170dd60fcb3a3b2ef26d192f6dbbdce9b6a26ff700d3"
FREEZE_FILE_SHA = "7175ca68247d958dabf83a97441fe6042d3b88feafa74f95c76e1720cc74fa1a"
FREEZE_CANONICAL_SHA = "ac605b5de8b58cc41c5c3609e7752e5e4441ab627dbbe6d31f4d8d086b33732d"
REDUCER_SHA = "ed7ebc7d939c9592537e33a6a37a6962ceaeca84b5da3b5efd0cbb641f652e94"
ANALYSIS_SHA = "824366e7fb10725be884b04448d5b4a8dd2ff5c478af5df7a8c98721f4641766"
EMPTY_SHA = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
FAMILIES = (
    "ns-hist-09-tomlkit",
    "ns-hist-10-installer",
    "ns-hist-11-tornado",
    "ns-hist-12-more-itertools",
    "ns-hist-13-charset_normalizer",
    "ns-hist-14-iniconfig",
    "ns-hist-15-wheel",
    "ns-hist-16-jinja",
)
OUTCOMES = {
    "full_cold_pass": 9,
    "hidden_acceptance_failed": 7,
    "known_proposal_failure": 2,
    "proposal_child_deadline": 14,
}
CURRENT = {
    P / "analysis/analyze.py": ANALYZER_SHA,
    P / "analysis/results.json": RESULTS_SHA,
    P / "analysis/statistical_report.md": STATS_SHA,
    P / "analysis/cost_report.md": COST_SHA,
    P / "manuscript/generated/table17.tex": TABLE17_SHA,
    P / "manuscript/generated/ablations.tex": ABLATIONS_TEX_SHA,
    P / "manuscript/generated/figures/family_useful.pdf": PDF_SHA,
    P / "manuscript/generated/figures/family_useful.svg": SVG_SHA,
}
SNAPSHOTS = {
    SNAP / "analyze.py": ANALYZER_SHA,
    RENDER / "analysis/results.json": RESULTS_SHA,
    RENDER / "analysis/statistical_report.md": STATS_SHA,
    RENDER / "analysis/cost_report.md": COST_SHA,
    RENDER / "manuscript/generated/table17.tex": TABLE17_SHA,
    RENDER / "manuscript/generated/ablations.tex": ABLATIONS_TEX_SHA,
    RENDER / "manuscript/generated/figures/family_useful.pdf": PDF_SHA,
    RENDER / "manuscript/generated/figures/family_useful.svg": SVG_SHA,
}
CRITERIA = (
    "One documented analysis command regenerates main and ablation tables from immutable raw records.",
    "All counts reconcile to the run manifest, including failed/unsolved/timeout/abstained/unavailable cases.",
    "Confidence intervals and quality gates follow the preregistered plan; deviations and inconclusive outcomes are explicit.",
    "No estimated preliminary number is labeled measured, no missing cost is zero, and overlapping stage times are not summed as elapsed.",
)
FORBIDDEN_CLAIMS = (
    "noninferiority margin",
    "superiority decision",
    "sixteen independent families",
    "32 independent repositories",
    "human-time estimate",
    "publication-comparison efficacy",
)


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require(ok: bool, message: str) -> None:
    if not ok:
        raise SystemExit(message)


def load_json(path: Path):
    return json.loads(path.read_bytes())


def main() -> int:
    require(sys.version_info[:2] == (3, 12), "Python 3.12 required")
    for path, expected in {**CURRENT, **SNAPSHOTS}.items():
        require(path.is_file() and sha(path) == expected, "hash mismatch: " + str(path.relative_to(ROOT)))
    print("output_snapshot_pairs", len(CURRENT))

    source = (P / "analysis/analyze.py").read_text(encoding="utf-8")
    require(
        "item['label'] not in by_label or by_label[item['label']] == item" in source,
        "qualified identical-label exception absent",
    )
    require("Ambiguous retained label" in source, "conflicting-label failure absent")
    tree = ast.parse(source)
    require(isinstance(tree, ast.Module), "analyzer is not valid Python")
    print("analyzer_sha256", ANALYZER_SHA)

    manifest = load_json(MAIN / "manifest.json")
    require(sha(MAIN / "manifest.json") == MAIN_MANIFEST_SHA, "NS017 manifest hash changed")
    require(manifest["schema"] == "ns017-actual-final32-main-adoption/v1", "actual NS017 schema required")
    require(manifest["planned_cells"] == 32 and manifest["terminal_cells"] == 32, "fixed32 denominator changed")
    require(manifest["independent_families"] == 8, "family count changed")
    require(manifest["nested_repetitions_per_family_arm"] == 2, "nested repetition count changed")
    require(manifest["freeze_file_sha256"] == FREEZE_FILE_SHA, "freeze file identity changed")
    require(manifest["freeze_canonical_sha256"] == FREEZE_CANONICAL_SHA, "canonical freeze identity changed")
    require(manifest["analysis_policy_sha256"] == POLICY_SHA, "analysis policy identity changed")
    require(len(manifest["ordered_cells"]) == 32 and len(set(manifest["ordered_cells"])) == 32, "cell order/identity changed")
    print("ns017_manifest_sha256", MAIN_MANIFEST_SHA)

    objects = manifest["retained_objects"]
    require(len(objects) == 685, "retained object count changed")
    by_label = {}
    duplicate_identical = 0
    for item in objects:
        prior = by_label.get(item["label"])
        if prior is None:
            by_label[item["label"]] = item
            continue
        require(prior == item, "conflicting retained label")
        duplicate_identical += 1
    require(len(by_label) == 683 and duplicate_identical == 2, "duplicate-label accounting changed")
    print("retained_labels", len(by_label), "identical_duplicate_records", duplicate_identical)

    ablation = load_json(ABLATIONS / "manifest.json")
    require(sha(ABLATIONS / "manifest.json") == ABLATION_MANIFEST_SHA, "NS018 ablation manifest hash changed")
    require(ablation["schema"] == "ns018-withdrawn-ablations-manifest/v1", "withdrawn ablation schema required")
    require(ablation["population"]["original_planned_factor_cells"] == 192, "original192 lineage changed")
    require(ablation["population"]["retained_main_cells"] == 32, "retained main count changed")
    require(ablation["population"]["withdrawn_planned_factor_cells"] == 160, "withdrawn cell count changed")
    require(ablation["population"]["unrecruited_families"] == 8, "unrecruited family count changed")
    require(ablation["population"]["withdrawn_disjoint_partition"] == {"non_AB_arm": 128, "AB_local_warm": 32},
            "withdrawn partition changed")
    require(sha(ABLATIONS / "attempts.jsonl") == EMPTY_SHA and sha(ABLATIONS / "resource_measurements.jsonl") == EMPTY_SHA,
            "measured ablation rows are not empty")
    print("ns018_ablation_manifest_sha256", ABLATION_MANIFEST_SHA)

    policy = load_json(POLICY)
    require(sha(POLICY) == POLICY_SHA, "frozen analysis policy hash changed")
    require(policy["fixed_denominator"] == 32 and policy["independent_family_count"] == 8, "policy denominator changed")
    require(policy["nested_repetitions"] == [104729, 130363], "policy repetitions changed")
    require(policy["missing_cost_is_zero"] is False, "policy allows missing cost as zero")
    require(policy["bootstrap"]["resamples"] == 20000 and policy["bootstrap"]["seed"] == 20260911, "bootstrap gate changed")
    print("analysis_policy_sha256", POLICY_SHA)

    results = load_json(P / "analysis/results.json")
    require(results["schema"] == "ns019-complete32-rendered-analysis/v1", "rendered schema changed")
    require(results["complete"] is True and results["useful_completions"] == 9, "useful-completion count changed")
    require(results["outcomes"] == OUTCOMES, "outcome accounting changed")
    require(sum(OUTCOMES.values()) == 32, "outcomes do not reconcile to 32")
    require(results["arm_useful_fixed16"] == {"A": {"planned": 16, "useful": 5}, "B": {"planned": 16, "useful": 4}},
            "arm useful counts changed")
    require(results["mean_B_minus_A_useful"] == -0.0625, "paired family mean changed")
    require(len(results["rows"]) == 32, "rendered row count changed")
    require([row["cell_id"] for row in results["rows"]] == manifest["ordered_cells"], "rendered order differs")
    require(all(row["terminal"] is True for row in results["rows"]), "nonterminal row in rendered results")
    require(results["measured_ablation_rows"] == 0, "measured ablation rows invented")
    require(results["new_scientific_calls"] == 0 and results["candidate_or_hidden_replay"] is False,
            "new scientific call claimed")
    require(results["provenance"]["reducer_source_sha256"] == REDUCER_SHA, "reducer identity changed")
    require(results["provenance"]["analysis_sha256"] == ANALYSIS_SHA, "strict analysis identity changed")
    require(results["provenance"]["manifest_sha256"] == MAIN_MANIFEST_SHA, "results provenance manifest changed")
    require(results["provenance"]["ablation_manifest_sha256"] == ABLATION_MANIFEST_SHA, "results provenance ablation changed")
    require(results["provenance"]["signatures_reverified"] == 48, "signature reverify count changed")
    ci = results["bootstrap"]["quality_B_minus_A"]
    require(ci == {"degenerate": False, "lower": -0.1875, "upper": 0.0}, "quality interval changed")
    require("confirmatory" in results["bootstrap"]["interpretation"] or "descriptive" in results["bootstrap"]["interpretation"],
            "interval interpretation missing")
    require("No replacement original D/A confirmatory gate" in results["bootstrap"]["interpretation"],
            "withdrawn confirmatory gate not explicit")
    for name, summary in results["resource_summaries"].items():
        require(summary["missing_is_zero"] is False, "missing cost treated as zero: " + name)
        require(summary["planned_count"] == 32, "resource planned count changed: " + name)
    require(all(row["unknown_external_charge"] is True for row in results["rows"]), "unknown charge relabeled")
    require(all(v is None for k, v in results["ablation_unmeasured_cost_attribution"].items() if k != "reason"),
            "unmeasured ablation cost filled")
    units = [pair["unit"] for pair in results["paired_family_rows"]]
    require(units == list(FAMILIES), "paired family order changed")
    print("results_sha256", RESULTS_SHA)
    print("useful_completions", results["useful_completions"])
    print("outcomes", json.dumps(results["outcomes"], sort_keys=True))
    print("quality_B_minus_A", json.dumps(ci, sort_keys=True))

    stats = (P / "analysis/statistical_report.md").read_text(encoding="utf-8")
    require("Useful completion is 9/32" in stats, "statistical report useful count missing")
    require("[-0.1875, 0]" in stats, "statistical report interval missing")
    require("16-family inference were withdrawn" in stats, "withdrawn inference not explicit")
    require("proposal_child_deadline: 14" in stats and "hidden_acceptance_failed: 7" in stats, "failure classes missing")
    require("Unrecruited original families: 8" in stats, "unrecruited families missing")
    cost = (P / "analysis/cost_report.md").read_text(encoding="utf-8")
    require("never added together" in cost or "are added together" in cost, "non-additive clock rule missing")
    require("unavailable, never zero" in cost, "missing-cost rule missing")
    require("Gateway score | 83.394 | 16 / 32 | 16 |" in cost, "unscored scorer clock missing")
    require("settlement unavailable" in cost, "settlement labeled measured")
    require("No retained invocation record observed for this phase; no zero cost or extra trial inferred." in cost,
            "missing operator phase zeroed")
    table = (P / "manuscript/generated/table17.tex").read_text(encoding="utf-8")
    require("5 / 16" in table and "4 / 16" in table and "-0.0625" in table, "table17 totals changed")
    require("Repetitions are nested; the eight families are the analysis blocks." in table, "nested-repetition caption missing")
    ablation_tex = (P / "manuscript/generated/ablations.tex").read_text(encoding="utf-8")
    for endpoint in policy["unsupported_endpoints"]:
        require(endpoint.replace("_", r"\_") in ablation_tex or endpoint in ablation_tex, "ablation endpoint missing: " + endpoint)
    require("Non-A/B planned cells (128)" in ablation_tex, "non-A/B withdrawal missing")
    require("A/B warm planned cells (32)" in ablation_tex, "warm withdrawal missing")
    require("no measured ablation rows" in ablation_tex, "empty ablation rows not explicit")
    combined = stats + cost + table + ablation_tex
    for phrase in FORBIDDEN_CLAIMS:
        require(phrase not in combined, "forbidden claim present: " + phrase)
    pdf = P / "manuscript/generated/figures/family_useful.pdf"
    svg = P / "manuscript/generated/figures/family_useful.svg"
    require(pdf.read_bytes()[:5] == b"%PDF-" and svg.read_bytes().lstrip().startswith(b"<?xml"), "figure bytes invalid")
    figure_files = {p.name for p in (P / "manuscript/generated/figures").iterdir() if p.is_file()}
    require(figure_files == {"family_useful.pdf", "family_useful.svg"}, "unexpected figure files")
    print("table17_sha256", TABLE17_SHA)
    print("ablations_tex_sha256", ABLATIONS_TEX_SHA)
    print("scientific_calls", 0)
    print("status rendered_fixed32_analysis_verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
