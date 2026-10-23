"""Fenced R20 admission; default is read-only and no capture is launched here."""
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
REPAIR = "VDG-013-R20"
DEPENDENCIES = ["VDG-013-R19"]
BATCH_COMMAND = "node swissknife/scripts/run-vdg-all-families.mjs --timeout-seconds 22200"
VALIDATION = "python3 data/agent_supervisor/virtual_desktop_gui_mcp/watchdog/verify-neural-history-repair.py"
COMMAND = VALIDATION
OWN_SOURCES = [
    "swissknife/web/js/apps/neural-photoshop.js",
    "swissknife/test/scripts/vdg-neural-photoshop-history-state.test.mjs",
    "swissknife/test/e2e/smoke/vdg-neural-photoshop-history-smoke.mjs",
    "data/agent_supervisor/virtual_desktop_gui_mcp/watchdog/verify-neural-history-repair.py",
    "data/agent_supervisor/virtual_desktop_gui_mcp/watchdog/admit-neural-history-repair.py",
]
ACCEPTANCE = (
    "Repair the actual HTTP and libp2p Neural Photoshop history-toggle selector failure with one stable real control identity "
    "and truthful initial accessibility state. Preserve the actual collapsed default and functional expand/collapse behavior. "
    "Require fresh27 behavioral tests, pinned original failures, actual canonical registered-factory browser proof for both "
    "profiles with all five history states, real confirmed native calls and independently verified receipt/event CIDs, exact "
    "PNG bytes and owned cleanup. Require source-current actual inventory, unchanged fingerprints for all eight unaffected "
    "Storage, Dataset, Network and Control transport cells and exact preservation of their eight completed captures. "
    "The separately observed Strudel AI DAW failure requires its own focused repair and new Local captures; no old "
    "Local checkpoint or failing capture gains acceptance. Preserve every original status, task history, "
    "refusal/attempt budget and workload/lifecycle bound. This focused repair grants no acquisition or GUI acceptance; the "
    "existing original batch must still acquire all twelve current captures, including both new Accelerate and both new Local captures, followed "
    "by the existing six strict family GO gates, aggregate GO and closeout."
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def build_admission(original, *, root=ROOT):
    before = dict(parse_todo_task_fields(original, task_header_prefix="## VDG-"))
    require(TARGET in before and before[TARGET].get("status") == "pending",
            "The original batch must remain pending; no completed task may be reclassified")
    require(all(before.get(task, {}).get("status") == "completed" for task in DEPENDENCIES),
            "R19 must naturally complete before R20 admission")
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
    require(after[REPAIR]["status"] in {"pending", "completed"}, "Invalid R20 lifecycle status")
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
    temporary = path.with_name(f".{path.name}.r20-{os.getpid()}.tmp")
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
    parser.add_argument("--apply", action="store_true", help="Commit only the reviewed additive R20 task/dependency under the owned stop fence")
    args = parser.parse_args(argv)
    with lifecycle_fence() as identity:
        original = BOARD.read_text()
        result, before, after = build_admission(original)
        spec = importlib.util.spec_from_file_location("r20_neural_history_verifier", WATCHDOG / "verify-neural-history-repair.py")
        verifier = importlib.util.module_from_spec(spec); spec.loader.exec_module(verifier)
        # Admission and R20 prove the focused canonical product repair. The
        # original still-pending batch remains the only acquisition producer.
        proof = verifier.verify_ready_proof()
        require(BOARD.read_text() == original, "Taskboard changed during admission preflight")
        recheck_fence(identity)
        amended = result.pop("todo_text")
        if args.apply and amended != original:
            capacity = check_storage_capacity([BOARD, WATCHDOG])
            require(capacity["ok"], "Durable storage admission failed")
            snapshot = WATCHDOG / "completion-board-before-neural-history.todo.snapshot"
            if snapshot.exists():
                require(snapshot.read_text() == original, "Existing immutable pre-R20 snapshot differs")
            else:
                atomic_write(snapshot, original)
            atomic_write(BOARD, amended)
        receipt = {"observed_at": time.time(), "apply_requested": args.apply, "tasks_before": len(before), "tasks_after": len(after),
                   "board_before_sha256": hashlib.sha256(original.encode()).hexdigest(),
                   "board_after_sha256": hashlib.sha256(amended.encode()).hexdigest(), "statuses_and_existing_contracts_preserved": True,
                   "identity": identity, "admission": result, "canonical_product_preflight": proof,
                   "gui_acceptance": False, "work_complete": False, "completion_authority": False}
        if args.apply:
            atomic_write(WATCHDOG / "neural-history-admission.json", json.dumps(receipt, indent=2) + "\n")
        print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
