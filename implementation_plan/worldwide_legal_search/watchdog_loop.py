#!/usr/bin/env python3
"""Observe a native campaign and dispatch bounded, idempotent recovery requests.

See WATCHDOG.md. This loop is not task/completion or code-promotion authority.
It needs the campaign adapter delivered by the first implementation milestone.
"""
from __future__ import annotations

import argparse
import contextlib
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
from typing import Any

HERE = Path(__file__).resolve().parent
EXTERNAL = {"credentials", "permission", "source_unavailable", "rights", "budget"}
BINDINGS = {"task_source", "lifecycle_restart", "rescue_planner", "rescue_orchestrator", "route_policy", "independent_validation", "validated_promotion", "incident_deduplication", "meaningful_progress"}
MAX_BYTES = 1_048_576


class ContractError(ValueError):
    pass


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    if path.stat().st_size > MAX_BYTES:
        raise ContractError("JSON input exceeds the size bound")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ContractError("JSON input must be an object")
    return value


def policy_check(policy: dict[str, Any]) -> None:
    if policy.get("schema") != "worldwide-legal-search.watchdog-policy@1" or not policy.get("policy_id"):
        raise ContractError("unsupported watchdog policy")
    for field in ("poll_seconds", "confirmation_count", "confirmation_interval_seconds", "startup_grace_seconds", "idle_seconds", "heartbeat_stale_seconds", "progress_stale_seconds", "max_stage_seconds", "cooldown_seconds", "max_backoff_seconds", "max_reconcile_attempts_per_incident", "max_recovery_attempts_per_incident", "max_repairs_per_incident", "max_campaign_repairs", "max_incidents", "max_campaign_actions", "adapter_timeout_seconds"):
        value = policy.get(field)
        if type(value) is not int or value < 1:
            raise ContractError("policy requires a positive integer: " + field)
    if policy["poll_seconds"] > 60 or policy["adapter_timeout_seconds"] > 60:
        raise ContractError("poll and adapter timeouts must not exceed 60 seconds")


def snapshot_check(value: dict[str, Any], now: float, policy: dict[str, Any]) -> None:
    if value.get("schema") != "wwl.watchdog.snapshot@1":
        raise ContractError("unsupported snapshot schema")
    for key in ("run_id", "authority_revision", "accepted_tree", "progress_token", "admitted_plan_revision"):
        if not isinstance(value.get(key), str) or not value[key] or len(value[key]) > 512:
            raise ContractError("missing or invalid snapshot field: " + key)
    for key in ("stage", "task_id", "failure_key", "reproducer_receipt", "completion_receipt"):
        if not isinstance(value.get(key), str) or len(value[key]) > 512:
            raise ContractError("invalid snapshot string: " + key)
    for key in ("hold", "completion_verified", "owner_alive", "owner_identity_verified", "dependency_running", "effects_unknown"):
        if type(value.get(key)) is not bool:
            raise ContractError("invalid snapshot boolean: " + key)
    for key in ("observed_at", "heartbeat_at", "stage_deadline_at"):
        if type(value.get(key)) not in (int, float) or not math.isfinite(value[key]) or value[key] < 0:
            raise ContractError("invalid snapshot timestamp: " + key)
    if value["observed_at"] > now + 30 or now - value["observed_at"] > max(120, policy["poll_seconds"] * 3):
        raise ContractError("snapshot is stale or from the future")
    if value["heartbeat_at"] > now + 30:
        raise ContractError("heartbeat is from the future")
    if value["stage_deadline_at"] > now + policy["max_stage_seconds"]:
        raise ContractError("stage deadline exceeds the admitted maximum")
    if type(value.get("runnable_count")) is not int or value["runnable_count"] < 0:
        raise ContractError("invalid runnable count")
    for key in ("required_task_ids", "verified_task_ids"):
        values = value.get(key)
        if not isinstance(values, list) or not all(isinstance(v, str) and v for v in values) or len(set(values)) != len(values):
            raise ContractError("invalid task set: " + key)
    if not value["required_task_ids"] or not set(value["verified_task_ids"]) <= set(value["required_task_ids"]):
        raise ContractError("task verification set is outside this campaign")
    if value.get("blocked_kind") not in EXTERNAL | {"none", "software_defect"}:
        raise ContractError("unknown blocker classification")
    if value["completion_verified"] and (set(value["verified_task_ids"]) != set(value["required_task_ids"]) or not value["completion_receipt"] or value["task_id"] or value["runnable_count"] or value["effects_unknown"]):
        raise ContractError("native completion evidence conflicts with unfinished work")
    observations = value.get("action_observations", [])
    if not isinstance(observations, list) or len(observations) > policy["max_campaign_actions"]:
        raise ContractError("invalid native action observations")
    seen = set()
    for item in observations:
        if not isinstance(item, dict) or item.get("schema") != "wwl.watchdog.action-observation@1" or not isinstance(item.get("action_id"), str) or not item["action_id"] or item["action_id"] in seen:
            raise ContractError("invalid or duplicate native action observation")
        seen.add(item["action_id"])
        if item.get("status") not in {"running", "succeeded", "failed", "blocked", "unknown"} or type(item.get("effects_verified")) is not bool or not isinstance(item.get("receipt"), str) or not item["receipt"]:
            raise ContractError("native action observation lacks status or evidence")
        if item["status"] in {"succeeded", "failed", "blocked"} and not item["effects_verified"]:
            raise ContractError("native terminal action outcome has unresolved effects")
        if item["status"] == "running" and (type(item.get("deadline_at")) not in (int, float) or not math.isfinite(item["deadline_at"]) or item["deadline_at"] < 0):
            raise ContractError("running native action lacks a bounded deadline")


