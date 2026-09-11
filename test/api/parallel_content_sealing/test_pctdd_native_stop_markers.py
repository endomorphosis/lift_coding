"""Configured native stops block every new start, without granting task authority."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[3]
NATIVE_ROOT = "/home/barberb/lift_coding/.worktrees/pctdd-g9-orphan-recovery"
MARKERS = ("HOLD", "OPERATOR_STOP", "watchdog.disabled", "watchdog.hold")


def load(installer=False):
    name = "parallel_content_sealing_proof_carrying_tdd" + ("_user_systemd" if installer else "")
    spec = importlib.util.spec_from_file_location(name + "_stop_test", ROOT / "scripts/ops/agent_supervisor" / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("name", MARKERS)
@pytest.mark.parametrize("kind", ["file", "directory", "dangling_symlink"])
def test_public_resume_rejects_existing_stop_before_state_or_runtime_effects(tmp_path, monkeypatch, name, kind):
    f = load()
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    marker = runtime / name
    if kind == "file":
        marker.write_text("operator custody\n")
    elif kind == "directory":
        marker.mkdir()
    else:
        marker.symlink_to("absent")
    board = SimpleNamespace()
    paths = {"runtime": runtime, "state": tmp_path / "absent-state"}
    monkeypatch.setattr(f, "_load_board", lambda p: (board, {}))
    monkeypatch.setattr(f, "_runtime_paths", lambda b: paths)
    monkeypatch.setattr(f, "_configured_board_preflight", lambda p: {"valid": True})
    monkeypatch.setattr(f, "_private_directory", lambda p: pytest.fail("stop must precede state creation"))
    monkeypatch.setattr(f, "_ensure_import_path", lambda: pytest.fail("stop must precede runtime recovery imports"))
    with pytest.raises(f.OperatorError, match="native start blocked by stop marker: " + name):
        f.resume(tmp_path / "config.json")
    assert marker.lstat()
    assert not paths["state"].exists()
    marker.rmdir() if kind == "directory" else marker.unlink()
    f._require_native_start_allowed(paths)


def test_unobservable_marker_fails_closed(tmp_path, monkeypatch):
    f = load()
    def unreadable(path):
        raise PermissionError("private filesystem detail")
    monkeypatch.setattr(Path, "lstat", unreadable)
    with pytest.raises(f.OperatorError, match="^native stop marker observation failed$"):
        f._require_native_start_allowed({"runtime": tmp_path})


def test_stop_appearing_while_waiting_for_native_resume_fence_prevents_maintenance(tmp_path, monkeypatch):
    f = load()
    paths = {"runtime": tmp_path, "state": tmp_path / "state"}
    board = SimpleNamespace()
    monkeypatch.setattr(f, "_load_board", lambda p: (board, {}))
    monkeypatch.setattr(f, "_runtime_paths", lambda b: paths)
    monkeypatch.setattr(f, "_configured_board_preflight", lambda p: {"valid": True})
    monkeypatch.setattr(f, "_private_directory", lambda p: p)
    monkeypatch.setattr(f, "_resume_locked", lambda *a, **kw: pytest.fail("stopped under resume fence"))
    f._ensure_import_path()
    from ipfs_accelerate_py.agent_supervisor.merge import checkout_lock
    held = []
    @contextmanager
    def lock(*a, **kw):
        (tmp_path / "watchdog.hold").touch()
        held.append("held")
        try:
            yield
        finally:
            held.append("released")
    monkeypatch.setattr(checkout_lock, "serialized_lock_update", lock)
    with pytest.raises(f.OperatorError, match="stop marker: watchdog.hold"):
        f.resume(tmp_path / "config.json")
    assert held == ["held", "released"]


def test_owner_and_scheduler_entrypoints_reject_stop_before_any_child_or_credentials(tmp_path, monkeypatch):
    f = load()
    (tmp_path / "OPERATOR_STOP").touch()
    paths = {"runtime": tmp_path}
    board = SimpleNamespace(resolved_database_program=lambda: pytest.fail("must precede owner dependency access"))
    monkeypatch.setattr(f, "_run", lambda *a, **kw: pytest.fail("must not launch"))
    with pytest.raises(f.OperatorError, match="stop marker: OPERATOR_STOP"):
        f._start_owner(board, paths, timeout=1)
    with pytest.raises(f.OperatorError, match="stop marker: OPERATOR_STOP"):
        f._launch_scheduler_and_monitor(tmp_path / "config.json", board=board, paths=paths, owner={}, initial_authority={}, monitor_seconds=1, command="resume", mode="real")


def canonical_units(module):
    units = module._render_units()
    units[module.SERVICE_NAME] = units[module.SERVICE_NAME].replace(str(module.ROOT).encode(), NATIVE_ROOT.encode()).replace(str(module._python_executable()).encode(), b"/usr/bin/python3.12")
    return units


def test_generated_unit_uses_exact_configured_runtime_and_same_four_markers():
    m = load(True)
    f = load()
    relative = json.loads(m.SCHEDULER_CONFIG.read_bytes())["runtime_paths"]["root"]
    service = m._render_units()[m.SERVICE_NAME].decode()
    assert f.NATIVE_STOP_MARKERS == MARKERS
    assert [x for x in service.splitlines() if x.startswith("Condition")] == ["ConditionPathExists=!" + str(m.ROOT / relative / name) for name in MARKERS]
    assert "KillMode=process" in service


def test_both_exact_prior_native_service_revisions_remain_migratable():
    m = load(True)
    units = canonical_units(m)
    predecessors = m._migratable_unit_payloads(units)[m.SERVICE_NAME]
    assert len(predecessors) == 2
    assert [hashlib.sha256(x).hexdigest() for x in predecessors] == ["b153a19680f7c700d07ccc87bafc2bd587911a0dbd60c8cea6128eea3c9d2ee8", m.PRE_STOP_MARKER_SERVICE_SHA256]
    assert all(b"ConditionPathExists" not in x for x in predecessors)
    units[m.SERVICE_NAME] += b"# unknown revision\n"
    with pytest.raises(m.EnsureError, match="sealed_predecessor_derivation_mismatch"):
        m._migratable_unit_payloads(units)


def test_unit_renderer_rejects_injected_or_removed_stop_conditions(tmp_path, monkeypatch):
    m = load(True)
    path = tmp_path / "service.in"
    path.write_text(m.SERVICE_TEMPLATE.read_text().replace("@STOP_MARKER_CONDITIONS@", "@STOP_MARKER_CONDITIONS@\nConditionPathExists=!/foreign"))
    monkeypatch.setattr(m, "SERVICE_TEMPLATE", path)
    with pytest.raises(m.EnsureError, match="service_template_claim_boundary_invalid"):
        m._render_units()


@pytest.mark.parametrize("root", ["../foreign", "/foreign", None, 123])
def test_unit_renderer_refuses_invalid_configured_runtime_root(tmp_path, monkeypatch, root):
    m = load(True)
    config = tmp_path / "config.json"
    config.write_text(json.dumps({"runtime_paths": {"root": root}}))
    with pytest.raises(m.EnsureError, match="configured_stop_marker_root_invalid"):
        m._stop_marker_conditions(config)


@pytest.mark.parametrize("boundary", ["owner_fence", "opened_owner_log"])
def test_late_owner_stop_preserves_database_and_releases_winner_without_spawn(tmp_path, monkeypatch, boundary):
    f = load()
    monkeypatch.setattr(f, "ROOT", tmp_path)
    paths = {name: tmp_path / name for name in ("runtime", "state", "logs", "owner", "database")}
    paths.update(owner_log=paths["logs"] / "owner.log", owner_pid=paths["state"] / "owner.pid")
    paths["database"].write_bytes(b"retained opaque database bytes")
    before = paths["database"].read_bytes()
    board = SimpleNamespace(config_path=tmp_path / "config.json", resolved_database_program=lambda: SimpleNamespace(endpoint_secret_handle="env://NATIVE_TEST"))
    events = []
    class Winner:
        def acquire(self):
            events.append("acquired")
            if boundary == "owner_fence":
                (paths["runtime"] / "HOLD").touch()
            return True
        def release(self):
            events.append("released")
    monkeypatch.setattr(f, "_owner_recovery_lock", lambda path: Winner())
    monkeypatch.setattr(f, "_owner_projection", lambda p: {"lifecycle": "stopped", "liveness": "dead"})
    monkeypatch.setattr(f.subprocess, "Popen", lambda *a, **kw: pytest.fail("late stop forbids new owner"))
    real_open = f._open_private_owner_log
    def opened(path):
        fd = real_open(path)
        (paths["runtime"] / "HOLD").touch()
        return fd
    if boundary == "opened_owner_log":
        monkeypatch.setattr(f, "_open_private_owner_log", opened)
    with pytest.raises(f.OperatorError, match="stop marker: HOLD"):
        f._start_owner(board, paths, timeout=1)
    assert events == ["acquired", "released"]
    assert paths["database"].read_bytes() == before
    assert not paths["owner_pid"].exists()


def test_late_scheduler_stop_after_token_read_forbids_dispatch(tmp_path, monkeypatch):
    f = load()
    program = SimpleNamespace(endpoint_secret_handle="env://NATIVE_TEST")
    board = SimpleNamespace(resolved_database_program=lambda: program)
    paths = {"runtime": tmp_path, "owner": tmp_path / "owner"}
    def token(path):
        (tmp_path / "watchdog.disabled").touch()
        return "test-only-unissued-token"
    monkeypatch.setattr(f, "_read_owner_token", token)
    monkeypatch.setattr(f, "_token_path", lambda *a: tmp_path / "never-read")
    monkeypatch.setattr(f, "_run", lambda *a, **kw: pytest.fail("late stop forbids dispatch"))
    with pytest.raises(f.OperatorError, match="stop marker: watchdog.disabled"):
        f._launch_scheduler_and_monitor(tmp_path / "config.json", board=board, paths=paths, owner={}, initial_authority={}, monitor_seconds=1, command="resume", mode="real")
