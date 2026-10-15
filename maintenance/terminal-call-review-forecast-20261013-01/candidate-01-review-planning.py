"""Current conditional evidence through a native, zero-width review forecast.

Only the task projection and parallel compilation wiring change. Native scan,
evidence, obligations, candidates, critique, admission and verdict remain in the
real service. Compiler acceptance is never worker or completion authority.
"""
from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import sys
from types import SimpleNamespace

from ipfs_datasets_py.logic.software_contracts.content import cid_for_structured
from ipfs_datasets_py.duckdb_control.codebase_catalog import CodebaseHead
from ipfs_accelerate_py.agent_supervisor.planning.plan_revision_contracts import PlanAuthorityRoots
from ipfs_accelerate_py.agent_supervisor.planning import repository_plan_preview as native_preview
from ipfs_accelerate_py.agent_supervisor.planning import codebase_source_delta_context as native_checks
from ipfs_accelerate_py.agent_supervisor.planning import parallel_plan_compiler as parallel
from ipfs_accelerate_py.agent_supervisor.prompt import plan_create_service as service

from . import terminal_call_intent_planning as previous
from . import terminal_call_proof_capsule as capsules
from . import terminal_call_review_projection as projections
from . import terminal_call_review_capacity as capacity
from . import terminal_call_ir_composition as composition
from . import terminal_revision_metadata as metadata
from . import terminal_revision_proof_cache as revisions

SCHEMA = "terminal-call-review-forecast-preview@1"
CAPACITY_KEY = "conditional_call_review_capacity"
AUTHORITY = {**previous.AUTHORITY, "review_task_completion_proved": False,
    "full_task_satisfaction": False, "original_task_budget_satisfied": False}


def _need(value, message):
    if not value:
        raise ValueError(message)


def _wire(value):
    return native_checks._wire(value)


@revisions._without_metadata
def build_call_review_plan_basis(*, prompt, intent_profile, model_record, query,
        callee_proof, repository, policy_roots):
    """Pure complete pre-capacity inputs; establish no current owner or lease."""
    basis = dict(prompt=prompt, intent_profile=intent_profile, model_record=model_record,
        query=query, callee_proof=callee_proof)
    capsule = capsules.build_call_proof_capsule(**basis)
    request, materials = previous.build_call_intent_plan_inputs(capsule=capsule,
        repository=repository, policy_roots=policy_roots, **basis)
    _need(request.roots.configuration_root == cid_for_structured(capacity.capacity_configuration_profile()),
        "complete fixed review-capacity configuration root differs")
    snapshot = service.freeze_plan_create_input_snapshot(request, materials=materials)
    binding = {"schema": capacity.BINDING_SCHEMA, "head": model_record["head"],
        "request_cid": request.request_cid, "material_basis_cid": snapshot.snapshot_cid,
        "capsule_id": capsule["capsule_id"]}
    return request, materials, binding


