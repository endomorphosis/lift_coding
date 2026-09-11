# Proof-Carrying Neurosymbolic Supervision: State, Logic-Governed Decisions, and Test-Evidence Reuse — objective heap

Reviewed scope: `papers/completion/neurosymbolic_supervision/review.md`. Executable board: `papers/completion/neurosymbolic_supervision/paper.todo.md`.

A completed paper means a reproducible, anonymous submission candidate with supported claims.
It does not mean OpenReview submission, acceptance, or completion of unrun experiments.

## NS-G000 Complete the evidence-backed workshop paper

- Status: active
- Parent: 
- Depends on:
- Fib priority: 1
- Priority: P0
- Track: neurosymbolic_supervision
- Bundle: neurosymbolic_supervision/NS-G000
- Goal: Complete an evidence-backed, anonymous and reproducible 2026 AI for Verifiable Coding workshop manuscript for the frozen neurosymbolic supervision core: recover editable sources; qualify the current integrated implementation; execute and independently score genuine matched benchmarks and ablations; replace all placeholders with measured, unavailable, or explicitly narrowed claims; and prepare a checked author-review submission package without inventing results or submitting automatically.
- Outputs: papers/completion/neurosymbolic_supervision/manuscript/main.tex, papers/completion/neurosymbolic_supervision/manuscript/references.bib, papers/completion/neurosymbolic_supervision/manuscript/BUILD.md, papers/completion/neurosymbolic_supervision/audit/source_recovery.md, papers/completion/neurosymbolic_supervision/audit/reconstruction_discrepancies.json, papers/completion/neurosymbolic_supervision/artifacts/source_forest.json, papers/completion/neurosymbolic_supervision/artifacts/capabilities.json, papers/completion/neurosymbolic_supervision/audit/implementation_inventory.json, papers/completion/neurosymbolic_supervision/audit/preliminary_evidence.json, papers/completion/neurosymbolic_supervision/audit/claim_evidence_matrix.json, papers/completion/neurosymbolic_supervision/protocol/scope.md, papers/completion/neurosymbolic_supervision/protocol/deadline_plan.md, papers/completion/neurosymbolic_supervision/protocol/preregistered_protocol.md, papers/completion/neurosymbolic_supervision/protocol/experiment_manifest.json, papers/completion/neurosymbolic_supervision/protocol/measurement_schema.json, papers/completion/neurosymbolic_supervision/benchmark/tasks.jsonl, papers/completion/neurosymbolic_supervision/benchmark/splits.json, papers/completion/neurosymbolic_supervision/benchmark/oracle_manifest.json, papers/completion/neurosymbolic_supervision/benchmark/provenance.md, papers/completion/neurosymbolic_supervision/audit/leakage_audit.json, papers/completion/neurosymbolic_supervision/experiments/run_comparison.py, papers/completion/neurosymbolic_supervision/experiments/score_runs.py, papers/completion/neurosymbolic_supervision/experiments/README.md, papers/completion/neurosymbolic_supervision/experiments/receipt_schema.json, papers/completion/neurosymbolic_supervision/audit/runner_validation.json, papers/completion/neurosymbolic_supervision/qualification/context_cases.json, papers/completion/neurosymbolic_supervision/qualification/context_results.jsonl, papers/completion/neurosymbolic_supervision/qualification/context_report.md, papers/completion/neurosymbolic_supervision/qualification/provider_gate_cases.json, papers/completion/neurosymbolic_supervision/qualification/provider_gate_receipts.jsonl, papers/completion/neurosymbolic_supervision/qualification/provider_gate_report.md, papers/completion/neurosymbolic_supervision/qualification/logic_cases.json, papers/completion/neurosymbolic_supervision/qualification/logic_receipts.jsonl, papers/completion/neurosymbolic_supervision/qualification/logic_profiles.json, papers/completion/neurosymbolic_supervision/qualification/logic_report.md, papers/completion/neurosymbolic_supervision/qualification/reuse_profile.json, papers/completion/neurosymbolic_supervision/qualification/reuse_adapter_report.md, papers/completion/neurosymbolic_supervision/qualification/reuse_phase_cases.json, papers/completion/neurosymbolic_supervision/qualification/cold_oracle_results.jsonl, papers/completion/neurosymbolic_supervision/qualification/reuse_mutation_results.jsonl, papers/completion/neurosymbolic_supervision/qualification/reuse_analysis.json, papers/completion/neurosymbolic_supervision/qualification/sealer_fault_matrix.json, papers/completion/neurosymbolic_supervision/qualification/sealer_results.jsonl, papers/completion/neurosymbolic_supervision/qualification/recovery_receipts.jsonl, papers/completion/neurosymbolic_supervision/qualification/sealer_recovery_report.md, papers/completion/neurosymbolic_supervision/qualification/end_to_end_witness.json, papers/completion/neurosymbolic_supervision/qualification/end_to_end_trace.jsonl, papers/completion/neurosymbolic_supervision/qualification/end_to_end_case_study.md, papers/completion/neurosymbolic_supervision/qualification/native_profile.json, papers/completion/neurosymbolic_supervision/qualification/native_results.jsonl, papers/completion/neurosymbolic_supervision/qualification/native_scope_decision.md, papers/completion/neurosymbolic_supervision/qualification/extensions_scope.json, papers/completion/neurosymbolic_supervision/qualification/extension_holdout_protocol.md, papers/completion/neurosymbolic_supervision/qualification/extension_results.jsonl, papers/completion/neurosymbolic_supervision/qualification/extensions_report.md, papers/completion/neurosymbolic_supervision/pilot/results.jsonl, papers/completion/neurosymbolic_supervision/pilot/readiness_report.md, papers/completion/neurosymbolic_supervision/artifacts/final_experiment_freeze.json, papers/completion/neurosymbolic_supervision/protocol/final_run_manifest.json, papers/completion/neurosymbolic_supervision/runs/main/manifest.json, papers/completion/neurosymbolic_supervision/runs/main/attempts.jsonl, papers/completion/neurosymbolic_supervision/runs/main/provider_receipts.jsonl, papers/completion/neurosymbolic_supervision/runs/main/resource_measurements.jsonl, papers/completion/neurosymbolic_supervision/runs/main/deviations.md, papers/completion/neurosymbolic_supervision/runs/ablations/manifest.json, papers/completion/neurosymbolic_supervision/runs/ablations/attempts.jsonl, papers/completion/neurosymbolic_supervision/runs/ablations/resource_measurements.jsonl, papers/completion/neurosymbolic_supervision/runs/ablations/deviations.md, papers/completion/neurosymbolic_supervision/analysis/analyze.py, papers/completion/neurosymbolic_supervision/analysis/results.json, papers/completion/neurosymbolic_supervision/analysis/statistical_report.md, papers/completion/neurosymbolic_supervision/analysis/cost_report.md, papers/completion/neurosymbolic_supervision/manuscript/generated/table17.tex, papers/completion/neurosymbolic_supervision/manuscript/generated/ablations.tex, papers/completion/neurosymbolic_supervision/manuscript/generated/figures/, papers/completion/neurosymbolic_supervision/analysis/boundary_witnesses.json, papers/completion/neurosymbolic_supervision/manuscript/generated/table18.tex, papers/completion/neurosymbolic_supervision/audit/final_claim_evidence_matrix.json, papers/completion/neurosymbolic_supervision/analysis/failure_cases.md, papers/completion/neurosymbolic_supervision/audit/reference_audit.md, papers/completion/neurosymbolic_supervision/audit/artifact_citation_map.json, papers/completion/neurosymbolic_supervision/audit/related_paper_overlap.md, papers/completion/neurosymbolic_supervision/audit/verified_references.bib, papers/completion/neurosymbolic_supervision/manuscript/paper.pdf, papers/completion/neurosymbolic_supervision/audit/manuscript_result_checks.json, papers/completion/neurosymbolic_supervision/audit/revision_notes.md, papers/completion/neurosymbolic_supervision/audit/formal_argument_review.md, papers/completion/neurosymbolic_supervision/audit/assumption_gate_map.json, papers/completion/neurosymbolic_supervision/manuscript/formal_arguments.tex, papers/completion/neurosymbolic_supervision/release/README.md, papers/completion/neurosymbolic_supervision/release/manifest.json, papers/completion/neurosymbolic_supervision/release/reproduce.sh, papers/completion/neurosymbolic_supervision/release/supplement.zip, papers/completion/neurosymbolic_supervision/release/paper.pdf, papers/completion/neurosymbolic_supervision/audit/anonymity_report.md, papers/completion/neurosymbolic_supervision/audit/llm_use_disclosure.md, papers/completion/neurosymbolic_supervision/audit/author_attestations.md, papers/completion/neurosymbolic_supervision/audit/workshop_compliance.json, papers/completion/neurosymbolic_supervision/manuscript/checklist.tex, papers/completion/neurosymbolic_supervision/manuscript/neurips_2026_vericode.sty, papers/completion/neurosymbolic_supervision/submission/template_inputs.json, papers/completion/neurosymbolic_supervision/release/FINAL_REVIEW.md, papers/completion/neurosymbolic_supervision/release/checksums.sha256, papers/completion/neurosymbolic_supervision/audit/final_readiness.json, papers/completion/neurosymbolic_supervision/audit/final_placeholder_scan.json
- Gap task: NS-001, NS-002, NS-003, NS-004, NS-005, NS-006, NS-007, NS-008, NS-009, NS-010, NS-011, NS-012, NS-013, NS-014, NS-015, NS-016, NS-017, NS-018, NS-019, NS-020, NS-021, NS-022, NS-023, NS-024, NS-025
- Acceptance: All linked task criteria have current artifact and validation evidence; numerical claims trace to real runs; author handoff is explicit.
- Validation: python3 scripts/paper_supervisors.py verify-goal --paper neurosymbolic_supervision --goal NS-G000

