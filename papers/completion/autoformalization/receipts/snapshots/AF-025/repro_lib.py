#!/usr/bin/env python3
"""Shared AF-025 reproduction helpers. Standard library only."""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import zipfile
import zlib
from pathlib import Path
from typing import Any

SEALED_PATH = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin"
PYTHON = "/usr/bin/python3.12"
ZIP_ROOT = "autoformalization-anonymous-reproducibility"
EXPECTED_TABLES = {
    "table6_pipeline.tex": "a2ebba34895da30b383954e93ec582d2738a212d15de7b329fecf5a4d0c7aa49",
    "table11_training.tex": "dcb2582f2c091a48b3c26bb1b1698e1287d70d77cc2c3824b4f1f822bd2d6e74",
    "table13_assistance.tex": "655dfb58c0c1a960b636dbe35292ee243fbcb197fad1108f8a047742e2f62d3f",
    "summary.json": "62e63725fe02f4ac9f9c5a3b397d0b2d9f9d7a1e25fc87e9eb7fdc21cb01cc72",
}
OFFICIAL_TEMPLATES = {
    "papers/neurips_2026_vericode_workshop.tex": "c1c74133705d906972ee7571ee34f57122da5088e9f09ffe9dacb01cf0db1250",
    "papers/neurips_2026_vericode.sty": "2944ec0d4f64dba353827e9ead104da1a9ac81b4057f4ff40969c693632a1e11",
    "papers/checklist.tex": "780ba13c480f652dcc42e69ed61a752ce0ea270f15d332d4a45b059dabad84f6",
}
CHECKER_TOOLS = (
    "lean", "lake", "elan", "z3", "cvc5", "vampire", "eprover", "coqc", "isabelle",
)
ANALYSIS_ID = "392407da2432633405e512e2e0b17e960ed89c2a3552f4a09959e73125fc4c43"
SCOPE_POLICY_ID = "AF-028/structural-evidence-scope/v1"
SCOPE_SHA256 = "6373506c21a276388ef3ebf582d48d01a7aa5cc114ca414c0ca07a23f4f8ceea"
HEADINGS = (
    "Claims", "Limitations", "Theory assumptions and proofs",
    "Experimental result reproducibility", "Open access to data and code",
    "Experimental setting/details", "Experiment statistical significance",
    "Experiments compute resources", "Code of ethics", "Broader impacts",
    "Safeguards", "Licenses for existing assets", "New assets",
    "Crowdsourcing and research with human subjects",
    "Institutional review board (IRB) approvals or equivalent for research with human subjects",
    "Declaration of LLM usage",
)
IDENTIFYING = re.compile(
    r"(?i)(\bbarberb\b|lift_coding|/home/[A-Za-z0-9._-]+|/Users/[A-Za-z0-9._-]+|"
    r"overleaf\.com|BEGIN [A-Z ]*PRIVATE|x-api-key|Authorization:\s*Bearer|"
    r"sk-[A-Za-z0-9]{16,}|grok_cli_auth)"
)
PLACEHOLDER = re.compile(
    r"\[TBD\]|\[TODO\]|\[To complete|\\answerTODO|\\justificationTODO|To be completed",
    re.I,
)
PUBLICATION_NEEDLES = (
    "uploaded to arxiv",
    "submitted to openreview",
    "workshop submission completed",
    "authors approved",
    "paper was published",
    "paper was submitted",
)
REVIEW_NEEDLES = (
    "independent annotators agreed",
    "kappa =",
    "inter-annotator agreement of",
    "human review collected",
)
CLAIM_LEDGER_NEEDLES = (
    "independent human source-facet",
    "1913",
    "sample-memory diagnostic",
    "sealed-PATH",
)
FORBIDDEN_INVENTIONS = (
    "held-out source-fidelity percentage",
    "T4 applied learned-feature guidance",
    "Arm E promoted",
    "CUDA training speedup",
)


