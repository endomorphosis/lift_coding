#!/usr/bin/env python3
"""Track 1 keep-best: splice hosted/fan-out tactics into Strata and lake-compile.

Local docker0 is not used. Candidates come from Mistral Labs receipts or
deterministic draft fan-out. Lake on tag-pinned v4.26.0 is the oracle.
Not official Track 2. Not an Arena ranking.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

HERE = Path(__file__).resolve().parent
PAPER_ROOT = HERE.parent
DEFAULT_STATE = Path.home() / ".local/state/ipfs_accelerate_py/vericodegen-2026-lra/track1-lake"
OUT_DEFAULT = PAPER_ROOT / "evidence" / "canaries"
CANARY_NAME = "CallElimCorrect.substOldPostSubset"
HARDWARE_CLASS = "mistral_labs_api"
PROTOTYPE_HARDWARE = "spark_gb10"

if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import compile_worker as lra_cw  # noqa: E402
import draft_fanout as lra_fan  # noqa: E402
import run_warmup as lra_loop  # noqa: E402
import splice as lra_splice  # noqa: E402
import track1_ledger as lra_t1  # noqa: E402

FROZEN_WARMUP_SHA256 = lra_splice.FROZEN_WARMUP_SHA256


def splice_src(path: Path, original_src: str, replacement: str) -> None:
    """Replace the frozen JSONL ``src`` substring. Does not search for ``:=``."""

    text = path.read_text(encoding="utf-8")
    if original_src not in text:
        raise RuntimeError(f"{path}: frozen src is not a substring of the lake file")
    path.write_text(text.replace(original_src, replacement, 1), encoding="utf-8")


def candidate_source(record: Mapping[str, Any], tactics: str) -> str:
    split = lra_splice.split_statement_body(record)
    return lra_splice.lake_candidate_source(
        header="",
        statement=split.statement,
        tactic_block=tactics,
    )


def compile_tactics(
    record: Mapping[str, Any],
    tactics: str,
    *,
    state_root: Path,
    timeout: float,
    restore: bytes,
) -> dict[str, Any]:
    pin = lra_cw.iter_version_pins(record.get("version_info"))[0]
    clone = lra_cw.clone_dir(str(record["url"]), state_root)
    rel = lra_cw.source_relpath(record)
    dest = clone / rel
    dest.write_bytes(restore)
    splice_src(dest, str(record["src"]), candidate_source(record, tactics))
    started = time.perf_counter()
    receipts = lra_cw.compile_record(
        record,
        timeout=timeout,
        state_root=state_root,
        network="allow",
        require_oleans=False,
        hardware_class=HARDWARE_CLASS,
        skip_checkout=True,
        abort_on_first_failure=True,
    )
    dest.write_bytes(restore)
    receipt = receipts[0].to_dict() if receipts else {"ok": False, "error": "no_receipt"}
    tokens = lra_loop.token_count(tactics)
    return {
        "ok": bool(receipt.get("ok")),
        "module_exit_0": receipt.get("exit_code") == 0 and not receipt.get("timed_out"),
        "exit_code": receipt.get("exit_code"),
        "wall_ms": receipt.get("wall_ms"),
        "error": receipt.get("error") or receipt.get("stderr_digest"),
        "token_count": tokens,
        "lean_tag": pin.lean_tag,
        "sorryAx": receipt.get("sorryAx"),
        "argv": receipt.get("argv"),
        "compile_wall_ms_outer": (time.perf_counter() - started) * 1000.0,
        "stdout_tail": (receipt.get("stdout") or "")[-400:] if isinstance(receipt.get("stdout"), str) else None,
        "stderr_tail": (receipt.get("stderr") or "")[-400:] if isinstance(receipt.get("stderr"), str) else None,
        "arena_score": None,
    }


def match_reference_indent(reference: str, tactics: str) -> str:
    ref_first = next((line for line in reference.splitlines() if line.strip()), "")
    indent = ref_first[: len(ref_first) - len(ref_first.lstrip())]
    body = tactics.lstrip("\n")
    if not indent or body.startswith(indent):
        return body
    return "\n".join((indent + line if line.strip() else line) for line in body.splitlines())


def hosted_tactics(path: Path) -> str:
    payload = json.loads(path.read_text(encoding="utf-8"))
    text = str(payload.get("text") or payload.get("text_head") or "")
    if payload.get("used_prototype_endpoint") or payload.get("called_docker0"):
        raise RuntimeError("refusing a prototype/docker0 generation as a Track 1 candidate")
    identity = payload.get("identity") or {}
    if identity.get("url_host") not in {None, "api.mistral.ai"} and "url_host" in identity:
        if identity.get("url_host") != "api.mistral.ai":
            raise RuntimeError(f"refusing non-Labs host {identity.get('url_host')}")
    return lra_loop.extract_generated_tactics(text)


def keepbest(
    *,
    name: str,
    hosted_path: Path,
    state_root: Path,
    timeout: float,
) -> dict[str, Any]:
    _raw, digest, records = lra_splice.load_warmup_records()
    record = next(item for item in records if item.get("name") == name)
    clone = lra_cw.require_clone(str(record["url"]), network="allow", state_root=state_root)
    rel = lra_cw.source_relpath(record)
    dest = clone / rel
    if not dest.is_file():
        raise RuntimeError(f"missing {dest}; clone/checkout Strata first")
    restore = dest.read_bytes()
    ref_tactics = lra_splice.tactic_block_from_body(lra_splice.split_statement_body(record).body_suffix)
    drafts = lra_fan.enumerate_drafts(record, records)
    collapse = next((item for item in drafts if "collapse_simp_at" in item.ops), None)
    hosted = match_reference_indent(ref_tactics, hosted_tactics(hosted_path))
    candidates = [
        {"kind": "reference", "generator": "deterministic", "tactics": ref_tactics},
        {"kind": "hosted_mistral", "generator": "labs-leanstral-1-5", "tactics": hosted},
    ]
    if collapse is not None and collapse.tactics != ref_tactics:
        candidates.append(
            {"kind": "fanout_collapse_simp_at", "generator": "deterministic", "tactics": collapse.tactics}
        )
    rows = []
    for item in candidates:
        compile_row = compile_tactics(
            record,
            item["tactics"],
            state_root=state_root,
            timeout=timeout,
            restore=restore,
        )
        rows.append({**item, "n_chars": len(item["tactics"]), **compile_row, "tactics_head": item["tactics"][:240]})
        del rows[-1]["tactics"]
    valid = [row for row in rows if row.get("ok") and not row.get("sorryAx")]
    module_ok = [row for row in rows if row.get("module_exit_0")]
    if valid:
        kept = sorted(valid, key=lambda row: (row["token_count"], row.get("wall_ms") or 0, row["kind"]))[0]
    elif module_ok:
        kept = next((row for row in module_ok if row["kind"] == "reference"), module_ok[0])
    else:
        kept = next((row for row in rows if row["kind"] == "reference"), rows[0] if rows else None)
    return {
        "schema": "lra-track1-keepbest/v1",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "name": name,
        "warmup_jsonl_sha256": digest,
        "hardware_class": HARDWARE_CLASS,
        "prototype_hardware_class": PROTOTYPE_HARDWARE,
        "used_prototype_endpoint": False,
        "called_docker0": False,
        "official_track2": False,
        "arena_score": None,
        "clone": str(clone),
        "file_path": rel,
        "hosted_receipt": str(hosted_path),
        "candidates": rows,
        "kept": None if kept is None else {"kind": kept["kind"], "ok": kept.get("ok"), "token_count": kept.get("token_count")},
        "n_valid": len(valid),
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", default=CANARY_NAME)
    parser.add_argument("--hosted", type=Path, default=OUT_DEFAULT / "track1-mistral-latest.json")
    parser.add_argument("--state-root", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--timeout", type=float, default=600.0)
    parser.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = parser.parse_args(list(argv) if argv is not None else None)
    os.environ.setdefault("IPFS_ACCELERATE_LLAMA_CPP_AUTOSTART", "0")
    report = keepbest(
        name=args.name,
        hosted_path=args.hosted,
        state_root=args.state_root,
        timeout=args.timeout,
    )
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    args.out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = args.out / f"track1-keepbest-{stamp}.json"
    latest = args.out / "track1-keepbest-latest.json"
    path.write_text(text, encoding="utf-8")
    latest.write_text(text, encoding="utf-8")
    print(json.dumps({
        "ok": any(row.get("ok") for row in report.get("candidates") or []),
        "latest": str(latest),
        "kept": report.get("kept"),
        "n_valid": report.get("n_valid"),
        "candidates": [
            {"kind": row.get("kind"), "ok": row.get("ok"), "tokens": row.get("token_count"), "exit": row.get("exit_code"), "error": row.get("error")}
            for row in report.get("candidates") or []
        ],
        "arena_score": None,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
