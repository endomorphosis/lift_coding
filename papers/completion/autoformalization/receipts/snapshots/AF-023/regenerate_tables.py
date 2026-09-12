#!/usr/bin/env python3
"""Regenerate reported Tables 6, 11, and 13 from frozen retained-claim records.

Works from the anonymous supplement ZIP or from the paper tree. Stdlib only.
Does not train models, call providers, open final-test bodies, or invent
confidence intervals.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

EXPECTED = {
    "table6_pipeline.tex": "a2ebba34895da30b383954e93ec582d2738a212d15de7b329fecf5a4d0c7aa49",
    "table11_training.tex": "dcb2582f2c091a48b3c26bb1b1698e1287d70d77cc2c3824b4f1f822bd2d6e74",
    "table13_assistance.tex": "655dfb58c0c1a960b636dbe35292ee243fbcb197fad1108f8a047742e2f62d3f",
    "summary.json": "62e63725fe02f4ac9f9c5a3b397d0b2d9f9d7a1e25fc87e9eb7fdc21cb01cc72",
}
PIPELINE_ARMS = ("A", "B", "C", "D", "E")
TRAINING_ARMS = ("T0", "T1", "T2", "T3", "T4", "T5")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def latex_escape(text: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(ch, ch) for ch in text)


def find_bundle(start: Path) -> tuple[Path, Path]:
    for path in (start.resolve(), *start.resolve().parents):
        frozen = path / "frozen" / "results" / "summary.json"
        if frozen.is_file():
            return path, path / "frozen"
        paper = path / "papers" / "completion" / "autoformalization" / "results" / "summary.json"
        if paper.is_file():
            return path, path / "papers" / "completion" / "autoformalization"
    raise SystemExit("cannot locate frozen retained-claim inputs or paper results")


def render_table6(cells: Sequence[Mapping[str, Any]]) -> str:
    by_arm = {arm: {} for arm in PIPELINE_ARMS}
    for item in cells:
        by_arm[item["arm"]][item["column"]] = item
    lines = [
        "% AF-021 regenerated Table 6. All 20 original placeholder cells replaced.",
        "% Population: final_test.natural_source_units = 1913. Unrun/unavailable are not measured zeros.",
        "% Independent source-semantic fidelity is unmeasured and is not prover or teacher agreement.",
        "\\begin{table}[t]",
        "\\centering",
        "\\small",
        "\\caption{Matched A--E pipeline comparison on the locked 1913-unit final-test population. "
        "Unrun and unavailable are not measured zeros. Independent source-semantic fidelity is unmeasured.}",
        "\\label{tab:pipeline-results}",
        "\\resizebox{\\linewidth}{!}{%",
        "\\begin{tabular}{lp{0.22\\linewidth}p{0.24\\linewidth}p{0.24\\linewidth}p{0.22\\linewidth}}",
        "\\hline",
        "Arm & Coverage / abstention & Independent fidelity / uncertainty & "
        "Native-checked useful proof / transfer & Total cost / latency \\\\",
        "\\hline",
    ]
    for arm in PIPELINE_ARMS:
        row = by_arm[arm]
        lines.append(
            f"{arm} & {latex_escape(row['sources_covered']['display'])} & "
            f"{latex_escape(row['fidelity_uncertainty']['display'])} & "
            f"{latex_escape(row['correct_transfers']['display'])} & "
            f"{latex_escape(row['cost_latency']['display'])} \\\\"
        )
    lines.extend(["\\hline", "\\end{tabular}}", "\\end{table}", ""])
    text = "\n".join(lines)
    if "TBD" in text:
        raise SystemExit("Table 6 still contains TBD")
    return text


def render_table11(cells: Sequence[Mapping[str, Any]]) -> str:
    by_arm = {arm: {} for arm in TRAINING_ARMS}
    for item in cells:
        by_arm[item["arm"]][item["column"]] = item
    lines = [
        "% AF-021 regenerated Table 11. All 24 original placeholder cells replaced.",
        "% Held-out fidelity remains unmeasured. Teacher cosine/reconstruction do not fill that column.",
        "\\begin{table}[t]",
        "\\centering",
        "\\small",
        "\\caption{T0--T5 learning comparisons. Split counts are frozen inventory. Held-out independent "
        "fidelity is unmeasured. Proof/route benefit and final-test cost remain unrun or unavailable.}",
        "\\label{tab:training-results}",
        "\\resizebox{\\linewidth}{!}{%",
        "\\begin{tabular}{lp{0.22\\linewidth}p{0.24\\linewidth}p{0.24\\linewidth}p{0.22\\linewidth}}",
        "\\hline",
        "Arm & Source/split counts & Held-out fidelity & Proof/route benefit & Total cost \\\\",
        "\\hline",
    ]
    for arm in TRAINING_ARMS:
        row = by_arm[arm]
        lines.append(
            f"{arm} & {latex_escape(row['source_split_counts']['display'])} & "
            f"{latex_escape(row['held_out_fidelity']['display'])} & "
            f"{latex_escape(row['proof_route_benefit']['display'])} & "
            f"{latex_escape(row['total_cost']['display'])} \\\\"
        )
    lines.extend(["\\hline", "\\end{tabular}}", "\\end{table}", ""])
    text = "\n".join(lines)
    if "TBD" in text:
        raise SystemExit("Table 11 still contains TBD")
    return text


def render_table13(rows: Sequence[Mapping[str, Any]]) -> str:
    lines = [
        "% AF-021 regenerated Table 13. Constructed/automatic-label diagnostics are labeled as such.",
        "% Natural held-out Table 13 cells remain unrun or unavailable.",
        "\\begin{table}[t]",
        "\\centering",
        "\\small",
        "\\caption{Retrieval, planning, and proof-assistance comparisons. Constructed automatic-label "
        "diagnostics do not fill natural held-out cells. Unavailable native checkers are not measured zeros.}",
        "\\label{tab:assistance-results}",
        "\\resizebox{\\linewidth}{!}{%",
        "\\begin{tabular}{p{0.18\\linewidth}p{0.22\\linewidth}p{0.22\\linewidth}p{0.32\\linewidth}}",
        "\\hline",
        "Comparison & Controlled variable & Required outcome & Audited result / status \\\\",
        "\\hline",
    ]
    for row in rows:
        lines.append(
            f"{latex_escape(row['comparison'])} & {latex_escape(row['controlled_variable'])} & "
            f"{latex_escape(row['required_outcome'])} & {latex_escape(row['display'])} \\\\"
        )
    lines.extend(["\\hline", "\\end{tabular}}", "\\end{table}", ""])
    text = "\n".join(lines)
    if "TBD" in text:
        raise SystemExit("Table 13 still contains TBD")
    return text


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Verify regenerated tables against frozen hashes")
    parser.add_argument("--write-dir", type=Path, help="Optional directory to write regenerated TeX")
    args = parser.parse_args(argv)
    _, bundle = find_bundle(Path(__file__).resolve().parent)
    summary_path = bundle / "results" / "summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary_digest = sha256_bytes(summary_path.read_bytes())
    if summary_digest != EXPECTED["summary.json"]:
        raise SystemExit(f"summary.json digest drifted: {summary_digest}")
    table6 = render_table6(summary["table6"]["cells"])
    table11 = render_table11(summary["table11"]["cells"])
    table13 = render_table13(summary["table13"]["rows"])
    generated = {
        "table6_pipeline.tex": table6,
        "table11_training.tex": table11,
        "table13_assistance.tex": table13,
    }
    report = {
        "ok": True,
        "summary_sha256": summary_digest,
        "tables": {},
        "unrun_is_not_zero": True,
        "independent_fidelity_unmeasured": True,
        "public_upload": False,
        "fabricated_human_review": False,
    }
    errors: list[str] = []
    for name, text in generated.items():
        digest = sha256_bytes(text.encode("utf-8"))
        frozen = bundle / "results" / name
        if frozen.is_file() and frozen.read_text(encoding="utf-8") != text:
            errors.append(f"{name} regenerated text differs from frozen copy")
        if digest != EXPECTED[name]:
            errors.append(f"{name} digest {digest} != {EXPECTED[name]}")
        report["tables"][name] = {"sha256": digest, "bytes": len(text.encode("utf-8"))}
        if args.write_dir:
            args.write_dir.mkdir(parents=True, exist_ok=True)
            (args.write_dir / name).write_text(text, encoding="utf-8")
    if errors:
        report["ok"] = False
        report["errors"] = errors
        print(json.dumps(report, indent=2, sort_keys=True))
        return 1
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
