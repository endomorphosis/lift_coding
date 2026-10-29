#!/usr/bin/env python3
"""Run the visual/functional repair lane in the foreground of its checkout lease.

The systemd service owns restart and process containment. The rescue lane owns
bounded task retries and evidence. No detached replacement writer is started.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from swissknife_checkout_lease_guard import SwissKnifeLeaseGuardError, require_swissknife_checkout_lease

LANE_ID = "swissknife-visual-functional"
BOARD = "implementation_plan/docs/53-swissknife-visual-functional-mcplusplus.todo.md"
OBJECTIVES = "implementation_plan/docs/53-swissknife-visual-functional-mcplusplus.objectives.md"
PROFILE = "config/swissknife_visual_functional_supervisor.json"
RUNTIME = "data/agent_supervisor/swissknife_visual_functional"
STATE = RUNTIME + "/state"
WORKER = "scripts/swissknife_visual_functional_worker.py"
PREFIX = "## SVF-"
STATE_PREFIX = "svf"
TERMINAL = frozenset({"completed", "complete", "done"})
SELECTABLE = frozenset({"pending", "ready", "in_progress"})
GOAL_STATES = frozenset({"active", "provisionally_complete", "verified_complete",
                         "analysis_inconclusive", "blocked", "reopened"})


class PreflightError(ValueError):
    """The lane cannot execute safely from these inputs."""


def _relative_path(root: Path, raw: str, *, must_exist: bool = False) -> Path:
    if not isinstance(raw, str):
        raise PreflightError("repository path must be a string")
    value = Path(raw)
    if not raw or value.is_absolute() or ".." in value.parts:
        raise PreflightError(f"unsafe repository-relative path: {raw!r}")
    path = root / value
    try:
        path.resolve(strict=must_exist).relative_to(root.resolve())
    except (OSError, ValueError) as exc:
        raise PreflightError(f"path is absent or escapes repository: {raw}") from exc
    return path


def _records(text: str, prefix: str) -> dict[str, dict[str, str]]:
    records: dict[str, dict[str, str]] = {}
    current: dict[str, str] | None = None
    for line in text.splitlines():
        if line.startswith("## "):
            current = None
            if not line.startswith(prefix):
                continue
            identity = line[3:].split(None, 1)[0]
            if identity in records:
                raise PreflightError(f"duplicate identity: {identity}")
            current = {}
            records[identity] = current
        elif current is not None and line.startswith("- ") and ":" in line:
            key, value = line[2:].split(":", 1)
            key = re.sub(r"[^a-z0-9]+", "_", key.lower()).strip("_")
            current[key] = value.strip()
    return records


def _dependencies(raw: str) -> list[str]:
    return [item for item in re.split(r"[,\s]+", raw.strip()) if item and item.lower() not in {"none", "n/a", "-"}]


def _acyclic(records: dict[str, dict[str, str]], *, field: str) -> None:
    visiting: set[str] = set()
    complete: set[str] = set()

    def visit(identity: str) -> None:
        if identity in visiting:
            raise PreflightError(f"dependency cycle at {identity}")
        if identity in complete:
            return
        visiting.add(identity)
        for dependency in _dependencies(records[identity].get(field, "")):
            if dependency not in records:
                raise PreflightError(f"{identity}: unknown dependency {dependency}")
            visit(dependency)
        visiting.remove(identity)
        complete.add(identity)

    for identity in records:
        visit(identity)


def _worker_command(raw: str, task_id: str, *, validation: bool, recovery: bool = False) -> None:
    if any(char in raw for char in ";|&$`<>\n"):
        raise PreflightError(f"{task_id}: shell syntax refused")
    try:
        argv = shlex.split(raw)
    except ValueError as exc:
        raise PreflightError(f"{task_id}: malformed worker command") from exc
    expected = ["python3", WORKER, "--task-id", task_id]
    if validation or recovery:
        expected.insert(2, "--recover" if recovery else "--validate")
    if argv != expected:
        raise PreflightError(f"{task_id}: command must be {shlex.join(expected)}")


def load_profile(root: Path, profile_path: str = PROFILE) -> dict[str, Any]:
    try:
        profile = json.loads(_relative_path(root, profile_path, must_exist=True).read_text())
    except (OSError, ValueError) as exc:
        raise PreflightError(f"profile is unreadable: {exc}") from exc
    expected = {"todoPath": BOARD, "objectivePath": OBJECTIVES, "taskPrefix": PREFIX,
                "goalPrefix": "SVF-G", "rootGoalId": "SVF-G000", "runtimeRoot": RUNTIME,
                "statePrefix": STATE_PREFIX}
    if not isinstance(profile, dict) or any(profile.get(key) != value for key, value in expected.items()):
        raise PreflightError("profile does not match the registered lane identity")
    router = profile.get("router") or {}
    if not isinstance(router, dict) or router.get("provider") != "grok_cli" or router.get("model") != "grok-4.7":
        raise PreflightError("profile requires llm_router grok_cli / grok-4.7")
    duration = (profile.get("bounds") or {}).get("masterDurationSeconds", 28800)
    if type(duration) is not int or not 60 <= duration <= 86400:
        raise PreflightError("masterDurationSeconds must be an integer between 60 and 86400")
    for key in ("taskSpecPath", "appContractPath"):
        path = _relative_path(root, profile.get(key, ""), must_exist=True)
        try:
            json.loads(path.read_text())
        except (OSError, ValueError) as exc:
            raise PreflightError(f"{key} is not valid JSON") from exc
    return profile


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(root), *args], capture_output=True,
                            text=True, timeout=30, check=False)
    if result.returncode:
        raise PreflightError(f"Git inspection failed in {root.name}: {' '.join(args[:2])}")
    return result.stdout


def dirty_paths(root: Path) -> list[str]:
    """Expand only registered nested checkouts; preserve revision/index drift."""
    paths: set[str] = set()
    nested = ("swissknife", "external/ipfs_kit")
    repositories = ((root, ""), *((root / name, name + "/") for name in nested))
    for repository, prefix in repositories:
        if prefix and Path(_git(repository, "rev-parse", "--show-toplevel").strip()).resolve() != repository.resolve():
            raise PreflightError(f"registered nested checkout is unavailable: {prefix.rstrip('/')}")
        for marker in ("MERGE_HEAD", "CHERRY_PICK_HEAD", "REVERT_HEAD", "BISECT_LOG", "rebase-merge", "rebase-apply"):
            raw = _git(repository, "rev-parse", "--git-path", marker).strip()
            path = Path(raw)
            if (path if path.is_absolute() else repository / path).exists():
                raise PreflightError(f"interrupted Git operation in {repository.name}: {marker}")
        if _git(repository, "ls-files", "--unmerged", "-z").strip():
            raise PreflightError(f"unresolved index in {repository.name}")
        names = set(_git(repository, "diff", "--no-renames", "--name-only", "HEAD", "-z").split("\0"))
        names.update(_git(repository, "diff", "--cached", "--no-renames", "--name-only", "-z").split("\0"))
        names.update(_git(repository, "diff", "--no-renames", "--name-only", "-z").split("\0"))
        names.update(_git(repository, "ls-files", "--others", "--exclude-standard", "-z").split("\0"))
        paths.update(prefix + name for name in names if name)
    for name in nested:
        pinned = _git(root, "ls-tree", "HEAD", "--", name).split()
        if len(pinned) < 3 or pinned[0] != "160000":
            raise PreflightError(f"registered nested checkout has no pinned gitlink: {name}")
        indexed = _git(root, "ls-files", "--stage", "--", name).split()
        current = _git(root / name, "rev-parse", "HEAD").strip()
        # Summary dirt is redundant only after independent concrete inspection
        # AND unchanged worktree/index revisions. A parent revision change
        # cannot be blessed by a ledger entry for one descendant source file.
        if len(indexed) >= 3 and indexed[:3] == ["160000", pinned[2], "0"] and current == pinned[2]:
            paths.discard(name)
            paths.discard(name + "/")
        else:
            paths.add(name)
    return sorted(paths)


def active_registered_writers(root: Path) -> list[dict[str, Any]]:
    """Observe explicit registered writer launches without signaling owners."""
    inventory = json.loads((root / "swissknife/docs/supervisor-lane-inventory.json").read_text())
    boards = {lane["board"] for lane in inventory["lanes"] if lane.get("kind") == "implementation-supervisor"}
    entrypoints = {"ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_supervisor",
                   "ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon"}
    for lane in inventory["lanes"]:
        command = (lane.get("launch") or {}).get("command", [])
        if "--" in command:
            child = command[command.index("--") + 1:]
            if len(child) >= 2:
                entrypoints.add(child[1])
    ancestors: set[int] = set()
    ancestor = os.getpid()
    while ancestor > 0 and ancestor not in ancestors:
        ancestors.add(ancestor)
        try:
            ancestor = _process_stat(ancestor)[0]
        except (OSError, ValueError, IndexError):
            break
    found = []
    for directory in Path("/proc").iterdir():
        if not directory.name.isdigit() or int(directory.name) in ancestors:
            continue
        try:
            if directory.stat().st_uid != os.getuid():
                continue
            argv = [part.decode(errors="replace") for part in (directory / "cmdline").read_bytes().split(b"\0") if part]
            normalized_argv = [part[len(str(root)) + 1:] if part.startswith(str(root) + "/") else part for part in argv]
            if "--implement" not in argv or not any(part in entrypoints for part in normalized_argv):
                continue
            cwd = (directory / "cwd").resolve(strict=True)
            if cwd != root.resolve():
                continue
            board = argv[argv.index("--todo-path") + 1] if "--todo-path" in argv else ""
            if board.startswith(str(root) + "/"):
                board = board[len(str(root)) + 1:]
            if board in boards:
                found.append({"pid": int(directory.name), "board": board})
        except (FileNotFoundError, ProcessLookupError):
            continue
        except PermissionError as exc:
            raise PreflightError("cannot verify an existing process identity") from exc
    return found


def preflight(root: Path, profile: dict[str, Any], *, inspect_git: bool = True) -> dict[str, Any]:
    board = _relative_path(root, BOARD, must_exist=True)
    goals_path = _relative_path(root, OBJECTIVES, must_exist=True)
    tasks = _records(board.read_text(), PREFIX)
    goals = _records(goals_path.read_text(), "## SVF-G")
    if not tasks or "SVF-G000" not in goals:
        raise PreflightError("board has no tasks or root goal is absent")
    _acyclic(tasks, field="depends_on")
    _acyclic(goals, field="parent")
    for goal_id, fields in goals.items():
        if fields.get("status", "active") not in GOAL_STATES:
            raise PreflightError(f"{goal_id}: noncanonical goal status")
    ready: list[str] = []
    for task_id, fields in tasks.items():
        status = fields.get("status", "").lower()
        if status not in SELECTABLE | TERMINAL | {"blocked"}:
            raise PreflightError(f"{task_id}: unsupported execution status {status}")
        if fields.get("goal_id") not in goals:
            raise PreflightError(f"{task_id}: missing or unknown goal id")
        _worker_command(fields.get("deterministic_command", ""), task_id, validation=False)
        _worker_command(fields.get("validation", ""), task_id, validation=True)
        if fields.get("semantic_recovery_command"):
            _worker_command(fields["semantic_recovery_command"], task_id, validation=False, recovery=True)
            try:
                failure_limit = int(fields.get("semantic_failure_limit", "6"))
                recovery_limit = int(fields.get("semantic_recovery_limit", "1"))
                recovery_timeout = int(fields.get("semantic_recovery_timeout_seconds", "900"))
                task_timeout = int(fields.get("implementation_timeout_seconds", "1800"))
            except ValueError as exc:
                raise PreflightError(f"{task_id}: malformed recovery bounds") from exc
            if not 1 <= failure_limit <= 6 or not 1 <= recovery_limit <= 2 or not 1 <= recovery_timeout <= min(1200, task_timeout):
                raise PreflightError(f"{task_id}: recovery bounds exceed registered limits")
        outputs = [part.strip() for part in fields.get("predicted_files", "").split(",") if part.strip()]
        if not outputs or not fields.get("acceptance"):
            raise PreflightError(f"{task_id}: predicted files and semantic acceptance are required")
        for output in outputs:
            _relative_path(root, output)
        if status in SELECTABLE and all(tasks[dep].get("status", "").lower() in TERMINAL
                                        for dep in _dependencies(fields.get("depends_on", ""))):
            ready.append(task_id)
    remaining = [key for key, fields in tasks.items() if fields.get("status", "").lower() not in TERMINAL]
    if remaining and not ready:
        raise PreflightError("nonterminal tasks have no selectable dependency frontier")
    holds = [directory / name for directory in (root, root / RUNTIME, root / STATE, root / RUNTIME / "watchdog")
             for name in ("HOLD", "OPERATOR_STOP", "watchdog.disabled", "hold", "operator.hold")]
    if any(path.exists() for path in holds):
        raise PreflightError("operator hold is active")
    if inspect_git and active_registered_writers(root):
        raise PreflightError("another registered SwissKnife writer is active; wait_for_owner_then_recheck")
    dirt = dirty_paths(root) if inspect_git else []
    ledger_path = root / RUNTIME / "owned-source-hashes.json"
    ledger = json.loads(ledger_path.read_text()) if ledger_path.exists() else {}
    if not isinstance(ledger, dict):
        raise PreflightError("owned source ledger is malformed")
    def owned_exact(path: str, output: str, task_id: str) -> bool:
        source = _relative_path(root, path)
        exact = (path == output and not source.is_symlink() and source.is_file()
                 and ledger.get(path) == hashlib.sha256(source.read_bytes()).hexdigest())
        if exact or path != output or not profile.get("phaseRemediation", {}).get("enabled"):
            return exact
        from swissknife_visual_functional_phase_remediation import recoverable_owned_source
        return recoverable_owned_source(root, profile, task_id, path)
    for task_id in ready:
        for output in (part.strip().rstrip("/") for part in tasks[task_id]["predicted_files"].split(",")):
            overlap = [path for path in dirt if path == output or path.startswith(output + "/") or output.startswith(path + "/")]
            foreign = [path for path in overlap if not owned_exact(path, output, task_id)]
            if foreign:
                raise PreflightError(f"{task_id}: dirty output overlap: {', '.join(foreign[:8])}")
    return {"schema": "swissknife.visual-functional-preflight@1", "ok": True,
            "task_count": len(tasks), "goal_count": len(goals), "ready_task_ids": ready,
            "remaining_task_ids": remaining, "dirty_path_count": len(dirt),
            "board_sha256": hashlib.sha256(board.read_bytes()).hexdigest(),
            "completion_authority": False, "work_complete": False}


def observer_manifest(profile: dict[str, Any]) -> dict[str, Any]:
    return {"schema": "swissknife.visual-functional-observer@1", "observation_only": True,
            "observed_todo_path": BOARD, "todo_path": "", "task_header_prefix": PREFIX,
            "allow_bounded_task_implement": False, "restart_authority": "leased_systemd_service",
            "autonomous_unstall_policy": {"enabled": False, "allow_provider_calls": False},
            "report_path": RUNTIME + "/watchdog/observer-report.json",
            "lanes": [{"bundle_key": LANE_ID, "state_dir": STATE, "state_prefix": STATE_PREFIX,
                       "log_path": RUNTIME + "/logs/supervisor.log"}],
            "completion_authority": False, "work_complete": False}


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix="." + path.name, dir=path.parent)
    try:
        with os.fdopen(fd, "w") as handle:
            json.dump(value, handle, indent=2)
            handle.write("\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def launch_arguments() -> list[str]:
    return ["python3", "scripts/swissknife_visual_functional_supervisor.py", "--profile", PROFILE,
            "--todo-path", BOARD, "--state-dir", STATE, "--task-prefix", PREFIX,
            "--state-prefix", STATE_PREFIX, "--implement", "--no-ephemeral-worktree",
            "--no-worktree-reconciliation"]


def service_path(root: Path) -> str:
    """Use the qualified operator CLI install after the selected Python venv."""
    return os.pathsep.join([str(root / "external/ipfs_datasets/.venv/bin"),
                           str(Path.home() / ".local/bin"), "/usr/local/bin", "/usr/bin", "/bin"])


def service_route_availability(root: Path) -> dict[str, str]:
    """Check exact service PATH resolution without calling either provider."""
    path = service_path(root)
    python = shutil.which("python3", path=path)
    grok = shutil.which("grok", path=path)
    expected_python = root / "external/ipfs_datasets/.venv/bin/python3"
    if not python or Path(python) != expected_python:
        raise PreflightError("service PATH does not select the qualified datasets Python")
    if not grok or not Path(grok).resolve().is_file():
        raise PreflightError("qualified Grok CLI is unavailable on the service PATH")
    return {"python": python, "grok": grok, "grok_resolved": str(Path(grok).resolve())}


def systemd_unit(root: Path) -> str:
    """Render containment for detached command sessions owned by the lane."""
    argv = ["/usr/bin/node", "swissknife/scripts/swissknife-checkout-lease.mjs", "--run",
            "--lane", LANE_ID, "--board", BOARD, "--", *launch_arguments()]
    return "\n".join([
        "[Unit]", "Description=SwissKnife visual and functional repair supervisor",
        "StartLimitIntervalSec=0", "", "[Service]", "Type=simple",
        f"WorkingDirectory={root}",
        "Environment=IPFS_ACCELERATE_AGENT_MAX_DIRTY_ATTEMPTS=0",
        "Environment=PYTHONDONTWRITEBYTECODE=1",
        f'Environment="PATH={service_path(root)}"',
        "ExecStart=" + shlex.join(argv), "Restart=always", "RestartSec=30",
        "KillMode=control-group", "TimeoutStopSec=120", "SendSIGKILL=yes",
        "", "[Install]", "WantedBy=default.target", "",
    ])


def _process_stat(pid: int) -> tuple[int, str, int]:
    raw = Path(f"/proc/{pid}/stat").read_text()
    fields = raw[raw.rfind(") ") + 2:].split()
    if fields[0] in {"Z", "X"}:
        raise PreflightError("lease process is not executing")
    return int(fields[1]), fields[19], int(fields[2])


def _verify_identity(pid: int, identity: dict[str, Any]) -> tuple[int, str, int]:
    if type(pid) is not int or pid <= 0 or not isinstance(identity, dict):
        raise PreflightError("lease process identity is absent")
    current = _process_stat(pid)
    if (identity.get("method") != "linux-procfs-starttime-v1"
            or identity.get("startTicks") != current[1]
            or identity.get("bootId") != Path("/proc/sys/kernel/random/boot_id").read_text().strip()
            or identity.get("pidNamespace") != os.readlink(f"/proc/{pid}/ns/pid")
            or identity.get("uid") != os.getuid()
            or Path(f"/proc/{pid}").stat().st_uid != os.getuid()):
        raise PreflightError("lease process identity no longer matches")
    return current


def _ancestor_chain(child: int, ancestor: int, expected_ticks: str) -> None:
    """Require actual ancestry and stable births, independent of process groups."""
    seen: set[int] = set()
    current = child
    for _ in range(128):
        if current <= 0 or current in seen:
            break
        seen.add(current)
        before = _process_stat(current)
        if Path(f"/proc/{current}").stat().st_uid != os.getuid():
            raise PreflightError("foreign UID in leased worker ancestry")
        if current == ancestor:
            if before[1] != expected_ticks:
                raise PreflightError("leased ancestor process birth changed")
            return
        parent = before[0]
        _process_stat(parent)
        if _process_stat(current) != before:
            raise PreflightError("worker ancestry changed while verifying lease")
        current = parent
    raise PreflightError("worker is not a descendant of the leased foreground supervisor")


def assert_campaign_lease(profile: dict[str, Any], *, root: Path | None = None) -> dict[str, str]:
    """Verify the inherited lease for a deterministic child in its own session.

    Child commands use new process groups for reliable timeout cleanup. Actual
    ancestry, process birth, UID, boot and namespace replace group equality;
    unrelated processes possessing copied environment values remain refused.
    """
    root = (root or Path(__file__).resolve().parents[1]).resolve()
    if profile.get("todoPath") != BOARD or profile.get("runtimeRoot") != RUNTIME:
        raise PreflightError("foreign campaign profile")
    env = os.environ
    lease_id = env.get("SWISSKNIFE_CHECKOUT_LEASE_ID", "")
    if (not lease_id or env.get("IPFS_ACCELERATE_AGENT_MAX_DIRTY_ATTEMPTS") != "0"
            or env.get("SWISSKNIFE_CHECKOUT_LEASE_LANE") != LANE_ID
            or env.get("SWISSKNIFE_CHECKOUT_LEASE_BOARD") != BOARD):
        raise PreflightError("worker has no matching inherited campaign lease")
    common = Path(_git(root, "rev-parse", "--path-format=absolute", "--git-common-dir").strip()).resolve()
    lease_dir = common / "swissknife-checkout-lease-v1"
    state_path = Path(env.get("SWISSKNIFE_CHECKOUT_LEASE_OWNER_FILE", ""))
    if (state_path.parent.resolve() != lease_dir or state_path.is_symlink()
            or not re.fullmatch(r"\.owner-state-[0-9a-f]{64}\.json", state_path.name)):
        raise PreflightError("lease state file is outside the canonical Git namespace")
    owner = json.loads(state_path.read_text())
    pointer_path = lease_dir / "owner.json"
    pointer = json.loads(pointer_path.read_text())
    immutable = ("schemaVersion", "leaseId", "namespace", "owner", "lane", "command", "acquiredAt")
    if any(owner.get(key) != pointer.get(key) for key in immutable):
        raise PreflightError("lease pointer does not own the inherited state")
    namespace, lane, wrapper = (owner.get(key) or {} for key in ("namespace", "lane", "owner"))
    if (owner.get("schemaVersion") != 1 or owner.get("leaseId") != lease_id
            or namespace.get("name") != "swissknife-supervisor-checkout-lease-v1"
            or Path(namespace.get("commonDirectory", "")).resolve() != common
            or Path(namespace.get("checkout", "")).resolve() != root / "swissknife"
            or wrapper.get("hostname") != socket.gethostname()
            or lane.get("id") != LANE_ID or lane.get("board") != BOARD
            or lane.get("taskPrefix") != PREFIX or lane.get("statePrefix") != STATE_PREFIX
            or lane.get("stateDirectory") != STATE):
        raise PreflightError("lease metadata does not match the campaign")
    wrapper_stat = _verify_identity(wrapper.get("pid"), wrapper.get("processIdentity"))
    child_pid = owner.get("childPid")
    child_stat = _verify_identity(child_pid, owner.get("childProcessIdentity"))
    if owner.get("childProcessGroupId") != child_stat[2]:
        raise PreflightError("foreground supervisor group identity changed")
    _ancestor_chain(os.getpid(), child_pid, child_stat[1])
    _ancestor_chain(child_pid, wrapper["pid"], wrapper_stat[1])
    if json.loads(pointer_path.read_text()).get("leaseId") != lease_id:
        raise PreflightError("lease changed during worker admission")
    return {"lease_id": lease_id, "lane_id": LANE_ID}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", default=PROFILE)
    parser.add_argument("--todo-path", default=BOARD)
    parser.add_argument("--state-dir", default=STATE)
    parser.add_argument("--task-prefix", default=PREFIX)
    parser.add_argument("--state-prefix", default=STATE_PREFIX)
    parser.add_argument("--implement", action="store_true")
    parser.add_argument("--no-ephemeral-worktree", action="store_true")
    parser.add_argument("--no-worktree-reconciliation", action="store_true")
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--print-systemd-unit", action="store_true")
    raw = list(sys.argv[1:] if argv is None else argv)
    args = parser.parse_args(raw)
    root = Path(__file__).resolve().parents[1]
    if args.print_systemd_unit:
        print(systemd_unit(root), end="")
        return 0
    if (args.profile, args.todo_path, args.state_dir, args.task_prefix, args.state_prefix) != (
            PROFILE, BOARD, STATE, PREFIX, STATE_PREFIX):
        raise PreflightError("arguments differ from registered lane identity")
    profile = load_profile(root)
    # This branch is strictly read-only, including under an operator HOLD.  It
    # may diagnose an existing intent but never initializes or recovers one.
    from swissknife_visual_functional_phase_remediation import (
        between_cycles, pending_publications, policy_enabled, recover_pending, assert_controller_pins)
    enabled = policy_enabled(profile)
    if args.preflight_only or not args.implement:
        if pending_publications(root, profile):
            raise PreflightError("pending authenticated phase publication requires leased normal startup recovery")
        result = preflight(root, profile)
        result["service_route"] = service_route_availability(root)
        print(json.dumps(result, indent=2))
        return 0
    if not args.no_ephemeral_worktree or not args.no_worktree_reconciliation:
        raise PreflightError("both shared-checkout safety flags are required")
    require_swissknife_checkout_lease(raw, allowed_lanes={LANE_ID: BOARD})
    from lift_ipfs_accelerate_bootstrap import bootstrap_ipfs_accelerate
    bootstrap_ipfs_accelerate(__file__)
    from ipfs_accelerate_py.agent_supervisor.rescue.lane_resume import serve
    authority = lambda: assert_campaign_lease(profile, root=root)
    pending = pending_publications(root, profile)
    if enabled or pending: assert_controller_pins(root, profile)
    startup_ready = False
    def checked_startup():
        nonlocal startup_ready
        # Recover only a pre-existing immutable intent before normal metadata
        # consistency checks; no new task admission occurs here.
        if pending_publications(root, profile):
            recover_pending(root, profile, ensure_authority=authority)
        result = preflight(root, profile)
        result["service_route"] = service_route_availability(root)
        startup_ready = True
        return result
    try:
        result = checked_startup()
    except (ValueError, OSError) as error:
        if not pending: raise
        # Native serve keeps the refusal bounded/backed off.  No run cycle is
        # allowed until authenticated publication and full preflight converge.
        result = {"ok":False,"phase":"pending_publication_refused",
                  "reason":" ".join(str(error).split())[:240],"completion_authority":False}
    deadline = int(time.time()*1000) + profile.get("bounds", {}).get("masterDurationSeconds",28800)*1000
    prior_deadline = os.environ.get("SVF_CAMPAIGN_DEADLINE_AT_MS")
    if prior_deadline:
        if not prior_deadline.isdecimal(): raise PreflightError("invalid inherited campaign absolute deadline")
        deadline = min(deadline,int(prior_deadline))
    os.environ["SVF_CAMPAIGN_DEADLINE_AT_MS"] = str(deadline)

    def admit_phase_gap():
        if not startup_ready: checked_startup()
        return between_cycles(root, profile, ensure_authority=authority)

    _atomic_json(root / RUNTIME / "startup-preflight.json", result)
    _atomic_json(root / RUNTIME / "watchdog/bundle_lanes.json", observer_manifest(profile))
    state = root / STATE
    logs = root / RUNTIME / "logs/supervisor.log"
    logs.parent.mkdir(parents=True, exist_ok=True)
    return serve(["--repo-root", str(root), "--todo-path", BOARD, "--task-header-prefix", PREFIX,
                  "--status-path", str(state / "svf_status.json"),
                  "--pid-path", str(state / "svf_bundle_supervisor.pid"), "--log-path", str(logs),
                  "--bundle-key", LANE_ID, "--max-seconds",
                  str(profile.get("bounds", {}).get("masterDurationSeconds", 28800))],
                 between_cycles=admit_phase_gap if enabled or pending else None)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (PreflightError, SwissKnifeLeaseGuardError, ValueError, OSError) as exc:
        print(json.dumps({"ok": False, "reason": str(exc), "recovery": "wait_for_owner_then_recheck",
                          "completion_authority": False, "work_complete": False}), file=sys.stderr)
        raise SystemExit(78) from None
