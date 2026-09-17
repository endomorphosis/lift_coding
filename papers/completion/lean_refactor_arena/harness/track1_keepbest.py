#!/usr/bin/env python3
"""Track 1 keep-best: splice hosted/fan-out tactics into Strata and lake-compile.

Local docker0 is not used. Candidates come from Mistral Labs receipts or
deterministic draft fan-out. Lake on tag-pinned v4.26.0 is the oracle.
Not official Track 2. Not an Arena ranking.
"""
from __future__ import annotations

import argparse
import json
import os
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
import track1_mistral_leanstral as lra_mistral  # noqa: E402

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
    replacement = candidate_source(record, tactics)
    original = restore.decode("utf-8")
    spliced = original.replace(str(record["src"]), replacement, 1)
    start_at = spliced.find(replacement)
    start_line = spliced[:start_at].count("\n") + 1 if start_at >= 0 else 1
    end_line = start_line + replacement.count("\n")
    splice_src(dest, str(record["src"]), replacement)
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
    stdout = str(receipt.get("stdout") or "")
    errors = parse_lean_errors(stdout)
    sorry_in_theorem = sorry_in_span(stdout, start_line, end_line)
    errors_in = [item for item in errors if _line_in_span(item.get("pos"), start_line, end_line)]
    errors_out = [item for item in errors if not _line_in_span(item.get("pos"), start_line, end_line)]
    timed_out = bool(receipt.get("timed_out"))
    exit_code = receipt.get("exit_code")
    theorem_ok = (
        not timed_out
        and not errors_in
        and not errors_out
        and not sorry_in_theorem
    )
    tokens = lra_loop.token_count(tactics)
    return {
        "ok": bool(theorem_ok),
        "theorem_ok": bool(theorem_ok),
        "module_exit_0": exit_code == 0 and not timed_out,
        "exit_code": exit_code,
        "wall_ms": receipt.get("wall_ms"),
        "error": receipt.get("error") or receipt.get("stderr_digest"),
        "token_count": tokens,
        "lean_tag": pin.lean_tag,
        "sorryAx": receipt.get("sorryAx"),
        "sorry_in_theorem": sorry_in_theorem,
        "theorem_span": [start_line, end_line],
        "argv": receipt.get("argv"),
        "compile_wall_ms_outer": (time.perf_counter() - started) * 1000.0,
        "stdout_tail": stdout[-400:] if stdout else None,
        "stderr_tail": (receipt.get("stderr") or "")[-400:] if isinstance(receipt.get("stderr"), str) else None,
        "errors": errors_in or errors[:6],
        "arena_score": None,
    }


def _line_in_span(pos: Any, start_line: int, end_line: int) -> bool:
    if not isinstance(pos, Mapping):
        return False
    try:
        line = int(pos.get("line"))
    except (TypeError, ValueError):
        return False
    return start_line <= line <= end_line


def sorry_in_span(stdout: str, start_line: int, end_line: int) -> bool:
    for line in (stdout or "").splitlines():
        if not line.startswith("{"):
            continue
        try:
            payload = json.loads(line)
        except Exception:
            continue
        if payload.get("kind") != "hasSorry" and "sorry" not in str(payload.get("data") or "").lower():
            continue
        if payload.get("severity") not in {"warning", "error", None}:
            continue
        if _line_in_span(payload.get("pos"), start_line, end_line):
            return True
    return False


def parse_lean_errors(stdout: str) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    for line in (stdout or "").splitlines():
        if not line.startswith("{"):
            continue
        try:
            payload = json.loads(line)
        except Exception:
            continue
        if payload.get("severity") != "error":
            continue
        errors.append({"pos": payload.get("pos"), "data": str(payload.get("data") or "")[:400]})
        if len(errors) >= 6:
            break
    return errors


