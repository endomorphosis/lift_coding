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

from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

HERE = Path(__file__).resolve().parent
PAPER_ROOT = HERE.parent
OUT_DEFAULT = PAPER_ROOT / "evidence" / "canaries"
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import _jevops_path  # noqa: E402,F401
import compile_worker as lra_cw  # noqa: E402
import draft_fanout as lra_fan  # noqa: E402
import run_warmup as lra_loop  # noqa: E402
import splice as lra_splice  # noqa: E402
import track1_ledger as lra_t1  # noqa: E402
import track1_mistral_leanstral as lra_mistral  # noqa: E402
from jevops.catalogs import CANARY_PRIMARY as CANARY_NAME  # noqa: E402
from jevops.catalogs import DEFAULT_TRACK1_STATE as DEFAULT_STATE  # noqa: E402
from jevops.catalogs import MISTRAL_HARDWARE_CLASS as HARDWARE_CLASS  # noqa: E402
from jevops.catalogs import PROTOTYPE_HARDWARE_CLASS as PROTOTYPE_HARDWARE  # noqa: E402

FROZEN_WARMUP_SHA256 = lra_splice.FROZEN_WARMUP_SHA256


def installed_matching_pins(record: Mapping[str, Any], clone: Path) -> list[dict[str, str]]:
    """Keep version_info rows whose elan tag is installed and commit matches the clone."""

    from jevops.lean import filter_installed_pin_maps
    from jevops.outer import drive_installed_head

    return drive_installed_head(
        record,
        clone,
        pins_fn=lambda info: lra_cw.iter_version_pins(info),
        resolve_fn=lambda pin: lra_cw.resolve_pin(pin, require_installed=True),
        filter_fn=filter_installed_pin_maps,
    )


def splice_src(path: Path, original_src: str, replacement: str) -> None:
    """Replace the frozen JSONL ``src`` substring. Does not search for ``:=``."""

    from jevops.outer import replace_once

    replace_once(
        path,
        original_src,
        replacement,
        error_cls=RuntimeError,
        miss="{path}: frozen src is not a substring of the lake file",
    )


def candidate_source(record: Mapping[str, Any], tactics: str) -> str:
    from jevops.lean import drive_split_candidate

    return drive_split_candidate(
        record,
        tactics,
        split_fn=lra_splice.split_statement_body,
        header="",
    )


def compile_tactics(
    record: Mapping[str, Any],
    tactics: str,
    *,
    state_root: Path,
    timeout: float,
    restore: bytes,
) -> dict[str, Any]:
    from jevops.lean import drive_keepbest_tactics, filter_installed_pin_maps, pack_compile_extra, pins_for_source
    from jevops.outer import get_str, head_seq, tail_chars

    def _pins(rec: Mapping[str, Any], clone: Any) -> list[Any]:
        return pins_for_source(
            rec,
            putnam_source="putnambench",
            putnam_fn=lambda item: filter_installed_pin_maps(
                lra_cw.iter_version_pins(item.get("version_info")),
                resolve_fn=lambda pin: lra_cw.resolve_pin(pin, require_installed=True),
            ),
            default_fn=lambda item: installed_matching_pins(item, clone),
        )

    def _compile(rec: Mapping[str, Any]) -> list[Any]:
        return lra_cw.compile_record(
            rec,
            timeout=timeout,
            state_root=state_root,
            network="allow",
            require_oleans=False,
            hardware_class=HARDWARE_CLASS,
            skip_checkout=True,
            abort_on_first_failure=True,
        )

    def _extra(
        receipt: Mapping[str, Any],
        rec: Mapping[str, Any],
        start_line: int,
        end_line: int,
        stdout: str,
        errors_in: Sequence[Mapping[str, Any]],
        errors_out: Sequence[Mapping[str, Any]],
        wall: float,
    ) -> dict[str, Any]:
        pin = lra_cw.iter_version_pins(rec.get("version_info"))[0]
        return pack_compile_extra(
            receipt,
            lean_tag=pin.lean_tag,
            start_line=start_line,
            end_line=end_line,
            stdout=stdout,
            errors_in=errors_in,
            errors_out=errors_out,
            wall=wall,
            tail_fn=tail_chars,
            head_fn=head_seq,
        )

    return drive_keepbest_tactics(
        record,
        tactics,
        state_root=state_root,
        timeout=timeout,
        restore=restore,
        url=get_str(record, "url"),
        clone_fn=lra_cw.clone_dir,
        relpath_fn=lra_cw.source_relpath,
        pins_fn=_pins,
        compile_record_fn=_compile,
        parse_errors_fn=parse_lean_errors,
        sorry_fn=sorry_in_span,
        token_fn=lra_loop.token_count,
        statement_fn=lambda rec: lra_splice.split_statement_body(rec).statement,
        candidate_source_fn=candidate_source,
        splice_fn=splice_src,
        line_in_span_fn=_line_in_span,
        extra_fn=_extra,
    )


def _line_in_span(pos: Any, start_line: int, end_line: int) -> bool:
    from jevops.outer import mapping_line_in_span

    return mapping_line_in_span(pos, start_line, end_line)


def sorry_in_span(stdout: str, start_line: int, end_line: int) -> bool:
    from jevops.outer import get_str, jsonl_pred_in_span

    def _pred(payload: Mapping[str, Any]) -> bool:
        if payload.get("kind") != "hasSorry" and "sorry" not in get_str(payload, "data").lower():
            return False
        return payload.get("severity") in {"warning", "error", None}

    return jsonl_pred_in_span(stdout, pred=_pred, start_line=start_line, end_line=end_line)


