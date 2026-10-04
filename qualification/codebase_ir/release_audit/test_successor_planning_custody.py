"""Synthetic, typed planning and custody refusal controls; stdlib only."""
import copy
import importlib.util
import json
import os
import tempfile
import unittest
from hashlib import sha256
from pathlib import Path
from unittest import mock

_SPEC = importlib.util.spec_from_file_location("successor_custody", Path(__file__).with_name("successor_planning_custody.py"))
m = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(m)


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode()


def tagged(value):
    if type(value) in (list, tuple):
        return {"$sequence": type(value).__name__, "items": [tagged(item) for item in value]}
    if type(value) is dict:
        if "$record" in value or "$enum" in value:
            return value
        return {"$mapping": {key: tagged(item) for key, item in value.items()}}
    return value


def record(kind, **fields):
    return {"$record": "ipfs_accelerate_py.agent_supervisor.planning." + kind, "fields": tagged(fields)}


def enum(kind, value):
    return {"$enum": "ipfs_accelerate_py.agent_supervisor.planning.obligation_graph_compiler." + kind, "value": value}


def material_variants(snapshot, context, advisory, scan_id, context_id):
    predicates, producers, tasks = [], [], []
    for index in (0, 1):
        goal, producer = f"goal:runtime:{index}", f"producer:runtime:{index}"
        predicates.append(record("obligation_graph_compiler.TypedPredicate", predicate_id=goal,
            predicate_type="reviewed_runtime_requirement", subject_ref="calc.py", object_ref=f"requirement:{index}",
            property_id="", polarity=enum("PredicatePolarity", "positive"), support=enum("SemanticSupport", "reviewed"),
            provenance_refs=(), assumption_refs=(), validation_requirement_refs=(), proof_requirement_refs=(), invalidation_selectors=()))
        producers.append(record("obligation_graph_compiler.ProducerRule", producer_id=producer, effect_predicate_ids=(goal,),
            required_predicate_ids=(), task_candidate_ids=(), provenance_refs=(), assumption_refs=(), validation_requirement_refs=(),
            proof_requirement_refs=(), invalidation_selectors=(), executable=True))
        tasks.append(record("obligation_graph_compiler.TaskCandidate", candidate_id=f"task:runtime:{index}", producer_id=producer,
            closes_obligation_ids=(f"obligation:producer:{producer}:for:{goal}",), depends_on_candidate_ids=(), provenance_refs=()))
    policy = record("plan_evaluator.EvidenceAwarePlanPolicy", acceptance_criteria=("goal:runtime:0", "goal:runtime:1"),
        evidence_terms=("source:authored-runtime",), trusted_assumptions=(), supported_semantics=(), satisfied_dependencies=(),
        allowed_scopes=("scope:calc.py",), available_resource_classes=("cpu",), max_estimated_resource_cost=1000000.0,
        max_estimated_tokens=1000000000, max_estimated_runtime_seconds=1000000.0, min_novelty=0.0, require_validation=True, require_proof=False)
    base = dict.fromkeys(("admission_materials", "candidate_context", "current_facts", "current_roots", "evidence_adapters",
        "evidence_bundle", "evidence_queries", "extra", "frozen_goal", "intent", "model_provider", "obligation_graph",
        "parallel_request", "parallel_tasks", "predicates", "producers", "query_plan", "scan", "task_candidates", "workflow_request"))
    candidate = {"repository_paths": ["calc.py"], "task_metadata": {f"task:runtime:{i}": {
        "predicted_files": ["calc.py"], "scope_ids": ["scope:calc.py"], "resource_classes": ["cpu"]} for i in (0, 1)}}
    base.update(current_facts=(), evidence_queries=(), predicates=(), producers=tuple(producers), task_candidates=tuple(tasks),
        intent=record("obligation_graph_compiler.TypedIntent", intent_id="intent:authored-source-successor", desired_predicates=tuple(predicates),
            source_refs=("source:authored-runtime",), current_root_id=snapshot, metadata={}),
        frozen_goal=record("adaptive_planner.FrozenPlanningGoal", goal_id="goal:runtime",
            goal_content_id="baguqeera4da5a3nxyystiby75cuecis6uqovskarvl5ch5fijthl7szrgutq", repository_tree_id=snapshot, policy=policy),
        candidate_context=candidate, extra={"authored_review": "review:complete-runtime-requirements"})
    intermediate = {**base, "extra": {**base["extra"], "codebase_source_delta_advisory": advisory}}
    consumed = {**intermediate, "scan": {"scan_cid": scan_id, "structural_codebase": context},
        "candidate_context": {**candidate, "structural_codebase": context, "structural_codebase_context_cid": context_id},
        "extra": {**intermediate["extra"], "root_observation_profile": "repository-live-root-observation@1",
                  "structural_codebase": context, "structural_codebase_context_cid": context_id}}
    return [{field: tagged(value) for field, value in fields.items()} for fields in (base, intermediate, consumed)]


def binding(fields):
    return {"schema": "ipfs_accelerate_py/agent-supervisor/plan-create-semantic-material-binding@1",
            "reuse_supported": True, "opaque_material_nonce": "", "unsupported_fields": {},
            "field_digests": {field: "sha256:" + sha256(b"plan-create-semantic-input\n" + field.encode() + b"\n" + encoded(value)).hexdigest() for field, value in fields.items()}}