class CallReviewForecastService(service.PlanCreateService):
    """Trusted application wiring around genuine native planning stages."""

    def __init__(self, *, capacity_control, binding, request, materials, **kwargs):
        _need(type(capacity_control) is capacity.CallReviewCapacity,
            "exact live review-capacity control required")
        capacity_control.require_current(binding=binding)
        self.capacity_control = capacity_control
        self.review_binding = json.loads(_wire(binding))
        self.authored_request = request
        self.authored_materials = materials
        self.observed_projection = None
        self.observed_selected_tasks = None
        self.observed_parallel_plan = None
        self.observed_compilation_request = None
        super().__init__(**kwargs)

    def _stage_candidate(self, request, materials, obligation, *, mode, snapshot):
        _need(request == self.authored_request and mode is service.PlanCreateMode.DETERMINISTIC,
            "exact model-off review request required")
        self.capacity_control.require_current(binding=self.review_binding)
        _need(_wire(materials.extra.get(CAPACITY_KEY)) == _wire(self.capacity_control.public_dict()),
            "consumed capacity differs from original held observation")
        _need(service.freeze_plan_create_input_snapshot(request, materials=materials) == snapshot,
            "native consumed review materials differ")
        self.actual_materials = materials
        self.actual_snapshot = snapshot
        return super()._stage_candidate(request, materials, obligation, mode=mode, snapshot=snapshot)

    def _candidate_plan_projection(self, request, portfolio, obligation):
        # Observe genuine native candidate selection before replacing its
        # generic update-to-first-source projection with truthful review tasks.
        super()._candidate_plan_projection(request, portfolio, obligation)
        selected = getattr(portfolio, "selected", None)
        symbolic = getattr(selected, "symbolic_candidate", None)
        selected_ids = list(getattr(symbolic, "task_candidate_ids", ()))
        value = projections.build_call_review_projection(request=request, materials=self.actual_materials,
            selected_task_ids=selected_ids, obligation_graph=obligation)
        _need(value["material_snapshot_cid"] == self.actual_snapshot.snapshot_cid,
            "review projection did not bind the actual native input snapshot")
        self.observed_selected_tasks = selected_ids
        self.observed_projection = json.loads(_wire(value))
        return value

    def _stage_parallel_plan(self, request, materials, candidate_plan):
        _need(request == self.authored_request and materials is self.actual_materials
            and _wire(candidate_plan) == _wire(self.observed_projection),
            "parallel compilation requires the exact native selected review projection")
        self.capacity_control.require_current(binding=self.review_binding)
        snapshot = service.freeze_plan_create_input_snapshot(request, materials=materials)
        _need(snapshot == self.actual_snapshot, "complete review materials changed before compile")
        plan = self.capacity_control.compile(candidate_plan["tasks"],
            repository_snapshot={"tree_id": request.roots.dirty_worktree_root,
                "repository_tree_id": request.roots.dirty_worktree_root,
                "head": self.review_binding["head"], "program_root": request.roots.program_root,
                "candidate_plan_id": candidate_plan["plan_id"], "candidate_plan_cid": cid_for_structured(candidate_plan),
                "input_snapshot_cid": snapshot.snapshot_cid},
            bound_material_snapshot_cid=snapshot.snapshot_cid,
            required_leaf_ids=tuple(candidate_plan["required_leaf_ids"]))
        _need(type(plan) is parallel.ParallelExecutionPlan
            and plan.outcome is parallel.ParallelPlanOutcome.REVIEW_ONLY
            and plan.admitted_width == 0 and not plan.execution_waves and not plan.assignments
            and not plan.merge_order and not plan.issues and plan.leaf_producer_closure.closed,
            "native compiler must accept only a complete zero-work review forecast")
        self.observed_parallel_plan = json.loads(_wire(plan.to_dict(include_replay_request=True)))
        self.observed_compilation_request = self.capacity_control.last_compilation_request
        self.capacity_control.require_current(binding=self.review_binding)
        return service.PlanCreateStageResult(stage=service.PlanCreateStage.PARALLEL_PLAN,
            artifact_cid=service._record_cid(plan, fallback_namespace="parallel"), passed=True,
            message="native review-only parallel forecast; zero execution width"), plan


