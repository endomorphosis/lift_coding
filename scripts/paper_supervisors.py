#!/usr/bin/env python3
"""Build, inspect, and run the three paper boards with ipfs_accelerate_py.

The default command is validation; live provider work requires the run command.
Markdown and tasks.json are reviewed import sources. Live scheduling uses the
Quack database campaign in paper_supervisor_campaign.py.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
BASE = Path("papers/completion")
RESEARCH_PAPERS = ("autoformalization", "law_to_action", "neurosymbolic_supervision")
COMPETITION_PAPERS = ("lean_refactor_arena",)
PAPERS = RESEARCH_PAPERS + COMPETITION_PAPERS
PREFIXES = {
    "autoformalization": "AF",
    "law_to_action": "LA",
    "neurosymbolic_supervision": "NS",
    "lean_refactor_arena": "LRA",
}
ACCEL = ROOT / "external/ipfs_accelerate"
SUBMODULES = ("external/ipfs_accelerate", "external/ipfs_datasets", "external/ipfs_kit")
TEMPLATES = ("papers/neurips_2026_vericode_workshop.tex", "papers/neurips_2026_vericode.sty", "papers/checklist.tex")
RECEIPT_CLOCK_TOLERANCE_SECONDS = 60


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def relative_file(value: str) -> Path:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"expected repository-relative path: {value}")
    resolved = (ROOT / path).resolve()
    if not resolved.is_relative_to(ROOT):
        raise ValueError(f"path escapes repository: {value}")
    return resolved


def manifest(paper: str):
    return read_json(ROOT / BASE / paper / "tasks.json")


def config(paper: str):
    return read_json(ROOT / BASE / paper / "supervisor.json")


def native_modules():
    # Use the canonical checkout; avoid the stale nested copy under hallucinate_app.
    os.environ.setdefault("IPFS_ACCEL_SKIP_CORE", "1")
    os.environ.setdefault("IPFS_AUTO_INSTALL", "false")
    os.environ.setdefault("IPFS_DATASETS_AUTO_INSTALL", "false")
    if str(ACCEL) not in sys.path:
        sys.path.insert(0, str(ACCEL))
    from ipfs_accelerate_py.agent_supervisor.objectives.objective_graph import parse_goal_heap
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import parse_task_file
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_supervisor import (
        parse_args, supervisor_config_from_args,
    )
    return parse_goal_heap, parse_task_file, parse_args, supervisor_config_from_args


def task_evidence_paths(paper: str, task_id: str):
    """Return only this task's receipt and immutable evidence directory."""
    if paper not in PREFIXES or not isinstance(task_id, str) or not re.fullmatch(re.escape(PREFIXES[paper]) + r"-[0-9]{3,}", task_id):
        raise ValueError(f"invalid paper/task evidence identity: {paper}/{task_id}")
    receipt = str(BASE / paper / "receipts" / f"{task_id}.json")
    snapshots = str(BASE / paper / "receipts" / "snapshots" / task_id) + "/"
    for path in (receipt, snapshots):
        if relative_file(path) != ROOT / path:
            raise ValueError(f"task evidence path must not redirect through symlinks: {path}")
    return receipt, snapshots


