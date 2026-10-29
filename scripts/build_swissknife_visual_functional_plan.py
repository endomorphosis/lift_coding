#!/usr/bin/env python3
"""Build the SVF execution board and objective heap from explicit app contracts.

Refuses to overwrite a board after execution has started. This generator is
not a completion writer and does not import historical completed statuses.
"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import shlex

ROOT = Path(__file__).resolve().parents[1]
STEM = "implementation_plan/docs/53-swissknife-visual-functional-mcplusplus"
PROFILE = "config/swissknife_visual_functional_supervisor.json"
SPEC = "config/swissknife_visual_functional_tasks.json"
CONTRACTS = "swissknife/config/visual-functional-app-contracts.json"
WORKFLOW_FIXTURES = "config/swissknife_visual_functional_payload_fixtures.json"
RUNTIME_REVISION = "SVF-20261027-R12-storage-admission-and-owned-ipfs"
DEFAULT_BACKENDS = {"ipfs_kit_py": "http://127.0.0.1:18316", "ipfs_datasets_py": "http://127.0.0.1:18312",
                    "ipfs_accelerate_py": "http://127.0.0.1:18315"}
RUNTIME = "data/agent_supervisor/swissknife_visual_functional"
NOTES_INDEXES_DIRECTORY = RUNTIME + "/backends/services/notes-datasets/indexes"
WORKER = "scripts/swissknife_visual_functional_worker.py"
EXECUTION_INPUTS = [
    "scripts/swissknife_visual_functional_llm.py",
    "config/swissknife_visual_functional_supervisor.json",
    "config/swissknife_visual_functional_tasks.json",
    "swissknife/config/visual-functional-app-contracts.json",
    "swissknife/scripts/capture-visual-functional-baseline.mjs",
    "external/ipfs_accelerate/ipfs_accelerate_py/llm_router.py",
    "external/ipfs_accelerate/ipfs_accelerate_py/cli_runtime/grok_stream_capture.py",
]


def decompose_foundation(spec: dict) -> dict:
    """Add bounded foundation stages without rewriting any completed contract.

    This is a pure plan transformation. The live Markdown board must be
    migrated separately under its registered lease, retaining status blocks.
    """
    result = copy.deepcopy(spec)
    indexed = {t["task_id"]: t for t in result["tasks"]}
    if any(f"SVF-{n:03}" in indexed for n in range(31, 35)):
        raise ValueError("foundation decomposition already present")
    final = indexed["SVF-030"]
    harness = final["edit_paths"][:]
    stages = [
        (31, "Validate scenario admission and independent observation detectors", "command",
         "Run the implemented strict scenario admission, exact semantic requirement binding, typed observation evaluator, DOM readers and genuine blank/clipped/nonplaying media refusal tests. This stage establishes reusable foundation primitives only; browser execution and app acceptance remain unimplemented until subsequent stages pass.", []),
        (32, "Implement the actual desktop lifecycle and scenario action engine", "command",
         "Extend openRealDesktopSession and executeScenarioPhase, preserving stage1 behavior. Reuse capture-visual-functional-baseline.mjs owned-server/Chrome lifecycle, canonical manifest launch and viewport capture; open actual canonical app windows, never setContent or a simulator. Implement bounded click/fill/select/key/close/reopen/wait/assert actions and read actual DOM/media values. Keep original app identity and storage across close/reopen. Add independent tests for wrong result, lost persisted data, clipped/blank content, focus, failure checkpoint and recovery. Wire foundation-check stage2 to concrete lifecycle/action-engine tests, retain explicit failure for unimplemented proof/pilot stages. Keep this patch limited to browser lifecycle/actions; do not implement MCP proof collection yet.", ["swissknife/scripts/capture-visual-functional-baseline.mjs"]),
        (33, "Implement raw MCP proof collection and workflow report assembly", "implementation",
         "Extend collectBackendProof and runWorkflow using the existing stage2 session/action engine and strict stage1 scenario schema. Observe genuine browser /mcp/tools/call request/result pairs, exact owner/tool/route/transport/correlation/app metadata, native outcome, raw receipt and event DAG artifact bytes with matching CIDs. Reuse established gateway/UCAN verification; never invent proofs, receipt bytes or success. Join raw call/result records and evaluate result_assertion RFC6901 pointers against retained raw receipt values. Produce the complete workflow.json schema required by final SVF-030 acceptance and the independent campaign worker, with source/contract hashes, actual viewports/screenshots/trace, all exact result_N/persist_reopen/failure_recovery assertions and five observed checks. Browser-local/external/policy apps must enforce zero unexpected Python-owner calls. Stage3 CLI and unit tests must reject absent/tampered receipts, mismatched joins, fabricated flags and stale sources. Retain stage1/2 guarantees; no app acceptance from unit fixtures.", ["swissknife/docs/visual-functional-driver-contract.md"]),
        (34, "Run a real Calculator foundation integration pilot", "implementation",
         "Implement runCalculatorPilot using the actual canonical Calculator in the completed desktop driver. Perform actual arithmetic, keyboard arithmetic and clear/retry recovery; independently read the rendered result for each. Capture real desktop/mobile PNGs and current driver/application source hashes. Emit pilot/pilot.json schema swissknife.visual-functional-driver-pilot.v1, app_id calculator, actual_desktop:true, foundation_integration_only:true, functional_acceptance:false. observations are exactly arithmetic_result, keyboard_result and clear_recovery, each with typed observation {operator,actual,expected} evaluated from actual UI reads. artifacts retain root-relative path/sha256/bytes, including desktop.png/mobile.png. This pilot proves driver integration only, not full Calculator acceptance or all app workflow completion. --foundation-check pilot --output-dir <dir> runs the real pilot, bounded and lease-owned; fail truthfully when unavailable.", ["swissknife/web/js/apps/calculator.js"]),
    ]
    additions = []
    for number, title, kind, acceptance, contexts in stages:
        identity = f"SVF-{number:03}"
        entry = copy.deepcopy(final)
        entry.update(task_id=identity, stable_task_id=identity, title=title, kind=kind,
                     goal_id=f"SVF-G{number:03}", subgoal_id=f"SVF-G{number:03}",
                     status="ready", dependencies=final["dependencies"][:] if number == 31 else [f"SVF-{number-1:03}"],
                     acceptance=acceptance, context_paths=contexts, foundation_stage=number-30,
                     llm_limits={"maxTurns": 8 if number == 31 else 16, "maxOutputTokens": 12288,
                                 "modelContextBytes": 49152 if number == 31 else 98304 if number == 32 else 262144},
                     edit_paths=harness[:], outputs=[f"{RUNTIME}/tasks/{identity}/receipt.json"],
                     predicted_files=[f"{RUNTIME}/tasks/{identity}/receipt.json", *harness],
                     execution_command=["python3", WORKER, "--task-id", identity],
                     execution_validation=[{"working_directory": ".", "argv": ["python3", WORKER, "--validate", "--task-id", identity]}])
        stage = f"stage{number-30}" if number < 34 else "pilot"
        entry["checks"] = [["node", "--test", harness[1]], ["node", harness[0], "--foundation-check", stage]]
        if number == 34:
            entry["foundation_pilot"] = True
            entry["pilot_sources"] = [harness[0], "swissknife/web/js/apps/calculator.js"]
            entry["checks"][-1] += ["--output-dir", f"{RUNTIME}/tasks/{identity}/pilot"]
        if number == 32:
            entry["llm_limits"]["reasoningEffort"] = "low"
        additions.append(entry)
        result["goals"].append({"goal_id": f"SVF-G{number:03}", "title": title,
                                "parent": "SVF-G030", "status": "active", "acceptance": acceptance})
    final.update(kind="foundation-gate", foundation_stages=[t["task_id"] for t in additions],
                 dependencies=[*final["dependencies"], "SVF-034"], context_paths=[])
    final["checks"] = [["node", "--test", harness[1]], ["node", "--check", harness[0]],
                       *[["node", harness[0], "--foundation-check", stage] for stage in ("stage1", "stage2", "stage3")]]
    position = result["tasks"].index(final)
    result["tasks"][position:position] = additions
    result["plan_revision"] = "SVF-20261024-R3-foundation-stages"
    return result


def enable_foreground_recovery(spec: dict, *, completed_ids=()) -> dict:
    """Admit maintained producers and a real, isolated foreground repair check."""
    result = copy.deepcopy(spec)
    done = set(completed_ids)
    indexed = {task["task_id"]: task for task in result["tasks"]}
    adapter = "scripts/swissknife_visual_functional_recovery.py"
    checker = "scripts/svf_recovery_canary.py"
    fixture = RUNTIME + "/fixtures/automatic-repair-canary.json"
    if "SVF-005" not in indexed:
        canary = copy.deepcopy(indexed["SVF-031"])
        canary.update(task_id="SVF-005", stable_task_id="SVF-005", title="Prove bounded foreground model recovery without human intervention",
                      kind="command", status="ready", goal_id="SVF-G005", subgoal_id="SVF-G005", dependencies=["SVF-010"],
                      acceptance="The original producer must genuinely fail on pending fixture data, then the registered foreground recovery hook must use Grok4.7 through llm_router without native tools to change only the isolated fixture recovery_state to repaired_by_scoped_model. Durable admission, finite budget, exact lease and source hashes and native model receipt are independently verified; only rerunning the original protected checker may complete this operational rehearsal. No app acceptance or goal completion is granted.",
                      edit_paths=[fixture], context_paths=[], checks=[["python3", checker, "--verify", "--fixture", fixture]],
                      outputs=[f"{RUNTIME}/tasks/SVF-005/receipt.json"], predicted_files=[f"{RUNTIME}/tasks/SVF-005/receipt.json", fixture],
                      execution_command=["python3", WORKER, "--task-id", "SVF-005"],
                      execution_validation=[{"working_directory": ".", "argv": ["python3", WORKER, "--validate", "--task-id", "SVF-005"]}],
                      execution_inputs=[*EXECUTION_INPUTS, adapter, checker, fixture], recovery_canary=True,
                      semantic_failure_limit=1, semantic_recovery_limit=1,
                      semantic_recovery_fixture_inputs=[fixture], llm_limits={"maxTurns":1,"maxOutputTokens":2048,"modelContextBytes":32768,"reasoningEffort":"low"})
        canary.pop("foundation_stage", None)
        result["tasks"].insert(1, canary)
        result["goals"].append({"goal_id":"SVF-G005","title":"An exhausted task repairs itself inside its existing lease",
                                "parent":"SVF-G001","status":"active","acceptance":canary["acceptance"]})
        indexed["SVF-005"] = canary
    for task in result["tasks"]:
        identity = task["task_id"]
        if identity in done:
            continue
        if identity in {"SVF-033","SVF-034","SVF-040","SVF-041","SVF-042"}:
            task["kind"] = "command"
        if identity == "SVF-033" and "SVF-005" not in task["dependencies"]:
            task["dependencies"].append("SVF-005")
        if identity == "SVF-034":
            for path in ("swissknife/scripts/svf-calculator-pilot.mjs", "swissknife/test/scripts/visual-functional-pilot.test.mjs"):
                if path not in task["edit_paths"]:
                    task["edit_paths"].append(path); task["predicted_files"].append(path)
            task["pilot_sources"] = ["swissknife/scripts/run-visual-functional-workflow.mjs", "swissknife/scripts/svf-calculator-pilot.mjs", "swissknife/web/js/apps/calculator.js"]
            unit = ["node", "--test", "swissknife/test/scripts/visual-functional-pilot.test.mjs"]
            if unit not in task["checks"]:
                task["checks"].insert(1, unit)
        if identity in {"SVF-040","SVF-041","SVF-042"}:
            tests = ["python3", "scripts/svf_backends/test_readiness.py"]
            if tests not in task["checks"]:
                task["checks"].insert(0, tests)
            for path in ("scripts/svf_backends/common.py", "scripts/svf_backends/scheduler_job.py"):
                if path not in task["edit_paths"]:
                    task["edit_paths"].append(path); task["predicted_files"].append(path)
                if path not in task["execution_inputs"]:
                    task["execution_inputs"].append(path)
            if "scripts/svf_backends/test_readiness.py" not in task["execution_inputs"]:
                task["execution_inputs"].append("scripts/svf_backends/test_readiness.py")
        task["context_paths"] = ["swissknife/docs/visual-functional-driver-contract.md" if p == "swissknife/scripts/run-visual-functional-workflow.mjs" else p for p in task.get("context_paths", [])]
        if not task.get("edit_paths"):
            continue
        for dependency in (adapter, "scripts/swissknife_visual_functional_supervisor.py",
                "external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/rescue/lane_resume.py",
                "external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/rescue/semantic_recovery.py"):
            if dependency not in task["execution_inputs"]:
                task["execution_inputs"].append(dependency)
        task["recovery_edit_paths"] = [p for p in task["edit_paths"] if "/test/" not in p or (p.startswith("swissknife/test/e2e/functional-workflows/") and p.endswith(".json"))]
        if not task["recovery_edit_paths"]:
            continue
        task["semantic_recovery_command"] = shlex.join(["python3", WORKER, "--recover", "--task-id", identity])
        task["semantic_recovery_inputs"] = [WORKER, "scripts/swissknife_visual_functional_llm.py", adapter, "swissknife/docs/visual-functional-driver-contract.md"]
        task["semantic_recovery_timeout_seconds"] = 900
        task.setdefault("semantic_recovery_limit", 2)
        task.setdefault("semantic_failure_limit", 6)
    result["plan_revision"] = "SVF-20261025-R4-foreground-recovery"
    return result


RUNTIME_SOURCE_INPUTS = [
    "external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/rescue/storage_pressure.py",
    "scripts/svf_backends/owned_kubo_watchdog.py",
    "config/swissknife_visual_functional_ipfs_watchdog.json",
    "config/systemd/swissknife-visual-functional-native-ipfs.service",
    "config/systemd/swissknife-visual-functional-ipfs-watchdog.service",
    "scripts/swissknife_visual_functional_worker.py",
    "swissknife/scripts/run-visual-functional-workflow.mjs",
    "swissknife/web/js/live-tool-gateway.js", "swissknife/web/js/main-simple.js",
    "swissknife/build-tools/configs/vite.web.config.ts", "swissknife/scripts/lib/pick-free-port.mjs",
    "swissknife/scripts/mcpplusplus-profile-a.cjs", "swissknife/scripts/mcpplusplus-artifact-store.cjs",
    "swissknife/scripts/vdg-connector-artifacts.cjs", "swissknife/scripts/start-ipfs-kit-mcp-compat.cjs",
    "swissknife/scripts/ipfs-kit-native-forwarder.cjs", "scripts/svf_backends/native_kit_service.py",
    "external/ipfs_kit/ipfs_kit_py/assurance/pinned_ipfs.py",
    "external/ipfs_kit/ipfs_kit_py/core/operation_contracts.py",
    "swissknife/src/services/mcp/all-app-tool-mediator.ts", "swissknife/src/services/mcp/all-app-tool-gateway.ts",
    "swissknife/src/services/mcp/mcp-plus-plus-connector.ts", "swissknife/src/services/mcp/mcp-plus-plus-profile-c.ts",
    "swissknife/src/services/apps/all-app-live-tool-bindings.ts",
    "swissknife/src/services/mcp/all-tools-disposition-catalog.ts",
    "swissknife/src/services/apps/all-app-backend-status-contract.ts",
    "swissknife/docs/visual-functional-driver-contract.md",
    "scripts/svf_backends/common.py", "scripts/svf_backends/ipfs_kit_py.py",
    "scripts/svf_backends/ipfs_datasets_py.py", "scripts/svf_backends/ipfs_accelerate_py.py",
    "config/systemd/swissknife-visual-functional-native-kit.service",
    "config/systemd/swissknife-visual-functional-kit-facade.service",
    "scripts/swissknife_visual_functional_blocked.py",
    "scripts/svf_backends/native_accelerate_backend.py", "scripts/svf_backends/native_accelerate_service.py",
    "swissknife/scripts/ipfs-accelerate-native-forwarder.cjs", "swissknife/scripts/all-tools-evidence-lib.cjs",
    "swissknife/scripts/start-ipfs-accelerate-mcp-compat.cjs", "swissknife/scripts/start-ipfs-datasets-mcp-compat.cjs",
    "config/systemd/swissknife-visual-functional-native-accelerate.service",
    "config/systemd/swissknife-visual-functional-accelerate-facade.service",
    "config/systemd/swissknife-visual-functional-notes-datasets.service",
    "external/ipfs_accelerate/ipfs_accelerate_py/inference_backend_manager.py",
    "external/ipfs_datasets/ipfs_datasets_py/vector_stores/management_engine.py",
    "external/ipfs_datasets/ipfs_datasets_py/vector_stores/duckdb_store.py",
    "scripts/svf_backends/notes_fixture.py", WORKFLOW_FIXTURES,
    "scripts/svf_backends/native_accelerate_observation.py",
    "external/ipfs_accelerate/ipfs_accelerate_py/hf_model_server/monitoring/health.py",
    "external/ipfs_accelerate/ipfs_accelerate_py/hf_model_server/monitoring/metrics.py",
    "scripts/swissknife_visual_functional_phase_budget.py",
    "swissknife/web/js/all-app-backend-status.js", "swissknife/web/index.html",
    "swissknife/web/css/desktop.css", "swissknife/web/css/windows.css",
    "swissknife/web/css/aero-enhanced.css", "swissknife/web/css/design-system.css",
    "swissknife/web/js/apps/network-native-tools.js",
    "swissknife/web/css/terminal.css", "swissknife/web/css/apps.css",
    "swissknife/web/css/model-browser.css", "swissknife/web/css/strudel.css",
    "swissknife/web/css/strudel-grandma.css", "swissknife/web/css/vibecode-enhanced.css",
    "swissknife/web/css/strudel-ai-daw.css", "swissknife/web/css/api-keys-enhanced.css",
    "swissknife/web/css/github-oauth.css", "swissknife/web/css/huggingface.css",
    "swissknife/web/css/openrouter.css",
]


def register_shared_desktop_recovery(spec: dict, completed_ids=()) -> dict:
    """Give shared UI failures a real owner without widening leaf app scope.

    This transformation never rewrites completed tasks, goals, spent budgets,
    validators or acceptance. Its protected checks must run in the original
    producer before any pending app is accepted.
    """
    result = copy.deepcopy(spec)
    done = set(completed_ids)
    identity = "SVF-035"
    if not any(task["task_id"] == identity for task in result["tasks"]):
        paths = ["swissknife/web/js/main-simple.js", "swissknife/web/js/all-app-backend-status.js"]
        test = "swissknife/test/scripts/shared-desktop-notices.test.mjs"
        receipt = f"{RUNTIME}/tasks/{identity}/receipt.json"
        entry = {
            "task_id": identity, "stable_task_id": identity,
            "title": "Repair shared desktop notices without obscuring application controls",
            "kind": "command", "status": "ready", "priority": "P0",
            "goal_id": "SVF-G030", "subgoal_id": "SVF-G030", "dependencies": ["SVF-040"],
            "acceptance": "Run protected shared-desktop tests and syntax checks. Software-renderer warnings remain truthful and keyboard accessible in a compact taskbar disclosure; renderer details must not cover app content by default at desktop or mobile widths. Backend status, policy confirmation, native errors and recovery controls remain accessible with honest state. Changes are limited to the two declared shared UI files. These checks establish shared infrastructure only; each app still requires its original semantic workflow, SDK proofs and pinned Grok4.7 final visual review.",
            "edit_paths": paths, "recovery_edit_paths": paths[:], "context_paths": [],
            "checks": [["node", "--test", test], *[["node", "--check", name] for name in paths]],
            "outputs": [receipt], "predicted_files": [receipt, *paths],
            "execution_command": ["python3", WORKER, "--task-id", identity],
            "execution_validation": [{"working_directory": ".", "argv": ["python3", WORKER, "--validate", "--task-id", identity]}],
            "execution_inputs": [*EXECUTION_INPUTS, test, *paths],
            "timeout_seconds": 1800, "resource_class": "cpu-small",
            "conflict_policy": "Hold the registered checkout lease; edit declared paths only; preserve foreign dirt and historical boards. Protected tests, acceptance and receipts are read only.",
            "semantic_failure_limit": 6, "semantic_recovery_limit": 2,
            "semantic_recovery_timeout_seconds": 900,
            "semantic_recovery_command": shlex.join(["python3", WORKER, "--recover", "--task-id", identity]),
            "semantic_recovery_inputs": [WORKER, "scripts/swissknife_visual_functional_llm.py",
                "scripts/swissknife_visual_functional_recovery.py", test],
            "llm_limits": {"maxTurns": 1, "maxOutputTokens": 16384,
                           "modelContextBytes": 262144, "reasoningEffort": "low"},
        }
        result["tasks"].insert(next((i for i, task in enumerate(result["tasks"])
                                     if task["task_id"] == "SVF-030"), 0), entry)
    for task in result["tasks"]:
        if task["task_id"] not in done and task.get("kind") == "verify":
            task["dependencies"] = list(dict.fromkeys([*task["dependencies"], identity]))
    result["plan_revision"] = RUNTIME_REVISION
    return result


def bind_runtime_sources(spec: dict, apps: list[dict], completed_ids=()) -> dict:
    """Bind actual readonly runtime dependencies without reopening history."""
    result = copy.deepcopy(spec)
    completed = set(completed_ids)
    indexed = {app["app_id"]: app for app in apps}
    for task in result["tasks"]:
        if task["task_id"] in completed:
            continue
        sources = list(RUNTIME_SOURCE_INPUTS)
        if task.get("app_id"):
            for name in indexed[task["app_id"]]["source_paths"]:
                if Path(name).is_absolute() or ".." in Path(name).parts:
                    raise ValueError("app runtime source must remain inside SwissKnife")
                sources.append(name if name.startswith("swissknife/") else "swissknife/" + name)
        task["execution_inputs"] = list(dict.fromkeys([*task.get("execution_inputs", []), *sources]))
    result["plan_revision"] = RUNTIME_REVISION
    return result


def canonicalize_app_source_paths(spec: dict, completed_ids=(), *, root: Path | None = None) -> dict:
    """Declare the regular implementation behind an in-tree app launch alias.

    Workers continue refusing symbolic-link source/evidence paths. Completed
    contracts remain byte-equivalent; no acceptance or retry bounds change.
    """
    root = (root or ROOT).resolve()
    result = copy.deepcopy(spec)
    completed = set(completed_ids)
    aliases = {}
    app_directory = root / "swissknife/web/js/apps"
    for task in result["tasks"]:
        if task["task_id"] in completed:
            continue
        for name in task.get("edit_paths", []):
            source = root / name
            if not name.startswith("swissknife/web/js/apps/") or not source.is_symlink():
                continue
            target = source.resolve(strict=True)
            if not target.is_relative_to(app_directory) or not target.is_file():
                raise ValueError("app launch alias must target a regular implementation inside the app directory")
            aliases[name] = target.relative_to(root).as_posix()
    for task in result["tasks"]:
        if task["task_id"] in completed:
            continue
        for key in ("edit_paths", "predicted_files", "recovery_edit_paths", "context_paths", "execution_inputs"):
            if key in task:
                task[key] = list(dict.fromkeys(aliases.get(name, name) for name in task[key]))
        if "checks" in task:
            task["checks"] = [[aliases.get(value, value) for value in argv] for argv in task["checks"]]
    if aliases:
        result["plan_revision"] = RUNTIME_REVISION
    return result


def bind_failure_feedback(spec: dict, completed_ids=()) -> dict:
    """Qualify recovery on the task's observed error without reopening history."""
    result = copy.deepcopy(spec)
    completed = set(completed_ids)
    for task in result["tasks"]:
        if task["task_id"] in completed or task.get("kind") != "verify":
            continue
        diagnostic = RUNTIME + "/tasks/" + task["task_id"] + "/last-execution-failure.json"
        task["semantic_recovery_inputs"] = list(dict.fromkeys([
            *task.get("semantic_recovery_inputs", []), diagnostic]))
    if result.get("plan_revision") != RUNTIME_REVISION:
        result["plan_revision"] = "SVF-20261026-R6-observed-failure-recovery"
    return result


