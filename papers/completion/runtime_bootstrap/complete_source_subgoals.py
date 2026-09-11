#!/usr/bin/env python3
"""Close only AF-S01 or LA-G1 after fresh, committed native validation.

Dry run is the default. Connects only to the campaign's existing authenticated
Quack owner; never opens database files, starts processes, or mutates tasks.
Historical completed-task evidence is authenticated without an age cutoff;
fresh verify-task and native goal-validation receipts establish currentness.
"""
from __future__ import annotations

import argparse
from collections.abc import Mapping
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
import materialize_paper_database as M
import paper_supervisor_campaign as C

STATE = Path.home() / ".local/state/ipfs_accelerate_py/vericodegen-2026"
TOKEN_ENV = "IPFS_ACCELERATE_AGENT_QUACK_TOKEN"
TARGETS = {
    "autoformalization": {
        "goal": "AF-S01", "members": ("AF-001", "AF-002", "AF-003"),
        "audit": "af_fifth_evidence_completion.json",
        "audit_sha256": "1260050fcf3e166f8fdd81d8cf35f2859fc510025c0d31554a9199afdb18af62",
        "receipts": {
            "AF-001": "5455f0b3084fd4950d35e6168193d70b152b44c7d62f9252f26ecdebe25fe4d5",
            "AF-002": "e990653ae9f80c734b673b759d9c352374d73e17aa403619e0d3dd8d5954e436",
            "AF-003": "57138515df7e9963716ce9dcbe2400d6e5a664584cfa017c9fae0ed1258867e6",
        },
    },
    "law_to_action": {
        "goal": "LA-G1", "members": ("LA-001", "LA-002"),
        "audit": "la_fifth_evidence_completion.json",
        "audit_sha256": "4fc2950cb506331d33c0261b21af68ce9784fbee1c3820fae7e29bcb27d936a5",
        "receipts": {
            "LA-001": "06ab422d87cb3cbf2341ff5384aa19701ad59f5927d6a03aa9620e6af46068b1",
            "LA-002": "625b62a00bc7508691388b3dd24c818d0345d7d8e3321ca9f33b7d5f08dc9df1",
        },
    },
}


def require(value, reason):
    if not value:
        raise RuntimeError(reason)


