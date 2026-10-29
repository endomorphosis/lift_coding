"""The repair lane must stay leased, selectable and independent of VOG state."""

from __future__ import annotations

import json
import hashlib
import os
import socket
import shutil
import shlex
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import swissknife_visual_functional_supervisor as supervisor


@pytest.fixture
def campaign(tmp_path):
    board = tmp_path / supervisor.BOARD
    goals = tmp_path / supervisor.OBJECTIVES
    board.parent.mkdir(parents=True)
    goals.write_text("## SVF-G000 Root\n- Status: active\n- Parent:\n\n"
                     "## SVF-G001 Child\n- Status: active\n- Parent: SVF-G000\n")
    task = (
        "## SVF-001 Foundation\n- Status: ready\n- Depends on:\n- Goal id: SVF-G001\n"
        f"- Deterministic command: python3 {supervisor.WORKER} --task-id SVF-001\n"
        f"- Validation: python3 {supervisor.WORKER} --validate --task-id SVF-001\n"
        "- Predicted files: data/agent_supervisor/swissknife_visual_functional/evidence/001.json\n"
        "- Acceptance: Verifies a real artifact and its provenance.\n"
    )
    board.write_text(task)
    return tmp_path, board, task


def test_valid_frontier_and_goal_relationships(campaign):
    root, _board, _task = campaign
    result = supervisor.preflight(root, {}, inspect_git=False)
    assert result["ready_task_ids"] == ["SVF-001"]
    assert result["task_count"] == 1 and result["goal_count"] == 2
    assert result["completion_authority"] is result["work_complete"] is False


@pytest.mark.parametrize(("before", "after", "message"), [
    ("- Depends on:", "- Depends on: SVF-404", "unknown dependency"),
    ("- Depends on:", "- Depends on: SVF-001", "dependency cycle"),
    ("- Goal id: SVF-G001", "- Goal id: SVF-G404", "unknown goal"),
    ("- Status: ready", "- Status: todo", "unsupported execution status"),
    ("- Status: ready", "- Status: blocked", "no selectable"),
    ("--validate --task-id SVF-001", "--task-id SVF-001", "command must be"),
    ("--task-id SVF-001", "--task-id SVF-001 && grok x", "shell syntax"),
    ("- Acceptance: Verifies a real artifact and its provenance.", "- Acceptance:", "semantic acceptance"),
])
def test_preflight_refuses_malformed_or_unselectable_work(campaign, before, after, message):
    root, board, task = campaign
    board.write_text(task.replace(before, after))
    with pytest.raises(supervisor.PreflightError, match=message):
        supervisor.preflight(root, {}, inspect_git=False)


def test_duplicate_tasks_fail_closed(campaign):
    root, board, task = campaign
    board.write_text(task + "\n" + task)
    with pytest.raises(supervisor.PreflightError, match="duplicate identity"):
        supervisor.preflight(root, {}, inspect_git=False)


def test_hold_prevents_start(campaign):
    root, _board, _task = campaign
    (root / "OPERATOR_STOP").touch()
    with pytest.raises(supervisor.PreflightError, match="operator hold"):
        supervisor.preflight(root, {}, inspect_git=False)


def test_dirty_output_overlap_is_not_repaired(campaign, monkeypatch):
    root, board, task = campaign
    board.write_text(task.replace("data/agent_supervisor/swissknife_visual_functional/evidence/001.json", "swissknife/web/js/apps"))
    monkeypatch.setattr(supervisor, "dirty_paths", lambda _root: ["swissknife/web/js/apps/image-viewer.js"])
    monkeypatch.setattr(supervisor, "active_registered_writers", lambda _root: [])
    with pytest.raises(supervisor.PreflightError, match="dirty output overlap"):
        supervisor.preflight(root, {})


@pytest.mark.parametrize("changed", [False, True])
def test_restart_accepts_only_exact_unchanged_campaign_owned_source(campaign, monkeypatch, changed):
    root, board, task = campaign
    name = "swissknife/scripts/owned-stage.mjs"
    source = root / name
    source.parent.mkdir(parents=True)
    source.write_text("// authored stage checkpoint\n")
    board.write_text(task.replace("data/agent_supervisor/swissknife_visual_functional/evidence/001.json", name))
    ledger = root / supervisor.RUNTIME / "owned-source-hashes.json"
    ledger.parent.mkdir(parents=True)
    ledger.write_text(json.dumps({name: hashlib.sha256(source.read_bytes()).hexdigest()}))
    monkeypatch.setattr(supervisor, "dirty_paths", lambda _root: [name])
    monkeypatch.setattr(supervisor, "active_registered_writers", lambda _root: [])
    if changed:
        source.write_text("// concurrent foreign change\n")
        with pytest.raises(supervisor.PreflightError, match="dirty output overlap"):
            supervisor.preflight(root, {})
    else:
        assert supervisor.preflight(root, {})["ready_task_ids"] == ["SVF-001"]


