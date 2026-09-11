"""Production native resume calls assessment and maintenance under its guards."""

import importlib.util
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
import pytest
from ipfs_accelerate_py.agent_supervisor.runtime import (
    accepted_submodule_maintenance as maintenance,
)
from ipfs_accelerate_py.agent_supervisor.merge import checkout_lock


def facade():
    path = (
        Path(__file__).resolve().parents[3]
        / "scripts/ops/agent_supervisor/parallel_content_sealing_proof_carrying_tdd.py"
    )
    spec = importlib.util.spec_from_file_location("native_accepted_dependency_resume", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def setup(tmp_path, monkeypatch):
    f = facade()
    board = SimpleNamespace(configuration_root="exact")
    payload = {"accepted": "config"}
    paths = {"state": tmp_path / "state", "owner": tmp_path / "owner"}
    events = []
    held = {"resume": False}
    monkeypatch.setattr(f, "_load_board", lambda p: (board, payload))
    monkeypatch.setattr(f, "_runtime_paths", lambda b: paths)
    monkeypatch.setattr(f, "_ensure_import_path", lambda: None)
    monkeypatch.setattr(f, "_private_directory", lambda p: events.append("mkdir"))

    @contextmanager
    def serialized(*a, **k):
        held["resume"] = True
        events.append("resume_lock")
        yield
        held["resume"] = False
        events.append("resume_unlock")

    monkeypatch.setattr(checkout_lock, "serialized_lock_update", serialized)

    def resume(*a, **k):
        assert held["resume"]
        events.append("normal_resume")
        return {"command": "resume"}

    monkeypatch.setattr(f, "_resume_locked", resume)
    return f, board, payload, paths, events, held


def test_actual_public_resume_assesses_before_state_then_reassesses_under_guards(
    setup, monkeypatch
):
    f, board, payload, paths, events, held = setup

    def rejected(path):
        events.append("initial_preflight")
        raise f.OperatorError("checkout mismatch")

    monkeypatch.setattr(f, "_configured_board_preflight", rejected)

    def assessment(b):
        assert b is board and not held["resume"] and "mkdir" not in events
        events.append("pure_assessment")
        return {"needed": True}

    monkeypatch.setattr(maintenance, "assess_accepted_configured_submodule", assessment)

    def maintain(*a, **k):
        assert held["resume"]
        events.append("guarded_maintenance")
        return {"changed": True}

    monkeypatch.setattr(f, "_maintain_accepted_submodule_before_resume", maintain)
    assert f.resume(Path("/config"), monitor_seconds=1)["command"] == "resume"
    assert events == [
        "initial_preflight",
        "pure_assessment",
        "mkdir",
        "resume_lock",
        "guarded_maintenance",
        "normal_resume",
        "resume_unlock",
    ]


def test_unrelated_failed_assessment_does_not_create_state_or_resume(setup, monkeypatch):
    f, board, payload, paths, events, held = setup
    monkeypatch.setattr(
        f,
        "_configured_board_preflight",
        lambda p: (_ for _ in ()).throw(f.OperatorError("source rejected")),
    )
    monkeypatch.setattr(
        maintenance,
        "assess_accepted_configured_submodule",
        lambda b: (_ for _ in ()).throw(RuntimeError("unrelated failure")),
    )
    with pytest.raises(f.OperatorError, match="source rejected"):
        f.resume(Path("/config"), monitor_seconds=1)
    assert events == []


def test_valid_preflight_never_calls_maintenance(setup, monkeypatch):
    f, board, payload, paths, events, held = setup
    monkeypatch.setattr(f, "_configured_board_preflight", lambda p: {"valid": True})
    monkeypatch.setattr(
        maintenance,
        "assess_accepted_configured_submodule",
        lambda b: pytest.fail("unexpected assessment"),
    )
    monkeypatch.setattr(
        f,
        "_maintain_accepted_submodule_before_resume",
        lambda *a, **k: pytest.fail("unexpected source effect"),
    )
    f.resume(Path("/config"), monitor_seconds=1)
    assert events == ["mkdir", "resume_lock", "normal_resume", "resume_unlock"]


def test_apply_time_maintenance_refusal_prevents_owner_start_or_resume(setup, monkeypatch):
    f, board, payload, paths, events, held = setup
    monkeypatch.setattr(
        f,
        "_configured_board_preflight",
        lambda p: (_ for _ in ()).throw(f.OperatorError("checkout mismatch")),
    )
    monkeypatch.setattr(
        maintenance, "assess_accepted_configured_submodule", lambda b: {"needed": True}
    )
    monkeypatch.setattr(
        f,
        "_maintain_accepted_submodule_before_resume",
        lambda *a, **k: (_ for _ in ()).throw(f.OperatorError("current custody changed")),
    )
    with pytest.raises(f.OperatorError, match="current custody changed"):
        f.resume(Path("/config"), monitor_seconds=1)
    assert "normal_resume" not in events


def test_real_operator_helper_orders_owner_then_mutation_guard_and_releases(setup, monkeypatch):
    from ipfs_accelerate_py.agent_supervisor.task_sources import duckdb_state

    f, board, payload, paths, events, held = setup

    class Winner:
        def acquire(self):
            events.append("owner_lock")
            return True

        def release(self):
            events.append("owner_unlock")

    monkeypatch.setattr(f, "_owner_recovery_lock", lambda path: Winner())

    @contextmanager
    def mutation(path, **kw):
        events.append("mutation_lock")
        yield
        events.append("mutation_unlock")

    monkeypatch.setattr(duckdb_state, "exclusive_file_lock", mutation)

    def maintain(b, *, archive_root, custody_guard):
        assert b is board
        custody_guard()
        events.append("native_maintenance")
        return {"changed": True}

    monkeypatch.setattr(maintenance, "maintain_accepted_configured_submodule", maintain)
    f._maintain_accepted_submodule_before_resume(
        Path("/config"), board=board, payload=payload, paths=paths
    )
    assert events == [
        "owner_lock",
        "mutation_lock",
        "native_maintenance",
        "mutation_unlock",
        "owner_unlock",
    ]