def initial_state(policy: dict[str, Any], run_id: str, now: float) -> dict[str, Any]:
    return {"schema": "wwl.watchdog.state@1", "run_id": run_id, "policy_digest": digest(policy), "started_at": now,
            "last_progress_at": now, "progress_token": "", "required_task_ids": [], "admitted_plan_revision": "",
            "incidents": {}, "confirmation_incident_id": "", "actions": 0, "repairs": 0, "outbox": None,
            "inflight": {}, "settled_actions": {}}


def state_check(state: dict[str, Any], policy: dict[str, Any], run_id: str) -> None:
    if state.get("schema") != "wwl.watchdog.state@1" or state.get("run_id") != run_id or state.get("policy_digest") != digest(policy):
        raise ContractError("state run or policy changed; preserve old state and use native re-admission")
    if not isinstance(state.get("incidents"), dict) or len(state["incidents"]) > policy["max_incidents"]:
        raise ContractError("invalid incident state")
    for key in ("actions", "repairs"):
        if type(state.get(key)) is not int or state[key] < 0:
            raise ContractError("invalid durable budget counter")
    for key in ("started_at", "last_progress_at"):
        if type(state.get(key)) not in (int, float) or not math.isfinite(state[key]) or state[key] < 0:
            raise ContractError("invalid durable progress timestamp")
    if not isinstance(state.get("progress_token"), str):
        raise ContractError("invalid durable progress cursor")
    required = state.get("required_task_ids")
    if not isinstance(required, list) or not all(isinstance(v, str) and v for v in required) or len(set(required)) != len(required) or not isinstance(state.get("admitted_plan_revision"), str):
        raise ContractError("invalid durable admitted task set")
    if not isinstance(state.get("confirmation_incident_id"), str):
        raise ContractError("invalid confirmation streak identity")
    for field in ("inflight", "settled_actions"):
        if not isinstance(state.get(field), dict) or len(state[field]) > policy["max_campaign_actions"]:
            raise ContractError("invalid durable action lifecycle state")
    for action_id, action in state["inflight"].items():
        if not isinstance(action, dict) or action.get("action_id") != action_id or action.get("run_id") != run_id or action.get("kind") not in {"reconcile", "recover", "repair"} or not action.get("admission_receipt") or type(action.get("deadline_at")) not in (int, float) or not math.isfinite(action["deadline_at"]) or action["deadline_at"] < 0:
            raise ContractError("invalid durable admitted action")
    for incident in state["incidents"].values():
        if not isinstance(incident, dict):
            raise ContractError("invalid durable incident")
        for key in ("confirmations", "reconcile", "recover", "repair"):
            if type(incident.get(key)) is not int or incident[key] < 0:
                raise ContractError("invalid durable incident accounting")
        for key in ("last_confirmed_at", "next_action_at"):
            if type(incident.get(key)) not in (int, float) or not math.isfinite(incident[key]) or incident[key] < 0:
                raise ContractError("invalid durable incident time")
    outbox = state.get("outbox")
    if outbox is not None and (not isinstance(outbox, dict) or outbox.get("schema") != "wwl.watchdog.action@1" or outbox.get("run_id") != run_id or not outbox.get("action_id") or outbox.get("kind") not in {"reconcile", "recover", "repair"}):
        raise ContractError("invalid durable action outbox")