def test_existing_registered_writer_is_reported_without_takeover(campaign, monkeypatch):
    root, _board, _task = campaign
    monkeypatch.setattr(supervisor, "active_registered_writers", lambda _root: [{"pid": 123, "board": "other-board"}])
    with pytest.raises(supervisor.PreflightError, match="another registered.*writer"):
        supervisor.preflight(root, {})


def test_observer_cannot_launch_raw_resume_and_service_contains_descendants():
    manifest = supervisor.observer_manifest({})
    assert manifest["todo_path"] == ""
    assert manifest["allow_bounded_task_implement"] is False
    assert manifest["restart_authority"] == "leased_systemd_service"
    assert not manifest["autonomous_unstall_policy"]["enabled"]
    unit = supervisor.systemd_unit(Path("/tmp/test-checkout"))
    for required in ("KillMode=control-group", "TimeoutStopSec=120", "Restart=always",
                     "IPFS_ACCELERATE_AGENT_MAX_DIRTY_ATTEMPTS=0", "swissknife-checkout-lease.mjs"):
        assert required in unit


def test_service_path_resolves_operator_grok_symlink_and_venv_python(tmp_path, monkeypatch):
    root, operator = tmp_path / "checkout", tmp_path / "operator"
    venv_bin = root / "external/ipfs_datasets/.venv/bin"
    cli_bin = operator / ".local/bin"
    native = operator / ".grok/downloads/grok-qualified"
    for directory in (venv_bin, cli_bin, native.parent):
        directory.mkdir(parents=True)
    (venv_bin / "python3").symlink_to(sys.executable)
    native.write_text("#!/bin/sh\nexit 0\n")
    native.chmod(0o755)
    (cli_bin / "grok").symlink_to(native)
    monkeypatch.setattr(Path, "home", classmethod(lambda _cls: operator))
    unit = supervisor.systemd_unit(root)
    path_line = next(line for line in unit.splitlines() if line.startswith('Environment="PATH='))
    rendered_path = shlex.split(path_line.split("=", 1)[1])[0].split("=", 1)[1]
    assert rendered_path.split(os.pathsep)[0] == str(venv_bin)
    assert rendered_path.split(os.pathsep)[1] == str(cli_bin)
    assert shutil.which("grok", path=rendered_path) == str(cli_bin / "grok")
    route = supervisor.service_route_availability(root)
    assert route["python"] == str(venv_bin / "python3")
    assert route["grok_resolved"] == str(native)


def test_inventory_matches_foreground_command_exactly():
    root = SCRIPTS.parent
    inventory = json.loads((root / "swissknife/docs/supervisor-lane-inventory.json").read_text())
    lane = next(item for item in inventory["lanes"] if item["id"] == supervisor.LANE_ID)
    command = lane["launch"]["command"]
    assert command[command.index("--") + 1:] == supervisor.launch_arguments()
    assert lane["launch"]["commandPolicy"] == "exact"
    assert lane["launch"]["environment"]["IPFS_ACCELERATE_AGENT_MAX_DIRTY_ATTEMPTS"] == "0"


def test_direct_writer_is_refused_before_runtime_write(campaign, monkeypatch):
    root, _board, _task = campaign
    monkeypatch.setattr(supervisor, "__file__", str(root / "scripts/entry.py"))
    monkeypatch.setattr(supervisor, "load_profile", lambda *_args: {})
    monkeypatch.setattr(supervisor, "preflight", lambda *_args: {"ok": True})
    monkeypatch.delenv("SWISSKNIFE_CHECKOUT_LEASE_ID", raising=False)
    monkeypatch.setenv("IPFS_ACCELERATE_AGENT_MAX_DIRTY_ATTEMPTS", "0")
    with pytest.raises(Exception, match="foreground child"):
        supervisor.main(["--implement", "--no-ephemeral-worktree", "--no-worktree-reconciliation"])
    assert not (root / supervisor.RUNTIME).exists()