def parse_lean_errors(stdout: str) -> list[dict[str, Any]]:
    from jevops.repair import parse_jsonl_errors

    return parse_jsonl_errors(stdout)


def flatten_overindent(reference: str, tactics: str) -> str:
    """If hosted ``case`` lines are deeper than the reference, strip the extra indent."""

    from jevops.repair import flatten_overindent as _fn

    return _fn(reference, tactics, header_fn=lambda s: s.startswith("case ") and "=>" in s)


def repair_prompt(record: Mapping[str, Any], *, failed: str, errors: Sequence[Mapping[str, Any]], reference: str) -> str:
    from jevops.tactics import repair_prompt as _fn

    return _fn(record, failed=failed, errors=errors, reference=reference)


def match_reference_indent(reference: str, tactics: str) -> str:
    from jevops.repair import match_leading_indent

    return match_leading_indent(reference, tactics)


def hosted_tactics(path: Path) -> str:
    from jevops.lean import drive_hosted_file
    from jevops.outer import read_json

    return drive_hosted_file(
        path,
        read_fn=read_json,
        extract_fn=lra_loop.extract_generated_tactics,
        error_cls=RuntimeError,
    )


def _row(item: Mapping[str, Any], compile_row: Mapping[str, Any]) -> dict[str, Any]:
    from jevops.outer import merge_head_row

    return merge_head_row(item, compile_row)


def keepbest(
    *,
    name: str,
    hosted_path: Optional[Path],
    state_root: Path,
    timeout: float,
    repair: bool = False,
) -> dict[str, Any]:
    from jevops.search import drive_keepbest

    return drive_keepbest(
        name=name,
        hosted_path=hosted_path,
        state_root=state_root,
        timeout=timeout,
        repair=repair,
        load_fn=lra_splice.load_warmup_records,
        clone_fn=lambda url, root: lra_cw.require_clone(url, network="allow", state_root=root),
        relpath_fn=lra_cw.source_relpath,
        split_fn=lra_splice.split_statement_body,
        body_fn=lra_splice.tactic_block_from_body,
        drafts_fn=lra_fan.enumerate_drafts,
        span_fn=lra_fan.span_preserving_drafts,
        hosted_fn=hosted_tactics,
        match_fn=match_reference_indent,
        flatten_fn=flatten_overindent,
        compile_fn=compile_tactics,
        row_fn=_row,
        token_fn=lra_loop.token_count,
        key_fns=(lra_mistral.load_keyfiles, lra_mistral.pin_paths),
        prompt_fn=repair_prompt,
        ledger_cls=lra_t1.ProblemLedger,
        generate_fn=lra_mistral.generate_mistral,
        extract_fn=lra_loop.extract_generated_tactics,
        hardware_class=HARDWARE_CLASS,
        prototype_hardware=PROTOTYPE_HARDWARE,
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", default=CANARY_NAME)
    parser.add_argument("--names", default="", help="comma-separated warmup names; overrides --name")
    parser.add_argument("--hosted", type=Path, default=OUT_DEFAULT / "track1-mistral-latest.json")
    parser.add_argument("--no-hosted", action="store_true")
    parser.add_argument("--state-root", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--timeout", type=float, default=600.0)
    parser.add_argument("--repair", action="store_true", help="one hosted Labs repair if drafts fail lake")
    parser.add_argument("--out", type=Path, default=OUT_DEFAULT)
    from jevops.outer import list_or_none

    args = parser.parse_args(list_or_none(argv))
    from jevops.outer import pin_env

    pin_env({"IPFS_ACCELERATE_LLAMA_CPP_AUTOSTART": "0"}, overwrite=False)
    from jevops.outer import call_if, first_where, or_list, replace_if, split_csv

    names = or_list(split_csv(args.names), [args.name])
    hosted = replace_if(args.no_hosted, None, args.hosted)
    reports = []
    for name in names:
        use_hosted = call_if(hosted is not None and name == CANARY_NAME, lambda: hosted)
        reports.append(
            keepbest(
                name=name,
                hosted_path=use_hosted,
                state_root=args.state_root,
                timeout=args.timeout,
                repair=args.repair and use_hosted is not None,
            )
        )
    from jevops.outer import field_of, first_where, or_list, path_safe, print_json, text_or, utc_stamp, write_json, write_json_pair

    if len(reports) == 1:
        report = reports[0]
        latest = write_json_pair(
            args.out,
            report,
            prefix="track1-keepbest",
            latest="track1-keepbest-latest.json",
        )
        print_json({
            "ok": any(row.get("ok") for row in or_list(report.get("candidates"), [])),
            "latest": text_or(latest),
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
                for row in or_list(report.get("candidates"), [])
            ],
            "arena_score": None,
        })
        return 0
    summary = {
        "schema": "lra-track1-keepbest-batch/v1",
        "observed_at": utc_stamp(),
        "arena_score": None,
        "called_docker0": False,
        "problems": [
            {
                "name": item.get("name"),
                "kept": item.get("kept"),
                "n_valid": item.get("n_valid"),
                "ref_tokens": field_of(
                    first_where(or_list(item.get("candidates"), []), lambda row: row.get("kind") == "reference"),
                    "token_count",
                    default=None,
                ),
            }
            for item in reports
        ],
    }
    latest = write_json_pair(
        args.out,
        summary,
        prefix="track1-keepbest-batch",
        latest="track1-keepbest-batch-latest.json",
    )
    for item in reports:
        write_json(args.out / f"track1-keepbest-{path_safe(item.get('name'))}.json", item)
    print_json({"ok": True, "latest": text_or(latest), "summary": summary["problems"], "arena_score": None})
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
