#!/usr/bin/env python3
"""Independent sealed-PATH checks for the AF-025 reproduction packet."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import repro_lib as lib  # noqa: E402

REPO_ROOT = lib.find_repo_root(HERE)
PAPER = REPO_ROOT / "papers/completion/autoformalization"

CRITERIA = (
    "Reproduction result includes exact commands/environment, expected versus actual tables, and explicit unavailable checks; mere LaTeX compilation is not empirical validation.",
    "Final packet links manuscript, supplement, claim audit and raw evidence with version/checksum identities.",
    "The manuscript objective is complete when every retained automated empirical claim has real reproducible evidence and omitted/unmeasured human-dependent claims are explicit. Outside reviewers and optional author feedback are not prerequisites; unfinished required training or fabricated scientific evidence cannot be hidden by the scope change.",
    "No claim that authors approved or the paper was submitted/published is made without real evidence.",
)


def errors_or_ok(errors: list[str], payload: dict) -> int:
    if errors:
        print("AF-025 check failed:\n- " + "\n- ".join(errors))
        return 1
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def main() -> int:
    errors: list[str] = []
    repro_path = PAPER / "evidence" / "final_reproduction.json"
    packet_path = PAPER / "submission" / "author_review_packet.md"
    checksum_path = PAPER / "submission" / "checksums.json"
    for path in (repro_path, packet_path, checksum_path):
        if not path.is_file():
            errors.append(f"missing {path}")
    if errors:
        return errors_or_ok(errors, {})

    repro = lib.load_json(repro_path)
    checksums = lib.load_json(checksum_path)
    packet = packet_path.read_text(encoding="utf-8")

    if repro.get("schema") != "autoformalization-final-reproduction/v1":
        errors.append("final_reproduction.json schema mismatch")
    if repro.get("ok") is not True:
        errors.append("final_reproduction.json ok is not true")
    if repro.get("latex_compilation_is_not_empirical_validation") is not True:
        errors.append("reproduction must state that LaTeX compilation is not empirical validation")
    if repro.get("environment", {}).get("latex_compilation_is_empirical_validation") is not False:
        errors.append("environment must not treat LaTeX as empirical validation")
    if repro.get("environment", {}).get("interpreter") != lib.PYTHON:
        errors.append("reproduction interpreter is not /usr/bin/python3.12")
    if repro.get("environment", {}).get("path") != lib.SEALED_PATH:
        errors.append("reproduction PATH is not the sealed PATH")
    if not str(repro.get("environment", {}).get("home") or "").find("ipfs-accelerate-validation-home-") >= 0:
        if "ipfs-accelerate-validation-home-" not in str(repro.get("environment", {}).get("home") or ""):
            errors.append("reproduction HOME is not a validation home")
    commands = repro.get("commands") or []
    if len(commands) < 3:
        errors.append("reproduction is missing exact commands")
    saw_regen = False
    saw_verify = False
    for command in commands:
        argv = command.get("argv") or []
        if command.get("exit_code") != 0:
            errors.append(f"recorded command failed: {command.get('name')}")
        if command.get("env", {}).get("PATH") != lib.SEALED_PATH:
            errors.append(f"command PATH is not sealed: {command.get('name')}")
        joined = " ".join(argv)
        if "regenerate_tables.py" in joined and "--check" in argv:
            saw_regen = True
        if "verify_retained_inputs.py" in joined:
            saw_verify = True
    if not saw_regen:
        errors.append("reproduction commands omit regenerate_tables.py --check")
    if not saw_verify:
        errors.append("reproduction commands omit verify_retained_inputs.py")

    home = Path(os.environ.get("HOME") or tempfile.mkdtemp(prefix="ipfs-accelerate-validation-home-af025-check-"))
    dest = Path(tempfile.mkdtemp(prefix="af025-check-unzip-", dir=str(home) if home.is_dir() else None))
    with zipfile.ZipFile(PAPER / "submission" / "supplement.zip") as zf:
        zf.extractall(dest)
    root = dest / lib.ZIP_ROOT
    proc = subprocess.run(
        [lib.PYTHON, "-S", "regenerate_tables.py", "--check"],
        cwd=str(root),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        errors.append(f"independent ZIP regenerate_tables.py failed: {proc.stderr or proc.stdout}")
        zip_report = {}
    else:
        zip_report = json.loads(proc.stdout)
    verify = subprocess.run(
        [lib.PYTHON, "-S", "verify_retained_inputs.py"],
        cwd=str(root),
        capture_output=True,
        text=True,
        check=False,
    )
    if verify.returncode != 0:
        errors.append(f"independent verify_retained_inputs.py failed: {verify.stderr or verify.stdout}")
        verify_report = {}
    else:
        verify_report = json.loads(verify.stdout)
        if verify_report.get("ok") is not True:
            errors.append("verify_retained_inputs.py reported ok=false")

    tables = (repro.get("tables") or {}).get("tables") or {}
    for name, expected in lib.EXPECTED_TABLES.items():
        paper_hash = lib.sha256_file(PAPER / "results" / name)
        recorded = tables.get(name) or {}
        zip_actual = None
        if name == "summary.json":
            zip_actual = zip_report.get("summary_sha256")
        else:
            zip_actual = (zip_report.get("tables") or {}).get(name, {}).get("sha256")
        if recorded.get("expected_sha256") != expected:
            errors.append(f"reproduction expected hash drifted for {name}")
        if recorded.get("actual_sha256_paper_tree") != paper_hash:
            errors.append(f"reproduction paper-tree hash does not match live {name}")
        if zip_actual and recorded.get("actual_sha256_zip_regeneration") != zip_actual:
            errors.append(f"reproduction ZIP hash does not match independent regen for {name}")
        if paper_hash != expected or zip_actual not in {None, expected}:
            errors.append(f"live table hash mismatch for {name}")
        if recorded.get("match") is not True:
            errors.append(f"reproduction table match is false for {name}")

    live_probe = lib.probe_checkers()
    recorded_probe = repro.get("unavailable_checks") or {}
    if live_probe.get("any_usable") is True:
        errors.append("a native checker is usable on sealed PATH; frozen unavailable cells would be stale")
    if recorded_probe.get("any_usable") is True:
        errors.append("reproduction recorded a usable sealed-PATH checker")
    if set(recorded_probe.get("missing") or []) != set(lib.CHECKER_TOOLS):
        errors.append("reproduction unavailable-check list does not cover the sealed-PATH tool set")
    for name in lib.CHECKER_TOOLS:
        if live_probe["missing"].count(name) != 1:
            errors.append(f"live probe did not mark {name} unavailable")

    native = repro.get("native_checker_receipts") or {}
    if (native.get("sealed_path_receipts") or {}).get("native_checked_proof_credit") != 0:
        errors.append("sealed native-checker receipts still grant proof credit")
    if (native.get("development_runtime_receipts") or {}).get("table6_credit") is not False:
        errors.append("development Lean/Z3 receipts must not receive Table 6 credit")
    examples = repro.get("example_receipts") or {}
    if (examples.get("finite_semantic_checks") or {}).get("all_match_declared_expected") is not True:
        errors.append("twelve finite checks are not all matching")
    if (examples.get("policy_code_trace") or {}).get("native_lean_q1") != 0:
        errors.append("native Lean Q1 must remain unavailable")
    if (examples.get("policy_code_trace") or {}).get("machine_checked_compiler_soundness") is True:
        errors.append("translation receipts claimed machine-checked compiler soundness")

    pdf = repro.get("pdf_and_supplement") or {}
    if (pdf.get("checklist") or {}).get("n_answers") != 16:
        errors.append("checklist does not have 16 answers")
    answers = (pdf.get("checklist") or {}).get("answers") or []
    if len(answers) == 16 and answers[6] != "No":
        errors.append("statistical-significance answer is not No")
    if (pdf.get("checklist") or {}).get("todo_fields") is True:
        errors.append("checklist still has TODO fields")
    if pdf.get("style_matches_official") is not True:
        errors.append("per-paper style does not match the official research style")
    if (pdf.get("pdf") or {}).get("workshop_footer_present") is not True:
        errors.append("workshop footer not confirmed")
    if (pdf.get("pdf") or {}).get("anonymous_block_retained") is not True:
        errors.append("official anonymous block not retained")
    if pdf.get("pdf", {}).get("scientific_placeholders"):
        errors.append("scientific placeholders remain")
    if pdf.get("pdf", {}).get("publication_hits"):
        errors.append("PDF/manuscript publication claim present")
    if (pdf.get("supplement") or {}).get("missing_required_members"):
        errors.append("supplement ZIP missing required claim-ledger members")
    live_pdf = lib.inspect_pdf_and_supplement(REPO_ROOT, PAPER)
    if live_pdf["pdf"]["sha256"] != (pdf.get("pdf") or {}).get("sha256"):
        errors.append("recorded PDF hash does not match live submission/paper.pdf")
    if live_pdf["supplement"]["sha256"] != (pdf.get("supplement") or {}).get("sha256"):
        errors.append("recorded supplement hash does not match live supplement.zip")
    for rel, digest in lib.OFFICIAL_TEMPLATES.items():
        if lib.sha256_file(REPO_ROOT / rel) != digest:
            errors.append(f"shared user template modified: {rel}")
        rec = (live_pdf.get("templates") or {}).get(rel) or {}
        if rec.get("match") is not True:
            errors.append(f"template checksum mismatch recorded for {rel}")

    objective = repro.get("manuscript_objective") or {}
    if objective.get("missing_source_files"):
        errors.append("retained claim sources are missing")
    if objective.get("unfinished_training_hidden_by_scope_change") is True:
        errors.append("scope change hid unfinished training")
    if objective.get("outside_reviewers_required") is True:
        errors.append("outside reviewers incorrectly required")
    if objective.get("optional_author_feedback_required") is True:
        errors.append("optional author feedback incorrectly required")
    retained = objective.get("retained_automated_claims") or []
    if not retained:
        errors.append("no retained automated claims listed")
    for claim in retained:
        if not claim.get("sources") or any(not src.get("present") for src in claim["sources"]):
            errors.append(f"retained claim {claim.get('id')} lacks live source files")
    omitted = objective.get("omitted_or_unmeasured_claims") or []
    omitted_ids = {c.get("id") for c in omitted}
    for required in ("C1", "C2", "C3", "C4", "C5", "C6", "ABS-HUMAN"):
        if required not in omitted_ids:
            errors.append(f"human-dependent or unrun claim {required} is not explicit")
    inventory = (repro.get("tables") or {}).get("status_inventory") or {}
    if inventory.get("af029_claim_admissible") is not False:
        errors.append("AF-029 packed-CPU updates were relabeled claim-admissible")
    if inventory.get("t2_update_counts") != [0]:
        errors.append("T2 zero-epoch result was not retained")
    if inventory.get("arm_E_activated") is not False or inventory.get("t4_activated") is not False:
        errors.append("T4 or Arm E was marked activated")
    if inventory.get("independent_gold_present") is not False:
        errors.append("independent gold was marked present")
    if inventory.get("gold_records_with_values") not in {0, None}:
        if inventory.get("gold_records_with_values") != 0:
            errors.append("gold_records_with_values is not zero")

    if checksums.get("schema") != "autoformalization-submission-checksums/v1":
        errors.append("checksums.json schema mismatch")
    files = checksums.get("files") or {}
    links = checksums.get("packet_links") or {}
    for group in ("manuscript", "supplement", "claim_audit", "raw_evidence"):
        items = links.get(group) or []
        if not items:
            errors.append(f"checksums.json missing {group} links")
        for rel in items:
            rec = files.get(rel)
            if not rec:
                errors.append(f"checksums.json missing file identity for {rel}")
                continue
            live = lib.sha256_file(REPO_ROOT / rel)
            if rec.get("sha256") != live:
                errors.append(f"checksums.json stale hash for {rel}")
    if files.get("papers/completion/autoformalization/evidence/final_reproduction.json", {}).get("sha256") != lib.sha256_file(repro_path):
        errors.append("checksums.json does not pin final_reproduction.json")

    for rel, rec in files.items():
        if rec.get("sha256") != lib.sha256_file(REPO_ROOT / rel):
            errors.append(f"checksums.json hash mismatch: {rel}")

    required_packet_bits = [
        "does **not** record author sign-off",
        "Expected versus actual tables",
        "Unavailable checks",
        "Finished automated work",
        "Measured failures",
        "Deliberately unrun",
        "Human-dependent claims",
        "Remaining author-only items",
        "Deadlines",
        "Submission files and checksum identities",
        "LaTeX compilation is **not** empirical validation",
        lib.EXPECTED_TABLES["table6_pipeline.tex"],
        lib.EXPECTED_TABLES["table11_training.tex"],
        lib.EXPECTED_TABLES["table13_assistance.tex"],
        files["papers/completion/autoformalization/submission/paper.pdf"]["sha256"],
        files["papers/completion/autoformalization/submission/supplement.zip"]["sha256"],
        files["papers/completion/autoformalization/evidence/final_claim_audit.json"]["sha256"],
        files["papers/completion/autoformalization/evidence/final_reproduction.json"]["sha256"],
        "gold_records_with_values=0",
        "claim_admissible=false",
        "update_counts=[0]",
    ]
    for bit in required_packet_bits:
        if bit not in packet:
            errors.append(f"author_review_packet.md missing required text: {bit[:80]}")
    if "This packet performs no abstract upload" not in packet:
        errors.append("packet does not explicitly deny abstract/paper upload")
    if "Authors did not approve the manuscript in this task." not in packet:
        errors.append("packet does not explicitly deny author approval")
    if "The paper was not submitted or published by this task." not in packet:
        errors.append("packet does not explicitly deny submission/publication")
    for hit in lib.identifying_hits(packet) + lib.identifying_hits(lib.dumps(repro)) + lib.identifying_hits(lib.dumps(checksums)):
        errors.append(f"identifying content in packet outputs: {hit}")
    if lib.placeholder_hits(packet):
        errors.append("author packet contains scientific placeholders")
    if repro.get("author_sign_off") is not False or repro.get("workshop_submission") is not False:
        errors.append("reproduction asserted sign-off or submission")
    if checksums.get("author_sign_off") is not False or checksums.get("workshop_submission") is not False:
        errors.append("checksums.json asserted sign-off or submission")
    if "independent reproduction here means a separate" not in packet.lower():
        errors.append("packet does not define independent reproduction as a clean environment")

    live_inventory = lib.table_status_inventory(lib.load_json(PAPER / "results" / "summary.json"))
    if live_inventory["hypothesis_status_counts"] != {"inconclusive": 1, "supported": 1, "unrun": 6, "unsupported": 1}:
        errors.append("hypothesis status counts drifted")

    payload = {
        "ok": not errors,
        "criteria": list(CRITERIA),
        "tables": {name: tables.get(name, {}).get("actual_sha256_paper_tree") for name in lib.EXPECTED_TABLES},
        "zip_located": verify_report.get("located"),
        "checkers_missing": live_probe.get("missing"),
        "checklist_answers": answers,
        "author_sign_off": False,
        "workshop_submission": False,
        "latex_is_empirical_validation": False,
        "retained_claims": [c.get("id") for c in retained],
        "omitted_claims": sorted(omitted_ids),
    }
    return errors_or_ok(errors, payload)


if __name__ == "__main__":
    raise SystemExit(main())
