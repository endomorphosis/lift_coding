"""Focused PCTDD wrapper tests for Quack lifecycle recovery controls."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[3]
FACADE = (
    ROOT
    / "scripts"
    / "ops"
    / "agent_supervisor"
    / "parallel_content_sealing_proof_carrying_tdd.py"
)


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, FACADE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _birth(*, pid: int = 424242, ticks: int = 8888) -> dict[str, object]:
    return {
        "pid": pid,
        "start_time_ticks": ticks,
        "boot_id": "boot-pctdd-wrapper",
        "parent_pid": 1,
    }


def _record(facade, birth: dict[str, object]) -> dict[str, object]:
    return {
        "schema": facade.OWNER_PID_SCHEMA,
        "pid": birth["pid"],
        "process_birth": dict(birth),
        "recorded_at": "2026-08-30T00:00:00Z",
    }


def test_json_object_reads_one_bounded_descriptor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    facade = _load("pctdd_bounded_descriptor_json")
    monkeypatch.setattr(facade, "ROOT", tmp_path)
    path = tmp_path / "runtime" / "status.json"
    path.parent.mkdir()
    path.write_text('{"ready":true}\n', encoding="utf-8")
    monkeypatch.setattr(
        Path,
        "read_text",
        lambda *_args, **_kwargs: pytest.fail("path-based second read is forbidden"),
    )

    assert facade._json_object(path) == {"ready": True}


def test_json_object_rejects_content_beyond_descriptor_bound(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    facade = _load("pctdd_oversized_descriptor_json")
    monkeypatch.setattr(facade, "ROOT", tmp_path)
    monkeypatch.setattr(facade, "MAX_JSON_BYTES", 16)
    path = tmp_path / "oversized.json"
    path.write_bytes(b'{"value":"123456789"}')

    with pytest.raises(facade.OperatorError, match="bounded regular file"):
        facade._json_object(path)


def test_json_object_rejects_fifo_without_blocking(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    facade = _load("pctdd_nonblocking_json_fifo")
    monkeypatch.setattr(facade, "ROOT", tmp_path)
    path = tmp_path / "status.json"
    os.mkfifo(path)

    with pytest.raises(facade.OperatorError, match="bounded regular file"):
        facade._json_object(path)


def test_json_object_rejects_multiply_linked_runtime_artifact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    facade = _load("pctdd_linked_runtime_json")
    monkeypatch.setattr(facade, "ROOT", tmp_path)
    path = tmp_path / "status.json"
    path.write_text('{"ready":true}\n', encoding="utf-8")
    os.link(path, tmp_path / "status-alias.json")

    with pytest.raises(facade.OperatorError, match="bounded regular file"):
        facade._json_object(path)


def test_json_object_rejects_path_replacement_during_descriptor_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    facade = _load("pctdd_replaced_descriptor_json")
    monkeypatch.setattr(facade, "ROOT", tmp_path)
    path = tmp_path / "status.json"
    replacement = tmp_path / "replacement.json"
    path.write_text('{"generation":1}\n', encoding="utf-8")
    replacement.write_text('{"generation":2}\n', encoding="utf-8")
    real_read = facade.os.read
    replaced = False

    def replacing_read(descriptor: int, count: int) -> bytes:
        nonlocal replaced
        if not replaced:
            replaced = True
            os.replace(replacement, path)
        return real_read(descriptor, count)

    monkeypatch.setattr(facade.os, "read", replacing_read)

    with pytest.raises(facade.OperatorError, match="changed while being read"):
        facade._json_object(path)


def test_runtime_path_rejects_intermediate_symlink_without_touching_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    facade = _load("pctdd_intermediate_symlink_custody")
    repository = tmp_path / "repository"
    outside = tmp_path / "outside"
    repository.mkdir()
    outside.mkdir()
    (repository / "runtime").symlink_to(outside, target_is_directory=True)
    monkeypatch.setattr(facade, "ROOT", repository)

    with pytest.raises(facade.OperatorError, match="custody is unsafe"):
        facade._private_directory(repository / "runtime" / "owner")

    assert list(outside.iterdir()) == []


def test_json_object_rejects_intermediate_symlink_escape(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    facade = _load("pctdd_json_intermediate_symlink")
    repository = tmp_path / "repository"
    outside = tmp_path / "outside"
    repository.mkdir()
    outside.mkdir()
    (outside / "status.json").write_text(json.dumps({"ready": True}))
    (repository / "runtime").symlink_to(outside, target_is_directory=True)
    monkeypatch.setattr(facade, "ROOT", repository)

    with pytest.raises(facade.OperatorError, match="custody is unsafe"):
        facade._json_object(repository / "runtime" / "status.json")


def test_exact_owned_pid_record_is_removed_without_touching_unrelated_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    facade = _load("pctdd_owned_pid_cleanup")
    monkeypatch.setattr(facade, "ROOT", tmp_path)
    path = tmp_path / "target" / "pctdd-quack-owner.pid"
    unrelated = tmp_path / "other-supervisor" / "owner.pid"
    unrelated.parent.mkdir(parents=True)
    unrelated.write_text("do-not-touch\n", encoding="utf-8")
    unrelated_hash = _sha256(unrelated)
    birth = _birth()
    facade._write_owner_process_record(path, _record(facade, birth))

    assert facade._cleanup_owned_owner_pid(path, birth) is True
    assert not path.exists()
    assert unrelated.exists()
    assert _sha256(unrelated) == unrelated_hash


@pytest.mark.parametrize(
    "recorded,observed",
    [
        (_birth(pid=10101), _birth(pid=20202)),
        (_birth(ticks=101), _birth(ticks=202)),
    ],
)
def test_mismatched_pid_or_process_birth_is_preserved(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    recorded: dict[str, object],
    observed: dict[str, object],
) -> None:
    facade = _load("pctdd_mismatched_pid_cleanup")
    monkeypatch.setattr(facade, "ROOT", tmp_path)
    path = tmp_path / "state" / "pctdd-quack-owner.pid"
    facade._write_owner_process_record(path, _record(facade, recorded))
    before = _sha256(path)

    assert facade._cleanup_owned_owner_pid(path, observed) is False
    assert path.exists()
    assert _sha256(path) == before


@pytest.mark.parametrize("matching", [True, False])
def test_state_owner_finally_only_removes_its_exact_process_record(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    matching: bool,
) -> None:
    facade = _load(f"pctdd_state_owner_finally_{matching}")
    monkeypatch.setattr(facade, "ROOT", tmp_path)
    paths = {
        "runtime": tmp_path / "runtime",
        "state": tmp_path / "state",
        "logs": tmp_path / "logs",
        "owner": tmp_path / "quack-owner",
        "database": tmp_path / "control.duckdb",
        "owner_pid": tmp_path / "state" / "pctdd-quack-owner.pid",
    }
    owned = _birth(pid=30303, ticks=40404)
    recorded = owned if matching else _birth(pid=30303, ticks=50505)
    facade._write_owner_process_record(
        paths["owner_pid"],
        _record(facade, recorded),
    )
    before = _sha256(paths["owner_pid"])
    program = SimpleNamespace(
        quack_endpoint="quack:127.0.0.1:27278",
        store_id="control.duckdb",
        endpoint_secret_handle="handle:pctdd-test",
    )
    board = SimpleNamespace(resolved_database_program=lambda: program)
    monkeypatch.setattr(facade, "_load_board", lambda _path: (board, {}))
    monkeypatch.setattr(facade, "_runtime_paths", lambda _board: paths)

    facade._ensure_import_path()
    import ipfs_accelerate_py.agent_supervisor.merge.worktree_lifecycle as lifecycle
    import ipfs_accelerate_py.agent_supervisor.runtime.quack_state_server as runtime

    monkeypatch.setattr(
        lifecycle,
        "current_process_birth",
        lambda: SimpleNamespace(to_dict=lambda: dict(owned)),
    )

    class FailedServer:
        lifecycle = SimpleNamespace(value="failed")

        def start(self):
            raise facade.OperatorError("injected startup failure")

    monkeypatch.setattr(runtime, "build_server", lambda **_kwargs: FailedServer())
    with pytest.raises(facade.OperatorError, match="injected startup failure"):
        facade._serve_state_owner(tmp_path / "config.json")

    assert paths["owner_pid"].exists() is (not matching)
    if not matching:
        assert _sha256(paths["owner_pid"]) == before


def test_live_owner_status_defers_to_authenticated_transport_without_file_open(
    tmp_path: Path,
) -> None:
    facade = _load("pctdd_live_status_no_direct_open")
    owner = {
        "lifecycle": "ready",
        "liveness": "alive",
        "identity": {"server_id": "server:live", "status": "ready"},
    }
    result = facade._cross_check_owner_lifecycle(
        owner,
        {"database": tmp_path / "must-not-open.duckdb"},
    )
    assert result["lifecycle_consistent"] is None
    assert result["authoritative_lifecycle"] == {
        "available": False,
        "reason": "deferred_to_authenticated_live_owner",
        "direct_database_file_open": False,
    }


@pytest.mark.parametrize(
    ("database_status", "owner_liveness"),
    [("starting", "absent"), ("ready", "dead")],
)
def test_nonterminal_database_row_without_live_owner_is_stale(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    database_status: str,
    owner_liveness: str,
) -> None:
    facade = _load(
        f"pctdd_stale_database_owner_{database_status}_{owner_liveness}"
    )
    facade._ensure_import_path()
    import ipfs_accelerate_py.agent_supervisor.runtime.quack_state_server as runtime

    latest = {
        "server_id": "server:stale",
        "store_id": "control.duckdb",
        "database_uuid": "database:stale",
        "process_birth_id": "birth:stale",
        "listen_uri": "quack:127.0.0.1:27278",
        "extension_fingerprint": "sha256:" + "ab" * 32,
        "schema_revision": 1,
        "generation": 7,
        "started_at": "2026-08-30T00:00:00Z",
        "status": database_status,
        "revision": 3,
    }
    monkeypatch.setattr(
        runtime,
        "inspect_state_server_lifecycle",
        lambda **_kwargs: {"available": True, "latest": latest},
    )
    owner = {
        "lifecycle": database_status if owner_liveness == "dead" else "absent",
        "liveness": owner_liveness,
        "identity": dict(latest) if owner_liveness == "dead" else {},
    }

    result = facade._cross_check_owner_lifecycle(
        owner,
        {"database": tmp_path / "control.duckdb"},
    )

    assert result["lifecycle"] == "stale"
    assert result["lifecycle_consistent"] is False
    assert result["reason_code"] == "authoritative_server_owner_not_live"


def test_stopped_status_rejects_database_json_lifecycle_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    facade = _load("pctdd_stopped_status_mismatch")
    facade._ensure_import_path()
    import ipfs_accelerate_py.agent_supervisor.runtime.quack_state_server as runtime

    latest = {
        "server_id": "server:one",
        "store_id": "control.duckdb",
        "database_uuid": "database:one",
        "process_birth_id": "birth:one",
        "listen_uri": "quack:127.0.0.1:27278",
        "extension_fingerprint": "sha256:" + "ab" * 32,
        "schema_revision": 1,
        "generation": 7,
        "started_at": "2026-08-30T00:00:00Z",
        "status": "stopped",
        "stopped_at": "2026-08-30T00:01:00Z",
        "revision": 9,
    }
    monkeypatch.setattr(
        runtime,
        "inspect_state_server_lifecycle",
        lambda **_kwargs: {
            "available": True,
            "authoritative": True,
            "latest": latest,
        },
    )
    owner = {
        "lifecycle": "ready",
        "liveness": "dead",
        "identity": {
            **latest,
            "status": "ready",
        },
    }
    result = facade._cross_check_owner_lifecycle(
        owner,
        {"database": tmp_path / "control.duckdb"},
    )
    assert result["lifecycle_consistent"] is False
    assert result["reason_code"] == "status_projection_lifecycle_mismatch"
    assert result["authoritative_lifecycle"]["latest"]["status"] == "stopped"


def test_stopped_status_rejects_extension_fingerprint_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    facade = _load("pctdd_stopped_extension_mismatch")
    facade._ensure_import_path()
    import ipfs_accelerate_py.agent_supervisor.runtime.quack_state_server as runtime

    latest = {
        "server_id": "server:one",
        "store_id": "control.duckdb",
        "database_uuid": "database:one",
        "process_birth_id": "birth:one",
        "listen_uri": "quack:127.0.0.1:27278",
        "extension_fingerprint": "sha256:" + "ab" * 32,
        "schema_revision": 1,
        "generation": 7,
        "started_at": "2026-08-30T00:00:00Z",
        "status": "stopped",
        "stopped_at": "2026-08-30T00:01:00Z",
        "revision": 9,
    }
    monkeypatch.setattr(
        runtime,
        "inspect_state_server_lifecycle",
        lambda **_kwargs: {"available": True, "latest": latest},
    )
    owner = {
        "lifecycle": "stopped",
        "liveness": "dead",
        "identity": {
            **latest,
            "extension_fingerprint": "sha256:" + "cd" * 32,
            "revision": 8,
        },
    }

    result = facade._cross_check_owner_lifecycle(
        owner,
        {"database": tmp_path / "control.duckdb"},
    )

    assert result["lifecycle_consistent"] is False
    assert result["reason_code"] == "status_projection_lifecycle_mismatch"


def _live_program() -> SimpleNamespace:
    return SimpleNamespace(
        quack_endpoint="quack:127.0.0.1:27278",
        store_id="control.duckdb",
        endpoint_secret_handle="env://PCTDD_TEST_QUACK_TOKEN",
    )


def _live_owner(program: SimpleNamespace) -> dict[str, object]:
    return {
        "lifecycle": "ready",
        "liveness": "alive",
        "identity": {
            "status": "ready",
            "listen_uri": program.quack_endpoint,
            "store_id": program.store_id,
            "secret_handle": program.endpoint_secret_handle,
            "process_birth": _birth(),
        },
    }


def test_operator_seal_check_passes_token_only_to_trusted_live_owner_child(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    facade = _load("pctdd_operator_seal_live_token")
    monkeypatch.setattr(facade, "ROOT", tmp_path)
    program = _live_program()
    board = SimpleNamespace(resolved_database_program=lambda: program)
    paths = {
        "owner": tmp_path / "quack-owner",
        "owner_status": tmp_path / "quack-owner" / "status.json",
    }
    config = tmp_path / "config.json"
    config.write_text("{}\n", encoding="utf-8")
    captured: dict[str, object] = {}
    token = "test_token_material_12345"
    monkeypatch.setattr(facade, "_load_board", lambda _path: (board, {}))
    monkeypatch.setattr(facade, "_runtime_paths", lambda _board: paths)
    monkeypatch.setattr(facade, "_owner_projection", lambda _paths: _live_owner(program))
    monkeypatch.setattr(facade, "_read_owner_token", lambda _path: token)

    def run(argv, *, environment=None, timeout=0.0):
        captured["argv"] = tuple(argv)
        captured["environment"] = dict(environment or {})
        captured["timeout"] = timeout
        return {
            "returncode": 0,
            "json": {"valid": True, "operator_controls_sealed": True},
            "stdout": "",
            "stderr": "",
        }

    monkeypatch.setattr(facade, "_run", run)

    result = facade._require_operator_seal(config)

    environment = captured["environment"]
    assert isinstance(environment, dict)
    assert environment["PCTDD_TEST_QUACK_TOKEN"] == token
    assert environment["IPFS_ACCELERATE_AGENT_QUACK_TOKEN"] == token
    assert "check-sealed" in captured["argv"]
    assert result["valid"] is True
    assert os.environ.get("PCTDD_TEST_QUACK_TOKEN") != token


@pytest.mark.parametrize(
    "lifecycle,liveness",
    [("ready", "dead"), ("starting", "alive"), ("malformed", "unknown")],
)
def test_operator_seal_check_refuses_non_exact_owner_without_token_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    lifecycle: str,
    liveness: str,
) -> None:
    facade = _load(f"pctdd_operator_seal_refuse_{lifecycle}_{liveness}")
    monkeypatch.setattr(facade, "ROOT", tmp_path)
    program = _live_program()
    board = SimpleNamespace(resolved_database_program=lambda: program)
    paths = {"owner": tmp_path / "owner"}
    monkeypatch.setattr(
        facade,
        "_owner_projection",
        lambda _paths: {
            **_live_owner(program),
            "lifecycle": lifecycle,
            "liveness": liveness,
        },
    )
    monkeypatch.setattr(
        facade,
        "_read_owner_token",
        lambda _path: pytest.fail("token vault must not be read"),
    )

    with pytest.raises(facade.OperatorError, match="exact ready\\+alive"):
        facade._operator_seal_check_environment(board, paths)


def test_operator_seal_check_uses_scrubbed_environment_when_stopped(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    facade = _load("pctdd_operator_seal_stopped_environment")
    monkeypatch.setattr(facade, "ROOT", tmp_path)
    program = _live_program()
    board = SimpleNamespace(resolved_database_program=lambda: program)
    monkeypatch.setattr(
        facade,
        "_owner_projection",
        lambda _paths: {"lifecycle": "stopped", "liveness": "dead", "identity": {}},
    )
    monkeypatch.setenv("PCTDD_TEST_QUACK_TOKEN", "must_be_scrubbed_123")
    monkeypatch.setenv("IPFS_ACCELERATE_AGENT_QUACK_TOKEN", "must_be_scrubbed_456")

    environment = facade._operator_seal_check_environment(
        board,
        {"owner": tmp_path / "owner"},
    )

    assert "PCTDD_TEST_QUACK_TOKEN" not in environment
    assert "IPFS_ACCELERATE_AGENT_QUACK_TOKEN" not in environment


def test_real_launch_recovers_owner_before_seal_preflight(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    facade = _load("pctdd_real_launch_owner_before_preflight")
    config = tmp_path / "config.json"
    config.write_text("{}\n", encoding="utf-8")
    board = SimpleNamespace()
    paths = {"runtime": tmp_path / "runtime"}
    calls: list[str] = []

    def load_board(_path: Path):
        calls.append("load_board")
        return board, {}

    def start_owner(_board, _paths, *, timeout: float):
        calls.append("start_owner")
        assert _board is board
        assert _paths is paths
        assert timeout == 30.0
        return {"started": True, "ready": True}

    def rejected_preflight(_path: Path):
        calls.append("preflight")
        raise facade.OperatorError("injected sealed preflight rejection")

    monkeypatch.setattr(facade, "_load_board", load_board)
    monkeypatch.setattr(facade, "_runtime_paths", lambda _board: paths)
    monkeypatch.setattr(facade, "_start_owner", start_owner)
    monkeypatch.setattr(facade, "preflight", rejected_preflight)
    monkeypatch.setattr(
        facade,
        "_run",
        lambda *_args, **_kwargs: pytest.fail(
            "scheduler must not launch after a preflight rejection"
        ),
    )

    with pytest.raises(facade.OperatorError, match="sealed preflight rejection"):
        facade.launch(config, dry_run=False, monitor_seconds=30.0)

    assert calls == ["load_board", "start_owner", "preflight"]


def test_dry_run_remains_owner_side_effect_free(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    facade = _load("pctdd_dry_run_never_starts_owner")
    config = tmp_path / "config.json"
    config.write_text("{}\n", encoding="utf-8")
    calls: list[str] = []

    def accepted_preflight(_path: Path):
        calls.append("preflight")
        return {"configured_board": {"valid": True}}

    def run_scheduler(argv, **_kwargs):
        calls.append("scheduler_dry_run")
        assert "--dry-run" in argv
        return {
            "returncode": 0,
            "json": {"valid": True, "mode": "dry_run"},
            "stdout": "",
            "stderr": "",
        }

    monkeypatch.setattr(facade, "preflight", accepted_preflight)
    monkeypatch.setattr(
        facade,
        "_start_owner",
        lambda *_args, **_kwargs: pytest.fail("dry-run must not start Quack"),
    )
    monkeypatch.setattr(
        facade,
        "_load_board",
        lambda *_args, **_kwargs: pytest.fail(
            "preflight owns dry-run board loading and validation"
        ),
    )
    monkeypatch.setattr(facade, "_run", run_scheduler)

    result = facade.launch(config, dry_run=True, monitor_seconds=0.0)

    assert result["mode"] == "dry_run"
    assert result["state_owner_started"] is False
    assert calls == ["preflight", "scheduler_dry_run"]


def test_invalid_real_monitor_window_has_no_owner_or_preflight_side_effect(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    facade = _load("pctdd_invalid_real_monitor_window")
    config = tmp_path / "config.json"
    config.write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(
        facade,
        "_load_board",
        lambda *_args, **_kwargs: pytest.fail("invalid input must fail before board load"),
    )
    monkeypatch.setattr(
        facade,
        "_start_owner",
        lambda *_args, **_kwargs: pytest.fail("invalid input must not start Quack"),
    )
    monkeypatch.setattr(
        facade,
        "preflight",
        lambda *_args, **_kwargs: pytest.fail("invalid input must not run preflight"),
    )

    with pytest.raises(facade.OperatorError, match="monitor-seconds must be positive"):
        facade.launch(config, dry_run=False, monitor_seconds=0.0)


def test_real_launch_revalidates_owner_binding_after_preflight(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    facade = _load("pctdd_real_launch_revalidates_owner_binding")
    config = tmp_path / "config.json"
    config.write_text("{}\n", encoding="utf-8")
    board = SimpleNamespace()
    changed_board = SimpleNamespace()
    paths = {"runtime": tmp_path / "runtime-a"}
    changed_paths = {"runtime": tmp_path / "runtime-b"}
    loaded = iter(((board, {"generation": 8}), (changed_board, {"generation": 9})))
    monkeypatch.setattr(facade, "_load_board", lambda _path: next(loaded))
    monkeypatch.setattr(
        facade,
        "_runtime_paths",
        lambda value: paths if value is board else changed_paths,
    )
    monkeypatch.setattr(
        facade,
        "_start_owner",
        lambda *_args, **_kwargs: {"started": True, "ready": True},
    )
    monkeypatch.setattr(
        facade,
        "preflight",
        lambda _path: {"configured_board": {"valid": True}},
    )
    monkeypatch.setattr(
        facade,
        "_run",
        lambda *_args, **_kwargs: pytest.fail(
            "scheduler must not launch with a changed owner binding"
        ),
    )

    with pytest.raises(facade.OperatorError, match="changed during owner recovery"):
        facade.launch(config, dry_run=False, monitor_seconds=30.0)


def _canonical_runtime_authority(facade) -> dict[str, object]:
    identities = [
        (f"task-cid-{index:03d}", alias, index + 1)
        for index, alias in enumerate(facade.CANONICAL_TASK_ALIASES)
    ]
    return {
        "authenticated_query": True,
        "task_count": 54,
        "task_aliases": list(facade.CANONICAL_TASK_ALIASES),
        "task_ordinals": list(range(1, 55)),
        "task_identity_rows": identities,
        "task_identity_unique": True,
        "operator_task_status": "completed",
        "completed_count": 17,
    }


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("authenticated_query", False),
        ("task_count", 55),
        ("task_aliases", [f"PCTDD-{index:03d}" for index in range(1, 55)]),
        ("task_ordinals", list(range(0, 54))),
        ("task_identity_unique", False),
        ("operator_task_status", "todo"),
        ("operator_task_status", "skipped"),
        ("operator_task_status", "complete"),
        ("operator_task_status", "done"),
        ("task_count", {"malformed": True}),
        ("task_aliases", "PCTDD-000"),
        ("task_ordinals", [True, *range(2, 55)]),
        ("task_identity_rows", [("wrong-cid", "PCTDD-000", 1)]),
    ],
)
def test_runtime_resume_rejects_noncanonical_or_unaccepted_authority(
    field: str,
    value: object,
) -> None:
    facade = _load(f"pctdd_resume_authority_{field}_{str(value)[:8]}")
    authority = _canonical_runtime_authority(facade)
    authority[field] = value
    expected = tuple(authority.get("task_identity_rows", ()))
    if field == "task_identity_rows":
        expected = tuple(_canonical_runtime_authority(facade)["task_identity_rows"])

    with pytest.raises(facade.OperatorError):
        facade._require_runtime_resume_authority(
            authority,
            expected_task_identities=expected,
        )


def test_runtime_resume_propagates_current_tree_preflight_rejection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    facade = _load("pctdd_resume_current_tree_preflight_rejection")
    config = tmp_path / "config.json"
    board = SimpleNamespace()
    paths = {"state": tmp_path / "state"}
    monkeypatch.setattr(
        facade,
        "_start_owner",
        lambda *_args, **_kwargs: {"started": True, "ready": True},
    )
    monkeypatch.setattr(
        facade,
        "_configured_board_preflight",
        lambda _path: (_ for _ in ()).throw(
            facade.OperatorError("protected control preflight rejected")
        ),
    )
    monkeypatch.setattr(
        facade,
        "_authenticated_projection",
        lambda *_args, **_kwargs: pytest.fail(
            "rejected current-tree controls must not reach task admission"
        ),
    )
    monkeypatch.setattr(
        facade,
        "_launch_scheduler_and_monitor",
        lambda *_args, **_kwargs: pytest.fail(
            "rejected current-tree controls must not launch the scheduler"
        ),
    )

    with pytest.raises(facade.OperatorError, match="protected control"):
        facade._resume_locked(
            config,
            board=board,
            payload={"generation": 8},
            paths=paths,
            monitor_seconds=30.0,
        )


def test_runtime_resume_adopts_healthy_existing_scheduler_idempotently(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    facade = _load("pctdd_resume_existing_scheduler")
    config = tmp_path / "config.json"
    board = SimpleNamespace()
    payload = {"generation": 8}
    paths = {"state": tmp_path / "state"}
    authority = _canonical_runtime_authority(facade)
    monkeypatch.setattr(
        facade,
        "_start_owner",
        lambda *_args, **_kwargs: {
            "started": False,
            "already_running": True,
            "ready": True,
        },
    )
    monkeypatch.setattr(
        facade,
        "_configured_board_preflight",
        lambda _path: {"valid": True, "checks": []},
    )
    monkeypatch.setattr(facade, "_load_board", lambda _path: (board, payload))
    monkeypatch.setattr(facade, "_runtime_paths", lambda _board: paths)
    monkeypatch.setattr(
        facade,
        "_authenticated_projection",
        lambda *_args, **_kwargs: authority,
    )
    monkeypatch.setattr(
        facade,
        "_configured_task_identities",
        lambda _board: tuple(authority["task_identity_rows"]),
    )
    monkeypatch.setattr(
        facade,
        "_supervisor_projection",
        lambda *_args, **_kwargs: {
            "master_pid": 41001,
            "master_alive": True,
            "ready": True,
            "healthy_lane_count": 4,
            "expected_lane_count": 4,
        },
    )
    monkeypatch.setattr(
        facade,
        "_launch_scheduler_and_monitor",
        lambda *_args, **_kwargs: pytest.fail(
            "a healthy existing scheduler must not be launched twice"
        ),
    )
    monkeypatch.setattr(
        facade,
        "_read_owner_token",
        lambda *_args, **_kwargs: pytest.fail(
            "idempotent scheduler adoption must not reread a launch token"
        ),
    )

    result = facade._resume_locked(
        config,
        board=board,
        payload=payload,
        paths=paths,
        monitor_seconds=30.0,
    )

    assert result["launched"] is False
    assert result["already_running"] is True
    assert result["runtime_admission"]["canonical_task_count"] == 54


def test_runtime_resume_refuses_duplicate_when_existing_scheduler_is_unhealthy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    facade = _load("pctdd_resume_unhealthy_existing_scheduler")
    config = tmp_path / "config.json"
    board = SimpleNamespace()
    payload = {"generation": 8}
    paths = {"state": tmp_path / "state"}
    authority = _canonical_runtime_authority(facade)
    monkeypatch.setattr(
        facade,
        "_start_owner",
        lambda *_args, **_kwargs: {
            "started": False,
            "already_running": True,
            "ready": True,
        },
    )
    monkeypatch.setattr(
        facade,
        "_configured_board_preflight",
        lambda _path: {"valid": True, "checks": []},
    )
    monkeypatch.setattr(facade, "_load_board", lambda _path: (board, payload))
    monkeypatch.setattr(facade, "_runtime_paths", lambda _board: paths)
    monkeypatch.setattr(
        facade,
        "_authenticated_projection",
        lambda *_args, **_kwargs: authority,
    )
    monkeypatch.setattr(
        facade,
        "_configured_task_identities",
        lambda _board: tuple(authority["task_identity_rows"]),
    )
    monkeypatch.setattr(
        facade,
        "_supervisor_projection",
        lambda *_args, **_kwargs: {
            "master_pid": 41001,
            "master_alive": True,
            "ready": False,
            "healthy_lane_count": 3,
            "expected_lane_count": 4,
        },
    )
    monkeypatch.setattr(
        facade,
        "_launch_scheduler_and_monitor",
        lambda *_args, **_kwargs: pytest.fail(
            "a live unhealthy scheduler must not be duplicated or reclaimed"
        ),
    )

    with pytest.raises(facade.OperatorError, match="live but not healthy"):
        facade._resume_locked(
            config,
            board=board,
            payload=payload,
            paths=paths,
            monitor_seconds=30.0,
        )


def test_runtime_resume_serializes_timer_and_manual_ensure_calls(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    facade = _load("pctdd_resume_operator_serialization")
    config = tmp_path / "config.json"
    board = SimpleNamespace()
    payload = {"generation": 8}
    paths = {"state": tmp_path / "state"}
    observed: dict[str, object] = {}
    monkeypatch.setattr(facade, "_load_board", lambda _path: (board, payload))
    monkeypatch.setattr(facade, "_runtime_paths", lambda _board: paths)
    monkeypatch.setattr(facade, "_private_directory", lambda path: path)
    monkeypatch.setattr(
        facade,
        "_resume_locked",
        lambda *_args, **_kwargs: {"command": "resume", "already_running": True},
    )
    facade._ensure_import_path()
    import ipfs_accelerate_py.agent_supervisor.merge.checkout_lock as checkout_lock

    @contextmanager
    def serialized(path: Path, *, timeout_seconds: float):
        observed["path"] = path
        observed["timeout_seconds"] = timeout_seconds
        observed["held"] = True
        yield
        observed["released"] = True

    monkeypatch.setattr(checkout_lock, "serialized_lock_update", serialized)

    result = facade.resume(config, monitor_seconds=30.0)

    assert result["already_running"] is True
    assert observed == {
        "path": paths["state"] / "pctdd-runtime-resume.lock",
        "timeout_seconds": 60.0,
        "held": True,
        "released": True,
    }


def test_runtime_resume_lock_contention_fails_with_bounded_typed_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    facade = _load("pctdd_resume_operator_lock_timeout")
    config = tmp_path / "config.json"
    board = SimpleNamespace()
    payload = {"generation": 8}
    paths = {"state": tmp_path / "state"}
    monkeypatch.setattr(facade, "_load_board", lambda _path: (board, payload))
    monkeypatch.setattr(facade, "_runtime_paths", lambda _board: paths)
    monkeypatch.setattr(facade, "_private_directory", lambda path: path)
    facade._ensure_import_path()
    import ipfs_accelerate_py.agent_supervisor.merge.checkout_lock as checkout_lock

    @contextmanager
    def contended(_path: Path, *, timeout_seconds: float):
        assert timeout_seconds == 60.0
        raise TimeoutError("injected contention")
        yield  # pragma: no cover

    monkeypatch.setattr(checkout_lock, "serialized_lock_update", contended)
    monkeypatch.setattr(
        facade,
        "_resume_locked",
        lambda *_args, **_kwargs: pytest.fail(
            "lock contention must not reach owner or scheduler recovery"
        ),
    )

    with pytest.raises(facade.OperatorError, match="timed out serializing"):
        facade.resume(config, monitor_seconds=30.0)


def test_runtime_resume_cli_is_explicit_and_rejects_invalid_window(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    facade = _load("pctdd_resume_cli_surface")
    parsed = facade._parser().parse_args(
        [
            "--config",
            str(tmp_path / "config.json"),
            "resume",
            "--monitor-seconds",
            "45",
        ]
    )

    assert parsed.command == "resume"
    assert parsed.monitor_seconds == 45.0
    monkeypatch.setattr(
        facade,
        "_load_board",
        lambda *_args, **_kwargs: pytest.fail(
            "invalid resume input must fail before board or state access"
        ),
    )
    with pytest.raises(facade.OperatorError, match="monitor-seconds must be positive"):
        facade.resume(tmp_path / "config.json", monitor_seconds=0.0)


def test_scheduler_launch_keeps_private_token_out_of_argv_and_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    facade = _load("pctdd_resume_private_token_boundary")
    monkeypatch.setattr(facade, "ROOT", tmp_path)
    token = "private_quack_token_12345"
    program = SimpleNamespace(endpoint_secret_handle="env://PCTDD_TEST_TOKEN")
    board = SimpleNamespace(resolved_database_program=lambda: program)
    paths = {"owner": tmp_path / "owner"}
    captured: dict[str, object] = {}
    monkeypatch.setattr(facade, "MIN_STABLE_HEALTH_SECONDS", 0.0)
    monkeypatch.setattr(facade, "_read_owner_token", lambda _path: token)

    def environment(*, token: str, secret_handle: str):
        captured["environment_token"] = token
        captured["secret_handle"] = secret_handle
        return {"PCTDD_TEST_TOKEN": token}

    def run(argv, *, environment, timeout: float):
        captured["argv"] = tuple(argv)
        captured["child_environment"] = dict(environment)
        assert timeout == 900.0
        return {
            "returncode": 0,
            "json": {"valid": True, "detached_pid": 41001},
            "stdout": "",
            "stderr": "",
        }

    status_payload = {
        "operational_ready": True,
        "program_state": "running",
        "task_authority": {"in_progress_count": 1, "completed_count": 17},
        "supervisor": {
            "master_pid": 41001,
            "lanes": [
                {"supervisor_pid": 41002, "daemon_pid": 41003},
            ],
        },
    }
    monkeypatch.setattr(facade, "_python_environment", environment)
    monkeypatch.setattr(facade, "_run", run)
    monkeypatch.setattr(facade, "status", lambda _path: status_payload)
    monkeypatch.setattr(facade.time, "sleep", lambda _seconds: None)

    result = facade._launch_scheduler_and_monitor(
        tmp_path / "config.json",
        board=board,
        paths=paths,
        owner={"ready": True},
        initial_authority={"completed_count": 17},
        monitor_seconds=30.0,
        command="resume",
        mode="runtime_resume",
        runtime_admission={"canonical_task_population": True},
    )

    assert token not in " ".join(captured["argv"])
    assert token not in json.dumps(result, sort_keys=True)
    assert captured["environment_token"] == token
    assert result["already_running"] is False


def test_secret_echo_rejection_never_reflects_the_secret() -> None:
    facade = _load("pctdd_resume_secret_echo_rejection")
    token = "private_quack_token_67890"

    with pytest.raises(facade.OperatorError) as captured:
        facade._reject_secret_echo({"stderr": f"accidental {token}"}, token)

    assert token not in str(captured.value)


@pytest.mark.parametrize("mismatch", [None, "listen_uri", "extension_fingerprint"])
def test_authenticated_projection_binds_live_endpoint_and_extension(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mismatch: str | None,
) -> None:
    facade = _load(f"pctdd_authenticated_full_identity_{mismatch}")
    monkeypatch.setattr(facade, "ROOT", tmp_path)
    program = _live_program()
    board = SimpleNamespace(resolved_database_program=lambda: program)
    identity = {
        "server_id": "server:live",
        "store_id": program.store_id,
        "database_uuid": "database:live",
        "process_birth_id": "birth:live",
        "process_birth": _birth(),
        "listen_uri": program.quack_endpoint,
        "extension_fingerprint": "sha256:" + "ef" * 32,
        "schema_revision": 3,
        "generation": 11,
        "started_at": "2026-08-30T00:00:00Z",
        "status": "ready",
        "revision": 0,
        "secret_handle": program.endpoint_secret_handle,
    }
    observed = dict(identity)
    observed["revision"] = 1
    if mismatch is not None:
        observed[mismatch] = (
            "quack:127.0.0.1:27279"
            if mismatch == "listen_uri"
            else "sha256:" + "11" * 32
        )
    row = tuple(
        observed[key]
        for key in (
            "server_id",
            "store_id",
            "database_uuid",
            "process_birth_id",
            "listen_uri",
            "extension_fingerprint",
            "schema_revision",
            "generation",
            "started_at",
            "status",
            "revision",
        )
    )

    class Connection:
        def execute(self, _query, _parameters):
            return self

        def fetchone(self):
            return row

        def close(self):
            return None

    monkeypatch.setattr(
        facade,
        "_owner_projection",
        lambda _paths: {
            "lifecycle": "ready",
            "liveness": "alive",
            "identity": identity,
        },
    )
    monkeypatch.setattr(facade, "_read_owner_token", lambda _path: "test_token_123")
    monkeypatch.setattr(facade, "_task_projection", lambda _connection: {})
    facade._ensure_import_path()
    import ipfs_accelerate_py.agent_supervisor.task_sources.duckdb_state as state

    monkeypatch.setattr(
        state,
        "open_quack_transport_connection",
        lambda _endpoint, token: Connection(),
    )
    paths = {"owner": tmp_path / "owner"}

    if mismatch is None:
        result = facade._authenticated_projection(board, paths)
        assert result["identity"]["listen_uri"] == program.quack_endpoint
        assert result["identity"]["extension_fingerprint"] == identity[
            "extension_fingerprint"
        ]
    else:
        with pytest.raises(facade.OperatorError, match=mismatch):
            facade._authenticated_projection(board, paths)
