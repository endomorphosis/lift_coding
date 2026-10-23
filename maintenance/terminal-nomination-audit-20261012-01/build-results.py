"""Summarize final independently pinned public validation without extending claims."""
import hashlib
import json
from pathlib import Path

stage = Path(__file__).resolve().parent
def read(name):
    return json.loads((stage / name).read_bytes())
def pin(name):
    body = (stage / name).read_bytes()
    return {"path": name, "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()}
def write(name, value):
    path = stage / name
    assert not path.exists()
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")

focused = read("final-focused-validation.json")
sources = read("source-manifest.json")
preservation = read("preservation-check.json")
host = read("host-model-audit-04/qualification.json")
installed = read("installed-audit-qualification-02/qualification.json")
tokens = read("installed-local-packet-token-measurement.json")
assert focused["all_selected_cases_passed"] and preservation["all_checks_passed"]
assert host["qualified"] and installed["qualified"] and tokens["qualified"]
assert len(sources["files"]) == 6 and sources["patch_applies_cleanly_to_captured_baseline"]
actual = installed["audit"]
assert len(actual["observations"]) == 12 and len(actual["negatives"]) == 4
assert actual["all_nineteen_task_requirements_residual"]
assert len(actual["imported_producer_provenance"]["actual_imported_producers"]) == 10
next_work = {
    "schema": "catalog-audit-next-work@1",
    "priority": [
        {"step": 1, "work": "Qualify the actual prepare/review/resume driver lifecycle and retained Harbor task container.",
         "acceptance": "Fresh task-bound signed review, real driver dispatch across both phases, original task image retained, worker isolation, and cumulative budgets account for preparation plus resumed execution."},
        {"step": 2, "work": "Run paired baseline and compact sessions with the same public task and comparable runtime/model settings.",
         "acceptance": "Count complete provider input/output/cache/reasoning usage across the entire session, including catalogs, metadata lookups, source/fact replies and repair retries; retain task outcome, cost and timing. Local packet counts are not substituted for usage."},
        {"step": 3, "work": "Measure when reviewed catalogs and bounded source/fact retrieval repay their prompt overhead.",
         "acceptance": "Join the ten independently pinned producers, actual token receipts and historical whole-input audit. Evaluate expanded, compact, identifier and demand-driven variants without losing mandatory requirements or accepting stale/current authority."},
        {"step": 4, "work": "Continue Codebase IR equivalence and proof-index qualification before adding planner authority.",
         "acceptance": "Bind repository/tree/source hashes to AST, graph, vectors and contracts; keep learned projections distinct from verified source semantics, replay formal obligations with the actual selected prover, invalidate proof-cache entries on changed dependencies, and retain counterexamples."},
        {"step": 5, "work": "Qualify on-the-fly training and convergence on held-out Terminal Bench repositories.",
         "acceptance": "Authenticated training traces/checkpoints and held-out semantic reconstruction metrics; distinguish finite optimization certificates from behavioral source equivalence, full task satisfaction and mathematical convergence claims."},
        {"step": 6, "work": "Version the inclusion receipt if cross-runtime historical replay becomes necessary.",
         "acceptance": "Independently validated canonical CLI argv/prefix provenance and full byte replay, with compatibility tests for existing @1 receipts; current @1 remains restricted to the same trusted runtime paths."}
    ],
    "all_nineteen_requirements_remain_residual": True,
    "provider_session_token_savings_source_equivalence_task_satisfaction_or_convergence_established": False
}
write("next-work.json", next_work)
summary = {
    "schema": "catalog-audit-stage-result@1", "qualified": True,
    "outcome": "Reviewed source nominations are included in exact complete task-model-input historical reconstruction from protected captured metadata and original signed Git blobs, including after changed publication and worktree retirement.",
    "validation": focused, "source_package": pin("source-manifest.json"), "changes_patch": pin("changes.patch"),
    "public_preservation": {"receipt": pin("preservation-check.json"), "checks": preservation["pin_checks"],
        "unique_paths": preservation["unique_checked_paths"], "all_checks_passed": True},
    "host_actual_matrix": {"receipt": pin("host-model-audit-04/qualification.json"), "positive_cases": 12, "negative_cases": 4},
    "installed_actual_matrix": {"receipt": pin("installed-audit-qualification-02/qualification.json"), "positive_cases": 12,
        "negative_cases": 4, "actual_imported_producer_hash_joins": 10,
        "python": actual["imported_producer_provenance"]["python_version"],
        "external_network_detached": True, "fresh_container_removed": installed["fresh_qualification_container_removed"]},
    "local_complete_packet_token_measurement": {"receipt": pin("installed-local-packet-token-measurement.json"),
        "modes": tokens["modes"], "tokenizer": tokens["tokenizer"], "provider_usage_measured": False},
    "all_nineteen_requirements_residual": True,
    "same_trusted_runtime_paths_required": True, "cross_runtime_replay_supported": False,
    "historical_identity_implies_current_freshness_or_dispatch_authority": False,
    "actual_Harbor_task_image_full_driver_review_lifecycle_qualified": False,
    "source_equivalence_full_task_satisfaction_or_convergence_proved": False,
    "provider_total_session_token_savings_established": False,
    "provider_calls": 0, "manual_qualification_training_steps": 0, "prover_invocations": 0,
    "production_training_defaults_changed": False, "budget_ledger_changed": False,
    "remote_publication_performed": False, "original_dirty_checkout_or_git_index_mutated": False,
    "retained_failures": pin("retained-public-harness-failures-installed.json"), "next_work": pin("next-work.json")
}
write("result-summary.json", summary)
print(json.dumps(pin("result-summary.json")))