def reset_confirmations(state: dict[str, Any]) -> None:
    state["confirmation_incident_id"] = ""
    for incident in state["incidents"].values():
        incident["confirmations"] = 0


def action_deadline(action: dict[str, Any], deadline: Any, policy: dict[str, Any], now: float) -> float:
    duration = policy["max_stage_seconds"] if action["kind"] == "repair" else policy["native_autonomous_unstall_policy"]["deadline_ms"] / 1000
    issued_at = action["issued_at"]
    if type(deadline) not in (int, float) or not math.isfinite(deadline) or deadline < 0 or deadline > issued_at + duration or deadline > now + duration:
        raise ContractError("native admitted action deadline exceeds its original bound")
    return float(deadline)


def reconcile_action_observations(snapshot: dict[str, Any], state: dict[str, Any], policy: dict[str, Any], now: float) -> None:
    for item in snapshot.get("action_observations", []):
        action_id = item["action_id"]
        pending = state.get("outbox")
        action = state["inflight"].get(action_id) or (pending if pending and pending["action_id"] == action_id else None)
        if not action:
            continue
        if item["status"] in {"succeeded", "failed", "blocked"}:
            state["settled_actions"][action_id] = {"status": item["status"], "receipt": item["receipt"]}
            state["inflight"].pop(action_id, None)
            if pending and pending["action_id"] == action_id:
                state["outbox"] = None
        elif item["status"] == "running":
            deadline = action_deadline(action, item["deadline_at"], policy, now)
            state["inflight"][action_id] = {**action, "admission_receipt": item["receipt"], "deadline_at": min(deadline, action.get("deadline_at", deadline)), "outcome_unknown": False}
            if pending and pending["action_id"] == action_id:
                state["outbox"] = None
        elif action_id in state["inflight"]:
            state["inflight"][action_id]["outcome_unknown"] = True


