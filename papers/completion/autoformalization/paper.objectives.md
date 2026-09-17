# Compiler-Guided Autoformalization with Adaptive Multi-View Representations — objective heap

Reviewed scope: `papers/completion/autoformalization/review.md`. Executable board: `papers/completion/autoformalization/paper.todo.md`.

A completed paper means a reproducible, anonymous submission candidate with supported claims.
It does not mean OpenReview submission, acceptance, or completion of unrun experiments.

## AF-G000 Complete the evidence-backed workshop paper

- Status: active
- Parent: 
- Depends on:
- Fib priority: 1
- Priority: P0
- Track: autoformalization
- Bundle: autoformalization/AF-G000
- Goal: Complete a reviewable workshop manuscript and reproducibility package establishing, with actual frozen evidence, whether compiler-guided shared representation learning improves independently judged source fidelity and useful checked proof coverage on unseen material; explicitly retain any unrun or unavailable conditions and prepare a concrete narrowed alternative if the full empirical scope cannot be finished.
- Outputs: papers/completion/autoformalization/manuscript/main.tex, papers/completion/autoformalization/manuscript/references.bib, papers/completion/autoformalization/evidence/source_recovery.json, papers/completion/autoformalization/evidence/source_discrepancies.md, papers/completion/autoformalization/protocol.md, papers/completion/autoformalization/config/experiment_plan.json, papers/completion/autoformalization/evidence/claim_task_map.json, papers/completion/autoformalization/evidence/deadline_scope_options.md, papers/completion/autoformalization/evidence/source_audit_private.json, papers/completion/autoformalization/evidence/runtime_capability_matrix.json, papers/completion/autoformalization/config/environment_manifest.json, papers/completion/autoformalization/data/corpus_manifest.json, papers/completion/autoformalization/data/splits.json, papers/completion/autoformalization/data/teacher_manifest.json, papers/completion/autoformalization/evidence/split_audit.json, papers/completion/autoformalization/data/annotation_guidelines.md, papers/completion/autoformalization/data/annotation_packets.jsonl, papers/completion/autoformalization/data/gold_facets.jsonl, papers/completion/autoformalization/evidence/annotation_provenance.json, papers/completion/autoformalization/evaluation/reference_semantics.py, papers/completion/autoformalization/evaluation/reference_results.json, papers/completion/autoformalization/data/minimal_pairs.jsonl, papers/completion/autoformalization/evidence/reference_provenance.json, papers/completion/autoformalization/evaluation/run_benchmark.py, papers/completion/autoformalization/evaluation/result_schema.json, papers/completion/autoformalization/evaluation/test_result_accounting.py, papers/completion/autoformalization/config/metrics.json, papers/completion/autoformalization/evaluation/inference_isolation.py, papers/completion/autoformalization/evaluation/test_inference_isolation.py, papers/completion/autoformalization/evidence/leakage_control_report.json, papers/completion/autoformalization/evidence/training_correctness.json, papers/completion/autoformalization/config/training_backend.json, papers/completion/autoformalization/evaluation/pipeline_arms.py, papers/completion/autoformalization/config/pipeline_arms.json, papers/completion/autoformalization/evidence/pipeline_arm_preflight.json, papers/completion/autoformalization/runs/training_baselines/manifest.json, papers/completion/autoformalization/runs/training_baselines/results.jsonl, papers/completion/autoformalization/checkpoints/baselines/manifest.json, papers/completion/autoformalization/data/proof_feedback_manifest.json, papers/completion/autoformalization/runs/proof_heads/results.jsonl, papers/completion/autoformalization/evidence/proof_head_isolation.json, papers/completion/autoformalization/runs/guidance_promotion/results.jsonl, papers/completion/autoformalization/evidence/guidance_export.json, papers/completion/autoformalization/evidence/consumer_activation.json, papers/completion/autoformalization/evidence/rollback_receipt.json, papers/completion/autoformalization/runs/compiler_repair/results.jsonl, papers/completion/autoformalization/evidence/repair_task_trace.json, papers/completion/autoformalization/evidence/compiler_patch.diff, papers/completion/autoformalization/evidence/repair_validation.json, papers/completion/autoformalization/evaluation/bridge_cases.py, papers/completion/autoformalization/data/policy_code_trace_cases.json, papers/completion/autoformalization/runs/bridge_validation/results.jsonl, papers/completion/autoformalization/evidence/translation_receipts.jsonl, papers/completion/autoformalization/runs/pipeline_comparison/manifest.json, papers/completion/autoformalization/runs/pipeline_comparison/results.jsonl, papers/completion/autoformalization/data/retrieval_judgments.jsonl, papers/completion/autoformalization/runs/retrieval/results.jsonl, papers/completion/autoformalization/runs/premise_selection/results.jsonl, papers/completion/autoformalization/config/retrieval_manifest.json, papers/completion/autoformalization/runs/proof_assistance/results.jsonl, papers/completion/autoformalization/runs/planning/results.jsonl, papers/completion/autoformalization/evidence/native_checker_receipts.jsonl, papers/completion/autoformalization/runs/domain_transfer/results.jsonl, papers/completion/autoformalization/evidence/domain_scope_matrix.json, papers/completion/autoformalization/evaluation/aggregate_costs.py, papers/completion/autoformalization/runs/costs/results.jsonl, papers/completion/autoformalization/evidence/cost_accounting.md, papers/completion/autoformalization/evaluation/analyze_results.py, papers/completion/autoformalization/results/table6_pipeline.tex, papers/completion/autoformalization/results/table11_training.tex, papers/completion/autoformalization/results/table13_assistance.tex, papers/completion/autoformalization/results/summary.json, papers/completion/autoformalization/results/hypothesis_report.md, papers/completion/autoformalization/evidence/final_claim_audit.json, papers/completion/autoformalization/evidence/bibliography_audit.md, papers/completion/autoformalization/artifact/README.md, papers/completion/autoformalization/artifact/manifest.json, papers/completion/autoformalization/artifact/S01_S40_map.json, papers/completion/autoformalization/submission/supplement.zip, papers/completion/autoformalization/evidence/anonymization_report.json, papers/completion/autoformalization/manuscript/checklist.tex, papers/completion/autoformalization/manuscript/llm_disclosure.tex, papers/completion/autoformalization/submission/paper.pdf, papers/completion/autoformalization/evidence/format_check.json, papers/completion/autoformalization/evidence/author_questions.md, papers/completion/autoformalization/manuscript/neurips_2026_vericode.sty, papers/completion/autoformalization/submission/template_inputs.json, papers/completion/autoformalization/evidence/final_reproduction.json, papers/completion/autoformalization/submission/author_review_packet.md, papers/completion/autoformalization/submission/checksums.json
- Gap task: AF-001, AF-002, AF-003, AF-004, AF-005, AF-006, AF-007, AF-008, AF-009, AF-010, AF-011, AF-012, AF-013, AF-014, AF-015, AF-016, AF-017, AF-018, AF-019, AF-020, AF-021, AF-022, AF-023, AF-024, AF-025
- Acceptance: All linked task criteria have current artifact and validation evidence; numerical claims trace to real runs; author handoff is explicit.
- Validation: python3 scripts/paper_supervisors.py verify-goal --paper autoformalization --goal AF-G000

