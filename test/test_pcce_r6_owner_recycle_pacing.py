"""Operation-aware recycle pacing for the exclusive PCCE r6 Quack owner."""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
OPERATOR = ROOT / "scripts" / "run_agent_supervisor_proof_carrying_context_engine.py"


def _load_operator():
    spec = importlib.util.spec_from_file_location("pcce_r6_recycle_operator", OPERATOR)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_request(
    inbox: Path,
    name: str,
    payload: Any,
    *,
    now: float,
    age_seconds: float = 15.0,
) -> Path:
    inbox.mkdir(parents=True, exist_ok=True)
    request = inbox / f"{name}.request.json"
    if isinstance(payload, bytes):
        request.write_bytes(payload)
    else:
        request.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    modified = now - age_seconds
    os.utime(request, (modified, modified))
    return request


def test_exact_dml_requires_request_age_and_short_inter_recycle_floor(
    tmp_path: Path,
) -> None:
    operator = _load_operator()
    now_epoch = 10_000.0
    inbox = tmp_path / "mutations"
    request = _write_request(
        inbox,
        "claim-cas",
        {
            "sql": "UPDATE tasks SET status = ? WHERE task_cid = ?",
            "parameters": ["in_progress", "cid-043"],
        },
        now=now_epoch,
        age_seconds=14.999,
    )

    assert (
        operator._owner_recycle_due(
            inbox,
            last_recycle_monotonic=None,
            now_monotonic=500.0,
            now_epoch_seconds=now_epoch,
        )
        == ""
    )

    old = now_epoch - 15.0
    os.utime(request, (old, old))
    assert (
        operator._owner_recycle_due(
            inbox,
            last_recycle_monotonic=500.0,
            now_monotonic=514.999,
            now_epoch_seconds=now_epoch,
        )
        == ""
    )
    assert (
        operator._owner_recycle_due(
            inbox,
            last_recycle_monotonic=500.0,
            now_monotonic=515.0,
            now_epoch_seconds=now_epoch,
        )
        == operator.OWNER_RECYCLE_EXACT_DML
    )


def test_first_aged_exact_dml_does_not_wait_for_an_imaginary_prior_recycle(
    tmp_path: Path,
) -> None:
    operator = _load_operator()
    now = 10_000.0
    inbox = tmp_path / "mutations"
    _write_request(
        inbox,
        "first",
        {
            "op": "owner_dml",
            "sql": "DELETE FROM task_blocks WHERE task_cid = ?",
            "parameters": ["cid-043"],
        },
        now=now,
    )

    assert (
        operator._owner_recycle_due(
            inbox,
            last_recycle_monotonic=None,
            now_monotonic=1.0,
            now_epoch_seconds=now,
        )
        == operator.OWNER_RECYCLE_EXACT_DML
    )


def test_generic_board_unstall_keeps_ten_minute_inter_recycle_floor(
    tmp_path: Path,
) -> None:
    operator = _load_operator()
    now = 10_000.0
    inbox = tmp_path / "mutations"
    _write_request(
        inbox,
        "unstall",
        {"op": "board_unstall", "stale_seconds": 600},
        now=now,
    )

    assert (
        operator._owner_recycle_due(
            inbox,
            last_recycle_monotonic=100.0,
            now_monotonic=699.999,
            now_epoch_seconds=now,
        )
        == ""
    )
    assert (
        operator._owner_recycle_due(
            inbox,
            last_recycle_monotonic=100.0,
            now_monotonic=700.0,
            now_epoch_seconds=now,
        )
        == operator.OWNER_RECYCLE_BOARD_UNSTALL
    )