def decide(snapshot: dict[str, Any], state: dict[str, Any], policy: dict[str, Any], now: float) -> dict[str, Any]:
    """Update bounded observation state and return at most one native request."""
    snapshot_check(snapshot, now, policy)
    state_check(state, policy, snapshot["run_id"])
    if not set(state["required_task_ids"]) <= set(snapshot["required_task_ids"]):
        raise ContractError("native task set pruned previously admitted work, including across restart")
    state["required_task_ids"] = list(snapshot["required_task_ids"])
    state["admitted_plan_revision"] = snapshot["admitted_plan_revision"]
    if now < state["last_progress_at"] or now < state["started_at"]:
        raise ContractError("clock moved backwards; reconcile through native authority")

    def report(status: str, reason: str, **fields: Any) -> dict[str, Any]:
        return {"schema": "wwl.watchdog.report@1", "run_id": snapshot["run_id"], "status": status, "reason": reason, "completion_authority": False, **fields}

    def passive(status: str, reason: str, **fields: Any) -> dict[str, Any]:
        reset_confirmations(state)
        return report(status, reason, **fields)

    if snapshot["hold"]:
        return passive("held", "native_pause_or_hold")
    reconcile_action_observations(snapshot, state, policy, now)
    pending = state.get("outbox")
    inflight = state["inflight"]
    if snapshot["completion_verified"] and not pending and not inflight:
        return passive("complete", "native_current_tree_completion_verified", receipt=snapshot["completion_receipt"])
    if snapshot["progress_token"] != state["progress_token"]:
        state["progress_token"] = snapshot["progress_token"]
        state["last_progress_at"] = now
        # A resolved episode needs fresh confirming observations. Its attempt
        # counters remain durable if the same defect returns later.
        reset_confirmations(state)

    reason, kind = "", ""
    if pending or snapshot["effects_unknown"]:
        reason, kind = "unknown_effects", "reconcile"
    elif any(not action.get("outcome_unknown") and now < action["deadline_at"] for action in inflight.values()):
        return passive("waiting", "native_action_in_progress", action_ids=list(inflight))
    elif inflight:
        reason, kind = "native_action_unsettled_or_expired", "reconcile"
    elif snapshot["blocked_kind"] in EXTERNAL and snapshot["runnable_count"] == 0:
        return passive("blocked", "external_" + snapshot["blocked_kind"])
    elif snapshot["blocked_kind"] == "software_defect":
        if not snapshot["failure_key"] or not snapshot["reproducer_receipt"]:
            reason, kind = "defect_needs_reproduction", "reconcile"
        else:
            reason, kind = "reproduced_supervisor_defect", "repair"
    elif now - state["started_at"] < policy["startup_grace_seconds"]:
        return passive("observing", "startup_grace")
    elif snapshot["dependency_running"] and snapshot["runnable_count"] == 0 and not snapshot["task_id"]:
        return passive("waiting", "dependency_work_in_progress")
    elif not snapshot["owner_alive"] and (snapshot["task_id"] or snapshot["runnable_count"]):
        reason, kind = "owner_absent", "recover"
    elif snapshot["owner_alive"] and not snapshot["owner_identity_verified"]:
        reason, kind = "owner_identity_unverified", "reconcile"
    elif snapshot["task_id"] and snapshot["stage_deadline_at"] and now >= snapshot["stage_deadline_at"]:
        reason, kind = "stage_deadline_expired", "reconcile"
    elif snapshot["task_id"] and now - snapshot["heartbeat_at"] >= policy["heartbeat_stale_seconds"]:
        reason, kind = "heartbeat_stale", "reconcile"
    elif snapshot["task_id"] and now - state["last_progress_at"] >= policy["progress_stale_seconds"]:
        reason, kind = "meaningful_progress_stalled", "reconcile"
    elif snapshot["runnable_count"] and not snapshot["task_id"] and now - state["last_progress_at"] >= policy["idle_seconds"]:
        reason, kind = "runnable_work_idle", "recover"
    elif not snapshot["task_id"] and not snapshot["runnable_count"] and set(snapshot["verified_task_ids"]) == set(snapshot["required_task_ids"]):
        reason, kind = "completion_needs_native_verification", "reconcile"
    elif not snapshot["task_id"] and not snapshot["runnable_count"]:
        reason, kind = "unfinished_work_has_no_runnable_frontier", "reconcile"
    else:
        return passive("healthy", "bounded_work_in_progress")

    unsettled = pending or next(iter(inflight.values()), None)
    if unsettled:
        # A lost ACK keeps the ORIGINAL incident, so restart or changing
        # observe revisions cannot reset the unknown-effect recovery bound.
        incident_id = unsettled["incident_id"]
    else:
        incident_id = digest([snapshot["run_id"], snapshot["task_id"], snapshot["stage"], snapshot["failure_key"], reason])
    incidents = state["incidents"]
    if incident_id not in incidents:
        if len(incidents) >= policy["max_incidents"]:
            return report("blocked", "campaign_incident_budget_exhausted")
        incidents[incident_id] = {"confirmations": 0, "last_confirmed_at": 0, "next_action_at": 0, "reconcile": 0, "recover": 0, "repair": 0}
    incident = incidents[incident_id]
    if state["confirmation_incident_id"] != incident_id:
        reset_confirmations(state)
        state["confirmation_incident_id"] = incident_id
    if incident["confirmations"] == 0 or now - incident["last_confirmed_at"] >= policy["confirmation_interval_seconds"]:
        incident["confirmations"] += 1
        incident["last_confirmed_at"] = now
    if incident["confirmations"] < policy["confirmation_count"]:
        return report("suspect", reason, incident_id=incident_id, confirmations=incident["confirmations"])
    if now < incident["next_action_at"]:
        return report("cooldown", reason, incident_id=incident_id, until=incident["next_action_at"])
    limit_key = {"reconcile": "max_reconcile_attempts_per_incident", "recover": "max_recovery_attempts_per_incident", "repair": "max_repairs_per_incident"}[kind]
    if incident[kind] >= policy[limit_key]:
        return report("blocked", kind + "_incident_budget_exhausted", incident_id=incident_id)
    if state["actions"] >= policy["max_campaign_actions"] or (kind == "repair" and state["repairs"] >= policy["max_campaign_repairs"]):
        return report("blocked", "campaign_action_budget_exhausted", incident_id=incident_id)
    incident[kind] += 1
    state["actions"] += 1
    state["repairs"] += int(kind == "repair")
    incident["next_action_at"] = now + min(policy["max_backoff_seconds"], policy["cooldown_seconds"] * 2 ** (incident[kind] - 1))
    action = {"schema": "wwl.watchdog.action@1", "run_id": snapshot["run_id"], "policy_id": policy["policy_id"], "incident_id": incident_id,
              "action_id": digest([snapshot["run_id"], incident_id, state["actions"]]), "kind": kind, "reason": reason,
              "task_id": snapshot["task_id"], "stage": snapshot["stage"], "authority_revision": snapshot["authority_revision"],
              "accepted_tree": snapshot["accepted_tree"], "reproducer_receipt": snapshot["reproducer_receipt"],
              "issued_at": now, "unsettled_action_ids": list(dict.fromkeys([*inflight, *([pending["action_id"]] if pending else [])])),
              "previous_unacknowledged_action": pending["action_id"] if pending else ""}
    state["outbox"] = action
    return report("action_requested", reason, action=action)