def fixture(workspace):
    ns = workspace / "artifacts/codebase_ir_terminal_bench/source-successor-qualification-20261003-02"
    paths = {"machine_review": workspace / "external/ipfs_accelerate/docs/architecture/repository_proof_index_and_codebase_ir.source_successor_review.json",
        "closed_audit": workspace / "closed-audit.json", "native_result": ns / "result.json",
        "failed_native_result": workspace / "artifacts/codebase_ir_terminal_bench/source-successor-qualification-20261003-01/result.json",
        **{role: ns / filename for role, filename in m.LOCAL_NAMES.items()}}
    head = {"snapshot_cid": "snapshot:current"}
    config = {"synthetic_recorded_configuration": 1}
    native = {"schema": "codebase-source-successor-native-qualification@1", "qualified": True,
        "scope": "fresh_300_member_successor_and_two_32_member_cpu8d_prefix_pages", "current_head": head,
        "pid": 42, "recorded_seconds": 809.0, "elapsed_seconds_so_far": 808.0, "parent_version_id": "sha256:parent", "child_version_id": "sha256:child",
        "setup_training_attempts": [{"name": name, "version_id": "sha256:" + version, "requested_epochs": 1,
            "actual_completed_epochs": 1, "unknown_actual_epochs_on_failure": False} for name, version in (("root", "parent"), ("child", "child"))],
        "new_fitting_epochs": 2, "training_attempts_after_setup": 0, "inference_attempts_during_selection_or_cold_receiving": 0,
        "source_property_solver_calls": 0, "inherited_scan_pages": 0, "inherited_setup_epochs": 0,
        "final_resources": {"active_lease_count": 0, "waiting_request_count": 0},
        "cold_receiving_verified": True, "native_owner_unchanged_except_explicit_reopen": True,
        "selected_producers_unchanged": True, "original_source_artifacts_preserved": True,
        "source_owner_reopens": 1, "model_owner_reopens": 1, "new_scan_pages_created": 2,
        "coverage": {"current_entries": 300, "previous_entries": 300},
        "prefix_coverage": {"inventory_entries": 32, "inferred_rows": 22, "dispositions": {"inferred": 22, "deferred_budget": 9, "unindexed": 1}},
        "opt_out_equivalence": {"scope": "first32_ordered_members_only", "entries_coverage_and_inference_exact": True,
            "throughput_qualified": False, "optimized_page_cid": "page:optimized", "optimized_root_cid": "root:optimized",
            "reference_page_cid": "page:reference", "reference_root_cid": "root:reference"},
        "prefix_page_cid": "page:optimized", "root_cid": "root:optimized", "planning_result_cid": "result:planning", "source_delta_cid": "delta:declared",
        "operation_deadline_seconds": copy.deepcopy(m.DEADLINES), "scheduler_configuration": config,
        "phases": [{"name": name, "status": "completed", "elapsed_seconds": 150.0 if i == 7 else 1.0} for i, name in enumerate(m.PHASES)],
        "controls": [{"name": "old_model_for_new_head", "error_type": "CodebaseSuccessorScanError",
                      "error": "selected version must be an exact registered direct child", "refused": True, "elapsed_seconds": 1.0},
                     {"name": "precancelled_selection_receiving", "error_type": "LeaseCancelledError",
                      "error": "resource lease request was cancelled", "refused": True, "elapsed_seconds": 0.01}]}
    for field in ("384d_qualified", "complete_scan_qualified", "cuda_qualified", "production_default_activated", "proof_authority",
                  "repository_code_executed", "worker_admission_qualified", "model_head_promoted", "numerical_reuse"):
        native[field] = False
    failed = copy.deepcopy(native)
    failed.update(qualified=False, recorded_seconds=394.0, elapsed_seconds_so_far=393.0,
        error_type="LeaseTimeoutError", error="resumable inventory deadline exceeded", new_scan_pages_created=0,
        phases=copy.deepcopy(native["phases"][:8]))
    failed["phases"][7].update(status="failed", elapsed_seconds=125.0)
    context = {"schema": "supervisor-structural-codebase-context@1", "authority": "structural_only", "head": head,
               **dict.fromkeys(("completion_authority", "execution_authority", "proof_authority", "source_semantics_verified"), False)}
    advisory = {"schema": "codebase-source-delta-advisory-refs@1", "authority": dict.fromkeys(m.PLAN_AUTHORITY, False), "artifact_cid": "delta:declared", "current_head": head}
    budget = {"schema": "ipfs_accelerate_py/agent-supervisor/plan-request-budget@1", "contract_version": 1,
        "max_analysis_operations": 64, "max_cost_micros": 0, "max_evidence_items": 512, "max_goals": 64, "max_graph_depth": 16,
        "max_latency_ms": 120000, "max_logic_families": 16, "max_model_calls": 0, "max_output_paths": 1024,
        "max_provider_tokens": 32768, "max_ready_width": 1, "max_repair_rounds": 2, "max_scan_bytes": 67108864, "max_tasks": 256}
    request = {"schema": "ipfs_accelerate_py/agent-supervisor/plan-create-request@1", "contract_version": 1, "observe_roots": False,
        "caller": "principal:unknown", "idempotency_key": "", "repository_root": str(ns / "repository"),
        "alias_prefix": "SUCCESSOR", "board_namespace": "source-successor", "budget": budget,
        "dirty_tree_policy": "observe_and_bind", "fallback_policy": "fail_closed", "optional_analysis_operations": [],
        "optional_logic_families": [], "repository_id": "qualification:source-successor", "required_analysis_operations": [],
        "required_logic_families": [], "roots": {"schema": "ipfs_accelerate_py/agent-supervisor/plan-authority-roots@1",
            "contract_version": 1, "repository_id": "qualification:source-successor", "task_source_id": "source:authored-runtime",
            **{key: key + ":declared" for key in ("repository_root_cid", "task_source_revision", "program_root", "legal_ir_root", "intent_ir_root",
              "security_ir_root", "policy_root", "configuration_root", "capability_catalog_root", "provider_catalog_root", "usage_policy_root", "dirty_worktree_root")}}, "scope_paths": ["calc.py"],
        "supervisor_profile": "implementation-daemon", "task_source_kind": "both"}
    snapshot = {key: copy.deepcopy(value) for key, value in request.items() if key not in ("schema", "contract_version", "observe_roots", "caller", "idempotency_key")}
    snapshot.update(schema="ipfs_accelerate_py/agent-supervisor/plan-create-input-snapshot@2", snapshot_cid="snapshot:input", request_cid="request:declared")
    stage_artifacts = [f"artifact:stage:{i}" for i in range(8)]
    stage_results = [f"result:stage:{i}" for i in range(8)]
    blockers = [[], [], [], [], [], [], m.BLOCKERS[:2], [m.BLOCKERS[2], m.BLOCKERS[3], *([m.BLOCKERS[4]] * 3), m.BLOCKERS[5]]]
    preview = {"schema": "ipfs_accelerate_py/agent-supervisor/plan-create-preview-receipt@1", "interface": "PlanCreateService@1",
        "mode": "deterministic", "read_only": True, "verdict": "review_only", "wrote_effects": [],
        "input_snapshot_cid": "snapshot:input", "request_cid": "request:declared", "roots": copy.deepcopy(request["roots"]),
        "receipt_cid": "receipt:planning", "rejection_reasons": list(m.BLOCKERS), "plan_root_cid": stage_artifacts[5],
        "stage_results": [{"schema": "ipfs_accelerate_py/agent-supervisor/plan-create-stage-result@1", "stage": name,
            "passed": i < 6, "artifact_cid": stage_artifacts[i], "result_cid": stage_results[i], "blockers": blockers[i],
            "detail_ids": [], "message": "retained synthetic stage"} for i, name in enumerate(m.STAGES)],
        "artifact_refs": [*stage_artifacts, *stage_results, "compatibility:declared"]}
    for key, value in zip(("scan_cid", "query_plan_cid", "evidence_bundle_cid", "obligation_graph_cid", "candidate_portfolio_cid",
                           "critique_cid", "admission_receipt_cid", "execution_plan_cid"), stage_artifacts, strict=True):
        preview[key] = value
    fields = material_variants(head["snapshot_cid"], context, advisory, preview["scan_cid"], "context:declared")
    entries = [{"binding": binding(value), "preimages": value} for value in fields]
    consumed_binding = copy.deepcopy(entries[2]["binding"])
    entries.sort(key=lambda entry: sha256(encoded(entry["binding"])).hexdigest())
    snapshot["material_binding"] = consumed_binding
    exported = {"schema": "source-successor-planning-semantic-preimages@1", "capture": "explicit_reconstruction_checked_against_native_consumed_material_binding",
                "execution_attestation": False, "entries": entries}
    planning = {"schema": "supervisor-codebase-source-delta-plan-preview@1", "authority": dict.fromkeys(m.PLAN_AUTHORITY, False),
        "declared_requirement_ids": list(m.GOALS), "declared_task_ids": list(m.TASKS), "residual_task_ids": list(m.TASKS),
        "residual_requirements": [{"predicate_id": goal, "status": "runtime_behavior_unresolved"} for goal in m.GOALS],
        "current_facts": [], "removed_task_ids": [], "inference_calls": 0, "training_steps": 0, "source_property_solver_calls": 0,
        **dict.fromkeys(("model_advanced", "numerical_reuse", "physical_absence_verified", "production_admitted", "worker_launched"), False),
        "result_cid": "result:planning", "producer": {"module": "ipfs_accelerate_py.agent_supervisor.planning.codebase_source_delta_context",
            "scope": "listed_local_file_only_not_execution_attestation", "sha256": "1" * 64}, "codebase_source_delta_advisory": advisory,
        "repository_preview": {"schema": "supervisor-repository-plan-preview@1", "input_snapshot": snapshot, "preview": preview,
            "structural_context": context, "structural_context_cid": "context:declared", "model_calls": 0, "observed_facts_supplied": 0,
            **dict.fromkeys(("completion_authority", "execution_authority", "production_admitted", "proof_authority", "source_semantics_verified", "worker_launched"), False)}}
    authored = {"request": request, "materials": {"schema": "ipfs_accelerate_py/agent-supervisor/plan-create-materials@1",
        "current_roots": {}, "evidence_adapter_slots": [], "extra_keys": ["authored_review"],
        "has_admission_materials": False, "has_model_provider": False, "has_workflow_request": False}}
    metrics = {"acquisitions_total": 49, "releases_total": 49, "cancellations_total": 1, "timeouts_total": 0,
        "recoveries_total": 0, "recovered_leases_total": 0, "saturation_events_total": 0, "wait_samples": [0.000001] * 50,
        "wait_seconds_max": 0.000001, "wait_seconds_total": 0.00005,
        "lanes": {"snapshot_evaluation": {"acquisitions_total": 45, "cancellations_total": 1, "timeouts_total": 0, "wait_count": 46,
                     "wait_seconds_max": 0.000001, "wait_seconds_total": 0.000046},
                  "trainer": {"acquisitions_total": 4, "cancellations_total": 0, "timeouts_total": 0, "wait_count": 4,
                     "wait_seconds_max": 0.000001, "wait_seconds_total": 0.000004}}}
    resource = {"schema_version": "legal-ir-global-resource-scheduler-v1", "config": config, "leases": {}, "waiters": {},
                "proof_backoff": {}, "metrics": metrics, "next_sequence": 51}
    audit = {"schema": "codebase-source-successor-independent-audit@1", "qualified": True, "errors": [], "preserved": True,
        "namespace": str(ns), "planning": {"requirements": list(m.GOALS), "tasks": list(m.TASKS), "observed_facts": 0, "removed_tasks": 0,
            "proof_authority": False, "result_cid": "result:planning", "input_snapshot_cid": "snapshot:input", "receipt_cid": "receipt:planning",
            "preimage_capture_scope": "explicit reconstruction bound to recorded native consumed snapshot; not execution attestation",
            "cold_preimage_scope": "same warm reconstructed preimages reused against exactly identical cold consumed binding"},
        "costs": {"phases": copy.deepcopy(native["phases"]), "explicit_setup_training": copy.deepcopy(native["setup_training_attempts"]),
            "operation_deadline_seconds": copy.deepcopy(m.DEADLINES), "phases_are_cooperative_not_kernel_deadlines": True,
            "recorded_native_seconds": native["recorded_seconds"], "training_attempts_after_setup": 0,
            "inference_attempts_during_selection_or_cold_receiving": 0, "source_property_solver_calls": 0, "new_fitting_epochs": 2},
        "resources": {"leases": 0, "waiters": 0, "final_resources": copy.deepcopy(native["final_resources"]), "kernel_memory_enforcement_claimed": False}}
    for field in ("384d_qualified", "complete_scan_qualified", "cuda_qualified", "git_executed", "mutable_working_checkout_qualified",
        "native_owners_opened", "numerical_execution_independently_reperformed", "primary_writes", "process_origin_attested", "proof_authority", "sql_executed", "worker_admission_qualified"):
        audit[field] = False
    machine = {"schema": "repository-proof-index-source-successor-review@1", "qualified": True,
        "native_namespace": str(ns.relative_to(workspace)), "production_open_tasks": 32,
        "native_work": {key: copy.deepcopy(native[key]) for key in ("prefix_coverage", "operation_deadline_seconds", "planning_result_cid")},
        "failed_native_attempt": {key: copy.deepcopy(failed[key]) for key in ("error", "error_type", "final_resources", "new_fitting_epochs", "new_scan_pages_created", "phases", "qualified", "recorded_seconds")},
        "costs": {"qualified_native_seconds": native["recorded_seconds"], "failed_native_seconds": failed["recorded_seconds"],
            "qualified_phase_seconds": {row["name"]: row["elapsed_seconds"] for row in native["phases"]},
            "benchmark_new_fitting_epochs_across_two_attempts": 4, "inherited_benchmark_fitting_epochs": 0,
            "unit_fixture_new_fitting_epochs_separate": 2, "independent_reader_seconds": 0.1}}
    for field in ("384d_qualified", "complete_successor_scan_qualified", "cuda_qualified", "production_default_activated",
        "production_task_status_changed", "proof_authority", "runtime_reexecuted_here", "scan_execution_attested", "signed_successor_worker_qualified", "source_execution_attested"):
        machine[field] = False
    docs = dict(zip(m.ROLES, (machine, audit, native, failed, authored, planning, copy.deepcopy(planning), exported, copy.deepcopy(exported), resource), strict=True))
    return docs, paths