## NS-SG1 Freeze a recoverable manuscript and supported scientific scope

- Status: active
- Parent: NS-G000
- Depends on:
- Fib priority: 2
- Priority: P0
- Track: neurosymbolic_supervision
- Bundle: neurosymbolic_supervision/NS-SG1
- Goal: Recover editable sources independently of code/protocol work, inventory the exact loaded source forest, and distinguish implemented/evaluated mechanisms from optional plans.
- Outputs: papers/completion/neurosymbolic_supervision/manuscript/main.tex, papers/completion/neurosymbolic_supervision/manuscript/references.bib, papers/completion/neurosymbolic_supervision/manuscript/BUILD.md, papers/completion/neurosymbolic_supervision/audit/source_recovery.md, papers/completion/neurosymbolic_supervision/audit/reconstruction_discrepancies.json, papers/completion/neurosymbolic_supervision/artifacts/source_forest.json, papers/completion/neurosymbolic_supervision/artifacts/capabilities.json, papers/completion/neurosymbolic_supervision/audit/implementation_inventory.json, papers/completion/neurosymbolic_supervision/audit/preliminary_evidence.json, papers/completion/neurosymbolic_supervision/audit/claim_evidence_matrix.json, papers/completion/neurosymbolic_supervision/protocol/scope.md, papers/completion/neurosymbolic_supervision/protocol/deadline_plan.md
- Gap task: NS-001, NS-002, NS-003
- Acceptance: All linked task criteria have current artifact and validation evidence; numerical claims trace to real runs; author handoff is explicit.
- Validation: python3 scripts/paper_supervisors.py verify-goal --paper neurosymbolic_supervision --goal NS-SG1

