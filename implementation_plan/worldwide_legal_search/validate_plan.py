#!/usr/bin/env python3
"""Validate the campaign definition and, optionally, its real native parsers.

Does not start a supervisor, call a model, or validate unimplemented website code.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
import tempfile

HERE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def relative(value: str) -> None:
    path = Path(value)
    require(bool(value) and not path.is_absolute() and ".." not in path.parts and "\0" not in value, "unsafe output path: " + value)


def validate(package: Path = HERE, native_root: Path | None = None) -> dict:
    plan = json.loads((package / "plan.json").read_text(encoding="utf-8"))
    policy = json.loads((package / "watchdog.policy.json").read_text(encoding="utf-8"))
    from watchdog_loop import policy_check
    policy_check(policy)
    require(plan["schema"] == "worldwide-legal-search.plan@1", "invalid plan schema")
    tasks, goals = plan["tasks"], plan["goals"]
    by_id = {t["id"]: t for t in tasks}
    by_goal = {g["id"]: g for g in goals}
    require(len(by_id) == len(tasks) and len(by_goal) == len(goals), "duplicate task/goal identity")
    require("WWL-G000" in by_goal and len(tasks) > 50, "incomplete campaign")
    require(plan["execution"]["live_launch_performed"] is False, "bootstrap cannot claim a live run")
    require(plan["routing"]["primary_model"] == "grok-4.7" and plan["routing"]["router"] == "ipfs_accelerate_py.llm_router", "wrong requested primary route")
    require(plan["routing"]["policy"] == "grok_quota_auth_or_unavailable" and plan["routing"]["unchanged_workspace_required"] is True, "emergency route lost side-effect protection")
    require(not plan["routing"]["mandatory_routine_codex_review"], "Codex should remain emergency-only")
    require([p["phase"] for p in plan["source_expansion"]["phases"]] == ["normalize", "index", "geo", "publish", "verify"], "source expansion must include immutable publication before verification")
    require("WWL-105" in by_id["WWL-005"]["depends_on"], "sustained recovery canary must follow fault/restart verification")
    for task in tasks:
        identity = task["id"]
        require(bool(re.fullmatch(r"WWL-\d{3}", identity)), "invalid task ID")
        require(task["status"] == "todo", identity + ": bootstrap task must be todo")
        require(task["goal_id"] in by_goal and task["subgoal_id"] in by_goal, identity + ": missing goal")
        require(by_goal[task["subgoal_id"]]["parent_ids"] == [task["goal_id"]], identity + ": inconsistent subgoal parent")
        require(identity in by_goal[task["subgoal_id"]]["task_ids"], identity + ": missing subgoal membership")
        require(task["repository"] in {"site", "accelerate"}, identity + ": unknown execution repository")
        require(task["outputs"] and task["acceptance"] and task["validation_argv"], identity + ": incomplete acceptance contract")
        require(all(d in by_id and d != identity for d in task["depends_on"]), identity + ": invalid dependency")
        require(len(task["depends_on"]) == len(set(task["depends_on"])), identity + ": duplicate dependency")
        for output in [*task["outputs"], task["evidence_output"], *task["write_scope"]]:
            relative(output)
        for command in task["validation_argv"]:
            require(isinstance(command, list) and command and all(isinstance(v, str) and v for v in command), identity + ": validation argv must be a string array")
            require(command[0] in {"python3", "npm", "node"}, identity + ": unsupported validation executable")
            for arg in command:
                if arg.startswith(("tests/", "test/")) and arg.endswith((".ts", ".tsx", ".py")):
                    require(arg in task["outputs"], identity + ": validation test must be a declared deliverable")
        require(task["bounds"]["max_attempts"] == 3 and task["bounds"]["validation_reserve_percent"] >= 25, identity + ": invalid retry/validation bound")
    order, visiting, visited = [], set(), set()

    def visit(identity: str) -> None:
        require(identity not in visiting, "task dependency cycle: " + identity)
        if identity in visited:
            return
        visiting.add(identity)
        for dependency in by_id[identity]["depends_on"]:
            visit(dependency)
        visiting.remove(identity)
        visited.add(identity)
        order.append(identity)

    for identity in by_id:
        visit(identity)
    require(set(by_goal["WWL-G000"]["task_ids"]) == set(by_id), "root does not cover every task")
    for goal in goals:
        require(goal["task_ids"] and set(goal["task_ids"]) <= set(by_id), "empty or invalid goal task membership: " + goal["id"])
        require(all(p in by_goal for p in goal["parent_ids"]), "unknown goal parent")
    # Rebuild projections in temporary storage so edits cannot drift unnoticed.
    import build_plan
    original = build_plan.HERE
    try:
        with tempfile.TemporaryDirectory(prefix="wwl-plan-check-") as directory:
            build_plan.HERE = Path(directory)
            # Suppress the generator's normal informational line.
            import contextlib
            import io
            with contextlib.redirect_stdout(io.StringIO()):
                build_plan.build()
            for name in ("plan.json", "tasks.todo.md", "goals.objectives.md", "supervisor.json"):
                require((package / name).read_bytes() == (build_plan.HERE / name).read_bytes(), "generated artifact differs from definition: " + name)
    finally:
        build_plan.HERE = original
    result = {"schema": "worldwide-legal-search.plan-validation@1", "tasks": len(tasks), "goals": len(goals), "ready_initial_task_ids": [t["id"] for t in tasks if not t["depends_on"]], "topological_order": order,
              "native_checked": False, "implementation_checks_run": False, "provider_calls": 0}
    if native_root:
        sys.path.insert(0, str(native_root.expanduser().resolve()))
        from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_supervisor import load_supervisor_scheduler_config
        from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import parse_task_file
        from ipfs_accelerate_py.agent_supervisor.objectives.objective_graph import parse_goal_heap
        from ipfs_accelerate_py.agent_supervisor.rescue.supervisor_watchdog import AutonomousUnstallPolicy
        repo = package.parents[1]
        native_profile = load_supervisor_scheduler_config(package / "supervisor.json", repo_root=repo)
        native_tasks = parse_task_file(package / "tasks.todo.md", "## WWL-")
        native_goals = parse_goal_heap((package / "goals.objectives.md").read_text(encoding="utf-8"))
        require([t.task_id for t in native_tasks] == list(by_id), "native task parsing lost IDs")
        require([g.goal_id for g in native_goals] == [g["id"] for g in goals], "native objective parsing lost IDs")
        for task in native_tasks:
            require(task.status == "todo" and task.completion == "auto", task.task_id + ": native task status/completion drift")
            require(list(task.depends_on) == by_id[task.task_id]["depends_on"], task.task_id + ": native dependency parsing drift")
            require(bool(task.validation), task.task_id + ": native validation parsing missing")
        for native_goal in native_goals:
            require(native_goal.parent_goal_ids == by_goal[native_goal.goal_id]["parent_ids"], native_goal.goal_id + ": native parent parsing drift")
        AutonomousUnstallPolicy(**policy["native_autonomous_unstall_policy"])
        require(native_profile["max_lanes"] == 1, "native initial lane bound changed")
        result["native_checked"] = True
        result["native_root"] = str(native_root.expanduser().resolve())
    return result


def baseline_check(path: Path) -> dict:
    record = json.loads(path.read_text(encoding="utf-8"))
    require(record.get("schema") == "worldwide-legal-search.baseline@1", "baseline evidence schema is missing")
    for field in ("site_revision", "reference_revisions", "dirty_paths", "active_lanes", "application_imports", "checks", "netherlands_cases"):
        require(field in record, "baseline evidence missing " + field)
    require(bool(re.fullmatch(r"[0-9a-f]{40}", record["site_revision"])), "baseline site revision is not a Git object ID")
    require(isinstance(record["checks"], list) and record["checks"], "baseline has no actual check records")
    for check in record["checks"]:
        require(isinstance(check.get("argv"), list) and check["argv"] and type(check.get("exit_code")) is int and check.get("evidence_sha256"), "baseline check lacks actual command, exit code or evidence hash")
    require(isinstance(record["netherlands_cases"], list) and record["netherlands_cases"], "baseline has no preserved Netherlands cases")
    return {"baseline_contract_valid": True, "baseline_checks": len(record["checks"]), "note": "Preexisting failures may be recorded; later release gates must pass."}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native-root", type=Path)
    parser.add_argument("--baseline-evidence", type=Path)
    args = parser.parse_args()
    try:
        result = baseline_check(args.baseline_evidence) if args.baseline_evidence else validate(native_root=args.native_root)
        print(json.dumps(result, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"valid": False, "error_class": type(exc).__name__, "error": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
