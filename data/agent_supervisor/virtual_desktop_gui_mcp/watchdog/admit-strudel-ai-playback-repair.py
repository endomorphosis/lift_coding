"""Fenced R21 admission; default is read-only and no capture is launched here."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import time

from ipfs_accelerate_py.agent_supervisor.rescue.gate_recovery import admit_gate_repair_task
from ipfs_accelerate_py.agent_supervisor.rescue.storage_pressure import check_storage_capacity
from ipfs_accelerate_py.agent_supervisor.rescue.supervisor_watchdog import parse_todo_task_fields

ROOT = Path(__file__).resolve().parents[4]
WATCHDOG = Path(__file__).resolve().parent
BOARD = ROOT / "implementation_plan/docs/50-virtual-desktop-gui-mcp.todo.md"
TARGET = "VDG-039-R01"
REPAIR = "VDG-013-R21"
DEPENDENCIES = ["VDG-013-R20"]
BATCH_COMMAND = "node swissknife/scripts/run-vdg-all-families.mjs --timeout-seconds 22200"
VALIDATION = "python3 data/agent_supervisor/virtual_desktop_gui_mcp/watchdog/verify-strudel-ai-playback-repair.py"
COMMAND = VALIDATION
OWN_SOURCES = [
    "swissknife/web/js/apps/strudel-ai-daw.js",
    "swissknife/web/js/audio/strudel-processor.js",
    "swissknife/test/scripts/vdg-strudel-ai-playback.test.mjs",
    "swissknife/test/e2e/smoke/vdg-strudel-ai-playback-smoke.mjs",
    "data/agent_supervisor/virtual_desktop_gui_mcp/watchdog/verify-strudel-ai-playback-repair.py",
    "data/agent_supervisor/virtual_desktop_gui_mcp/watchdog/admit-strudel-ai-playback-repair.py",
    "data/agent_supervisor/virtual_desktop_gui_mcp/watchdog/test-strudel-ai-playback-ops.py",
]
ACCEPTANCE = (
    "Repair the actual Strudel AI DAW Play failure without hiding its captured page error. Preserve a complete real SDK "
    "transport when available; otherwise label real bounded WebAudio playback as a local metronome/reference-tone preview "
    "with Strudel compilation unavailable. Preserve both complete existing SDK globals and bound import/resume/suspend/close waits. "
    "Require fresh38 meaningful app tests and reviewed canonical registered-factory "
    "Chrome proof in both declared profiles: actual signal and silence, trusted Play/Pause/Resume/Stop, tempo/gain/tap/editor "
    "controls, playing-window close/reopen, zero POSTs/pageerrors, exact PNG bytes and closed owned resources. Reject "
    "candidate module overrides and intercepted browser evidence. Archive the immutable original 2178-row failed Local "
    "HTTP capture and row2092 before/after PNGs. Require fresh actual inventory and unchanged eight completed unaffected "
    "Storage/Dataset/Network/Control source fingerprints, report hashes and acquisition identities against the authoritative "
    "pre-repair baseline. Preserve every existing task status, history, contract, attempt/refusal budget and lifecycle bound. "
    "This focused repair grants no Local or Accelerate capture acceptance: the existing pending original039 batch remains "
    "the only acquisition producer and must acquire all twelve current cells, including both new Accelerate and both new "
    "Local captures, followed by six strict family GO gates, aggregate GO and060 closeout."
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def build_admission(original, *, root=ROOT):
    before = dict(parse_todo_task_fields(original, task_header_prefix="## VDG-"))
    require(TARGET in before and before[TARGET].get("status") == "pending",
            "The original batch must remain pending; no completed task may be reclassified")
    require(all(before.get(task, {}).get("status") in {"pending", "completed"} for task in DEPENDENCIES),
            "The sole R20 prerequisite must exist with pending or completed status")
    require(before["VDG-039-R01"].get("deterministic_command") == BATCH_COMMAND, "Original bounded acquisition contract changed")
    predicted = [item.strip() for item in before["VDG-039-R01"].get("predicted_files", "").split(",") if item.strip()]
    predicted = list(dict.fromkeys([*predicted, *OWN_SOURCES]))
    result = admit_gate_repair_task(original, repo_root=root, task_id=TARGET, repair_task_id=REPAIR,
        command=COMMAND, validation=VALIDATION, predicted_files=predicted, acceptance=ACCEPTANCE,
        depends_on=DEPENDENCIES, resource_class="cpu-small", implementation_timeout_seconds=1800)
    amended = result["todo_text"]
    after = dict(parse_todo_task_fields(amended, task_header_prefix="## VDG-"))
    require(set(after) == set(before) | {REPAIR}, "Unexpected task creation or removal")
    for task, fields in before.items():
        if task == TARGET:
            expected = dict(fields)
            expected["depends_on"] = ", ".join(dict.fromkeys([*(value.strip() for value in fields.get("depends_on", "").split(",") if value.strip()), REPAIR]))
            require(after[task] == expected, "Only the original batch's additive dependency may change")
        else:
            require(after[task] == fields, f"Existing task/history contract changed: {task}")
    require(after[REPAIR]["status"] in {"pending", "completed"}, "Invalid R21 lifecycle status")
    active, seen = set(), set()
    def visit(task):
        require(task in after and task not in active, f"Missing dependency or cycle: {task}")
        if task in seen:
            return
        active.add(task)
        for value in after[task].get("depends_on", "").split(","):
            if value.strip():
                visit(value.strip())
        active.remove(task); seen.add(task)
    for task in after:
        visit(task)
    return result, before, after


def node_script(argv):
    if not argv or Path(argv[0]).name not in {"node", "nodejs"}:
        return None
    index = 1
    while index < len(argv):
        value = argv[index]
        if value == "--":
            return argv[index + 1] if index + 1 < len(argv) else None
        if value in {"-e", "--eval", "-p", "--print"} or value.startswith(("--eval=", "--print=")):
            return None
        if value in {"--import", "--require", "-r", "--loader", "--experimental-loader", "--conditions", "-C"}:
            index += 2
            continue
        if value.startswith("-"):
            index += 1
            continue
        return value
    return None


def active_captures(root=ROOT, proc_root=Path("/proc")):
    """Inspect actual Node script operands, never arbitrary argument data."""
    paths = {root / "swissknife/scripts" / name for name in
             ("run-vdg-family.mjs", "run-vdg-all-families.mjs", "verify-vdg-family.mjs")}
    found = []
    for directory in proc_root.iterdir():
        if not directory.name.isdecimal():
            continue
        try:
            if directory.stat().st_uid != os.getuid():
                continue
            argv = (directory / "cmdline").read_bytes().decode().rstrip("\0").split("\0")
            script = node_script(argv)
            if not script:
                continue
            candidate = Path(script)
            if not candidate.is_absolute():
                candidate = (directory / "cwd").resolve(strict=True) / candidate
            if candidate.resolve() in paths:
                if (directory / "exe").resolve(strict=True).name not in {"node", "nodejs"}:
                    continue
                found.append(int(directory.name))
        except (OSError, UnicodeError):
            # A disappearing process cannot own a surviving lifecycle lock.
            if directory.exists():
                raise
    return found


@contextmanager
def lifecycle_fence(watchdog=WATCHDOG, root=ROOT):
    lane = watchdog / "lanes/vdg-planning"
    descriptor = os.open(lane / "vdg-planning.resume.lock", os.O_RDONLY | os.O_NOFOLLOW)
    try:
        info = os.fstat(descriptor)
        require(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid(), "Unsafe lifecycle lock ownership")
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        status = json.loads((lane / "vdg_planning_status.json").read_text())
        pid = status.get("pid")
        require(type(pid) is int and pid > 0 and not Path(f"/proc/{pid}").exists(), "Exact prior lane must be absent")
        require(int((lane / "vdg_planning_bundle_supervisor.pid").read_text().strip()) == pid,
                "Canonical stopped status and independent owner PID file disagree")
        require(status.get("state") == "stopped" and status.get("terminal_reason") == "resume_stopped", "Canonical owned stop is required")
        hold = json.loads((watchdog / "repair-dispatcher.hold").read_text())
        require(hold.get("reason") == "controlled VDG completion repairs" and hold.get("lane_pid") == pid,
                "An explicit controlled repair hold must bind the stopped owner")
        require(not active_captures(root), "An actual owned capture entrypoint remains active")
        yield {"lane_pid": pid, "lock_inode": info.st_ino, "lock_device": info.st_dev,
               "hold_sha256": hashlib.sha256((watchdog / "repair-dispatcher.hold").read_bytes()).hexdigest()}
    finally:
        os.close(descriptor)


def recheck_fence(identity, watchdog=WATCHDOG, root=ROOT):
    lane = watchdog / "lanes/vdg-planning"
    lock = (lane / "vdg-planning.resume.lock").lstat()
    require(stat.S_ISREG(lock.st_mode) and lock.st_uid == os.getuid()
            and lock.st_ino == identity["lock_inode"] and lock.st_dev == identity["lock_device"], "Lifecycle fence path changed")
    status = json.loads((lane / "vdg_planning_status.json").read_text())
    require(status.get("pid") == identity["lane_pid"] and status.get("state") == "stopped"
            and status.get("terminal_reason") == "resume_stopped"
            and not Path(f"/proc/{identity['lane_pid']}").exists(), "Stopped owner changed during preflight")
    require(hashlib.sha256((watchdog / "repair-dispatcher.hold").read_bytes()).hexdigest() == identity["hold_sha256"],
            "Controlled repair hold changed during preflight")
    require(not active_captures(root), "An owned capture started during admission preflight")


def atomic_write(path, text):
    temporary = path.with_name(f".{path.name}.r21-{os.getpid()}.tmp")
    try:
        with temporary.open("x") as handle:
            handle.write(text); handle.flush(); os.fsync(handle.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        temporary.unlink(missing_ok=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Commit only the reviewed additive R21 task/dependency under the owned stop fence")
    args = parser.parse_args(argv)
    with lifecycle_fence() as identity:
        original = BOARD.read_text()
        result, before, after = build_admission(original)
        spec = importlib.util.spec_from_file_location("r21_strudel_ai_playback_verifier", WATCHDOG / "verify-strudel-ai-playback-repair.py")
        verifier = importlib.util.module_from_spec(spec); spec.loader.exec_module(verifier)
        # Admission and R21 prove the focused canonical product repair. The
        # original still-pending batch remains the only acquisition producer.
        proof = verifier.verify_ready_proof()
        require(BOARD.read_text() == original, "Taskboard changed during admission preflight")
        recheck_fence(identity)
        amended = result.pop("todo_text")
        if args.apply and amended != original:
            capacity = check_storage_capacity([BOARD, WATCHDOG])
            require(capacity["ok"], "Durable storage admission failed")
            snapshot = WATCHDOG / "completion-board-before-strudel-ai-playback.todo.snapshot"
            if snapshot.exists():
                require(snapshot.read_text() == original, "Existing immutable pre-R21 snapshot differs")
            else:
                atomic_write(snapshot, original)
            atomic_write(BOARD, amended)
        receipt = {"observed_at": time.time(), "apply_requested": args.apply, "tasks_before": len(before), "tasks_after": len(after),
                   "board_before_sha256": hashlib.sha256(original.encode()).hexdigest(),
                   "board_after_sha256": hashlib.sha256(amended.encode()).hexdigest(), "statuses_and_existing_contracts_preserved": True,
                   "identity": identity, "admission": result, "canonical_product_preflight": proof,
                   "gui_acceptance": False, "work_complete": False, "completion_authority": False}
        if args.apply:
            atomic_write(WATCHDOG / "strudel-ai-playback-admission.json", json.dumps(receipt, indent=2) + "\n")
        print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