## NS-SG2 Build a leakage-safe benchmark and instrumented comparison runner

- Status: active
- Parent: NS-G000
- Depends on:
- Fib priority: 3
- Priority: P0
- Track: neurosymbolic_supervision
- Bundle: neurosymbolic_supervision/NS-SG2
- Goal: Freeze tasks, hidden acceptance oracles, matched A–D conditions, resource metrics, and preregistered statistical and quality criteria.
- Outputs: papers/completion/neurosymbolic_supervision/protocol/preregistered_protocol.md, papers/completion/neurosymbolic_supervision/protocol/experiment_manifest.json, papers/completion/neurosymbolic_supervision/protocol/measurement_schema.json, papers/completion/neurosymbolic_supervision/benchmark/tasks.jsonl, papers/completion/neurosymbolic_supervision/benchmark/splits.json, papers/completion/neurosymbolic_supervision/benchmark/oracle_manifest.json, papers/completion/neurosymbolic_supervision/benchmark/provenance.md, papers/completion/neurosymbolic_supervision/audit/leakage_audit.json, papers/completion/neurosymbolic_supervision/experiments/run_comparison.py, papers/completion/neurosymbolic_supervision/experiments/score_runs.py, papers/completion/neurosymbolic_supervision/experiments/README.md, papers/completion/neurosymbolic_supervision/experiments/receipt_schema.json, papers/completion/neurosymbolic_supervision/audit/runner_validation.json
- Gap task: NS-004, NS-005, NS-006
- Acceptance: All linked task criteria have current artifact and validation evidence; numerical claims trace to real runs; author handoff is explicit.
- Validation: python3 scripts/paper_supervisors.py verify-goal --paper neurosymbolic_supervision --goal NS-SG2

