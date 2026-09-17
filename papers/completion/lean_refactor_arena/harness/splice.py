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
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

HERE = Path(__file__).resolve().parent
PAPER_ROOT = HERE.parent
REPO_ROOT = HERE.parents[3]
WARMUP_JSONL = PAPER_ROOT / "data" / "benchmark_data_warmup.jsonl"
ACCEL_ROOT = REPO_ROOT / "external" / "ipfs_accelerate"

FROZEN_WARMUP_SHA256 = "6209680cf00cde0765b77b24834cd72c64dd585b2f7e3f2a58209980ab59a804"
WARMUP_N = 15
JSONL_FIELDS = (
    "name",
    "source",
    "statement",
    "src",
    "proof_length",
    "num_lines",
    "header",
    "file_path",
    "url",
    "start_line",
    "end_line",
    "version_info",
)
REQUIRED_JSONL_FIELDS = (
    "name",
    "source",
    "statement",
    "src",
    "proof_length",
    "num_lines",
    "header",
    "file_path",
    "url",
    "version_info",
)
STATEMENT_SORRY_SUFFIX = " := by\nsorry"
BODY_BY_PREFIXES = (
    " := by \n",
    " := by\n",
    " := by ",
    " := by",
    ":= by \n",
    ":= by\n",
    ":= by",
)
FORBIDDEN_PROOF_TOKENS = ("theorem", "lemma", "import", "open")
FORBIDDEN_IMPORT_NAMES = frozenset({"fcntl", "LeanstralProofProvider", "leanstral_proof_provider"})
_SCAN_METHODS = frozenset(
    {
        "find",
        "rfind",
        "index",
        "rindex",
        "partition",
        "rpartition",
        "split",
        "rsplit",
        "count",
        "replace",
    }
)
_ASSIGN_NEEDLE = ":" + "="
_TOKEN_BOUNDARY = r"(?<![A-Za-z0-9_']){token}(?![A-Za-z0-9_'])"


class SpliceError(RuntimeError):
    """Fail-closed prefix-splice or lexical-admission error."""


class DigestMismatch(SpliceError):
    """Warm-up JSONL digest drifted from the frozen SHA-256."""


class PrefixBindError(SpliceError):
    """``src`` is not the frozen ``statement`` plus a body suffix."""


@dataclass(frozen=True)
class StatementBody:
    name: str
    source: str
    statement: str
    body_suffix: str
    header: str

    @property
    def reconstructed_src(self) -> str:
        return self.statement + self.body_suffix


@dataclass(frozen=True)
class AdmissionView:
    accepted: bool
    failure_code: str
    reason: str
    name: str
    native_source_starts_with_statement: bool
    used_full_src_as_native: bool = False
    used_full_src_as_canonical: bool = False
    arena_score: None = None


def _ensure_accel_path() -> None:
    os.environ.setdefault("IPFS_ACCEL_SKIP_CORE", "1")
    os.environ.setdefault("IPFS_AUTO_INSTALL", "false")
    accel = str(ACCEL_ROOT)
    if accel not in sys.path:
        sys.path.insert(0, accel)


def _admit_lean_proof_text():
    _ensure_accel_path()
    from ipfs_accelerate_py.agent_supervisor.proof.kernel_verification import admit_lean_proof_text

    return admit_lean_proof_text


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load_warmup_records(path: Optional[Path] = None) -> tuple[bytes, str, list[dict[str, Any]]]:
    """Load the frozen warm-up JSONL. Refuses digest drift. Does not rewrite the file."""

    jsonl = Path(path) if path is not None else WARMUP_JSONL
    raw = jsonl.read_bytes()
    digest = sha256_bytes(raw)
    if digest != FROZEN_WARMUP_SHA256:
        raise DigestMismatch(f"warmup JSONL hash mismatch: {digest} != {FROZEN_WARMUP_SHA256}")
    records = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
    if len(records) != WARMUP_N:
        raise SpliceError(f"warmup JSONL must contain {WARMUP_N} records, got {len(records)}")
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise SpliceError(f"warmup record {index} is not an object")
        missing = [field for field in REQUIRED_JSONL_FIELDS if field not in record]
        if missing:
            raise SpliceError(f"warmup record {index} missing fields: {missing}")
    return raw, digest, records