def build(paper: str):
    data = manifest(paper)
    folder = BASE / paper
    prefix = PREFIXES[paper]
    root_goal = f"{prefix}-G000"
    paths = {name: str(folder / filename) for name, filename in (
        ("todo_path", "paper.todo.md"), ("objective_path", "paper.objectives.md"),
        ("review_path", "review.md"), ("manifest_path", "tasks.json"),
    )}
    for name in ("todo_path", "objective_path"):
        existing = ROOT / paths[name]
        if existing.exists():
            raise ValueError(f"refusing to overwrite runtime board {existing}; edit the board directly")
    cfg = {
        "schema": "vericodegen-paper-supervisor/v1", "paper_id": paper,
        "title": data["title"], "pdf": data["pdf"], **paths,
        "research_template_paths": list(TEMPLATES),
        "source_project": "https://www.overleaf.com/project/6a7b4742e20ac910c422a7e0",
        "source_project_access": "HTTP 403 on 2026-09-11; paper membership unverified",
        "task_prefix": f"{prefix}-", "root_goal_id": root_goal,
        "board_namespace": f"vericodegen-2026-{paper}",
        "state_prefix": f"paper_{paper}", "submodule_paths": list(SUBMODULES),
        "implementation_timeout_seconds": 7200, "max_task_attempts": 3,
        "runtime_authority": "native DatabaseTaskSource through dedicated Quack owner; fail closed",
        "refill_policy": "fixed reviewed board; split/discover follow-ups explicitly with lineage",
    }
    write_json(ROOT / folder / "supervisor.json", cfg)
    goals = [{"id": root_goal, "title": "Complete the evidence-backed workshop paper",
              "description": data["goal"]}, *data["subgoals"]]
    lines = [f"# {data['title']} — objective heap", "",
             f"Reviewed scope: `{paths['review_path']}`. Executable board: `{paths['todo_path']}`.", "",
             "A completed paper means a reproducible, anonymous submission candidate with supported claims.",
             "It does not mean OpenReview submission, acceptance, or completion of unrun experiments.", ""]
    for n, goal in enumerate(goals):
        tasks = data["tasks"] if n == 0 else [t for t in data["tasks"] if t["subgoal_id"] == goal["id"]]
        outputs = list(dict.fromkeys(p for t in tasks for p in t["deliverables"]))
        lines.extend([
            f"## {goal['id']} {goal['title']}", "", "- Status: active",
            f"- Parent: {root_goal if n else ''}", "- Depends on:",
            f"- Fib priority: {min(n + 1, 13)}", "- Priority: P0",
            f"- Track: {paper}", f"- Bundle: {paper}/{goal['id']}",
            f"- Goal: {goal['description']}", f"- Outputs: {', '.join(outputs)}",
            f"- Gap task: {', '.join(t['id'] for t in tasks)}",
            "- Acceptance: All linked task criteria have current artifact and validation evidence; numerical claims trace to real runs; author handoff is explicit.",
            f"- Validation: python3 scripts/paper_supervisors.py verify-goal --paper {paper} --goal {goal['id']}",
            "",
        ])
    (ROOT / paths["objective_path"]).write_text("\n".join(lines), encoding="utf-8")
    lines = [f"# {data['title']} — implementation taskboard", "",
             f"Read `{paths['review_path']}` and `papers/completion/README.md` before work.",
             f"Objective heap: `{paths['objective_path']}`. Board namespace: `{cfg['board_namespace']}`.", "",
             "All tasks start open. P0 is submission-critical, P1 supports the full study, P2 is optional extension.",
             "Dependencies still apply across priority levels. A blocked experiment remains blocked until run or explicitly rescoped with a recorded claim change.",
             "Never turn estimates, mocks, dry runs, or missing values into measured results.",
             "Implement in native ephemeral worktrees. Coordinate shared library changes through the supervisor merge queue.",
             "Each task must write its receipt using the contract in the runbook; this is provenance validation, not scientific peer review.", ""]
    for task in data["tasks"]:
        receipt, snapshots = task_evidence_paths(paper, task["id"])
        outputs = list(dict.fromkeys([*task["deliverables"], receipt, snapshots]))
        lines.extend([
            f"## {task['id']} {task['title']}", "", "- Status: todo", "- Completion: auto",
            "- Is schedulable: true", "- Review only: false", f"- Priority: {task['priority']}",
            f"- Track: {paper}", f"- Depends on: {', '.join(task['depends_on'])}",
            f"- Goal id: {task['subgoal_id']}", f"- Parent goal: {root_goal}",
            f"- Objective heap: {paths['objective_path']}",
            f"- Board namespace: {cfg['board_namespace']}",
            f"- Bundle: {paper}/{task['subgoal_id']}", f"- Parallel lane: {paper}",
            f"- Outputs: {', '.join(outputs)}",
            f"- Predicted files: {', '.join(outputs)}",
            f"- Allowed paths: {', '.join(task.get('implementation_paths', []))}",
            "- Resource class: cpu-medium", "- Resource stage: execution",
            "- Implementation timeout seconds: 7200",
            f"- Validation: python3 scripts/paper_supervisors.py verify-task --paper {paper} --task {task['id']}",
            f"- Acceptance: {'; '.join(task['acceptance_criteria'])}",
            f"- Paper evidence: {'; '.join(task['paper_evidence'])}",
            f"- Reuse candidates: {', '.join(task['suggested_code_paths'])}",
            f"- Receipt: {receipt}", "", task["description"], "", "Acceptance criteria:", "",
            *[f"{i}. {criterion}" for i, criterion in enumerate(task["acceptance_criteria"], 1)], "",
            "Record dependencies, exact code/data/model/tool versions, actual command logs, failures and claim limitations in the receipt. Expand this task into bounded follow-ups when discovery requires it; preserve its goal and evidence obligations.", "",
        ])
    (ROOT / paths["todo_path"]).write_text("\n".join(lines), encoding="utf-8")


