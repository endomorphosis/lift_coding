"""Seed a real Profile G goal -> subgoal/branch -> selection -> task chain
through the datasets compat adapter (:3002) Profile G mutations, so the
Agent Supervisor console has a legitimate steering target in its live
snapshot. Artifacts are built and pre-validated with the datasets
package's own logic (profile_g_cid / GoalPlanValidator); every mutation
goes over the wire with the gateway's mutation-context envelope.
Prints the resulting CIDs as JSON."""
import importlib.util  # noqa: F401
import json
import time
import urllib.request

ADAPTER = "http://127.0.0.1:3002/mcp"

from ipfs_datasets_py.logic.profile_g import (
    GoalPlanValidator,
    profile_g_cid,
    validate_profile_g_artifact,
)

NOW_MS = int(time.time() * 1000)
DID = "did:key:zSupervisorConsoleSeed"
CORR = "steering-route-seed-2026-10-14"


def filler(label: str) -> str:
    return profile_g_cid({"schema": "steering-route/seed-ref@1", "label": label})


def base() -> dict:
    return {"created_at_ms": NOW_MS, "parents": [], "correlation_id": CORR}


def ctx(step: str) -> dict:
    return {
        "idempotency_key": f"steering-route-seed:{step}",
        "correlation_id": CORR,
        "caller_did": DID,
        "proof_cid": filler(f"proof:{step}"),
        "policy_decision_cid": filler(f"policy-decision:{step}"),
        "parents": [],
    }


def rpc(method: str, params: dict) -> dict:
    body = json.dumps({"jsonrpc": "2.0", "id": method, "method": method, "params": params}).encode()
    req = urllib.request.Request(ADAPTER, data=body, headers={"content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.loads(resp.read())
    if "error" in payload:
        raise RuntimeError(f"{method} -> {json.dumps(payload['error'])[:400]}")
    return payload["result"]


goal = {
    "schema": "mcp++/profile-g/goal@1",
    **base(),
    "owner_did": DID,
    "objective_cid": filler("objective:supervisor-steering-verification"),
    "policy_cid": filler("policy:supervisor-console-seed"),
    "parent_goal_cids": [],
    "labels": ["steering-route", "supervisor-console"],
}
goal_cid = validate_profile_g_artifact("Goal", goal)

subgoal = {
    "schema": "mcp++/profile-g/subgoal@1",
    **base(),
    "goal_cid": goal_cid,
    "parent_subgoal_cid": None,
    "objective_cid": filler("objective:steerable-verification-task"),
    "decomposition_method": "manual-seed",
    "decomposer_cid": filler("decomposer:steering-route-seed"),
    "selection_cid": None,
}
subgoal_cid = validate_profile_g_artifact("Subgoal", subgoal)

branch = {
    "schema": "mcp++/profile-g/plan-branch@1",
    **base(),
    "subgoal_cid": subgoal_cid,
    "candidate_input_cids": [],
    "task_template_cids": [filler("task-template:steering-verification")],
    "evaluator_cid": filler("evaluator:steering-route-seed"),
    "score_millionths": 900000,
    "explanation_cid": filler("explanation:direct-verification-branch"),
}
branch_cid = validate_profile_g_artifact("PlanBranch", branch)

selection = {
    "schema": "mcp++/profile-g/plan-selection@1",
    **base(),
    "subgoal_cid": subgoal_cid,
    "plan_branch_cid": branch_cid,
    "selector_did": DID,
    "proof_cid": filler("proof:plan-selection"),
    "policy_decision_cid": filler("policy-decision:plan-selection"),
    "reason_cid": filler("reason:only-branch"),
}
selection_cid = validate_profile_g_artifact("PlanSelection", selection)

task = {
    "schema": "mcp++/profile-g/task@1",
    **base(),
    "subgoal_cid": subgoal_cid,
    "plan_branch_cid": branch_cid,
    "selection_cid": selection_cid,
    "interface_cid": filler("interface:agent-supervisor-prompt-steering"),
    "input_cid": filler("input:steering-verification-backlog"),
    "tool": "agent_supervisor.prompt_steering.request",
    "dependency_task_cids": [],
    "idempotency_key": "steering-route-seed:task",
    "resource_class": "supervisor-verification",
    "deadline_ms": None,
    "expected_value_millionths": 800000,
    "max_attempts": 3,
    "execution_mode": "idempotent",
}
task_cid = validate_profile_g_artifact("TaskSpec", task)

# Local cross-artifact validation with a dict resolver, mirroring the service.
store = {goal_cid: goal, subgoal_cid: subgoal, branch_cid: branch, selection_cid: selection, task_cid: task}
validator = GoalPlanValidator(
    lambda cid: store.get(cid),
    authority_validator=lambda *_args: True,  # mirrors the trusted-local service
    policy_validator=lambda *_args: True,
)
assert validator.validate_goal(goal) == goal_cid
assert validator.validate_decomposition([subgoal, branch], goal_cid) == [subgoal_cid, branch_cid]
assert validator.validate_selection(selection) == selection_cid
assert validator.validate_task(task) == task_cid
print("local validation: goal/subgoal/branch/selection/task all valid", flush=True)

def attempt(method: str, params: dict) -> dict:
    try:
        return {"ok": True, "result": rpc(method, params)}
    except Exception as error:  # record the backend's verbatim denial
        return {"ok": False, "error": str(error)}


results = {}
results["goal"] = attempt("mcp++/goals/create", {"artifact": goal, **ctx("goal")})
results["decompose"] = attempt("mcp++/goals/decompose", {"goal_cid": goal_cid, "artifacts": [subgoal, branch], **ctx("decompose")})
results["select"] = attempt("mcp++/goals/select", {"artifact": selection, **ctx("select")})
results["task"] = attempt("mcp++/tasks/create", {"artifact": task, **ctx("task")})

goals = rpc("mcp++/goals/list", {})
tasks = rpc("mcp++/tasks/list", {})
print(json.dumps({
    "goal_cid": goal_cid,
    "subgoal_cid": subgoal_cid,
    "branch_cid": branch_cid,
    "selection_cid": selection_cid,
    "task_cid": task_cid,
    "mutation_outcomes": results,
    "goals_list_count": len(goals.get("items", [])),
    "tasks_list_count": len(tasks.get("items", [])),
}, indent=2))