def test_mixed_pending_requests_use_exact_dml_urgency_only_with_valid_dml(
    tmp_path: Path,
) -> None:
    operator = _load_operator()
    now = 10_000.0
    inbox = tmp_path / "mutations"
    _write_request(
        inbox,
        "unstall",
        {"op": "board_unstall", "stale_seconds": 600},
        now=now,
    )
    _write_request(
        inbox,
        "exact",
        {
            "sql": "MERGE INTO tasks USING staged_tasks ON tasks.task_cid = staged_tasks.task_cid WHEN MATCHED THEN UPDATE SET revision = staged_tasks.revision",
            "parameters": None,
        },
        now=now,
    )

    assert (
        operator._owner_recycle_due(
            inbox,
            last_recycle_monotonic=100.0,
            now_monotonic=115.0,
            now_epoch_seconds=now,
        )
        == operator.OWNER_RECYCLE_EXACT_DML
    )


def test_malformed_mixed_request_cannot_accelerate_valid_board_unstall(
    tmp_path: Path,
) -> None:
    operator = _load_operator()
    now = 10_000.0
    inbox = tmp_path / "mutations"
    _write_request(
        inbox,
        "unstall",
        {"op": "board_unstall", "stale_seconds": 600},
        now=now,
    )
    _write_request(
        inbox,
        "malformed-exact",
        {
            "sql": "UPDATE tasks SET status = 'retrying'; DELETE FROM tasks",
            "parameters": None,
        },
        now=now,
    )

    assert (
        operator._owner_recycle_due(
            inbox,
            last_recycle_monotonic=100.0,
            now_monotonic=115.0,
            now_epoch_seconds=now,
        )
        == ""
    )
    assert (
        operator._owner_recycle_due(
            inbox,
            last_recycle_monotonic=100.0,
            now_monotonic=700.0,
            now_epoch_seconds=now,
        )
        == operator.OWNER_RECYCLE_BOARD_UNSTALL
    )


@pytest.mark.parametrize(
    "payload",
    [
        b"{not-json\n",
        [],
        {"sql": "SELECT * FROM tasks", "parameters": None},
        {"sql": "UPDATE tasks SET status = 'retrying'; DELETE FROM tasks"},
        {"sql": "UPDATE tasks SET status = ?", "parameters": "retrying"},
        {"op": "board_unstall", "stale_seconds": 0},
        {"op": "board_unstall", "stale_seconds": "600"},
        {"op": True, "sql": "UPDATE tasks SET status = 'retrying'"},
    ],
)
def test_malformed_request_fails_closed(
    tmp_path: Path,
    payload: Any,
) -> None:
    operator = _load_operator()
    now = 10_000.0
    inbox = tmp_path / "mutations"
    _write_request(inbox, "bad", payload, now=now)

    assert (
        operator._owner_recycle_due(
            inbox,
            last_recycle_monotonic=None,
            now_monotonic=1_000.0,
            now_epoch_seconds=now,
        )
        == ""
    )


def test_symlink_and_bounce_without_valid_request_fail_closed(tmp_path: Path) -> None:
    operator = _load_operator()
    now = 10_000.0
    inbox = tmp_path / "mutations"
    inbox.mkdir()
    outside = tmp_path / "outside.json"
    outside.write_text(
        '{"sql":"UPDATE tasks SET status = \'retrying\'"}\n',
        encoding="utf-8",
    )
    (inbox / "alias.request.json").symlink_to(outside)
    (inbox / "board-unstall.bounce").write_text(
        '{"op":"owner_dml","request_id":"missing"}\n',
        encoding="utf-8",
    )

    assert (
        operator._owner_recycle_due(
            inbox,
            last_recycle_monotonic=None,
            now_monotonic=1_000.0,
            now_epoch_seconds=now,
        )
        == ""
    )


def test_done_exact_request_does_not_trigger_recycle(tmp_path: Path) -> None:
    operator = _load_operator()
    now = 10_000.0
    inbox = tmp_path / "mutations"
    request = _write_request(
        inbox,
        "done",
        {"sql": "INSERT INTO task_events VALUES (?, ?)", "parameters": [1, 2]},
        now=now,
    )
    request.with_name("done.done.json").write_text(
        '{"ok":true,"rowcount":1}\n',
        encoding="utf-8",
    )

    assert (
        operator._owner_recycle_due(
            inbox,
            last_recycle_monotonic=None,
            now_monotonic=1_000.0,
            now_epoch_seconds=now,
        )
        == ""
    )