def state_root() -> Path:
    override = os.environ.get("VERICODEGEN_STATE_ROOT")
    if override:
        return Path(override).expanduser().resolve()
    return (Path(os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local/state")))
            / "ipfs_accelerate_py/vericodegen-2026").resolve()


def supervisor_argv(paper: str) -> list[str]:
    """Validate the actual database command with a non-routable sample identity.

    Live identities are supplied exclusively by the campaign owner's verified
    readiness. This helper never launches a process or resolves credentials.
    """
    sys.path.insert(0, str(ROOT / "scripts"))
    from paper_supervisor_campaign import native_argv
    ready = {"quack_endpoint": "quack:127.0.0.1:1",
             "endpoint_secret_handle": "handle:validation-only:" + paper,
             "store_id": "vericodegen-2026-" + paper,
             "store_generation": "1", "schema_revision": "1"}
    return native_argv(ROOT, paper, state_root() / paper, ready)[4:]


def check_dag(graph: dict[str, list[str]]):
    seen, active = set(), set()

    def visit(node):
        if node not in graph:
            raise ValueError(f"unknown dependency {node}")
        if node in active:
            raise ValueError(f"dependency cycle at {node}")
        if node in seen:
            return
        active.add(node)
        for dep in graph[node]:
            visit(dep)
        active.remove(node)
        seen.add(node)

    for node in graph:
        visit(node)


def validate(paper: str):
    parse_goals, parse_tasks, parse_args, make_config = native_modules()
    cfg, data = config(paper), manifest(paper)
    goals = parse_goals(relative_file(cfg["objective_path"]).read_text())
    tasks = parse_tasks(relative_file(cfg["todo_path"]), cfg["task_prefix"])
    goal_ids, task_ids = [g.goal_id for g in goals], [t.task_id for t in tasks]
    if len(set(goal_ids)) != len(goal_ids) or len(set(task_ids)) != len(task_ids):
        raise ValueError(f"duplicate goal or task IDs in {paper}")
    required_tasks = {t["id"] for t in data["tasks"]}
    if not required_tasks.issubset(task_ids):
        raise ValueError(f"missing reviewed tasks in {paper}")
    expected_goals = {cfg["root_goal_id"], *(g["id"] for g in data["subgoals"])}
    if not expected_goals.issubset(goal_ids):
        raise ValueError(f"missing reviewed goals in {paper}")
    check_dag({t.task_id: t.depends_on for t in tasks})
    check_dag({g.goal_id: [v.strip() for v in g.fields.get("parent", "").split(",") if v.strip()] for g in goals})
    for task in tasks:
        if task.metadata.get("goal id") not in goal_ids:
            raise ValueError(f"orphan task: {task.task_id}")
        if not task.validation or not task.acceptance or not task.outputs:
            raise ValueError(f"incomplete execution contract: {task.task_id}")
        if task.board_namespace != cfg["board_namespace"]:
            raise ValueError(f"wrong namespace: {task.task_id}")
        for path in task.outputs:
            relative_file(path)
        for field in ("predicted files", "allowed paths"):
            for path in task.metadata.get(field, "").split(","):
                if path.strip():
                    relative_file(path.strip())
        seed = next((t for t in data["tasks"] if t["id"] == task.task_id), None)
        if seed and task.acceptance != "; ".join(seed["acceptance_criteria"]):
            raise ValueError(f"reviewed acceptance criteria changed: {task.task_id}")
    parsed = parse_args(supervisor_argv(paper))
    native_cfg = make_config(parsed, repo_root=ROOT)
    if not native_cfg.implement or not native_cfg.use_ephemeral_worktree:
        raise ValueError("live command must use isolated native implementation worktrees")
    if not relative_file(cfg["pdf"]).is_file():
        raise ValueError("missing input PDF")
    for path in cfg["research_template_paths"]:
        if not relative_file(path).is_file():
            raise ValueError(f"missing research template input: {path}")
    completed = {t.task_id for t in tasks if t.status == "completed"}
    return {
        "paper": paper, "goals": len(goals), "subgoals": len(goals) - 1,
        "tasks": len(tasks), "completed": len(completed),
        "ready": [t.task_id for t in tasks if t.status in {"todo", "ready", "needed"}
                  and set(t.depends_on).issubset(completed)],
        "native_parser_and_cli_valid": True, "provider_or_experiment_started": False,
    }


def digest(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def paper_task_contracts(paper: str):
    """Join immutable seed criteria with explicitly added native board tasks."""
    parse_goals, parse_tasks, _, _ = native_modules()
    cfg, data = config(paper), manifest(paper)
    native_goals = parse_goals(relative_file(cfg["objective_path"]).read_text())
    native_tasks = parse_tasks(relative_file(cfg["todo_path"]), cfg["task_prefix"])
    goals = {g.goal_id: [p.strip() for p in g.fields.get("parent", "").split(",") if p.strip()]
             for g in native_goals}
    if len(goals) != len(native_goals) or len({t.task_id for t in native_tasks}) != len(native_tasks):
        raise ValueError("duplicate native task or goal IDs")
    check_dag(goals)
    check_dag({t.task_id: t.depends_on for t in native_tasks})
    if cfg["root_goal_id"] not in goals:
        raise ValueError("missing paper root goal")
    seeds = {t["id"]: t for t in data["tasks"]}
    if not seeds.keys() <= {t.task_id for t in native_tasks}:
        raise ValueError("reviewed tasks disappeared from the runtime board")
    contracts = {}
    for task in native_tasks:
        goal_id = task.metadata.get("goal id")
        if goal_id not in goals or task.board_namespace != cfg["board_namespace"]:
            raise ValueError(f"invalid task goal or namespace: {task.task_id}")
        if task.task_id in seeds:
            contract = dict(seeds[task.task_id])
            if goal_id != contract["subgoal_id"]:
                raise ValueError(f"reviewed task goal changed: {task.task_id}")
        else:
            own_receipt, own_snapshots = task_evidence_paths(paper, task.task_id)
            contract = {
                "id": task.task_id, "subgoal_id": goal_id,
                # Evidence is writable native output, not a scientific output
                # which must itself acquire another recursive evidence copy.
                "deliverables": [v for v in task.outputs if v.rstrip("/") not in
                                 {own_receipt, own_snapshots.rstrip("/")}],
                "acceptance_criteria": [task.acceptance.strip()] if task.acceptance.strip() else [],
            }
        if not contract["deliverables"] or not contract["acceptance_criteria"] or not task.validation:
            raise ValueError(f"incomplete task contract: {task.task_id}")
        contract["depends_on"] = list(task.depends_on)
        contracts[task.task_id] = contract
    return cfg, goals, contracts


def _utc_now():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc)


def _receipt_time(value):
    from datetime import datetime, timedelta
    if not isinstance(value, str):
        raise ValueError("receipt requires completed_at as an aware UTC timestamp")
    try:
        instant = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid receipt completed_at timestamp") from exc
    if instant.tzinfo is None or instant.utcoffset() != timedelta(0):
        raise ValueError("receipt completed_at must have an explicit UTC offset")
    if instant > _utc_now() + timedelta(seconds=RECEIPT_CLOCK_TOLERANCE_SECONDS):
        raise ValueError("receipt completed_at is in the future beyond the 60-second clock tolerance")
    return instant


def _python_source_valid(source, label):
    """Check executable syntax only; never execute receipt-supplied programs."""
    try:
        compile(source, label, "exec")
    except (SyntaxError, ValueError, TypeError) as exc:
        raise ValueError(f"validation command has invalid Python source: {label}") from exc


def _validation_command_source(command, artifacts):
    """Check reproducible source references without claiming execution proof.

    Python stdin requires ``stdin_artifact`` naming a hashed snapshot containing
    the exact stdin bytes. A named script can optionally use ``script_artifact``
    to bind its argv script path to retained source; otherwise its repository
    path must exist. Literal ``-c`` already retains its source in argv.
    """
    argv = command["argv"]
    start = 0
    if Path(argv[0]).name == "env":
        start = 1
        while start < len(argv):
            value = argv[start]
            if value in {"-i", "--ignore-environment", "--"}:
                start += 1
                continue
            if value in {"-u", "--unset"}:
                start += 2
                continue
            if value.startswith("--unset="):
                start += 1
                continue
            if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", value, re.DOTALL):
                assigned = value.split("=", 1)[1].strip()
                if re.fullmatch(r"<(?:fresh|temporary|temp|replace|your|path|actual|placeholder|tbd|todo)(?:[- _][^<>]+)?>|\[(?:tbd|todo|placeholder)\]|(?:tbd|todo|placeholder)", assigned, re.IGNORECASE):
                    raise ValueError("validation command contains a placeholder environment value")
                start += 1
                continue
            break
    if start >= len(argv) or not re.fullmatch(r"python(?:[23](?:\.[0-9]+)?)?", Path(argv[start]).name):
        return
    index, mode, source = start + 1, "stdin", None
    while index < len(argv):
        value = argv[index]
        if value == "-c" or value.startswith("-c") and len(value) > 2:
            if value == "-c":
                if index + 1 >= len(argv):
                    raise ValueError("Python -c validation command has no source")
                source = argv[index + 1]
            else:
                source = value[2:]
            mode = "literal"
            break
        if value == "-m" or value.startswith("-m") and len(value) > 2:
            if value == "-m" and index + 1 >= len(argv):
                raise ValueError("Python -m validation command has no module")
            return  # Named modules are retained by recorded source/runtime versions.
        if value in {"-V", "--version", "-h", "--help", "--help-env", "--help-xoptions", "--help-all"}:
            return
        if value == "-":
            break
        if value == "--":
            index += 1
            if index == len(argv):
                break
            source, mode = argv[index], "script"
            break
        if value in {"-W", "-X", "--check-hash-based-pycs"}:
            index += 2
            continue
        if value.startswith("-"):
            index += 1
            continue
        source, mode = value, "script"
        break
    if mode == "literal":
        _python_source_valid(source, "literal -c payload")
        return
    field = "stdin_artifact" if mode == "stdin" else "script_artifact"
    retained = command.get(field)
    if retained is not None:
        if not isinstance(retained, str) or retained not in artifacts:
            raise ValueError(f"{field} must name a hashed snapshot artifact")
        _python_source_valid(relative_file(retained).read_bytes(), retained)
    elif mode == "stdin":
        raise ValueError("Python stdin validation command requires a hashed stdin_artifact")
    else:
        cwd = command.get("cwd", ".")
        if not isinstance(cwd, str):
            raise ValueError("validation command cwd must be a repository-relative path")
        script = relative_file(str(Path(cwd) / source))
        if not script.is_file():
            raise ValueError("Python script validation command requires retained repository source or script_artifact")
        _python_source_valid(script.read_bytes(), str(script.relative_to(ROOT)))


def _output_belongs_to(output, deliverable):
    return output == deliverable.rstrip("/") or output.startswith(deliverable.rstrip("/") + "/")


def _check_current_outputs(outputs, artifacts):
    for name, snapshot in outputs.items():
        target = relative_file(name)
        if not target.is_file() or digest(target) != artifacts[snapshot]:
            raise ValueError(f"current output differs from its completed snapshot: {name}")


def _check_directory_coverage(deliverables, outputs):
    for output in deliverables:
        target = relative_file(output)
        if target.is_dir():
            files = {str(p.relative_to(ROOT)) for p in target.rglob("*") if p.is_file()}
            if not files or not files <= outputs.keys():
                raise ValueError(f"directory contains unaccounted output files: {output}")


def _verify_task_contract(paper: str, task, *, check_current: bool):
    task_id = task["id"]
    path = ROOT / BASE / paper / "receipts" / f"{task_id}.json"
    receipt = read_json(path)
    if not isinstance(receipt, dict) or receipt.get("schema") != "paper-task-evidence/v1" or receipt.get("task_id") != task_id:
        raise ValueError("receipt schema/task mismatch")
    if receipt.get("status") != "complete":
        raise ValueError("blocked, unrun, or partial task cannot pass")
    completed_at = _receipt_time(receipt.get("completed_at"))
    artifacts, outputs = receipt.get("artifacts"), receipt.get("outputs")
    if not isinstance(artifacts, dict) or not artifacts or not isinstance(outputs, dict) or not outputs:
        raise ValueError("receipt requires hashed snapshot artifacts and current-output mappings")
    snapshot_root = relative_file(str(BASE / paper / "receipts" / "snapshots" / task_id))
    for name, sha in artifacts.items():
        if not isinstance(name, str) or not isinstance(sha, str) or len(sha) != 64:
            raise ValueError("invalid snapshot hash entry")
        artifact = relative_file(name)
        if not artifact.is_relative_to(snapshot_root) or not artifact.is_file() or digest(artifact) != sha:
            raise ValueError(f"missing, changed, or non-snapshot evidence: {name}")
    for output, snapshot in outputs.items():
        if not isinstance(output, str) or not isinstance(snapshot, str) or snapshot not in artifacts:
            raise ValueError("output references unhashed snapshot evidence")
        if relative_file(output) == relative_file(snapshot):
            raise ValueError("mutable output cannot be its own evidence snapshot")
        if not any(_output_belongs_to(output, d) for d in task["deliverables"]):
            raise ValueError(f"output is outside task deliverables: {output}")
    for output in task["deliverables"]:
        relative_file(output)
        if not any(_output_belongs_to(name, output) for name in outputs):
            raise ValueError(f"unaccounted deliverable: {output}")
    criteria = receipt.get("criteria")
    if not isinstance(criteria, list) or not all(isinstance(c, dict) for c in criteria):
        raise ValueError("receipt criteria must be a list of supported judgments")
    if [c.get("criterion") for c in criteria] != task["acceptance_criteria"]:
        raise ValueError("receipt must cover the exact task acceptance criteria in order")
    for criterion in criteria:
        evidence = criterion.get("evidence")
        if criterion.get("status") != "met" or not isinstance(criterion.get("explanation"), str) or not criterion["explanation"].strip():
            raise ValueError("each criterion needs a supported explanation")
        if not isinstance(evidence, list) or not evidence or not all(isinstance(v, str) and v in artifacts for v in evidence):
            raise ValueError("criterion references absent or unhashed evidence")
    commands, versions = receipt.get("commands"), receipt.get("source_versions")
    if not isinstance(commands, list) or not commands or not isinstance(versions, dict) or not versions:
        raise ValueError("receipt requires actual validation commands and source versions")
    for command in commands:
        if not isinstance(command, dict):
            raise ValueError("invalid validation command")
        argv = command.get("argv")
        if not isinstance(argv, list) or not argv or not all(isinstance(v, str) and v for v in argv) or type(command.get("exit_code")) is not int or command["exit_code"] != 0:
            raise ValueError("validation command is absent or failed")
        if not isinstance(command.get("log"), str) or command["log"] not in artifacts:
            raise ValueError("validation log must be a hashed snapshot artifact")
        _validation_command_source(command, artifacts)
    if check_current:
        _check_current_outputs(outputs, artifacts)
        _check_directory_coverage(task["deliverables"], outputs)
    return {"task": task_id, "artifact_integrity_valid": True,
            "current_outputs_checked": check_current, "completed_at": completed_at.isoformat(),
            "outputs": outputs, "artifacts": artifacts,
            "limitation": "Recorded evidence is checked; this is not independent scientific replication."}


def verify_task(paper: str, task_id: str):
    _, _, contracts = paper_task_contracts(paper)
    if task_id not in contracts:
        raise ValueError(f"unknown runtime task: {task_id}")
    return _verify_task_contract(paper, contracts[task_id], check_current=True)


def verify_goal(paper: str, goal_id: str):
    cfg, goals, contracts = paper_task_contracts(paper)
    if goal_id not in goals:
        raise ValueError("goal must name a native root goal or subgoal for this paper")
    def within(candidate):
        return candidate == goal_id or any(within(p) for p in goals[candidate])
    selected = [t for t in contracts.values() if goal_id == cfg["root_goal_id"] or within(t["subgoal_id"])]
    if not selected:
        raise ValueError("goal has no executable task contracts")
    results = [_verify_task_contract(paper, task, check_current=False) for task in selected]
    if goal_id == cfg["root_goal_id"]:
        latest, all_artifacts = {}, {}
        for result in results:
            instant = _receipt_time(result["completed_at"])
            all_artifacts.update(result["artifacts"])
            for name, snapshot in result["outputs"].items():
                prior = latest.get(name)
                if prior and instant == prior[0] and result["artifacts"][snapshot] != all_artifacts[prior[1]]:
                    raise ValueError(f"ambiguous simultaneous output versions: {name}")
                if prior is None or instant > prior[0]:
                    latest[name] = (instant, snapshot, result["task"])
        current_outputs = {name: entry[1] for name, entry in latest.items()}
        _check_current_outputs(current_outputs, all_artifacts)
        _check_directory_coverage([d for t in selected for d in t["deliverables"]], current_outputs)
        for result in results:
            result["latest_outputs_checked_at_root"] = True
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("build", "validate", "commands", "run", "verify-task", "verify-goal"), nargs="?", default="validate")
    parser.add_argument("--paper", choices=(*PAPERS, "all"), default="all")
    parser.add_argument("--task")
    parser.add_argument("--goal")
    args = parser.parse_args()
    papers = list(PAPERS) if args.paper == "all" else [args.paper]
    if args.action in {"verify-task", "verify-goal"} and len(papers) != 1:
        parser.error("select one --paper for evidence verification")
    if args.action == "build":
        for paper in papers:
            build(paper)
    elif args.action == "validate":
        print(json.dumps([validate(paper) for paper in papers], indent=2))
    elif args.action == "commands":
        print("python3 scripts/paper_supervisor_campaign.py start")
        print("python3 scripts/paper_supervisor_campaign.py status")
    elif args.action == "run":
        if args.paper != "all":
            parser.error("the Quack/DuckLake campaign starts all three isolated lanes together")
        os.execv(sys.executable, [sys.executable, str(ROOT / "scripts/paper_supervisor_campaign.py"),
                                 "start", "--state-root", str(state_root())])
    elif args.action == "verify-task":
        if not args.task:
            parser.error("--task is required")
        print(json.dumps(verify_task(args.paper, args.task), indent=2))
    else:
        if not args.goal:
            parser.error("--goal is required")
        print(json.dumps(verify_goal(args.paper, args.goal), indent=2))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("paper supervisors: launcher interrupted; owned live process trees stopped", file=sys.stderr)
        raise SystemExit(130)
    except (ValueError, OSError, StopIteration, RuntimeError) as exc:
        print(f"paper supervisors: {exc}", file=sys.stderr)
        raise SystemExit(1)
