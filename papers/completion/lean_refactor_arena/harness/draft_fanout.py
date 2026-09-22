#!/usr/bin/env python3
"""AST-ish tactic draft enumerator plus one TypeSafe Choice-over-ids call.

Walks the reference tactic block for ``case`` spans and simp/have/calc lines,
emits deterministic rewrite drafts, then ranks them with one System One
request. Jev does not generate Lean. Lake is not the oracle on this path.
Not official Track 2. Not an Arena ranking. Never LOCK_EX.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

HERE = Path(__file__).resolve().parent
PAPER_ROOT = HERE.parent
REPO_ROOT = HERE.parents[3]
WARMUP_JSONL = PAPER_ROOT / "data" / "benchmark_data_warmup.jsonl"
OUT_DEFAULT = PAPER_ROOT / "evidence" / "canaries"

if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import _jevops_path  # noqa: E402,F401
import retrieve as lra_retrieve  # noqa: E402
import splice as lra_splice  # noqa: E402
from jevops.catalogs import ACCEL_ROOT as ROOT_ACCEL
from jevops.catalogs import CANARY_NAMES
from jevops.catalogs import CASE_REPLACE_CAP
from jevops.catalogs import TYPESAFE_KEYFILE as KEYFILE
from jevops.catalogs import MAX_CHOICE_OPTIONS
from jevops.catalogs import MAX_DRAFTS
from jevops.catalogs import NEIGHBOR_DRAFT_CAP
from jevops.catalogs import NEIGHBOR_HEAD_LINES
from jevops.catalogs import PROTOCOL
from jevops.catalogs import STATEMENT_CHARS

FROZEN_WARMUP_SHA256 = lra_splice.FROZEN_WARMUP_SHA256
WARMUP_N = lra_splice.WARMUP_N
PR_ID = "PR-9b"
LRAH_ID = "LRAH-006b"
from jevops.catalogs import DRAFT_HEAD_CHARS as HEAD_CHARS
from jevops.catalogs import DRAFT_REF_HEAD_LINES as REF_HEAD_LINES
from jevops.tactics import HAMMER_BODIES
from jevops.catalogs import DRAFT_FANOUT_BEST
from jevops.catalogs import DRAFT_FANOUT_NOULS
from jevops.catalogs import LIKELY_SHORTER_CRITERIA
from jevops.tactics import CALC as _CALC
from jevops.tactics import CASE as _CASE
from jevops.tactics import HAVE_OBTAIN as _HAVE_OBTAIN
from jevops.tactics import SIMP_AT as _SIMP_AT
from jevops.tactics import CaseSpan as CaseSpan
FORBIDDEN_IMPORT_NAMES = frozenset(
    {
        "fcntl",
        "generate_text",
        "llm_router",
        "LeanstralProofProvider",
        "typesafe_sdk",
    }
)


from jevops.tactics import Draft


def load_keyfile() -> None:
    from jevops.outer import load_env_file

    load_env_file(KEYFILE)


def pin_typesafe_path() -> None:
    from jevops.outer import pin_sys_path

    pin_sys_path(
        ROOT_ACCEL,
        defaults={
            "IPFS_ACCEL_SKIP_CORE": "1",
            "IPFS_AUTO_INSTALL": "false",
            "IPFS_ACCELERATE_LLAMA_CPP_AUTOSTART": "0",
        },
    )


def tactic_block(record: Mapping[str, Any]) -> str:
    split = lra_splice.split_statement_body(record)
    return lra_splice.tactic_block_from_body(split.body_suffix)


def case_spans(text: str) -> list[CaseSpan]:
    from jevops.tactics import case_spans as _fn

    return _fn(text)


def replace_case_body(text: str, span: CaseSpan, body: str) -> str:
    from jevops.tactics import replace_case_body as _fn

    return _fn(text, span, body)


def collapse_simp_at(text: str) -> str:
    from jevops.tactics import collapse_simp_at as _fn

    return _fn(text)


def drop_redundant_simp_at(text: str) -> str:
    """Delete a ``simp at`` run when the next tactic is already ``simp_all``."""

    from jevops.tactics import drop_redundant_simp_at as _fn

    return _fn(text)


def span_preserving_drafts(tactics: str) -> list[Draft]:
    """One-case edits that keep every ``case`` arm. Not whole-proof templates."""

    from jevops.tactics import span_preserving_edits

    drafts: list[Draft] = []
    seen: set[str] = set()
    for family, body, ops in span_preserving_edits(tactics):
        _push(drafts, seen, family, body, ops)
    return drafts


def drop_have_obtain(text: str) -> str:
    """Drop unused have/obtain/rename_i only. Keep destructuring and used binders."""

    from jevops.tactics import drop_have_obtain as _fn

    return _fn(text)


def first_case_only(text: str) -> str:
    from jevops.tactics import first_case_only as _fn

    return _fn(text)


def _draft_id(index: int) -> str:
    from jevops.pick import padded_id

    return padded_id(index)


def _push(drafts: list[Draft], seen: set[str], family: str, tactics: str, ops: Sequence[str]) -> None:
    from jevops.tactics import push_draft

    push_draft(drafts, seen, family, tactics, ops, cap=MAX_DRAFTS, head_chars=HEAD_CHARS)


def neighbor_tactic_head(record: Mapping[str, Any], *, n_lines: int = NEIGHBOR_HEAD_LINES) -> str:
    try:
        block = tactic_block(record)
    except Exception:
        return ""
    from jevops.outer import head_lines

    return head_lines(block, n_lines)


def enumerate_drafts(
    record: Mapping[str, Any],
    records: Sequence[Mapping[str, Any]],
) -> list[Draft]:
    """Deterministic drafts from the reference tactic tree. Not a Lean parser."""

    reference = tactic_block(record)
    from jevops.tactics import closed_tree_edits, collect_tree_drafts, neighbor_style_ops

    retrieval = lra_retrieve.retrieve_record(record, records)
    neighbors = lra_retrieve.prompt_neighbors(retrieval, k=NEIGHBOR_DRAFT_CAP)
    by_name = {item.get("name"): item for item in records}
    return collect_tree_drafts(
        closed_edits=closed_tree_edits(reference, case_replace_cap=CASE_REPLACE_CAP),
        neighbor_ops=neighbor_style_ops(neighbors, by_name, head_fn=neighbor_tactic_head),
        push_fn=_push,
        cap=MAX_DRAFTS,
    )


def draft_catalog(drafts: Sequence[Draft]) -> list[dict[str, Any]]:
    from jevops.pick import project_items

    return project_items(
        drafts,
        {
            "id": "draft_id",
            "family": "family",
            "ops": lambda item: list(item.ops),
            "n_chars": "n_chars",
            "head": "head",
        },
    )


def fanout_state(
    record: Mapping[str, Any],
    drafts: Sequence[Draft],
) -> dict[str, Any]:
    from jevops.jev import fanout_problem_state
    from jevops.outer import get_list, get_str

    split = lra_splice.split_statement_body(record)
    tactics = lra_splice.tactic_block_from_body(split.body_suffix)
    ref_lines = tactics.splitlines()
    return fanout_problem_state(
        record,
        statement_n=STATEMENT_CHARS,
        problem={
            "name": get_str(record, "name"),
            "source": get_str(record, "source"),
            "n_toolchains": len(get_list(record, "version_info")),
            "proof_length": record.get("proof_length"),
            "num_lines": record.get("num_lines"),
        },
        extra={
            "reference_head": "\n".join(ref_lines[:REF_HEAD_LINES]),
            "drafts": draft_catalog(drafts),
        },
    )


def fanout_questions(drafts: Sequence[Draft], *, Choice: Any, Noul: Any, Score: Any) -> dict[str, Any]:
    from jevops.jev import choice_questions, draft_criteria, require_choice_cap

    require_choice_cap(len(drafts), MAX_CHOICE_OPTIONS)
    return choice_questions(
        Choice=Choice,
        Noul=Noul,
        Score=Score,
        criteria=draft_criteria(drafts),
        best_instructions=DRAFT_FANOUT_BEST,
        nouls=DRAFT_FANOUT_NOULS,
        scores={
            "likely_token_cut": (
                "How large a source-token cut is plausible if the best draft replaces the reference?",
                list(LIKELY_SHORTER_CRITERIA),
            )
        },
    )


def redact(payload: Any) -> Any:
    from jevops.jev import redact as _fn

    return _fn(payload)


def rank_choice(probabilities: Mapping[str, Any], drafts: Sequence[Draft], *, k: int = 8) -> list[dict[str, Any]]:
    from jevops.pick import attach_ranked, rank_by_prob

    return attach_ranked(
        rank_by_prob(probabilities, k=k),
        {item.draft_id: item for item in drafts},
        {
            "family": "family",
            "ops": lambda item: list(item.ops),
            "n_chars": "n_chars",
            "head": "head",
        },
    )


def rank_problem(record: Mapping[str, Any], records: Sequence[Mapping[str, Any]], *, live: bool) -> dict[str, Any]:
    from jevops.jev import invoke_system_one, rank_catalog_or_live, unpack_response
    from jevops.outer import dumps_sorted, overlay_map, unless_flag

    drafts = enumerate_drafts(record, records)
    state = fanout_state(record, drafts)
    families = [{"family": fam} for fam in sorted({item.family for item in drafts})]

    def _project(result: Any, wall_ms: float) -> dict[str, Any]:
        from jevops.jev import pack_fanout_live_row

        return pack_fanout_live_row(
            result,
            wall_ms,
            unpack_fn=unpack_response,
            rank_fn=rank_choice,
            drafts=drafts,
        )

    def _invoke() -> tuple[Any, float]:
        from jevops.jev import load_typesafe_inference

        loaded = load_typesafe_inference(setup=(pin_typesafe_path,), fallback=False)
        Choice, Noul, Score, TypeSafeClient = (
            loaded["Choice"],
            loaded["Noul"],
            loaded["Score"],
            loaded["TypeSafeClient"],
        )
        questions = fanout_questions(drafts, Choice=Choice, Noul=Noul, Score=Score)
        return invoke_system_one(TypeSafeClient(timeout=60.0), state, questions)

    def _configured() -> bool:
        from jevops.jev import typesafe_is_configured

        return typesafe_is_configured(setup=(pin_typesafe_path,), fallback=False)

    return rank_catalog_or_live(
        record,
        drafts=drafts,
        families=families,
        features={},
        live=live,
        extra=overlay_map(
            {
                "n_case_spans": len(case_spans(tactic_block(record))),
                "state_chars": len(dumps_sorted(state)),
                "compile_attempted": False,
            },
            **unless_flag(live, {"catalog": draft_catalog(drafts)}),
        ),
        catalog_fn=lambda: draft_catalog(drafts),
        pin_fn=pin_typesafe_path,
        configured_fn=_configured,
        invoke_fn=_invoke,
        project_fn=_project,
        redact_fn=redact,
    )


def audit_source(source: Optional[str] = None) -> dict[str, Any]:
    from jevops.outer import source_text
    from jevops.repair import audit_source as _audit

    text = source_text(source, path=__file__)
    out = _audit(text, forbidden_imports=FORBIDDEN_IMPORT_NAMES)
    imported = set(out["imported_names"])
    return {
        "forbidden_imports": out["forbidden_imports"],
        "uses_lock_ex": out["uses_lock_ex"],
        "ok": not out["uses_lock_ex"]
        and "generate_text" not in imported
        and "typesafe_sdk" not in imported,
    }


def self_check(path: Optional[Path] = None) -> dict[str, Any]:
    from jevops.outer import digest_file, path_or

    jsonl = path_or(path, WARMUP_JSONL)

    before = digest_file(jsonl)
    _raw, digest, records = lra_splice.load_warmup_records(jsonl)
    after = digest_file(jsonl)
    audit = audit_source()
    from jevops.outer import all_rows, any_in, finalize_ok, lookup_named

    rows = [
        rank_problem(
            lookup_named(records, name, error_cls=RuntimeError, miss=f"unknown warm-up problem: {name}"),
            records,
            live=False,
        )
        for name in CANARY_NAMES
    ]
    return finalize_ok(
        {
            "protocol": PROTOCOL,
            "pr": PR_ID,
            "lrah": LRAH_ID,
            "frozen_warmup_sha256": FROZEN_WARMUP_SHA256,
            "warmup_jsonl_sha256": digest,
            "jsonl_unchanged": before == after == FROZEN_WARMUP_SHA256,
            "audit": audit,
            "max_drafts": MAX_DRAFTS,
            "max_choice_options": MAX_CHOICE_OPTIONS,
            "jev_generated_lean": False,
            "arena_score": None,
            "canaries": rows,
        },
        audit["ok"],
        before == after == FROZEN_WARMUP_SHA256,
        all_rows(rows, lambda row: row["n_drafts"] >= 6),
        all_rows(rows, lambda row: row["draft_ids"][0] == "d000"),
        all_rows(rows, lambda row: "reference" in row["families"]),
        all_rows(rows, lambda row: any_in(row["families"], ("simp_set", "aesop"))),
        all_rows(rows, lambda row: row["n_drafts"] <= MAX_CHOICE_OPTIONS),
    )


def live_rank(names: Sequence[str], path: Optional[Path] = None) -> dict[str, Any]:
    from jevops.outer import pin_calls

    pin_calls(load_keyfile, pin_typesafe_path)()
    from jevops.outer import path_or

    jsonl = path_or(path, WARMUP_JSONL)
    _raw, digest, records = lra_splice.load_warmup_records(jsonl)
    started = time.perf_counter()
    from jevops.outer import elapsed_ms, pack_live_rank, rank_named_rows

    rows = rank_named_rows(
        names, records, lambda record: rank_problem(record, records, live=True)
    )
    return pack_live_rank(
        schema="lra-draft-fanout/v1",
        digest=digest,
        canaries=rows,
        wall_ms=elapsed_ms(started),
        extra={
            "protocol": PROTOCOL,
            "pr": PR_ID,
            "frozen_warmup_sha256": FROZEN_WARMUP_SHA256,
            "compile_attempted": False,
        },
        redact_fn=redact,
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-check", action="store_true")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--names", default=",".join(CANARY_NAMES))
    parser.add_argument("--jsonl", type=Path, default=None)
    parser.add_argument("--out", type=Path, default=OUT_DEFAULT)
    from jevops.outer import list_or_none

    args = parser.parse_args(list_or_none(argv))
    if args.self_check or not args.live:
        report = self_check(args.jsonl)
        from jevops.outer import print_ok

        return print_ok(report)
    from jevops.outer import split_csv, write_json_pair

    names = split_csv(args.names)
    report = live_rank(names, args.jsonl)
    latest = write_json_pair(
        args.out,
        report,
        prefix="draft-fanout",
        latest="draft-fanout-latest.json",
        refuse="apikey_",
    )
    from jevops.outer import or_list, print_json, text_or

    print_json(
        {
            "ok": all(row.get("live") for row in or_list(report.get("canaries"), [])),
            "latest": text_or(latest),
            "n": len(or_list(report.get("canaries"), [])),
            "picks": [
                {"name": row.get("name"), "best": row.get("best_first_draft"), "n_drafts": row.get("n_drafts"), "wall_ms": row.get("wall_ms")}
                for row in or_list(report.get("canaries"), [])
            ],
            "arena_score": None,
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
