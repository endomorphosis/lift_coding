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
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

HERE = Path(__file__).resolve().parent
PAPER_ROOT = HERE.parent
REPO_ROOT = HERE.parents[3]
WARMUP_JSONL = PAPER_ROOT / "data" / "benchmark_data_warmup.jsonl"

if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import splice as lra_splice  # noqa: E402

FROZEN_WARMUP_SHA256 = lra_splice.FROZEN_WARMUP_SHA256
WARMUP_N = lra_splice.WARMUP_N
NEIGHBOR_N = WARMUP_N - 1
SRC_LEMMA_CAP = 16
PROMPT_HEAD_CHARS = 400

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
FORBIDDEN_CORPUS_ATTRS = frozenset(
    {
        "CorpusManifest",
        "TheoremEntry",
        "GoalFeatures",
        "select_premises",
        "select_premises_for_theorem",
        "register_source",
        "ingest",
    }
)

# Character-class ident; not a Lean parser. Allows Unicode (ι) and dotted names.
_IDENT = re.compile(
    r"(?:[^\W\d])(?:[\w'])*(?:\.(?:[^\W\d])(?:[\w'])*)*",
    re.UNICODE,
)
_SIMP_RW_OPEN = re.compile(
    r"\b(?P<tactic>simp(?:_all|_rw)?(?:\s+only)?|rw!?|erw)\s*\[",
    re.UNICODE,
)
_EXACT_APPLY_OPEN = re.compile(
    r"\b(?P<tactic>exact'?|apply'?)\b\s*",
    re.UNICODE,
)
# Binders / tactic modifiers, not theorem names. Compared case-insensitively.
_STOPWORDS = frozenset(
    {
        "forall",
        "exists",
        "fun",
        "let",
        "in",
        "if",
        "then",
        "else",
        "do",
        "match",
        "with",
        "end",
        "where",
        "open",
        "import",
        "using",
        "from",
        "as",
        "return",
        "case",
        "of",
        "by",
        "have",
        "show",
        "this",
        "sorry",
        "admit",
        "at",
        "only",
        "all",
        "try",
        "first",
        "focus",
        "repeat",
        "skip",
        "next",
        "intro",
        "intros",
        "cases",
        "constructor",
        "refine",
        "apply",
        "exact",
        "simp",
        "rw",
        "erw",
        "simp_all",
        "simp_rw",
        "true",
        "false",
        "and",
        "or",
        "not",
        "some",
        "none",
        "generalizing",
        "hiding",
        "renaming",
        "calc",
        "suffices",
        "obtain",
        "rcases",
        "rintro",
        "all_goals",
        "any_goals",
    }
)


class RetrieveError(RuntimeError):
    """Fail-closed warm-up retrieval error."""


class UnknownProblem(RetrieveError):
    """The requested JSONL name is not in the frozen warm-up set."""


@dataclass(frozen=True)
class NeighborProof:
    name: str
    source: str
    statement: str
    src: str
    header: str
    file_path: str
    proof_length: int
    url: str

    @property
    def statement_head(self) -> str:
        return self.statement[:PROMPT_HEAD_CHARS]

    @property
    def proof_head(self) -> str:
        return self.src[:PROMPT_HEAD_CHARS]


@dataclass(frozen=True)
class SrcLemma:
    name: str
    tactic: str
    opener: str
    offset: int


@dataclass(frozen=True)
class Retrieval:
    query: str
    source: str
    neighbors: tuple[NeighborProof, ...]
    src_lemmas: tuple[SrcLemma, ...]
    lemma_ids: tuple[str, ...]
    lemma_id_digest: str
    n_src_lemmas_uncapped: int
    arena_score: None = None
    corpus_manifest_ingest: bool = False
    mathlib_ingest: bool = False


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

    if not isinstance(src, str):
        raise RetrieveError("src must be a string")
    events: list[tuple[int, str, re.Match[str]]] = []
    for match in _SIMP_RW_OPEN.finditer(src):
        events.append((match.start(), "list", match))
    for match in _EXACT_APPLY_OPEN.finditer(src):
        events.append((match.start(), "ident", match))
    events.sort(key=lambda item: item[0])

    from jevops.pick import unique_first

    lemmas: list[SrcLemma] = []
    for offset, kind, match in events:
        tactic = _tactic_family(match.group("tactic"))
        opener = match.group(0).strip()
        if kind == "list":
            inner = _bracket_inner(src, match.end())
            for ident_match in _IDENT.finditer(inner):
                lemmas.append(
                    SrcLemma(
                        name=ident_match.group(0),
                        tactic=tactic,
                        opener=opener,
                        offset=offset + ident_match.start(),
                    )
                )
            continue
        ident_match = _IDENT.match(src, match.end())
        if ident_match is None:
            continue
        lemmas.append(
            SrcLemma(
                name=ident_match.group(0),
                tactic=tactic,
                opener=opener,
                offset=ident_match.start(),
            )
        )
    if cap < 0:
        raise RetrieveError("src lemma cap must be non-negative")
    kept, uncapped = unique_first(lemmas, key_fn=lambda item: item.name, keep_fn=_keep_ident, cap=cap)
    return tuple(kept), uncapped


