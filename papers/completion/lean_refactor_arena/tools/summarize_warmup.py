#!/usr/bin/env python3
"""Characterize the frozen Lean Refactor Arena warm-up JSONL.

Does not score refactors. Writes warmup_summary.json, a LaTeX table, and an
import receipt. The SHA-256 of data/benchmark_data_warmup.jsonl must match the
frozen digest recorded in the receipt.
"""
from __future__ import annotations

import hashlib
import json
import statistics
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "harness"
JSONL = ROOT / "data" / "benchmark_data_warmup.jsonl"
SUMMARY = ROOT / "data" / "warmup_summary.json"
TABLE = ROOT / "manuscript" / "warmup_table.tex"
RECEIPT = ROOT / "evidence" / "import_receipt.json"

if str(HARNESS) not in sys.path:
    sys.path.insert(0, str(HARNESS))
import _jevops_path  # noqa: E402,F401
from jevops.catalogs import ARENA_SITE  # noqa: E402
from jevops.catalogs import ARENA_SPACE  # noqa: E402
from jevops.catalogs import FROZEN_WARMUP_SHA256 as FROZEN_SHA256  # noqa: E402
from jevops.catalogs import SOURCE_LABEL  # noqa: E402
from jevops.catalogs import WARMUP_DISPLAY_NAMES as DISPLAY_NAMES  # noqa: E402
from jevops.catalogs import WARMUP_SOURCE_URL as SOURCE_URL  # noqa: E402
from jevops.catalogs import WORKSHOP  # noqa: E402


def tex_escape(value: str) -> str:
    from jevops.lean import tex_escape as _fn

    return _fn(value)


def lean_versions(record: dict) -> list[str]:
    from jevops.lean import listed_version_tags

    return listed_version_tags(record.get("version_info"), first_only=True)


def load_records() -> tuple[bytes, str, list[dict]]:
    from jevops.outer import read_digest_jsonl

    return read_digest_jsonl(JSONL, frozen=FROZEN_SHA256)


def problem_row(record: dict) -> dict:
    from jevops.lean import drive_warmup_row

    return drive_warmup_row(record, versions_fn=lean_versions)


def write_table(problems: list[dict]) -> None:
    from jevops.lean import warmup_latex_table
    from jevops.outer import drive_write_rendered

    drive_write_rendered(
        TABLE,
        problems,
        render_fn=lambda rows: warmup_latex_table(
            rows, display_names=DISPLAY_NAMES, source_labels=SOURCE_LABEL
        ),
    )


def main() -> None:
    raw, digest, records = load_records()
    problems = [problem_row(record) for record in records]
    lengths = [p["proof_length"] for p in problems]
    lines = [p["num_lines"] for p in problems]
    src_chars = [p["src_chars"] for p in problems]
    summary = {
        "schema": "lean-refactor-arena-warmup-summary/v1",
        "source_url": SOURCE_URL,
        "arena_space": ARENA_SPACE,
        "arena_site": ARENA_SITE,
        "workshop": WORKSHOP,
        "sha256": digest,
        "bytes": len(raw),
        "n_problems": len(problems),
        "n_jsonl_fields": 12,
        "sources": dict(Counter(p["source"] for p in problems)),
        "proof_length_min": min(lengths),
        "proof_length_max": max(lengths),
        "proof_length_mean": round(statistics.mean(lengths), 1),
        "num_lines_min": min(lines),
        "num_lines_max": max(lines),
        "num_lines_mean": round(statistics.mean(lines), 1),
        "src_chars_min": min(src_chars),
        "src_chars_max": max(src_chars),
        "src_chars_mean": round(statistics.mean(src_chars), 1),
        "n_with_repo_url": sum(1 for p in problems if p["url"]),
        "n_putnam_without_path": sum(
            1 for p in problems if p["source"] == "putnambench" and not p["file_path"]
        ),
        "problems": problems,
        "arena_scores_claimed": False,
        "refactoring_run_executed": False,
        "official_track2_run_executed": False,
    }
    SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_table(problems)
    RECEIPT.parent.mkdir(parents=True, exist_ok=True)
    RECEIPT.write_text(
        json.dumps(
            {
                "schema": "lean-refactor-arena-import/v1",
                "imported_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "source_url": SOURCE_URL,
                "arena_space": ARENA_SPACE,
                "workshop": WORKSHOP,
                "local_path": "papers/completion/lean_refactor_arena/data/benchmark_data_warmup.jsonl",
                "sha256": digest,
                "bytes": len(raw),
                "n_problems": len(problems),
                "gradio_tmp_url_ephemeral": True,
                "frozen_copy_authoritative": True,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"ok {len(problems)} problems sha256={digest}")


if __name__ == "__main__":
    main()