def flatten_overindent(reference: str, tactics: str) -> str:
    """If hosted ``case`` lines are deeper than the reference, strip the extra indent."""

    def case_indents(text: str) -> list[int]:
        found = []
        for line in text.splitlines():
            stripped = line.lstrip()
            if stripped.startswith("case ") and "=>" in stripped:
                found.append(len(line) - len(stripped))
        return found

    ref_cases = case_indents(reference)
    tac_cases = case_indents(tactics)
    if not ref_cases or not tac_cases:
        return tactics
    extra = min(tac_cases) - min(ref_cases)
    if extra <= 0:
        return tactics
    floor = min(tac_cases)
    out = []
    for line in tactics.splitlines():
        if not line.strip():
            out.append(line)
            continue
        indent = len(line) - len(line.lstrip())
        if indent >= floor:
            line = line[extra:]
        out.append(line)
    return "\n".join(out)


def repair_prompt(record: Mapping[str, Any], *, failed: str, errors: Sequence[Mapping[str, Any]], reference: str) -> str:
    err_lines = []
    for item in errors[:4]:
        err_lines.append(f"{item.get('pos')}: {item.get('data')}")
    return (
        "Lean Refactor Arena repair. The previous tactic block failed `lake env lean`.\n"
        "Return ONLY the corrected tactic block after `:= by`.\n"
        "Match reference indentation: top-level tactics and `case` lines use the same indent as the reference.\n"
        "Do not re-introduce explicit binders already in the theorem telescope.\n"
        "Do not repeat the statement. Do not emit sorry, admit, theorem, lemma, import, or open.\n\n"
        f"Problem: {record.get('name')}\n\n"
        f"Statement:\n{record.get('statement')}\n\n"
        f"Reference tactic block (lake exit 0):\n{reference[:1200]}\n\n"
        f"Failed tactic block:\n{failed[:1200]}\n\n"
        f"Lake errors:\n" + "\n".join(err_lines)
    )


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


def _row(item: Mapping[str, Any], compile_row: Mapping[str, Any]) -> dict[str, Any]:
    payload = {**item, **compile_row, "n_chars": len(str(item.get("tactics") or "")), "tactics_head": str(item.get("tactics") or "")[:240]}
    payload.pop("tactics", None)
    return payload