def split_statement_body(record: Mapping[str, Any]) -> StatementBody:
    """Bind the statement as a prefix of ``src``. Never search for ``:=``."""

    name = str(record.get("name") or "")
    statement = record.get("statement")
    src = record.get("src")
    if not isinstance(statement, str) or not statement:
        raise PrefixBindError(f"{name}: statement must be a non-empty string")
    if not isinstance(src, str) or not src:
        raise PrefixBindError(f"{name}: src must be a non-empty string")
    if not src.startswith(statement):
        raise PrefixBindError(f"{name}: src does not start with the frozen statement")
    header = record.get("header") or ""
    if not isinstance(header, str):
        header = ""
    return StatementBody(
        name=name,
        source=str(record.get("source") or ""),
        statement=statement,
        body_suffix=src[len(statement) :],
        header=header,
    )


def statement_sorry_template(statement: str) -> str:
    """Supervisor-owned hole for lexical admission. Not a lake file and not ``src``."""

    if not isinstance(statement, str) or not statement:
        raise PrefixBindError("statement must be a non-empty string")
    return statement + STATEMENT_SORRY_SUFFIX


def tactic_block_from_body(body_suffix: str) -> str:
    """Strip the leading `` := by`` of an already-split body. Does not inspect the statement."""

    if not isinstance(body_suffix, str) or not body_suffix:
        raise SpliceError("body suffix is empty")
    for prefix in BODY_BY_PREFIXES:
        if body_suffix.startswith(prefix):
            return body_suffix[len(prefix) :]
    raise SpliceError("body suffix does not start with ' := by' after the frozen statement")


def lake_candidate_source(*, header: str, statement: str, tactic_block: str) -> str:
    """Put Putnam ``header`` in the lake file. ``proof_text`` remains the tactic block only."""

    core = statement + " := by\n" + str(tactic_block).lstrip("\n")
    if isinstance(header, str) and header.strip():
        return header.rstrip() + "\n\n" + core
    return core


def forbidden_proof_tokens(proof_text: str) -> tuple[str, ...]:
    """Tokens that make ``proof_text`` a declaration/import rather than a tactic block."""

    if not isinstance(proof_text, str):
        raise SpliceError("proof_text must be a string")
    found: list[str] = []
    for token in FORBIDDEN_PROOF_TOKENS:
        if re.search(_TOKEN_BOUNDARY.format(token=re.escape(token)), proof_text, re.IGNORECASE):
            found.append(token)
    return tuple(found)


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
    admit = _admit_lean_proof_text()
    return admit(
        proof_text,
        native,
        theorem_id=theorem_id,
        declaration_name=declaration_name,
        canonical_source="",
        expected_statement="",
    )


def admission_view(record: Mapping[str, Any], proof_text: str) -> AdmissionView:
    split = split_statement_body(record)
    native = statement_sorry_template(split.statement)
    admission = admit_tactic_block(
        split.statement,
        proof_text,
        theorem_id=split.name,
        declaration_name=split.name.rsplit(".", 1)[-1],
    )
    return AdmissionView(
        accepted=bool(admission.accepted),
        failure_code=getattr(admission.failure_code, "value", str(admission.failure_code)),
        reason=str(admission.reason),
        name=split.name,
        native_source_starts_with_statement=native.startswith(split.statement),
        used_full_src_as_native=False,
        used_full_src_as_canonical=False,
        arena_score=None,
    )


def source_assign_scan_issues(source: str) -> list[str]:
    """Flag uses of the two-character assign needle. Longer `` := by`` prefixes are the body marker."""

    needle = _ASSIGN_NEEDLE
    tree = ast.parse(source)
    issues: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and node.value == needle:
            issues.append(f"bare assign needle at line {getattr(node, 'lineno', 0)}")
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr not in _SCAN_METHODS:
            continue
        for arg in list(node.args) + [kw.value for kw in node.keywords]:
            if isinstance(arg, ast.Constant) and arg.value == needle:
                issues.append(
                    f"{node.func.attr}(assign-needle) scan at line {getattr(node, 'lineno', 0)}"
                )
    return issues