def packet(workspace, docs, paths):
    """Rebind every enclosing declaration so mutations reach semantic checks."""
    def pin(role, root):
        raw = encoded(docs[role])
        return {"path": str(paths[role].relative_to(root)), "sha256": sha256(raw).hexdigest(), "bytes": len(raw)}

    ns = paths["native_result"].parent
    audit, machine = docs["closed_audit"], docs["machine_review"]
    audit["audited_result"] = pin("native_result", ns)
    rows = [{"kind": "file", "mode": 0o444, "mtime_ns": 1, "nlink": 1, **pin(role, ns)} for role in m.ROLES[4:]]
    audit["archive"] = {"files": rows, "regular_files": len(rows), "regular_bytes": sum(row["bytes"] for row in rows)}
    machine["native_result"] = pin("native_result", workspace)
    machine["failed_native_attempt"]["result"] = pin("failed_native_result", workspace)
    machine["independent_closed_audit"] = pin("closed_audit", workspace)
    selected = []
    for role in m.ROLES:
        paths[role].parent.mkdir(parents=True, exist_ok=True)
        raw = encoded(docs[role])
        paths[role].write_bytes(raw)
        selected.append({"role": role, "path": str(paths[role]), "sha256": sha256(raw).hexdigest(), "size_bytes": len(raw)})
    manifest = workspace / "input.json"
    manifest.write_bytes(encoded({"schema": m.INPUT_SCHEMA, "selected_profile": m.PROFILE, "selected_files": selected}))
    return manifest, selected[0]["sha256"]


class SuccessorPlanningTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.workspace = Path(self.temp.name)
        self.docs, self.paths = fixture(self.workspace)

    def run_packet(self):
        manifest, anchor = packet(self.workspace, self.docs, self.paths)
        with mock.patch.object(m, "PUBLIC_ANCHOR", anchor):
            return m.audit(manifest, self.workspace / "out")

    def refused(self, mutation):
        before = copy.deepcopy(self.docs)
        mutation(self.docs)
        for warm, cold in (("planning_preview", "cold_planning_preview"), ("planning_semantic_preimages", "cold_planning_semantic_preimages")):
            if encoded(self.docs[warm]) != encoded(before[warm]) and encoded(self.docs[cold]) == encoded(before[cold]):
                self.docs[cold] = copy.deepcopy(self.docs[warm])
        for key in self.docs["machine_review"]["native_work"]:
            if encoded(self.docs["machine_review"]["native_work"][key]) == encoded(before["machine_review"]["native_work"][key]):
                self.docs["machine_review"]["native_work"][key] = copy.deepcopy(self.docs["native_result"][key])
        for key in self.docs["machine_review"]["failed_native_attempt"]:
            if encoded(self.docs["machine_review"]["failed_native_attempt"][key]) == encoded(before["machine_review"]["failed_native_attempt"][key]):
                self.docs["machine_review"]["failed_native_attempt"][key] = copy.deepcopy(self.docs["failed_native_result"][key])
        with self.assertRaises((ValueError, KeyError, TypeError, OSError)):
            self.run_packet()

    def test_complete_residual_report(self):
        report = self.run_packet()
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["selected_file_count"], 10)
        self.assertEqual(report["planning"]["preimage_materials"]["byte_digests_rederived"], 60)
        self.assertEqual(report["planning"]["residual_task_ids"], ["task:runtime:0", "task:runtime:1"])
        self.assertEqual(report["planning"]["passed_stage_count"], 6)
        for flag in m.TRUE_FLAGS:
            self.assertIs(report[flag], True)
        for flag in m.FALSE_FLAGS:
            self.assertIs(report[flag], False)
        for field in m.ZERO_FIELDS:
            self.assertIs(type(report[field]), int)
            self.assertEqual(report[field], 0)
        self.assertEqual(set(report["declared_missing_closure"].values()), {"unknown_not_selected"})
        for index, role in enumerate(m.ROLES):
            self.assertEqual(report[role + "_sha256"], report["selected_files"][index]["sha256"])

    def test_omitted_authored_task(self):
        self.refused(lambda d: d["planning_preview"]["residual_task_ids"].pop())

    def test_runtime_fact_invented(self):
        self.refused(lambda d: d["planning_preview"]["current_facts"].append("fact:runtime:0"))

    def test_task_removed(self):
        self.refused(lambda d: d["planning_preview"]["removed_task_ids"].append("task:runtime:0"))

    def test_requirement_satisfied(self):
        self.refused(lambda d: d["planning_preview"]["residual_requirements"][0].update(status="satisfied"))

    def test_goal_population(self):
        self.refused(lambda d: d["planning_preview"]["declared_requirement_ids"].append("goal:extra"))

    def test_admission_promoted(self):
        self.refused(lambda d: d["planning_preview"]["repository_preview"]["preview"]["stage_results"][6].update(passed=True))

    def test_critic_failure_erased(self):
        self.refused(lambda d: d["planning_preview"]["repository_preview"]["preview"]["stage_results"][5].update(passed=False))

    def test_parallel_duplicate_blocker_erased(self):
        self.refused(lambda d: d["planning_preview"]["repository_preview"]["preview"]["stage_results"][7]["blockers"].pop(2))

    def test_wrote_effect(self):
        self.refused(lambda d: d["planning_preview"]["repository_preview"]["preview"]["wrote_effects"].append("publication"))

    def test_planning_authority(self):
        self.refused(lambda d: d["planning_preview"]["authority"].update(proof_authority=True))

    def test_stage_reference_substitution(self):
        self.refused(lambda d: d["planning_preview"]["repository_preview"]["preview"]["stage_results"][0].update(artifact_cid="substitution"))

    def test_native_snapshot_schema(self):
        self.refused(lambda d: d["planning_preview"]["repository_preview"]["input_snapshot"].update(schema="old@1"))

    def test_bool_budget_alias(self):
        self.refused(lambda d: d["authored_planning_inputs"]["request"]["budget"].update(contract_version=True))

    def test_request_model_budget(self):
        self.refused(lambda d: d["authored_planning_inputs"]["request"]["budget"].update(max_model_calls=1))

    def test_cold_result_bytes_differ(self):
        self.refused(lambda d: d["cold_planning_preview"].update(unrecorded_extra=True))

    def test_cold_preimages_independently_replaced(self):
        self.refused(lambda d: d["cold_planning_semantic_preimages"].update(capture="new independent cold capture"))

    def test_preimage_field_missing(self):
        self.refused(lambda d: d["planning_semantic_preimages"]["entries"][0]["preimages"].pop("workflow_request"))

    def test_preimage_binding_field_missing(self):
        self.refused(lambda d: d["planning_semantic_preimages"]["entries"][0]["binding"]["field_digests"].pop("workflow_request"))

    def test_preimage_variant_missing(self):
        self.refused(lambda d: d["planning_semantic_preimages"]["entries"].pop())

    def test_preimage_execution_attestation_promoted(self):
        self.refused(lambda d: d["planning_semantic_preimages"].update(execution_attestation=True))

    def semantic_mutation(self, mutation, *, repin=True):
        exported = self.docs["planning_semantic_preimages"]
        for entry in exported["entries"]:
            mutation(entry["preimages"])
            if repin:
                entry["binding"] = binding(entry["preimages"])
        exported["entries"].sort(key=lambda entry: sha256(encoded(entry["binding"])).hexdigest())
        self.docs["cold_planning_semantic_preimages"] = copy.deepcopy(exported)
        consumed = next(entry for entry in exported["entries"] if entry["preimages"]["scan"] is not None)
        for role in ("planning_preview", "cold_planning_preview"):
            self.docs[role]["repository_preview"]["input_snapshot"]["material_binding"] = copy.deepcopy(consumed["binding"])

    def test_digest_domain_required(self):
        exported = self.docs["planning_semantic_preimages"]
        for entry in exported["entries"]:
            entry["binding"]["field_digests"]["workflow_request"] = "sha256:" + sha256(encoded(None)).hexdigest()
        self.docs["cold_planning_semantic_preimages"] = copy.deepcopy(exported)
        with self.assertRaises(ValueError):
            self.run_packet()

    def test_exact_typed_digest_vectors(self):
        fields = {"workflow_request": None, "current_facts": {"$sequence": "tuple", "items": []}}
        computed = binding(fields)["field_digests"]
        self.assertEqual(computed["workflow_request"], "sha256:f688dad1273ce18869644f4c3c7a4dc7f7a843bce54c7c0c9556b595a364816a")
        self.assertEqual(computed["current_facts"], "sha256:b74af97bd7cfe2dadc437d00296e9fc8744f248a019cb13b68eceb38e319cd08")

    def test_native_class_not_imported(self):
        self.semantic_mutation(lambda f: f["intent"].update({"$record": "unreviewed.OwnerClass"}))
        with self.assertRaises(ValueError):
            self.run_packet()

    def test_native_enum_value(self):
        self.semantic_mutation(lambda f: f["intent"]["fields"]["$mapping"]["desired_predicates"]["items"][0]["fields"]["$mapping"]["support"].update(value="trusted"))
        with self.assertRaises(ValueError):
            self.run_packet()

    def test_rebound_typed_tuple_alias(self):
        self.semantic_mutation(lambda f: f["current_facts"].update({"$sequence": "list"}))
        with self.assertRaises(ValueError):
            self.run_packet()

    def test_rebound_policy_bool_number(self):
        self.semantic_mutation(lambda f: f["frozen_goal"]["fields"]["$mapping"]["policy"]["fields"]["$mapping"].update(min_novelty=False))
        with self.assertRaises(ValueError):
            self.run_packet()

    def test_rebound_task_producer(self):
        self.semantic_mutation(lambda f: f["task_candidates"]["items"][0]["fields"]["$mapping"].update(producer_id="producer:other"))
        with self.assertRaises(ValueError):
            self.run_packet()

    def test_rebound_omitted_authored_task(self):
        self.semantic_mutation(lambda f: f["task_candidates"]["items"].pop())
        with self.assertRaises(ValueError):
            self.run_packet()

    def test_rebound_fact_added(self):
        self.semantic_mutation(lambda f: f["current_facts"]["items"].append("fact:new"))
        with self.assertRaises(ValueError):
            self.run_packet()

    def test_duplicate_material_variant(self):
        self.refused(lambda d: d["planning_semantic_preimages"]["entries"].__setitem__(1, copy.deepcopy(d["planning_semantic_preimages"]["entries"][0])))

    def test_prefix_inflated_to_complete(self):
        self.refused(lambda d: d["native_result"].update(complete_scan_qualified=True))

    def test_two_prefixes_inflated_to_64(self):
        self.refused(lambda d: d["native_result"]["prefix_coverage"].update(inventory_entries=64))

    def test_deferred_prefix_budget_erased(self):
        self.refused(lambda d: d["native_result"]["prefix_coverage"]["dispositions"].update(deferred_budget=0))

    def test_cold_owner_restart_invented(self):
        self.refused(lambda d: d["native_result"].update(model_owner_reopens=2))

    def test_receiving_extra_training(self):
        self.refused(lambda d: d["native_result"].update(training_attempts_after_setup=1))

    def test_setup_epoch_bool_alias(self):
        self.refused(lambda d: d["native_result"]["setup_training_attempts"][0].update(actual_completed_epochs=True))

    def test_failed_reference_promoted(self):
        self.refused(lambda d: d["failed_native_result"].update(qualified=True))

    def test_failed_reference_deadline_rewritten(self):
        self.refused(lambda d: d["failed_native_result"]["phases"][7].update(elapsed_seconds=601.0))

    def test_failed_attempt_cost_omitted(self):
        self.refused(lambda d: d["machine_review"]["costs"].update(failed_native_seconds=0.0))

    def test_unit_epochs_added_to_benchmark(self):
        self.refused(lambda d: d["machine_review"]["costs"].update(benchmark_new_fitting_epochs_across_two_attempts=6))

    def test_source_property_solver_count_promoted(self):
        self.refused(lambda d: d["native_result"].update(source_property_solver_calls=1))

    def test_scheduler_pending_lease(self):
        self.refused(lambda d: d["resource_admission"]["leases"].update(lease="pending"))

    def test_scheduler_boolean_count(self):
        self.refused(lambda d: d["resource_admission"]["metrics"].update(cancellations_total=True))

    def test_scheduler_wait_cost(self):
        self.refused(lambda d: d["resource_admission"]["metrics"].update(wait_seconds_total=10.0))

    def test_scheduler_wait_population(self):
        self.refused(lambda d: d["resource_admission"]["metrics"]["wait_samples"].pop())

    def test_reader_does_not_open_declared_repository(self):
        with mock.patch("os.system", side_effect=AssertionError("process forbidden")), mock.patch("os.popen", side_effect=AssertionError("process forbidden")):
            self.run_packet()
        self.assertFalse((self.paths["native_result"].parent / "repository").exists())

    def test_closed_role_order(self):
        manifest, anchor = packet(self.workspace, self.docs, self.paths)
        value = json.loads(manifest.read_bytes())
        value["selected_files"].reverse()
        manifest.write_bytes(encoded(value))
        with mock.patch.object(m, "PUBLIC_ANCHOR", anchor), self.assertRaises(ValueError):
            m.audit(manifest, self.workspace / "out")

    def test_extra_selected_role(self):
        manifest, anchor = packet(self.workspace, self.docs, self.paths)
        value = json.loads(manifest.read_bytes())
        value["selected_files"].append(value["selected_files"][-1])
        manifest.write_bytes(encoded(value))
        with mock.patch.object(m, "PUBLIC_ANCHOR", anchor), self.assertRaises(ValueError):
            m.audit(manifest, self.workspace / "out")

    def test_descriptor_bool_size(self):
        with self.assertRaises(ValueError):
            m.descriptor({"path": str(self.workspace / "x"), "sha256": "0" * 64, "size_bytes": True})

    def test_unpinned_path_refused_before_open(self):
        manifest, anchor = packet(self.workspace, self.docs, self.paths)
        value = json.loads(manifest.read_bytes())
        value["selected_files"][4]["path"] = str(self.workspace / "forbidden")
        manifest.write_bytes(encoded(value))
        observed = []
        real = m.Capture.raw
        def raw(path, maximum):
            observed.append(path)
            return real(path, maximum)
        with mock.patch.object(m, "PUBLIC_ANCHOR", anchor), mock.patch.object(m.Capture, "raw", side_effect=raw), self.assertRaises(ValueError):
            m.audit(manifest, self.workspace / "out")
        self.assertNotIn(self.workspace / "forbidden", observed)

    def test_duplicate_json_keys(self):
        with self.assertRaises(ValueError):
            m.document(b'{"x":1,"x":2}')

    def test_nonfinite_json(self):
        for token in (b"NaN", b"Infinity", b"-Infinity", b"1e999"):
            with self.subTest(token=token), self.assertRaises(ValueError):
                m.document(b'{"x":' + token + b'}')

    def test_structure_depth_before_parse(self):
        with mock.patch.object(m.json, "loads", side_effect=AssertionError("parsed oversized depth")), self.assertRaises(ValueError):
            m.document(b'{"x":' + b'[' * 33 + b'0' + b']' * 33 + b'}')

    def test_value_population(self):
        with mock.patch.object(m.json, "loads", side_effect=AssertionError("parsed oversized population")), self.assertRaises(ValueError):
            m.document(encoded({"values": [None] * m.MAX_VALUES}))

    def test_source_advisory_authority_repacked(self):
        self.docs["planning_preview"]["codebase_source_delta_advisory"]["authority"]["proof_authority"] = True
        self.docs["cold_planning_preview"] = copy.deepcopy(self.docs["planning_preview"])
        with self.assertRaises(ValueError):
            self.run_packet()

    def test_request_root_bool_contract(self):
        self.refused(lambda d: d["authored_planning_inputs"]["request"]["roots"].update(contract_version=True))

    def test_scheduler_lane_cost_disagreement(self):
        self.refused(lambda d: d["resource_admission"]["metrics"]["lanes"]["trainer"].update(wait_seconds_total=10.0))

    def test_file_preallocation_bound(self):
        path = self.workspace / "large"
        path.write_bytes(b'x' * (m.MAX_FILE + 1))
        with self.assertRaises(ValueError):
            m.Capture().read(path)

    def test_cache_preallocation_bound(self):
        path = self.workspace / "one"
        path.write_bytes(b'x')
        capture = m.Capture()
        capture.total = m.MAX_BYTES
        with self.assertRaises(ValueError):
            capture.read(path, maximum=1)

    def test_cache_file_count_bound(self):
        path = self.workspace / "one"
        path.write_bytes(b'x')
        capture = m.Capture()
        capture.files = {Path(f'/synthetic/{i}'): b'x' for i in range(m.MAX_FILES)}
        with self.assertRaises(ValueError):
            capture.read(path, maximum=1)

    def test_deadline(self):
        with mock.patch.object(m.time, "monotonic", return_value=121), self.assertRaises(ValueError):
            m.Capture(started=0).deadline()

    def test_fifo_nonblocking_refusal(self):
        path = self.workspace / "fifo"
        os.mkfifo(path)
        with self.assertRaises(ValueError):
            m.Capture.raw(path, 1)

    def test_symlink_refusal(self):
        path = self.workspace / "real"
        path.write_bytes(b'{}')
        link = self.workspace / "link"
        link.symlink_to(path)
        with self.assertRaises(ValueError):
            m.Capture.raw(link, 2)

    def test_capture_identity_same_bytes_replaced(self):
        path = self.workspace / "regular"
        path.write_bytes(b'{}')
        capture = m.Capture()
        capture.read(path, maximum=2)
        replacement = self.workspace / "replacement"
        replacement.write_bytes(b'{}')
        replacement.replace(path)
        with self.assertRaises(ValueError):
            capture.stable()

    def late_mutation(self, action):
        manifest, anchor = packet(self.workspace, self.docs, self.paths)
        real = m.write_new
        def write(path, raw):
            real(path, raw)
            if path.name == "successor_planning_custody.json":
                action(self.workspace / "out")
        with mock.patch.object(m, "PUBLIC_ANCHOR", anchor), mock.patch.object(m, "write_new", side_effect=write), self.assertRaises((ValueError, OSError)):
            m.audit(manifest, self.workspace / "out")

    @staticmethod
    def replace_body(path):
        path.chmod(0o644)
        path.write_bytes(b'{}')

    def test_late_original(self):
        self.late_mutation(lambda _: self.replace_body(self.paths["resource_admission"]))

    def test_late_manifest(self):
        self.late_mutation(lambda _: self.replace_body(self.workspace / "input.json"))

    def test_late_copy(self):
        self.late_mutation(lambda out: self.replace_body(out / "retained/09-resource_admission.json"))

    def test_late_nested_receipt(self):
        self.late_mutation(lambda out: self.replace_body(out / "selected_custody.json"))

    def test_late_main_report(self):
        self.late_mutation(lambda out: self.replace_body(out / "successor_planning_custody.json"))

    def test_late_extra_output_member(self):
        self.late_mutation(lambda out: (out / "unselected.json").write_bytes(b'{}'))

    def test_local_nested_path_cannot_escape(self):
        real = m.bounded_canonical
        def serialize(value, maximum):
            if value.get("schema") == m.SCHEMA:
                value["custody"]["local_receipt"]["path"] = str(self.workspace / "escaped.json")
            return real(value, maximum)
        with mock.patch.object(m, "bounded_canonical", side_effect=serialize), self.assertRaises(ValueError):
            self.run_packet()

    def test_bounded_output_serialization(self):
        with self.assertRaises(ValueError):
            m.bounded_canonical({"large": "x" * 1000}, 64)

    def test_existing_output_refused(self):
        (self.workspace / "out").mkdir()
        with self.assertRaises(ValueError):
            self.run_packet()

    def test_closed_relocated_map(self):
        manifest, anchor = packet(self.workspace, self.docs, self.paths)
        mapping = {str(manifest): str(manifest), **{str(path): str(path) for path in self.paths.values()}, "/unselected": "/unselected"}
        with mock.patch.object(m, "PUBLIC_ANCHOR", anchor), self.assertRaises(ValueError):
            m.audit(manifest, self.workspace / "out", relocated_sources=mapping)

    def test_explicit_relocated_receiving(self):
        manifest, anchor = packet(self.workspace, self.docs, self.paths)
        destination = self.workspace / "relocated"
        destination.mkdir()
        mapping = {}
        for index, logical in enumerate((manifest, *self.paths.values())):
            physical = destination / f"{index:02}.json"
            physical.write_bytes(logical.read_bytes())
            mapping[str(logical)] = str(physical)
            logical.unlink()
        with mock.patch.object(m, "PUBLIC_ANCHOR", anchor), mock.patch("os.system", side_effect=AssertionError("exec forbidden")):
            report = m.audit(manifest, self.workspace / "out", relocated_sources=mapping)
        self.assertIs(report["qualified"], True)


if __name__ == "__main__":
    unittest.main()
