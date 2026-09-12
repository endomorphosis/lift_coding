#!/usr/bin/env python3
"""Run the feasible AF-025 reproduction and write the author handoff packet."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import repro_lib as lib  # noqa: E402

REPO_ROOT = lib.find_repo_root(HERE)
PAPER = REPO_ROOT / "papers/completion/autoformalization"
SNAP = PAPER / "receipts" / "snapshots" / "AF-025"
LOGS = SNAP / "logs"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sealed_argv(home: Path, python_tail: list[str]) -> list[str]:
    return [
        "/usr/bin/env", "-i",
        f"PATH={lib.SEALED_PATH}",
        f"HOME={home}",
        f"XDG_CACHE_HOME={home / '.cache'}",
        f"XDG_CONFIG_HOME={home / '.config'}",
        f"XDG_DATA_HOME={home / '.local/share'}",
        f"XDG_STATE_HOME={home / '.local/state'}",
        "PYTHONDONTWRITEBYTECODE=1",
        "PYTHONNOUSERSITE=1",
        "LANG=C.UTF-8",
        lib.PYTHON,
        *python_tail,
    ]


def run_recorded(name: str, argv: list[str], cwd: Path, home: Path) -> dict:
    LOGS.mkdir(parents=True, exist_ok=True)
    started = utc_now()
    t0 = time.perf_counter()
    proc = subprocess.run(argv, cwd=str(cwd), capture_output=True, text=True, check=False)
    elapsed = time.perf_counter() - t0
    finished = utc_now()
    stdout_path = LOGS / f"{name}.stdout.log"
    stderr_path = LOGS / f"{name}.stderr.log"
    stdout_path.write_text(proc.stdout, encoding="utf-8")
    stderr_path.write_text(proc.stderr, encoding="utf-8")
    record = {
        "name": name,
        "argv": argv,
        "cwd": str(cwd if cwd == REPO_ROOT else cwd),
        "cwd_recorded": "." if cwd == REPO_ROOT else str(cwd),
        "elapsed_seconds": elapsed,
        "env": {
            "HOME": str(home),
            "LANG": "C.UTF-8",
            "PATH": lib.SEALED_PATH,
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1",
        },
        "exit_code": proc.returncode,
        "finished_at": finished,
        "started_at": started,
        "stdout_log": str(stdout_path.relative_to(REPO_ROOT)),
        "stderr_log": str(stderr_path.relative_to(REPO_ROOT)),
    }
    (LOGS / f"{name}.meta.json").write_text(lib.dumps(record), encoding="utf-8")
    return record


def prepare_home() -> Path:
    existing = os.environ.get("HOME", "")
    if existing.startswith("/tmp/") and "ipfs-accelerate-validation-home-" in existing:
        home = Path(existing)
    else:
        home = Path(tempfile.mkdtemp(prefix="ipfs-accelerate-validation-home-af025-"))
    (home / ".cache").mkdir(parents=True, exist_ok=True)
    (home / ".config").mkdir(parents=True, exist_ok=True)
    (home / ".local" / "share").mkdir(parents=True, exist_ok=True)
    (home / ".local" / "state").mkdir(parents=True, exist_ok=True)
    return home


def unpack_supplement(home: Path) -> Path:
    dest = Path(tempfile.mkdtemp(prefix="af025-unzip-", dir=str(home)))
    with zipfile.ZipFile(PAPER / "submission" / "supplement.zip") as zf:
        zf.extractall(dest)
    root = dest / lib.ZIP_ROOT
    if not root.is_dir():
        raise SystemExit("supplement.zip did not unpack the anonymous reproducibility root")
    return root


def compare_tables(zip_report: dict, paper_tree: dict[str, str]) -> dict:
    rows = {}
    ok = True
    for name, expected in lib.EXPECTED_TABLES.items():
        zip_actual = None
        if name == "summary.json":
            zip_actual = zip_report.get("summary_sha256")
        else:
            zip_actual = (zip_report.get("tables") or {}).get(name, {}).get("sha256")
        paper_actual = paper_tree[name]
        match = expected == zip_actual == paper_actual
        if not match:
            ok = False
        rows[name] = {
            "expected_sha256": expected,
            "actual_sha256_zip_regeneration": zip_actual,
            "actual_sha256_paper_tree": paper_actual,
            "match": match,
        }
    return {"ok": ok, "tables": rows, "zip_ok": zip_report.get("ok") is True}


def identity_set() -> dict[str, dict]:
    files = {
        "papers/completion/autoformalization/submission/paper.pdf": "manuscript_pdf",
        "papers/completion/autoformalization/manuscript/main.tex": "manuscript_source",
        "papers/completion/autoformalization/manuscript/checklist.tex": "checklist",
        "papers/completion/autoformalization/manuscript/llm_disclosure.tex": "llm_disclosure",
        "papers/completion/autoformalization/manuscript/empirical_scope.tex": "empirical_scope",
        "papers/completion/autoformalization/manuscript/neurips_2026_vericode.sty": "per_paper_style",
        "papers/completion/autoformalization/manuscript/references.bib": "bibliography",
        "papers/neurips_2026_vericode_workshop.tex": "official_research_shell",
        "papers/neurips_2026_vericode.sty": "official_research_style",
        "papers/checklist.tex": "official_questionnaire",
        "papers/completion/autoformalization/submission/supplement.zip": "anonymous_supplement",
        "papers/completion/autoformalization/artifact/README.md": "artifact_readme",
        "papers/completion/autoformalization/artifact/manifest.json": "artifact_manifest",
        "papers/completion/autoformalization/artifact/S01_S40_map.json": "s01_s40_map",
        "papers/completion/autoformalization/evidence/anonymization_report.json": "anonymization_report",
        "papers/completion/autoformalization/evidence/final_claim_audit.json": "claim_audit",
        "papers/completion/autoformalization/evidence/bibliography_audit.md": "bibliography_audit",
        "papers/completion/autoformalization/results/hypothesis_report.md": "hypothesis_report",
        "papers/completion/autoformalization/results/summary.json": "results_summary",
        "papers/completion/autoformalization/results/table6_pipeline.tex": "table6",
        "papers/completion/autoformalization/results/table11_training.tex": "table11",
        "papers/completion/autoformalization/results/table13_assistance.tex": "table13",
        "papers/completion/autoformalization/evidence/native_checker_receipts.jsonl": "sealed_native_checker_receipts",
        "papers/completion/autoformalization/evidence/runtime_qualification/native_checker_receipts.jsonl": "development_native_checker_receipts",
        "papers/completion/autoformalization/evaluation/reference_results.json": "finite_example_receipts",
        "papers/completion/autoformalization/evidence/translation_receipts.jsonl": "bridge_example_receipts",
        "papers/completion/autoformalization/config/structural_evidence_scope.json": "structural_evidence_scope",
        "papers/completion/autoformalization/evidence/author_feedback_status.json": "author_feedback_status",
        "papers/completion/autoformalization/evidence/author_questions.md": "author_questions",
        "papers/completion/autoformalization/evidence/format_check.json": "format_check",
        "papers/completion/autoformalization/submission/template_inputs.json": "template_inputs",
        "papers/completion/autoformalization/data/splits.json": "splits",
    }
    return {rel: lib.file_identity(REPO_ROOT, rel, role) for rel, role in files.items()}


def write_author_packet(repro: dict, checksums: dict) -> str:
    tables = repro["tables"]["tables"]
    table_lines = [
        "| File | Expected SHA-256 | ZIP regeneration | Paper tree | Match |",
        "| --- | --- | --- | --- | --- |",
    ]
    for name, row in tables.items():
        table_lines.append(
            f"| `{name}` | `{row['expected_sha256']}` | `{row['actual_sha256_zip_regeneration']}` | "
            f"`{row['actual_sha256_paper_tree']}` | {'yes' if row['match'] else 'NO'} |"
        )
    tool_lines = [
        "| Tool | Sealed PATH resolution | Status |",
        "| --- | --- | --- |",
    ]
    for row in repro["unavailable_checks"]["tools"]:
        tool_lines.append(
            f"| `{row['name']}` | `{row['resolved_path'] or 'not found'}` | {row['status']} |"
        )
    files = checksums["files"]
    def cite(rel: str) -> str:
        item = files[rel]
        return f"`{rel}` SHA-256 `{item['sha256']}` ({item['bytes']} bytes)"

    claim_status = repro["pdf_and_supplement"]["claim_ledger"]["statuses"]
    retained_ids = [c["id"] for c in repro["manuscript_objective"]["retained_automated_claims"]]
    omitted_ids = [
        f"{c['id']}:{c['status']}" for c in repro["manuscript_objective"]["omitted_or_unmeasured_claims"]
    ]
    lines = [
        "# Author review packet (AF-025)",
        "",
        "This packet is an autonomous evidence handoff for the compiler-guided",
        "autoformalization manuscript. Independent reproduction here means a separate",
        "clean sealed-PATH execution environment; it does not require an outside person.",
        "It does **not** record author sign-off, OpenReview upload, workshop submission,",
        "or publication.",
        "",
        "## Environment and commands",
        "",
        f"- Interpreter: `{lib.PYTHON}` (`{repro['environment']['python_version']}`)",
        f"- `PATH`: `{lib.SEALED_PATH}`",
        f"- HOME prefix: `ipfs-accelerate-validation-home-`",
        "- Standard library only for table regeneration and receipt inspection.",
        "- LaTeX compilation is **not** empirical validation and was not used as such.",
        "- Paper-tree `evaluation/analyze_results.py --check` was not executed because it",
        "  rewrites undeclared result files; the declared feasible command is the",
        "  anonymous ZIP regenerator.",
        "",
        "Documented ZIP commands actually run:",
        "",
        "```",
        "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin HOME=<ipfs-accelerate-validation-home-*> \\",
        "/usr/bin/python3.12 -S regenerate_tables.py --check",
        "/usr/bin/python3.12 -S verify_retained_inputs.py",
        "```",
        "",
        "Exact argv, timestamps, and exit codes are in",
        "`papers/completion/autoformalization/evidence/final_reproduction.json`.",
        "",
        "## Expected versus actual tables",
        "",
        *table_lines,
        "",
        "Unrun and unavailable cells remain labeled; they are not measured zeros.",
        f"Table 6 statuses: `{repro['tables']['status_inventory']['table6']['statuses']}`.",
        f"Table 11 statuses: `{repro['tables']['status_inventory']['table11']['statuses']}`.",
        f"Table 13 statuses: `{repro['tables']['status_inventory']['table13']['statuses']}`.",
        "",
        "## Unavailable checks",
        "",
        *tool_lines,
        "",
        "Sealed-PATH native useful-proof cells stay unavailable, not 0/1913 soundness.",
        "AF-027 development Lean/Z3 receipts used operator-local binaries that are not on",
        "this PATH; they do not receive Table 6 credit and were not replayed.",
        "pdflatex/latexmk are also absent from sealed PATH; format evidence is the frozen",
        "AF-024 PDF/log inspection, not a new compilation.",
        "",
        "## Finished automated work",
        "",
        "- Anonymous supplement, S01-S40 map, and table regenerators (AF-023).",
        "- Official style/checklist/disclosure/PDF anonymity checks (AF-024).",
        "- Claim ledger with 27 mapped claims (AF-022).",
        "- Regenerable Tables 6/11/13 from frozen `summary.json` (AF-021).",
        "- Finite constructed checks (12/12 match) and Q1/Q2 translation receipts (AF-006/AF-015).",
        "- Sealed-PATH native-checker unavailability receipts (AF-018) and development",
        "  Lean success/failure plus Z3 unsat sentinels (AF-027), explicitly non-Table-6.",
        "- Structural-evidence scope: human fidelity unmeasured; teacher/prover not source gold (AF-028).",
        "",
        "Retained automated claim IDs with hash-bound sources:",
        ", ".join(f"`{cid}`" for cid in retained_ids) + ".",
        "",
        "## Measured failures and negative results",
        "",
        "- Shared-parameter T2 accepted 0 sealed-PATH epochs (`update_counts=[0]`); H-T2 is unsupported.",
        "- T1 train-versus-selection teacher cosine is a sample-memory diagnostic, not generalization;",
        "  `claim_admissible_for_paper_primary=false`.",
        "- AF-029 packed-CPU MiniLM updates remain `claim_admissible=false` and do not fill Table 11 held-out cells.",
        "- C7 retrieval/planning/assistance utility is inconclusive on natural held-out cells.",
        "- Sorry/admit/unapproved-axiom Lean fixtures are policy-rejected before any kernel claim.",
        "- AF-027 `False:=trivial` is an explicit development type error, not a Table 6 success.",
        "",
        "## Deliberately unrun or unavailable conditions",
        "",
        "- Locked 1913-unit final-test A--E coverage, cost, and native useful-proof cells.",
        "- Held-out independent source-semantic fidelity (no gold; teacher cosine is not this cell).",
        "- T3 eligible native labels, T4 consumer load, and Arm E promotion (`e_locked`).",
        "- Related-work systems (LeanDojo, DSP/miniF2F, Sledgehammer, Baldur, CompCert, seL4, Dafny) not executed.",
        "- Independent 100-unit human review sample remains blank (`gold_records_with_values=0`).",
        "",
        "Omitted/unmeasured claim IDs:",
        ", ".join(f"`{item}`" for item in omitted_ids) + ".",
        "",
        "The AF-028 reporting scope does not convert those unrun training or human-dependent",
        "cells into measured success. Unfinished required training is still recorded as",
        "unrun/unavailable/unsupported.",
        "",
        "## Human-dependent claims",
        "",
        "Independent human agreement and source-semantic fidelity are **unmeasured, not",
        "collected**. They are not replaced by prover success, teacher agreement, reconstruction",
        "scores, or optional author comments. Outside reviewers and optional author feedback",
        "are not manuscript-completion prerequisites. Optional author feedback was not supplied",
        "and is acceptable in its absence.",
        "",
        "## Remaining author-only items (cannot be invented)",
        "",
        "1. Camera-ready names, affiliations, postal addresses, and emails for a non-anonymous `final` build.",
        "2. Author verification of equations, examples, bibliography, checklist, and LLM disclosure.",
        "3. Any additional model/provider/date/prompt/code/annotation assistance not already logged.",
        "4. Camera-ready funding acknowledgements.",
        "5. Actual OpenReview/workshop upload and licensing. This packet does not perform them.",
        "6. Overleaf project membership remains unverified (historical HTTP 403).",
        "7. Coding-shard license-risk rows stay unadmitted.",
        "8. Optional independent annotation of the blank 100-unit sample.",
        "9. Any license statement on the anonymous supplement beyond the hash-bound package.",
        "",
        "## Deadlines",
        "",
        "The reviewed CFP record (checked 2026-09-11 against",
        "https://vericodegen.github.io/cfp.html) lists tentative AoE dates: abstract 2026-09-11",
        "and paper 2026-09-13. Those dates are tentative. Authors must recheck the live CFP",
        "and OpenReview before any external action. This packet performs no abstract upload,",
        "paper upload, or author approval.",
        "",
        "## Submission files and checksum identities",
        "",
        "- Manuscript PDF: " + cite("papers/completion/autoformalization/submission/paper.pdf"),
        "- Manuscript source: " + cite("papers/completion/autoformalization/manuscript/main.tex"),
        "- Anonymous supplement: " + cite("papers/completion/autoformalization/submission/supplement.zip"),
        "- Claim audit: " + cite("papers/completion/autoformalization/evidence/final_claim_audit.json"),
        "- Results summary: " + cite("papers/completion/autoformalization/results/summary.json"),
        "- Reproduction result: " + cite("papers/completion/autoformalization/evidence/final_reproduction.json"),
        "- Checksum ledger: `papers/completion/autoformalization/submission/checksums.json`",
        f"  SHA-256 `{checksums['self_sha256_placeholder']}`",
        "",
        "Official templates remain unmodified:",
        f"- `papers/neurips_2026_vericode_workshop.tex` `{files['papers/neurips_2026_vericode_workshop.tex']['sha256']}`",
        f"- `papers/neurips_2026_vericode.sty` `{files['papers/neurips_2026_vericode.sty']['sha256']}`",
        f"- `papers/checklist.tex` `{files['papers/checklist.tex']['sha256']}`",
        "",
        "Checklist: 16 official questions with Yes/No/N/A answers",
        f"`{','.join(repro['pdf_and_supplement']['checklist']['answers'])}`; statistical significance is No;",
        "instruction block removed; Affiliation/Address/email is style-generated anonymous text.",
        "Workshop footer and review line numbers are retained.",
        "",
        f"Analysis identity: `{lib.ANALYSIS_ID}`. Scope policy: `{lib.SCOPE_POLICY_ID}`",
        f"(SHA-256 `{lib.SCOPE_SHA256}`).",
        "",
        "## What this packet does not claim",
        "",
        "- Authors did not approve the manuscript in this task.",
        "- The paper was not submitted or published by this task.",
        "- Independent human fidelity was not measured.",
        "- Native useful-proof coverage on 1913 units was not obtained.",
        "- Scope narrowing does not complete C1--C6 or hide T2/T4/E/AF-029 training status.",
        "",
    ]
    # placeholder replaced after checksums.json is hashed
    return "\n".join(lines) + "\n"


def main() -> int:
    home = prepare_home()
    LOGS.mkdir(parents=True, exist_ok=True)
    version = run_recorded(
        "packet_python_version",
        sealed_argv(home, ["-V"]),
        REPO_ROOT,
        home,
    )
    python_version = (LOGS / "packet_python_version.stdout.log").read_text(encoding="utf-8").strip()
    bundle = unpack_supplement(home)
    zip_regen = run_recorded(
        "zip_regenerate_tables",
        sealed_argv(home, ["-S", "regenerate_tables.py", "--check"]),
        bundle,
        home,
    )
    zip_verify = run_recorded(
        "zip_verify_retained_inputs",
        sealed_argv(home, ["-S", "verify_retained_inputs.py"]),
        bundle,
        home,
    )
    if zip_regen["exit_code"] != 0 or zip_verify["exit_code"] != 0:
        print("ZIP reproduction failed", file=sys.stderr)
        print((LOGS / "zip_regenerate_tables.stderr.log").read_text(encoding="utf-8"), file=sys.stderr)
        print((LOGS / "zip_verify_retained_inputs.stderr.log").read_text(encoding="utf-8"), file=sys.stderr)
        return 1
    zip_report = json.loads((LOGS / "zip_regenerate_tables.stdout.log").read_text(encoding="utf-8"))
    verify_report = json.loads((LOGS / "zip_verify_retained_inputs.stdout.log").read_text(encoding="utf-8"))
    paper_tree_hashes = {
        "table6_pipeline.tex": lib.sha256_file(PAPER / "results" / "table6_pipeline.tex"),
        "table11_training.tex": lib.sha256_file(PAPER / "results" / "table11_training.tex"),
        "table13_assistance.tex": lib.sha256_file(PAPER / "results" / "table13_assistance.tex"),
        "summary.json": lib.sha256_file(PAPER / "results" / "summary.json"),
    }
    tables = compare_tables(zip_report, paper_tree_hashes)
    summary = lib.load_json(PAPER / "results" / "summary.json")
    tables["status_inventory"] = lib.table_status_inventory(summary)
    checkers = lib.probe_checkers()
    (LOGS / "checker_probe.json").write_text(lib.dumps(checkers), encoding="utf-8")
    pdf_report = lib.inspect_pdf_and_supplement(REPO_ROOT, PAPER)
    audit = lib.load_json(PAPER / "evidence" / "final_claim_audit.json")
    objective = lib.claim_evidence_complete(REPO_ROOT, PAPER, audit)
    native = lib.inspect_native_checker_receipts(PAPER)
    examples = lib.inspect_example_receipts(PAPER)
    identities = identity_set()
    environment = {
        "interpreter": lib.PYTHON,
        "python_version": python_version,
        "path": lib.SEALED_PATH,
        "home": str(home),
        "home_prefix": "ipfs-accelerate-validation-home-",
        "standard_library_only": True,
        "latex_compilation_is_empirical_validation": False,
        "analyze_results_py_check_executed": False,
        "analyze_results_py_check_reason": "analyze_results.py --check rewrites undeclared results files; ZIP regenerate_tables.py --check is the declared feasible reproduction.",
    }
    commands = []
    for record in (version, zip_regen, zip_verify):
        commands.append({
            "argv": record["argv"],
            "cwd": record["cwd_recorded"] if record is version else str(Path(record["cwd"]).name if False else record["cwd_recorded"]),
            "elapsed_seconds": record["elapsed_seconds"],
            "env": record["env"],
            "exit_code": record["exit_code"],
            "started_at": record["started_at"],
            "finished_at": record["finished_at"],
            "log": record["stdout_log"],
            "stderr_log": record["stderr_log"],
            "name": record["name"],
        })
    # Record ZIP cwd as the unpacked bundle path without operator-identifying parents
    commands[1]["cwd"] = str(bundle)
    commands[1]["cwd_role"] = "unpacked_anonymous_supplement"
    commands[2]["cwd"] = str(bundle)
    commands[2]["cwd_role"] = "unpacked_anonymous_supplement"
    commands[0]["cwd"] = "."
    reproduction = {
        "schema": "autoformalization-final-reproduction/v1",
        "task_id": "AF-025",
        "reproduced_at": utc_now(),
        "analysis_id": lib.ANALYSIS_ID,
        "scope_policy_id": lib.SCOPE_POLICY_ID,
        "scope_policy_sha256": lib.SCOPE_SHA256,
        "environment": environment,
        "commands": commands,
        "tables": tables,
        "unavailable_checks": checkers,
        "native_checker_receipts": native,
        "example_receipts": examples,
        "pdf_and_supplement": pdf_report,
        "manuscript_objective": objective,
        "zip_retained_inputs": {
            "ok": verify_report.get("ok") is True,
            "located": verify_report.get("located"),
            "missing": verify_report.get("missing") or [],
            "mismatched": verify_report.get("mismatched") or [],
        },
        "author_sign_off": False,
        "workshop_submission": False,
        "openreview_upload": False,
        "public_upload": False,
        "human_fidelity_status": "unmeasured_not_collected",
        "latex_compilation_is_not_empirical_validation": True,
        "independent_reproduction_means": "separate_clean_execution_environment_not_an_outside_person",
        "outside_reviewers_required": False,
        "optional_author_feedback_required": False,
        "identities": identities,
    }
    if not tables["ok"] or checkers["any_usable"] or objective["missing_source_files"] or objective["unfinished_training_hidden_by_scope_change"]:
        reproduction["ok"] = False
    else:
        reproduction["ok"] = (
            zip_regen["exit_code"] == 0
            and zip_verify["exit_code"] == 0
            and verify_report.get("ok") is True
            and pdf_report["format_check_ok"] is True
            and pdf_report["checklist"]["n_answers"] == 16
            and not pdf_report["checklist"]["todo_fields"]
            and pdf_report["style_matches_official"]
            and not pdf_report["pdf"]["scientific_placeholders"]
            and not pdf_report["pdf"]["publication_hits"]
            and examples["finite_semantic_checks"]["all_match_declared_expected"]
            and native["sealed_path_receipts"]["native_checked_proof_credit"] == 0
        )
    repro_path = PAPER / "evidence" / "final_reproduction.json"
    repro_path.write_text(lib.dumps(reproduction), encoding="utf-8")
    identities["papers/completion/autoformalization/evidence/final_reproduction.json"] = lib.file_identity(
        REPO_ROOT,
        "papers/completion/autoformalization/evidence/final_reproduction.json",
        "final_reproduction",
    )
    checksums = {
        "schema": "autoformalization-submission-checksums/v1",
        "task_id": "AF-025",
        "generated_at": utc_now(),
        "analysis_id": lib.ANALYSIS_ID,
        "scope_policy_id": lib.SCOPE_POLICY_ID,
        "scope_policy_sha256": lib.SCOPE_SHA256,
        "python": {
            "interpreter": lib.PYTHON,
            "version": python_version,
            "path": lib.SEALED_PATH,
        },
        "packet_links": {
            "manuscript": [
                "papers/completion/autoformalization/submission/paper.pdf",
                "papers/completion/autoformalization/manuscript/main.tex",
                "papers/completion/autoformalization/manuscript/checklist.tex",
                "papers/completion/autoformalization/manuscript/llm_disclosure.tex",
            ],
            "supplement": [
                "papers/completion/autoformalization/submission/supplement.zip",
                "papers/completion/autoformalization/artifact/manifest.json",
                "papers/completion/autoformalization/artifact/README.md",
            ],
            "claim_audit": [
                "papers/completion/autoformalization/evidence/final_claim_audit.json",
                "papers/completion/autoformalization/results/hypothesis_report.md",
            ],
            "raw_evidence": [
                "papers/completion/autoformalization/results/summary.json",
                "papers/completion/autoformalization/results/table6_pipeline.tex",
                "papers/completion/autoformalization/results/table11_training.tex",
                "papers/completion/autoformalization/results/table13_assistance.tex",
                "papers/completion/autoformalization/evidence/native_checker_receipts.jsonl",
                "papers/completion/autoformalization/evaluation/reference_results.json",
                "papers/completion/autoformalization/evidence/translation_receipts.jsonl",
                "papers/completion/autoformalization/evidence/final_reproduction.json",
            ],
        },
        "files": identities,
        "author_sign_off": False,
        "workshop_submission": False,
        "public_upload": False,
    }
    checksum_path = PAPER / "submission" / "checksums.json"
    checksum_path.write_text(lib.dumps(checksums), encoding="utf-8")
    checksums_hash = lib.sha256_file(checksum_path)
    packet = write_author_packet(reproduction, {**checksums, "self_sha256_placeholder": checksums_hash})
    packet = packet.replace(checksums_hash, checksums_hash)
    packet_path = PAPER / "submission" / "author_review_packet.md"
    packet_path.write_text(packet, encoding="utf-8")
    report = {
        "ok": reproduction["ok"],
        "final_reproduction": str(repro_path.relative_to(REPO_ROOT)),
        "checksums": str(checksum_path.relative_to(REPO_ROOT)),
        "author_review_packet": str(packet_path.relative_to(REPO_ROOT)),
        "tables_match": tables["ok"],
        "checkers_usable": checkers["any_usable"],
        "located_zip_members": verify_report.get("located"),
    }
    print(lib.dumps(report), end="")
    return 0 if reproduction["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
