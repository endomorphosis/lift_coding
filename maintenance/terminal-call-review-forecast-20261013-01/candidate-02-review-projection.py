"""Project the three conditional caller reviews without proposing mutations.

This is a pure, content-bound projection of typed planning declarations and a
selected task population. It verifies their agreement, not live repository,
proof, portfolio, scheduler, or execution authority. The owner adapter must
separately authenticate those origins and retain its current-source guards.
"""
from __future__ import annotations

import json

from ipfs_datasets_py.duckdb_control.codebase_catalog import CodebaseHead
from ipfs_datasets_py.logic.software_contracts.content import cid_for_structured
from ipfs_accelerate_py.agent_supervisor.planning.adaptive_planner import FrozenPlanningGoal
from ipfs_accelerate_py.agent_supervisor.planning.obligation_graph_compiler import (
    ObligationGraph, ObligationGraphCompiler, ObligationStatus, ProducerRule,
    TaskCandidate, TypedIntent, TypedPredicate, obligation_id_for_producer,
)
from ipfs_accelerate_py.agent_supervisor.planning.plan_evaluator import EvidenceAwarePlanPolicy
from ipfs_accelerate_py.agent_supervisor.planning.plan_revision_contracts import (
    DirtyTreePolicy, PlanCreateRequest, PlanRequestBudget, TaskSourceKind,
)
from ipfs_accelerate_py.agent_supervisor.prompt.plan_create_service import (
    PlanCreateMaterials, freeze_plan_create_input_snapshot,
)

from . import terminal_call_intent_planning as intent_planning
from . import terminal_call_proof_capsule as capsules
from . import terminal_revision_proof_cache as revisions
from .terminal_call_review_capacity import task_resource_profile


SCHEMA = "terminal-call-review-projection@1"
ESTIMATED_DURATION_MS = 1000
AUTHORITY = {**intent_planning.AUTHORITY, **{name: False for name in (
    "capsule_origin_verified", "current_head_verified", "selected_portfolio_origin_verified",
    "scheduler_lease_held", "task_execution_qualified", "logical_review_goals_completed",
    "parallel_execution_admitted",
)}}


def _need(condition, message):
    if not condition:
        raise ValueError(message)


def _wire(value):
    return intent_planning._wire(value)


def _copy(value):
    return json.loads(_wire(value))


def _same(actual, expected, message):
    _need(_wire(actual) == _wire(expected), message)


def _capsule(materials):
    """Invert U's explicit, lossless prompt-reference field projection."""
    _need(type(materials.extra) is dict and intent_planning.MATERIAL_KEY in materials.extra,
          "complete conditional capsule material required")
    projected = _copy(materials.extra[intent_planning.MATERIAL_KEY])
    _need(type(projected) is dict and projected.get("schema")
          == "terminal-call-proof-capsule-planner-projection@1",
          "exact planner capsule projection required")
    _need("projection_id" in projected and "source_capsule_id" in projected
          and type(projected.get("intent")) is dict
          and "prompt_reference" in projected["intent"] and "prompt" not in projected["intent"],
          "complete reversible capsule projection required")
    projection_id = projected.pop("projection_id")
    _need(projection_id == cid_for_structured(projected), "planner capsule identity differs")
    _same(projected.pop("reference_field_mapping", None),
          {"intent.prompt": "intent.prompt_reference"}, "capsule reference mapping differs")
    projected["schema"] = capsules.SCHEMA
    projected["capsule_id"] = projected.pop("source_capsule_id")
    projected["intent"]["prompt"] = projected["intent"].pop("prompt_reference")
    fields = {"schema", "head", "conditional_model_claim", "scope", "intent", "model",
        "source_closure", "assumptions", "checker_dependencies", "coverage", "residuals",
        "opaque_call_model_assumption", "native_call_opacity_preserved", "expansion", "producer",
        "training_steps", "provider_calls", "new_prover_invocations", "source_body_executed",
        "capsule_id", *capsules.AUTHORITY}
    _need(set(projected) == fields, "closed complete capsule fields required")
    capsules._check_identity(projected, "capsule_id")
    _same(CodebaseHead.from_dict(projected["head"]).to_dict(), projected["head"],
          "exact complete native capsule head required")
    _need(all(projected[name] is False for name in capsules.AUTHORITY)
          and projected["source_body_executed"] is False
          and projected["conditional_model_claim"] is True
          and projected["opaque_call_model_assumption"] is True
          and projected["native_call_opacity_preserved"] is True,
          "conditional capsule authority ceilings differ")
    _need(all(type(projected[name]) is int and projected[name] == 0
              for name in ("training_steps", "provider_calls", "new_prover_invocations")),
          "capsule counters must remain exactly zero")
    _same(intent_planning.project_call_proof_capsule_for_planning(projected),
          materials.extra[intent_planning.MATERIAL_KEY], "capsule projection is not reversible")
    return projected


