#!/usr/bin/env python3
"""Import one reviewed paper board into a new, offline authoritative DuckDB.

No server/provider is started. Existing databases are never overwritten.
Markdown and tasks.json become source provenance; runtime mutations belong to DB.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
RESEARCH_PAPERS = ("autoformalization", "law_to_action", "neurosymbolic_supervision")
COMPETITION_PAPERS = ("lean_refactor_arena",)
PAPERS = RESEARCH_PAPERS + COMPETITION_PAPERS
PREFIXES = {
    "autoformalization": "AF",
    "law_to_action": "LA",
    "neurosymbolic_supervision": "NS",
    "lean_refactor_arena": "LRA",
}


def _native(repo_root):
    os.environ.setdefault("IPFS_ACCEL_SKIP_CORE", "1")
    os.environ.setdefault("IPFS_AUTO_INSTALL", "false")
    os.environ.setdefault("IPFS_DATASETS_AUTO_INSTALL", "false")
    for relative in reversed(("external/ipfs_accelerate", "external/ipfs_datasets", "external/ipfs_kit")):
        sys.path.insert(0, str(repo_root / relative))
    from ipfs_accelerate_py.agent_supervisor.objectives.objective_graph import parse_goal_heap
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import parse_task_file
    from ipfs_accelerate_py.agent_supervisor.task_sources.task_identity import canonical_content_cid
    from ipfs_accelerate_py.agent_supervisor.task_sources.database_task_source import DatabaseTaskSource
    from ipfs_accelerate_py.agent_supervisor.task_sources.control_plane_schema import verify_installed_schema
    return parse_goal_heap, parse_task_file, canonical_content_cid, DatabaseTaskSource, verify_installed_schema


def _json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _digest(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def _path(repo_root, relative):
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"invalid repository-relative source/output path: {relative}")
    result = (repo_root / path).resolve()
    if not result.is_relative_to(repo_root):
        raise ValueError(f"source/output path escapes repository: {relative}")
    return result


def _topological(graph):
    visited, active, ordered = set(), set(), []
    def visit(key):
        if key not in graph:
            raise ValueError(f"unknown dependency or parent: {key}")
        if key in active:
            raise ValueError(f"dependency cycle at {key}")
        if key in visited:
            return
        active.add(key)
        for dependency in graph[key]:
            visit(dependency)
        active.remove(key)
        visited.add(key)
        ordered.append(key)
    for key in graph:
        visit(key)
    return ordered


def _validation_argv(command, paper, task_id):
    """Keep the reviewed verifier as literal argv through the native bridge.

    Wrapping this command in a nested shell changes its native safety policy
    and blocks provider dispatch. This importer accepts only the verifier
    bound to this exact paper/task; arbitrary shell programs need a separately
    reviewed execution contract.
    """
    expected = ["python3", "scripts/paper_supervisors.py", "verify-task",
                "--paper", paper, "--task", task_id]
    try:
        actual = shlex.split(command)
    except ValueError as exc:
        raise ValueError(f"task {task_id} has malformed validation argv") from exc
    if actual != expected:
        raise ValueError(f"task {task_id} validation must be its direct reviewed paper verifier")
    return actual


def _task_outputs(paper, task_id, outputs, repo_root):
    """Admit one task-specific evidence directory, never a receipt subtree."""
    if paper not in PREFIXES or not isinstance(task_id, str) or not re.fullmatch(re.escape(PREFIXES[paper]) + r"-[0-9]{3,}", task_id):
        raise ValueError(f"invalid paper/task evidence identity: {paper}/{task_id}")
    receipt = f"papers/completion/{paper}/receipts/{task_id}.json"
    snapshots = f"papers/completion/{paper}/receipts/snapshots/{task_id}/"
    admitted = []
    receipt_roots = [Path(f"papers/completion/{name}/receipts") for name in PAPERS]
    for output in [*outputs, receipt, snapshots]:
        if not isinstance(output, str) or not output.strip() or output != output.strip():
            raise ValueError("invalid empty or non-string native output path")
        resolved = _path(repo_root, output)
        path = Path(output)
        if str(path) != output.removesuffix("/") or any(char in output for char in "*?[]\\,\r\n\x00"):
            raise ValueError(f"native output path must be canonical and literal: {output}")
        if output in {receipt, snapshots} and resolved != repo_root / path:
            raise ValueError(f"task evidence path must not redirect through symlinks: {output}")
        if output not in {receipt, snapshots} and any(
                path == root or path.is_relative_to(root) or root.is_relative_to(path)
                for root in receipt_roots):
            raise ValueError(f"native output grants foreign or broad receipt evidence scope: {output}")
        if output not in admitted:
            admitted.append(output)
    return admitted


def build_population(paper, repo_root=ROOT):
    repo_root = Path(repo_root).resolve()
    if paper not in PAPERS:
        raise ValueError("unknown paper")
    parse_goals, parse_tasks, cid, _, _ = _native(repo_root)
    folder = Path("papers/completion") / paper
    manifest_path, config_path = folder / "tasks.json", folder / "supervisor.json"
    manifest, config = _json(repo_root / manifest_path), _json(repo_root / config_path)
    todo_path = _path(repo_root, config["todo_path"])
    objective_path = _path(repo_root, config["objective_path"])
    tasks = parse_tasks(todo_path, config["task_prefix"])
    goals = parse_goals(objective_path.read_text())
    by_task, by_goal = {t.task_id: t for t in tasks}, {g.goal_id: g for g in goals}
    seeds = {t["id"]: t for t in manifest["tasks"]}
    if len(by_task) != len(tasks) or len(by_goal) != len(goals):
        raise ValueError("duplicate native IDs")
    if not seeds.keys() <= by_task.keys() or config["root_goal_id"] not in by_goal:
        raise ValueError("native board is missing reviewed tasks or root goal")
    parents = {g.goal_id: [v.strip() for v in g.fields.get("parent", "").split(",") if v.strip()]
               for g in goals}
    if any(len(v) > 1 for v in parents.values()):
        raise ValueError("goal has multiple parents; explicit reconciliation is required")
    goal_order = _topological(parents)
    dependencies = {t.task_id: list(t.depends_on) for t in tasks}
    task_order = _topological(dependencies)
    source_paths = [manifest_path, config_path, Path(config["todo_path"]), Path(config["objective_path"]),
                    Path(config["pdf"]), Path(config["review_path"])]
    source_digests = {str(p): _digest(_path(repo_root, p)) for p in source_paths}
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo_root, text=True).strip()
    tree = subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"], cwd=repo_root, text=True).strip()
    source_root = cid({"schema": "paper-reviewed-sources/v1", "paper": paper, "files": source_digests})
    objective_id = cid({"schema": "paper-objective/v1", "paper": paper, "goal": manifest["goal"], "source_root": source_root})
    goal_cids = {g.goal_id: cid({"schema": "paper-goal/v1", "source_root": source_root,
                               "goal_alias": g.goal_id, "title": g.title, "fields": g.fields}) for g in goals}
    task_cids = {t.task_id: cid({"schema": "paper-task/v1", "source_root": source_root,
                               "task_alias": t.task_id, "title": t.title, "metadata": t.metadata,
                               "reviewed_task": seeds.get(t.task_id)}) for t in tasks}
    plan_cids = {g: cid({"schema": "paper-plan/v1", "source_root": source_root,
                         "goal_cid": goal_cids[g], "task_cids": [task_cids[t.task_id] for t in tasks
                                                                   if t.metadata.get("goal id") == g]})
                 for g in goal_order}
    population_goals, population_tasks = [], []
    for ordinal, alias in enumerate(goal_order, 1):
        goal = by_goal[alias]
        if goal.status not in {"open", "active", "todo", "proposed", "ready"}:
            raise ValueError(f"goal {alias} needs explicit status migration rather than fresh bootstrap")
        population_goals.append({"goal_cid": goal_cids[alias], "goal_alias": alias,
                                 "title": goal.title, "objective_id": objective_id,
                                 "objective_alias": config["root_goal_id"],
                                 "parent_goal_cid": goal_cids[parents[alias][0]] if parents[alias] else "",
                                 "status": "open", "ordinal": ordinal,
                                 "native_fields": dict(goal.fields), "source_root": source_root})
    text = todo_path.read_text()
    headings = list(re.finditer(r"(?m)^##\s+(\S+)[^\n]*$", text))
    blocks = {match.group(1): text[match.start():headings[i + 1].start() if i + 1 < len(headings) else len(text)]
              for i, match in enumerate(headings)}
    for ordinal, alias in enumerate(task_order, 1):
        task, seed = by_task[alias], seeds.get(alias)
        goal_alias = task.metadata.get("goal id", "")
        if goal_alias not in goal_cids or task.board_namespace != config["board_namespace"]:
            raise ValueError(f"task {alias} has foreign goal or board namespace")
        if seed and seed["subgoal_id"] != goal_alias:
            raise ValueError(f"task {alias} changed its reviewed goal")
        if task.status not in {"todo", "ready", "needed", "blocked"}:
            raise ValueError(f"task {alias} needs evidence-aware status migration rather than fresh bootstrap")
        if not task.validation or not task.outputs or not task.acceptance:
            raise ValueError(f"task {alias} lacks executable output/validation/acceptance contract")
        outputs = _task_outputs(paper, alias, task.outputs, repo_root)
        criteria = seed["acceptance_criteria"] if seed else [task.acceptance]
        # Flatten native metadata: the database Portal bridge re-renders body
        # keys, so nesting it under metadata would lose Goal id / scope fields.
        record = {**dict(task.metadata),
                  "task_cid": task_cids[alias], "task_id": alias, "title": task.title,
                  "goal_cid": goal_cids[goal_alias], "plan_cid": plan_cids[goal_alias],
                  "objective_id": objective_id, "ordinal": ordinal,
                  "status": "blocked" if task.status == "blocked" else "ready",
                  "priority": task.priority, "track": task.track, "completion": task.completion,
                  "board_namespace": task.board_namespace,
                  "depends_on": [task_cids[d] for d in task.depends_on],
                  "outputs": [{"path": output, "kind": "directory" if output.endswith("/") else "file"}
                              for output in outputs],
                  "acceptance_criteria": criteria,
                  "validation_commands": [{"argv": _validation_argv(command, paper, alias), "source_command": command}
                                          for command in task.validation],
                  "description": seed["description"] if seed else blocks.get(alias, ""),
                  "native_source_block": blocks.get(alias, ""), "source_root": source_root}
        population_tasks.append(record)
    population = {"schema": "paper-database-population/v1", "paper_id": paper,
                  "repository_tree_id": "git-tree:" + tree,
                  "plan_root_cid": plan_cids[config["root_goal_id"]],
                  "objective_contract": {"objective_id": objective_id, "objective_alias": config["root_goal_id"],
                                         "title": manifest["title"], "status": "open", "priority": "P0",
                                         "body": {"goal": manifest["goal"], "source_root": source_root}},
                  "objectives": population_goals,
                  "plans": [{"plan_cid": plan_cids[g], "plan_alias": paper + "/" + g,
                             "goal_cid": goal_cids[g], "status": "active", "source_root": source_root}
                            for g in goal_order],
                  "taskboard": population_tasks,
                  "goal_edges": [{"parent_goal_cid": goal_cids[parent], "child_goal_cid": goal_cids[child],
                                  "edge_kind": "subgoal"} for child, values in parents.items() for parent in values]}
    provenance = {"source_head": head, "source_tree": tree, "source_root_cid": source_root,
                  "source_sha256": source_digests, "objective_id": objective_id,
                  "goal_cids": goal_cids, "task_cids": task_cids,
                  "plan_cids": plan_cids, "population_cid": cid(population)}
    return population, provenance


def materialize(paper, database, repo_root=ROOT):
    repo_root, database = Path(repo_root).resolve(), Path(database).expanduser().absolute()
    receipt_path = database.with_name(database.name + ".bootstrap.json")
    if database.exists() or database.is_symlink() or receipt_path.exists():
        raise ValueError("refusing to overwrite an existing database or bootstrap receipt")
    if any(database.with_name(database.name + suffix).exists() for suffix in (".wal", ".tmp")):
        raise ValueError("database has preexisting recovery sidecars")
    population, provenance = build_population(paper, repo_root)
    _, _, _, DatabaseTaskSource, verify_schema = _native(repo_root)
    database.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".paper-bootstrap-", dir=database.parent) as temporary:
        staging = Path(temporary) / "control.duckdb"
        # Prevent ambient fleet discovery/environment bindings from redirecting
        # this offline bootstrap to a currently running owner.
        isolated_names = ("IPFS_ACCELERATE_AGENT_QUACK_ENDPOINT", "IPFS_ACCELERATE_AGENT_STATE_STORE_ID",
                          "IPFS_ACCELERATE_AGENT_QUACK_TOKEN", "IPFS_ACCELERATE_AGENT_QUACK_MUTATION_DIR",
                          "IPFS_ACCELERATE_AGENT_QUACK_REQUIRE")
        saved = {name: os.environ.pop(name) for name in isolated_names if name in os.environ}
        prior_prefer = os.environ.get("IPFS_ACCELERATE_AGENT_QUACK_PREFER")
        os.environ["IPFS_ACCELERATE_AGENT_QUACK_PREFER"] = "false"
        try:
            with DatabaseTaskSource(staging, owner_id="paper-bootstrap:" + paper) as source:
                imported = dict(source.materialize(population))
                source.intent.upsert_objective(**population["objective_contract"])
                records = source.list_tasks(limit=1000).tasks
                if len(records) != len(population["taskboard"]):
                    raise ValueError("task count changed during database import")
                expected = {t["task_cid"]: t for t in population["taskboard"]}
                for record in records:
                    planned = expected[record.task_cid]
                    if set(record.dependencies) != set(planned["depends_on"]):
                        raise ValueError(f"dependency projection mismatch: {record.task_alias}")
                    if [(o["path"], o["effect"].get("kind")) for o in record.outputs] != [(o["path"], o["kind"]) for o in planned["outputs"]]:
                        raise ValueError(f"output projection mismatch: {record.task_alias}")
                    if record.body.get("goal id") != planned["goal id"]:
                        raise ValueError(f"native goal metadata was lost: {record.task_alias}")
                    if [c["criterion"] for c in record.acceptance] != planned["acceptance_criteria"]:
                        raise ValueError(f"acceptance projection mismatch: {record.task_alias}")
                    if [list(v["argv"]) for v in record.validations] != [v["argv"] for v in planned["validation_commands"]]:
                        raise ValueError(f"validation argv projection mismatch: {record.task_alias}")
                for goal in population["objectives"]:
                    observed = source.get_goal(goal["goal_cid"])
                    if observed["parent_goal_cid"] != goal["parent_goal_cid"]:
                        raise ValueError("goal parent projection mismatch")
                ready = [t.task_alias for t in source.ready_tasks(limit=1000).tasks]
                expected_ready = [t["task_id"] for t in population["taskboard"]
                                  if not t["depends_on"] and t["status"] == "ready"]
                if set(ready) != set(expected_ready):
                    raise ValueError("database readiness differs from imported dependency DAG")
                snapshot = source.snapshot().to_dict()
                imported["projection_cid"] = snapshot["projection_cid"]
                imported["event_watermark"] = snapshot["event_cursor"]
            schema = verify_schema(staging)
        finally:
            for name in isolated_names:
                os.environ.pop(name, None)
            os.environ.update(saved)
            if prior_prefer is None:
                os.environ.pop("IPFS_ACCELERATE_AGENT_QUACK_PREFER", None)
            else:
                os.environ["IPFS_ACCELERATE_AGENT_QUACK_PREFER"] = prior_prefer
        report = {"schema": "paper-database-bootstrap/v1", "paper_id": paper,
                  "database": str(database), "authoritative_task_source": "DatabaseTaskSource@1",
                  "population": imported, "source_provenance": provenance,
                  "ready_tasks": ready, "task_snapshot": snapshot,
                  "schema_revision": schema["schema_revision"], "schema_fingerprint": schema["schema_fingerprint"],
                  "bootstrap_database_sha256": _digest(staging),
                  "server_started": False, "provider_started": False}
        staged_receipt = Path(temporary) / "bootstrap.json"
        staged_receipt.write_text(json.dumps(report, indent=2) + "\n")
        for artifact in (staging, staged_receipt):
            artifact.chmod(0o600)
            with artifact.open("rb") as handle:
                os.fsync(handle.fileno())
        # link() is atomic and fails if a competing bootstrap created the name;
        # unlike replace(), it can never overwrite a live existing store.
        # Publish provenance first, then the usable store. If another bootstrap
        # wins the database name, remove only our receipt, never its database.
        os.link(staged_receipt, receipt_path)
        try:
            os.link(staging, database)
        except BaseException:
            if receipt_path.stat().st_ino == staged_receipt.stat().st_ino:
                receipt_path.unlink()
            raise
        directory_fd = os.open(database.parent, os.O_DIRECTORY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--paper", choices=PAPERS, required=True)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    args = parser.parse_args()
    print(json.dumps(materialize(args.paper, args.database, args.repo_root), indent=2))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, RuntimeError) as exc:
        print(f"paper database bootstrap: {exc}", file=sys.stderr)
        raise SystemExit(1)
