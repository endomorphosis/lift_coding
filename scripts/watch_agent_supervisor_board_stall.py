#!/usr/bin/env python3
"""Watch one agent-supervisor board and spawn a bounded repair subagent.

The subagent records successor subgoals or inserts a missing status line.
It does not mark a task completed, drop a dependency, renew a clock, add a
ready task, or restart the supervisor. A second copy exits while the lock
is held.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "external" / "ipfs_accelerate"))
sys.path.insert(0, str(ROOT / "scripts"))

from ipfs_accelerate_py.agent_supervisor.rescue.board_stall_watchdog import (  # noqa: E402
    BOARD_STALL_PACKET_SCHEMA,
    BOARD_STALL_RECEIPT_SCHEMA,
    RuntimeSnapshot,
    accept_receipt,
    apply_repair_packet,
    classify_board_stall,
    decide_spawn,
    parse_task_board,
    stall_signature,
)


_CHILD_TIMEOUT_S = 180.0


def _atomic_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".", suffix=".tmp")
    try:
        os.write(fd, payload)
        os.fsync(fd)
        os.close(fd)
        fd = -1
        os.chmod(name, 0o644)
        os.replace(name, path)
    finally:
        if fd >= 0:
            os.close(fd)
        if os.path.exists(name):
            try:
                os.unlink(name)
            except OSError:
                pass


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _supervisor_alive(pid: object, mark: str) -> bool:
    if not isinstance(pid, int) or isinstance(pid, bool) or pid <= 0 or not mark:
        return False
    try:
        raw = Path(f"/proc/{pid}/cmdline").read_bytes()
    except OSError:
        return False
    return mark.encode() in raw.replace(b"\x00", b" ")


def _runtime(status: dict[str, Any], *, now_ms: float, mark: str) -> RuntimeSnapshot:
    heartbeat = status.get("heartbeat_at_ms")
    age = None
    if isinstance(heartbeat, (int, float)) and not isinstance(heartbeat, bool) and heartbeat > 0:
        age = max(0.0, (now_ms - float(heartbeat)) / 1000.0)
    transition = status.get("last_task_transition_at_ms")
    idle = 0.0
    if isinstance(transition, (int, float)) and not isinstance(transition, bool) and transition > 0:
        idle = max(0.0, (now_ms - float(transition)) / 1000.0)
    return RuntimeSnapshot(
        supervisor_alive=_supervisor_alive(status.get("pid"), mark),
        phase=str(status.get("phase") or ""),
        active_task_id=str(status.get("active_task_id") or ""),
        heartbeat_age_s=age,
        idle_for_s=idle,
        work_complete=status.get("work_complete") is True,
        completion_authority=status.get("completion_authority") is True,
    )


def _successor(root: Path, profile_path: Path) -> dict[str, Any]:
    profile = _read_json(profile_path)
    from swissknife_visual_functional_proof_ceiling import record_proof_ceiling_plan

    planned = record_proof_ceiling_plan(root, profile)
    planned["work_complete"] = False
    planned["completion_authority"] = False
    return planned


def apply_packet(path: Path) -> int:
    """Run as the repair subagent. Refuse completion and forbidden effects."""

    packet = _read_json(path)
    board_path = ROOT / str(packet.get("board_path") or "")
    board_text = ""
    if packet.get("repair_kind") in {"repair_board", "successor_tasks"} and board_path.is_file():
        board_text = board_path.read_text(encoding="utf-8")
    profile_path = ROOT / str(packet.get("profile_path") or "")

    def successor() -> dict[str, Any]:
        return _successor(ROOT, profile_path)

    proposals = None
    if packet.get("repair_kind") == "successor_tasks":
        from swissknife_visual_functional_proof_ceiling import propose_successor_tasks

        proposals = propose_successor_tasks(ROOT, _read_json(profile_path))
    result = apply_repair_packet(
        packet,
        board_text=board_text,
        successor=successor if packet.get("repair_kind") == "successor_subgoals" else None,
        proposals=proposals,
    )
    result["schema"] = BOARD_STALL_RECEIPT_SCHEMA
    result["work_complete"] = False
    result["completion_authority"] = False
    if (
        result.get("applied")
        and result.get("reason") in {"missing_status_inserted", "successor_tasks_recorded"}
        and result.get("board_text") != board_text
        and board_path.is_file()
    ):
        _atomic_bytes(board_path, str(result["board_text"]).encode())
    result.pop("board_text", None)
    receipt_path = Path(str(packet.get("receipt_path") or ""))
    if receipt_path:
        _atomic_bytes(receipt_path, (json.dumps(result, indent=2, sort_keys=True) + "\n").encode())
    return 0 if result.get("applied") or result.get("reason") == str(packet.get("reason") or "record_only") else 2


def _log(path: Path, line: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line.rstrip() + "\n")


def run_cycle(
    config: dict[str, Any],
    *,
    now_ms: float,
    child: dict[str, Any] | None,
    allow_spawn: bool = True,
) -> dict[str, Any]:
    """Observe once and spawn at most one repair subagent."""

    root = Path(str(config.get("repo_root") or ROOT))
    state_dir = root / str(config["state_dir"])
    state_dir.mkdir(parents=True, exist_ok=True)
    state_path = state_dir / "state.json"
    state = _read_json(state_path)
    state["work_complete"] = False
    state["completion_authority"] = False
    if child and child.get("proc") is not None:
        proc = child["proc"]
        started = float(child.get("started") or now_ms / 1000.0)
        returncode = proc.poll()
        if returncode is None and (time.time() - started) > _CHILD_TIMEOUT_S:
            try:
                os.killpg(proc.pid, 15)
            except OSError:
                pass
            returncode = proc.poll()
        if returncode is None:
            return {"action": "subagent_running", "child": child, "state": state}
        receipt = _read_json(state_dir / "receipt.json")
        signature = str(state.get("attempt_signature") or "")
        accepted = accept_receipt(receipt, signature) if returncode == 0 else {
            "accepted": False, "reason": f"subagent_exit_{returncode}",
        }
        if accepted["accepted"]:
            state["last_success_signature"] = signature
            kind = str(receipt.get("repair_kind") or state.get("pending_kind") or "")
            if state.get("repair_signature") != signature:
                state["completed_kinds"] = []
            kinds = [item for item in (state.get("completed_kinds") or []) if isinstance(item, str)]
            if kind and kind not in kinds:
                kinds.append(kind)
            state["completed_kinds"] = kinds
            state["repair_signature"] = signature
        state["child_pid"] = 0
        state["last_receipt_reason"] = accepted["reason"]
        child = None
    board_path = root / str(config["board_path"])
    status_path = root / str(config["status_path"])
    text = board_path.read_text(encoding="utf-8")
    parsed = parse_task_board(text, str(config["task_prefix"]))
    runtime = _runtime(
        _read_json(status_path),
        now_ms=now_ms,
        mark=str(config.get("supervisor_cmdline_mark") or ""),
    )
    verdict = classify_board_stall(
        parsed,
        runtime,
        idle_stall_seconds=float(config.get("idle_stall_seconds") or 300),
        heartbeat_stale_seconds=float(config.get("heartbeat_stale_seconds") or 600),
    )
    signature = stall_signature(parsed, verdict)
    alive = bool(child and child.get("proc") is not None and child["proc"].poll() is None)
    decision = decide_spawn(state, verdict, signature, child_alive=alive)
    action = str(decision["action"])
    if decision["spawn"] and not allow_spawn:
        action = "repair_pending"
    elif decision["spawn"]:
        packet_path = state_dir / "packet.json"
        receipt_path = state_dir / "receipt.json"
        if receipt_path.exists():
            receipt_path.unlink()
        packet = {
            "schema": BOARD_STALL_PACKET_SCHEMA,
            "repair_kind": decision["repair_kind"],
            "reason": verdict.reason,
            "task_ids": list(verdict.task_ids),
            "requested_effects": [],
            "work_complete": False,
            "completion_authority": False,
            "signature": signature,
            "board_path": str(config["board_path"]),
            "prefix": str(config["task_prefix"]),
            "profile_path": str(config["profile_path"]),
            "repo_root": str(root),
            "receipt_path": str(receipt_path),
        }
        _atomic_bytes(packet_path, (json.dumps(packet, indent=2, sort_keys=True) + "\n").encode())
        log_handle = (state_dir / "subagent.log").open("a", encoding="utf-8")
        import subprocess
        proc = subprocess.Popen(
            [sys.executable, "-B", str(Path(__file__).resolve()), "--apply-packet", str(packet_path)],
            cwd=str(root),
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        state["attempts"] = int(decision["attempts"])
        state["attempt_signature"] = signature
        state["pending_kind"] = decision["repair_kind"]
        state["child_pid"] = proc.pid
        child = {"proc": proc, "started": time.time()}
        action = "subagent_started"
    state["last_action"] = action
    state["last_reason"] = verdict.reason
    state["last_signature"] = signature
    state["supervisor_alive"] = runtime.supervisor_alive
    state["work_complete"] = False
    state["completion_authority"] = False
    _atomic_bytes(state_path, (json.dumps(state, indent=2, sort_keys=True) + "\n").encode())
    return {"action": action, "reason": verdict.reason, "child": child, "state": state}


def serve(config: dict[str, Any], *, once: bool) -> int:
    if config.get("restart_supervisor") is True:
        raise SystemExit("this watchdog does not restart the supervisor")
    state_dir = Path(str(config.get("repo_root") or ROOT)) / str(config["state_dir"])
    state_dir.mkdir(parents=True, exist_ok=True)
    lock_path = state_dir / "watch.lock"
    lock_handle = lock_path.open("a", encoding="utf-8")
    import fcntl
    try:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        return 0
    log_path = state_dir / "watch.log"
    child: dict[str, Any] | None = None
    previous = ""
    spawned = 0
    poll = max(15.0, float(config.get("poll_seconds") or 60))
    while True:
        outcome = run_cycle(config, now_ms=time.time() * 1000.0, child=child)
        child = outcome.get("child")
        action = str(outcome.get("action") or "")
        if action != previous:
            _log(log_path, f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} {action} {outcome.get('reason', '')}")
            previous = action
        if once:
            if action == "subagent_started":
                spawned += 1
            if spawned > 8:
                return 1
            if child and child.get("proc") is not None:
                try:
                    child["proc"].wait(timeout=_CHILD_TIMEOUT_S)
                except Exception:
                    try:
                        os.killpg(child["proc"].pid, 15)
                    except OSError:
                        pass
                continue
            quiet = action in {"observe", "already_repaired", "repair_attempt_cap"}
            accepted = outcome.get("state", {}).get("last_success_signature")
            return 0 if accepted or quiet else 1
        time.sleep(poll)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "config/agent_supervisor_board_stall_watchdog.json")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--apply-packet", type=Path)
    args = parser.parse_args(argv)
    if args.apply_packet:
        return apply_packet(args.apply_packet)
    config = _read_json(args.config)
    if not config:
        raise SystemExit(f"missing watchdog config: {args.config}")
    return serve(config, once=args.once)


if __name__ == "__main__":
    raise SystemExit(main())
