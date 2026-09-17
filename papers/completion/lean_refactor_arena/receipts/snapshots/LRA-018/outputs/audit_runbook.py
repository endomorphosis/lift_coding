#!/usr/bin/env python3
"""Audit LRA-018 runbook + freeze against the three acceptance criteria.

Does not write manuscript files. Does not claim official Track 2 scores.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path.cwd()
PAPER = ROOT / "papers/completion/lean_refactor_arena"
FROZEN = "6209680cf00cde0765b77b24834cd72c64dd585b2f7e3f2a58209980ab59a804"
CID = "bafkreicgnd6su3jhmtpckbejqurdb2lchdvvydluswdg5m5zy3cpvroh3i"
REV = "abcc5ce2528c6375148d41dac6dce20f06c339f4"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    runbook_path = PAPER / "harness" / "RUNBOOK.md"
    freeze_path = PAPER / "evidence" / "run_freeze.json"
    main_tex = PAPER / "manuscript" / "main.tex"
    table_tex = PAPER / "manuscript" / "warmup_table.tex"
    jsonl = PAPER / "data" / "benchmark_data_warmup.jsonl"
    runbook = runbook_path.read_text(encoding="utf-8")
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    ms = main_tex.read_text(encoding="utf-8")
    table = table_tex.read_text(encoding="utf-8")
    failures: list[str] = []

    def need(cond: bool, msg: str) -> None:
        if not cond:
            failures.append(msg)

    need("hardware_class=spark_gb10" in runbook, "runbook missing hardware_class=spark_gb10")
    need("run_warmup.py" in runbook and "--run" in runbook, "runbook missing operator --run")
    need("n_problems=15" in runbook, "runbook missing n_problems=15")
    need("verify_lra_batch" in runbook and "--require-complete" in runbook, "runbook missing verifier")
    need("status=PASS" in runbook, "runbook missing status=PASS")
    need(
        "Does not write Arena scores into the manuscript" in runbook,
        "runbook missing manuscript prohibition",
    )
    need("manuscript/main.tex" in runbook, "runbook missing main.tex")
    need("This runbook **does not** edit" in runbook, "runbook must not edit manuscript")
    need("Do not add `lean_refactor_arena` to `scripts/paper_supervisors.py`" in runbook, "PAPERS")
    need("LRAH-008" in runbook and "LRAH-009" in runbook, "LRAH documentation ids")
    need("submissions/warmup" in runbook, "receipts dir")

    need(freeze.get("schema") == "lra-run-freeze/v1", "freeze schema")
    need(freeze.get("hardware_class") == "spark_gb10", "freeze hardware_class")
    need(freeze.get("n_problems") == 15, "freeze n_problems")
    need(freeze.get("arena_score") is None, "freeze arena_score")
    need(freeze.get("official_score") is None, "freeze official_score")
    need(freeze.get("writes_arena_scores_into_manuscript") is False, "freeze writes manuscript")
    need(freeze["jsonl"]["sha256"] == FROZEN, "jsonl sha")
    need(freeze["jsonl"]["n_problems"] == 15, "jsonl n")
    need(len(freeze["jsonl"]["names"]) == 15, "jsonl names")
    need(freeze["weight_identity"]["revision"] == REV, "weight revision")
    need(freeze["weight_identity"]["cid"] == CID, "weight cid")
    need(freeze["weight_identity"]["nvfp4_bytes"] == 67135119264, "nvfp4 bytes")
    need(freeze["weight_identity"]["sm80_derivative_sha256"] is None, "sm80 sha must be null")
    need(freeze["weight_identity"]["unpublished_sha_3fe4e64d_cited"] is False, "unpublished sha cited")
    need(freeze["weight_identity"]["revision"] != "3fe4e64d", "revision is unpublished sha")
    need(freeze["completion_authority"]["command_flag"] == "--require-complete", "authority flag")
    need(freeze["completion_authority"]["required_status"] == "PASS", "authority PASS")
    need("--require-complete" in freeze["completion_authority"]["argv"], "authority argv")
    need("--run" in freeze["operator_command"]["argv"], "operator --run")
    need(freeze["operator_command"]["n_problems"] == 15, "operator n")
    need(freeze["operator_command"]["hardware_class"] == "spark_gb10", "operator hardware")
    need(freeze["freeze_binding"]["warmup_sha256"] == FROZEN, "binding sha")
    need(freeze["freeze_binding"]["arena_score"] is None, "binding arena")
    need(freeze["freeze_binding"]["tiny_byte_lm"] is False, "tiny-byte-lm")
    need(freeze["added_to_paper_supervisors_papers"] is False, "added to PAPERS")
    need(freeze["manuscript"]["arena_scores_written"] is False, "manuscript flag")
    need(freeze["policy_json"]["sha256"] is None, "policy sha present")
    need(sha256_file(jsonl) == FROZEN, "jsonl file drifted")
    need(sha256_file(main_tex) == freeze["manuscript"]["main_tex_sha256"], "main.tex drifted")
    need(sha256_file(table_tex) == freeze["manuscript"]["warmup_table_tex_sha256"], "table drifted")
    need("arena_score" not in ms, "main.tex contains arena_score")
    need("arena_score" not in table, "warmup_table contains arena_score")
    need("official_score" not in ms, "main.tex contains official_score")
    need("Score" not in table, "warmup_table grew a Score column")
    need("does \\emph{not} claim Arena leaderboard scores" in ms, "manuscript still disclaims scores")
    run_warmup = PAPER / "harness" / "run_warmup.py"
    verifier = PAPER / "tools" / "verify_lra_batch.py"
    prompt = PAPER / "harness" / "lra_prompt.txt"
    need(
        sha256_file(run_warmup)
        == freeze["code"]["files"]["papers/completion/lean_refactor_arena/harness/run_warmup.py"],
        "run_warmup sha drift",
    )
    need(
        sha256_file(verifier)
        == freeze["code"]["files"]["papers/completion/lean_refactor_arena/tools/verify_lra_batch.py"],
        "verifier sha drift",
    )
    need(
        sha256_file(prompt) == freeze["prompt_templates"]["lra_prompt_txt"]["sha256"],
        "prompt sha drift",
    )
    argv = freeze["operator_command"]["argv"]
    need(argv[1].endswith("run_warmup.py"), "operator script")
    need("15 problems on Spark" in runbook or "15 frozen warm-up problems" in runbook, "15 on Spark")

    report = {
        "ok": not failures,
        "failures": failures,
        "n_problems": 15,
        "hardware_class": "spark_gb10",
        "operator_command_runs_15_on_spark_gb10": True,
        "completing_requires_verify_lra_batch_require_complete_pass": True,
        "writes_arena_scores_into_manuscript": False,
        "arena_score": None,
        "official_score": None,
        "score": None,
        "manuscript_main_tex_sha256": freeze["manuscript"]["main_tex_sha256"],
        "manuscript_warmup_table_sha256": freeze["manuscript"]["warmup_table_tex_sha256"],
        "run_freeze_schema": freeze["schema"],
        "jsonl_sha256": freeze["jsonl"]["sha256"],
        "completion_authority": freeze["completion_authority"]["command_flag"],
        "operator_argv": freeze["operator_command"]["argv"],
        "added_to_paper_supervisors_papers": False,
        "official_track2": False,
    }
    json.dump(report, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
