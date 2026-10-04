"""Real finite planning/capacity qualification in privately owned state.

The public APIs deliberately return review-only proposals. This adapter records
actual stage outcomes and refusal controls without signing or launching tasks.
"""
from __future__ import annotations

import argparse
import importlib
import importlib.abc
import importlib.machinery
import json
import sys
import time
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from codebase_ir_acceptance import (
    FALSE_AUTHORITY,
    OFFSET_CLAUSE,
    TYPE_CLAUSE,
    canonical_bytes,
    scenarios,
    sha256,
    source_function,
    validate_native_result,
)
from codebase_ir_external_pins import (
    MAX_FILES,
    MAX_TOTAL_BYTES,
    capture_external_manifest,
    compare_external_pins,
    interpreter_site_roots,
    read_file_pin,
)
from codebase_ir_native_contracts import _git, imported_native_sources, native_source_snapshot

TASK_TYPE = "task:qualification:finite:type"
TASK_OFFSET = "task:qualification:finite:offset"
REVIEW_REF = "review:authored-qualification-finite-operations@1"


def reviewed_operations() -> list[dict[str, str]]:
    return [{"requirement_id": clause, "task_id": task, "producer_id": producer,
        "path": "calc.py", "function_name": "increment", "parameter": "n",
        "review_ref": REVIEW_REF, "operation": "update"}
        for clause, task, producer in (
            (TYPE_CLAUSE, TASK_TYPE, "producer:qualification:finite:type"),
            (OFFSET_CLAUSE, TASK_OFFSET, "producer:qualification:finite:offset"))]


