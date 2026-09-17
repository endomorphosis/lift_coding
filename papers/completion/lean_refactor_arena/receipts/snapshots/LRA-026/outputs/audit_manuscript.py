#!/usr/bin/env python3
"""Audit LRA-026 manuscript fill against receipts.

Approach/Models/Budget/Reproduction must be filled only from receipts.
Unrun rows stay unrun. No invented leaderboard ranks or token savings.
Author line remains Benjamin Barber / starworks5@gmail.com.
"""
from __future__ import annotations

import ast
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path.cwd()
PAPER = ROOT / "papers/completion/lean_refactor_arena"
MS = PAPER / "manuscript" / "main.tex"
TABLE = PAPER / "manuscript" / "warmup_table.tex"
JSONL = PAPER / "data" / "benchmark_data_warmup.jsonl"
FREEZE = PAPER / "evidence" / "run_freeze.json"
GEN = PAPER / "harness" / "generate_text.py"
RUN = PAPER / "harness" / "run_warmup.py"
PROMPT = PAPER / "harness" / "lra_prompt.txt"
FROZEN = "6209680cf00cde0765b77b24834cd72c64dd585b2f7e3f2a58209980ab59a804"
CID = "bafkreicgnd6su3jhmtpckbejqurdb2lchdvvydluswdg5m5zy3cpvroh3i"
REV = "abcc5ce2528c6375148d41dac6dce20f06c339f4"
PROMPT_SHA = "57036f2bb94d8d8b38d77096ad92a2e615571addee7d01c72e104edaacfee96a"
AUTHOR = "Benjamin Barber"
EMAIL = "starworks5@gmail.com"
REQUIRED_HEADINGS = (
    r"\\section\{Approach\}",
    r"\\section\{Models\}",
    r"\\section\{Budget accounting\}",
    r"\\section\{Reproduction\}",
)
FORBIDDEN_SCORE_ASSIGN = re.compile(
    r"(?:arena_score|official_score|token_savings|leaderboard_rank)\s*=\s*[0-9]"
)
PERCENT_SAVINGS = re.compile(
    r"(?:saved \d+%|\d+%\s*(?:token|elaboration)\s*(?:reduction|saving)|tokens saved)",
    re.IGNORECASE,
)
RANK_CLAIM = re.compile(
    r"(?:leaderboard rank|ranked\s+#\d|place\s+\d+\s+on the Arena|Arena rank\s+\d+)",
    re.IGNORECASE,
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def const_int(tree: ast.AST, name: str) -> int:
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    if isinstance(node.value, ast.Constant) and isinstance(node.value.value, int):
                        return int(node.value.value)
    raise ValueError(f"missing int constant {name}")


def const_str(tree: ast.AST, name: str) -> str:
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                        return str(node.value.value)
    raise ValueError(f"missing str constant {name}")


def const_float(tree: ast.AST, name: str) -> float:
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    if isinstance(node.value, ast.Constant) and isinstance(node.value.value, (int, float)):
                        return float(node.value.value)
    raise ValueError(f"missing float constant {name}")


def main() -> int:
    failures: list[str] = []

    def need(cond: bool, msg: str) -> None:
        if not cond:
            failures.append(msg)

    ms = MS.read_text(encoding="utf-8")
    table = TABLE.read_text(encoding="utf-8")
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    gen_tree = ast.parse(GEN.read_text(encoding="utf-8"), filename=str(GEN))
    run_tree = ast.parse(RUN.read_text(encoding="utf-8"), filename=str(RUN))
    default_tokens = const_int(gen_tree, "DEFAULT_MAX_NEW_TOKENS")
    putnam_tokens = const_int(gen_tree, "PUTNAM_MAX_NEW_TOKENS")
    default_timeout = const_int(gen_tree, "DEFAULT_TIMEOUT_SECONDS")
    putnam_timeout = const_int(gen_tree, "PUTNAM_TIMEOUT_SECONDS")
    token_w = const_float(run_tree, "TOKEN_WEIGHT")
    elab_w = const_float(run_tree, "ELAB_WEIGHT")
    tokenizer = const_str(run_tree, "TOKENIZER_ID")
    hardware = const_str(run_tree, "HARDWARE_CLASS")
    protocol = const_str(run_tree, "PROTOCOL")
    typesafe = const_str(run_tree, "TYPESAFE")
    hammers = const_str(run_tree, "HAMMERS")

    need(AUTHOR in ms, "author name missing")
    need(EMAIL.replace("@", r"@") in ms or EMAIL in ms, "author email missing")
    need(r"\texttt{starworks5@gmail.com}" in ms, "author email not in texttt")
    need("Hippocampus" not in ms, "template author leaked")
    headings = [h for h in REQUIRED_HEADINGS if re.search(h, ms)]
    need(len(headings) == 4, f"required headings missing: {REQUIRED_HEADINGS}")
    order = [m.start() for m in (re.search(h, ms) for h in REQUIRED_HEADINGS) if m]
    need(order == sorted(order) and len(order) == 4, "required headings out of order")

    need(f"max\\_new\\_tokens={default_tokens}" in ms or f"{default_tokens}" in ms, "default 1400 missing")
    need(str(default_tokens) in ms, "1400 not in manuscript")
    need(str(putnam_tokens) in ms, "4096 not in manuscript")
    need("1024 completion tokens" not in ms, "stale 1024 completion limit remains")
    need("2048-token input ceiling" not in ms, "stale 2048 input ceiling remains")
    need(str(default_timeout) in ms, "300s timeout missing")
    need("600" in ms, "600s Putnam/warm-up timeout missing")
    need(REV in ms, "weight revision missing")
    need(CID in ms, "weight CID missing")
    need("67135119264" in ms.replace("\\,", "") or "67\\,135\\,119\\,264" in ms, "nvfp4 bytes missing")
    need(PROMPT_SHA in ms, "prompt sha missing")
    need(FROZEN in ms, "frozen jsonl sha missing")
    need(protocol == "LRA/v1", "run_warmup protocol drifted")
    need("LRA/v1" in ms, "protocol LRA/v1 missing from manuscript")
    need("LRA/v2" not in ms, "protocol grown to LRA/v2")
    need("3fe4e64d" not in ms, "unpublished SHA cited")
    need(hardware == "spark_gb10", "run_warmup hardware drifted")
    need("spark\\_gb10" in ms or "spark_gb10" in ms, "hardware_class missing")
    need(typesafe == "off" and hammers == "off", "v1 gates drifted")
    need("LRA\\_TYPESAFE=off" in ms or "TypeSafe Jev are off" in ms, "typesafe-off missing")
    need(abs(token_w - 0.55) < 1e-9 and abs(elab_w - 0.45) < 1e-9, "keep-best weights drifted")
    need("0.55" in ms and "0.45" in ms, "keep-best weights missing")
    need(tokenizer in ms, "tokenizer id missing")
    need("unrun" in ms, "unrun labels missing")
    need("Development harness (Spark GB10, 15 problems)" in ms, "15-problem row missing")
    need("Official Track~2 benchmark run" in ms, "official track2 row missing")
    # The 15-problem and official rows must still say unrun.
    dev_row = "Development harness (Spark GB10, 15 problems) & 1 $\\times$ GB10 & unrun"
    off_row = "Official Track~2 benchmark run & 4 $\\times$ A100 80\\,GB & unrun; cap 48 h"
    need(dev_row in ms, "15-problem row is not unrun")
    need(off_row in ms, "official Track 2 row is not unrun")
    need("We do not claim general token savings" in ms, "token-savings disclaimer missing")
    need("does \\emph{not} claim Arena leaderboard scores" in ms, "arena disclaimer missing")
    need("No Arena submission was made with this report" in ms, "submission disclaimer missing")
    need("submissions/warmup" in ms, "operator receipts dir missing")
    need("verify\\_lra\\_batch" in ms or "verify_lra_batch" in ms, "verifier missing")
    need("--require-complete" in ms, "require-complete missing")
    need("status=PASS" in ms or "prints \\texttt{PASS}" in ms, "PASS gate missing")
    need("CallElimCorrect.substOldPostSubset" in ms, "live probe problem missing")
    need("32" in ms and "new tokens" in ms, "32-token probe missing")
    need("hardware\\_class=synthetic" in ms or "hardware_class=synthetic" in ms, "synthetic compile caveat missing")
    need("capability gap" in ms, "elan capability gap missing")
    need("SM80 derivative SHA is null" in ms, "sm80 null missing")
    need("src.startswith(statement)" in ms, "prefix-bind fact missing")
    need("byte 55" in ms, "CCS named-assign fact missing")
    need("keeps 27" in ms, "ArkLib 27 := missing")
    need("70097d371a247f758872fcedd7d14209553aa4afac8ecb1e40e2555b87253e9f" in ms, "retrieve lemma digest missing")
    need("1400" in ms and "4096" in ms, "harness token limits missing")
    need("Score" not in table, "warmup_table grew a Score column")
    need("arena_score" not in table, "warmup_table contains arena_score")
    need(FORBIDDEN_SCORE_ASSIGN.search(ms) is None, "numeric score assignment in manuscript")
    need(PERCENT_SAVINGS.search(ms) is None, "invented token-savings percentage")
    need(RANK_CLAIM.search(ms) is None, "invented leaderboard rank")
    need("rank #1" not in ms.lower() and "first place" not in ms.lower(), "invented place claim")
    need(sha256_file(JSONL) == FROZEN, "jsonl digest drifted")
    need(JSONL.stat().st_size == 113826, "jsonl size drifted")
    need(sha256_file(PROMPT) == PROMPT_SHA, "prompt digest drifted")
    need(freeze["jsonl"]["sha256"] == FROZEN, "freeze jsonl sha")
    need(freeze["arena_score"] is None, "freeze arena_score not null")
    need(freeze["official_score"] is None, "freeze official_score not null")
    need(freeze["token_savings"] is None, "freeze token_savings not null")
    need(freeze["writes_arena_scores_into_manuscript"] is False, "freeze writes scores")
    need(freeze["weight_identity"]["revision"] == REV, "freeze revision")
    need(freeze["weight_identity"]["cid"] == CID, "freeze cid")
    need(freeze["weight_identity"]["nvfp4_bytes"] == 67135119264, "freeze nvfp4")
    need(freeze["weight_identity"]["sm80_derivative_sha256"] is None, "freeze sm80")
    need(freeze["weight_identity"]["unpublished_sha_3fe4e64d_cited"] is False, "unpublished cited")
    need(freeze["operator_command"]["n_problems"] == 15, "operator n")
    need(freeze["operator_command"]["hardware_class"] == "spark_gb10", "operator hardware")
    need(freeze["typesafe"]["lra_typesafe"] == "off", "freeze typesafe")
    need(freeze["protocol"] == "LRA/v1", "freeze protocol")
    need(not (PAPER / "submissions" / "warmup").exists(), "15-problem receipt tree exists; row would not be unrun")
    need(default_tokens == 1400 and putnam_tokens == 4096, "generate_text token constants drifted")
    need(default_timeout == 300 and putnam_timeout == 600, "generate_text timeouts drifted")

    payload = {
        "ok": not failures,
        "failures": failures,
        "author": AUTHOR,
        "email": EMAIL,
        "protocol": protocol,
        "hardware_class": hardware,
        "default_max_new_tokens": default_tokens,
        "putnam_max_new_tokens": putnam_tokens,
        "token_weight": token_w,
        "elab_weight": elab_w,
        "tokenizer_id": tokenizer,
        "typesafe": typesafe,
        "hammers": hammers,
        "frozen_warmup_sha256": FROZEN,
        "jsonl_bytes": JSONL.stat().st_size,
        "prompt_sha256": PROMPT_SHA,
        "main_tex_sha256": sha256_file(MS),
        "warmup_table_sha256": sha256_file(TABLE),
        "weight_revision": REV,
        "weight_cid": CID,
        "nvfp4_bytes": 67135119264,
        "sm80_derivative_sha256": None,
        "arena_score": None,
        "official_score": None,
        "token_savings": None,
        "leaderboard_rank": None,
        "writes_arena_scores": False,
        "unrun_15_problem_spark": True,
        "unrun_official_track2": True,
        "submissions_warmup_exists": (PAPER / "submissions" / "warmup").exists(),
        "required_headings_in_order": True,
        "stale_1024_2048_removed": "1024 completion tokens" not in ms and "2048-token input ceiling" not in ms,
        "live_probe_32_tokens_disclosed": True,
        "synthetic_compile_not_claimed_as_live": True,
        "protocol_not_grown": "LRA/v2" not in ms,
    }
    json.dump(payload, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