def _identity(pid):
    return {"method": "linux-procfs-starttime-v1", "startTicks": supervisor._process_stat(pid)[1],
            "bootId": Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
            "pidNamespace": os.readlink(f"/proc/{pid}/ns/pid"), "uid": os.getuid()}


def _lease(tmp_path, child_pid):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "swissknife").mkdir()
    common = tmp_path / ".git"
    lease_dir = common / "swissknife-checkout-lease-v1"
    lease_dir.mkdir()
    owner = {"schemaVersion": 1, "leaseId": "owned-test-lease",
             "namespace": {"name": "swissknife-supervisor-checkout-lease-v1",
                           "commonDirectory": str(common), "checkout": str(tmp_path / "swissknife")},
             "lane": {"id": supervisor.LANE_ID, "board": supervisor.BOARD,
                      "taskPrefix": supervisor.PREFIX, "statePrefix": supervisor.STATE_PREFIX,
                      "stateDirectory": supervisor.STATE},
             "owner": {"pid": os.getpid(), "hostname": socket.gethostname(),
                       "processIdentity": _identity(os.getpid())},
             "command": supervisor.launch_arguments(), "acquiredAt": "fixture",
             "childPid": child_pid, "childProcessIdentity": _identity(child_pid),
             "childProcessGroupId": supervisor._process_stat(child_pid)[2]}
    state = lease_dir / (".owner-state-" + "a" * 64 + ".json")
    state.write_text(json.dumps(owner))
    (lease_dir / "owner.json").write_text(json.dumps(owner))
    env = os.environ.copy()
    env.update({"IPFS_ACCELERATE_AGENT_MAX_DIRTY_ATTEMPTS": "0",
                "SWISSKNIFE_CHECKOUT_LEASE_ID": owner["leaseId"],
                "SWISSKNIFE_CHECKOUT_LEASE_LANE": supervisor.LANE_ID,
                "SWISSKNIFE_CHECKOUT_LEASE_BOARD": supervisor.BOARD,
                "SWISSKNIFE_CHECKOUT_LEASE_OWNER_FILE": str(state)})
    return env, state


def _worker(root, env):
    profile = {"todoPath": supervisor.BOARD, "runtimeRoot": supervisor.RUNTIME}
    code = (
        "import sys\nfrom pathlib import Path\n"
        f"sys.path.insert(0, {str(SCRIPTS)!r})\n"
        "import swissknife_visual_functional_supervisor as s\n"
        "try:\n"
        f"    s.assert_campaign_lease({profile!r}, root=Path({str(root)!r}))\n"
        "except Exception as e:\n    print(type(e).__name__, str(e)); raise SystemExit(2)\n"
    )
    return subprocess.run([sys.executable, "-c", code], env=env, start_new_session=True,
                          capture_output=True, text=True, timeout=15)


def test_real_detached_worker_requires_live_ancestry(tmp_path):
    env, _state = _lease(tmp_path, os.getpid())
    result = _worker(tmp_path, env)
    assert result.returncode == 0, result.stdout + result.stderr


def test_copied_lease_environment_cannot_authorize_sibling(tmp_path):
    sentinel = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"], start_new_session=True)
    try:
        env, _state = _lease(tmp_path, sentinel.pid)
        result = _worker(tmp_path, env)
        assert result.returncode == 2
        assert result.stdout.startswith("PreflightError ")
        assert "not a descendant" in result.stdout or "foreign UID in leased worker ancestry" in result.stdout
    finally:
        sentinel.terminate()
        sentinel.wait(timeout=10)


@pytest.mark.parametrize("tamper", ["birth", "uuid", "dirty-policy"])
def test_worker_refuses_changed_identity_or_policy(tmp_path, tamper):
    env, state = _lease(tmp_path, os.getpid())
    if tamper == "dirty-policy":
        env["IPFS_ACCELERATE_AGENT_MAX_DIRTY_ATTEMPTS"] = "1"
    else:
        owner = json.loads(state.read_text())
        if tamper == "birth":
            owner["childProcessIdentity"]["startTicks"] = "0"
        else:
            owner["leaseId"] = "different"
        state.write_text(json.dumps(owner))
    result = _worker(tmp_path, env)
    assert result.returncode == 2
    expected = {"birth": "identity no longer matches", "uuid": "pointer does not own",
                "dirty-policy": "no matching inherited campaign lease"}
    assert expected[tamper] in result.stdout