@revisions._without_metadata
def preview_current_call_review_plan(*, index, repository: Path, expected_head, tool_policy,
        prompt, intent_profile, model_record, query, callee_proof, policy_roots,
        policy_observer, scheduler, capacity_control):
    """Current proof custody plus genuine native review-only service evaluation.

    A trusted application must hold the exact capacity control until return.
    Neither a serialized capacity dictionary nor an accepted compiler forecast
    grants execution/admission authority. No checker, worker, model or source
    body executes here; every later use requires fresh current validation.
    """
    _need(type(capacity_control) is capacity.CallReviewCapacity and callable(policy_observer)
        and type(expected_head) is CodebaseHead and type(policy_roots) is PlanAuthorityRoots,
        "exact live capacity and independent policy observer required")
    inputs = dict(prompt=prompt, intent_profile=intent_profile, model_record=model_record,
        query=query, callee_proof=callee_proof)
    before = _wire(inputs)
    controls = _wire({"tool_policy": tool_policy, "expected_head": expected_head.to_dict(),
        "policy_roots": policy_roots.to_dict()})
    modules = [sys.modules[__name__], previous, capsules, projections, capacity, composition,
        native_preview, native_checks, service, parallel]
    projection = query["rows"]["call_ir_projections"][0]["payload"]
    declarations = [*projection["producer"]["files"], *projection["callee_projection"]["producer"]["files"],
        *query["producer"]["files"], *model_record["adapter_pins"].values(),
        *model_record["callee"]["integration_adapters"].values()]
    declared = {}
    for pin in declarations:
        _need(pin["path"] not in declared or _wire(declared[pin["path"]]) == _wire(pin),
            "selected review producer declarations disagree")
        declared[pin["path"]] = pin
    modules.extend(SimpleNamespace(__file__=path) for path in sorted(declared))
    with metadata._producer(modules) as (producer, producer_guard):
        actual_pins = {pin["path"]: pin for pin in producer["files"]}
        _need(all(_wire(actual_pins[path]) == _wire(pin) for path, pin in declared.items()),
            "selected review producer differs")
        _, source_guard = revisions._capture(repository, model_record["paths"], expected_head.repository_id)
        artifact_guards = previous._retain_model_artifacts(model_record, callee_proof)
        request, authored_materials, binding = build_call_review_plan_basis(repository=repository,
            policy_roots=policy_roots, **inputs)
        _need(_wire(binding["head"]) == _wire(expected_head.to_dict()), "selected current review head differs")
        capacity_control.require_current(binding=binding)
        frozen_capacity = capacity_control.public_dict()
        materials = replace(authored_materials, extra={**authored_materials.extra, CAPACITY_KEY: frozen_capacity})
        native_checks._authored_inputs(request, materials)
        authored_state = native_checks._plain_state([request, materials])

        def check():
            _need(_wire(inputs) == before and native_checks._plain_state([request, materials]) == authored_state,
                "review evidence or complete materials changed")
            capacity_control.require_current(binding=binding)
            _need(_wire(capacity_control.public_dict()) == _wire(frozen_capacity),
                "original held capacity changed")
            result = composition.validate_current_call_composition(expected=model_record, index=index,
                repository=repository, expected_head=expected_head, tool_policy=tool_policy, scheduler=scheduler)
            actual_query = capsules.query_call_capsule_rows(output=Path(model_record["output"]) / "metadata",
                expected_metadata=model_record["metadata"], expected_head=expected_head.to_dict())
            _need(_wire(actual_query) == _wire(query), "current review metadata selection differs")
            source_guard.verify_originals(); producer_guard()
            for guard in artifact_guards:
                guard()
            return result

        checked_before = check()
        services = []
        def factory(**kwargs):
            value = CallReviewForecastService(capacity_control=capacity_control, binding=binding,
                request=request, materials=materials, **kwargs)
            services.append(value)
            return value
        owner = native_preview.RepositoryPlanPreviewOwner(index=index, repository=repository,
            expected_head=expected_head, scheduler=scheduler, timeout_seconds=90, memory_mb=256)
        preview = native_preview.preview_repository_plan(owner=owner, request=request, materials=materials,
            policy_observer=policy_observer, service_factory=factory)
        native_checks._check_preview(preview, request, materials, expected_head)
        _need(len(services) == 1, "one genuine native review service required")
        observed = services[0]
        receipt = service.PlanCreatePreviewReceipt.from_dict(preview["preview"])
        stages = {item.stage.value: item for item in receipt.stage_results}
        _need(set(stages) == {"scan", "query", "evidence", "obligation", "candidate", "critique", "admission", "parallel_plan"}
            and all(item.passed for key, item in stages.items() if key != "admission")
            and stages["admission"].passed is False
            and stages["admission"].blockers == ("ir_admission_materials_absent",)
            and receipt.verdict.value == "review_only" and receipt.admitted is False,
            "native stages must accept review forecasting and retain only missing-IR admission refusal")
        required_tasks = [task.candidate_id for task in materials.task_candidates]
        _need(observed.observed_selected_tasks == required_tasks
            and [task["task_id"] for task in observed.observed_projection["tasks"]] == required_tasks,
            "native review forecast omitted a required task")
        checked_after = check()
        result = {"schema": SCHEMA, "head": expected_head.to_dict(), "capsule": capsules.build_call_proof_capsule(**inputs),
            "request": request.to_dict(), "pre_capacity_binding": binding, "capacity": frozen_capacity,
            "native_preview": preview, "review_projection": observed.observed_projection,
            "native_parallel_plan": observed.observed_parallel_plan,
            "native_parallel_request": observed.observed_compilation_request,
            "selected_task_ids": required_tasks, "requirement_ids": list(materials.intent.goal_predicate_ids),
            "cold_validation_before": checked_before, "cold_validation_after": checked_after,
            "producer": producer, "review_forecast_accepted": True, "native_parallel_stage_passed": True,
            "admitted_execution_width": 0, "observed_behavior_facts": 0, "provider_calls": 0,
            "training_steps": 0, "checker_invocations": 0, **AUTHORITY}
        result["result_cid"] = cid_for_structured(result)
        index.observe_current(repository, expected_head=expected_head, scheduler=scheduler)
        capacity_control.require_current(binding=binding)
        _need(_wire(inputs) == before and native_checks._plain_state([request, materials]) == authored_state
            and _wire(capacity_control.public_dict()) == _wire(frozen_capacity)
            and _wire({"tool_policy": tool_policy, "expected_head": expected_head.to_dict(),
                "policy_roots": policy_roots.to_dict()}) == controls,
            "review owner, materials, evidence or capacity changed at final return")
        source_guard.verify_originals(); producer_guard()
        for guard in artifact_guards:
            guard()
        return result