def jsonl_neighbors(
    records: Sequence[Mapping[str, Any]],
    query_name: str,
) -> tuple[NeighborProof, ...]:
    """Return the other 14 warm-up proofs in JSONL order. Never the query."""

    from jevops.outer import exclude_named
    from jevops.outer import unique_names

    if not query_name:
        raise RetrieveError("query name is empty")
    names = unique_names(records)
    if len(names) != WARMUP_N or len(set(names)) != WARMUP_N:
        raise RetrieveError(f"warmup JSONL must contain {WARMUP_N} uniquely named records")
    if query_name not in names:
        raise UnknownProblem(f"unknown warm-up problem: {query_name}")
    neighbors: list[NeighborProof] = []
    for record in exclude_named(records, query_name):
        name = str(record.get("name") or "")
        statement = record.get("statement")
        src = record.get("src")
        if not isinstance(statement, str) or not statement:
            raise RetrieveError(f"{name}: statement must be a non-empty string")
        if not isinstance(src, str) or not src:
            raise RetrieveError(f"{name}: src must be a non-empty string")
        if not src.startswith(statement):
            raise RetrieveError(f"{name}: src does not start with the frozen statement")
        header = record.get("header") or ""
        file_path = record.get("file_path") or ""
        url = record.get("url") or ""
        neighbors.append(
            NeighborProof(
                name=name,
                source=str(record.get("source") or ""),
                statement=statement,
                src=src,
                header=header if isinstance(header, str) else "",
                file_path=file_path if isinstance(file_path, str) else "",
                proof_length=int(record.get("proof_length") or 0),
                url=url if isinstance(url, str) else "",
            )
        )
    if len(neighbors) != NEIGHBOR_N:
        raise RetrieveError(f"{query_name}: expected {NEIGHBOR_N} neighbors, got {len(neighbors)}")
    if any(item.name == query_name for item in neighbors):
        raise RetrieveError(f"{query_name}: neighbor table includes the query")
    return tuple(neighbors)


def lemma_id_digest(query: str, neighbor_names: Sequence[str], lemma_names: Sequence[str]) -> str:
    """Content digest of retrieved lemma ids. Not a score."""

    payload = {
        "cap": SRC_LEMMA_CAP,
        "n_jsonl_neighbors": NEIGHBOR_N,
        "neighbors": list(neighbor_names),
        "query": query,
        "src_lemmas": list(lemma_names),
    }
    from jevops.outer import digest_canonical

    return digest_canonical(payload)


def retrieve_record(record: Mapping[str, Any], records: Sequence[Mapping[str, Any]]) -> Retrieval:
    name = str(record.get("name") or "")
    src = record.get("src")
    if not isinstance(src, str) or not src:
        raise RetrieveError(f"{name}: src must be a non-empty string")
    neighbors = jsonl_neighbors(records, name)
    src_lemmas, uncapped = extract_src_lemmas(src, cap=SRC_LEMMA_CAP)
    neighbor_names = tuple(item.name for item in neighbors)
    lemma_names = tuple(item.name for item in src_lemmas)
    lemma_ids = tuple(f"jsonl:{item}" for item in neighbor_names) + tuple(
        f"src:{item}" for item in lemma_names
    )
    return Retrieval(
        query=name,
        source=str(record.get("source") or ""),
        neighbors=neighbors,
        src_lemmas=src_lemmas,
        lemma_ids=lemma_ids,
        lemma_id_digest=lemma_id_digest(name, neighbor_names, lemma_names),
        n_src_lemmas_uncapped=uncapped,
        arena_score=None,
        corpus_manifest_ingest=False,
        mathlib_ingest=False,
    )