def plain(value):
    if isinstance(value, Mapping):
        return {str(k): plain(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [plain(v) for v in value]
    return value


def digest(value):
    return hashlib.sha256(json.dumps(plain(value), sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()


def sha(path):
    with Path(path).open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def git(repo, *argv):
    return subprocess.check_output(["git", "--no-optional-locks", "-C", str(repo), *argv],
                                   stderr=subprocess.PIPE, timeout=30)


def checked_tree(repo, paper, expected_head):
    require(git(repo, "rev-parse", "HEAD").decode().strip() == expected_head, "Source HEAD changed")
    require(git(repo, "branch", "--show-current").decode().strip() ==
            "agent/vericodegen-2026-" + paper, "Wrong integration branch")
    require(not git(repo, "status", "--porcelain=v1", "--untracked-files=all"),
            "Integration source is dirty")
    return git(repo, "rev-parse", "HEAD^{tree}").decode().strip()


def committed_file(repo, head, relative, expected=None):
    relative = Path(relative)
    require(not relative.is_absolute() and ".." not in relative.parts,
            "Evidence path must stay inside the repository")
    path = repo / relative
    require(path.resolve() == path and path.is_file(), "Evidence path is missing or redirected")
    data = git(repo, "show", f"{head}:{relative.as_posix()}")
    hashed = hashlib.sha256(data).hexdigest()
    require(sha(path) == hashed and (expected is None or hashed == expected),
            "Committed evidence hash differs: " + relative.as_posix())
    return data, hashed


def rows(connection, sql, parameters=()):
    require(sql.lstrip().upper().startswith("SELECT "), "Read helper refuses non-SELECT SQL")
    return [dict(row.items()) for row in connection.execute(sql, list(parameters)).fetchall()]


@contextmanager
def authenticated_owner(paper, repo):
    campaign = C.read(STATE / "campaign.json")
    require(not campaign.get("stopped_at") and C.alive(campaign.get("controller")),
            "Campaign is not running")
    lane = campaign["lanes"][paper]
    require(lane["repo"] == str(repo), "Wrong integration lane")
    ready_path = STATE / paper / "quack-owner/paper-owner.ready.json"
    ready = C.read(ready_path)
    expected_process = {k: lane["owner"][k] for k in ("pid", "birth", "boot_id")}
    require(ready.get("ready") and C.owner_process(ready) == expected_process
            and C.alive(expected_process), "Existing owner identity differs")
    require(ready.get("database") == str(STATE / paper / "control.duckdb")
            and ready.get("store_id") == "vericodegen-2026-" + paper,
            "Wrong owner database/store identity")
    endpoint = ready["quack_endpoint"]
    require(re.fullmatch(r"quack:127\.0\.0\.1:[0-9]+", endpoint), "Expected loopback Quack endpoint")
    environment = {
        TOKEN_ENV: C.token_for(ready, STATE / paper),
        "IPFS_ACCELERATE_AGENT_STATE_SCHEMA_REVISION": str(ready["schema_revision"]),
        "IPFS_ACCELERATE_AGENT_STATE_STORE_ID": str(STATE / paper / "control.duckdb"),
        "IPFS_ACCELERATE_AGENT_QUACK_MUTATION_DIR": str(STATE / paper / "quack-owner/mutations"),
    }
    previous = {key: os.environ.get(key) for key in environment}
    os.environ.update(environment)
    try:
        yield endpoint, ready
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def checked_owner(connection, paper, ready):
    identity = rows(connection,
        "SELECT server_id, database_uuid, generation, schema_revision FROM state_servers "
        "WHERE store_id = ? AND listen_uri = ? AND stopped_at IS NULL AND status IN ('starting', 'ready') "
        "AND generation = (SELECT max(generation) FROM state_servers WHERE store_id = ?)",
        [ready["store_id"], ready["quack_endpoint"], ready["store_id"]])
    require(len(identity) == 1, "No unique current authenticated owner")
    require(all(identity[0][k] == ready["identity"][k] for k in identity[0]),
            "Authenticated server generation/identity differs from readiness")
    uuid = rows(connection, "SELECT value FROM control_plane_metadata WHERE key = 'database_uuid'")
    require(len(uuid) == 1 and uuid[0]["value"] == identity[0]["database_uuid"], "Database UUID differs")
    current = C.read(STATE / paper / "quack-owner/paper-owner.ready.json")
    require(current == ready and C.alive(C.owner_process(current)), "Owner changed during validation")
    return identity[0]


def population(source, connection, target, seeds, baseline):
    tasks = [plain(t) for t in source.intent.list_tasks(limit=1000)]
    require(len(tasks) == 25 and {t["task_alias"] for t in tasks} == set(seeds)
            and {t["task_alias"]: t["task_cid"] for t in tasks} == baseline,
            "Exact 25-task native population changed")
    goals = rows(connection, "SELECT goal_cid, goal_alias, parent_goal_cid FROM goals ORDER BY goal_cid LIMIT 1000")
    require(len(goals) < 1000, "Goal population exceeds bounded audit")
    by_alias = {g["goal_alias"]: g for g in goals}
    require(len(by_alias) == len(goals), "Ambiguous goal aliases")
    goal = plain(source.get_goal(target["goal"]))
    require(goal and by_alias[target["goal"]]["goal_cid"] == goal["goal_cid"], "Target goal identity differs")
    # These two source goals have no child goals. Reject every additional
    # descendant even if it currently has no task; parent pointers and edges
    # are both checked, as are the task-to-goal contracts for all 25 tasks.
    require(not any(g["parent_goal_cid"] == goal["goal_cid"] for g in goals), "Target has additional descendant goals")
    edges = rows(connection, "SELECT * FROM goal_edges ORDER BY parent_goal_cid, child_goal_cid LIMIT 1000")
    require(len(edges) < 1000 and not any(e["parent_goal_cid"] == goal["goal_cid"] for e in edges),
            "Target has additional outgoing goal edges")
    for task in tasks:
        seed = seeds[task["task_alias"]]
        require(task["goal_cid"] == by_alias[seed["subgoal_id"]]["goal_cid"]
                and task["body"].get("goal id") == seed["subgoal_id"]
                and task["identity"].get("task_cid") == task["task_cid"]
                and task["identity"].get("task_alias") == task["task_alias"],
                "Native task identity or reviewed goal membership changed")
    members = {t["task_alias"]: t for t in tasks if t["goal_cid"] == goal["goal_cid"]}
    require(set(members) == set(target["members"]), "Target membership includes missing/additional tasks")
    require(set(v.strip() for v in goal["body"]["native_fields"]["gap_task"].split(",")) == set(members),
            "Native goal's declared task membership differs")
    topology = {"tasks": [{k: t[k] for k in ("task_cid", "task_alias", "goal_cid")}
                          for t in sorted(tasks, key=lambda t: t["task_alias"])],
                "goals": goals, "edges": edges}
    return goal, members, topology


def validation_evidence(connection, task, evidence, expected_digest):
    selected = [e for e in evidence if e["evidence_kind"] == "validation" and e["digest"] == expected_digest]
    require(len(selected) == 1, "Missing or ambiguous native validation evidence")
    node = selected[0]
    result = rows(connection,
        "SELECT result_id, run_id, task_cid, outcome, evidence_digest, body_json FROM validation_results "
        "WHERE result_id = ?", [node["body"]["result_id"]])
    require(len(result) == 1, "Native validation result missing")
    result = result[0]
    result["body"] = json.loads(result.pop("body_json"))
    require(result["run_id"] == node["body"]["run_id"] and result["task_cid"] == task["task_cid"]
            and result["outcome"] == node["body"]["outcome"] == "passed"
            and result["evidence_digest"] == expected_digest, "Native validation evidence/result binding differs")
    return {"node": node, "result": result}


def member_evidence(source, connection, repo, head, paper, alias, task, seed, target, audit):
    require(task["status"] == "completed", alias + " is not natively completed")
    baseline = next(t for t in audit["final_tasks"] if t["task_alias"] == alias)
    require(task["revision"] == baseline["revision"], alias + " completion revision changed")
    relative = f"papers/completion/{paper}/receipts/{alias}.json"
    data, receipt_hash = committed_file(repo, head, relative, target["receipts"][alias])
    receipt = json.loads(data)
    require(receipt.get("schema") == "paper-task-evidence/v1" and receipt.get("task_id") == alias
            and receipt.get("status") == "complete", "Paper receipt identity/status differs")
    criteria = [c["criterion"] for c in receipt["criteria"]]
    require(criteria == seed["acceptance_criteria"] == [c["criterion"] for c in task["acceptance"]]
            and all(c["status"] == "met" for c in receipt["criteria"]), "Acceptance criteria differ")
    argv = ["python3", "scripts/paper_supervisors.py", "verify-task", "--paper", paper, "--task", alias]
    require([v["argv"] for v in task["validations"]] == [argv], "Declared native task validator differs")
    for path, hashed in receipt["artifacts"].items():
        committed_file(repo, head, path, hashed)
    completion = task["body"].get("completion_receipt", {})
    require(completion.get("evidence_digest"), "Native completion receipt is absent")
    # This Source is explicitly opened with freshness_seconds=0: historical
    # proof is preserved, while fresh CLI checks below establish currentness.
    evidence = plain(source.intent.current_evidence_for_task(task["task_cid"]))
    required_ok, missing = source.intent.required_evidence_satisfied(task["task_cid"])
    require(required_ok and not missing, "Persisted native acceptance evidence missing")
    original = validation_evidence(connection, task, evidence, completion["evidence_digest"])
    if alias.endswith("-001"):
        require(completion.get("operation") == "paper_agent_assisted_checkpoint_complete"
                and completion.get("task_id") == alias and completion.get("paper_receipt") == relative
                and completion["evidence_digest"] == "sha256:" + receipt_hash,
                "Source checkpoint completion is not bound to the committed receipt")
        details = completion["validation_event"]["details"]
        require(details["result_id"] == original["result"]["result_id"]
                and details["body"] == original["result"]["body"]
                and details["body"]["acceptance_criteria"] == receipt["criteria"],
                "Checkpoint validation/acceptance binding differs")
    else:
        require(completion.get("operation") == "database_complete", "Expected native provider completion")
        validation = completion["validation"]
        preparation = completion["coordination_preparation"]
        require(validation["outcome"] == "passed" and validation["task_cid"] == task["task_cid"]
                and validation["evidence_digest"] == completion["evidence_digest"]
                and validation["attempt_id"] == completion["attempt_id"]
                and original["result"]["body"] == validation
                and all(preparation[k] == completion[k] for k in
                        ("attempt_id", "claim_id", "owner_session_id", "lease_id", "fencing_token", "fence_epoch", "evidence_digest")),
                "Native provider completion/validation identity differs")
    correction = None
    if alias in {"AF-003", "LA-002"}:
        expected = next(m for m in audit["mutations"] if m["kind"] == "append_corrected_evidence"
                        and m["receipt"]["task_id"] == alias)
        corrected = [e for e in evidence if e["evidence_id"] == expected["event"]["subject_id"]]
        require(len(corrected) == 1, "Reviewed appended correction node missing")
        node = corrected[0]
        body = node["body"]
        require(body == expected["receipt"] and node["evidence_kind"] == "paper_command_receipt_correction"
                and node["digest"] == "sha256:" + receipt_hash
                and body["prior_native_receipt_sha256"] == digest(completion),
                "Corrected receipt must match appended evidence, preserving original completion")
        corrected_validation = validation_evidence(connection, task, evidence, node["digest"])
        details = body["validation_event"]["details"]
        require(details["result_id"] == corrected_validation["result"]["result_id"]
                and details["body"] == corrected_validation["result"]["body"]
                and details["body"]["receipt_sha256"] == receipt_hash
                and details["body"]["acceptance_criteria"] == receipt["criteria"]
                and details["argv"] == argv, "Appended corrected validation/acceptance binding differs")
        log = Path(details["body"]["validation_log"])
        require(log.is_relative_to(Path(__file__).parent) and sha(log) == details["body"]["validation_log_sha256"],
                "Reviewed correction validation log changed")
        require(subprocess.run(["git", "-C", str(repo), "merge-base", "--is-ancestor", body["source_commit"], head],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0,
                "Current source is not descended from reviewed correction")
        correction = {"node": node, "validation": corrected_validation}
    return {"task_cid": task["task_cid"], "task_alias": alias, "revision": task["revision"],
            "task_sha256": digest(task), "receipt_path": relative, "receipt_sha256": receipt_hash,
            "committed_artifact_hashes": receipt["artifacts"], "acceptance_criteria": receipt["criteria"],
            "completion_receipt": completion, "original_validation": original,
            "corrected_evidence": correction, "historical_evidence_sha256": digest(evidence),
            "evidence_policy": "immutable completed-task proof plus fresh current validators; historical age cutoff disabled"}


def fresh_task_validation(repo, paper, alias, report_path):
    argv = ["python3", "scripts/paper_supervisors.py", "verify-task", "--paper", paper, "--task", alias]
    log = report_path.with_name(report_path.stem + "-" + alias + ".verify-task.log")
    started = C.now()
    with log.open("x") as handle:
        completed = subprocess.run(argv, cwd=repo, env=C.environment(repo), stdin=subprocess.DEVNULL,
                                   stdout=handle, stderr=subprocess.STDOUT, timeout=120)
    record = {"argv": argv, "started_at": started, "finished_at": C.now(), "returncode": completed.returncode,
              "log": str(log), "log_sha256": sha(log)}
    require(completed.returncode == 0, alias + " current verify-task failed; inspect " + str(log))
    output = json.loads(log.read_text())
    require(output["task"] == alias and output.get("artifact_integrity_valid") is True
            and output.get("current_outputs_checked") is True, "Current validator omitted a required gate")
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--paper", choices=tuple(TARGETS), required=True)
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--report", type=Path, required=True)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    require(re.fullmatch(r"[0-9a-f]{40}", args.expected_head), "Expected a full source commit SHA")
    report_path = args.report.resolve()
    require(not report_path.exists(), "Report exists; inspect before any rerun")
    require(report_path.parent == Path(__file__).parent, "Report must be in root runtime_bootstrap")
    target = TARGETS[args.paper]
    repo = ROOT / ".worktrees" / f"vericodegen-{args.paper}-2026"
    report = {"schema": "paper-source-subgoal-completion/v1", "paper": args.paper, "goal": target["goal"],
              "started_at": C.now(), "apply": args.apply, "success": False, "goal_mutations": 0,
              "task_mutations": 0, "provider_invoked": False, "source_commit": args.expected_head,
              "helper_sha256": sha(__file__), "current_task_validations": {}}
    C.write(report_path, report)
    try:
        tree = checked_tree(repo, args.paper, args.expected_head)
        report["source_tree"] = tree
        audit_path = Path(__file__).with_name(target["audit"])
        require(sha(audit_path) == target["audit_sha256"], "Reviewed native completion audit changed")
        audit = C.read(audit_path)
        require(audit["success"] and audit["paper"] == args.paper, "Reviewed completion audit failed")
        baseline = {t["task_alias"]: t["task_cid"] for t in audit["final_tasks"]}
        manifest_bytes, manifest_sha = committed_file(repo, args.expected_head, f"papers/completion/{args.paper}/tasks.json")
        seeds = {t["id"]: t for t in json.loads(manifest_bytes)["tasks"]}
        require(len(seeds) == len(baseline) == 25, "Expected exactly 25 reviewed native tasks")
        report.update(completion_audit={"path": str(audit_path), "sha256": target["audit_sha256"]},
                      committed_manifest_sha256=manifest_sha)
        _, _, cid, Source, _ = M._native(repo)
        from ipfs_accelerate_py.agent_supervisor.task_sources.duckdb_state import open_quack_transport_connection
        from ipfs_accelerate_py.agent_supervisor.objectives.objective_graph import ObjectiveGoal
        with authenticated_owner(args.paper, repo) as (endpoint, ready):
            connection = open_quack_transport_connection(endpoint)
            try:
                report["owner_identity"] = checked_owner(connection, args.paper, ready)
                with Source(endpoint, install_schema=False, owner_id="paper-source-subgoal-rollup:" + args.paper,
                            evidence_freshness_seconds=0) as source:
                    goal, members, topology = population(source, connection, target, seeds, baseline)
                    require(goal["status"] == "open", "Target goal is not open; inspect its existing completion")
                    require(not {"completion_validation", "completion_task_evidence"} & goal["body"].keys(),
                            "Goal already has completion metadata")
                    fields = goal["body"]["native_fields"]
                    command = ["python3", "scripts/paper_supervisors.py", "verify-goal", "--paper", args.paper,
                               "--goal", target["goal"]]
                    require(shlex.split(fields["validation"]) == command, "Declared goal validator differs")
                    evidence = {alias: member_evidence(source, connection, repo, args.expected_head, args.paper,
                                alias, members[alias], seeds[alias], target, audit) for alias in target["members"]}
                    report.update(original_goal=goal, membership=topology, member_evidence=evidence)
                    C.write(report_path, report)
                    for alias in target["members"]:
                        report["current_task_validations"][alias] = fresh_task_validation(repo, args.paper, alias, report_path)
                        C.write(report_path, report)
                    checked_tree(repo, args.paper, args.expected_head)
                    # Native goal validation does not need owner credentials.
                    from ipfs_accelerate_py.agent_supervisor.objectives.objective_tracker import run_goal_validation
                    token = os.environ.pop(TOKEN_ENV)
                    try:
                        validation = run_goal_validation(repo_root=repo,
                            goal=ObjectiveGoal(goal["goal_alias"], goal["title"], dict(fields)), timeout_seconds=120)
                    finally:
                        os.environ[TOKEN_ENV] = token
                    report["goal_validation"] = validation
                    C.write(report_path, report)
                    require(validation.get("attempted") is True and validation.get("passed") is True
                            and validation.get("returncode") == 0 and validation["tree_id"] == tree
                            and validation["goal_id"] == goal["goal_alias"]
                            and validation["receipt_cid"] == cid({k: v for k, v in validation.items() if k != "receipt_cid"}),
                            "Native tree-bound goal validation failed")
                    checked_tree(repo, args.paper, args.expected_head)
                    checked_owner(connection, args.paper, ready)
                    before_goal, before_members, before_topology = population(source, connection, target, seeds, baseline)
                    require((before_goal, before_members, before_topology) == (goal, members, topology),
                            "Goal, member revisions, or membership changed before goal CAS")
                    final_evidence = {alias: member_evidence(source, connection, repo, args.expected_head, args.paper,
                                      alias, before_members[alias], seeds[alias], target, audit) for alias in target["members"]}
                    require(final_evidence == evidence, "Native completion evidence changed during validation")
                    body = {**goal["body"], "completion_validation": validation,
                            "completion_task_evidence": {"schema": "paper-source-subgoal-member-evidence/v1",
                                "source_commit": args.expected_head, "source_tree": tree,
                                "members": evidence, "current_task_validations": report["current_task_validations"],
                                "membership_sha256": digest(topology), "report": str(report_path),
                                "scope": "source/audit checkpoints only; paper and later research tasks remain open"}}
                    report.update(stage="all_gates_passed", proposed_goal_body=body)
                    C.write(report_path, report)
                    checked_tree(repo, args.paper, args.expected_head)
                    if args.apply:
                        event = source.intent.upsert_goal(**{k: goal[k] for k in
                            ("goal_cid", "goal_alias", "title", "objective_id", "parent_goal_cid", "ordinal")},
                            status="completed", expected_revision=goal["revision"], body=body)
                        report.update(goal_mutations=1, goal_event=plain(event.to_dict()), stage="goal_cas_returned")
                        C.write(report_path, report)
                    after_goal, after_members, after_topology = population(source, connection, target, seeds, baseline)
                    require(after_members == members and after_topology == topology, "Membership/member revisions changed after goal operation")
                    expected = {**goal, "status": "completed", "revision": goal["revision"] + 1, "body": body} if args.apply else goal
                    require({k: v for k, v in after_goal.items() if k != "updated_at"} ==
                            {k: v for k, v in expected.items() if k != "updated_at"}, "Goal CAS readback differs")
                    checked_tree(repo, args.paper, args.expected_head)
                    checked_owner(connection, args.paper, ready)
                    report.update(final_goal=after_goal, success=True,
                                  stage="goal_completed" if args.apply else "dry_run_passed")
            finally:
                connection.close()
    except Exception as exc:
        report.update(error_type=type(exc).__name__, error=str(exc))
        raise
    finally:
        report["finished_at"] = C.now()
        C.write(report_path, report)
    print(json.dumps({k: report[k] for k in ("paper", "goal", "stage", "success", "goal_mutations", "task_mutations")}))


if __name__ == "__main__":
    main()