def assert_planning_crossing(result: dict[str, Any], case: dict[str, Any], *, capacity: bool) -> None:
    """Structural comparison of an owner-returned proposal, never authentication."""
    validate_native_result(result["match"], case)
    if any(result.get(name) is not False for name in (*FALSE_AUTHORITY, "production_admitted", "worker_launched", "omission_authority")):
        raise ValueError("planning proposal acquired undeclared authority")
    forbidden = set(FALSE_AUTHORITY) | {"production_admitted", "worker_launched", "omission_authority",
        "write_authority", "worker_allowed", "production_activated", "signed_evidence_admitted"}
    pending = [result]
    while pending:
        value = pending.pop()
        if type(value) is dict:
            if any(child is not False for key, child in value.items() if key in forbidden):
                raise ValueError("nested planning material acquired undeclared authority")
            pending.extend(value.values())
        elif type(value) is list:
            pending.extend(value)
    declared = {row["task_id"]: row for row in reviewed_operations()}
    if result.get("declared_task_requirement_ids") != {task: row["requirement_id"] for task, row in declared.items()}:
        raise ValueError("complete task/requirement population changed")
    catalog = result.get("operation_catalog", {}).get("operations")
    if type(catalog) is not list or len(catalog) != len(declared) or {row["task_id"]: row for row in catalog} != declared:
        raise ValueError("complete reviewed operation catalog changed")
    graph = result.get("obligation_graph", {})
    tasks = graph.get("task_candidates")
    if type(tasks) is not list or len(tasks) != 2 or {row["candidate_id"] for row in tasks} != set(declared):
        raise ValueError("graph dropped or duplicated a declared task")
    roots = graph.get("root_obligation_ids")
    if type(roots) is not list or len(roots) != 2 or len(set(roots)) != 2:
        raise ValueError("both distinct root obligations required")
    if graph.get("current_root_id") != result["match"]["current_root_id"]:
        raise ValueError("graph changed current source root")
    typed = result["match"]["typed_intent"]
    mapping = typed["metadata"]["requirement_predicate_ids"]
    predicates = typed.get("desired_predicates")
    if (type(predicates) is not list or len(predicates) != 2
            or {row["predicate_id"] for row in predicates} != set(mapping.values())
            or graph.get("predicates") != predicates):
        raise ValueError("complete graph predicates must equal the two exact typed clauses")
    expected_roots = sorted("obligation:predicate:" + predicate for predicate in mapping.values())
    if roots != expected_roots:
        raise ValueError("graph roots differ from exact typed clause obligations")
    nodes = graph.get("nodes")
    if type(nodes) is not list:
        raise ValueError("complete typed goal and producer nodes required")
    by_node = {row["obligation_id"]: row for row in nodes}
    if len(by_node) != len(nodes):
        raise ValueError("duplicate graph nodes")
    for clause, predicate in mapping.items():
        node = by_node.get("obligation:predicate:" + predicate, {})
        status = "discharged" if clause in case["expected"]["eligible_clause_ids_after_fresh_native_check"] else "open"
        if (node.get("kind") != "goal" or node.get("predicate_id") != predicate
                or node.get("status") != status or node.get("parent_obligation_ids") != []
                or node.get("producer_id") != ""):
            raise ValueError("typed clause goal node is missing or changed")
    graph_facts, matched_facts = graph.get("facts", []), result["match"]["current_facts"]
    if (len(graph_facts) != len(matched_facts)
            or {row["fact_id"]: row for row in graph_facts} != {row["fact_id"]: row for row in matched_facts}):
        raise ValueError("graph facts differ from complete owned finite match")
    critic = result.get("critic_evidence", {})
    if critic.get("finite_match") != result["match"]:
        raise ValueError("critic lacks exact complete finite match")
    structural = critic.get("structural_evidence", {})
    if (type(structural) is not dict or structural.get("current_root_id") != result["match"]["current_root_id"]
            or structural.get("body_free") is not True or "results" not in structural or "backend_health" not in structural):
        raise ValueError("critic lost source-bound structural evidence or its unavailable coverage")
    bindings = critic.get("operation_bindings", {})
    if set(bindings) != set(declared):
        raise ValueError("critic dropped an operation binding")
    graph_tasks = {row["candidate_id"]: row for row in tasks}
    expected_nodes = set(expected_roots)
    for task_id, operation in declared.items():
        binding = bindings[task_id]
        if any(binding.get(key) != value for key, value in operation.items()):
            raise ValueError("critic operation retargeted a reviewed declaration")
        if (binding.get("predicate_id") != mapping[operation["requirement_id"]]
                or graph_tasks[task_id].get("producer_id") != operation["producer_id"]
                or binding.get("closes_obligation_ids") != graph_tasks[task_id].get("closes_obligation_ids")
                or binding.get("depends_on") != []):
            raise ValueError("reviewed operation changed predicate or graph closure")
        predicate = mapping[operation["requirement_id"]]
        if operation["requirement_id"] in case["expected"]["eligible_clause_ids_after_fresh_native_check"]:
            closure = "obligation:predicate:" + predicate
        else:
            closure = "obligation:producer:" + operation["producer_id"] + ":for:" + predicate
            producer_node = by_node.get(closure, {})
            if (producer_node.get("kind") != "producer" or producer_node.get("producer_id") != operation["producer_id"]
                    or producer_node.get("predicate_id") != predicate
                    or producer_node.get("parent_obligation_ids") != ["obligation:predicate:" + predicate]):
                raise ValueError("typed residual producer node missing or changed")
        if binding.get("closes_obligation_ids") != [closure]:
            raise ValueError("task closure is detached from exact typed clause")
        expected_nodes.add(closure)
    if set(by_node) != expected_nodes:
        raise ValueError("complete typed graph node population differs")
    expected_tasks = [task for task, row in declared.items() if row["requirement_id"] in case["expected"]["residual_clause_ids"]]
    if result.get("selected_task_ids") != expected_tasks:
        raise ValueError("selected task population differs from applicable residuals")
    candidate = result.get("candidate_plan", {})
    projected = candidate.get("tasks", [])
    effects = candidate.get("effects", [])
    if len(projected) != len(expected_tasks) or [row["task_id"] for row in projected] != expected_tasks or len(effects) != len(projected):
        raise ValueError("candidate task/effect population differs")
    for task, effect in zip(projected, effects, strict=True):
        binding = bindings[task["task_id"]]
        for name in ("producer_id", "requirement_id", "review_ref", "closes_obligation_ids", "depends_on"):
            if task.get(name) != binding[name]:
                raise ValueError("candidate task changed reviewed meaning")
        if (task.get("outputs") != [binding["path"]] or task.get("predicted_files") != [binding["path"]]
                or task.get("predicted_symbols") != [binding["function_name"]]):
            raise ValueError("candidate task selector drifted")
        if (effect.get("task_id") != task["task_id"] or effect.get("target_id") != binding["path"]
                or effect.get("operation") != binding["operation"]
                or effect.get("predicate_id") != binding["predicate_id"]
                or effect.get("requirement_id") != binding["requirement_id"] or effect.get("review_ref") != binding["review_ref"]
                or task.get("effect_ids") != [effect.get("effect_id")] or task.get("expected_effects") != [effect.get("effect_id")]):
            raise ValueError("candidate effect changed complete reviewed operation")
    if candidate.get("expected_effect_ids") != [row["effect_id"] for row in effects] or candidate.get("required_goal_ids") != roots:
        raise ValueError("candidate dropped a required goal or effect")
    critique = result.get("critique", {})
    if critique.get("accepted") is not True or critique.get("truncated") is not False:
        raise ValueError("complete native critic did not accept proposal")
    preview = result.get("preview", {})
    if preview.get("verdict") != "review_only" or preview.get("read_only") is not True or preview.get("wrote_effects") != []:
        raise ValueError("finite preview cannot admit or mutate tasks")
    stage_rows = preview.get("stage_results", [])
    stages = {row["stage"]: row for row in stage_rows}
    if len(stages) != len(stage_rows):
        raise ValueError("duplicate stage outcomes")
    if set(stages) != {"scan", "query", "evidence", "obligation", "candidate", "critique", "parallel_plan", "admission"}:
        raise ValueError("exact closed finite stage profile required")
    for name in ("scan", "query", "evidence", "obligation", "candidate", "critique"):
        if stages.get(name, {}).get("passed") is not True:
            raise ValueError("real finite planning stage did not pass: " + name)
    if (stages.get("admission", {}).get("passed") is not False
            or stages["admission"].get("blockers") != ["ir_admission_materials_absent"]):
        raise ValueError("unsupported finite behavioral admission passed")
    if capacity:
        if (stages.get("parallel_plan", {}).get("passed") is not True
                or result.get("reservation_released_on_return") is not True
                or result.get("capacity_scope") != "feasibility_during_live_reservation_only"
                or result.get("planning_model_calls") != 0 or result.get("training_steps_during_preview") != 0):
            raise ValueError("held-capacity preview scope or cleanup differs")
        if result.get("operational_model", {}).get("kernel_checked_model") is not True:
            raise ValueError("operational arithmetic model was not kernel checked")
        execution = result.get("execution_plan", {})
        if expected_tasks:
            if execution.get("admitted") is not True:
                raise ValueError("live capacity did not qualify residual schedule feasibility")
            root = result["match"]["current_root_id"]
            assignments = execution.get("assignments", [])
            if ([row.get("task_id") for row in assignments] != expected_tasks
                    or any(row.get("base_revision") != root or row.get("merge_target") != root for row in assignments)
                    or execution.get("repository_tree_id") != root
                    or execution.get("deterministic_replay", {}).get("repository_tree_id") != root):
                raise ValueError("held schedule task or source root differs from validated candidate")
            leaves = execution.get("leaf_producer_closure", {})
            if (leaves.get("closed") is not True
                    or leaves.get("required_leaf_ids") != candidate["expected_effect_ids"]
                    or leaves.get("terminal_task_ids") != expected_tasks
                    or leaves.get("producer_by_leaf_id") != {row["effect_id"]: row["task_id"] for row in effects}):
                raise ValueError("held schedule leaf effects differ from complete reviewed candidate")
            waves = execution.get("execution_waves", [])
            if ([task for wave in waves for task in wave.get("task_ids", [])] != expected_tasks
                    or [row.get("task_id") for row in execution.get("merge_order", [])] != expected_tasks
                    or execution.get("conflict_graph", {}).get("task_ids") != expected_tasks
                    or execution.get("critical_path") != expected_tasks
                    or execution.get("dependency_edges") != []):
                raise ValueError("held schedule task population or dependency changed")
        elif (execution.get("status") != "no_execution_requested" or execution.get("admitted") is not False
                or execution.get("task_ids") != []):
            raise ValueError("satisfied successor unexpectedly requested task execution")
    elif expected_tasks:
        if stages.get("parallel_plan", {}).get("passed") is not False or "parallel:stale_capacity" not in stages["parallel_plan"].get("blockers", []):
            raise ValueError("plain finite preview invented held capacity")