def task_markdown(entry: dict) -> str:
    lines = [f"## {entry['task_id']} {entry['title']}", "", "- Status: ready", f"- Priority: {entry['priority']}",
        f"- Track: {entry['kind']}", "- Depends on: " + ", ".join(entry["dependencies"]), f"- Goal id: {entry['goal_id']}",
        "- Outputs: " + ", ".join(entry["outputs"]), "- Deterministic command: " + shlex.join(entry["execution_command"]),
        "- Execution inputs: " + ", ".join(entry["execution_inputs"]), "- Validation: " + shlex.join(entry["execution_validation"][0]["argv"]),
        "- Predicted files: " + ", ".join(entry["predicted_files"]), f"- Implementation timeout seconds: {entry['timeout_seconds']}",
        f"- Resource class: {entry['resource_class']}", "- Board namespace: swissknife-visual-functional-v1",
        "- Parallel lane: swissknife-visual-functional", f"- Bundle: swissknife/visual-functional/{entry.get('app_id',entry['kind'])}",
        f"- Conflict policy: {entry['conflict_policy']}", f"- Acceptance: {entry['acceptance']}"]
    for key in ("semantic_failure_limit", "semantic_recovery_command", "semantic_recovery_inputs", "semantic_recovery_timeout_seconds",
                "semantic_recovery_limit", "semantic_recovery_fixture_inputs"):
        if key in entry:
            value = entry[key]
            lines.append(f"- {key.replace('_',' ').capitalize()}: " + (", ".join(value) if isinstance(value,list) else str(value)))
    return "\n".join([*lines,"",""]) + "\n"