def retrieve_by_name(
    name: str,
    records: Optional[Sequence[Mapping[str, Any]]] = None,
    *,
    path: Optional[Path] = None,
) -> Retrieval:
    from jevops.outer import lookup_named

    if records is None:
        _, _, records = load_warmup_records(path)
    record = lookup_named(records, name)
    if record is None:
        raise UnknownProblem(f"unknown warm-up problem: {name}")
    return retrieve_record(record, records)


def prompt_neighbors(retrieval: Retrieval, *, k: int = 4) -> list[dict[str, str]]:
    """TypeSafe neighbor slice from the design: name / statement[:400] / proof_head."""

    from jevops.pick import project_items

    return project_items(
        retrieval.neighbors[:k],
        {
            "name": "name",
            "statement": "statement_head",
            "proof_head": "proof_head",
        },
    )


def retrieval_view(retrieval: Retrieval, *, src_chars: int = PROMPT_HEAD_CHARS) -> dict[str, Any]:
    """JSON view with truncated proofs. Full ``src`` stays on the dataclass."""

    return {
        "query": retrieval.query,
        "source": retrieval.source,
        "n_neighbors": len(retrieval.neighbors),
        "n_src_lemmas": len(retrieval.src_lemmas),
        "n_src_lemmas_uncapped": retrieval.n_src_lemmas_uncapped,
        "src_lemma_cap": SRC_LEMMA_CAP,
        "neighbors": [
            {
                "name": item.name,
                "source": item.source,
                "statement": item.statement[:src_chars],
                "proof_head": item.src[:src_chars],
                "file_path": item.file_path,
                "url": item.url,
                "proof_length": item.proof_length,
                "src_chars": len(item.src),
                "retrieved_full_src": True,
            }
            for item in retrieval.neighbors
        ],
        "src_lemmas": [asdict(item) for item in retrieval.src_lemmas],
        "lemma_ids": list(retrieval.lemma_ids),
        "lemma_id_digest": retrieval.lemma_id_digest,
        "prompt_neighbors": prompt_neighbors(retrieval),
        "arena_score": retrieval.arena_score,
        "corpus_manifest_ingest": retrieval.corpus_manifest_ingest,
        "mathlib_ingest": retrieval.mathlib_ingest,
        "score": None,
        "relevance_score": None,
    }


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
    names = [f"Lemma_{index:02d}" for index in range(20)]
    src = "theorem T : True := by\n  simp [" + ", ".join(names) + "]\n  exact Lemma_00\n  apply ExtraIdent"
    lemmas, uncapped = extract_src_lemmas(src, cap=SRC_LEMMA_CAP)
    lemma_names = [item.name for item in lemmas]
    return {
        "uncapped": uncapped,
        "returned": len(lemmas),
        "names": lemma_names,
        "first": lemma_names[0] if lemma_names else "",
        "last": lemma_names[-1] if lemma_names else "",
        "includes_extra_apply": "ExtraIdent" in lemma_names,
        "tactics": sorted({item.tactic for item in lemmas}),
        "capped_at_16": len(lemmas) == SRC_LEMMA_CAP and lemma_names == names[:SRC_LEMMA_CAP],
        "uncapped_has_all_twenty_plus_extra": uncapped == 21,
    }