## NS-SG3 Qualify the actual supervision and evidence boundaries

- Status: active
- Parent: NS-G000
- Depends on:
- Fib priority: 4
- Priority: P0
- Track: neurosymbolic_supervision
- Bundle: neurosymbolic_supervision/NS-SG3
- Goal: Exercise valid progress and adversarial rejection through current context, routing, translation, fixture reuse, sealing, restart, and retained optional mechanisms.
- Outputs: papers/completion/neurosymbolic_supervision/qualification/context_cases.json, papers/completion/neurosymbolic_supervision/qualification/context_results.jsonl, papers/completion/neurosymbolic_supervision/qualification/context_report.md, papers/completion/neurosymbolic_supervision/qualification/provider_gate_cases.json, papers/completion/neurosymbolic_supervision/qualification/provider_gate_receipts.jsonl, papers/completion/neurosymbolic_supervision/qualification/provider_gate_report.md, papers/completion/neurosymbolic_supervision/qualification/logic_cases.json, papers/completion/neurosymbolic_supervision/qualification/logic_receipts.jsonl, papers/completion/neurosymbolic_supervision/qualification/logic_profiles.json, papers/completion/neurosymbolic_supervision/qualification/logic_report.md, papers/completion/neurosymbolic_supervision/qualification/reuse_profile.json, papers/completion/neurosymbolic_supervision/qualification/reuse_adapter_report.md, papers/completion/neurosymbolic_supervision/qualification/reuse_phase_cases.json, papers/completion/neurosymbolic_supervision/qualification/cold_oracle_results.jsonl, papers/completion/neurosymbolic_supervision/qualification/reuse_mutation_results.jsonl, papers/completion/neurosymbolic_supervision/qualification/reuse_analysis.json, papers/completion/neurosymbolic_supervision/qualification/sealer_fault_matrix.json, papers/completion/neurosymbolic_supervision/qualification/sealer_results.jsonl, papers/completion/neurosymbolic_supervision/qualification/recovery_receipts.jsonl, papers/completion/neurosymbolic_supervision/qualification/sealer_recovery_report.md, papers/completion/neurosymbolic_supervision/qualification/end_to_end_witness.json, papers/completion/neurosymbolic_supervision/qualification/end_to_end_trace.jsonl, papers/completion/neurosymbolic_supervision/qualification/end_to_end_case_study.md, papers/completion/neurosymbolic_supervision/qualification/native_profile.json, papers/completion/neurosymbolic_supervision/qualification/native_results.jsonl, papers/completion/neurosymbolic_supervision/qualification/native_scope_decision.md, papers/completion/neurosymbolic_supervision/qualification/extensions_scope.json, papers/completion/neurosymbolic_supervision/qualification/extension_holdout_protocol.md, papers/completion/neurosymbolic_supervision/qualification/extension_results.jsonl, papers/completion/neurosymbolic_supervision/qualification/extensions_report.md
- Gap task: NS-007, NS-008, NS-009, NS-010, NS-011, NS-012, NS-013, NS-014, NS-015
- Acceptance: All linked task criteria have current artifact and validation evidence; numerical claims trace to real runs; author handoff is explicit.
- Validation: python3 scripts/paper_supervisors.py verify-goal --paper neurosymbolic_supervision --goal NS-SG3

