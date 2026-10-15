"""Summarize scoped public evidence and the remaining supervisor work."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

STAGE = Path(__file__).resolve().parent


def load(name: str):
    return json.loads((STAGE / name).read_text())


def pin(name: str):
    raw = (STAGE / name).read_bytes()
    return {"path": name, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def write(name: str, data):
    (STAGE / name).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def main():
    native = load("public-native-fixture-01/summary.json")
    public = load("public-nomination-qualification-02/qualification.json")
    source = load("source-manifest.json")
    focused = load("final-focused-validation.json")
    preservation = load("preservation-check.json")
    review = load("final-independent-review.json")
    assert public["qualified"] and review["review_passed"]
    assert focused["qualified"] and focused["latest_distinct_classname_name_cases"] == 235
    assert preservation["all_checks_passed"]
    assert sum(case["complete_output_bytes"] for case in public["cases"]) == 19798
    assert sum(case["sum_independent_local_output_tokens"] for case in public["cases"]) == 7319
    tasks = [
        {
            "priority": 1,
            "work": "Make reviewed source nomination usable by the coding worker.",
            "implementation": [
                "Plumb the paired review path/digest through the supervisor entry point and runtime packaging; retain an explicit opt-in and unchanged defaults.",
                "Teach the context compiler and worker router to recognize the paired nomination metadata and expose the bounded reader with independently bound task, frontier, native artifact, contract, instruction and review identities.",
                "Provide a compact candidate catalog with row handles and residual requirement IDs; keep full contracts and index snapshots out of the prompt.",
                "Qualify actual signed admission, native context hydration and an installed archive in a fresh sandbox before a provider run.",
            ],
            "acceptance": [
                "The deployed worker can read an explicitly nominated off-query symbol; an unreviewed row and substituted pins are refused.",
                "Default full/compact retrieval behavior is preserved and no task instructions or signed planning inputs are rewritten.",
                "Source existence and reviewed row selection remain descriptive evidence rather than behavioral satisfaction.",
            ],
        },
        {
            "priority": 2,
            "work": "Reduce repeated response provenance without weakening source binding.",
            "implementation": [
                "Use one verified manifest plus parent-bound compact source/fact pages and continuation deltas; the verifier must independently resolve the pinned parent.",
                "Cache verified structural replay using task, repository tree, source manifests, index/extractor/schema versions, dependency scope and reader configuration as keys; invalidate on any change.",
                "Keep cache misses, stale dependencies and unresolved facts explicit. A cache hit never upgrades a learned candidate to a proved contract.",
                "Measure complete serialized output bytes and local tokens, including handles and first-manifest cost, for both one-page and multi-page sessions.",
            ],
            "acceptance": [
                "Exact source/fact reconstruction, UTF-8 paging, byte and token caps, post-counter guards and independent pins still pass.",
                "Report the break-even call count and replay cost; do not infer provider session savings from local packet counts.",
            ],
        },
        {
            "priority": 3,
            "work": "Admit current source evidence before symbolic planning.",
            "implementation": [
                "Create a pre-plan source evidence baseline with explicit observation types and signed admission policy rather than reusing the post-plan sidecar as authority.",
                "Join IntentIR requirement IDs to independently checked source observations; keep symbol existence, candidate relevance, checked preconditions, behavioral obligations and task completion distinct.",
                "Implement imports/aliases, receiver resolution, global initialization and control/data-flow coverage incrementally; each unsupported category remains not_analyzed with unknown counts.",
                "Only a checker receipt with stated assumptions may discharge an obligation. Replan when the repository changes and invalidate affected evidence.",
            ],
            "acceptance": [
                "The planner consumes admitted structural observations with provenance and leaves behavioral requirements residual unless separately checked.",
                "Changing source or task bindings invalidates observations, plans and relevant proof-cache entries.",
                "Task ambiguity is retained in the contract; the public header fixture is not silently interpreted as a complete task specification.",
            ],
        },
        {
            "priority": 4,
            "work": "Build typed CodebaseIR and versioned DuckDB/DuckLake projections.",
            "implementation": [
                "Scan public repository units into deterministic source/AST, qualified symbol, import, call, receiver, data-flow, contract, effect and dependency records with source spans and confidence/coverage fields.",
                "Store repository tree, source blob, IR schema/extractor/config identities, evidence status, assumptions, checker versions and invalidation edges in native metadata. Keep AST/KG/vectors/contracts as projections of the same pinned IR.",
                "Use DuckDB/Quack/DuckLake through qualified interfaces with explicit transaction ownership and snapshot identities; avoid hidden process-global metadata-owner activation.",
                "Represent proof obligations and receipts separately from candidate assertions; index unknown/unsupported obligations as well as successful proofs.",
            ],
            "acceptance": [
                "A fresh scan and a replayed cache agree on source identities, deterministic records and all projection joins.",
                "Source or dependency mutations invalidate the affected vectors, capsules, contracts and proof receipts without masking uncovered units.",
                "No learned encoder output is treated as source semantics or a checked proof.",
            ],
        },
        {
            "priority": 5,
            "work": "Train a repository-adapted encoder against a fixed source-derived IR.",
            "implementation": [
                "Train small reproducible encoder/decoder baselines on public Terminal Bench repository snapshots using source-separated held-out splits and explicit training-only metadata.",
                "Keep the canonical typed IR independent of model weights; model candidates must decode to the schema and pass deterministic source joins before planning use.",
                "Log reconstruction loss, schema-valid rate, symbol retrieval, requirement-to-candidate recall, held-out performance, compute and all preparation/model tokens.",
                "Bound on-the-fly adaptation and compare its cost against an untrained native AST/lexical retrieval baseline; persist model/data/config seeds and checkpoint identities.",
            ],
            "acceptance": [
                "Held-out source retrieval and validated reconstruction improve under a prespecified evaluation; test/task verifier data do not leak into training.",
                "Observed training loss convergence is reported as empirical. A mathematical convergence theorem requires explicit objective and optimizer assumptions and a checked proof.",
                "End-to-end task success and total session tokens remain separate measured outcomes.",
            ],
        },
        {
            "priority": 6,
            "work": "Project supported IR obligations into formal logic and qualify their proofs.",
            "implementation": [
                "Discover actual ipfs_datasets_py logic-family and Lean capabilities from pinned code; publish a supported/unsupported translation matrix for IR constructs.",
                "Generate typed obligations with explicit operational semantics, assumptions and translation receipts; compile supported Lean modules without admitting unproved placeholders.",
                "Prove translation/refinement and source-to-model equivalence for a deliberately bounded subset before making broader equivalence claims.",
                "Cache checked proof receipts by source, IR, obligation, assumptions, translator, prover and toolchain identity; invalidate whenever any dependency changes.",
            ],
            "acceptance": [
                "Lean compilation and proof checking are reproducible, with no sorry/admitted assumptions presented as proved obligations.",
                "A successful projected theorem is distinguished from Python source equivalence, full task satisfaction and model convergence.",
                "Counterexamples, unsupported constructs and proof failures remain visible to the planner.",
            ],
        },
        {
            "priority": 7,
            "work": "Measure paired full-session token use and task success.",
            "implementation": [
                "Compare native retrieval, reviewed source access, compact provenance, semantic capsules, conservative minification and any trained IR retrieval on repeated matched tasks.",
                "Count preparation/planning/capsule/proof model calls, worker/audit/retries and readbacks using provider usage; cached input and reasoning output are subcategories, not extra tokens.",
                "Keep missing usage unknown and report lower bounds rather than invented totals; pair task outcomes with latency, compute, calls, failure/refusal rates and complete tokens.",
                "Use existing Terminal Bench task verifiers for task outcomes and independent audits for evidence quality; keep runtime budget enforcement distinct from a post-run ledger.",
            ],
            "acceptance": [
                "A prespecified repeated comparison improves complete provider token use while preserving task success and evidence validity.",
                "Smaller prompts, local token counts and lower training loss alone do not meet the acceptance criterion.",
            ],
        },
    ]
    write("next-work.json", {
        "schema": "intent-source-nomination-next-work@1",
        "objective": "Reduce complete ipfs_accelerate_py supervisor Terminal Bench session tokens while retaining task success and checked source-grounded planning.",
        "current_stage": "Explicit reviewed source-row nominations, protected readback and optional post-plan context attachment qualified in host/unit scopes.",
        "ordered_work": tasks,
        "current_unresolved": {
            "task_requirements_residual": 19, "reviewed_unknown_symbol_requirements": 17,
            "reviewed_unbound_requirements": 16,
            "dependency_categories": public["reviewed_unknown_census"]["dependencies"],
            "review_authentication": False, "source_semantics_checked": False,
            "automatic_worker_consumption": False, "admitted_planner_current_facts": False,
            "installed_runtime_qualified": False, "provider_total_token_savings_established": False,
            "codebase_encoder_trained_in_this_stage": False,
        },
        "basis": [pin("public-nomination-qualification-02/qualification.json"), pin("final-independent-review.json")],
    })
    write("result-summary.json", {
        "schema": "intent-source-nomination-stage-result@1",
        "outcome": "Implemented reviewed IntentIR-to-current-source nominations and protected bounded source/fact readback, with optional post-plan worker-context attachment.",
        "source": pin("source-manifest.json"), "patch": pin("changes.patch"),
        "implementation": {
            "changed_existing_files": 3, "new_files": 5,
            "canonical_pure_nomination_and_validator": True,
            "explicit_review_and_independent_digest_required_for_symbol_rows": True,
            "native_full_row_AST_source_span_and_fact_replay": True,
            "old_reader_still_requires_original_query_hit": True,
            "bounded_protected_capture_and_final_post_token_counter_guards": True,
            "whole_public_operation_metadata_factory_bypass_and_context_restoration": True,
            "context_attachment_scope": "optional_postplan_worker_context_only",
            "default_retrieval_behavior_changed": False,
            "signed_planning_inputs_modified": False, "symbolic_planner_current_facts_added": 0,
        },
        "validation": {"receipt": pin("final-focused-validation.json"), "focused_distinct_passed": 235, "whole_repository_pass_claimed": False},
        "native_public_qualification": {
            "receipt": pin("public-nomination-qualification-02/qualification.json"),
            "native_symbols_and_fact_rows": native["native_symbols"],
            "vectors": native["vectors"], "ducklake": public["ducklake_projection"],
            "literal_query_hits": public["literal_query_hits"],
            "reviewed_candidates": public["reviewed_candidates"],
            "candidate_selection": "Separate authored selectors bound to two requirements; identity/provenance, not authenticated task meaning or a behavioral proof.",
            "successful_CLI_calls": 4, "refused_CLI_calls": 7,
            "original_seven_fixture_file_bytes_and_witnesses_unchanged": public["original_fixture_file_bytes_and_witnesses_unchanged"],
            "fresh_final_attempt_metadata_owner_activated": public["unrelated_metadata_owner_activated"],
            "cases": public["cases"], "complete_output_bytes": 19798,
            "sum_independent_LOCAL_output_tokens": 7319,
            "tokenizer": public["local_tokenizer"],
            "timing_scope": "Host qualification including two preparations and subprocess overhead; concurrent tests were running. Not an isolated latency benchmark.",
            "qualification_seconds": public["seconds"], "preparation_seconds": public["prepare_seconds"],
            "persisted_nomination_wrapper_bytes": public["artifact_bytes"],
            "persisted_wrappers_are_coding_prompt_text": False,
            "generic_unknown_census": public["generic_unknown_census"],
            "reviewed_unknown_census": public["reviewed_unknown_census"],
            "all_requirements_remain_residual": True,
        },
        "retained_failure_and_fix": {
            "failed_attempt": pin("public-nomination-failure-01.json"),
            "trace": pin("metadata-factory-trace-01.json"),
            "first_attempt_qualified": False,
            "first_attempt_created_fresh_unrelated_sentinel": True,
            "sentinel_body_or_existing_owner_database_read": False,
            "cause": "CID canonical and validated metadata mirrors ran outside the earlier AST-only guard.",
            "fix": "Guard the full exported pure builder/validator and both protected reader/preparer operations; retained golden artifact bytes match before the guard.",
            "first_attempt_published_nomination_or_invoked_CLI": False,
            "earlier_test_failures_retained": True,
        },
        "independent_review": pin("final-independent-review.json"),
        "preservation": pin("preservation-check.json"), "next_work": pin("next-work.json"),
        "limits": {
            "context_test_admission_and_prior_hydration_are_explicit_stubs": True,
            "actual_signed_admission_or_installed_worker_qualified": False,
            "automatic_coding_prompt_or_router_consumption_qualified": False,
            "review_or_source_custody_authenticated": False,
            "same_owner_source_immutability_claimed": False,
            "proof_authority": False, "mutation_authority": False,
            "execution_authority": False, "completion_authority": False,
            "source_to_model_equivalence_proved": False,
            "full_task_satisfaction_proved": False, "model_convergence_proved": False,
            "provider_total_session_token_savings_established": False,
            "provider_calls": 0, "training_steps": 0, "prover_invocations": 0,
            "target_module_imports": 0, "official_task_verifier_invocations": 0,
            "runtime_archive_built_or_installed": False, "remote_publication_performed": False,
            "original_dirty_checkout_or_git_index_mutated": False,
        },
    })
    print(json.dumps({"result": pin("result-summary.json"), "next_work": pin("next-work.json")}))


if __name__ == "__main__":
    main()