def _record_report(record: Mapping[str, Any], records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    retrieval = retrieve_record(record, records)
    neighbor_names = [item.name for item in retrieval.neighbors]
    all_names = [str(item.get("name") or "") for item in records]
    expected = [name for name in all_names if name != retrieval.query]
    lemma_in_src = all(item.name in record["src"] for item in retrieval.src_lemmas)
    tactics = sorted({item.tactic for item in retrieval.src_lemmas})
    families = {item.tactic for item in retrieval.src_lemmas}
    return {
        "name": retrieval.query,
        "source": retrieval.source,
        "n_neighbors": len(retrieval.neighbors),
        "neighbor_names": neighbor_names,
        "neighbors_are_the_other_fourteen": neighbor_names == expected,
        "self_excluded": retrieval.query not in neighbor_names,
        "full_src_retrieved": all(item.src == next(r["src"] for r in records if r["name"] == item.name) for item in retrieval.neighbors),
        "prefix_bind_neighbors": all(item.src.startswith(item.statement) for item in retrieval.neighbors),
        "n_src_lemmas": len(retrieval.src_lemmas),
        "n_src_lemmas_uncapped": retrieval.n_src_lemmas_uncapped,
        "src_lemma_cap_held": len(retrieval.src_lemmas) <= SRC_LEMMA_CAP,
        "src_lemmas": [asdict(item) for item in retrieval.src_lemmas],
        "src_lemma_names": [item.name for item in retrieval.src_lemmas],
        "src_lemma_tactics": tactics,
        "has_simp": "simp" in families,
        "has_rw": "rw" in families,
        "has_exact": "exact" in families,
        "has_apply": "apply" in families,
        "lemmas_mentioned_in_src": lemma_in_src,
        "lemma_id_digest": retrieval.lemma_id_digest,
        "lemma_id_digest_hex64": len(retrieval.lemma_id_digest) == 64,
        "n_lemma_ids": len(retrieval.lemma_ids),
        "arena_score": retrieval.arena_score,
        "score": None,
        "relevance_score": None,
        "corpus_manifest_ingest": retrieval.corpus_manifest_ingest,
        "mathlib_ingest": retrieval.mathlib_ingest,
        "prompt_neighbor_names": [item["name"] for item in prompt_neighbors(retrieval)],
    }


def self_check(path: Optional[Path] = None) -> dict[str, Any]:
    """Retrieve 14 JSONL neighbors + src lemmas for all 15 records. No compile."""

    source = Path(__file__).read_text(encoding="utf-8")
    jsonl = Path(path) if path is not None else WARMUP_JSONL
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

    all_names = [str(record.get("name") or "") for record in records]
    neighbor_cover = all(item["neighbors_are_the_other_fourteen"] and item["self_excluded"] for item in per_record)
    full_src = all(item["full_src_retrieved"] and item["prefix_bind_neighbors"] for item in per_record)
    lemmas_ok = all(item["lemmas_mentioned_in_src"] and item["src_lemma_cap_held"] for item in per_record)
    has_simp = any(item["has_simp"] for item in per_record)
    has_rw = any(item["has_rw"] for item in per_record)
    has_exact = any(item["has_exact"] for item in per_record)
    no_scores = all(
        item["arena_score"] is None and item["score"] is None and item["relevance_score"] is None
        for item in per_record
    )
    no_manifest = all(item["corpus_manifest_ingest"] is False and item["mathlib_ingest"] is False for item in per_record)
    n_neighbors_ok = all(item["n_neighbors"] == NEIGHBOR_N for item in per_record)
    unknown_closed = False
    try:
        retrieve_by_name("not-a-warmup-problem", records)
    except UnknownProblem:
        unknown_closed = True

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
        "called_select_premises": "select_premises" in call_names or "select_premises_for_theorem" in call_names,
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
        "warmup_path": str(jsonl.relative_to(REPO_ROOT)),
        "protocol": "LRA/v1",
        "loop": "v2-deferred-retrieve-only",
    }
    report["ok"] = bool(
        report["n_records"] == WARMUP_N
        and report["jsonl_unchanged"]
        and neighbor_cover
        and n_neighbors_ok
        and full_src
        and lemmas_ok
        and has_simp
        and has_rw
        and has_exact
        and cap_fixture["capped_at_16"]
        and unknown_closed
        and not forbidden_imports
        and not corpus_attrs
        and not report["called_select_premises"]
        and not report["uses_fcntl"]
        and not uses_lock_ex
        and not uses_subprocess
        and no_scores
        and not score_issues
        and no_manifest
        and report["compiled"] is False
        and report["lake"] is False
        and report["arena_score"] is None
        and report["score"] is None
    )
    return report


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
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.retrieve:
        if not args.name:
            parser.error("--retrieve requires --name")
        try:
            retrieval = retrieve_by_name(args.name, path=args.jsonl)
        except RetrieveError as exc:
            json.dump(
                {
                    "ok": False,
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                    "arena_score": None,
                    "score": None,
                    "corpus_manifest_ingest": False,
                },
                sys.stdout,
                indent=2,
                sort_keys=True,
            )
            sys.stdout.write("\n")
            return 1
        json.dump(retrieval_view(retrieval, src_chars=args.src_chars), sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        return 0
    if args.self_check or argv is None or argv == []:
        report = self_check(args.jsonl)
        json.dump(report, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        return 0 if report["ok"] else 1
    parser.error("choose --self-check or --retrieve")
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