## NS-SG4 Execute frozen main experiments and isolated ablations

- Status: active
- Parent: NS-G000
- Depends on:
- Fib priority: 5
- Priority: P0
- Track: neurosymbolic_supervision
- Bundle: neurosymbolic_supervision/NS-SG4
- Goal: Pilot separately, freeze final versions, then obtain genuine provider/runner/checker evidence under fixed budgets without relabeling replay fixtures.
- Outputs: papers/completion/neurosymbolic_supervision/pilot/results.jsonl, papers/completion/neurosymbolic_supervision/pilot/readiness_report.md, papers/completion/neurosymbolic_supervision/artifacts/final_experiment_freeze.json, papers/completion/neurosymbolic_supervision/protocol/final_run_manifest.json, papers/completion/neurosymbolic_supervision/runs/main/manifest.json, papers/completion/neurosymbolic_supervision/runs/main/attempts.jsonl, papers/completion/neurosymbolic_supervision/runs/main/provider_receipts.jsonl, papers/completion/neurosymbolic_supervision/runs/main/resource_measurements.jsonl, papers/completion/neurosymbolic_supervision/runs/main/deviations.md, papers/completion/neurosymbolic_supervision/runs/ablations/manifest.json, papers/completion/neurosymbolic_supervision/runs/ablations/attempts.jsonl, papers/completion/neurosymbolic_supervision/runs/ablations/resource_measurements.jsonl, papers/completion/neurosymbolic_supervision/runs/ablations/deviations.md
- Gap task: NS-016, NS-017, NS-018
- Acceptance: All linked task criteria have current artifact and validation evidence; numerical claims trace to real runs; author handoff is explicit.
- Validation: python3 scripts/paper_supervisors.py verify-goal --paper neurosymbolic_supervision --goal NS-SG4

## NS-SG5 Independently analyze outcomes and reconcile every claim

- Status: active
- Parent: NS-G000
- Depends on:
- Fib priority: 6
- Priority: P0
- Track: neurosymbolic_supervision
- Bundle: neurosymbolic_supervision/NS-SG5
- Goal: Compute uncertainty, full denominators, actual economics, positive/negative integration witnesses, conditional theorem assumptions, and explicit limitations.
- Outputs: papers/completion/neurosymbolic_supervision/analysis/analyze.py, papers/completion/neurosymbolic_supervision/analysis/results.json, papers/completion/neurosymbolic_supervision/analysis/statistical_report.md, papers/completion/neurosymbolic_supervision/analysis/cost_report.md, papers/completion/neurosymbolic_supervision/manuscript/generated/table17.tex, papers/completion/neurosymbolic_supervision/manuscript/generated/ablations.tex, papers/completion/neurosymbolic_supervision/manuscript/generated/figures/, papers/completion/neurosymbolic_supervision/analysis/boundary_witnesses.json, papers/completion/neurosymbolic_supervision/manuscript/generated/table18.tex, papers/completion/neurosymbolic_supervision/audit/final_claim_evidence_matrix.json, papers/completion/neurosymbolic_supervision/analysis/failure_cases.md, papers/completion/neurosymbolic_supervision/audit/formal_argument_review.md, papers/completion/neurosymbolic_supervision/audit/assumption_gate_map.json, papers/completion/neurosymbolic_supervision/manuscript/formal_arguments.tex
- Gap task: NS-019, NS-020, NS-023
- Acceptance: All linked task criteria have current artifact and validation evidence; numerical claims trace to real runs; author handoff is explicit.
- Validation: python3 scripts/paper_supervisors.py verify-goal --paper neurosymbolic_supervision --goal NS-SG5

