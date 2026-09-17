#!/usr/bin/env python3
"""Extract receipt-backed Models/Budget constants used to fill the manuscript.

Read-only. Does not edit main.tex. Does not claim Arena scores.
"""
from __future__ import annotations

import ast
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path.cwd()
PAPER = ROOT / "papers/completion/lean_refactor_arena"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def assign_constants(path: Path, names: set[str]) -> dict[str, object]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    out: dict[str, object] = {}
    for node in tree.body:
        targets: list[ast.expr] = []
        value = None
        if isinstance(node, ast.Assign):
            targets = list(node.targets)
            value = node.value
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            targets = [node.target]
            value = node.value
        for target in targets:
            if isinstance(target, ast.Name) and target.id in names:
                out[target.id] = ast.literal_eval(value)
    missing = names - set(out)
    if missing:
        raise SystemExit(f"missing constants {sorted(missing)} in {path}")
    return out


def main() -> int:
    gen = assign_constants(
        PAPER / "harness" / "generate_text.py",
        {
            "DEFAULT_MAX_NEW_TOKENS",
            "PUTNAM_MAX_NEW_TOKENS",
            "DEFAULT_TIMEOUT_SECONDS",
            "PUTNAM_TIMEOUT_SECONDS",
            "REQUESTED_PROVIDER",
            "REQUESTED_MODEL",
            "FAIL_CLOSED_KWARGS",
        },
    )
    run = assign_constants(
        PAPER / "harness" / "run_warmup.py",
        {
            "PROTOCOL",
            "LOOP_VERSION",
            "HARDWARE_CLASS",
            "TYPESAFE",
            "HAMMERS",
            "GATES",
            "TOKEN_WEIGHT",
            "ELAB_WEIGHT",
            "TOKENIZER_ID",
            "LIVE_SELF_CHECK_MAX_NEW_TOKENS",
        },
    )
    freeze = json.loads((PAPER / "evidence" / "run_freeze.json").read_text(encoding="utf-8"))
    jsonl = PAPER / "data" / "benchmark_data_warmup.jsonl"
    payload = {
        "ok": True,
        "arena_score": None,
        "official_score": None,
        "token_savings": None,
        "leaderboard_rank": None,
        "generate_text": gen,
        "run_warmup": run,
        "jsonl_sha256": sha256_file(jsonl),
        "jsonl_bytes": jsonl.stat().st_size,
        "prompt_sha256": sha256_file(PAPER / "harness" / "lra_prompt.txt"),
        "freeze": {
            "schema": freeze.get("schema"),
            "protocol": freeze.get("protocol"),
            "hardware_class": freeze.get("hardware_class"),
            "n_problems": freeze.get("n_problems"),
            "arena_score": freeze.get("arena_score"),
            "official_score": freeze.get("official_score"),
            "token_savings": freeze.get("token_savings"),
            "writes_arena_scores_into_manuscript": freeze.get("writes_arena_scores_into_manuscript"),
            "jsonl_sha256": freeze["jsonl"]["sha256"],
            "weight_revision": freeze["weight_identity"]["revision"],
            "weight_cid": freeze["weight_identity"]["cid"],
            "nvfp4_bytes": freeze["weight_identity"]["nvfp4_bytes"],
            "sm80_derivative_sha256": freeze["weight_identity"]["sm80_derivative_sha256"],
            "unpublished_sha_3fe4e64d_cited": freeze["weight_identity"]["unpublished_sha_3fe4e64d_cited"],
            "typesafe": freeze["typesafe"]["lra_typesafe"],
            "operator_argv": freeze["operator_command"]["argv"],
            "completing_argv": freeze["completion_authority"]["argv"],
        },
        "submissions_warmup_exists": (PAPER / "submissions" / "warmup").exists(),
        "main_tex_sha256": sha256_file(PAPER / "manuscript" / "main.tex"),
    }
    json.dump(payload, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
