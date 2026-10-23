"""Conditional caller evidence through the real, model-off supervisor preview.

The three goals concern reviewing evidence. They never assert Python behavior,
discharge runtime obligations, authorize updates, or omit uncovered source.
Detached capsule integrity is separate from the live owner's cold validation.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
from types import SimpleNamespace

from ipfs_datasets_py.logic.software_contracts.content import cid_for_structured
from ipfs_accelerate_py.agent_supervisor.planning.adaptive_planner import FrozenPlanningGoal
from ipfs_accelerate_py.agent_supervisor.planning.obligation_graph_compiler import (
    ProducerRule, TaskCandidate, TypedIntent, TypedPredicate, obligation_id_for_producer,
)
from ipfs_accelerate_py.agent_supervisor.planning.plan_evaluator import EvidenceAwarePlanPolicy
from ipfs_accelerate_py.agent_supervisor.planning.plan_revision_contracts import (
    DirtyTreePolicy, PlanAuthorityRoots, PlanCreateRequest, PlanRequestBudget, TaskSourceKind,
)
from ipfs_accelerate_py.agent_supervisor.planning import repository_plan_preview as native_preview
from ipfs_accelerate_py.agent_supervisor.planning import codebase_source_delta_context as native_checks
from ipfs_accelerate_py.agent_supervisor.prompt import plan_create_service as native_service

from . import terminal_call_ir_composition as composition
from . import terminal_call_intent_profile as profiles
from . import terminal_call_proof_capsule as capsules
from . import terminal_revision_metadata as metadata
from . import terminal_revision_proof_cache as revisions

SCHEMA = "terminal-call-intent-plan-preview@1"
MATERIAL_KEY = "conditional_call_proof_capsule"
OPERATIONS = (
    ("revalidate_conditional_model", "Recheck current source, contracts and Lean model closure."),
    ("review_runtime_assumptions", "Review exact-int, parser, import and opaque-call assumptions; runtime equivalence remains unproved."),
    ("review_uncovered_source", "Review every source residual, including code outside the closed caller model."),
)
AUTHORITY = {name: False for name in (
    "proof_authority", "execution_authority", "completion_authority", "mutation_authority",
    "omission_authority", "production_admitted", "worker_launched", "source_semantics_verified",
    "runtime_behavior_verified", "public_terminal_bench_task_satisfied", "convergence_proved",
    "source_body_executed", "training_executed", "network_isolation_enforced",
    "caller_record_origin_verified",
)}


class CallIntentPlanningError(ValueError):
    """The complete conditional evidence cannot supply this preview."""


def _need(value, message):
    if not value:
        raise CallIntentPlanningError(message)


def _wire(value):
    # Reuse the bounded, inert, float-free material protocol. Native IntentIR's
    # confidence floats remain in its own canonical JSON string and hash.
    return native_checks._wire(value)


def intent_root(profile):
    return cid_for_structured({"schema": "canonical-call-intent-reference@1",
        "sha256": profile["intent_document_sha256"], "bytes": profile["intent_document_bytes"]})


@revisions._without_metadata
def build_call_intent_plan_inputs(*, capsule, prompt, intent_profile, model_record,
        query, callee_proof, repository: Path, policy_roots: PlanAuthorityRoots):
    """Rebuild all evidence, then author bounded review goals with no facts.

    This pure function cannot establish freshness or proof origin. The live
    adapter below separately checks the native owner before and after planning.
    """
    profiles.validate_call_intent_profile(intent_profile, prompt=prompt)
    capsules.validate_call_proof_capsule(capsule, prompt=prompt, intent_profile=intent_profile,
        model_record=model_record, query=query, callee_proof=callee_proof)
    _need(type(policy_roots) is PlanAuthorityRoots, "exact complete policy roots required")
    head = model_record["head"]
    _need(_wire(capsule["head"]) == _wire(head)
        and policy_roots.repository_id == head["repository_id"]
        and policy_roots.repository_root_cid == head["snapshot_cid"]
        and policy_roots.dirty_worktree_root == head["snapshot_cid"]
        and policy_roots.intent_ir_root == intent_root(intent_profile),
        "policy, intent and complete caller head differ")
    repository = Path(repository)
    _need(repository.is_absolute() and str(repository) == str(repository.absolute()),
        "absolute repository locator required")
    # semantic_key ignores predicate assumptions/property/proof refs. Binding
    # the ENTIRE capsule in object_ref prevents those fields aliasing a goal.
    binding = cid_for_structured({"schema": "conditional-call-review-binding@1",
        "capsule": capsule, "intent_profile_id": intent_profile["profile_id"],
        "head": head, "scope": model_record["paths"], "operations": [list(x) for x in OPERATIONS]})
    refs = (capsule["capsule_id"], intent_profile["profile_id"], model_record["result_cid"])
    goals, producers, tasks = [], [], []
    for operation, _ in OPERATIONS:
        object_ref = cid_for_structured({"complete_binding": binding, "operation": operation})
        goal = TypedPredicate("goal:call-review:" + operation, "conditional_model_review_requirement",
            head["snapshot_cid"], object_ref=object_ref, provenance_refs=refs)
        producer = ProducerRule("producer:call-review:" + operation, (goal.predicate_id,),
            provenance_refs=refs)
        task = TaskCandidate("task:call-review:" + operation,
            (obligation_id_for_producer(producer.producer_id, goal.predicate_id),),
            producer_id=producer.producer_id,
            depends_on_candidate_ids=(() if not tasks else (tasks[-1].candidate_id,)),
            provenance_refs=refs)
        goals.append(goal)
        producers.append(producer)
        tasks.append(task)
    intent = TypedIntent("intent:conditional-call-review", tuple(goals), refs,
        current_root_id=head["snapshot_cid"])
    policy = EvidenceAwarePlanPolicy(acceptance_criteria=intent.goal_predicate_ids,
        evidence_terms=refs, allowed_scopes=("scope:call-review",),
        available_resource_classes=("cpu",), require_validation=True, require_proof=False)
    request = PlanCreateRequest(
        prompt_source_cid=cid_for_structured({"schema": "call-prompt-reference@1", **intent_profile["prompt"]}),
        repository_id=head["repository_id"], repository_root=str(repository),
        scope_paths=tuple(model_record["paths"]), dirty_tree_policy=DirtyTreePolicy.OBSERVE_AND_BIND,
        task_source_kind=TaskSourceKind.BOTH, board_namespace="conditional-call-review", alias_prefix="CCR",
        roots=policy_roots, budget=PlanRequestBudget(max_goals=3, max_tasks=3, max_model_calls=0,
            max_provider_tokens=0, max_latency_ms=90_000, max_ready_width=1),
        required_analysis_operations=(), optional_analysis_operations=(),
        required_logic_families=(), optional_logic_families=(), observe_roots=True,
        supervisor_profile="conditional-call-evidence-preview", caller="principal:authored-qualification")
    materials = native_service.PlanCreateMaterials(intent=intent, producers=tuple(producers),
        task_candidates=tuple(tasks), frozen_goal=FrozenPlanningGoal("goal:conditional-call-review",
            binding, head["snapshot_cid"], policy),
        candidate_context={"domain": "conditional_call_evidence_review",
            "repository_paths": list(model_record["paths"]), "complete_binding": binding,
            "task_metadata": {task.candidate_id: {"predicted_files": list(model_record["paths"]),
                "scope_ids": ["scope:call-review"], "resource_classes": ["cpu"],
                "meaning": meaning} for task, (_, meaning) in zip(tasks, OPERATIONS)}},
        extra={MATERIAL_KEY: json.loads(_wire(capsule)), "complete_binding": binding})
    native_checks._authored_inputs(request, materials)
    return request, materials


class _ObservedPreviewService(native_service.PlanCreateService):
    """Retain actual native output; all stage implementations remain native."""

    def _candidate_plan_projection(self, request, portfolio, obligation):
        value = super()._candidate_plan_projection(request, portfolio, obligation)
        self.observed_projection = json.loads(_wire(value))
        selected = getattr(portfolio, "selected", None)
        symbolic = getattr(selected, "symbolic_candidate", None)
        self.observed_selected_tasks = list(getattr(symbolic, "task_candidate_ids", ()))
        return value


def _retain_model_artifacts(model_record, callee_proof):
    """Retain generated files across callbacks; source producers use _producer.

    This is an explicit closure, not a recursive walk through producer paths.
    Native metadata catalogs are private witnesses, never prompt payloads.
    """
    paths = set()
    for record in (model_record, model_record["callee"]):
        output = Path(record["output"])
        paths.update(output / name for name in ("result.json", "cache-report.json", "cache-dimensions.json"))
        for name in ("projection", "generated", "source", "callee_object", "caller_object", "process", "native_proof"):
            if name in record:
                paths.add(Path(record[name]["path"]))
        if "native_proof" in record:
            paths.add(output / "checked-object.olean")
        cache = Path(record["advisory_cache"]["output"])
        paths.update(cache / name for name in ("manifest.json", "artifact.bin"))
        for report in (record["metadata"], record["advisory_cache"]["metadata"]):
            catalog = Path(report["output"])
            paths.update(catalog / name for name in ("manifest.json", "metadata.duckdb"))
            for envelope in report["exports"].values():
                paths.add(catalog / envelope["relative_path"])
    paths.add(Path(callee_proof["output"]) / "result.json")
    paths.update(Path(pin["path"]) for pin in callee_proof["artifacts"].values())
    guards = []
    for path in sorted(paths):
        _, _, guard = revisions._file(path, maximum=256 * 1024 * 1024 if path.name == "metadata.duckdb" else 4 * 1024 * 1024)
        guards.append(guard)
    return guards


@revisions._without_metadata
def preview_current_call_intent_plan(*, index, repository: Path, expected_head, tool_policy,
        prompt, intent_profile, model_record, query, callee_proof, policy_roots,
        policy_observer, scheduler):
    """Cold-check the current proof cache and run the genuine supervisor service.

    The caller supplies trusted live policy wiring, not serialized facts. This
    operation invokes no prover, model provider, Python source body or worker.
    Resource controls bound each native owner/preview operation; they do not
    enforce network isolation or prove original benchmark budget compliance.
    """
    _need(callable(policy_observer), "independent live policy observer required")
    inputs = dict(prompt=prompt, intent_profile=intent_profile, model_record=model_record,
        query=query, callee_proof=callee_proof)
    before = _wire(inputs)
    controls = _wire({"tool_policy": tool_policy, "expected_head": expected_head.to_dict(),
        "policy_roots": policy_roots.to_dict()})
    selected_modules = [sys.modules[__name__], profiles, capsules, composition,
        native_preview, native_checks, native_service]
    projection = query["rows"]["call_ir_projections"][0]["payload"]
    declarations = [*projection["producer"]["files"],
        *projection["callee_projection"]["producer"]["files"], *query["producer"]["files"],
        *model_record["adapter_pins"].values(), *model_record["callee"]["integration_adapters"].values()]
    declared = {}
    for pin in declarations:
        _need(pin["path"] not in declared or _wire(declared[pin["path"]]) == _wire(pin),
            "selected producer declarations disagree")
        declared[pin["path"]] = pin
    selected_modules.extend(SimpleNamespace(__file__=path) for path in sorted(declared))
    with metadata._producer(selected_modules) as (producer, producer_guard):
        actual_pins = {pin["path"]: pin for pin in producer["files"]}
        _need(all(_wire(actual_pins[path]) == _wire(pin) for path, pin in declared.items()),
            "selected declared producer differs")
        _, source_guard = revisions._capture(repository, model_record["paths"], expected_head.repository_id)
        artifact_guards = _retain_model_artifacts(model_record, callee_proof)

        def check():
            _need(_wire(inputs) == before, "conditional evidence changed during planning")
            producer_guard()
            source_guard.verify_originals()
            for guard in artifact_guards:
                guard()
            value = composition.validate_current_call_composition(expected=model_record, index=index,
                repository=repository, expected_head=expected_head, tool_policy=tool_policy, scheduler=scheduler)
            actual_query = capsules.query_call_capsule_rows(output=Path(model_record["output"]) / "metadata",
                expected_metadata=model_record["metadata"], expected_head=expected_head.to_dict())
            _need(_wire(actual_query) == _wire(query), "current bounded metadata query differs")
            return value

        checked_before = check()
        capsule = capsules.build_call_proof_capsule(**inputs)
        request, materials = build_call_intent_plan_inputs(capsule=capsule, repository=repository,
            policy_roots=policy_roots, **inputs)
        _need(_wire(model_record["head"]) == _wire(expected_head.to_dict()), "selected caller head differs")
        request_state, material_state = _wire(request.to_dict()), native_checks._plain_state([request, materials])
        services = []

        def factory(**kwargs):
            service = _ObservedPreviewService(**kwargs)
            services.append(service)
            return service

        owner = native_preview.RepositoryPlanPreviewOwner(index=index, repository=repository,
            expected_head=expected_head, scheduler=scheduler, timeout_seconds=90, memory_mb=64)
        preview = native_preview.preview_repository_plan(owner=owner, request=request, materials=materials,
            policy_observer=policy_observer, service_factory=factory)
        native_checks._check_preview(preview, request, materials, expected_head)
        _need(len(services) == 1, "exactly one genuine preview service required")
        receipt = native_service.PlanCreatePreviewReceipt.from_dict(preview["preview"])
        stages = {item.stage.value: item for item in receipt.stage_results}
        _need(set(stages) == {"scan", "query", "evidence", "obligation", "candidate", "critique", "admission", "parallel_plan"}
            and all(stages[name].passed for name in ("scan", "query", "evidence", "obligation", "candidate")),
            "genuine native planning stages did not produce a conditional proposal")
        required_tasks = [task.candidate_id for task in materials.task_candidates]
        projection = services[0].observed_projection
        _need(set(services[0].observed_selected_tasks) == set(required_tasks)
            and [task["task_id"] for task in projection["tasks"]] == services[0].observed_selected_tasks,
            "planner omitted or replaced a required evidence review task")
        checked_after = check()
        result = {"schema": SCHEMA, "head": expected_head.to_dict(), "capsule": capsule,
            "request": request.to_dict(), "authored_material_binding": materials.to_binding_dict(),
            "native_preview": preview, "native_candidate_projection": projection,
            "selected_task_ids": services[0].observed_selected_tasks,
            "requirement_ids": list(materials.intent.goal_predicate_ids),
            "cold_validation_before": checked_before, "cold_validation_after": checked_after,
            "producer": producer, "observed_behavior_facts": 0, "provider_calls": 0,
            "training_steps": 0, "checker_invocations": 0,
            "projection_effect_scope": "generic_native_hypothetical_updates;not_executed_or_authorized",
            "review_task_completion_proved": False, "original_task_budget_satisfied": False,
            **AUTHORITY}
        result["result_cid"] = cid_for_structured(result)
        _need(_wire(request.to_dict()) == request_state
            and native_checks._plain_state([request, materials]) == material_state,
            "complete authored planning material changed")
        index.observe_current(repository, expected_head=expected_head, scheduler=scheduler)
        _need(_wire(request.to_dict()) == request_state
            and native_checks._plain_state([request, materials]) == material_state
            and _wire({"tool_policy": tool_policy, "expected_head": expected_head.to_dict(),
                "policy_roots": policy_roots.to_dict()}) == controls,
            "current owner or planning controls changed at final return")
        source_guard.verify_originals()
        producer_guard()
        for guard in artifact_guards:
            guard()
        _need(_wire(inputs) == before, "conditional evidence changed at final return")
        return result


@revisions._without_metadata
def build_call_context_packet(*, representation, prompt, intent_profile, model_record, query, callee_proof):
    """Whole local context packets for offline comparison, never provider usage."""
    _need(type(representation) is str and representation in {"expanded", "capsule"}, "closed context representation required")
    basis = dict(prompt=prompt, intent_profile=intent_profile, model_record=model_record,
        query=query, callee_proof=callee_proof)
    capsule = capsules.build_call_proof_capsule(**basis)
    value = {"schema": "terminal-call-context-packet@1", "user_prompt": prompt,
        "representation": representation, "head": model_record["head"],
        "capsule_id": capsule["capsule_id"], "context": ({"intent_profile": intent_profile,
            "query": query} if representation == "expanded" else {"capsule": capsule})}
    raw = _wire(value)
    _need(len(raw) <= 256_000, "whole context packet exceeds offline measurement bound")
    return raw.decode("utf-8")


@revisions._without_metadata
def normalize_call_context_packet(text, *, prompt, intent_profile, model_record, query, callee_proof):
    """Replay an exact packet against external current-owner evidence.

    Expansion needs the retained evidence basis; the compact packet cannot
    authenticate itself or nominate its own checked files, rows or facts.
    """
    _need(type(text) is str and len(text.encode("utf-8")) <= 256_000, "bounded UTF-8 context packet required")
    try:
        value = json.loads(text)
    except (ValueError, TypeError) as exc:
        raise CallIntentPlanningError("canonical context packet required") from exc
    _need(type(value) is dict, "closed context packet required")
    basis = dict(prompt=prompt, intent_profile=intent_profile, model_record=model_record,
        query=query, callee_proof=callee_proof)
    expected = build_call_context_packet(representation=value.get("representation"), **basis)
    _need(text == expected, "context packet or retained evidence binding differs")
    return capsules.build_call_proof_capsule(**basis)