def build() -> dict:
    apps = json.loads((ROOT / CONTRACTS).read_text())["apps"]
    if len(apps) != 45 or len({a["app_id"] for a in apps}) != 45:
        raise ValueError("scope must match the 45 canonical app contracts")
    board_path = ROOT / (STEM + ".todo.md")
    if board_path.exists() and ("- Status: completed" in board_path.read_text() or "- Status: in_progress" in board_path.read_text()):
        raise ValueError("execution started; never regenerate authoritative task statuses")
    settings = {"provider": "grok_cli", "model": "grok-4.7", "temperature": 0,
                "timeoutSeconds": 600, "maxOutputTokens": 16384, "maxTurns": 24,
                "allowLocalFallback": False, "allowCrossProviderFallback": False,
                "disableModelRetry": True, "repairReadPolicy":"inline_only", "repairReasoningEffort":"low"}
    profile = {
        "schema": "swissknife.visual-functional-supervisor-profile.v1", "profileId": "swissknife-visual-functional-v1",
        "repositoryRoot": ".", "primaryRepository": "swissknife", "humanPlanPath": STEM + ".md",
        "objectivePath": STEM + ".objectives.md", "todoPath": STEM + ".todo.md", "taskSpecPath": SPEC,
        "appContractPath": CONTRACTS, "taskPrefix": "## SVF-", "goalPrefix": "SVF-G", "rootGoalId": "SVF-G000",
        "runtimeRoot": RUNTIME, "statePrefix": "svf", "router": settings, "llm": settings,
        "bounds": {"masterDurationSeconds": 28800, "heartbeatSeconds": 30, "defaultTaskTimeoutSeconds": 1800,
                   "browserTaskTimeoutSeconds": 3600, "attemptsPerTask": 3, "modelRepairAttemptsPerTask": 3},
        "backends": dict(DEFAULT_BACKENDS), "workflowFixturesPath": WORKFLOW_FIXTURES,
        "backendReadiness": {"kuboApi":"http://127.0.0.1:5031", "ipfsGateway":"http://127.0.0.1:8092", "python":"external/ipfs_datasets/.venv/bin/python",
                             "notesIndexesDirectory": NOTES_INDEXES_DIRECTORY},
        "authority": {"model": "proposal_only", "baseline": "not_functional_acceptance", "historicalGO": "not_current_app_acceptance",
                      "supervisor": "task_status_only", "work_complete": False, "completion_authority": False},
        "safety": {"exclusiveCheckoutLease": "swissknife-supervisor-checkout-lease-v1", "laneId": "swissknife-visual-functional",
                   "maxDirtyAttempts": 0, "ephemeralWorktrees": False, "worktreeReconciliation": False,
                   "mutations": "isolated test fixtures with UI-mediated policy confirmation; no user data or external account actions",
                   "preserveOtherBoards": ["SVD", "SWR", "VDG", "VDL", "VOG"]},
    }
    goals, tasks = [], []

    def goal(goal_id: str, title: str, parent: str = "SVF-G000", acceptance: str = "") -> str:
        goals.append({"goal_id": goal_id, "title": title, "parent": parent, "status": "active", "acceptance": acceptance or title})
        return goal_id

    def task(task_id: str, title: str, kind: str, goal_id: str, deps: list[str], acceptance: str,
             *, app: dict | None = None, edit_paths: list[str] | None = None, checks: list[list[str]] | None = None,
             extra: dict | None = None, priority: str = "P1") -> str:
        edits = edit_paths or []
        command = ["python3", WORKER, "--task-id", task_id]
        validation = ["python3", WORKER, "--validate", "--task-id", task_id]
        entry = {"task_id": task_id, "stable_task_id": task_id, "title": title, "kind": kind,
                 "status": "ready", "goal_id": goal_id, "subgoal_id": goal_id, "dependencies": deps,
                 "acceptance": acceptance, "priority": priority, "edit_paths": edits, "checks": checks or [],
                 "outputs": [f"{RUNTIME}/tasks/{task_id}/receipt.json"],
                 "predicted_files": [f"{RUNTIME}/tasks/{task_id}/receipt.json", *edits],
                 "execution_command": command, "execution_validation": [{"working_directory": ".", "argv": validation}],
                 "execution_inputs": EXECUTION_INPUTS[:],
                 "timeout_seconds": 3600 if kind in {"baseline", "verify", "regression"} else 1800,
                 "resource_class": "cpu-browser" if kind in {"baseline", "verify", "regression"} else "cpu-small",
                 "conflict_policy": "Hold the registered checkout lease; edit declared paths only; preserve foreign dirt and all historical boards; no fake success, test weakening or receipt fabrication."}
        if app:
            entry["app_id"] = app["app_id"]
            entry["context_paths"] = ["swissknife/" + p for p in app["source_paths"]]
        entry.update(extra or {})
        tasks.append(entry)
        return task_id

    goal("SVF-G000", "All 45 actual desktop applications perform their intended user workflows with truthful MCP++ integration", "",
         "Fresh desktop/mobile visual inspection, semantic workflow and recovery evidence for every canonical app, genuine relevant backend outcomes, and all cross-app regressions; objective verification remains separately governed.")
    goal("SVF-G001", "Canonical plan ingestion and safe autonomous execution")
    goal("SVF-G010", "Exact model route and real three-owner backend readiness")
    goal("SVF-G020", "Actual desktop visual baselines and actionable findings for every application")
    goal("SVF-G030", "Trustworthy workflow runner, compact usable UI and accessible recovery")
    goal("SVF-G040", "Application-specific repairs with preserved intended behavior")
    goal("SVF-G050", "Current full regression and cross-application workflows")
    goal("SVF-G090", "Evidence-based closeout without historical or model self-certification")

    task("SVF-000", "Ingest the complete goal hierarchy and executable taskboard", "seal", "SVF-G001", [],
         "Canonical load_taskboard and parse_goal_heap accept all records, independent DAG checks pass, DuckDB ingests every task with execution_validation retained, and all app references match the manifest.", priority="P0")
    task("SVF-010", "Prove the exact Grok 4.7 route through llm_router", "model-probe", "SVF-G010", ["SVF-000"],
         "One real uncached native completion proves effective grok_cli/grok-4.7, temperature zero, no fallback, no model retry, bounded deadline and no provider writes; retain native trace and result.", priority="P0")
    task("SVF-011", "Audit actual adapters and record degraded upstream owners", "backend-audit", "SVF-G010", ["SVF-000"],
         "Record all three MCP++ adapter health responses and upstream availability separately. An audit may finish with explicit degraded owners; it does not grant backend readiness or app acceptance.", priority="P0")

    # Three pilots establish behavior across storage, datasets, and acceleration.
    ordered = sorted(apps, key=lambda a: ({"image-viewer": 0, "notes": 1, "accelerate-panel": 2}.get(a["app_id"], 10), a["canonical_order"]))
    app_ids = {}
    for index, app in enumerate(ordered, 1):
        n = 100 + index * 10
        app_ids[app["app_id"]] = {"baseline": f"SVF-{n}", "review": f"SVF-{n+1}", "repair": f"SVF-{n+2}", "verify": f"SVF-{n+3}"}
        gid = f"SVF-G{100+index:03}"
        goal(gid, app["title"] + ": useful visual layout and intended workflow", "SVF-G040",
             "; ".join(app["primary_workflow"]["expected_results"]) + "; " + app["primary_workflow"]["persist_reopen"] + "; " + app["primary_workflow"]["error"])
        goal(gid + "-V", "Real desktop and narrow viewport inspection", gid, "Capture actual app primary content and inspect screenshots against app-specific visual checks; diagnostics cannot displace the user's task.")
        goal(gid + "-F", "Semantic workflow, persistence and failure recovery", gid, "Execute the declared inputs and actions, assert actual results and state after reopen, then exercise the declared failure and recovery.")
        goal(gid + "-M", "Truthful backend and policy boundary", gid, app["backend_boundary"])
        baseline_id = task(app_ids[app["app_id"]]["baseline"], "Capture actual " + app["title"] + " baseline", "baseline", gid + "-V", ["SVF-000", "SVF-010"],
                           "Launch the canonical real app, capture desktop/mobile full and primary-area PNGs plus DOM, console, network and source hashes; report baseline_only and not_evaluated, never GO.", app=app)
        task(app_ids[app["app_id"]]["review"], "Inspect " + app["title"] + " screenshots and workflow gaps", "review", gid + "-V", [baseline_id],
             "Grok4.7 through the pinned router reads all four retained PNGs and reports concrete visual, accessibility, workflow and backend findings with evidence paths; model review remains proposal-only.", app=app,
             extra={"baseline_task": baseline_id})

    harness_paths = ["swissknife/scripts/run-visual-functional-workflow.mjs", "swissknife/test/scripts/visual-functional-workflow.test.mjs"]
    task("SVF-030", "Implement trustworthy real-desktop semantic workflow execution", "implementation", "SVF-G030",
         [app_ids["image-viewer"]["review"], "SVF-011"],
         "Implement the documented workflow runner/report contract using actual canonical app windows and Playwright; no setContent simulator or fabricated IDs. Tests must detect blank media, generic click-only evidence, missing persisted content, missing receipt bytes, stale source hashes and policy boundary violations. Driver --app/--contracts/--output-dir emits workflow.json and real desktop/mobile PNG and trace artifacts. It must load each app's declarative scenario under test/e2e/functional-workflows/<app>.json; fail when absent. It must compute all semantic_assertions from browser/owner observations, not copy expectations. Return source_template:false,actual_desktop:true, source_sha256 for every manifest source path prefixed swissknife/, contract_sha256, artifacts[path,sha256,bytes], checks for primary_result/keyboard/desktop_layout/mobile_layout/error_recovery. Each check.observation and semantic_assertion.observed is {operator,actual,expected}; operator equals/not_equals/contains/at_least is independently evaluated by the worker. Semantic assertions have unique requirement_id result_1..N/persist_reopen/failure_recovery and requirement_text matching the exact app contract text (failure_recovery is error plus ' Recovery: ' plus recovery). Tool-backed backend_observations include owner/tool/transport/correlation/app/route/outcome, receipt_id,event_dag_cid and root-relative receipt_artifact/event_artifact paths also present in artifacts. Retain actual raw bytes whose content hashes match the CIDs; verify the call/result joins. Include result_assertion {pointer,operator,actual,expected} where the RFC6901 pointer resolves into the retained raw receipt and actual equals the pointed value. Flags alone are insufficient. Local/external/policy apps have zero unexpected Python-owner calls. Screenshots must show actual decoded/edited/generated content. Test fixtures are bounded and consent-mediated. Tests execute at least one real failure detector and reject synthetic reports; do not weaken the independent campaign worker validator.",
         edit_paths=harness_paths,
         checks=[["node", "--test", harness_paths[1]], ["node", "--check", harness_paths[0]]],
         extra={"context_paths": ["swissknife/scripts/capture-visual-functional-baseline.mjs", "swissknife/test/e2e/helpers/live-click-session.ts", "scripts/swissknife_visual_functional_worker.py", "swissknife/scripts/vog_live_click_requires_observation.py"]}, priority="P0")
    # Owner-specific preparation is independent: a degraded A owner cannot stop
    # browser-local baselines or K/D repairs. Verification carries relevant deps.
    backend_tasks = {}
    for number, owner in enumerate(["ipfs_kit_py", "ipfs_datasets_py", "ipfs_accelerate_py"], 40):
        path = f"scripts/svf_backends/{owner}.py"
        task_id = f"SVF-{number:03}"
        backend_tasks[owner] = task_id
        task(task_id, "Qualify and repair " + owner + " semantic readiness", "backend-repair", "SVF-G010", ["SVF-011", "SVF-010"],
             "Implement a bounded owner-readiness/ensure utility. Verify native MCP schemas and a real owner operation, not adapter health alone: K retrieves independently hashed fixture bytes; D returns real bounded rows/search results; A runs bounded actual inference or a real bounded scheduler job and returns usable output. If an upstream is missing, start/configure an isolated campaign-owned service on an available reserved port with identity/state records; preserve foreign services and never replace an arbitrary listener or claim mock success. Existing HTTP and libp2p connectors/UCAN/event DAG contracts remain intact. --ensure --verify uses only controlled fixtures and bounded resource limits, writes an honest semantic readiness receipt, fails if unavailable, and supports repeat-safe recovery. Do not change user credentials or global service defaults.",
             edit_paths=[path], checks=[["python3", path, "--ensure", "--verify", "--profile", PROFILE]],
             extra={"context_paths": ["swissknife/scripts/verify-vdg-backends.mjs", "swissknife/scripts/start-ipfs-accelerate-mcp-compat.cjs", "swissknife/scripts/start-ipfs-datasets-mcp-compat.cjs", "swissknife/scripts/start-ipfs-kit-mcp-compat.cjs"]}, priority="P1")
    for app in ordered:
        ids = app_ids[app["app_id"]]
        gid = f"SVF-G{101+ordered.index(app):03}"
        app_source = "swissknife/" + app["source_paths"][0]
        scenario = "swissknife/test/e2e/functional-workflows/" + app["app_id"] + ".json"
        edits = [app_source, scenario]
        expected = "; ".join(app["primary_workflow"]["expected_results"])
        task(ids["repair"], "Repair " + app["title"] + " intended workflow and layout", "repair", gid + "-F", [ids["review"], "SVF-030"],
             "Address the retained app-specific findings without replacing the original intended behavior. Primary fixture: " + app["primary_workflow"]["input_fixture"] + ". Expected: " + expected + ". Persistence: " + app["primary_workflow"]["persist_reopen"] + ". Error/recovery: " + app["primary_workflow"]["error"] + "; " + app["primary_workflow"]["recovery"] + ". Preserve the disposition: " + app["backend_boundary"] + " Add a declarative test scenario for this app as required by the runner. No fabricated CID, DOM proof labels, hidden controls, generic event-only success or weakened tests. Use existing design tokens and progressive disclosure of diagnostics.", app=app, edit_paths=edits,
             checks=[["node", "--check", app_source], ["python3", "-m", "json.tool", scenario]],
             extra={"baseline_task": ids["baseline"], "context_paths": [app_source, "swissknife/scripts/run-visual-functional-workflow.mjs", f"{RUNTIME}/tasks/{ids['review']}/review.json"]})
        owners = {item.get("owner") for item in app["backend_roles"]}
        deps = [ids["repair"], *[backend_tasks[o] for o in sorted(owners) if o in backend_tasks]]
        task(ids["verify"], "Verify " + app["title"] + " actual results, recovery and final visuals", "verify", gid + "-M", deps,
             "Execute the declared semantic workflow on actual desktop and mobile viewports, check real rendered results, keyboard, persistence/reopen and failure/recovery, and bind screenshots/traces to current source and contract. Require all result_N/persist_reopen/failure_recovery assertions. Tool-backed workflows require genuine owner execution, independently retrieved/hashed receipts+DAG, and useful result assertions; dry-run previews cannot prove writes. Local, external and policy-blocked behavior must remain honest. Final pinned-model visual review must pass; failed verification gets at most two scoped automatic repair attempts before the ordinary bounded retry policy. Never report accepted just because an event fired or text changed.", app=app, edit_paths=edits)
    verifies = [app_ids[a["app_id"]]["verify"] for a in ordered]
    task("SVF-900", "Rerun all 45 app workflows against the final shared source", "regression", "SVF-G050", verifies,
         "Re-execute every real app workflow serially after all source repairs. Refresh all source/contract hashes and screenshot/trace artifacts so shared CSS/gateway/generated-surface changes cannot reuse stale app acceptance.", priority="P2")
    for number, title, expectation in [
        (910, "Dataset to inference to saved result", "Use D to retrieve bounded actual rows, A to compute a real bounded inference/result, K to persist exact output; reopen it in the user-facing apps with linked verified provenance."),
        (920, "CID media to edit/export to reopen", "Retrieve verified CID bytes, display/decode them, edit/export an actual media result, persist and reopen the result; compare intended content rather than proof labels."),
        (930, "Goal to task to real worker output", "Inspect goal/subgoal/task dependencies, request one bounded test dispatch through the supervisor app, observe actual worker progress/output and verified acceptance, exercise timeout/cancel/recovery without mutating old boards."),
    ]:
        path = f"swissknife/scripts/svf-cross-workflow-{number}.mjs"
        task(f"SVF-{number}", "Verify cross-app " + title, "implementation", "SVF-G050", ["SVF-900"],
             expectation + " Use the same actual desktop driver, isolated fixtures, consent and truthful MCP++ observations. Fail on missing capability; retain current screenshots, source-bound semantic results, and receipt/DAG proofs. Emit <output-dir>/workflow.json with schema swissknife.visual-functional-cross-workflow.v1, task_id, task_spec_sha256, contract_sha256, current source_sha256, canonical app_ids, desktop/mobile artifact hashes, and typed primary_result/persist_reopen/failure_recovery assertions whose requirement_text binds to this task acceptance. Each observation is {operator,actual,expected}; backend observations retain raw receipt_artifact/event_artifact with verifiable CIDs and independently evaluated result_assertion JSON pointers. Match the independent worker validate_cross_workflow contract exactly. Model text or passed flags alone cannot certify a composed workflow.",
             edit_paths=[path], checks=[["node", path, "--verify", "--output-dir", f"{RUNTIME}/tasks/SVF-{number}/cross-workflow"]], priority="P2")
    task("SVF-990", "Aggregate current app and cross-app acceptance without bypasses", "aggregate", "SVF-G090", ["SVF-900", "SVF-910", "SVF-920", "SVF-930"],
         "Validate all 45 current regression reports and all three cross-app task receipts. Refuse missing, stale, failed, generic, unverified, or baseline-only evidence. Produce a scoped program decision; objective completion authority and work_complete remain false.",
         extra={"regression_task": "SVF-900"}, priority="P2")

    spec = {"schema": "swissknife.visual-functional-taskboard.v1", "board_namespace": "swissknife-visual-functional-v1",
            "title": "SwissKnife real desktop visual and functional repair", "plan_revision": "SVF-20261024-R2-watchdog", "goals": goals, "tasks": tasks}
    spec = canonicalize_app_source_paths(bind_failure_feedback(bind_runtime_sources(register_shared_desktop_recovery(
        enable_foreground_recovery(decompose_foundation(spec))), apps)))
    tasks, goals = spec["tasks"], spec["goals"]
    (ROOT / PROFILE).write_text(json.dumps(profile, indent=2) + "\n")
    (ROOT / SPEC).write_text(json.dumps(spec, indent=2) + "\n")

    heading = "# SwissKnife Visual and Functional MCP++ Taskboard (SVF)\n\n"
    heading += f"Executable projection of [{Path(STEM).name}.md]({Path(STEM).name}.md). Machine task contracts: `{SPEC}`.\n\n"
    heading += "All initial task statuses use the canonical `ready` value; dependencies control selectability. Only the registered accelerator lane marks task completion after its independent validator passes. Model proposals, historical completed labels, click counts and baseline screenshots cannot grant completion.\n\n"
    heading += "The canonical JSON/DuckDB import is the initial plan snapshot. This Markdown board is the single runtime status authority. Preserve SVD/SWR/VDG/VDL/VOG boards and foreign working-tree changes. One browser task and one leased writer run at a time.\n\n"
    chunks = [heading]
    for entry in tasks:
        chunks.append(task_markdown(entry))
    board_path.write_text("".join(chunks))
    objective = ["# SwissKnife Real Desktop Objective Heap (SVF)\n\n", f"Profile: `{PROFILE}`. Execution board: `{STEM}.todo.md`. Full requirements: `{CONTRACTS}`.\n\n",
                 "All goals begin active. Passing tasks supplies evidence; it does not promote a goal to verified_complete. The canonical goal lifecycle owns that separate decision.\n\n"]
    for item in goals:
        linked = [t for t in tasks if t["goal_id"] == item["goal_id"] or t["goal_id"].startswith(item["goal_id"] + "-")]
        objective.append("\n".join([f"## {item['goal_id']} {item['title']}", "", "- Status: active", f"- Parent: {item['parent']}",
                                    "- Priority: P0" if item["goal_id"] in {"SVF-G000", "SVF-G001"} else "- Priority: P1",
                                    "- Track: visual-functional", f"- Bundle: swissknife/visual-functional/{item['goal_id']}",
                                    f"- Goal: {item['title']}", "- Evidence: " + ", ".join(t["outputs"][0] for t in linked),
                                    f"- Outputs: {RUNTIME}/tasks/", f"- Acceptance: {item['acceptance']}", "", ""]))
    (ROOT / (STEM + ".objectives.md")).write_text("".join(objective))
    return {"tasks": len(tasks), "goals": len(goals), "apps": len(apps), "profile": PROFILE, "board": str(board_path.relative_to(ROOT))}


if __name__ == "__main__":
    argparse.ArgumentParser(description=__doc__).parse_args()
    print(json.dumps(build(), indent=2))