def atomic_save(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".wwl-watchdog-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(state, stream, sort_keys=True, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(name):
            os.unlink(name)


@contextlib.contextmanager
def owner_lock(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+", encoding="utf-8") as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ContractError("a watchdog already owns this state") from exc
        yield


def call_adapter(argv: list[str], operation: str, request: dict[str, Any], timeout: int) -> dict[str, Any]:
    # Temporary files keep a noisy/malformed adapter from growing RAM without
    # bound; the process contract itself is also subject to native host limits.
    with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as errors:
        result = subprocess.run([*argv, operation], input=json.dumps(request).encode(), stdout=output, stderr=errors, timeout=timeout, check=False)
        if result.returncode != 0:
            raise ContractError(f"native adapter {operation} failed with exit {result.returncode}; inspect native host logs")
        if output.tell() > MAX_BYTES:
            raise ContractError("native adapter output exceeds its bound")
        output.seek(0)
        value = json.loads(output.read().decode("utf-8"))
    if not isinstance(value, dict):
        raise ContractError("native adapter returned a non-object")
    return value


def ready_check(ready: dict[str, Any], plan: dict[str, Any], policy: dict[str, Any]) -> str:
    if ready.get("schema") != "wwl.watchdog.ready@1" or ready.get("policy_id") != policy["policy_id"]:
        raise ContractError("native adapter policy handshake failed")
    for key in ("run_id", "native_revision", "readiness_receipt"):
        if not isinstance(ready.get(key), str) or not ready[key]:
            raise ContractError("native adapter readiness missing: " + key)
    if ready.get("repository") != plan["product"]["repository"]:
        raise ContractError("native adapter repository differs from campaign")
    required = ready.get("required_task_ids")
    core = {t["id"] for t in plan["tasks"]}
    if not isinstance(required, list) or not all(isinstance(v, str) for v in required) or len(set(required)) != len(required) or not core <= set(required):
        raise ContractError("native adapter required task set omits core tasks")
    expanded = set(required) - core
    if expanded and (not all(re.fullmatch(plan["source_expansion"]["id_pattern"], v) for v in expanded) or not ready.get("expansion_receipt")):
        raise ContractError("expanded source tasks lack the native admitted expansion receipt")
    if not isinstance(ready.get("admitted_plan_revision"), str) or not ready["admitted_plan_revision"]:
        raise ContractError("native admitted plan revision is missing")
    bindings = ready.get("bindings")
    if not isinstance(bindings, dict) or any(bindings.get(k) is not True for k in BINDINGS):
        raise ContractError("native lifecycle, progress or validated repair binding is missing; complete WWL-004/005/102")
    return ready["run_id"]


def acknowledge(state: dict[str, Any], result: dict[str, Any], policy: dict[str, Any], now: float) -> None:
    action = state["outbox"]
    if not action or result.get("schema") != "wwl.watchdog.action-result@1" or result.get("action_id") != action["action_id"] or result.get("status") not in {"accepted", "blocked", "unknown"} or not isinstance(result.get("receipt"), str) or not result["receipt"]:
        raise ContractError("dispatch acknowledgement is missing or mismatched; effects remain unknown")
    if result["status"] == "accepted":
        deadline = action_deadline(action, result.get("deadline_at"), policy, now)
        if deadline <= now:
            raise ContractError("native action admission already expired; effects remain unknown")
        state["inflight"][action["action_id"]] = {**action, "deadline_at": deadline, "admission_receipt": result["receipt"], "outcome_unknown": False}
        state["outbox"] = None
    elif result["status"] == "blocked":
        # The native refusal receipt establishes no admitted operation.
        state["settled_actions"][action["action_id"]] = {"status": "blocked", "receipt": result["receipt"]}
        state["outbox"] = None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", type=Path, default=HERE / "watchdog.policy.json")
    parser.add_argument("--plan", type=Path, default=HERE / "plan.json")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--snapshot", type=Path, help="Fixture observation; never dispatches live recovery")
    source.add_argument("--adapter-argv-json", help="Registered native adapter argv; never executed through a shell")
    parser.add_argument("--state", type=Path, default=HERE / ".runtime/watchdog.json")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--execute", action="store_true", help="Persist state and request native recovery; requires the ready adapter")
    args = parser.parse_args(argv)
    try:
        if args.snapshot and args.execute:
            raise ContractError("a fixture cannot authorize live recovery")
        if args.snapshot and not args.once:
            raise ContractError("snapshot fixtures require --once; use the native adapter for a live loop")
        policy, plan = read_json(args.policy), read_json(args.plan)
        policy_check(policy)
        command = json.loads(args.adapter_argv_json) if args.adapter_argv_json else []
        if args.adapter_argv_json and (not isinstance(command, list) or not command or not all(isinstance(v, str) and v and "\0" not in v for v in command)):
            raise ContractError("adapter argv must be a nonempty JSON string array")
        request = {"schema": "wwl.watchdog.request@1", "operation": "ready", "policy_id": policy["policy_id"], "required_task_ids": [t["id"] for t in plan["tasks"]]}
        run_id = ""
        if command:
            ready = call_adapter(command, "ready", request, policy["adapter_timeout_seconds"])
            run_id = ready_check(ready, plan, policy)
            request["required_task_ids"] = ready["required_task_ids"]
            request["admitted_plan_revision"] = ready["admitted_plan_revision"]
        # Observation-only operation holds no write lock and writes no state.
        lock = owner_lock(args.state.with_suffix(args.state.suffix + ".lock")) if args.execute else contextlib.nullcontext()
        with lock:
            state = read_json(args.state) if args.execute and args.state.exists() else None
            if state is not None:
                state_check(state, policy, run_id)
                if not set(state["required_task_ids"]) <= set(request["required_task_ids"]):
                    raise ContractError("native readiness pruned required tasks recorded before restart")
            while True:
                request.update(operation="observe", run_id=run_id)
                request["action_ids"] = list(dict.fromkeys([*(state["inflight"] if state else []), *([state["outbox"]["action_id"]] if state and state["outbox"] else [])]))
                snapshot = call_adapter(command, "observe", request, policy["adapter_timeout_seconds"]) if command else read_json(args.snapshot)
                # Fixture-only observations use their recorded clock. They
                # cannot authorize dispatch, and are deliberately single-pass.
                now = time.time() if command else snapshot["observed_at"]
                if run_id and snapshot.get("run_id") != run_id:
                    raise ContractError("native observation changed run identity")
                if command and (snapshot.get("required_task_ids") != request["required_task_ids"] or snapshot.get("admitted_plan_revision") != request["admitted_plan_revision"]):
                    refreshed = call_adapter(command, "ready", request, policy["adapter_timeout_seconds"])
                    if ready_check(refreshed, plan, policy) != run_id or not set(request["required_task_ids"]) <= set(refreshed["required_task_ids"]) or snapshot.get("required_task_ids") != refreshed["required_task_ids"] or snapshot.get("admitted_plan_revision") != refreshed["admitted_plan_revision"]:
                        raise ContractError("native source expansion changed run identity, pruned work or lacks current evidence")
                    request["required_task_ids"] = refreshed["required_task_ids"]
                    request["admitted_plan_revision"] = refreshed["admitted_plan_revision"]
                state = state if state is not None else initial_state(policy, snapshot["run_id"], now)
                before = json.loads(json.dumps(state)) if not args.execute else None
                report = decide(snapshot, state, policy, now)
                if args.execute:
                    # Write-ahead persistence includes charged action budgets.
                    atomic_save(args.state, state)
                    if report.get("action"):
                        try:
                            result = call_adapter(command, "dispatch", report["action"], policy["adapter_timeout_seconds"])
                            acknowledge(state, result, policy, time.time())
                            report["dispatch_status"] = result["status"]
                        except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
                            report["dispatch_status"] = "unknown"
                            report["dispatch_error_class"] = type(exc).__name__
                        atomic_save(args.state, state)
                else:
                    report["observation_only"] = True
                    report["fixture"] = bool(args.snapshot)
                    if report.get("action"):
                        # A preview must not pretend an effect was attempted.
                        state = before
                        report["status"] = "would_request_action"
                print(json.dumps(report, sort_keys=True), flush=True)
                if report["status"] == "complete":
                    return 0
                if report["status"] == "blocked" and report["reason"].endswith("budget_exhausted"):
                    return 3
                if args.once:
                    return 3 if report["status"] == "blocked" else 0
                time.sleep(policy["poll_seconds"])
    except (OSError, ValueError, KeyError, subprocess.TimeoutExpired) as exc:
        print(json.dumps({"schema": "wwl.watchdog.error@1", "error": str(exc), "completion_authority": False}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