def _declarations(request, materials, capsule):
    head, intent = capsule["head"], capsule["intent"]
    paths = capsule["source_closure"]["paths"]
    _need(type(paths) is list and len(paths) >= 2 and paths == sorted(set(paths)),
          "complete ordered source scope required")
    expected_request = PlanCreateRequest(
        prompt_source_cid=cid_for_structured({"schema": "call-prompt-reference@1", **intent["prompt"]}),
        repository_id=head["repository_id"], repository_root=request.repository_root,
        scope_paths=tuple(paths), dirty_tree_policy=DirtyTreePolicy.OBSERVE_AND_BIND,
        task_source_kind=TaskSourceKind.BOTH, board_namespace="conditional-call-review", alias_prefix="CCR",
        roots=request.roots, budget=PlanRequestBudget(max_goals=3, max_tasks=3, max_model_calls=0,
            max_provider_tokens=0, max_latency_ms=90_000, max_ready_width=1),
        required_analysis_operations=(), optional_analysis_operations=(), required_logic_families=(),
        optional_logic_families=(), observe_roots=True, supervisor_profile="conditional-call-evidence-preview",
        caller="principal:authored-qualification")
    _same(request.to_dict(), expected_request.to_dict(), "request differs from the closed caller review profile")
    _need(request.roots.repository_root_cid == head["snapshot_cid"]
          and request.roots.dirty_worktree_root == head["snapshot_cid"]
          and request.roots.intent_ir_root == intent_planning.intent_root(intent),
          "request, capsule head and intent roots differ")
    binding = cid_for_structured({"schema": "conditional-call-review-binding@1", "capsule": capsule,
        "intent_profile_id": intent["profile_id"], "head": head, "scope": paths,
        "operations": [list(item) for item in intent_planning.OPERATIONS]})
    refs = (capsule["capsule_id"], intent["profile_id"], capsule["model"]["model_record_result_cid"])
    goals, producers, candidates = [], [], []
    for operation, _ in intent_planning.OPERATIONS:
        goal = TypedPredicate("goal:call-review:" + operation, "conditional_model_review_requirement",
            head["snapshot_cid"], object_ref=cid_for_structured({"complete_binding": binding,
                "operation": operation}), provenance_refs=refs)
        producer = ProducerRule("producer:call-review:" + operation, (goal.predicate_id,), provenance_refs=refs)
        task = TaskCandidate("task:call-review:" + operation,
            (obligation_id_for_producer(producer.producer_id, goal.predicate_id),),
            producer_id=producer.producer_id,
            depends_on_candidate_ids=(() if not candidates else (candidates[-1].candidate_id,)), provenance_refs=refs)
        goals.append(goal); producers.append(producer); candidates.append(task)
    expected_intent = TypedIntent("intent:conditional-call-review", tuple(goals), refs,
        current_root_id=head["snapshot_cid"])
    _same(materials.intent.to_dict(), expected_intent.to_dict(), "complete typed review goals differ")
    _same([item.to_dict() for item in materials.producers], [item.to_dict() for item in producers],
          "exact review producer declarations differ")
    _same([item.to_dict() for item in materials.task_candidates], [item.to_dict() for item in candidates],
          "exact review candidates or dependency chain differ")
    policy = EvidenceAwarePlanPolicy(acceptance_criteria=expected_intent.goal_predicate_ids,
        evidence_terms=refs, allowed_scopes=("scope:call-review",), available_resource_classes=("cpu",),
        require_validation=True, require_proof=False)
    expected_goal = FrozenPlanningGoal("goal:conditional-call-review", binding, head["snapshot_cid"], policy)
    _need(type(materials.frozen_goal) is FrozenPlanningGoal, "exact typed frozen review goal required")
    _same(materials.frozen_goal.to_dict(), expected_goal.to_dict(), "frozen review policy differs")
    context = {"domain": "conditional_call_evidence_review", "repository_paths": paths,
        "complete_binding": binding, "task_metadata": {task.candidate_id: {
            "predicted_files": paths, "scope_ids": ["scope:call-review"], "resource_classes": ["cpu"],
            "meaning": meaning} for task, (_, meaning) in zip(candidates, intent_planning.OPERATIONS)}}
    _need(type(materials.candidate_context) is dict, "complete candidate context required")
    for name, value in context.items():
        _same(materials.candidate_context.get(name), value, "authored review context differs")
    _need(materials.extra.get("complete_binding") == binding, "whole capsule material binding differs")
    return binding, goals, producers, candidates