class SnapshotNamespaceFinder(importlib.abc.MetaPathFinder):
    """Refuse core package imports that escape explicitly supplied snapshots."""
    def __init__(self, roots: list[Path]):
        self.roots = roots

    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".", 1)[0] not in {"ipfs_accelerate_py", "ipfs_datasets_py"}:
            return None
        specification = importlib.machinery.PathFinder.find_spec(fullname, path if path is not None else [str(root) for root in self.roots])
        if specification is None:
            raise ImportError("core module absent from pinned runtime snapshot: " + fullname)
        locations = ([specification.origin] if specification.origin and specification.origin != "namespace" else []) + list(specification.submodule_search_locations or [])
        if not locations or any(not any(Path(location).resolve().is_relative_to(root) for root in self.roots) for location in locations):
            raise ImportError("core module escaped pinned runtime snapshot: " + fullname)
        return specification


def configure_snapshot(roots: list[Path]) -> None:
    for name in tuple(sys.modules):
        if name.split(".", 1)[0] in {"ipfs_accelerate_py", "ipfs_datasets_py"}:
            raise ValueError("snapshot must be configured before importing core modules")
    if not roots or any(not root.is_dir() or root.resolve() != root for root in roots):
        raise ValueError("canonical existing snapshot import roots required")
    sys.meta_path.insert(0, SnapshotNamespaceFinder(roots))