def _imported_names(source: str) -> set[str]:
    tree = ast.parse(source)
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name.split(".", 1)[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                names.add(node.module.split(".", 1)[0])
            for alias in node.names:
                names.add(alias.name)
    return names


def _record_report(record: Mapping[str, Any]) -> dict[str, Any]:
    split = split_statement_body(record)
    tactics = tactic_block_from_body(split.body_suffix)
    template = statement_sorry_template(split.statement)
    view = admission_view(record, "simp")
    return {
        "name": split.name,
        "source": split.source,
        "prefix_bind": record["src"].startswith(record["statement"]),
        "body_is_suffix": split.body_suffix == record["src"][len(record["statement"]) :],
        "reconstructed_src": split.reconstructed_src == record["src"],
        "statement_chars": len(split.statement),
        "body_chars": len(split.body_suffix),
        "header_chars": len(split.header),
        "body_starts_with_by": any(split.body_suffix.startswith(prefix) for prefix in BODY_BY_PREFIXES),
        "tactic_block_chars": len(tactics),
        "template_starts_with_statement": template.startswith(split.statement),
        "template_sorry_count": template.count("sorry"),
        "admission_simp": asdict(view),
        "header_not_in_src": (not split.header.strip()) or (not record["src"].startswith(split.header)),
        "arena_score": None,
    }


def self_check(path: Optional[Path] = None) -> dict[str, Any]:
    """Prefix-bind all 15 records and exercise lexical admission. No compile."""

    source = Path(__file__).read_text(encoding="utf-8")
    jsonl = Path(path) if path is not None else WARMUP_JSONL
    before = sha256_file(jsonl)
    raw, digest, records = load_warmup_records(jsonl)
    per_record = [_record_report(record) for record in records]
    after = sha256_file(jsonl)
    imported = _imported_names(source)
    forbidden_imports = sorted(name for name in imported if name in FORBIDDEN_IMPORT_NAMES)
    assign_scan_issues = source_assign_scan_issues(source)
    uses_lock_ex = any(
        isinstance(node, ast.Attribute) and node.attr == "LOCK_EX" for node in ast.walk(ast.parse(source))
    )

    sample = records[8] if len(records) > 8 else records[0]
    forbidden_views = {}
    for proof in ("theorem foo : True := rfl", "lemma bar", "import Mathlib", "open Nat"):
        view = admission_view(sample, proof)
        forbidden_views[proof.split()[0]] = asdict(view)

    putnam = next(record for record in records if record["source"] == "putnambench")
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

    report = {
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
            "failure_code": getattr(source_copy.failure_code, "value", str(source_copy.failure_code)),
            "reason": source_copy.reason,
        },
        "src_as_native_source": {
            "accepted": bool(src_as_native.accepted),
            "failure_code": getattr(src_as_native.failure_code, "value", str(src_as_native.failure_code)),
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
        "arena_score": None,
        "warmup_path": str(jsonl.relative_to(REPO_ROOT)),
    }
    report["ok"] = bool(
        report["n_records"] == WARMUP_N
        and report["jsonl_unchanged"]
        and report["prefix_bind_all"]
        and report["sorry_templates_prefix_bound"]
        and report["never_scans_first_assign"]
        and not forbidden_imports
        and not report["uses_fcntl"]
        and not uses_lock_ex
        and forbidden_rejected
        and simp_prefix_bound
        and others_admitted
        and wick["prefix_bind"]
        and wick["admission_simp"]["native_source_starts_with_statement"]
        and not source_copy.accepted
        and not src_as_native.accepted
        and report["compiled"] is False
        and report["lake"] is False
        and report["arena_score"] is None
    )
    return report


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-check", action="store_true", help="prefix-bind and lexical-admit all 15 records; no compile")
    parser.add_argument("--jsonl", type=Path, default=None, help="warmup JSONL path (default: frozen data/benchmark_data_warmup.jsonl)")
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.self_check or argv is None or argv == []:
        report = self_check(args.jsonl)
        json.dump(report, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        return 0 if report["ok"] else 1
    parser.error("choose --self-check")
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