def keepbest(
    *,
    name: str,
    hosted_path: Path,
    state_root: Path,
    timeout: float,
    repair: bool = False,
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
    flattened = flatten_overindent(ref_tactics, hosted)
    candidates = [
        {"kind": "reference", "generator": "deterministic", "tactics": ref_tactics},
        {"kind": "hosted_mistral", "generator": "labs-leanstral-1-5", "tactics": hosted},
    ]
    if flattened != hosted:
        candidates.append(
            {"kind": "hosted_indent_normalized", "generator": "deterministic", "tactics": flattened}
        )
    if collapse is not None and collapse.tactics != ref_tactics:
        candidates.append(
            {"kind": "fanout_collapse_simp_at", "generator": "deterministic", "tactics": collapse.tactics}
        )
    for draft in lra_fan.span_preserving_drafts(ref_tactics):
        if draft.tactics == ref_tactics:
            continue
        candidates.append(
            {
                "kind": f"span_{draft.draft_id}_{draft.ops[-1] if draft.ops else draft.family}",
                "generator": "deterministic",
                "tactics": draft.tactics,
                "ops": list(draft.ops),
            }
        )
    rows = []
    tactics_by_kind = {item["kind"]: item["tactics"] for item in candidates}
    for item in candidates:
        compile_row = compile_tactics(
            record,
            item["tactics"],
            state_root=state_root,
            timeout=timeout,
            restore=restore,
        )
        rows.append(_row(item, compile_row))
    repair_identity = None
    repaired = False
    hosted_row = next((row for row in rows if row["kind"] == "hosted_mistral"), None)
    indent_row = next((row for row in rows if row["kind"] == "hosted_indent_normalized"), None)
    ref_tokens = lra_loop.token_count(ref_tactics)
    beats_reference = any(
        row.get("module_exit_0") and int(row.get("token_count") or ref_tokens) < ref_tokens
        for row in rows
        if row["kind"] != "reference"
    )
    needs_repair = repair and not beats_reference
    if needs_repair and hosted_row is not None:
        lra_mistral.load_keyfiles()
        lra_mistral.pin_paths()
        failed = tactics_by_kind.get("hosted_indent_normalized") or tactics_by_kind["hosted_mistral"]
        errors = (hosted_row.get("errors") if hosted_row else None) or []
        if indent_row and indent_row.get("module_exit_0"):
            errors = [
                {
                    "pos": None,
                    "data": (
                        "The indent-normalized draft compiles but is not shorter than the "
                        "reference. Return a strictly shorter tactic block that still compiles."
                    ),
                }
            ]
        prompt = repair_prompt(record, failed=failed, errors=errors, reference=ref_tactics)
        ledger = lra_t1.ProblemLedger(name=f"{name}#repair")
        text, repair_identity, _line = lra_mistral.generate_mistral(
            prompt,
            ledger,
            max_new_tokens=1400,
            timeout=180.0,
        )
        repaired_tactics = flatten_overindent(
            ref_tactics,
            match_reference_indent(ref_tactics, lra_loop.extract_generated_tactics(text)),
        )
        compile_row = compile_tactics(
            record,
            repaired_tactics,
            state_root=state_root,
            timeout=timeout,
            restore=restore,
        )
        rows.append(
            _row(
                {
                    "kind": "hosted_mistral_repair",
                    "generator": "labs-leanstral-1-5",
                    "tactics": repaired_tactics,
                    "ledger": ledger.as_dict(),
                    "repair_identity": repair_identity,
                },
                compile_row,
            )
        )
        repaired = True
    valid = [row for row in rows if row.get("theorem_ok") or (row.get("ok") and not row.get("sorry_in_theorem"))]
    module_ok = [row for row in rows if row.get("module_exit_0") or row.get("theorem_ok")]
    if valid:
        kept = sorted(
            valid,
            key=lambda row: (
                int(row.get("token_count") or 10**9),
                0 if row.get("kind") == "reference" else 1,
                float(row.get("wall_ms") or 0),
            ),
        )[0]
    elif module_ok:
        kept = sorted(
            module_ok,
            key=lambda row: (
                int(row.get("token_count") or 10**9),
                0 if row.get("kind") == "reference" else 1,
                float(row.get("wall_ms") or 0),
            ),
        )[0]
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
        "repaired": repaired,
        "official_track2": False,
        "arena_score": None,
        "clone": str(clone),
        "file_path": rel,
        "hosted_receipt": str(hosted_path),
        "candidates": rows,
        "kept": None
        if kept is None
        else {
            "kind": kept["kind"],
            "ok": kept.get("ok"),
            "theorem_ok": kept.get("theorem_ok"),
            "module_exit_0": kept.get("module_exit_0"),
            "token_count": kept.get("token_count"),
        },
        "n_valid": len(valid),
        "n_module_exit_0": len(module_ok),
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", default=CANARY_NAME)
    parser.add_argument("--hosted", type=Path, default=OUT_DEFAULT / "track1-mistral-latest.json")
    parser.add_argument("--state-root", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--timeout", type=float, default=600.0)
    parser.add_argument("--repair", action="store_true", help="one hosted Labs repair if drafts fail lake")
    parser.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = parser.parse_args(list(argv) if argv is not None else None)
    os.environ.setdefault("IPFS_ACCELERATE_LLAMA_CPP_AUTOSTART", "0")
    report = keepbest(
        name=args.name,
        hosted_path=args.hosted,
        state_root=args.state_root,
        timeout=args.timeout,
        repair=args.repair,
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
        "repaired": report.get("repaired"),
        "candidates": [
            {
                "kind": row.get("kind"),
                "ok": row.get("ok"),
                "theorem_ok": row.get("theorem_ok"),
                "module_exit_0": row.get("module_exit_0"),
                "tokens": row.get("token_count"),
                "exit": row.get("exit_code"),
                "errors": row.get("errors"),
            }
            for row in report.get("candidates") or []
        ],
        "arena_score": None,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