## AF-S01 Recover sources and freeze executable research scope

- Status: active
- Parent: AF-G000
- Depends on:
- Fib priority: 2
- Priority: P0
- Track: autoformalization
- Bundle: autoformalization/AF-S01
- Goal: Recover editable material, define claim-linked protocols, and pin actual implementation/runtime capabilities without blocking independent work on inaccessible author sources.
- Outputs: papers/completion/autoformalization/manuscript/main.tex, papers/completion/autoformalization/manuscript/references.bib, papers/completion/autoformalization/evidence/source_recovery.json, papers/completion/autoformalization/evidence/source_discrepancies.md, papers/completion/autoformalization/protocol.md, papers/completion/autoformalization/config/experiment_plan.json, papers/completion/autoformalization/evidence/claim_task_map.json, papers/completion/autoformalization/evidence/deadline_scope_options.md, papers/completion/autoformalization/evidence/source_audit_private.json, papers/completion/autoformalization/evidence/runtime_capability_matrix.json, papers/completion/autoformalization/config/environment_manifest.json
- Gap task: AF-001, AF-002, AF-003
- Acceptance: All linked task criteria have current artifact and validation evidence; numerical claims trace to real runs; author handoff is explicit.
- Validation: python3 scripts/paper_supervisors.py verify-goal --paper autoformalization --goal AF-S01

## AF-S02 Create independent source-grounded evaluation populations

