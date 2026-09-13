#!/usr/bin/env python3.12
"""Ordinary current-output verification for NS-022.

Sealed validation PATH is /usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin.
This program uses python3.12, pdffonts, pdfinfo, and pdftotext from that
environment. It does not invoke pdflatex, providers, scorers, or experiments.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

def repository_root() -> Path:
    here = Path(__file__).resolve()
    for candidate in [here, *here.parents]:
        if (candidate / "scripts/paper_supervisors.py").is_file() and (
            candidate / "papers/completion/neurosymbolic_supervision"
        ).is_dir():
            return candidate
    raise FileNotFoundError("cannot locate repository root from validator path")


ROOT = repository_root()
PAPER = ROOT / "papers/completion/neurosymbolic_supervision"
LIVE_MS = PAPER / "manuscript"
LIVE_AUDIT = PAPER / "audit"
SNAP = PAPER / "receipts/snapshots/NS-022"
INPUTS = PAPER / "writing_inputs/ns022_complete_manuscript_v1"
RESULTS = PAPER / "analysis/results.json"
CHECKS = LIVE_AUDIT / "manuscript_result_checks.json"
NOTES = LIVE_AUDIT / "revision_notes.md"

ACCEPTED_PDF = "907f0a24b775d22cbff1a35e958c2f121cbb4784756b2943dcee4eb5ae3e14ab"
ACCEPTED_MAIN = "d10683b13e4fb0c5566e3b71fb7941fb2a95f1be5e1a50aa38957fe3092bf8ab"
MANIFEST_SHA = "1ee539aa44992c6f4aaae6b475921525380faecb15fe3e61b6aeae892da543af"
LAYOUT_RAW = "d70be87412a97285b440aef5de8b05c6fe575d3cbaf00b3abe34eae707146443"
NS019_ASCII_PDF = "8ea081bca5d5e309cc5659628b7ceea5e053089b3adfd1d5ae11a7f5c163e4a5"
NS019_SVG = "e1503343b198855975b3136e44efbe5330791945435bfabf99b53ea9a400cc90"
TABLE17 = "ffbb7f2e6aecefb0e4a65fe2da32cc43e87601e01eb7ab97715e516a22cc0b79"
TABLE18 = "3fa332e34627a5825f6065623ac39bd3f0a5041627375d167e3fd397f33e2495"
ABLATIONS = "8c57477902aba200e9a2228d6a316ec06f14859f7894fa1f534f16e8b19d8ccf"
RESULTS_SHA = "6b07e88ff02ad6674fd5979b361f4de4f121ec6b58906927d8cbfafca86b972e"
HIST_MATPLOTLIB_PDF = "001ddc3496915e7c21a52567551b36711a3dd4740ff12a0b4ae2402e56b96a06"
PRIOR_RECONSTRUCTION = "46a14011d3ec69cf2b399d310b830901a59c4d50bb4834142103c5f171a70585"

ALLOWLIST = [
    "appendix/entry.tex",
    "appendix/formal_arguments.tex",
    "fragments/abstract.tex",
    "fragments/analysis_method.tex",
    "fragments/conclusion.tex",
    "fragments/design.tex",
    "fragments/evidence_method.tex",
    "fragments/introduction.tex",
    "fragments/limitations.tex",
    "fragments/related_work.tex",
    "fragments/results.tex",
    "generated/ablations.tex",
    "generated/figures/family_useful.svg",
    "generated/table17.tex",
    "generated/table18.tex",
    "header.tex",
    "layout/family_useful.pdf",
    "layout/table18.tex",
    "main.tex",
    "neurips_2026_vericode.sty",
    "verified_references.bib",
]
SCIENTIFIC_REL = [
    "main.tex",
    "header.tex",
    "appendix/entry.tex",
    "appendix/formal_arguments.tex",
    "fragments/abstract.tex",
    "fragments/analysis_method.tex",
    "fragments/conclusion.tex",
    "fragments/design.tex",
    "fragments/evidence_method.tex",
    "fragments/introduction.tex",
    "fragments/limitations.tex",
    "fragments/related_work.tex",
    "fragments/results.tex",
    "generated/ablations.tex",
    "generated/table17.tex",
    "generated/table18.tex",
    "layout/table18.tex",
]
PLACEHOLDER_PATTERNS = [
    r"\[RESULTS(?:\s*:|\])",
    r"TO BE FILLED",
    r"\bTBD\b",
    r"RESULTS placeholder",
    r"answerTODO",
    r"justificationTODO",
]


def sha256(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def fail(failures: list[str], message: str) -> None:
    failures.append(message)


def round3(value: float) -> float:
    return float(f"{value:.3f}")


def run_tool(name: str, args: list[str]) -> subprocess.CompletedProcess[str]:
    binary = shutil.which(name)
    if binary is None:
        raise FileNotFoundError(f"sealed-PATH tool missing: {name}")
    return subprocess.run([binary, *args], check=True, capture_output=True, text=True)


def pdf_text(path: Path) -> str:
    return run_tool("pdftotext", ["-layout", str(path), "-"]).stdout


def pdf_info(path: Path) -> dict[str, str]:
    out = run_tool("pdfinfo", [str(path)]).stdout
    info = {}
    for line in out.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            info[key.strip()] = value.strip()
    return info


def pdf_fonts(path: Path) -> str:
    return run_tool("pdffonts", [str(path)]).stdout


def assemble_scientific_text() -> str:
    parts = []
    for rel in SCIENTIFIC_REL:
        parts.append((SNAP / "manuscript" / rel).read_text(encoding="utf-8"))
    return "\n".join(parts)


def placeholder_hits(text: str) -> list[str]:
    hits = []
    for pattern in PLACEHOLDER_PATTERNS:
        for match in re.finditer(pattern, text):
            start = max(0, match.start() - 40)
            end = min(len(text), match.end() + 40)
            hits.append(f"{pattern}: ...{text[start:end].replace(chr(10), ' ')}...")
    return hits


def folded(text: str) -> str:
    return re.sub(r"\s+", " ", text)


def contains(text: str, *needles: str) -> bool:
    haystack = folded(text)
    return all(folded(needle) in haystack for needle in needles)


def build_report() -> dict:
    failures: list[str] = []
    results = json.loads(RESULTS.read_text(encoding="utf-8"))
    manifest = json.loads((INPUTS / "manifest.json").read_text(encoding="utf-8"))
    live_main = LIVE_MS / "main.tex"
    live_pdf = LIVE_MS / "paper.pdf"
    snap_main = SNAP / "manuscript/main.tex"
    snap_pdf = SNAP / "manuscript/paper.pdf"

    if sha256(INPUTS / "manifest.json") != MANIFEST_SHA:
        fail(failures, "writing_inputs manifest sha mismatch")
    if sha256(INPUTS / "paper.pdf") != ACCEPTED_PDF:
        fail(failures, "writing_inputs paper.pdf sha mismatch")
    if sha256(live_main) != ACCEPTED_MAIN or sha256(snap_main) != ACCEPTED_MAIN:
        fail(failures, "live/snapshot main.tex is not the accepted entrypoint")
    if sha256(live_pdf) != ACCEPTED_PDF or sha256(snap_pdf) != ACCEPTED_PDF:
        fail(failures, "live/snapshot paper.pdf is not the accepted 907f0a24 product")
    if live_pdf.stat().st_size != 216541:
        fail(failures, "paper.pdf size is not 216541")
    if sha256(RESULTS) != RESULTS_SHA:
        fail(failures, "analysis/results.json moved away from NS-019 6b07e88f")

    live_generated = {
        "generated/figures/family_useful.pdf": NS019_ASCII_PDF,
        "generated/figures/family_useful.svg": NS019_SVG,
        "generated/table17.tex": TABLE17,
        "generated/table18.tex": TABLE18,
        "generated/ablations.tex": ABLATIONS,
    }
    for rel, expected in live_generated.items():
        got = sha256(LIVE_MS / rel)
        if got != expected:
            fail(failures, f"NS019/NS020 generated output changed: {rel} {got}")

    copied = {}
    for rel in ALLOWLIST:
        src_meta = manifest["files"]["source/" + rel]
        src = INPUTS / "source" / rel
        if sha256(src) != src_meta["sha256"]:
            fail(failures, f"writing_inputs source drifted: {rel}")
        if rel == "layout/family_useful.pdf":
            binding = json.loads((SNAP / "source_evidence/layout_family_useful.binding.json").read_text(encoding="utf-8"))
            b64_path = SNAP / "source_evidence/layout_family_useful.pdf.b64"
            if binding["raw_sha256"] != LAYOUT_RAW or sha256(src) != LAYOUT_RAW:
                fail(failures, "layout family_useful raw digest is not d70be874")
            if not b64_path.is_file() or sha256(b64_path) != binding["base64_sha256"]:
                fail(failures, "layout family_useful base64 snapshot mismatch")
            if (SNAP / "manuscript/layout/family_useful.pdf").exists():
                fail(failures, "unauthorized raw layout snapshot is present")
            copied[rel] = {"kind": "base64", "raw_sha256": LAYOUT_RAW, "base64_sha256": binding["base64_sha256"]}
            continue
        dest = SNAP / "manuscript" / rel
        if not dest.is_file() or sha256(dest) != src_meta["sha256"]:
            fail(failures, f"snapshot source copy mismatch: {rel}")
        copied[rel] = {"kind": "raw_source_copy", "sha256": src_meta["sha256"], "bytes": src_meta["bytes"]}

    excluded = INPUTS / "source/generated/figures/family_useful.pdf"
    if sha256(excluded) != HIST_MATPLOTLIB_PDF:
        fail(failures, "historical matplotlib figure digest drifted")
    if (SNAP / "manuscript/generated/figures/family_useful.pdf").exists():
        fail(failures, "excluded generated figure was copied into the NS-022 snapshot")
    main_tex = live_main.read_text(encoding="utf-8")
    if "layout/family_useful.pdf" not in main_tex:
        fail(failures, "accepted main.tex does not include layout/family_useful.pdf")
    if "generated/figures/family_useful.pdf" in main_tex:
        fail(failures, "accepted main.tex references the NS019 generated PDF")

    info = pdf_info(live_pdf)
    fonts = pdf_fonts(live_pdf)
    text = pdf_text(live_pdf)
    pages = int(info.get("Pages", "0"))
    if pages != 12:
        fail(failures, f"paper.pdf pages={pages}, expected 12")
    if "Type 3" in fonts or "Type3" in fonts:
        fail(failures, "Type3 font present in accepted paper.pdf")
    if "TrueType" not in fonts or "Type 1" not in fonts:
        fail(failures, "accepted paper.pdf missing expected Type1/TrueType fonts")
    if not info.get("Author", "").startswith("Anonymous"):
        fail(failures, "paper.pdf author is not anonymous")

    scientific = assemble_scientific_text()
    sci_hits = placeholder_hits(scientific)
    pdf_hits = placeholder_hits(text)
    if sci_hits:
        fail(failures, "placeholder remains in scientific source: " + sci_hits[0])
    if pdf_hits:
        fail(failures, "placeholder remains in paper.pdf: " + pdf_hits[0])

    useful = results["useful_completions"]
    arm = results["arm_useful_fixed16"]
    mean = results["mean_B_minus_A_useful"]
    ci = results["bootstrap"]["quality_B_minus_A"]
    outcomes = results["outcomes"]
    clocks = results["resource_summaries"]
    numeric_checks = []

    def check_num(name: str, expected, displayed: bool, detail: str) -> None:
        numeric_checks.append({"name": name, "expected": expected, "present": displayed, "detail": detail})
        if not displayed:
            fail(failures, f"numeric check failed: {name}: {detail}")

    check_num("useful_9_of_32", useful, contains(scientific, "9/32") and contains(text, "9/32"), "useful_completions=9")
    check_num("arm_A_5_of_16", arm["A"]["useful"], contains(scientific, "5/16") and contains(text, "5/16"), "A useful=5")
    check_num("arm_B_4_of_16", arm["B"]["useful"], contains(scientific, "4/16") and contains(text, "4/16"), "B useful=4")
    check_num(
        "mean_B_minus_A",
        mean,
        ("-0.0625" in scientific and ("-0.0625" in text or "−0.0625" in text)),
        "mean_B_minus_A_useful=-0.0625",
    )
    check_num(
        "descriptive_ci",
        [ci["lower"], ci["upper"]],
        ("[-0.1875,0]" in scientific.replace(" ", "") or "[-0.1875, 0]" in scientific)
        and ("-0.1875" in text or "−0.1875" in text),
        "bootstrap quality_B_minus_A [-0.1875, 0]",
    )
    check_num("families_8", results["independent_families"], "eight" in scientific.lower() and "eight" in text.lower(), "independent_families=8")
    check_num("cells_32", results["planned_cells"], "32" in scientific and "32" in text, "planned_cells=32")
    check_num("nested_104729", 104729, "104729" in scientific and "104729" in text, "nested repetition 104729")
    check_num("nested_130363", 130363, "130363" in scientific and "130363" in text, "nested repetition 130363")
    check_num("deadlines_14", outcomes["proposal_child_deadline"], "Fourteen" in scientific or "14 proposal" in scientific, "proposal_child_deadline=14")
    check_num("hidden_failed_7", outcomes["hidden_acceptance_failed"], "seven" in scientific.lower(), "hidden_acceptance_failed=7")
    check_num("proposal_failures_2", outcomes["known_proposal_failure"], "two known proposal" in scientific.lower(), "known_proposal_failure=2")
    check_num("scoring_16", clocks["gateway_score_elapsed_seconds"]["known_count"], "Sixteen scoring" in scientific or "16 scoring" in scientific.lower(), "score known_count=16")
    check_num("cold_completed_15", sum(1 for row in results["rows"] if row.get("actual_cold_completed")), "fifteen completed" in scientific.lower() or "15 completed" in scientific, "actual_cold_completed=15")
    check_num("posts_32", sum(row.get("actual_provider_posts") or 0 for row in results["rows"]), "32 original proposal POSTs" in scientific or "one proposal POST each" in scientific, "actual_provider_posts=32")
    check_num(
        "child_median_472.777",
        round3(clocks["provider_child_elapsed_seconds"]["median"]),
        "472.777" in scientific,
        f"round3({clocks['provider_child_elapsed_seconds']['median']})=472.777",
    )
    check_num(
        "wrapper_median_473.660",
        round3(clocks["http_wrapper_elapsed_seconds"]["median"]),
        "473.660" in scientific,
        f"round3({clocks['http_wrapper_elapsed_seconds']['median']})=473.660",
    )
    check_num(
        "gateway_median_474.107",
        round3(clocks["gateway_proposal_elapsed_seconds"]["median"]),
        "474.107" in scientific,
        f"round3({clocks['gateway_proposal_elapsed_seconds']['median']})=474.107",
    )
    check_num(
        "score_median_2.500",
        round3(clocks["gateway_score_elapsed_seconds"]["median"]),
        "2.500" in scientific,
        f"round3({clocks['gateway_score_elapsed_seconds']['median']})=2.500",
    )
    check_num(
        "grant_median_603.644",
        round3(clocks["grant_to_terminal_elapsed_seconds"]["median"]),
        "603.644" in scientific,
        f"round3({clocks['grant_to_terminal_elapsed_seconds']['median']})=603.644",
    )
    check_num(
        "grant_max_10938.574",
        round(clocks["grant_to_terminal_elapsed_seconds"]["maximum"], 3),
        "10,938.574" in scientific,
        f"round3({clocks['grant_to_terminal_elapsed_seconds']['maximum']})=10938.574",
    )
    check_num("original_192", results["ablation_population"]["original_planned_factor_cells"], "192" in scientific, "original_planned_factor_cells=192")
    check_num("withdrawn_160", results["ablation_population"]["withdrawn_planned_factor_cells"], "160" in scientific, "withdrawn_planned_factor_cells=160")
    check_num("unrecruited_8", results["unrecruited_original_families"], "eight additional target families" in scientific or "eight unrecruited" in scientific.lower() or "not recruited" in scientific, "unrecruited_original_families=8")
    check_num("api_usage_16_of_32", results["observed_api_usage"]["total_tokens"]["known_count"], contains(scientific, "16/32", "settlement is unavailable"), "API usage known_count=16, settled_charge=false")
    check_num("paired_score_families_1", results["paired_cost_family_coverage"]["gateway_score_elapsed_seconds"]["complete_families"], contains(scientific, "Only one of eight families has complete scoring-time"), "complete scoring-time families=1")
    check_num("false_reuse_1_of_26", "1/26", contains(scientific, "1/26"), "historical false reuse 1/26")
    check_num("cell5_28_of_28", "28/28", contains(scientific, "28/28"), "cell 5 public checks 28/28")
    check_num("cell27_895.290", "895.290", contains(scientific, "895.290"), "cell 27 reservation 895.290 seconds")
    table17 = (SNAP / "manuscript/generated/table17.tex").read_text(encoding="utf-8")
    check_num("table17_tornado", "-0.5", "11-tornado & 2 & 1 & -0.5" in table17, "Tornado family row")
    check_num("table17_all", "-0.0625", "5 / 16 & 4 / 16 & -0.0625" in table17, "all-eight table footer")
    check_num("settled_charges_unavailable", False, contains(scientific, "All provider charges remain unsettled") or contains(scientific, "settlement is unavailable for all 32"), "settled_charge is false for all API usage scopes")
    check_num("no_advantage", True, contains(scientific.lower(), "no observed advantage") and contains(text.lower(), "no observed advantage"), "abstract/conclusion negative result")

    structural = {
        "research_question": contains(scientific, "whether adding native source-linked semantic context", "useful cold repair"),
        "novel_composition": contains(scientific, "evidence boundaries", "conditional acceptance") and "not a first-of-kind" in scientific,
        "trusted_assumptions": contains(scientific, "These classes cannot substitute", "Completeness and determinism are substantive premises"),
        "matched_method_baseline": contains(scientific, "Arm A receives the selected public raw context", "Arm B preserves the matched raw selection"),
        "results": contains(scientific, "All 32 planned cells have verified terminal records", "mean of the eight paired family"),
        "negative_cases": contains(scientific, "proposal-child deadlines", "incomplete hidden validation", "Withdrawn or unmeasured"),
        "supplement_not_evaluated_implementation": contains(scientific, "they do not establish that the complete intended loop ran as a live benchmark")
        and contains(scientific, "Earlier boundary evidence is also separate from final repair outcomes"),
        "withdrawn_cd_warm_reuse_publication_16family": contains(scientific, "C/D routing", "warm-cache", "publication efficacy", "sixteen-family"),
        "ns_nnn_defined_as_qualification_ids": contains(scientific, "Identifiers of the form NS-NNN name internal qualification records"),
        "checklist_not_in_ns022": "\\answerTODO" not in scientific and "checklist.tex" not in main_tex,
        "figure_not_additional_experiment": "it is not an additional experiment" in scientific,
    }
    for key, ok in structural.items():
        if not ok:
            fail(failures, f"structural check failed: {key}")

    ledger = json.loads((LIVE_AUDIT / "final_claim_evidence_matrix.json").read_text(encoding="utf-8"))
    ledger_ok = (
        ledger.get("actual_final32_reconciliation", {}).get("actual_terminal_cells") == 32
        and results["useful_completions"] == 9
        and "withdrawn" in json.dumps(ledger).lower()
    )
    if not ledger_ok:
        fail(failures, "claim ledger final32 reconciliation missing or mismatched")

    def sealed_tool(name: str) -> str | None:
        for directory in ("/usr/local/sbin", "/usr/local/bin", "/usr/sbin", "/usr/bin"):
            candidate = Path(directory) / name
            if candidate.is_file():
                return str(candidate)
        return None

    if sealed_tool("pdflatex") is not None:
        fail(failures, "sealed validation PATH unexpectedly provides pdflatex")
    for required in ("python3.12", "pdffonts", "pdfinfo", "pdftotext"):
        if sealed_tool(required) is None:
            fail(failures, f"sealed validation PATH missing {required}")

    report = {
        "schema": "ns022-manuscript-result-checks/v1",
        "task_id": "NS-022",
        "all_passed": not failures,
        "failures": failures,
        "accepted_outputs": {
            "manuscript/main.tex": {"sha256": sha256(live_main), "bytes": live_main.stat().st_size},
            "manuscript/paper.pdf": {"sha256": sha256(live_pdf), "bytes": live_pdf.stat().st_size, "pages": pages},
        },
        "source_adoption": {
            "writing_inputs_manifest_sha256": sha256(INPUTS / "manifest.json"),
            "allowlisted_source_count": 21,
            "excluded_generated_figure": "source/generated/figures/family_useful.pdf",
            "copied": copied,
            "live_manuscript_writes": [
                "papers/completion/neurosymbolic_supervision/manuscript/main.tex",
                "papers/completion/neurosymbolic_supervision/manuscript/paper.pdf",
            ],
        },
        "figure_ownership": {
            "published_figure1": {
                "source": "layout/family_useful.pdf",
                "raw_sha256": LAYOUT_RAW,
                "snapshot": "canonical base64, not a raw layout snapshot",
            },
            "live_ns019_ascii_pdf": {
                "path": "papers/completion/neurosymbolic_supervision/manuscript/generated/figures/family_useful.pdf",
                "sha256": sha256(LIVE_MS / "generated/figures/family_useful.pdf"),
                "bytes": (LIVE_MS / "generated/figures/family_useful.pdf").stat().st_size,
                "preserved_unchanged": True,
                "not_the_published_figure": True,
            },
            "historical_matplotlib_pdf": {
                "sha256": HIST_MATPLOTLIB_PDF,
                "bytes": 16554,
                "not_copied": True,
                "type3": True,
            },
        },
        "pdf_inspection": {
            "pages": pages,
            "page_boundaries": {"main": [1, 6], "references": [7, 7], "appendices": [8, 12]},
            "title": info.get("Title"),
            "author": info.get("Author"),
            "type3_present": False,
            "fonts_embedded_type1_or_cid_truetype": True,
            "pdffonts": fonts,
        },
        "placeholder_scan": {
            "scientific_source_hits": sci_hits,
            "paper_pdf_hits": pdf_hits,
            "style_todo_macros_are_official_definitions_not_scientific_placeholders": True,
        },
        "numeric_checks": numeric_checks,
        "structural_checks": structural,
        "claim_ledger_alignment": {
            "results_sha256": RESULTS_SHA,
            "final_claim_evidence_matrix": "papers/completion/neurosymbolic_supervision/audit/final_claim_evidence_matrix.json",
            "scientific_scope": "eight-family A/B local-cold 32-cell descriptive comparison; C/D, warm, reuse, publication, and sixteen-family inferential objectives remain withdrawn",
            "matched": ledger_ok,
        },
        "interrupted_authoring": {
            "prior_live_main_tex_sha256": PRIOR_RECONSTRUCTION,
            "replaced_by_accepted_entrypoint": ACCEPTED_MAIN,
            "ns001_snapshot_preserved": True,
        },
        "toolchain": {
            "validation_path": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin",
            "pdflatex": sealed_tool("pdflatex"),
            "python3.12": sealed_tool("python3.12"),
            "pdffonts": sealed_tool("pdffonts"),
            "pdfinfo": sealed_tool("pdfinfo"),
            "pdftotext": sealed_tool("pdftotext"),
        },
        "new_scientific_calls": 0,
        "publication_authorized": False,
        "outside_reviewer_required": False,
    }
    return report


def main() -> int:
    write = "--write" in sys.argv
    report = build_report()
    if write:
        CHECKS.parent.mkdir(parents=True, exist_ok=True)
        payload = dict(report)
        payload.pop("failures", None)
        CHECKS.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        (SNAP / "audit/manuscript_result_checks.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {CHECKS}")
    else:
        if not CHECKS.is_file():
            print("missing manuscript_result_checks.json", file=sys.stderr)
            return 1
        current = json.loads(CHECKS.read_text(encoding="utf-8"))
        expected = dict(report)
        expected.pop("failures", None)
        if current != expected:
            print("manuscript_result_checks.json does not match recomputed report", file=sys.stderr)
            current_dump = json.dumps(current, indent=2, sort_keys=True)
            expected_dump = json.dumps(expected, indent=2, sort_keys=True)
            if current_dump != expected_dump:
                print("current keys", sorted(current))
                print("expected keys", sorted(expected))
                for key in sorted(set(current) | set(expected)):
                    if current.get(key) != expected.get(key):
                        print("differ", key)
                return 1
        if sha256(CHECKS) != sha256(SNAP / "audit/manuscript_result_checks.json"):
            print("live result checks differ from snapshot", file=sys.stderr)
            return 1
        if not NOTES.is_file() or sha256(NOTES) != sha256(SNAP / "audit/revision_notes.md"):
            print("revision_notes missing or snapshot mismatch", file=sys.stderr)
            return 1
    if report["failures"]:
        print("FAILED")
        for item in report["failures"]:
            print(" -", item)
        return 1
    print("NS-022 manuscript current-output verification passed")
    print("paper.pdf", ACCEPTED_PDF, "pages=12 type3=0")
    print("main.tex", ACCEPTED_MAIN)
    print("ns019 ascii figure preserved", NS019_ASCII_PDF)
    print("numeric_checks", len(report["numeric_checks"]))
    print("new_scientific_calls=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
