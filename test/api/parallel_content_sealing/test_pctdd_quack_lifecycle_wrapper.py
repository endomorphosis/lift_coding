"""Focused PCTDD wrapper tests for Quack lifecycle recovery controls."""

from __future__ import annotations

import hashlib
import importlib.util
import os
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