@revisions._without_metadata
def build_call_review_context_packet(*, representation, capacity_control, **basis):
    """Whole offline context with the same original held capacity in both arms."""
    _need(type(capacity_control) is capacity.CallReviewCapacity, "exact held review control required")
    text = previous.build_call_context_packet(representation=representation, **basis)
    value = json.loads(text)
    public = capacity_control.public_dict()
    _need(_wire(public["input_binding"]["head"]) == _wire(basis["model_record"]["head"])
        and public["input_binding"]["capsule_id"] == value["capsule_id"],
        "offline packet and actual held capacity basis differ")
    value["schema"] = "terminal-call-review-context-packet@1"
    value["review_forecast_context"] = {"capacity": public,
        "task_resource_profile": capacity.task_resource_profile(), "writes": [],
        "execution_width": 0, "provider_calls": 0, "completion_authority": False}
    raw = _wire(value)
    _need(len(raw) <= 256_000, "whole review context packet exceeds measurement bound")
    return raw.decode("utf-8")


@revisions._without_metadata
def normalize_call_review_context_packet(text, *, capacity_control, **basis):
    _need(type(text) is str and len(text.encode("utf-8")) <= 256_000, "bounded review context required")
    try:
        value = json.loads(text)
    except (ValueError, TypeError) as exc:
        raise ValueError("canonical review context JSON required") from exc
    _need(type(value) is dict, "closed review context packet required")
    expected = build_call_review_context_packet(representation=value.get("representation"),
        capacity_control=capacity_control, **basis)
    _need(text == expected, "review context or original held capacity changed")
    return {"capsule": capsules.build_call_proof_capsule(**basis), "capacity": capacity_control.public_dict()}