- Status: active
- Parent: AF-G000
- Depends on:
- Fib priority: 3
- Priority: P0
- Track: autoformalization
- Bundle: autoformalization/AF-S02
- Goal: Freeze provenance, grouped partitions, candidate-blind annotation and adversarial semantic witnesses distinct from teacher-generated targets.
- Outputs: papers/completion/autoformalization/data/corpus_manifest.json, papers/completion/autoformalization/data/splits.json, papers/completion/autoformalization/data/teacher_manifest.json, papers/completion/autoformalization/evidence/split_audit.json, papers/completion/autoformalization/data/annotation_guidelines.md, papers/completion/autoformalization/data/annotation_packets.jsonl, papers/completion/autoformalization/data/gold_facets.jsonl, papers/completion/autoformalization/evidence/annotation_provenance.json, papers/completion/autoformalization/evaluation/reference_semantics.py, papers/completion/autoformalization/evaluation/reference_results.json, papers/completion/autoformalization/data/minimal_pairs.jsonl, papers/completion/autoformalization/evidence/reference_provenance.json
- Gap task: AF-004, AF-005, AF-006
- Acceptance: All linked task criteria have current artifact and validation evidence; numerical claims trace to real runs; author handoff is explicit.
- Validation: python3 scripts/paper_supervisors.py verify-goal --paper autoformalization --goal AF-S02

## AF-S03 Build and validate an honest benchmark harness

- Status: active
- Parent: AF-G000
- Depends on:
- Fib priority: 4
- Priority: P0
- Track: autoformalization
- Bundle: autoformalization/AF-S03
- Goal: Implement matched conditions, result/coverage accounting, inference isolation and numerical training validation before admitting research results.
- Outputs: papers/completion/autoformalization/evaluation/run_benchmark.py, papers/completion/autoformalization/evaluation/result_schema.json, papers/completion/autoformalization/evaluation/test_result_accounting.py, papers/completion/autoformalization/config/metrics.json, papers/completion/autoformalization/evaluation/inference_isolation.py, papers/completion/autoformalization/evaluation/test_inference_isolation.py, papers/completion/autoformalization/evidence/leakage_control_report.json, papers/completion/autoformalization/evidence/training_correctness.json, papers/completion/autoformalization/config/training_backend.json, papers/completion/autoformalization/evaluation/pipeline_arms.py, papers/completion/autoformalization/config/pipeline_arms.json, papers/completion/autoformalization/evidence/pipeline_arm_preflight.json
- Gap task: AF-007, AF-008, AF-009, AF-010
- Acceptance: All linked task criteria have current artifact and validation evidence; numerical claims trace to real runs; author handoff is explicit.
- Validation: python3 scripts/paper_supervisors.py verify-goal --paper autoformalization --goal AF-S03

## AF-S04 Measure learning, trusted feedback, guidance, and compiler repair

- Status: active
- Parent: AF-G000
- Depends on:
- Fib priority: 5
- Priority: P0
- Track: autoformalization
- Bundle: autoformalization/AF-S04
- Goal: Execute T0–T5 with frozen checkpoints, independent selection/test roles, actual activated consumers and traceable isolated repairs.
- Outputs: papers/completion/autoformalization/runs/training_baselines/manifest.json, papers/completion/autoformalization/runs/training_baselines/results.jsonl, papers/completion/autoformalization/checkpoints/baselines/manifest.json, papers/completion/autoformalization/data/proof_feedback_manifest.json, papers/completion/autoformalization/runs/proof_heads/results.jsonl, papers/completion/autoformalization/evidence/proof_head_isolation.json, papers/completion/autoformalization/runs/guidance_promotion/results.jsonl, papers/completion/autoformalization/evidence/guidance_export.json, papers/completion/autoformalization/evidence/consumer_activation.json, papers/completion/autoformalization/evidence/rollback_receipt.json, papers/completion/autoformalization/runs/compiler_repair/results.jsonl, papers/completion/autoformalization/evidence/repair_task_trace.json, papers/completion/autoformalization/evidence/compiler_patch.diff, papers/completion/autoformalization/evidence/repair_validation.json
- Gap task: AF-011, AF-012, AF-013, AF-014
- Acceptance: All linked task criteria have current artifact and validation evidence; numerical claims trace to real runs; author handoff is explicit.
- Validation: python3 scripts/paper_supervisors.py verify-goal --paper autoformalization --goal AF-S04

## AF-S05 Measure valid proof transfer and supporting components

