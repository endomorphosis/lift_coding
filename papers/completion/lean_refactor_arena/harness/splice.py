#!/usr/bin/env python3
"""Prefix splice and lexical admission for Lean Refactor Arena warm-up records.

The JSONL bind is ``src.startswith(statement)``. The proof body is the suffix
after that frozen statement. Never scan ``src`` or ``statement`` for the first
``:=``: ArkLib/CSLib named arguments and ``by omega`` inside types stay in the
statement. Lexical admission punches ``statement + " := by\\nsorry"`` and
accepts tactic-only ``proof_text``. Admission is not a lake compile and does
not claim Arena scores.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import _jevops_path  # noqa: E402,F401
PAPER_ROOT = HERE.parent
REPO_ROOT = HERE.parents[3]
WARMUP_JSONL = PAPER_ROOT / "data" / "benchmark_data_warmup.jsonl"
ACCEL_ROOT = REPO_ROOT / "external" / "ipfs_accelerate"

from jevops.catalogs import FORBIDDEN_IMPORT_CORE as FORBIDDEN_IMPORT_NAMES  # noqa: E402
from jevops.catalogs import FROZEN_WARMUP_SHA256  # noqa: E402
from jevops.catalogs import JSONL_FIELDS  # noqa: E402
from jevops.catalogs import REQUIRED_JSONL_FIELDS  # noqa: E402
from jevops.catalogs import WARMUP_N  # noqa: E402
from jevops.lean import BODY_BY_PREFIXES  # noqa: E402
from jevops.lean import FORBIDDEN_PROOF_TOKENS  # noqa: E402
from jevops.lean import STATEMENT_SORRY_SUFFIX  # noqa: E402
from jevops.lean import ASSIGN_NEEDLE as _ASSIGN_NEEDLE  # noqa: E402
from jevops.lean import TOKEN_BOUNDARY as _TOKEN_BOUNDARY  # noqa: E402
from jevops.repair import ASSIGN_SCAN_METHODS as _SCAN_METHODS  # noqa: E402


class SpliceError(RuntimeError):
    """Fail-closed prefix-splice or lexical-admission error."""


class DigestMismatch(SpliceError):
    """Warm-up JSONL digest drifted from the frozen SHA-256."""


class PrefixBindError(SpliceError):
    """``src`` is not the frozen ``statement`` plus a body suffix."""


from jevops.lean import AdmissionView
from jevops.lean import StatementBody


def _ensure_accel_path() -> None:
    from jevops.outer import pin_sys_path

    pin_sys_path(
        ACCEL_ROOT,
        defaults={
            "IPFS_ACCEL_SKIP_CORE": "1",
            "IPFS_AUTO_INSTALL": "false",
        },
    )


def _admit_lean_proof_text():
    from jevops.lean import load_admit_lean_proof_text

    return load_admit_lean_proof_text(setup=(_ensure_accel_path,))


def sha256_bytes(data: bytes) -> str:
    from jevops.outer import digest_hex

    return digest_hex(data)


def sha256_file(path: Path) -> str:
    from jevops.outer import digest_file

    return digest_file(path)


def load_warmup_records(path: Optional[Path] = None) -> tuple[bytes, str, list[dict[str, Any]]]:
    """Load the frozen warm-up JSONL. Refuses digest drift. Does not rewrite the file."""

    from jevops.outer import load_jsonl_objects, path_or

    jsonl = path_or(path, WARMUP_JSONL)
    return load_jsonl_objects(
        jsonl,
        expected_digest=FROZEN_WARMUP_SHA256,
        expected_n=WARMUP_N,
        required_fields=REQUIRED_JSONL_FIELDS,
        mismatch_exc=DigestMismatch,
        record_exc=SpliceError,
    )


def split_statement_body(record: Mapping[str, Any]) -> StatementBody:
    """Bind the statement as a prefix of ``src``. Never search for ``:=``."""

    from jevops.outer import as_str, get_str, require_str

    name = get_str(record, "name")
    statement = require_str(
        record.get("statement"),
        error_cls=PrefixBindError,
        empty=f"{name}: statement must be a non-empty string",
    )
    src = require_str(
        record.get("src"),
        error_cls=PrefixBindError,
        empty=f"{name}: src must be a non-empty string",
    )
    from jevops.outer import split_statement_suffix

    suffix = split_statement_suffix(
        src,
        statement,
        name=name,
        error_cls=PrefixBindError,
        miss_msg=f"{name}: src does not start with the frozen statement",
    )
    header = as_str(record.get("header"))
    return StatementBody(
        name=name,
        source=get_str(record, "source"),
        statement=statement,
        body_suffix=suffix,
        header=header,
    )


def statement_sorry_template(statement: str) -> str:
    """Supervisor-owned hole for lexical admission. Not a lake file and not ``src``."""

    from jevops.lean import statement_sorry_template as _fn

    return _fn(statement, error_cls=PrefixBindError)


def tactic_block_from_body(body_suffix: str) -> str:
    """Strip the leading `` := by`` of an already-split body. Does not inspect the statement."""

    from jevops.lean import tactic_block_from_body as _fn

    return _fn(body_suffix, error_cls=SpliceError)


def lake_candidate_source(*, header: str, statement: str, tactic_block: str) -> str:
    """Put Putnam ``header`` in the lake file. ``proof_text`` remains the tactic block only."""

    from jevops.lean import lake_candidate_source as _fn

    return _fn(header=header, statement=statement, tactic_block=tactic_block)


def forbidden_proof_tokens(proof_text: str) -> tuple[str, ...]:
    """Tokens that make ``proof_text`` a declaration/import rather than a tactic block."""

    from jevops.repair import forbidden_tokens

    from jevops.outer import raise_if

    raise_if(not isinstance(proof_text, str), SpliceError, "proof_text must be a string")
    return forbidden_tokens(proof_text, FORBIDDEN_PROOF_TOKENS, boundary=_TOKEN_BOUNDARY)


def admit_tactic_block(
    statement: str,
    proof_text: str,
    *,
    theorem_id: str = "",
    declaration_name: str = "",
) -> Any:
    """Lexical admit of a tactic-only block into ``statement + ' := by\\nsorry'``.

    Never pass the original complete ``src`` as ``native_source`` or
    ``canonical_source`` (SOURCE_COPY / THEOREM_SUBSTITUTION). Never pass the
    JSONL statement as ``expected_statement``: ``admit_lean_proof_text`` scans
    the first ``:=`` / ``by`` and that is not the LRA bind.
    """

    forbidden_proof_tokens(proof_text)
    native = statement_sorry_template(statement)
    from jevops.lean import admit_empty_canonical

    return admit_empty_canonical(
        _admit_lean_proof_text(),
        proof_text,
        native,
        theorem_id=theorem_id,
        declaration_name=declaration_name,
    )


def admission_view(record: Mapping[str, Any], proof_text: str) -> AdmissionView:
    from jevops.lean import pack_admission_view
    from jevops.outer import last_component

    split = split_statement_body(record)
    native = statement_sorry_template(split.statement)
    admission = admit_tactic_block(
        split.statement,
        proof_text,
        theorem_id=split.name,
        declaration_name=last_component(split.name),
    )
    return pack_admission_view(
        admission,
        name=split.name,
        native=native,
        statement=split.statement,
        view_cls=AdmissionView,
    )


def source_assign_scan_issues(source: str) -> list[str]:
    """Flag uses of the two-character assign needle. Longer `` := by`` prefixes are the body marker."""

    from jevops.repair import scan_constant_uses

    return scan_constant_uses(
        source,
        _ASSIGN_NEEDLE,
        methods=_SCAN_METHODS,
        bare_fmt="bare assign needle at line {line}",
        call_fmt="{attr}(assign-needle) scan at line {line}",
    )


def _imported_names(source: str) -> set[str]:
    from jevops.repair import imported_names

    return imported_names(source)


def _record_report(record: Mapping[str, Any]) -> dict[str, Any]:
    split = split_statement_body(record)
    tactics = tactic_block_from_body(split.body_suffix)
    template = statement_sorry_template(split.statement)
    view = admission_view(record, "simp")
    from jevops.lean import pack_statement_report
    from jevops.outer import prefix_bind_flags

    flags = prefix_bind_flags(record["src"], record["statement"], split.body_suffix)
    return pack_statement_report(
        name=split.name,
        source=split.source,
        prefix_bind=flags["prefix_bind"],
        body_is_suffix=flags["body_is_suffix"],
        reconstructed_src=split.reconstructed_src == record["src"],
        statement_chars=len(split.statement),
        body_chars=len(split.body_suffix),
        header_chars=len(split.header),
        body_starts_with_by=any(split.body_suffix.startswith(prefix) for prefix in BODY_BY_PREFIXES),
        tactic_block_chars=len(tactics),
        template_starts_with_statement=template.startswith(split.statement),
        template_sorry_count=template.count("sorry"),
        admission_simp=asdict(view),
        header_not_in_src=(not split.header.strip()) or (not record["src"].startswith(split.header)),
    )


def self_check(path: Optional[Path] = None) -> dict[str, Any]:
    """Prefix-bind all 15 records and exercise lexical admission. No compile."""

    from jevops.outer import read_text

    source = read_text(__file__)
    from jevops.outer import path_or, relative_or_str

    jsonl = path_or(path, WARMUP_JSONL)
    before = sha256_file(jsonl)
    raw, digest, records = load_warmup_records(jsonl)
    per_record = [_record_report(record) for record in records]
    after = sha256_file(jsonl)
    imported = _imported_names(source)
    forbidden_imports = sorted(name for name in imported if name in FORBIDDEN_IMPORT_NAMES)
    assign_scan_issues = source_assign_scan_issues(source)
    from jevops.repair import uses_attr

    uses_lock_ex = uses_attr(source, "LOCK_EX")

    from jevops.outer import at_or

    sample = at_or(records, 8)
    forbidden_views = {}
    from jevops.outer import first_token, text_or

    for proof in ("theorem foo : True := rfl", "lemma bar", "import Mathlib", "open Nat"):
        view = admission_view(sample, proof)
        forbidden_views[first_token(proof)] = asdict(view)

    from jevops.outer import first_where

    putnam = first_where(records, lambda record: record["source"] == "putnambench")
    putnam_split = split_statement_body(putnam)
    putnam_tactics = tactic_block_from_body(putnam_split.body_suffix)
    admit = _admit_lean_proof_text()
    source_copy = admit(
        putnam_tactics,
        statement_sorry_template(putnam_split.statement),
        theorem_id=putnam_split.name,
        canonical_source=putnam["src"],
        expected_statement="",
    )
    src_as_native = admit(
        "simp",
        putnam["src"],
        theorem_id=putnam_split.name,
        canonical_source="",
        expected_statement="",
    )

    prefix_ok = all(item["prefix_bind"] and item["body_is_suffix"] and item["reconstructed_src"] for item in per_record)
    templates_ok = all(item["template_starts_with_statement"] and item["template_sorry_count"] == 1 for item in per_record)
    forbidden_rejected = all(not item["accepted"] for item in forbidden_views.values())
    simp_prefix_bound = all(item["admission_simp"]["native_source_starts_with_statement"] for item in per_record)
    wick = next(item for item in per_record if "timeOrderF_superCommuteF_eq_time" in item["name"])
    others_admitted = all(
        item["admission_simp"]["accepted"]
        for item in per_record
        if "timeOrderF_superCommuteF_eq_time" not in item["name"]
    )

    from jevops.outer import pack_unscored

    report = pack_unscored(**{
        "ok": True,
        "n_records": len(records),
        "n_jsonl_fields": len(JSONL_FIELDS),
        "frozen_warmup_sha256": FROZEN_WARMUP_SHA256,
        "warmup_jsonl_sha256": digest,
        "jsonl_bytes": len(raw),
        "jsonl_unchanged": before == after == FROZEN_WARMUP_SHA256,
        "prefix_bind_all": prefix_ok,
        "sorry_templates_prefix_bound": templates_ok,
        "assign_scan_issues": assign_scan_issues,
        "never_scans_first_assign": not assign_scan_issues,
        "forbidden_imports": forbidden_imports,
        "uses_fcntl": "fcntl" in imported,
        "uses_lock_ex": uses_lock_ex,
        "imported_names": sorted(imported),
        "forbidden_proof_text": forbidden_views,
        "forbidden_proof_text_rejected": forbidden_rejected,
        "source_copy_when_canonical_is_src": {
            "accepted": bool(source_copy.accepted),
            "failure_code": getattr(source_copy.failure_code, "value", text_or(source_copy.failure_code)),
            "reason": source_copy.reason,
        },
        "src_as_native_source": {
            "accepted": bool(src_as_native.accepted),
            "failure_code": getattr(src_as_native.failure_code, "value", text_or(src_as_native.failure_code)),
            "reason": src_as_native.reason,
        },
        "simp_native_source_prefix_bound": simp_prefix_bound,
        "simp_admitted_ascii_decls": others_admitted,
        "wickalgebra_unicode_decl": {
            "name": wick["name"],
            "prefix_bind": wick["prefix_bind"],
            "native_source_prefix_bound": wick["admission_simp"]["native_source_starts_with_statement"],
            "admission_accepted": wick["admission_simp"]["accepted"],
            "failure_code": wick["admission_simp"]["failure_code"],
            "note": "admit_lean_proof_text ASCII identifier regex does not match lemma ι_*; prefix bind remains the authority",
        },
        "records": per_record,
        "compiled": False,
        "lake": False,
        "llama_server_started": False,
        "warmup_path": relative_or_str(jsonl, REPO_ROOT),
    })
    from jevops.outer import finalize_ok

    return finalize_ok(
        report,
        report["n_records"] == WARMUP_N,
        report["jsonl_unchanged"],
        report["prefix_bind_all"],
        report["sorry_templates_prefix_bound"],
        report["never_scans_first_assign"],
        not forbidden_imports,
        not report["uses_fcntl"],
        not uses_lock_ex,
        forbidden_rejected,
        simp_prefix_bound,
        others_admitted,
        wick["prefix_bind"],
        wick["admission_simp"]["native_source_starts_with_statement"],
        not source_copy.accepted,
        not src_as_native.accepted,
        report["compiled"] is False,
        report["lake"] is False,
        report["arena_score"] is None,
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-check", action="store_true", help="prefix-bind and lexical-admit all 15 records; no compile")
    parser.add_argument("--jsonl", type=Path, default=None, help="warmup JSONL path (default: frozen data/benchmark_data_warmup.jsonl)")
    from jevops.outer import list_or_none

    args = parser.parse_args(list_or_none(argv))
    if args.self_check or argv is None or argv == []:
        from jevops.outer import print_ok

        return print_ok(self_check(args.jsonl))
    parser.error("choose --self-check")
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
