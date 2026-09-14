"""Real private lane trees exercise phase health separately from dispatch readiness."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import importlib.util
import json
import os
from pathlib import Path
import select
import subprocess
import sys
from types import SimpleNamespace

import pytest

from ipfs_accelerate_py.agent_supervisor.merge.worktree_lifecycle import read_process_birth
from ipfs_accelerate_py.agent_supervisor.todo_daemon.supervisor_activity import SupervisorMaintenanceWindow

ROOT = Path(__file__).resolve().parents[2]
NOW = datetime(2026, 9, 14, 6, 0, 0, tzinfo=timezone.utc)
SUPERVISOR = '''import subprocess, sys
child = subprocess.Popen([sys.executable, "-B", "-c", "import sys; sys.stdin.buffer.read()"], stdin=subprocess.PIPE)
print(child.pid, flush=True)
try:
    for line in sys.stdin:
        if line.strip() in {"stop-daemon", "stop"}:
            if child.poll() is None:
                child.stdin.close()
                child.wait(timeout=5)
            print("daemon-closed", flush=True)
        if line.strip() == "stop": break
finally:
    if child.poll() is None:
        child.stdin.close()
        child.wait(timeout=5)
'''


def reply(process):
    assert select.select([process.stdout], [], [], 5)[0], "owned fixture did not reply"
    line = process.stdout.readline().strip()
    assert line
    return line


@pytest.fixture
def lanes(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("doep_lane_activity_test", ROOT / "scripts/ops/agent_supervisor/direct_objective_event_driven_planning_handoff.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "datetime", SimpleNamespace(now=lambda tz: NOW))
    processes, records, states = [], [], []
    paths = {"state": tmp_path}
    try:
        for lane in range(4):
            process = subprocess.Popen([sys.executable, "-B", "-u", "-c", SUPERVISOR],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
            processes.append(process)
            daemon_pid = int(reply(process))
            birth = read_process_birth(daemon_pid).to_dict()
            supervisor_birth = read_process_birth(process.pid).to_dict()
            assert birth["parent_pid"] == process.pid
            assert supervisor_birth["parent_pid"] == os.getpid()
            records.append({"client_id": f"database-implementation-daemon:{module.OWNER_SESSION}:shard:{lane}-of-4",
                "process_birth": birth, "parent_pid": process.pid})
            states.append({"status": "running", "updated_at": NOW.isoformat(),
                "supervisor_pid": process.pid, "supervisor_pid_alive": True,
                "supervisor_process_birth": supervisor_birth,
                "daemon_pid": daemon_pid, "daemon_pid_alive": True, "daemon_process_birth": dict(birth)})
        def observe(operator_pid=None):
            for lane, state in enumerate(states):
                path = tmp_path / f"lane-{lane}/doep_lane_{lane}_supervisor_status.json"
                path.parent.mkdir(exist_ok=True)
                path.write_text(json.dumps(state))
            return module._lane_observations(paths, {"current": records},
                operator_pid=operator_pid if operator_pid is not None else os.getpid())
        yield SimpleNamespace(module=module, processes=processes, records=records,
                              states=states, observe=observe)
    finally:
        for process in processes:
            if process.poll() is None:
                process.stdin.close()
            process.wait(timeout=5)
            process.stdout.close()


def maintenance(state, *, phase="running", start=None):
    start = start or NOW - timedelta(seconds=20)
    window = SupervisorMaintenanceWindow.begin(started_at=start.isoformat(), timeout_seconds=300)
    state.update(status="agentic_maintenance_started" if phase == "running" else "agentic_maintenance_" + phase,
        supervisor_maintenance=window.event(phase=phase, observed_at=NOW.isoformat()),
        active_agentic_maintenance_has_daemon=True, last_agentic_maintenance_status=phase,
        active_agentic_maintenance_timeout_seconds=300,
        active_agentic_maintenance_started_at=start.isoformat() if phase == "running" else "")


def test_four_real_running_lanes_remain_live_and_dispatchable(lanes):
    result = lanes.observe()
    assert len(result) == 4
    assert all(row["live"] and row["dispatch_ready"] for row in result)
    assert all(row["daemon_birth_alive"] and row["supervisor_birth_alive"] for row in result)


@pytest.mark.parametrize("phase", ["running", "completed"])
def test_current_real_lane_can_maintain_health_without_dispatch_readiness(lanes, phase):
    maintenance(lanes.states[2], phase=phase)
    result = lanes.observe()
    assert all(row["live"] for row in result)
    assert [row["dispatch_ready"] for row in result] == [True, True, False, True]
    assert result[2]["maintenance_processes_current"]
    assert result[2]["activity"]["reason"] == "bounded_maintenance_" + phase
    lanes.states[2]["status"] = "running"
    assert all(row["dispatch_ready"] for row in lanes.observe())


@pytest.mark.parametrize("change", [
    "expired", "nonfinite", "future-start", "stale-heartbeat", "stale-daemon-birth",
    "stale-supervisor-birth", "missing-supervisor-birth", "missing-typed-window",
    "wrong-record-parent", "wrong-daemon-parent", "wrong-operator", "dead-parent", "dead-daemon",
])
def test_maintenance_never_hides_unknown_or_changed_process_scope(lanes, change):
    state = lanes.states[2]
    maintenance(state)
    if change == "expired": maintenance(state, start=NOW - timedelta(seconds=301))
    elif change == "nonfinite": state["supervisor_maintenance"]["timeout_seconds"] = float("inf")
    elif change == "future-start": maintenance(state, start=NOW + timedelta(seconds=1))
    elif change == "stale-heartbeat": state["updated_at"] = (NOW - timedelta(seconds=61)).isoformat()
    elif change == "stale-daemon-birth":
        lanes.records[2]["process_birth"]["start_time_ticks"] += 1
        state["daemon_process_birth"] = deepcopy(lanes.records[2]["process_birth"])
    elif change == "stale-supervisor-birth": state["supervisor_process_birth"]["start_time_ticks"] += 1
    elif change == "missing-supervisor-birth": state.pop("supervisor_process_birth")
    elif change == "missing-typed-window": state.pop("supervisor_maintenance")
    elif change == "wrong-record-parent": lanes.records[2]["parent_pid"] = os.getpid()
    elif change == "wrong-daemon-parent":
        lanes.records[2]["process_birth"]["parent_pid"] = os.getpid()
        state["daemon_process_birth"] = deepcopy(lanes.records[2]["process_birth"])
    elif change in {"dead-parent", "dead-daemon"}:
        process = lanes.processes[2]
        process.stdin.write("stop\n" if change == "dead-parent" else "stop-daemon\n")
        process.stdin.flush()
        assert reply(process) == "daemon-closed"
        if change == "dead-parent": process.wait(timeout=5)
    result = lanes.observe(operator_pid=os.getpid() + 1 if change == "wrong-operator" else None)
    assert not result[2]["live"] and not result[2]["dispatch_ready"], result[2]
    if change != "wrong-operator":
        assert all(result[i]["live"] for i in (0, 1, 3))
    if change == "stale-daemon-birth": assert not result[2]["daemon_birth_alive"]
    if change == "dead-parent": assert not result[2]["supervisor_birth_alive"]
    if change == "dead-daemon": assert result[2]["supervisor_birth_alive"] and not result[2]["daemon_birth_alive"]


def test_each_observation_clock_is_taken_after_its_status_read(lanes, monkeypatch):
    module = lanes.module
    original = module._json_object
    clock = {"now": NOW}
    events = []
    def status_read(path):
        result = original(path)
        clock["now"] += timedelta(milliseconds=1)
        result["updated_at"] = clock["now"].isoformat()
        events.append("read")
        return result
    def observation_clock(tz):
        events.append("clock")
        return clock["now"]
    monkeypatch.setattr(module, "_json_object", status_read)
    monkeypatch.setattr(module, "datetime", SimpleNamespace(now=observation_clock))
    result = lanes.observe()
    assert events == ["read", "clock"] * 4
    assert all(row["live"] and row["dispatch_ready"] for row in result)
    assert all(row["heartbeat_age_seconds"] == 0 for row in result)
