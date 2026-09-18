#!/usr/bin/env python3
"""AST-ish tactic draft enumerator plus one TypeSafe Choice-over-ids call.

Walks the reference tactic block for ``case`` spans and simp/have/calc lines,
emits deterministic rewrite drafts, then ranks them with one System One
request. Jev does not generate Lean. Lake is not the oracle on this path.
Not official Track 2. Not an Arena ranking. Never LOCK_EX.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

HERE = Path(__file__).resolve().parent
PAPER_ROOT = HERE.parent
REPO_ROOT = HERE.parents[3]
WARMUP_JSONL = PAPER_ROOT / "data" / "benchmark_data_warmup.jsonl"
ROOT_ACCEL = Path("/home/barberb/lift_coding/external/ipfs_accelerate")
KEYFILE = Path.home() / ".config/ipfs_accelerate_py/typesafe.env"
OUT_DEFAULT = PAPER_ROOT / "evidence" / "canaries"
CANARY_NAMES = (
    "CallElimCorrect.substOldPostSubset",
    "Cslib.CCS.bisimilarity_congr_choice",
)

if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import retrieve as lra_retrieve  # noqa: E402
import splice as lra_splice  # noqa: E402

FROZEN_WARMUP_SHA256 = lra_splice.FROZEN_WARMUP_SHA256
WARMUP_N = lra_splice.WARMUP_N
PROTOCOL = "LRA/v1"
PR_ID = "PR-9b"
LRAH_ID = "LRAH-006b"
MAX_DRAFTS = 48
MAX_CHOICE_OPTIONS = 255
HEAD_CHARS = 220
STATEMENT_CHARS = 480
REF_HEAD_LINES = 24
CASE_REPLACE_CAP = 8
NEIGHBOR_DRAFT_CAP = 3
NEIGHBOR_HEAD_LINES = 8
HAMMER_BODIES = (
    ("native_hammer", "rfl", ("template", "rfl")),
    ("native_hammer", "simp_all", ("template", "simp_all")),
    ("aesop", "aesop", ("template", "aesop")),
    ("omega_decide", "omega", ("template", "omega")),
)
LIKELY_SHORTER_CRITERIA = (
    "longer or same",
    "modest cut around 10 percent",
    "large cut of 30 percent or more",
)
_CASE = re.compile(r"^(?P<indent> *)case (?P<label>.+?) =>[ \t]*$", re.M)
_SIMP_AT = re.compile(r"^(?P<indent> *)simp at \S+\s*$")
_HAVE_OBTAIN = re.compile(r"^(?P<indent> *)(have |obtain |rename_i )")
_CALC = re.compile(r"^\s*calc\b", re.M)
FORBIDDEN_IMPORT_NAMES = frozenset(
    {
        "fcntl",
        "generate_text",
        "llm_router",
        "LeanstralProofProvider",
        "typesafe_sdk",
    }
)


@dataclass(frozen=True)
class CaseSpan:
    label: str
    start: int
    header_end: int
    end: int
    indent: int


@dataclass
class Draft:
    draft_id: str
    family: str
    tactics: str
    ops: tuple[str, ...] = ()
    n_chars: int = 0
    head: str = ""

    def __post_init__(self) -> None:
        tactics = str(self.tactics).strip("\n")
        object.__setattr__(self, "tactics", tactics)
        object.__setattr__(self, "n_chars", len(tactics))
        object.__setattr__(self, "head", tactics[:HEAD_CHARS])


def load_keyfile() -> None:
    if not KEYFILE.is_file():
        return
    for line in KEYFILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        os.environ.setdefault(name.strip(), value.strip())


def pin_typesafe_path() -> None:
    os.environ.setdefault("IPFS_ACCEL_SKIP_CORE", "1")
    os.environ.setdefault("IPFS_AUTO_INSTALL", "false")
    os.environ.setdefault("IPFS_ACCELERATE_LLAMA_CPP_AUTOSTART", "0")
    text = str(ROOT_ACCEL)
    if text in sys.path:
        sys.path.remove(text)
    sys.path.insert(0, text)


def tactic_block(record: Mapping[str, Any]) -> str:
    split = lra_splice.split_statement_body(record)
    return lra_splice.tactic_block_from_body(split.body_suffix)


def case_spans(text: str) -> list[CaseSpan]:
    matches = list(_CASE.finditer(text))
    spans: list[CaseSpan] = []
    for index, match in enumerate(matches):
        indent = len(match.group("indent"))
        end = len(text)
        for nxt in matches[index + 1 :]:
            if len(nxt.group("indent")) <= indent:
                end = nxt.start()
                break
        header_end = match.end()
        if header_end < len(text) and text[header_end] == "\n":
            header_end += 1
        spans.append(
            CaseSpan(
                label=str(match.group("label")),
                start=match.start(),
                header_end=header_end,
                end=end,
                indent=indent,
            )
        )
    return spans


def replace_case_body(text: str, span: CaseSpan, body: str) -> str:
    indent = " " * (span.indent + 2)
    replacement = indent + body.strip() + "\n"
    return text[: span.header_end] + replacement + text[span.end :]


def collapse_simp_at(text: str) -> str:
    lines = text.splitlines()
    out: list[str] = []
    index = 0
    while index < len(lines):
        match = _SIMP_AT.match(lines[index])
        if not match:
            out.append(lines[index])
            index += 1
            continue
        indent = match.group("indent")
        run = 0
        while index < len(lines) and _SIMP_AT.match(lines[index]) and lines[index].startswith(indent):
            run += 1
            index += 1
        if run >= 2:
            out.append(f"{indent}simp_all")
        else:
            out.append(lines[index - 1] if run == 1 else f"{indent}simp_all")
    return "\n".join(out)


def drop_redundant_simp_at(text: str) -> str:
    """Delete a ``simp at`` run when the next tactic is already ``simp_all``."""

    lines = text.splitlines()
    out: list[str] = []
    index = 0
    while index < len(lines):
        match = _SIMP_AT.match(lines[index])
        if not match:
            out.append(lines[index])
            index += 1
            continue
        indent = match.group("indent")
        run_end = index
        while run_end < len(lines) and _SIMP_AT.match(lines[run_end]) and lines[run_end].startswith(indent):
            run_end += 1
        skip = run_end
        while skip < len(lines) and not lines[skip].strip():
            skip += 1
        following = lines[skip].strip() if skip < len(lines) else ""
        # A single ``simp at hyp`` immediately before ``simp_all`` is also residual.
        if run_end > index and following.startswith("simp_all"):
            index = run_end
            continue
        if run_end - index >= 2:
            out.append(f"{indent}simp_all")
            index = run_end
            continue
        out.append(lines[index])
        index += 1
    return "\n".join(out)


def span_preserving_drafts(tactics: str) -> list[Draft]:
    """One-case edits that keep every ``case`` arm. Not whole-proof templates."""

    drafts: list[Draft] = []
    seen: set[str] = set()
    spans = case_spans(tactics)
    if not spans:
        whole = drop_redundant_simp_at(tactics)
        _push(drafts, seen, "simp_set", whole, ("drop_redundant_simp_at", "whole"))
        return drafts
    top = min(span.indent for span in spans)
    for span in spans:
        if span.indent != top:
            continue
        body = tactics[span.header_end : span.end]
        collapsed = drop_redundant_simp_at(body)
        if collapsed != body:
            merged = tactics[: span.header_end] + collapsed + tactics[span.end :]
            _push(
                drafts,
                seen,
                "simp_set",
                merged,
                ("drop_redundant_simp_at", "case", span.label),
            )
        dropped = drop_have_obtain(body)
        if dropped != body:
            merged = tactics[: span.header_end] + dropped + tactics[span.end :]
            _push(
                drafts,
                seen,
                "have_chain",
                merged,
                ("drop_have_obtain", "case", span.label),
            )
    whole = drop_redundant_simp_at(tactics)
    _push(drafts, seen, "simp_set", whole, ("drop_redundant_simp_at", "all_cases"))
    return drafts


def drop_have_obtain(text: str) -> str:
    """Drop unused have/obtain/rename_i only. Keep destructuring and used binders."""

    import binder_use as lra_bind

    return lra_bind.drop_unused_binders(text, kinds=("rename_i", "have", "obtain"))


def first_case_only(text: str) -> str:
    spans = case_spans(text)
    if not spans:
        return text
    first = spans[0]
    return text[: first.end].rstrip() + "\n"


def _draft_id(index: int) -> str:
    return f"d{index:03d}"


def _push(drafts: list[Draft], seen: set[str], family: str, tactics: str, ops: Sequence[str]) -> None:
    body = tactics.strip("\n")
    if not body or body in seen or len(drafts) >= MAX_DRAFTS:
        return
    seen.add(body)
    drafts.append(
        Draft(
            draft_id=_draft_id(len(drafts)),
            family=family,
            tactics=body,
            ops=tuple(ops),
        )
    )


def neighbor_tactic_head(record: Mapping[str, Any], *, n_lines: int = NEIGHBOR_HEAD_LINES) -> str:
    try:
        block = tactic_block(record)
    except Exception:
        return ""
    return "\n".join(block.splitlines()[:n_lines]).strip("\n")


def enumerate_drafts(
    record: Mapping[str, Any],
    records: Sequence[Mapping[str, Any]],
) -> list[Draft]:
    """Deterministic drafts from the reference tactic tree. Not a Lean parser."""

    reference = tactic_block(record)
    drafts: list[Draft] = []
    seen: set[str] = set()
    _push(drafts, seen, "reference", reference, ("identity",))
    for family, body, ops in HAMMER_BODIES:
        _push(drafts, seen, family, body, ops)
    collapsed = collapse_simp_at(reference)
    _push(drafts, seen, "simp_set", collapsed, ("collapse_simp_at",))
    dropped = drop_have_obtain(reference)
    _push(drafts, seen, "have_chain", dropped, ("drop_have_obtain",))
    if _CALC.search(reference):
        calc_lines = [line for line in reference.splitlines() if line.strip().startswith("calc") or line.startswith("  ")]
        _push(drafts, seen, "calc", "\n".join(calc_lines[:40]), ("keep_calc",))
    _push(drafts, seen, "custom", first_case_only(reference), ("first_case_only",))
    for span in case_spans(reference)[:CASE_REPLACE_CAP]:
        _push(
            drafts,
            seen,
            "simp_set",
            replace_case_body(reference, span, "simp_all"),
            ("replace_case", span.label, "simp_all"),
        )
        _push(
            drafts,
            seen,
            "aesop",
            replace_case_body(reference, span, "aesop"),
            ("replace_case", span.label, "aesop"),
        )
    retrieval = lra_retrieve.retrieve_record(record, records)
    neighbors = lra_retrieve.prompt_neighbors(retrieval, k=NEIGHBOR_DRAFT_CAP)
    by_name = {item.get("name"): item for item in records}
    for neighbor in neighbors:
        name = str(neighbor.get("name") or "")
        source = by_name.get(name)
        if not isinstance(source, Mapping):
            continue
        head = neighbor_tactic_head(source)
        if head:
            _push(drafts, seen, "custom", head, ("neighbor_style", name))
    return drafts[:MAX_DRAFTS]


def draft_catalog(drafts: Sequence[Draft]) -> list[dict[str, Any]]:
    return [
        {
            "id": item.draft_id,
            "family": item.family,
            "ops": list(item.ops),
            "n_chars": item.n_chars,
            "head": item.head,
        }
        for item in drafts
    ]


def fanout_state(
    record: Mapping[str, Any],
    drafts: Sequence[Draft],
) -> dict[str, Any]:
    split = lra_splice.split_statement_body(record)
    tactics = lra_splice.tactic_block_from_body(split.body_suffix)
    ref_lines = tactics.splitlines()
    return {
        "problem": {
            "name": record.get("name"),
            "source": record.get("source"),
            "n_toolchains": len(record.get("version_info") or []),
            "proof_length": record.get("proof_length"),
            "num_lines": record.get("num_lines"),
        },
        "statement": str(record.get("statement") or "")[:STATEMENT_CHARS],
        "reference_head": "\n".join(ref_lines[:REF_HEAD_LINES]),
        "drafts": draft_catalog(drafts),
    }


def fanout_questions(drafts: Sequence[Draft], *, Choice: Any, Noul: Any, Score: Any) -> dict[str, Any]:
    if len(drafts) > MAX_CHOICE_OPTIONS:
        raise RuntimeError(f"draft catalog {len(drafts)} exceeds Choice option cap {MAX_CHOICE_OPTIONS}")
    criteria = {
        item.draft_id: f"{item.family}; ops={','.join(item.ops)}; {item.n_chars} chars"
        for item in drafts
    }
    return {
        "best_first_draft": Choice(
            instructions=(
                "Which draft id in `drafts` should code lake-compile first as a refactor of "
                "`reference_head` for `statement`? Pick exactly one id. Do not write Lean."
            ),
            criteria=criteria,
        ),
        "any_draft_likely_compiles": Noul(
            instructions="Is at least one catalog draft likely to compile on the record's version_info tags?"
        ),
        "likely_token_cut": Score(
            instructions="How large a source-token cut is plausible if the best draft replaces the reference?",
            criteria=list(LIKELY_SHORTER_CRITERIA),
        ),
        "spend_llm_after_fanout": Noul(
            instructions="After trying the ranked drafts, should code still spend a Leanstral generation?"
        ),
    }


def redact(payload: Any) -> Any:
    if isinstance(payload, Mapping):
        out = {}
        for key, value in payload.items():
            name = str(key).lower()
            if "api_key" in name or name in {"authorization", "token"} and name not in {
                "input_tokens",
                "output_tokens",
                "total_tokens",
                "completion_tokens",
                "prompt_tokens",
            }:
                out[key] = "[redacted]" if value else value
            else:
                out[key] = redact(value)
        return out
    if isinstance(payload, list):
        return [redact(item) for item in payload]
    if isinstance(payload, str) and payload.startswith("apikey_"):
        return "[redacted]"
    return payload


def rank_choice(probabilities: Mapping[str, Any], drafts: Sequence[Draft], *, k: int = 8) -> list[dict[str, Any]]:
    by_id = {item.draft_id: item for item in drafts}
    ranked = sorted(
        ((str(key), float(value)) for key, value in probabilities.items()),
        key=lambda item: item[1],
        reverse=True,
    )
    rows = []
    for draft_id, probability in ranked[:k]:
        draft = by_id.get(draft_id)
        rows.append(
            {
                "id": draft_id,
                "probability": probability,
                "family": None if draft is None else draft.family,
                "ops": None if draft is None else list(draft.ops),
                "n_chars": None if draft is None else draft.n_chars,
                "head": None if draft is None else draft.head,
            }
        )
    return rows


def rank_problem(record: Mapping[str, Any], records: Sequence[Mapping[str, Any]], *, live: bool) -> dict[str, Any]:
    drafts = enumerate_drafts(record, records)
    state = fanout_state(record, drafts)
    payload = {
        "name": record.get("name"),
        "source": record.get("source"),
        "n_drafts": len(drafts),
        "draft_ids": [item.draft_id for item in drafts],
        "families": sorted({item.family for item in drafts}),
        "n_case_spans": len(case_spans(tactic_block(record))),
        "state_chars": len(json.dumps(state, sort_keys=True)),
        "jev_generated_lean": False,
        "arena_score": None,
        "compile_attempted": False,
    }
    if not live:
        payload["live"] = False
        payload["catalog"] = draft_catalog(drafts)
        return payload
    pin_typesafe_path()
    from ipfs_accelerate_py.typesafe_inference import Choice, Noul, Score, TypeSafeClient, typesafe_configured

    if not typesafe_configured():
        payload["live"] = False
        payload["error"] = "TYPESAFE_API_KEY is not set"
        payload["catalog"] = draft_catalog(drafts)
        return payload
    questions = fanout_questions(drafts, Choice=Choice, Noul=Noul, Score=Score)
    client = TypeSafeClient(timeout=60.0)
    started = time.perf_counter()
    result = client.system_one(state, questions)
    wall_ms = (time.perf_counter() - started) * 1000.0
    best = (getattr(result, "choices", None) or {}).get("best_first_draft")
    noul_any = (getattr(result, "nouls", None) or {}).get("any_draft_likely_compiles")
    spend = (getattr(result, "nouls", None) or {}).get("spend_llm_after_fanout")
    shorter = (getattr(result, "scores", None) or {}).get("likely_token_cut")
    probabilities = dict(getattr(best, "probabilities", None) or {})
    payload.update(
        {
            "live": True,
            "model": getattr(result, "model", None),
            "usage": dict(getattr(result, "usage", None) or {}),
            "wall_ms": wall_ms,
            "best_first_draft": getattr(best, "choice", None),
            "best_confidence": getattr(best, "confidence", None),
            "any_draft_likely_compiles": getattr(noul_any, "noul", None),
            "spend_llm_after_fanout": getattr(spend, "noul", None),
            "likely_token_cut": getattr(shorter, "score", None),
            "top": rank_choice(probabilities, drafts),
        }
    )
    return redact(payload)


def audit_source(source: Optional[str] = None) -> dict[str, Any]:
    text = Path(__file__).read_text(encoding="utf-8") if source is None else source
    tree = ast.parse(text)
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".", 1)[0])
    lock_ex = any(isinstance(node, ast.Attribute) and node.attr == "LOCK_EX" for node in ast.walk(tree))
    return {
        "forbidden_imports": sorted(name for name in imported if name in FORBIDDEN_IMPORT_NAMES),
        "uses_lock_ex": lock_ex,
        "ok": not lock_ex and "generate_text" not in imported and "typesafe_sdk" not in imported,
    }


def self_check(path: Optional[Path] = None) -> dict[str, Any]:
    jsonl = Path(path) if path is not None else WARMUP_JSONL
    before = hashlib.sha256(jsonl.read_bytes()).hexdigest()
    _raw, digest, records = lra_splice.load_warmup_records(jsonl)
    after = hashlib.sha256(jsonl.read_bytes()).hexdigest()
    audit = audit_source()
    rows = []
    for name in CANARY_NAMES:
        record = next(item for item in records if item.get("name") == name)
        rows.append(rank_problem(record, records, live=False))
    ok = (
        audit["ok"]
        and before == after == FROZEN_WARMUP_SHA256
        and all(row["n_drafts"] >= 6 for row in rows)
        and all(row["draft_ids"][0] == "d000" for row in rows)
        and all("reference" in row["families"] for row in rows)
        and all("simp_set" in row["families"] or "aesop" in row["families"] for row in rows)
        and all(row["n_drafts"] <= MAX_CHOICE_OPTIONS for row in rows)
    )
    return {
        "ok": ok,
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
    }


def live_rank(names: Sequence[str], path: Optional[Path] = None) -> dict[str, Any]:
    load_keyfile()
    pin_typesafe_path()
    jsonl = Path(path) if path is not None else WARMUP_JSONL
    _raw, digest, records = lra_splice.load_warmup_records(jsonl)
    started = time.perf_counter()
    rows = []
    for name in names:
        record = next((item for item in records if item.get("name") == name), None)
        if record is None:
            rows.append({"name": name, "error": "unknown warm-up problem", "arena_score": None})
            continue
        rows.append(rank_problem(record, records, live=True))
    payload = {
        "schema": "lra-draft-fanout/v1",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "protocol": PROTOCOL,
        "pr": PR_ID,
        "live": True,
        "frozen_warmup_sha256": FROZEN_WARMUP_SHA256,
        "warmup_jsonl_sha256": digest,
        "jev_generated_lean": False,
        "typesafe_key_in_receipt": False,
        "lock_ex": False,
        "llama_server_started": False,
        "official_track2": False,
        "compile_attempted": False,
        "arena_score": None,
        "wall_ms": (time.perf_counter() - started) * 1000.0,
        "canaries": rows,
    }
    return redact(payload)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-check", action="store_true")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--names", default=",".join(CANARY_NAMES))
    parser.add_argument("--jsonl", type=Path, default=None)
    parser.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.self_check or not args.live:
        report = self_check(args.jsonl)
        json.dump(report, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        return 0 if report["ok"] else 1
    names = [item.strip() for item in str(args.names).split(",") if item.strip()]
    report = live_rank(names, args.jsonl)
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if "apikey_" in text:
        raise SystemExit("refusing to write a receipt that contains an API key")
    args.out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = args.out / f"draft-fanout-{stamp}.json"
    latest = args.out / "draft-fanout-latest.json"
    path.write_text(text, encoding="utf-8")
    latest.write_text(text, encoding="utf-8")
    print(json.dumps(
        {
            "ok": all(row.get("live") for row in report.get("canaries") or []),
            "latest": str(latest),
            "n": len(report.get("canaries") or []),
            "picks": [
                {"name": row.get("name"), "best": row.get("best_first_draft"), "n_drafts": row.get("n_drafts"), "wall_ms": row.get("wall_ms")}
                for row in report.get("canaries") or []
            ],
            "arena_score": None,
        },
        indent=2,
        sort_keys=True,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