def _build(*, request, materials, selected_task_ids, obligation_graph):
    """Bind exact selected reviews without producing files, facts or authority.

    The supplied capsule's identity is checked, not its external origin. Scan
    and other live owner enrichments are retained in the frozen material
    binding. They cannot inject observations or replace the closed typed
    goals, producers, candidates, or policy.
    """
    _need(type(request) is PlanCreateRequest and type(materials) is PlanCreateMaterials
          and type(materials.intent) is TypedIntent and type(obligation_graph) is ObligationGraph,
          "exact native request, materials, intent and obligation graph required")
    _need(type(selected_task_ids) in (list, tuple), "exact selected task population required")
    declared_inputs = _wire({"request": request.to_dict(), "selected_task_ids": list(selected_task_ids),
        "obligation_graph": obligation_graph.to_dict()})
    _need(type(materials.current_facts) is tuple and not materials.current_facts
          and materials.model_provider is None and materials.current_roots is None
          and materials.obligation_graph is None and materials.evidence_bundle is None
          and materials.admission_materials is None and not materials.evidence_adapters
          and not materials.evidence_queries and materials.parallel_request is None
          and materials.parallel_tasks is None and materials.query_plan is None
          and materials.workflow_request is None and materials.predicates == (),
          "review inputs cannot inject facts, providers or execution stages")
    _need(type(materials.producers) is tuple and type(materials.task_candidates) is tuple
          and all(type(item) is ProducerRule for item in materials.producers)
          and all(type(item) is TaskCandidate for item in materials.task_candidates),
          "exact immutable review declarations required")
    before = freeze_plan_create_input_snapshot(request, materials=materials)
    _need(before.material_binding.get("reuse_supported") is True,
          "all bound native planning materials must have semantic identities")
    capsule = _capsule(materials)
    binding, goals, producers, candidates = _declarations(request, materials, capsule)
    selected = [item.candidate_id for item in candidates]
    _need(type(selected_task_ids) in (list, tuple) and len(selected_task_ids) == 3
          and all(type(item) is str for item in selected_task_ids)
          and list(selected_task_ids) == selected, "exact three ordered selected review tasks required")
    regenerated = ObligationGraphCompiler().compile(materials.intent, current_facts=(),
        producers=materials.producers, task_candidates=materials.task_candidates, predicates=(),
        current_root_id=request.roots.dirty_worktree_root)
    _same(obligation_graph.to_dict(), regenerated.to_dict(), "actual obligation graph differs from typed review inputs")
    _need(not obligation_graph.facts and all(node.status is not ObligationStatus.DISCHARGED
        for node in obligation_graph.nodes), "review graph cannot claim completed obligations")
    expansion_id = cid_for_structured(capsule["expansion"])
    read_handles = {"capsule_id": capsule["capsule_id"], "head_snapshot_cid": capsule["head"]["snapshot_cid"],
        "source_paths": capsule["source_closure"]["paths"], "proof_expansion_cid": expansion_id}
    tasks, actions = [], []
    leaves = [goal.predicate_id for goal in goals]
    for task, goal, producer in zip(candidates, goals, producers):
        tasks.append({"task_id": task.candidate_id, "action_id": task.candidate_id,
            "producer_id": producer.producer_id, "goal_id": goal.predicate_id,
            "closes_obligation_ids": list(task.closes_obligation_ids),
            "depends_on": list(task.depends_on_candidate_ids), "produces": [goal.predicate_id],
            "required_leaf_ids": [goal.predicate_id], "outputs": [], "effects": [],
            "changed_paths": [], "predicted_paths": [], "review_only": True, "worktree_policy": "none",
            "resource_contract": task_resource_profile(), "estimated_duration_ms": ESTIMATED_DURATION_MS,
            "duration_semantics": "bounded_forecast_not_observed_execution",
            "read_only_inputs": _copy(read_handles), "completion_facts": []})
        actions.append({"action_id": task.candidate_id, "depends_on": list(task.depends_on_candidate_ids),
            "producer_id": producer.producer_id, "goal_id": goal.predicate_id,
            "produces": [goal.predicate_id], "effects": [], "review_only": True})
    body = {"schema": SCHEMA, "request": request.to_dict(), "request_cid": request.request_cid,
        "material_snapshot_cid": before.snapshot_cid,
        "material_binding": _copy(before.to_dict()["material_binding"]),
        "source_capsule_id": capsule["capsule_id"], "head": capsule["head"], "complete_binding": binding,
        "obligation_graph": obligation_graph.to_dict(), "selected_task_ids": selected,
        "tasks": tasks, "actions": actions, "required_leaf_ids": leaves,
        "read_only_inputs": {"capsule": _copy(materials.extra[intent_planning.MATERIAL_KEY]),
            "proof_expansion": capsule["expansion"], "proof_expansion_cid": expansion_id,
            "source_closure": capsule["source_closure"]},
        "outputs": [], "effects": [], "changed_paths": [], "predicted_paths": [],
        "current_facts": [], "completion_facts": [], "completed_task_ids": [],
        "review_only": True, "worktree_policy": "none", "projection_data_validated": True,
        "producer_origin_scope": "supplied_typed_inputs_only_not_live_owner_or_portfolio_authentication",
        "training_steps": 0, "provider_calls": 0, "new_prover_invocations": 0, **AUTHORITY}
    result = _copy({**body, "plan_id": cid_for_structured(body)})
    after = freeze_plan_create_input_snapshot(request, materials=materials)
    _same(after.to_dict(), before.to_dict(), "native review materials changed during projection")
    _need(declared_inputs == _wire({"request": request.to_dict(),
        "selected_task_ids": list(selected_task_ids), "obligation_graph": obligation_graph.to_dict()}),
        "selected task population or actual graph changed during projection")
    return result


@revisions._without_metadata
def build_call_review_projection(*, request, materials, selected_task_ids, obligation_graph):
    """Return the complete no-write review projection from exact typed inputs."""
    try:
        return _build(request=request, materials=materials, selected_task_ids=selected_task_ids,
            obligation_graph=obligation_graph)
    except (KeyError, TypeError, AttributeError) as exc:
        raise ValueError("malformed closed caller review inputs") from exc


def validate_call_review_projection(projection, *, request, materials, selected_task_ids, obligation_graph):
    """Replay every review field against the same complete external inputs."""
    replayed = build_call_review_projection(request=request, materials=materials,
        selected_task_ids=selected_task_ids, obligation_graph=obligation_graph)
    _same(projection, replayed, "complete read-only review projection differs from replay")
    return {"schema": "terminal-call-review-projection-validation@1", "data_validated": True,
        "plan_id": replayed["plan_id"], "material_snapshot_cid": replayed["material_snapshot_cid"],
        **AUTHORITY}