def verify_snapshot_binding(roots: list[Path], expected_sha256: str) -> dict[str, Any]:
    if not roots or len(set(roots)) != len(roots) or len({root.parent for root in roots}) != 1:
        raise ValueError("snapshot identity requires distinct canonical sibling import roots")
    qualification_root = str(Path(__file__).resolve().parents[1])
    sys.path.insert(0, qualification_root)
    try:
        verifier = importlib.import_module("release_audit.snapshot_verify")
    finally:
        sys.path.remove(qualification_root)
    result = verifier.verify_snapshot(roots[0].parent, expected_sha256, expected_roots=roots)
    implementation = Path(verifier.__file__).resolve()
    result.update({"verifier_path": str(implementation), "verifier_sha256": sha256(implementation.read_bytes())})
    return result


def external_dependency_pins(*, strict_roots: list[Path] | None = None) -> dict[str, dict[str, Any]]:
    """Pin actual loaded site-package files; late imports remain explicit."""
    paths, bounded_pins, total = {}, {}, 0
    for name, module in tuple(sys.modules.items()):
        origin = getattr(module, "__file__", None)
        if not origin:
            continue
        selected = Path(origin)
        path = selected.resolve()
        if not {"site-packages", "dist-packages"} & (set(path.parts) | set(selected.parts)):
            continue
        if not path.is_file():
            if strict_roots is not None:
                raise ValueError("loaded external dependency is not an existing regular file")
            continue
        if strict_roots is not None:
            if selected != path or any(part.is_symlink() for part in (selected, *selected.parents)):
                raise ValueError("loaded external dependency has noncanonical or symlink path")
            if path not in bounded_pins:
                if len(bounded_pins) >= MAX_FILES:
                    raise ValueError("loaded external dependency file count exceeds bounded profile")
                pin = read_file_pin(selected, roots=strict_roots)
                total += pin["size_bytes"]
                if total > MAX_TOTAL_BYTES:
                    raise ValueError("loaded external dependencies exceed total byte cap")
                bounded_pins[path] = pin
        paths.setdefault(path, []).append(name)
    pins = {}
    for path, names in sorted(paths.items()):
        if strict_roots is not None:
            pin = bounded_pins[path]
        else:
            raw = path.read_bytes()
            pin = {"sha256": sha256(raw), "size_bytes": len(raw)}
        pins[str(path)] = {"module_names": sorted(names), **pin}
    return pins


def retain_initial_external_observation(progress: dict[str, Any], existing: dict[str, dict[str, Any]]) -> None:
    previous = progress.setdefault("external_dependency_before", {})
    if "external_dependency_manifest" in progress:
        progress["external_dependency_after_initial_imports"] = existing
    else:
        for path, pin in existing.items():
            previous.setdefault(path, pin)


