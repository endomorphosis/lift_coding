#!/usr/bin/env python3
"""Premise retrieval from the other 14 warm-up JSONL proofs plus src lemmas.

Warm-up v1 retrieval is only:

- the other 14 public JSONL records (never the query itself);
- lemma names mentioned in the current ``src`` via regex on ``simp [`` /
  ``rw [`` / the identifier after ``exact`` / ``apply``.

Src lemmas are capped at 16. This is not a Lean parser, not lake-wide
ingest, and not a ``CorpusManifest`` of Mathlib. No embeddings, no Jev, no
invented scores. Loop v2 / PR-6 deferred path; not a scored Arena run.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

HERE = Path(__file__).resolve().parent
PAPER_ROOT = HERE.parent
REPO_ROOT = HERE.parents[3]
WARMUP_JSONL = PAPER_ROOT / "data" / "benchmark_data_warmup.jsonl"

if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import _jevops_path  # noqa: E402,F401
import splice as lra_splice  # noqa: E402

FROZEN_WARMUP_SHA256 = lra_splice.FROZEN_WARMUP_SHA256
WARMUP_N = lra_splice.WARMUP_N
NEIGHBOR_N = WARMUP_N - 1
from jevops.catalogs import FORBIDDEN_CORPUS_ATTRS
from jevops.catalogs import PROMPT_HEAD_CHARS
from jevops.catalogs import SRC_LEMMA_CAP

FORBIDDEN_IMPORT_NAMES = frozenset(
    {
        "fcntl",
        "LeanstralProofProvider",
        "leanstral_proof_provider",
        "CorpusManifest",
        "TheoremEntry",
        "GoalFeatures",
        "PremiseSelectionWeights",
        "PremiseSelectionResult",
        "select_premises",
        "select_premises_for_theorem",
        "premise_selection",
        "ipfs_datasets",
        "ipfs_datasets_py",
    }
)

from jevops.tactics import EXACT_APPLY_OPEN as _EXACT_APPLY_OPEN
from jevops.tactics import IDENT as _IDENT
from jevops.tactics import LEMMA_STOPWORDS as _STOPWORDS
from jevops.tactics import SIMP_RW_OPEN as _SIMP_RW_OPEN


class RetrieveError(RuntimeError):
    """Fail-closed warm-up retrieval error."""


class UnknownProblem(RetrieveError):
    """The requested JSONL name is not in the frozen warm-up set."""


from jevops.lean import NeighborProof
from jevops.lean import Retrieval
from jevops.tactics import SrcLemma


def sha256_bytes(data: bytes) -> str:
    from jevops.outer import digest_hex

    return digest_hex(data)


def sha256_file(path: Path) -> str:
    from jevops.outer import digest_file

    return digest_file(path)


def load_warmup_records(path: Optional[Path] = None) -> tuple[bytes, str, list[dict[str, Any]]]:
    """Load the frozen warm-up JSONL through the LRA-011 splice bind."""

    return lra_splice.load_warmup_records(path)


def _tactic_family(opener: str) -> str:
    from jevops.outer import token_family

    return token_family(
        opener,
        prefixes=("simp", "exact", "apply"),
        aliases={"rw": "rw", "erw": "rw"},
    )


def _bracket_inner(text: str, open_end: int) -> str:
    """Take the substring of a ``[…]`` list by character depth. Not a Lean parser."""

    from jevops.mask import bracket_inner

    return bracket_inner(text, open_end)


def _keep_ident(name: str) -> bool:
    from jevops.pick import keep_token

    return keep_token(name, stopwords=_STOPWORDS, min_len=2)


def extract_src_lemmas(src: str, *, cap: int = SRC_LEMMA_CAP) -> tuple[tuple[SrcLemma, ...], int]:
    """Regex-extract lemma idents from ``simp [`` / ``rw [`` / ``exact`` / ``apply``.

    Does not parse Lean. Unique names, first-occurrence order, then cap.
    """

    from jevops.tactics import extract_src_lemmas as _fn

    return _fn(src, cap=cap, error_cls=RetrieveError)


def jsonl_neighbors(
    records: Sequence[Mapping[str, Any]],
    query_name: str,
) -> tuple[NeighborProof, ...]:
    """Return the other 14 warm-up proofs in JSONL order. Never the query."""

    from jevops.lean import jsonl_neighbors as _fn

    return _fn(
        records,
        query_name,
        expected_n=WARMUP_N,
        neighbor_n=NEIGHBOR_N,
        error_cls=RetrieveError,
        unknown_cls=UnknownProblem,
        head_chars=PROMPT_HEAD_CHARS,
    )


def lemma_id_digest(query: str, neighbor_names: Sequence[str], lemma_names: Sequence[str]) -> str:
    """Content digest of retrieved lemma ids. Not a score."""

    from jevops.lean import lemma_id_digest as _fn

    return _fn(query, neighbor_names, lemma_names, cap=SRC_LEMMA_CAP, neighbor_n=NEIGHBOR_N)


def retrieve_record(record: Mapping[str, Any], records: Sequence[Mapping[str, Any]]) -> Retrieval:
    from jevops.lean import retrieve_record as _fn

    return _fn(
        record,
        records,
        expected_n=WARMUP_N,
        neighbor_n=NEIGHBOR_N,
        lemma_cap=SRC_LEMMA_CAP,
        error_cls=RetrieveError,
        unknown_cls=UnknownProblem,
        head_chars=PROMPT_HEAD_CHARS,
    )


def retrieve_by_name(
    name: str,
    records: Optional[Sequence[Mapping[str, Any]]] = None,
    *,
    path: Optional[Path] = None,
) -> Retrieval:
    from jevops.outer import either, load_named_pack, lookup_named

    record, records, _digest = either(
        records is None,
        lambda: load_named_pack(
            load_warmup_records,
            name,
            error_cls=UnknownProblem,
            miss=f"unknown warm-up problem: {name}",
            extra=path,
        ),
        lambda: (
            lookup_named(records, name, error_cls=UnknownProblem, miss=f"unknown warm-up problem: {name}"),
            records,
            None,
        ),
    )
    return retrieve_record(record, records)


def prompt_neighbors(retrieval: Retrieval, *, k: int = 4) -> list[dict[str, str]]:
    """TypeSafe neighbor slice from the design: name / statement[:400] / proof_head."""

    from jevops.lean import prompt_neighbors as _fn

    return _fn(retrieval, k=k)


def retrieval_view(retrieval: Retrieval, *, src_chars: int = PROMPT_HEAD_CHARS) -> dict[str, Any]:
    """JSON view with truncated proofs. Full ``src`` stays on the dataclass."""

    from jevops.lean import retrieval_view as _fn

    return _fn(retrieval, src_chars=src_chars, lemma_cap=SRC_LEMMA_CAP)


def _imported_names(source: str) -> set[str]:
    from jevops.repair import imported_names

    return imported_names(source)


def _attr_names(source: str) -> set[str]:
    from jevops.repair import attr_names

    return attr_names(source)


def _call_func_names(source: str) -> set[str]:
    from jevops.repair import call_func_names

    return call_func_names(source)


def _numeric_score_assignments(source: str) -> list[str]:
    """Flag invented numeric scores. ``arena_score = None`` is allowed."""

    from jevops.repair import score_assignments

    return score_assignments(source, ("score", "relevance_score", "arena_score", "official_score"))


def _synthetic_cap_fixture() -> dict[str, Any]:
    from jevops.lean import pack_lemma_cap_fixture

    names = [f"Lemma_{index:02d}" for index in range(20)]
    src = "theorem T : True := by\n  simp [" + ", ".join(names) + "]\n  exact Lemma_00\n  apply ExtraIdent"
    lemmas, uncapped = extract_src_lemmas(src, cap=SRC_LEMMA_CAP)
    return pack_lemma_cap_fixture(
        names=names, lemmas=lemmas, uncapped=uncapped, cap=SRC_LEMMA_CAP
    )


def _record_report(record: Mapping[str, Any], records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    from jevops.lean import pack_retrieval_report

    retrieval = retrieve_record(record, records)
    return pack_retrieval_report(
        retrieval,
        records=records,
        lemma_cap=SRC_LEMMA_CAP,
        prompt_neighbors=prompt_neighbors(retrieval),
        asdict_fn=asdict,
    )


def self_check(path: Optional[Path] = None) -> dict[str, Any]:
    """Retrieve 14 JSONL neighbors + src lemmas for all 15 records. No compile."""

    from jevops.outer import read_text

    source = read_text(__file__)
    from jevops.outer import any_in, path_or, relative_or_str

    jsonl = path_or(path, WARMUP_JSONL)
    before = sha256_file(jsonl)
    raw, digest, records = load_warmup_records(jsonl)
    per_record = [_record_report(record, records) for record in records]
    after = sha256_file(jsonl)
    imported = _imported_names(source)
    forbidden_imports = sorted(name for name in imported if name in FORBIDDEN_IMPORT_NAMES)
    corpus_attrs = sorted(name for name in _attr_names(source) if name in FORBIDDEN_CORPUS_ATTRS)
    call_names = _call_func_names(source)
    score_issues = _numeric_score_assignments(source)
    uses_lock_ex = any(
        isinstance(node, ast.Attribute) and node.attr == "LOCK_EX" for node in ast.walk(ast.parse(source))
    )
    uses_subprocess = "subprocess" in imported
    cap_fixture = _synthetic_cap_fixture()

    from jevops.outer import all_rows, any_row, closed_on_error

    from jevops.outer import get_str, project_map

    all_names = project_map(records, lambda record: get_str(record, "name"))
    neighbor_cover = all_rows(
        per_record, lambda item: item["neighbors_are_the_other_fourteen"] and item["self_excluded"]
    )
    full_src = all_rows(
        per_record, lambda item: item["full_src_retrieved"] and item["prefix_bind_neighbors"]
    )
    lemmas_ok = all_rows(
        per_record, lambda item: item["lemmas_mentioned_in_src"] and item["src_lemma_cap_held"]
    )
    has_simp = any_row(per_record, lambda item: item["has_simp"])
    has_rw = any_row(per_record, lambda item: item["has_rw"])
    has_exact = any_row(per_record, lambda item: item["has_exact"])
    no_scores = all_rows(
        per_record,
        lambda item: item["arena_score"] is None and item["score"] is None and item["relevance_score"] is None,
    )
    no_manifest = all_rows(
        per_record, lambda item: item["corpus_manifest_ingest"] is False and item["mathlib_ingest"] is False
    )
    n_neighbors_ok = all_rows(per_record, lambda item: item["n_neighbors"] == NEIGHBOR_N)
    unknown_closed = closed_on_error(
        lambda: retrieve_by_name("not-a-warmup-problem", records),
        UnknownProblem,
    )

    report = {
        "ok": True,
        "n_records": len(records),
        "n_neighbors_per_query": NEIGHBOR_N,
        "src_lemma_cap": SRC_LEMMA_CAP,
        "frozen_warmup_sha256": FROZEN_WARMUP_SHA256,
        "warmup_jsonl_sha256": digest,
        "jsonl_bytes": len(raw),
        "jsonl_unchanged": before == after == FROZEN_WARMUP_SHA256,
        "names": all_names,
        "neighbor_cover_all": neighbor_cover,
        "n_neighbors_all_14": n_neighbors_ok,
        "full_neighbor_proofs_retrieved": full_src,
        "src_lemmas_from_simp_rw_exact_apply": lemmas_ok,
        "has_simp_lemma": has_simp,
        "has_rw_lemma": has_rw,
        "has_exact_lemma": has_exact,
        "cap_fixture": cap_fixture,
        "unknown_name_fail_closed": unknown_closed,
        "imported_names": sorted(imported),
        "forbidden_imports": forbidden_imports,
        "corpus_manifest_attrs": corpus_attrs,
        "called_select_premises": any_in(call_names, ("select_premises", "select_premises_for_theorem")),
        "uses_fcntl": "fcntl" in imported,
        "uses_lock_ex": uses_lock_ex,
        "uses_subprocess": uses_subprocess,
        "numeric_score_assignments": score_issues,
        "no_invented_scores": no_scores and not score_issues,
        "no_corpus_manifest_ingest": no_manifest and not forbidden_imports and not corpus_attrs,
        "records": per_record,
        "compiled": False,
        "lake": False,
        "llama_server_started": False,
        "arena_score": None,
        "score": None,
        "warmup_path": relative_or_str(jsonl, REPO_ROOT),
        "protocol": "LRA/v1",
        "loop": "v2-deferred-retrieve-only",
    }
    from jevops.outer import finalize_ok

    return finalize_ok(
        report,
        report["n_records"] == WARMUP_N,
        report["jsonl_unchanged"],
        neighbor_cover,
        n_neighbors_ok,
        full_src,
        lemmas_ok,
        has_simp,
        has_rw,
        has_exact,
        cap_fixture["capped_at_16"],
        unknown_closed,
        not forbidden_imports,
        not corpus_attrs,
        not report["called_select_premises"],
        not report["uses_fcntl"],
        not uses_lock_ex,
        not uses_subprocess,
        no_scores,
        not score_issues,
        no_manifest,
        report["compiled"] is False,
        report["lake"] is False,
        report["arena_score"] is None,
        report["score"] is None,
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-check", action="store_true", help="retrieve all 15 records; no compile")
    parser.add_argument("--retrieve", action="store_true", help="retrieve one warm-up problem by --name")
    parser.add_argument("--name", default="", help="JSONL problem name")
    parser.add_argument("--jsonl", type=Path, default=None, help="warmup JSONL path (default: frozen file)")
    parser.add_argument(
        "--src-chars",
        type=int,
        default=PROMPT_HEAD_CHARS,
        help="truncate neighbor statement/src in JSON output (full src is still retrieved)",
    )
    from jevops.outer import list_or_none

    args = parser.parse_args(list_or_none(argv))
    if args.retrieve:
        if not args.name:
            parser.error("--retrieve requires --name")
        try:
            retrieval = retrieve_by_name(args.name, path=args.jsonl)
        except RetrieveError as exc:
            from jevops.outer import failed_check, print_json

            print_json(failed_check(exc, score=None, corpus_manifest_ingest=False))
            return 1
        from jevops.outer import print_json

        print_json(retrieval_view(retrieval, src_chars=args.src_chars))
        return 0
    if args.self_check or argv is None or argv == []:
        from jevops.outer import print_ok

        return print_ok(self_check(args.jsonl))
    parser.error("choose --self-check or --retrieve")
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
