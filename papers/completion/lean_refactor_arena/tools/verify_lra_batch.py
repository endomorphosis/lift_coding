#!/usr/bin/env python3
"""Fail-closed batch verifier for Lean Refactor Arena warm-up receipts.

Dedicated LRA verifier. Does not import law_to_action ``verify_batch.py``.
Does not write Arena scores. ``--require-complete`` is the only process
allowed to declare the warm-up run complete, and it requires:

- frozen JSONL digest
- statement-bind (``candidate.startswith(header+statement)`` / prefix)
- one compile record per listed ``version_info`` tag
- axiom reports with no ``sorryAx``
- one receipt per scheduled problem

Incomplete is not success. This tool does not compile Lean, does not call
Leanstral, and does not emit Track 1/Track 2 rankings.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

HERE = Path(__file__).resolve().parent
PAPER_ROOT = HERE.parent
REPO_ROOT = HERE.parents[3]
HARNESS = PAPER_ROOT / "harness"
WARMUP_JSONL = PAPER_ROOT / "data" / "benchmark_data_warmup.jsonl"

if str(HARNESS) not in sys.path:
    sys.path.insert(0, str(HARNESS))
import _jevops_path  # noqa: E402,F401
import splice as lra_splice  # noqa: E402

from jevops.catalogs import BATCH_GATES as ALL_GATES
from jevops.catalogs import BATCH_SCHEMA
from jevops.catalogs import COMPILE_SCHEMA
from jevops.catalogs import FREEZE_SCHEMA
from jevops.catalogs import FROZEN_WARMUP_SHA256
from jevops.catalogs import HEX64
from jevops.catalogs import PROBLEM_SCHEMA
from jevops.catalogs import PROTOCOL
from jevops.catalogs import RESERVED_DIR_NAMES
from jevops.catalogs import SKIP_JSON_NAMES
from jevops.catalogs import WARMUP_N
FORBIDDEN_IMPORT_ROOTS = frozenset(
    {
        "law_to_action",
        "verify_batch",
        "fcntl",
        "IndependentKernelVerifier",
        "KernelVerifier",
        "LeanstralProofProvider",
        "leanstral_proof_provider",
        "driver",
    }
)
FORBIDDEN_IMPORT_NEEDLES = (
    "law_to_action",
    "verify_batch",
    "generated_code_study",
)
FORBIDDEN_SCORE_NAMES = frozenset(
    {
        "arena_score",
        "arena_score_tokens",
        "arena_score_elab",
        "official_track2_score",
        "token_savings",
        "score",
        "relevance_score",
        "official_score",
    }
)
EMPTY_AXIOM_DIGEST = hashlib.sha256(b"[]").hexdigest()

if lra_splice.FROZEN_WARMUP_SHA256 != FROZEN_WARMUP_SHA256:
    raise RuntimeError("verify_lra_batch frozen digest drifted from splice.py")
if lra_splice.WARMUP_N != WARMUP_N:
    raise RuntimeError("verify_lra_batch warm-up count drifted from splice.py")


class VerifyError(RuntimeError):
    """Fail-closed batch-verifier error."""


@dataclass
class TagRecord:
    lean_tag: str
    git_commit: str = ""
    sorryAx: bool = False
    axiom_names: list[str] = field(default_factory=list)
    axiom_digest: str = ""
    stdout: str = ""
    stderr: str = ""
    exit_code: int = -1
    ok: bool = False
    path: str = ""
    arena_score: None = None
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from jevops.outer import public_fields

        return public_fields(
            self,
            ("lean_tag", "git_commit", "sorryAx", "axiom_names", "axiom_digest", "exit_code", "ok", "path"),
            extra={"arena_score": None},
        )


@dataclass
class ProblemReceipt:
    name: str
    source: str = ""
    header: str = ""
    statement: str = ""
    candidate: str = ""
    warmup_sha256: str = ""
    accepted: Optional[bool] = None
    compile_records: dict[str, TagRecord] = field(default_factory=dict)
    path: str = ""
    arena_score: Any = None
    score: Any = None
    mock: bool = False
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class ProblemJudgment:
    name: str
    source: str
    listed_tags: list[str]
    receipt_found: bool
    duplicate: bool
    digest_ok: bool
    statement_bind_ok: bool
    all_tags_ok: bool
    no_sorry_ok: bool
    one_receipt: bool
    arena_score_null: bool
    failures: list[str] = field(default_factory=list)
    tag_records: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        from jevops.outer import public_fields

        return public_fields(
            self,
            (
                "name",
                "source",
                "listed_tags",
                "receipt_found",
                "duplicate",
                "digest_ok",
                "statement_bind_ok",
                "all_tags_ok",
                "no_sorry_ok",
                "one_receipt",
                "arena_score_null",
                "failures",
                "tag_records",
            ),
            extra={"arena_score": None, "score": None},
        )


def sha256_bytes(data: bytes) -> str:
    from jevops.outer import digest_hex

    return digest_hex(data)


def sha256_file(path: Path) -> str:
    from jevops.outer import digest_file

    return digest_file(path)


def sha256_text(text: str) -> str:
    from jevops.outer import digest_text

    return digest_text(text)


def load_json(path: Path) -> Any:
    from jevops.outer import read_json

    return read_json(path, require_object=False)


from jevops.lean import candidate_binds_statement
from jevops.lean import listed_version_commits as listed_commits
from jevops.lean import listed_version_tags as listed_tags


def _is_hex64(value: Any) -> bool:
    return isinstance(value, str) and HEX64.fullmatch(value) is not None


def _score_nonnull(payload: Mapping[str, Any], *keys: str) -> list[str]:
    from jevops.repair import present_nonnull

    return present_nonnull(payload, keys)


def axiom_report_exists(record: TagRecord) -> bool:
    from jevops.lean import axiom_report_exists as _fn

    return _fn(record, hex64=HEX64)


def has_sorry_ax(record: TagRecord) -> bool:
    from jevops.lean import has_sorry_ax as _fn

    return _fn(record)


def tag_record_from_payload(payload: Mapping[str, Any], *, path: str = "") -> TagRecord:
    from jevops.lean import tag_from_payload

    return tag_from_payload(payload, path=path, tag_cls=TagRecord)


def _read_candidate(directory: Path, payload: Mapping[str, Any]) -> str:
    from jevops.lean import read_candidate_text

    return read_candidate_text(directory, payload)


def _compile_records_from_payload(payload: Mapping[str, Any], *, path: str) -> dict[str, TagRecord]:
    from jevops.lean import compile_records_from_payload

    return compile_records_from_payload(payload, path=path, tag_fn=tag_record_from_payload)


def load_tag_files(directory: Path) -> dict[str, TagRecord]:
    from jevops.lean import load_tag_directory

    return load_tag_directory(
        directory,
        skip_names=SKIP_JSON_NAMES,
        compile_schema=COMPILE_SCHEMA,
        tag_fn=tag_record_from_payload,
        load_json_fn=load_json,
    )


def load_problem_from_dir(directory: Path) -> Optional[ProblemReceipt]:
    from jevops.lean import problem_from_directory

    return problem_from_directory(
        directory,
        reserved=RESERVED_DIR_NAMES,
        skip_names=SKIP_JSON_NAMES,
        compile_schema=COMPILE_SCHEMA,
        tag_fn=tag_record_from_payload,
        problem_cls=ProblemReceipt,
        load_json_fn=load_json,
        error_cls=VerifyError,
    )


def load_problem_from_file(path: Path) -> Optional[ProblemReceipt]:
    from jevops.lean import problem_from_json_file

    return problem_from_json_file(
        path,
        compile_schema=COMPILE_SCHEMA,
        problem_schema=PROBLEM_SCHEMA,
        tag_fn=tag_record_from_payload,
        problem_cls=ProblemReceipt,
        load_json_fn=load_json,
        error_cls=VerifyError,
    )


def iter_receipt_roots(receipts_dir: Path) -> list[Path]:
    from jevops.lean import iter_receipt_roots as _fn

    return _fn(receipts_dir)


def load_problem_receipts(receipts_dir: Path) -> list[ProblemReceipt]:
    from jevops.lean import load_receipt_tree

    return load_receipt_tree(
        receipts_dir,
        reserved=RESERVED_DIR_NAMES,
        skip_names=SKIP_JSON_NAMES,
        from_dir_fn=load_problem_from_dir,
        from_file_fn=load_problem_from_file,
        error_cls=VerifyError,
    )


def load_freeze_binding(receipts_dir: Path) -> dict[str, Any]:
    from jevops.lean import load_freeze_file

    return load_freeze_file(receipts_dir, load_json_fn=load_json, error_cls=VerifyError)


def judge_problem(
    record: Mapping[str, Any],
    receipts: Sequence[ProblemReceipt],
    *,
    frozen_digest: str,
) -> ProblemJudgment:
    from jevops.lean import drive_judge_problem

    return drive_judge_problem(
        record,
        receipts,
        frozen_digest=frozen_digest,
        tags_fn=listed_tags,
        score_names=tuple(FORBIDDEN_SCORE_NAMES),
        bind_fn=candidate_binds_statement,
        axiom_fn=axiom_report_exists,
        sorry_fn=has_sorry_ax,
        judgment_cls=ProblemJudgment,
    )


def schedule_view(records: Sequence[Mapping[str, Any]], digest: str, nbytes: int) -> dict[str, Any]:
    from jevops.lean import schedule_rows

    return {
        "schema": BATCH_SCHEMA,
        "status": "SCHEDULE",
        "protocol": PROTOCOL,
        "n_scheduled": len(records),
        "frozen_warmup_sha256": FROZEN_WARMUP_SHA256,
        "warmup_jsonl_sha256": digest,
        "jsonl_bytes": nbytes,
        "problems": schedule_rows(records, tags_fn=listed_tags),
        "arena_score": None,
        "score": None,
        "writes_arena_scores": False,
        "imports_law_to_action_verify_batch": False,
    }


def verify_batch(
    *,
    jsonl: Path,
    receipts_dir: Path,
    require_digest: bool = False,
    require_statement_bind: bool = False,
    require_all_tags: bool = False,
    require_no_sorry: bool = False,
    require_complete: bool = False,
) -> tuple[int, dict[str, Any], str]:
    """Return (exit_code, payload, fail_message). Exit 2 is fail-closed."""

    from jevops.lean import drive_verify_batch, note_freeze_binding, selected_gates

    return drive_verify_batch(
        jsonl=jsonl,
        receipts_dir=receipts_dir,
        gates=selected_gates(
            digest=require_digest,
            statement=require_statement_bind,
            tags=require_all_tags,
            sorry=require_no_sorry,
            complete=require_complete,
            all_gates=ALL_GATES,
        ),
        load_fn=lra_splice.load_warmup_records,
        digest_fn=sha256_file,
        frozen=FROZEN_WARMUP_SHA256,
        expected_n=WARMUP_N,
        fail_fn=_fail_payload,
        mismatch_type=lra_splice.DigestMismatch,
        io_types=(OSError, lra_splice.SpliceError, json.JSONDecodeError),
        load_receipts_fn=load_problem_receipts,
        load_binding_fn=load_freeze_binding,
        note_fn=note_freeze_binding,
        judge_fn=judge_problem,
        error_types=(OSError, json.JSONDecodeError, VerifyError),
        score_names=tuple(FORBIDDEN_SCORE_NAMES),
        schema=BATCH_SCHEMA,
        protocol=PROTOCOL,
    )


def _fail_payload(gates: Sequence[str], failures: Sequence[str], *, n_scheduled: int) -> dict[str, Any]:
    from jevops.lean import fail_batch_payload

    return fail_batch_payload(
        gates,
        failures,
        n_scheduled=n_scheduled,
        schema=BATCH_SCHEMA,
        protocol=PROTOCOL,
    )


def compact_candidate(record: Mapping[str, Any]) -> str:
    from jevops.lean import drive_split_candidate

    return drive_split_candidate(record, "rfl", split_fn=lra_splice.split_statement_body)


def compact_tag_payload(record: Mapping[str, Any], tag: str, commit: str) -> dict[str, Any]:
    from jevops.lean import synthetic_ok_tag

    return synthetic_ok_tag(
        record,
        tag,
        commit,
        schema=COMPILE_SCHEMA,
        axiom_digest=EMPTY_AXIOM_DIGEST,
    )


def write_problem_fixture(
    dest: Path,
    record: Mapping[str, Any],
    *,
    digest: str,
    drop_tags: Sequence[str] = (),
    mutate_candidate: Optional[str] = None,
    sorry_tags: Sequence[str] = (),
    injected_score: Any = None,
    warmup_sha256: Optional[str] = None,
    accepted: bool = True,
    statement: Optional[str] = None,
) -> Path:
    from jevops.lean import drive_listed_fixture, lake_candidate_source

    return drive_listed_fixture(
        dest,
        record,
        digest=digest,
        tags_fn=listed_tags,
        commits_fn=listed_commits,
        problem_schema=PROBLEM_SCHEMA,
        tag_payload_fn=compact_tag_payload,
        candidate_fn=compact_candidate,
        lake_source_fn=lake_candidate_source,
        sorry_digest_fn=sha256_text,
        drop_tags=drop_tags,
        mutate_candidate=mutate_candidate,
        sorry_tags=sorry_tags,
        injected_score=injected_score,
        warmup_sha256=warmup_sha256,
        accepted=accepted,
        statement=statement,
    )


def write_complete_fixture(
    dest: Path,
    records: Sequence[Mapping[str, Any]],
    *,
    digest: str,
) -> None:
    from jevops.lean import write_freeze_bundle

    write_freeze_bundle(
        dest,
        records,
        digest=digest,
        schema=FREEZE_SCHEMA,
        protocol=PROTOCOL,
        write_problem_fn=write_problem_fixture,
    )


def _copy_fixture(src: Path, dest: Path) -> None:
    from jevops.outer import drive_replace_tree

    drive_replace_tree(src, dest)


def _imported_names(source: str) -> set[str]:
    from jevops.repair import imported_names

    return imported_names(source)


def _numeric_score_assignments(source: str) -> list[str]:
    from jevops.repair import assignment_score_issues

    return assignment_score_issues(source, FORBIDDEN_SCORE_NAMES)


def audit_source(source: Optional[str] = None) -> dict[str, Any]:
    from jevops.outer import source_text

    text = source_text(source, path=__file__)
    imported = _imported_names(text)
    forbidden = sorted(
        name
        for name in imported
        if name in FORBIDDEN_IMPORT_ROOTS or any(needle == name or needle in name.split(".") for needle in FORBIDDEN_IMPORT_NEEDLES)
    )
    needle_hits = sorted(
        {
            needle
            for needle in FORBIDDEN_IMPORT_NEEDLES
            if any(needle == name or needle in name.split(".") for name in imported)
        }
    )
    # Import audit only. Docstrings may mention the missing law_to_action path.
    score_issues = _numeric_score_assignments(text)
    uses_lock_ex = any(
        isinstance(node, ast.Attribute) and node.attr == "LOCK_EX"
        for node in ast.walk(ast.parse(text))
    )
    path_insert_law = False
    tree = ast.parse(text)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr in {"insert", "append"}:
            for arg in node.args:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    if "law_to_action" in arg.value or "verify_batch" in arg.value:
                        path_insert_law = True
    return {
        "imported_names": sorted(imported),
        "forbidden_imports": forbidden,
        "forbidden_import_needles": needle_hits,
        "score_assignments": score_issues,
        "uses_lock_ex": uses_lock_ex,
        "sys_path_inserts_law_to_action": path_insert_law,
        "imports_law_to_action_verify_batch": bool(forbidden or needle_hits or path_insert_law),
        "writes_arena_scores": bool(score_issues),
        "ok": (
            not forbidden
            and not needle_hits
            and not score_issues
            and not uses_lock_ex
            and not path_insert_law
        ),
    }


def _run_verify(
    receipts_dir: Path,
    jsonl: Path,
    **flags: bool,
) -> tuple[int, dict[str, Any], str]:
    return verify_batch(jsonl=jsonl, receipts_dir=receipts_dir, **flags)


def _cli_verify(receipts_dir: Path, jsonl: Path, extra: Sequence[str]) -> dict[str, Any]:
    proc = subprocess.run(
        [
            sys.executable,
            "-B",
            str(Path(__file__).resolve()),
            "--jsonl",
            str(jsonl),
            "--receipts-dir",
            str(receipts_dir),
            *extra,
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    stdout = proc.stdout or ""
    payload: dict[str, Any] = {}
    json_text = stdout
    if stdout.startswith("FAIL:"):
        newline = stdout.find("\n")
        json_text = stdout[newline + 1 :] if newline >= 0 else ""
    json_text = json_text.strip()
    if json_text.startswith("{"):
        try:
            payload = json.loads(json_text)
        except json.JSONDecodeError:
            payload = {}
    return {
        "exit_code": proc.returncode,
        "stdout_head": stdout[:400],
        "stderr_head": (proc.stderr or "")[:200],
        "fail_line": stdout.splitlines()[0] if stdout.startswith("FAIL:") else "",
        "status": payload.get("status"),
        "arena_score": payload.get("arena_score"),
        "complete": payload.get("complete"),
        "imports_law_to_action_verify_batch": payload.get("imports_law_to_action_verify_batch"),
        "writes_arena_scores": payload.get("writes_arena_scores"),
    }


def self_check(path: Optional[Path] = None) -> dict[str, Any]:
    """Prove fail-closed gates on compact synthetic receipts. No lake compile."""

    from jevops.outer import read_text

    source = read_text(__file__)
    jsonl = Path(path) if path is not None else WARMUP_JSONL
    before = sha256_file(jsonl)
    raw, digest, records = lra_splice.load_warmup_records(jsonl)
    after = sha256_file(jsonl)
    audit = audit_source(source)
    multi = next(record for record in records if len(listed_tags(record.get("version_info"))) > 1)
    putnam = next(record for record in records if record.get("source") == "putnambench")
    first = records[0]

    fail_closed: dict[str, Any] = {}
    with tempfile.TemporaryDirectory(prefix="lra-015-verify-") as tmp:
        tmp_path = Path(tmp)
        complete_dir = tmp_path / "complete"
        write_complete_fixture(complete_dir, records, digest=digest)
        code, payload, message = _run_verify(
            complete_dir,
            jsonl,
            require_digest=True,
            require_statement_bind=True,
            require_all_tags=True,
            require_no_sorry=True,
            require_complete=True,
        )
        complete_ok = (
            code == 0
            and payload.get("status") == "PASS"
            and payload.get("complete") is True
            and payload.get("n_scheduled") == WARMUP_N
            and payload.get("one_receipt_per_scheduled_problem") is True
            and payload.get("digest_ok") is True
            and payload.get("statement_bind_ok") is True
            and payload.get("all_tags_ok") is True
            and payload.get("no_sorryAx") is True
            and payload.get("arena_score") is None
            and payload.get("writes_arena_scores") is False
            and payload.get("imports_law_to_action_verify_batch") is False
        )
        fail_closed["complete"] = {
            "exit_code": code,
            "status": payload.get("status"),
            "complete": payload.get("complete"),
            "message": message,
            "ok": complete_ok,
        }
        cli = _cli_verify(
            complete_dir,
            jsonl,
            [
                "--require-complete",
                "--require-digest",
                "--require-statement-bind",
                "--require-all-tags",
                "--require-no-sorry",
            ],
        )
        fail_closed["complete_cli"] = cli
        fail_closed["complete_cli"]["ok"] = (
            cli["exit_code"] == 0
            and cli["status"] == "PASS"
            and cli["arena_score"] is None
            and cli["imports_law_to_action_verify_batch"] is False
        )

        missing_dir = tmp_path / "missing"
        _copy_fixture(complete_dir, missing_dir)
        shutil.rmtree(missing_dir / first["name"])
        code, payload, message = _run_verify(missing_dir, jsonl, require_complete=True)
        fail_closed["missing_receipt"] = {
            "exit_code": code,
            "status": payload.get("status"),
            "missing": payload.get("missing_receipts"),
            "message": message,
            "ok": code == 2 and first["name"] in (payload.get("missing_receipts") or []) and payload.get("complete") is False,
        }

        digest_dir = tmp_path / "digest"
        _copy_fixture(complete_dir, digest_dir)
        write_problem_fixture(
            digest_dir,
            first,
            digest=digest,
            warmup_sha256="0" * 64,
        )
        binding = load_json(digest_dir / "freeze_binding.json")
        binding["warmup_sha256"] = "0" * 64
        (digest_dir / "freeze_binding.json").write_text(
            json.dumps(binding, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        code, payload, message = _run_verify(digest_dir, jsonl, require_digest=True, require_complete=True)
        fail_closed["digest_mismatch"] = {
            "exit_code": code,
            "status": payload.get("status"),
            "digest_ok": payload.get("digest_ok"),
            "message": message,
            "ok": code == 2 and payload.get("digest_ok") is False,
        }

        bind_dir = tmp_path / "bind"
        _copy_fixture(complete_dir, bind_dir)
        evil = "axiom evil : True\n\n" + compact_candidate(first)
        write_problem_fixture(bind_dir, first, digest=digest, mutate_candidate=evil)
        code, payload, message = _run_verify(bind_dir, jsonl, require_statement_bind=True, require_complete=True)
        fail_closed["statement_unbound"] = {
            "exit_code": code,
            "status": payload.get("status"),
            "statement_bind_ok": payload.get("statement_bind_ok"),
            "message": message,
            "ok": code == 2 and payload.get("statement_bind_ok") is False,
        }

        mutated_dir = tmp_path / "mutated-statement"
        _copy_fixture(complete_dir, mutated_dir)
        write_problem_fixture(
            mutated_dir,
            first,
            digest=digest,
            statement=str(first["statement"]) + " -> True",
        )
        code, payload, message = _run_verify(
            mutated_dir, jsonl, require_statement_bind=True, require_complete=True
        )
        fail_closed["statement_mutated"] = {
            "exit_code": code,
            "status": payload.get("status"),
            "statement_bind_ok": payload.get("statement_bind_ok"),
            "ok": code == 2 and payload.get("statement_bind_ok") is False,
        }

        tags_dir = tmp_path / "tags"
        _copy_fixture(complete_dir, tags_dir)
        drop = listed_tags(multi.get("version_info"))[-1]
        write_problem_fixture(tags_dir, multi, digest=digest, drop_tags=(drop,))
        code, payload, message = _run_verify(tags_dir, jsonl, require_all_tags=True, require_complete=True)
        fail_closed["missing_tag"] = {
            "exit_code": code,
            "status": payload.get("status"),
            "all_tags_ok": payload.get("all_tags_ok"),
            "dropped_tag": drop,
            "problem": multi.get("name"),
            "message": message,
            "ok": code == 2 and payload.get("all_tags_ok") is False,
        }

        sorry_dir = tmp_path / "sorry"
        _copy_fixture(complete_dir, sorry_dir)
        sorry_tag = listed_tags(putnam.get("version_info"))[0]
        write_problem_fixture(sorry_dir, putnam, digest=digest, sorry_tags=(sorry_tag,))
        code, payload, message = _run_verify(sorry_dir, jsonl, require_no_sorry=True, require_complete=True)
        fail_closed["sorryAx"] = {
            "exit_code": code,
            "status": payload.get("status"),
            "no_sorryAx": payload.get("no_sorryAx"),
            "problem": putnam.get("name"),
            "tag": sorry_tag,
            "message": message,
            "ok": code == 2 and payload.get("no_sorryAx") is False,
        }

        score_dir = tmp_path / "score"
        _copy_fixture(complete_dir, score_dir)
        write_problem_fixture(score_dir, first, digest=digest, injected_score=0.42)
        code, payload, message = _run_verify(score_dir, jsonl, require_complete=True)
        fail_closed["arena_score_written"] = {
            "exit_code": code,
            "status": payload.get("status"),
            "message": message,
            "ok": code == 2 and payload.get("complete") is False,
        }

        dup_dir = tmp_path / "dup"
        _copy_fixture(complete_dir, dup_dir)
        duplicate = dup_dir / "problems" / first["name"]
        write_problem_fixture(dup_dir / "problems", first, digest=digest)
        code, payload, message = _run_verify(dup_dir, jsonl, require_complete=True)
        fail_closed["duplicate_receipt"] = {
            "exit_code": code,
            "status": payload.get("status"),
            "duplicate": payload.get("duplicate_receipts"),
            "ok": code == 2 and first["name"] in (payload.get("duplicate_receipts") or []),
        }
        del duplicate

        header_ok = candidate_binds_statement(
            compact_candidate(putnam),
            str(putnam.get("header") or ""),
            str(putnam.get("statement") or ""),
        )
        header_concat_ok = candidate_binds_statement(
            str(putnam.get("header") or "") + str(putnam.get("statement") or "") + " := by\nrfl\n",
            str(putnam.get("header") or ""),
            str(putnam.get("statement") or ""),
        )

        lra014 = (
            PAPER_ROOT
            / "receipts"
            / "snapshots"
            / "LRA-014"
            / "outputs"
            / "receipts"
        )
        partial = {}
        if lra014.is_dir():
            code, payload, message = _run_verify(lra014, jsonl, require_complete=True)
            partial = {
                "exit_code": code,
                "status": payload.get("status"),
                "complete": payload.get("complete"),
                "n_receipts": payload.get("n_receipts"),
                "missing_n": len(payload.get("missing_receipts") or []),
                "ok": code == 2 and payload.get("complete") is False,
            }
        fail_closed["lra014_incomplete"] = partial

    named_assign = next(
        record for record in records if record.get("name") == "Cslib.CCS.bisimilarity_congr_choice"
    )
    first_assign = str(named_assign["statement"]).find(":=")
    bind_ignores_first_assign = first_assign != -1 and first_assign < len(named_assign["statement"])

    gates_ok = all(
        fail_closed[key]["ok"]
        for key in (
            "complete",
            "complete_cli",
            "missing_receipt",
            "digest_mismatch",
            "statement_unbound",
            "statement_mutated",
            "missing_tag",
            "sorryAx",
            "arena_score_written",
            "duplicate_receipt",
        )
    )
    report = {
        "ok": False,
        "schema": BATCH_SCHEMA,
        "protocol": PROTOCOL,
        "n_records": len(records),
        "frozen_warmup_sha256": FROZEN_WARMUP_SHA256,
        "warmup_jsonl_sha256": digest,
        "jsonl_bytes": len(raw),
        "jsonl_unchanged": before == after == FROZEN_WARMUP_SHA256,
        "empty_axiom_digest": EMPTY_AXIOM_DIGEST,
        "require_digest": True,
        "require_statement_bind": True,
        "require_all_tags": True,
        "require_no_sorry": True,
        "require_complete": True,
        "one_receipt_per_scheduled_problem": True,
        "header_bind_putnam": header_ok,
        "header_plus_statement_bind": header_concat_ok,
        "named_assign_inside_statement": bind_ignores_first_assign,
        "named_assign_first_assign_byte": first_assign,
        "imports_law_to_action_verify_batch": audit["imports_law_to_action_verify_batch"],
        "writes_arena_scores": audit["writes_arena_scores"],
        "audit": audit,
        "fail_closed": fail_closed,
        "gates_ok": gates_ok,
        "arena_score": None,
        "score": None,
        "compiled": False,
        "lake": False,
        "llama_server_started": False,
        "independent_kernel_verifier_used": False,
        "names": [str(record.get("name") or "") for record in records],
        "n_listed_tags": sum(len(listed_tags(record.get("version_info"))) for record in records),
        "warmup_path": str(jsonl.relative_to(REPO_ROOT)) if jsonl.is_relative_to(REPO_ROOT) else str(jsonl),
    }
    report["ok"] = bool(
        report["n_records"] == WARMUP_N
        and report["jsonl_unchanged"]
        and report["header_bind_putnam"]
        and report["header_plus_statement_bind"]
        and report["named_assign_inside_statement"]
        and audit["ok"]
        and not audit["imports_law_to_action_verify_batch"]
        and not audit["writes_arena_scores"]
        and gates_ok
        and (not fail_closed["lra014_incomplete"] or fail_closed["lra014_incomplete"].get("ok"))
        and report["arena_score"] is None
        and report["score"] is None
        and report["compiled"] is False
        and EMPTY_AXIOM_DIGEST == "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945"
    )
    return report


def _print_json(payload: Mapping[str, Any]) -> None:
    from jevops.outer import print_json

    print_json(payload)


def _print_fail(message: str, payload: Mapping[str, Any]) -> None:
    from jevops.outer import drive_print_fail

    drive_print_fail(message, payload)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--self-check",
        action="store_true",
        help="compact synthetic 15-problem fixture plus fail-closed mutations; no lake",
    )
    parser.add_argument(
        "--schedule",
        action="store_true",
        help="print the frozen 15-problem schedule; check JSONL digest",
    )
    parser.add_argument(
        "--audit-source",
        action="store_true",
        help="AST-audit imports and Arena-score writes",
    )
    parser.add_argument("--jsonl", type=Path, default=None, help="warmup JSONL (default: frozen file)")
    parser.add_argument(
        "--receipts-dir",
        "--results",
        dest="receipts_dir",
        type=Path,
        default=None,
        help="directory of per-problem receipts",
    )
    parser.add_argument("--require-complete", action="store_true", help="every scheduled problem has a receipt; all gates")
    parser.add_argument("--require-digest", action="store_true", help="JSONL SHA-256 matches frozen")
    parser.add_argument("--require-no-sorry", action="store_true", help="axiom reports exist and have no sorryAx")
    parser.add_argument(
        "--require-statement-bind",
        action="store_true",
        help="candidate.startswith(header+statement) / prefix check",
    )
    parser.add_argument("--require-all-tags", action="store_true", help="one compile record per version_info tag")
    args = parser.parse_args(list(argv) if argv is not None else None)
    jsonl = args.jsonl if args.jsonl is not None else WARMUP_JSONL

    if args.self_check or argv is None or argv == []:
        report = self_check(jsonl)
        _print_json(report)
        return 0 if report["ok"] else 1

    if args.audit_source:
        report = audit_source()
        report["arena_score"] = None
        report["score"] = None
        report["imports_law_to_action_verify_batch"] = report["imports_law_to_action_verify_batch"]
        _print_json(report)
        return 0 if report["ok"] else 1

    if args.schedule:
        try:
            raw, digest, records = lra_splice.load_warmup_records(jsonl)
        except (OSError, lra_splice.SpliceError) as exc:
            _print_fail(str(exc), _fail_payload(["digest"], [str(exc)], n_scheduled=WARMUP_N))
            return 2
        _print_json(schedule_view(records, digest, len(raw)))
        return 0

    if args.receipts_dir is None:
        parser.error("choose --self-check, --schedule, --audit-source, or --receipts-dir")
        return 2

    code, payload, message = verify_batch(
        jsonl=jsonl,
        receipts_dir=args.receipts_dir,
        require_digest=args.require_digest,
        require_statement_bind=args.require_statement_bind,
        require_all_tags=args.require_all_tags,
        require_no_sorry=args.require_no_sorry,
        require_complete=args.require_complete,
    )
    if code != 0:
        _print_fail(message or "batch is not complete", payload)
        return code
    _print_json(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