def native_session(output: Path, *, lean: Path, progress: dict[str, Any]) -> dict[str, Any]:
    import duckdb

    from ipfs_accelerate_py.agent_supervisor.planning import finite_integer_codebase as matcher
    from ipfs_accelerate_py.agent_supervisor.planning.finite_integer_capacity_preview import (
        preview_capacity_bound_finite_integer_plan,
    )
    from ipfs_accelerate_py.agent_supervisor.planning.finite_integer_plan_preview import (
        FiniteIntegerOperationCatalog,
        FiniteIntegerPlanPreviewError,
        ReviewedFiniteIntegerOperation,
        finite_integer_intent_cid,
        finite_integer_prompt_cid,
        preview_finite_integer_plan,
    )
    from ipfs_accelerate_py.agent_supervisor.planning.plan_revision_contracts import (
        DirtyTreePolicy,
        PlanAuthorityRoots,
        PlanCreateRequest,
        PlanRequestBudget,
        PlanRevisionStaleRootError,
        TaskSourceKind,
    )
    from ipfs_accelerate_py.agent_supervisor.planning.repository_plan_preview import (
        RepositoryPlanPreviewOwner,
    )
    from ipfs_accelerate_py.agent_supervisor.prompt.plan_create_service import (
        PlanCreateInputSnapshot,
        PlanCreatePreviewReceipt,
    )
    from ipfs_datasets_py.duckdb_control.codebase_catalog import CodebaseCatalog
    from ipfs_datasets_py.logic.software_contracts.cache import ImmutableCAS
    from ipfs_datasets_py.logic.software_contracts.codebase_finite_integer_observation import (
        FiniteIntegerObservationError,
        seal_finite_integer_tools,
    )
    from ipfs_datasets_py.logic.software_contracts.codebase_ir import (
        RepositoryCodebaseIndex,
        StaleCodebaseError,
    )
    from ipfs_datasets_py.logic.software_contracts.content import cid_for_structured
    from ipfs_datasets_py.logic.software_contracts.duckdb_ast_store import DuckDBASTStore
    from ipfs_datasets_py.logic.software_contracts.duckdb_ingest import DuckDBASTIngestor
    from ipfs_datasets_py.optimizers.logic_theorem_optimizer.resource_scheduler import (
        GlobalResourceScheduler,
        ResourceSchedulerConfig,
    )

    external_roots = [Path(root) for root in progress.get("external_dependency_manifest", {}).get("site_packages_roots", [])]
    existing = external_dependency_pins(strict_roots=external_roots or None)
    retain_initial_external_observation(progress, existing)
    deadline = time.monotonic() + 180
    def remaining():
        seconds = deadline - time.monotonic()
        if seconds <= 0:
            raise TimeoutError("180 second complete planning qualification budget exhausted")
        return min(60, seconds)
    cases = {case["scenario_id"]: case for case in scenarios()}
    repository = output / "repository"
    repository.mkdir(mode=0o700)
    for path, raw in cases["baseline"]["source_bytes"].items():
        (repository / path).write_bytes(raw)
    _git(repository, "init", "-q")
    _git(repository, "add", ".")
    _git(repository, "-c", "user.name=Qualification", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "authored planning control")
    git_head = _git(repository, "rev-parse", "HEAD")
    policy = seal_finite_integer_tools(python_executable=Path(sys.executable).resolve(), lean_executable=lean.resolve())
    progress["tool_policy"] = policy
    progress["private_state_paths"] = {"repository": str(repository), "duckdb": str(output / "codebase.duckdb"),
        "cas": str(output / "cas"), "scheduler": str(output / "resource_leases.json")}
    scheduler = GlobalResourceScheduler(ResourceSchedulerConfig.for_proof_host(state_path=output / "resource_leases.json",
        total_cpu_slots=2, total_child_process_slots=2, lane_reservations={}, auto_renew_leases=False))
    connection = duckdb.connect(str(output / "codebase.duckdb"), config={"threads": 1, "memory_limit": "64MB"})
    store, artifacts = DuckDBASTStore(connection=connection), ImmutableCAS(output / "cas")
    index = RepositoryCodebaseIndex(ingestor=DuckDBASTIngestor(store=store), artifacts=artifacts, catalog=CodebaseCatalog(store, artifacts))
    repository_id = "repository:qualification-finite-planning"
    def cleanup():
        connection.close()
        snapshot = scheduler.snapshot()
        progress["final_resource_state"] = {"active_lease_count": snapshot["active_lease_count"],
            "waiting_request_count": snapshot["waiting_request_count"]}
    try:
        head = index.prepare_current(repository, repository_id=repository_id, operation_id="planning-baseline",
            expected_head=None, scheduler=scheduler).head
    except BaseException:
        cleanup()
        raise
    catalog = FiniteIntegerOperationCatalog(operations=tuple(ReviewedFiniteIntegerOperation(**row) for row in reviewed_operations()))
    authority = {role: {"schema": "qualification-finite-authority@1", "role": role,
        "worker_allowed": False, "production_activated": False, "model_calls": 0}
        for role in ("policy", "legal", "security", "provider", "usage", "configuration")}
    authority_path, prompt_path = output / "authority.json", output / "prompt.txt"
    authority_path.write_bytes(canonical_bytes(authority) + b"\n")
    prompt_path.write_bytes(cases["baseline"]["requirements"]["original_prompt"].encode("utf-8"))
    def request_for(selected_head, document, selected_catalog):
        live = json.loads(authority_path.read_bytes())
        def cid(role):
            return cid_for_structured(live[role])
        roots = PlanAuthorityRoots(repository_id=repository_id, repository_root_cid=selected_head.snapshot_cid,
            dirty_worktree_root=selected_head.snapshot_cid,
            task_source_id=cid_for_structured({"schema": "qualification-finite-task-source@1", "catalog": selected_catalog.cid}),
            task_source_revision=selected_catalog.cid, policy_root=cid("policy"),
            intent_ir_root=finite_integer_intent_cid(document), legal_ir_root=cid("legal"), security_ir_root=cid("security"),
            program_root=index.load(selected_head.manifest_cid).semantic_state.state_cid,
            capability_catalog_root=selected_catalog.cid, provider_catalog_root=cid("provider"),
            usage_policy_root=cid("usage"), configuration_root=cid("configuration"))
        return PlanCreateRequest(prompt_source_cid=finite_integer_prompt_cid(prompt_path.read_text()),
            repository_id=repository_id, repository_root=str(repository), scope_paths=("calc.py",),
            dirty_tree_policy=DirtyTreePolicy.OBSERVE_AND_BIND, task_source_kind=TaskSourceKind.BOTH,
            board_namespace="qualification-finite-planning", alias_prefix="QFP", roots=roots,
            budget=PlanRequestBudget(max_goals=2, max_tasks=2, max_model_calls=0, max_latency_ms=int(remaining() * 1000)),
            required_analysis_operations=(), optional_analysis_operations=(), required_logic_families=(), optional_logic_families=(),
            observe_roots=True, supervisor_profile="qualification-finite-review-only", caller="principal:authored-qualification")
    results, mutations = progress.setdefault("results", {}), progress.setdefault("mutations", [])
    def arguments(case, selected_head, name):
        document = matcher.build_finite_integer_intent(case["requirements"]["original_prompt"])
        request = request_for(selected_head, document, catalog)
        def observer(bound):
            if bound != request or prompt_path.read_bytes() != case["requirements"]["original_prompt"].encode("utf-8"):
                raise ValueError("exact request/prompt changed during policy observation")
            fresh = request_for(selected_head, document, catalog)
            fresh.roots.require_current(bound.roots)
            return fresh.roots
        return {"owner": RepositoryPlanPreviewOwner(index=index, repository=repository, expected_head=selected_head,
            scheduler=scheduler, timeout_seconds=remaining(), memory_mb=1024), "request": request,
            "intent_document": document, "source_text": case["requirements"]["original_prompt"],
            "operation_catalog": catalog, "output": output / name, "tool_policy": policy, "policy_observer": observer}
    def invoke(case, selected_head, name, *, capacity=True):
        result = (preview_capacity_bound_finite_integer_plan if capacity else preview_finite_integer_plan)(**arguments(case, selected_head, name))
        (output / f"{name}.json").write_bytes(canonical_bytes(result) + b"\n")
        if result["result_cid"] != cid_for_structured({key: value for key, value in result.items() if key != "result_cid"}):
            raise AssertionError("complete planning result identity differs")
        PlanCreatePreviewReceipt.from_dict(result["preview"])
        PlanCreateInputSnapshot.from_dict(result["input_snapshot"])
        assert_planning_crossing(result, case, capacity=capacity)
        results[name] = {"result_path": str(output / f"{name}.json"), "result_cid": result["result_cid"],
            "stage_results": result["preview"]["stage_results"], "selected_task_ids": result["selected_task_ids"],
            "declared_task_requirement_ids": result["declared_task_requirement_ids"], "current_facts_count": result["current_facts_count"],
            "execution_plan_status": result.get("execution_plan", {}).get("status"),
            "execution_plan_feasibility_admitted": result.get("execution_plan", {}).get("admitted"),
            "operational_model_status": result.get("operational_model", {}).get("status"),
            "requested_model_theorem_proved": result.get("operational_model", {}).get("requested_model_theorem_proved"),
            "production_admitted": False, "worker_launched": False}
        return result
    try:
        first = invoke(cases["baseline"], head, "baseline_plain", capacity=False)
        held = invoke(cases["baseline"], head, "baseline_capacity")
        if held["match"]["eligible_clause_ids"] != first["match"]["eligible_clause_ids"]:
            raise AssertionError("held capacity changed finite fact meaning")
        for mutation in ("selector_scope", "retarget_catalog", "clause_identity", "task_population"):
            args = arguments(cases["baseline"], head, "refusal_" + mutation)
            try:
                if mutation == "selector_scope":
                    args["request"] = replace(args["request"], scope_paths=("decoy.py",))
                elif mutation == "retarget_catalog":
                    changed = FiniteIntegerOperationCatalog(operations=tuple(replace(row, path="decoy.py") for row in catalog.operations))
                    args["operation_catalog"] = changed
                    args["request"] = replace(args["request"], roots=replace(args["request"].roots, capability_catalog_root=changed.cid))
                elif mutation == "clause_identity":
                    args["intent_document"] = matcher.build_finite_integer_intent(cases["changed_requirement"]["requirements"]["original_prompt"])
                else:
                    args["operation_catalog"] = FiniteIntegerOperationCatalog(operations=(catalog.operations[0],))
                preview_capacity_bound_finite_integer_plan(**args)
            except (FiniteIntegerPlanPreviewError, matcher.FiniteIntegerIntentError) as exc:
                mutations.append({"mutation_id": mutation, "refused": True, "exception": type(exc).__name__,
                    "message": str(exc), "owned_output_created": args["output"].exists(), "production_admitted": False})
            else:
                raise AssertionError("changed exact crossing declaration accepted: " + mutation)
        for mutation in ("policy_root", "source_bytes", "finite_artifact"):
            args = arguments(cases["baseline"], head, "refusal_" + mutation)
            original = args["policy_observer"]
            changed = []
            def observer(bound, operation=mutation, invocation=args, previous=original, recorded=changed):
                target = invocation["output"] / "finite-observation" / "FiniteInteger.olean"
                if target.exists() and not recorded:
                    if operation == "policy_root":
                        altered = json.loads(authority_path.read_bytes())
                        altered["policy"]["revision"] = "drifted-during-observation"
                        authority_path.write_bytes(canonical_bytes(altered) + b"\n")
                        recorded.append({"path": str(authority_path), "mutation": operation})
                    else:
                        target = repository / "calc.py" if operation == "source_bytes" else target
                        before = target.read_bytes()
                        after = source_function(9) if operation == "source_bytes" else before + b"authored-corruption"
                        target.write_bytes(after)
                        recorded.append({"path": str(target), "before_sha256": sha256(before), "after_sha256": sha256(after)})
                return previous(bound)
            args["policy_observer"] = observer
            try:
                preview_capacity_bound_finite_integer_plan(**args)
            except (PlanRevisionStaleRootError, StaleCodebaseError, FiniteIntegerObservationError, matcher.FiniteIntegerIntentError) as exc:
                if not changed:
                    raise AssertionError("mutation failed before its genuine owned boundary") from exc
                mutations.append({"mutation_id": mutation, "refused": True, "exception": type(exc).__name__,
                    "message": str(exc), "changes": changed, "owned_output_created": args["output"].exists(), "production_admitted": False})
            else:
                raise AssertionError("genuine source/evidence/policy drift accepted: " + mutation)
            finally:
                authority_path.write_bytes(canonical_bytes(authority) + b"\n")
                (repository / "calc.py").write_bytes(source_function())
            snapshot = scheduler.snapshot()
            if snapshot["active_lease_count"] or snapshot["waiting_request_count"]:
                raise AssertionError("refused planning crossing leaked leases")
        (repository / "calc.py").write_bytes(source_function(2))
        if _git(repository, "rev-parse", "HEAD") != git_head:
            raise AssertionError("source edit changed authored Git HEAD")
        try:
            preview_capacity_bound_finite_integer_plan(**arguments(cases["baseline"], head, "stale_source"))
        except StaleCodebaseError as exc:
            mutations.append({"mutation_id": "same_head_old_generation", "refused": True, "exception": type(exc).__name__,
                "message": str(exc), "production_admitted": False})
        else:
            raise AssertionError("old planning source generation accepted dirty successor")
        successor = index.prepare_current(repository, repository_id=repository_id, operation_id="planning-successor",
            expected_head=head, scheduler=scheduler).head
        second = invoke(cases["successor"], successor, "successor_capacity")
        if first["match"]["current_root_id"] == second["match"]["current_root_id"]:
            raise AssertionError("successor source root did not change")
        snapshot = scheduler.snapshot()
        if snapshot["active_lease_count"] or snapshot["waiting_request_count"]:
            raise AssertionError("planning qualification leaked leases or waiters")
        progress.update({"status": "passed", "results": results, "mutations": mutations, "tool_policy": policy,
            "original_requirements_unchanged": first["operation_catalog"] == second["operation_catalog"],
            "complete_declared_task_population_preserved": first["declared_task_requirement_ids"] == second["declared_task_requirement_ids"],
            "git_head_before_and_after": git_head, "zero_leases_and_waiters": True,
            "overall_timeout_seconds": 180, "per_crossing_timeout_seconds": 60,
            "scheduler_cpu_slots": 2, "scheduler_process_slots": 2, "native_owner_memory_mb": 1024,
            "signed_behavioral_admission": "unsupported_by_current_finite_profile",
            "worker_launch": "not_authorized_by_review_only_preview", "production_qualified": False})
        return progress
    finally:
        cleanup()