- Status: active
- Parent: AF-G000
- Depends on:
- Fib priority: 6
- Priority: P0
- Track: autoformalization
- Bundle: autoformalization/AF-S05
- Goal: Execute A–E plus supported bridge/code/trace, retrieval, planning, proof-assistance and cross-domain comparisons with native evidence and explicit limitations.
- Outputs: papers/completion/autoformalization/evaluation/bridge_cases.py, papers/completion/autoformalization/data/policy_code_trace_cases.json, papers/completion/autoformalization/runs/bridge_validation/results.jsonl, papers/completion/autoformalization/evidence/translation_receipts.jsonl, papers/completion/autoformalization/runs/pipeline_comparison/manifest.json, papers/completion/autoformalization/runs/pipeline_comparison/results.jsonl, papers/completion/autoformalization/data/retrieval_judgments.jsonl, papers/completion/autoformalization/runs/retrieval/results.jsonl, papers/completion/autoformalization/runs/premise_selection/results.jsonl, papers/completion/autoformalization/config/retrieval_manifest.json, papers/completion/autoformalization/runs/proof_assistance/results.jsonl, papers/completion/autoformalization/runs/planning/results.jsonl, papers/completion/autoformalization/evidence/native_checker_receipts.jsonl, papers/completion/autoformalization/runs/domain_transfer/results.jsonl, papers/completion/autoformalization/evidence/domain_scope_matrix.json
- Gap task: AF-015, AF-016, AF-017, AF-018, AF-019
- Acceptance: All linked task criteria have current artifact and validation evidence; numerical claims trace to real runs; author handoff is explicit.
- Validation: python3 scripts/paper_supervisors.py verify-goal --paper autoformalization --goal AF-S05

## AF-S06 Analyze evidence and rewrite the empirical paper

- Status: active
- Parent: AF-G000
- Depends on:
- Fib priority: 7
- Priority: P0
- Track: autoformalization
- Bundle: autoformalization/AF-S06
- Goal: Account for total cost, uncertainty, coverage, failures and missingness; generate tables and align every manuscript claim with measured scope.
- Outputs: papers/completion/autoformalization/evaluation/aggregate_costs.py, papers/completion/autoformalization/runs/costs/results.jsonl, papers/completion/autoformalization/evidence/cost_accounting.md, papers/completion/autoformalization/evaluation/analyze_results.py, papers/completion/autoformalization/results/table6_pipeline.tex, papers/completion/autoformalization/results/table11_training.tex, papers/completion/autoformalization/results/table13_assistance.tex, papers/completion/autoformalization/results/summary.json, papers/completion/autoformalization/results/hypothesis_report.md, papers/completion/autoformalization/manuscript/main.tex, papers/completion/autoformalization/manuscript/references.bib, papers/completion/autoformalization/evidence/final_claim_audit.json, papers/completion/autoformalization/evidence/bibliography_audit.md
- Gap task: AF-020, AF-021, AF-022
- Acceptance: All linked task criteria have current artifact and validation evidence; numerical claims trace to real runs; author handoff is explicit.
- Validation: python3 scripts/paper_supervisors.py verify-goal --paper autoformalization --goal AF-S06

## AF-S07 Prepare anonymous reproducible submission files for author review

- Status: active
- Parent: AF-G000
- Depends on:
- Fib priority: 8
- Priority: P0
- Track: autoformalization
- Bundle: autoformalization/AF-S07
- Goal: Freeze anonymous artifacts, official template/questionnaire/disclosures, clean reproduction and a concrete author review packet; keep author sign-off and submission external.
- Outputs: papers/completion/autoformalization/artifact/README.md, papers/completion/autoformalization/artifact/manifest.json, papers/completion/autoformalization/artifact/S01_S40_map.json, papers/completion/autoformalization/submission/supplement.zip, papers/completion/autoformalization/evidence/anonymization_report.json, papers/completion/autoformalization/manuscript/checklist.tex, papers/completion/autoformalization/manuscript/llm_disclosure.tex, papers/completion/autoformalization/submission/paper.pdf, papers/completion/autoformalization/evidence/format_check.json, papers/completion/autoformalization/evidence/author_questions.md, papers/completion/autoformalization/manuscript/neurips_2026_vericode.sty, papers/completion/autoformalization/submission/template_inputs.json, papers/completion/autoformalization/evidence/final_reproduction.json, papers/completion/autoformalization/submission/author_review_packet.md, papers/completion/autoformalization/submission/checksums.json
- Gap task: AF-023, AF-024, AF-025
- Acceptance: All linked task criteria have current artifact and validation evidence; numerical claims trace to real runs; author handoff is explicit.
- Validation: python3 scripts/paper_supervisors.py verify-goal --paper autoformalization --goal AF-S07