## NS-SG6 Finish the scientific manuscript and references

- Status: active
- Parent: NS-G000
- Depends on:
- Fib priority: 7
- Priority: P0
- Track: neurosymbolic_supervision
- Bundle: neurosymbolic_supervision/NS-SG6
- Goal: Replace placeholders from generated evidence, sharpen novelty and scope, verify references/artifact links, and clearly distinguish the three related submissions.
- Outputs: papers/completion/neurosymbolic_supervision/audit/reference_audit.md, papers/completion/neurosymbolic_supervision/audit/artifact_citation_map.json, papers/completion/neurosymbolic_supervision/audit/related_paper_overlap.md, papers/completion/neurosymbolic_supervision/audit/verified_references.bib, papers/completion/neurosymbolic_supervision/manuscript/main.tex, papers/completion/neurosymbolic_supervision/manuscript/paper.pdf, papers/completion/neurosymbolic_supervision/audit/manuscript_result_checks.json, papers/completion/neurosymbolic_supervision/audit/revision_notes.md
- Gap task: NS-021, NS-022
- Acceptance: All linked task criteria have current artifact and validation evidence; numerical claims trace to real runs; author handoff is explicit.
- Validation: python3 scripts/paper_supervisors.py verify-goal --paper neurosymbolic_supervision --goal NS-SG6

## NS-SG7 Deliver an anonymous reproducible submission package

- Status: active
- Parent: NS-G000
- Depends on:
- Fib priority: 8
- Priority: P0
- Track: neurosymbolic_supervision
- Bundle: neurosymbolic_supervision/NS-SG7
- Goal: Use the official 2026 template/checklist, audit disclosures and anonymity, reproduce tables from raw evidence, and prepare a final independent author-review package without submission.
- Outputs: papers/completion/neurosymbolic_supervision/release/README.md, papers/completion/neurosymbolic_supervision/release/manifest.json, papers/completion/neurosymbolic_supervision/release/reproduce.sh, papers/completion/neurosymbolic_supervision/release/supplement.zip, papers/completion/neurosymbolic_supervision/release/paper.pdf, papers/completion/neurosymbolic_supervision/audit/anonymity_report.md, papers/completion/neurosymbolic_supervision/audit/llm_use_disclosure.md, papers/completion/neurosymbolic_supervision/audit/author_attestations.md, papers/completion/neurosymbolic_supervision/audit/workshop_compliance.json, papers/completion/neurosymbolic_supervision/manuscript/checklist.tex, papers/completion/neurosymbolic_supervision/manuscript/neurips_2026_vericode.sty, papers/completion/neurosymbolic_supervision/submission/template_inputs.json, papers/completion/neurosymbolic_supervision/release/FINAL_REVIEW.md, papers/completion/neurosymbolic_supervision/release/checksums.sha256, papers/completion/neurosymbolic_supervision/audit/final_readiness.json, papers/completion/neurosymbolic_supervision/audit/final_placeholder_scan.json
- Gap task: NS-024, NS-025
- Acceptance: All linked task criteria have current artifact and validation evidence; numerical claims trace to real runs; author handoff is explicit.
- Validation: python3 scripts/paper_supervisors.py verify-goal --paper neurosymbolic_supervision --goal NS-SG7