def run(output: Path, *, lean: Path, snapshot_roots: list[Path] | None = None,
        external_manifest: Path | None = None, snapshot_sha256: str | None = None) -> dict[str, Any]:
    output = output.resolve()
    if output.exists():
        raise ValueError("planning output must be a fresh private directory")
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    roots, before = [], {}
    report = {"schema": "codebase-ir-finite-planning-qualification@1", "status": "incomplete",
        "started_at": datetime.now(UTC).isoformat(), "output": str(output), "production_qualified": False,
        "runtime_snapshot_roots": [str(root) for root in snapshot_roots or []],
        "requested_runtime_snapshot_sha256": snapshot_sha256,
        "runtime_source_mode": "pinned_snapshot" if snapshot_roots else "working_tree_observed",
        "python_executable": str(Path(sys.executable).resolve()), "python_prefix": sys.prefix,
        "external_dependency_profile": "interpreter_site_packages_observed",
        "runtime_dependency_closure_proven": False}
    try:
        report["native_planning"] = {"status": "incomplete"}
        if external_manifest:
            pins, metadata = capture_external_manifest(external_manifest)
            report["external_dependency_profile"] = "interpreter_site_packages_explicit_observed_manifest"
            report["external_dependency_manifest"] = metadata
            report["native_planning"].update({"external_dependency_before": pins, "external_dependency_manifest": metadata})
        if snapshot_sha256 is not None:
            report["runtime_snapshot_before"] = verify_snapshot_binding(snapshot_roots or [], snapshot_sha256)
        if snapshot_roots:
            configure_snapshot(snapshot_roots)
        roots, before = native_source_snapshot()
        report["native_planning"] = native_session(output, lean=lean, progress=report["native_planning"])
        report["status"] = "passed"
    except ImportError as exc:
        report["status"] = "unavailable"
        report["error"] = f"{type(exc).__name__}: {exc}"
    except Exception as exc:
        report["status"] = "failed"
        report["error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        report["finished_at"] = datetime.now(UTC).isoformat()
        if snapshot_sha256 is not None:
            try:
                report["runtime_snapshot_after"] = verify_snapshot_binding(snapshot_roots or [], snapshot_sha256)
                report["runtime_snapshot_identity_stable"] = report.get("runtime_snapshot_before") == report["runtime_snapshot_after"]
                if not report["runtime_snapshot_identity_stable"]:
                    raise ValueError("snapshot identity or verifier bytes changed during run")
            except (ValueError, OSError) as exc:
                report["status"] = "snapshot_integrity_refused"
                report["runtime_snapshot_identity_stable"] = False
                report["runtime_snapshot_error"] = f"{type(exc).__name__}: {exc}"
        report["imported_native_sources"] = imported_native_sources(roots, before)
        report["imported_native_source_bytes_stable"] = bool(report["imported_native_sources"]) and all(row["unchanged"] for row in report["imported_native_sources"])
        previous = report.get("native_planning", {}).get("external_dependency_before", {})
        try:
            following = external_dependency_pins(strict_roots=interpreter_site_roots() if external_manifest else None)
            report["external_dependency_pins"] = compare_external_pins(previous, following, roots=interpreter_site_roots()) if external_manifest else [
                {"path": path, "before": previous.get(path), "after": pin,
                "unchanged": previous.get(path) == pin, "late_import": path not in previous}
                for path, pin in following.items()]
        except (ValueError, OSError) as exc:
            following = {}
            report["status"] = "external_dependency_refused"
            report["external_dependency_error"] = f"{type(exc).__name__}: {exc}"
            report["external_dependency_pins"] = []
        report["observed_external_dependency_bytes_stable"] = bool(following) and all(
            pin["unchanged"] for pin in report["external_dependency_pins"])
        if report["status"] == "passed" and not report["imported_native_source_bytes_stable"]:
            report["status"] = "source_changed_during_run"
        (output / "planning_qualification.json").write_bytes(canonical_bytes(report) + b"\n")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--lean", type=Path, required=True)
    parser.add_argument("--snapshot-root", type=Path, action="append", help="explicit immutable core package import root; repeat for each repository snapshot")
    parser.add_argument("--snapshot-sha256", help="release generation canonical identity; verifies exact bounded sealed file set before and after")
    parser.add_argument("--external-manifest", type=Path, help="bounded previously observed interpreter file manifest; pre-read bytes without importing")
    args = parser.parse_args(argv)
    try:
        result = run(args.output, lean=args.lean, snapshot_roots=args.snapshot_root, external_manifest=args.external_manifest,
            snapshot_sha256=args.snapshot_sha256)
    except (ValueError, OSError, AssertionError) as exc:
        parser.exit(2, f"planning qualification failed; retained report: {exc}\n")
    print(json.dumps({"status": result["status"], "report": str(args.output.resolve() / "planning_qualification.json"), "production_qualified": False}, sort_keys=True))
    return 0 if result["status"] == "passed" else 3


if __name__ == "__main__":
    raise SystemExit(main())