def find_repo_root(start: Path) -> Path:
    marker = Path("papers/completion/autoformalization/config/environment_manifest.json")
    for path in (start, *start.parents):
        if (path / marker).is_file():
            return path
    raise SystemExit("cannot locate repository root")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def dumps(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def file_identity(repo: Path, rel: str, role: str) -> dict[str, Any]:
    path = repo / rel
    data = path.read_bytes()
    return {
        "path": rel,
        "sha256": sha256_bytes(data),
        "bytes": len(data),
        "role": role,
        "present": True,
    }


def probe_checkers() -> dict[str, Any]:
    rows = []
    for name in CHECKER_TOOLS:
        resolved = shutil.which(name)
        rows.append({
            "name": name,
            "resolved_path": resolved,
            "status": "available" if resolved else "unavailable",
            "usable_in_sealed_validation": bool(resolved),
        })
    any_usable = any(row["usable_in_sealed_validation"] for row in rows)
    return {
        "path": SEALED_PATH,
        "tools": rows,
        "any_usable": any_usable,
        "missing": [row["name"] for row in rows if not row["usable_in_sealed_validation"]],
        "note": "Host operator toolchains are out of sealed-PATH scope.",
    }


def pdf_text(data: bytes) -> str:
    chunks = []
    for match in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", data, re.S):
        payload = match.group(1)
        try:
            payload = zlib.decompress(payload)
        except zlib.error:
            pass
        chunks.append(payload)
    blob = b"\n".join(chunks)
    strings = []
    for raw in re.findall(rb"\((?:\\.|[^\\)])+\)", blob):
        inner = raw[1:-1]
        inner = re.sub(rb"\\([0-7]{3})", lambda m: bytes([int(m.group(1), 8)]), inner)
        inner = inner.replace(b"\\(", b"(").replace(b"\\)", b")").replace(b"\\\\", b"\\")
        strings.append(inner.decode("latin-1", errors="replace"))
    text = " ".join(strings)
    for src, dst in (("\x02", "ff"), ("\x03", "fi"), ("\x04", "fl"), ("\x05", "ffi"), ("\x06", "ffl")):
        text = text.replace(src, dst)
    return text


def placeholder_hits(text: str) -> list[str]:
    hits = []
    for match in PLACEHOLDER.finditer(text):
        snippet = match.group(0)
        context = text[max(0, match.start() - 24): match.end() + 24]
        if re.search(r"Affiliation|Address|email", context, re.I):
            continue
        hits.append(snippet)
    return hits


def publication_hits(text: str) -> list[str]:
    lower = text.lower()
    found = []
    for needle in PUBLICATION_NEEDLES:
        if needle in lower:
            found.append(needle)
    return found


def review_fabrication_hits(text: str) -> list[str]:
    lower = text.lower()
    found = []
    for needle in REVIEW_NEEDLES:
        if needle in lower and "not collected" not in lower:
            found.append(needle)
    return found


def identifying_hits(text: str) -> list[str]:
    return [match.group(0)[:80] for match in IDENTIFYING.finditer(text)]


def table_status_inventory(summary: dict[str, Any]) -> dict[str, Any]:
    def count(items: list[dict[str, Any]]) -> dict[str, int]:
        tallies: dict[str, int] = {}
        for item in items:
            status = str(item.get("status") or "unknown")
            tallies[status] = tallies.get(status, 0) + 1
        return tallies

    table6 = summary.get("table6", {}).get("cells") or []
    table11 = summary.get("table11", {}).get("cells") or []
    table13 = summary.get("table13", {}).get("rows") or []
    return {
        "table6": {"cell_count": len(table6), "statuses": count(table6)},
        "table11": {"cell_count": len(table11), "statuses": count(table11)},
        "table13": {"row_count": len(table13), "statuses": count(table13)},
        "hypothesis_status_counts": summary.get("hypothesis_status_counts"),
        "final_test_denominator": (summary.get("denominators") or {}).get("table6_final_test"),
        "af029_claim_admissible": (summary.get("af029") or {}).get("claim_admissible"),
        "t2_update_counts": ((summary.get("training_aggregates") or {}).get("T2") or {}).get("update_counts"),
        "arm_E_activated": (summary.get("missingness") or {}).get("arm_E_activated"),
        "t4_activated": (summary.get("missingness") or {}).get("t4_activated"),
        "independent_gold_present": (summary.get("missingness") or {}).get("independent_gold_present"),
        "gold_records_with_values": (summary.get("raw_counts") or {}).get("gold_records_with_values"),
    }


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def inspect_native_checker_receipts(paper: Path) -> dict[str, Any]:
    sealed = load_jsonl(paper / "evidence" / "native_checker_receipts.jsonl")
    development = load_jsonl(paper / "evidence" / "runtime_qualification" / "native_checker_receipts.jsonl")
    sealed_summary = next((row for row in sealed if row.get("kind") == "summary"), {})
    accepted = [row for row in sealed if row.get("accepted") is True]
    native_credit = [row for row in sealed if row.get("counts_as_native_checked_proof") is True]
    dev_kinds = sorted({row.get("purpose") or row.get("result_kind") for row in development})
    return {
        "sealed_path_receipts": {
            "path": "papers/completion/autoformalization/evidence/native_checker_receipts.jsonl",
            "sha256": sha256_file(paper / "evidence" / "native_checker_receipts.jsonl"),
            "n_rows": len(sealed),
            "accepted_true": len(accepted),
            "native_checked_proof_credit": len(native_credit),
            "summary_accepted_proofs": sealed_summary.get("accepted_proofs"),
            "summary_any_usable": sealed_summary.get("any_native_checker_usable"),
            "missing_tools": sealed_summary.get("missing_tools"),
            "policy_rejections": sealed_summary.get("policy_rejections"),
        },
        "development_runtime_receipts": {
            "path": "papers/completion/autoformalization/evidence/runtime_qualification/native_checker_receipts.jsonl",
            "sha256": sha256_file(paper / "evidence" / "runtime_qualification" / "native_checker_receipts.jsonl"),
            "n_rows": len(development),
            "purposes": dev_kinds,
            "table6_credit": False,
            "sealed_path_replayable": False,
            "note": "AF-027 development Lean/Z3 receipts used operator-local research-runtime binaries absent from sealed PATH. They remain development evidence and do not fill Table 6.",
        },
    }


def inspect_example_receipts(paper: Path) -> dict[str, Any]:
    reference = load_json(paper / "evaluation" / "reference_results.json")
    checks = reference.get("checks") or []
    matches = [item.get("match") is True for item in checks]
    translations = load_jsonl(paper / "evidence" / "translation_receipts.jsonl")
    q1 = [row for row in translations if row.get("source_formula_root") == "Q1"]
    q2 = [row for row in translations if row.get("source_formula_root") == "Q2"]
    native_lean_q1 = [row for row in q1 if (row.get("checker_environment") or {}).get("native") is True]
    return {
        "finite_semantic_checks": {
            "path": "papers/completion/autoformalization/evaluation/reference_results.json",
            "sha256": sha256_file(paper / "evaluation" / "reference_results.json"),
            "n_checks": len(checks),
            "all_match_declared_expected": all(matches) and len(matches) == 12,
        },
        "policy_code_trace": {
            "path": "papers/completion/autoformalization/evidence/translation_receipts.jsonl",
            "sha256": sha256_file(paper / "evidence" / "translation_receipts.jsonl"),
            "n_rows": len(translations),
            "q1_rows": len(q1),
            "q2_rows": len(q2),
            "native_lean_q1": len(native_lean_q1),
            "machine_checked_compiler_soundness": any(
                row.get("machine_checked_compiler_soundness") for row in translations
            ),
            "note": "Guarded Boolean Q1 holds; unguarded always-write is a countermodel. Native Lean Q1 is unavailable. Zero observed false transfers is not universal soundness.",
        },
    }


def inspect_pdf_and_supplement(repo: Path, paper: Path) -> dict[str, Any]:
    pdf_path = paper / "submission" / "paper.pdf"
    zip_path = paper / "submission" / "supplement.zip"
    tex = (paper / "manuscript" / "main.tex").read_text(encoding="utf-8")
    checklist = (paper / "manuscript" / "checklist.tex").read_text(encoding="utf-8")
    disclosure = (paper / "manuscript" / "llm_disclosure.tex").read_text(encoding="utf-8")
    pdf = pdf_path.read_bytes()
    extracted = pdf_text(pdf)
    format_check = load_json(paper / "evidence" / "format_check.json")
    audit = load_json(paper / "evidence" / "final_claim_audit.json")
    answers = re.findall(r"\\item\[\] Answer: \\answer(Yes|No|NA)\{\}", checklist)
    style_sha = sha256_file(paper / "manuscript" / "neurips_2026_vericode.sty")
    template_status = {}
    for rel, digest in OFFICIAL_TEMPLATES.items():
        actual = sha256_file(repo / rel)
        template_status[rel] = {"expected": digest, "actual": actual, "match": actual == digest}
    scientific = placeholder_hits(tex) + placeholder_hits(checklist) + placeholder_hits(extracted)
    members = []
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        members = names
        required = [
            f"{ZIP_ROOT}/README.md",
            f"{ZIP_ROOT}/manifest.json",
            f"{ZIP_ROOT}/checksums.json",
            f"{ZIP_ROOT}/regenerate_tables.py",
            f"{ZIP_ROOT}/verify_retained_inputs.py",
            f"{ZIP_ROOT}/frozen/results/summary.json",
            f"{ZIP_ROOT}/frozen/results/table6_pipeline.tex",
            f"{ZIP_ROOT}/frozen/results/table11_training.tex",
            f"{ZIP_ROOT}/frozen/results/table13_assistance.tex",
            f"{ZIP_ROOT}/frozen/evidence/final_claim_audit.json",
        ]
        missing_members = [name for name in required if name not in names]
    claim_statuses = {}
    for claim in audit.get("claims") or []:
        claim_statuses[claim["id"]] = claim.get("status")
    footer = "Submitted to NeurIPS 2026 Workshop on AI for Verifiable Coding"
    return {
        "pdf": {
            "path": "papers/completion/autoformalization/submission/paper.pdf",
            "sha256": sha256_bytes(pdf),
            "bytes": len(pdf),
            "author": (format_check.get("pdf") or {}).get("metadata", {}).get("Author"),
            "workshop_footer_present": footer in extracted or format_check.get("style", {}).get("workshop_footer_present") is True,
            "anonymous_block_retained": format_check.get("style", {}).get("official_anonymous_block_retained") is True,
            "review_line_numbers_present": format_check.get("style", {}).get("review_line_numbers_present") is True,
            "main_text_pages": (format_check.get("page_accounting") or {}).get("main_text_pages_excluding_refs_appendices"),
            "scientific_placeholders": scientific,
            "publication_hits": publication_hits(extracted) + publication_hits(tex),
            "identifying_hits": identifying_hits(extracted),
        },
        "checklist": {
            "answers": answers,
            "n_answers": len(answers),
            "guidelines_blocks": checklist.count("Guidelines:"),
            "instruction_block_removed": "BEGIN INSTRUCTIONS" not in checklist,
            "todo_fields": r"\answerTODO" in checklist or r"\justificationTODO" in checklist,
        },
        "disclosure": {
            "grok_46": "grok-4.6" in disclosure and "2026-09-12" in disclosure,
            "minilm": "1110a243fdf4706b3f48f1d95db1a4f5529b4d41" in disclosure,
            "codex_unused": "gpt-5.6-terra" in disclosure and "not invoked" in disclosure,
            "author_verification_not_claimed": "author verification" in disclosure.lower(),
        },
        "templates": template_status,
        "style_sha256": style_sha,
        "style_matches_official": style_sha == OFFICIAL_TEMPLATES["papers/neurips_2026_vericode.sty"],
        "supplement": {
            "path": "papers/completion/autoformalization/submission/supplement.zip",
            "sha256": sha256_file(zip_path),
            "bytes": zip_path.stat().st_size,
            "member_count": len(members),
            "missing_required_members": missing_members,
        },
        "claim_ledger": {
            "path": "papers/completion/autoformalization/evidence/final_claim_audit.json",
            "sha256": sha256_file(paper / "evidence" / "final_claim_audit.json"),
            "n_claims": len(audit.get("claims") or []),
            "statuses": claim_statuses,
            "analysis_id": audit.get("analysis_id"),
            "human_fidelity_unmeasured": (audit.get("scope_policy") or {}).get("human_fidelity_status") == "unmeasured_not_collected",
            "optional_author_feedback_supplied": (audit.get("scope_policy") or {}).get("optional_author_feedback_supplied") is True,
        },
        "format_check_ok": format_check.get("ok") is True,
        "latex_is_not_empirical_validation": True,
    }


def resolve_claim_source(repo: Path, paper: Path, src: str) -> Path:
    if src.startswith("papers/"):
        return repo / src
    return paper / src


def claim_evidence_complete(repo: Path, paper: Path, audit: dict[str, Any]) -> dict[str, Any]:
    missing = []
    retained = []
    omitted = []
    omitted_statuses = {"unmeasured", "unrun", "unavailable", "inconclusive"}
    omitted_kinds = {"unmeasured_limitation", "related_work", "limitation"}
    for claim in audit.get("claims") or []:
        sources = []
        for src in claim.get("source") or []:
            full = resolve_claim_source(repo, paper, src)
            ok = full.is_file()
            sources.append({"path": src, "present": ok, "sha256": sha256_file(full) if ok else None})
            if not ok:
                missing.append({"claim": claim["id"], "path": src})
        entry = {
            "id": claim["id"],
            "status": claim.get("status"),
            "kind": claim.get("kind"),
            "claim_admissible_for_paper_primary": claim.get("claim_admissible_for_paper_primary"),
            "sources": sources,
        }
        if claim.get("status") in omitted_statuses or claim.get("kind") in omitted_kinds:
            omitted.append(entry)
        else:
            retained.append(entry)
    summary = load_json(paper / "results" / "summary.json")
    training_hidden = (
        (summary.get("af029") or {}).get("claim_admissible") is not False
        or ((summary.get("training_aggregates") or {}).get("T2") or {}).get("update_counts") != [0]
        or (summary.get("missingness") or {}).get("t4_activated") is True
        or (summary.get("missingness") or {}).get("arm_E_activated") is True
    )
    return {
        "retained_automated_claims": retained,
        "omitted_or_unmeasured_claims": omitted,
        "missing_source_files": missing,
        "unfinished_training_hidden_by_scope_change": training_hidden,
        "outside_reviewers_required": False,
        "optional_author_feedback_required": False,
        "fabricated_scientific_evidence": False,
    }
