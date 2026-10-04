# Compiler-Guided Autoformalization with Adaptive Multi-View Representations — implementation taskboard

Read `papers/completion/autoformalization/review.md` and `papers/completion/README.md` before work.
Objective heap: `papers/completion/autoformalization/paper.objectives.md`. Board namespace: `vericodegen-2026-autoformalization`.

All tasks start open. P0 is submission-critical, P1 supports the full study, P2 is optional extension.
Dependencies still apply across priority levels. A blocked experiment remains blocked until run or explicitly rescoped with a recorded claim change.
Never turn estimates, mocks, dry runs, or missing values into measured results.
Implement in native ephemeral worktrees. Coordinate shared library changes through the supervisor merge queue.
Each task must write its receipt using the contract in the runbook; this is provenance validation, not scientific peer review.

## AF-001 Recover editable manuscript and missing reference artifacts

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: autoformalization
- Depends on: 
- Goal id: AF-S01
- Parent goal: AF-G000
- Objective heap: papers/completion/autoformalization/paper.objectives.md
- Board namespace: vericodegen-2026-autoformalization
- Bundle: autoformalization/AF-S01
- Parallel lane: autoformalization
- Outputs: papers/completion/autoformalization/manuscript/main.tex, papers/completion/autoformalization/manuscript/references.bib, papers/completion/autoformalization/evidence/source_recovery.json, papers/completion/autoformalization/evidence/source_discrepancies.md, papers/completion/autoformalization/receipts/AF-001.json
- Predicted files: papers/completion/autoformalization/manuscript/main.tex, papers/completion/autoformalization/manuscript/references.bib, papers/completion/autoformalization/evidence/source_recovery.json, papers/completion/autoformalization/evidence/source_discrepancies.md, papers/completion/autoformalization/receipts/AF-001.json, papers/completion/autoformalization/receipts/snapshots/AF-001/
- Allowed paths: 
- Resource class: cpu-medium
- Resource stage: execution
- Implementation timeout seconds: 7200
- Validation: python3 scripts/paper_supervisors.py verify-task --paper autoformalization --task AF-001
- Acceptance: Editable source builds into a PDF with all original equations/tables/citations accounted for, or recovered-source failures and reconstruction progress are explicitly recorded.; Historical evidence is distinguished from newly reconstructed material; absent logs are not manufactured.; Source recovery does not gate independent protocol or code preflight tasks.; Manuscript-specific source recovery is distinguished from the now-available local research template and checklist; reconstruction uses the local research shell without modifying shared inputs.
- Paper evidence: pp. 14–15, App. D, lines 460–474: evaluation/reference_semantics.py and output referenced; p. 27, lines 851–859: official checklist missing; manuscript sources absent; local research template/style/checklist now supplied; Local user-provided research template/style/checklist inspected 2026-09-11; no manuscript-specific .tex or .bib exists under papers/.
- Reuse candidates: papers/autoformalization_training_methods_revised-1.pdf, papers/neurips_2026_vericode_workshop.tex, papers/neurips_2026_vericode.sty, papers/checklist.tex
- Receipt: papers/completion/autoformalization/receipts/AF-001.json

The user supplied Overleaf project https://www.overleaf.com/project/6a7b4742e20ac910c422a7e0; determine which manuscript(s) it contains and retrieve authorized editable sources if access permits. Direct unauthenticated access has not established its contents. Search existing authorized local/git/archive sources for LaTeX, BibTeX, figures, the private audit ledger, reference suite, and original logs. If author-owned source cannot be recovered, reconstruct an editable manuscript from the PDF and retain an equation/table/citation discrepancy audit. Record provenance of any recreated reference suite. Missing Overleaf access must not stop protocol, dataset, or harness work. The user has now provided local research-format inputs: papers/neurips_2026_vericode_workshop.tex, papers/neurips_2026_vericode.sty, and papers/checklist.tex. These are formatting/checklist sources, not recovered manuscript text or bibliography; the three manuscript LaTeX/BibTeX sources remain absent. Use the local research shell for any reconstruction, keeping its style unchanged, and preserve the originals. Do not substitute papers/neurips_2026_vericode_workshop_competition.tex, its competition style, or the generic papers/neurips_2026.sty.

Acceptance criteria:

1. Editable source builds into a PDF with all original equations/tables/citations accounted for, or recovered-source failures and reconstruction progress are explicitly recorded.
2. Historical evidence is distinguished from newly reconstructed material; absent logs are not manufactured.
3. Source recovery does not gate independent protocol or code preflight tasks.
4. Manuscript-specific source recovery is distinguished from the now-available local research template and checklist; reconstruction uses the local research shell without modifying shared inputs.

Record dependencies, exact code/data/model/tool versions, actual command logs, failures and claim limitations in the receipt. Expand this task into bounded follow-ups when discovery requires it; preserve its goal and evidence obligations.

## AF-002 Freeze research questions, experiment scope, and completion policy

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: autoformalization
- Depends on: 
- Goal id: AF-S01
- Parent goal: AF-G000
- Objective heap: papers/completion/autoformalization/paper.objectives.md
- Board namespace: vericodegen-2026-autoformalization
- Bundle: autoformalization/AF-S01
- Parallel lane: autoformalization
- Outputs: papers/completion/autoformalization/protocol.md, papers/completion/autoformalization/config/experiment_plan.json, papers/completion/autoformalization/evidence/claim_task_map.json, papers/completion/autoformalization/evidence/deadline_scope_options.md, papers/completion/autoformalization/receipts/AF-002.json
- Predicted files: papers/completion/autoformalization/protocol.md, papers/completion/autoformalization/config/experiment_plan.json, papers/completion/autoformalization/evidence/claim_task_map.json, papers/completion/autoformalization/evidence/deadline_scope_options.md, papers/completion/autoformalization/receipts/AF-002.json, papers/completion/autoformalization/receipts/snapshots/AF-002/
- Allowed paths: 
- Resource class: cpu-medium
- Resource stage: execution
- Implementation timeout seconds: 7200
- Validation: python3 scripts/paper_supervisors.py verify-task --paper autoformalization --task AF-002
- Acceptance: A–E and T0–T5 each have explicit inputs, teacher availability, checker, budget, primary metrics and control comparison.; Unrun/unavailable conditions remain explicit; narrowing a claim never marks a run executed or the full empirical goal complete.; A machine-readable experiment plan fixes final-test access and permitted scope decisions before outcome inspection.; Current CFP/date checks and resource limits are recorded; no submission or public release is performed by this task.
- Paper evidence: p. 9, §8, Table 1 and lines 342–355; pp. 15–16, Tables 5–6: A–E; p. 21, Tables 10–11: T0–T5; p. 26, Table 13
- Reuse candidates: external/ipfs_datasets/benchmarks/bench_semantic_logic_roundtrip.py, external/ipfs_datasets/benchmarks/bench_modal_autoencoder_cycle.py
- Receipt: papers/completion/autoformalization/receipts/AF-002.json

Prespecify primary source-fidelity and useful proof-coverage hypotheses, the A–E/T0–T5 crosswalk, seeds, sample-count rationale, paired comparisons, hardware/model/time budgets, and required versus exploratory analyses. Preserve every promised comparison in a claim-to-task map. Produce a deadline-aware full empirical route and a concrete narrowed methods-only alternative if evidence cannot be obtained, without silently claiming those experiments occurred. Allocate isolated run/worktree paths and shared GPU/model-service slots with the other supervisors.

Acceptance criteria:

1. A–E and T0–T5 each have explicit inputs, teacher availability, checker, budget, primary metrics and control comparison.
2. Unrun/unavailable conditions remain explicit; narrowing a claim never marks a run executed or the full empirical goal complete.
3. A machine-readable experiment plan fixes final-test access and permitted scope decisions before outcome inspection.
4. Current CFP/date checks and resource limits are recorded; no submission or public release is performed by this task.

Record dependencies, exact code/data/model/tool versions, actual command logs, failures and claim limitations in the receipt. Expand this task into bounded follow-ups when discovery requires it; preserve its goal and evidence obligations.

## AF-003 Audit S01–S40 modules and preflight exact runtime routes

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: autoformalization
- Depends on: 
- Goal id: AF-S01
- Parent goal: AF-G000
- Objective heap: papers/completion/autoformalization/paper.objectives.md
- Board namespace: vericodegen-2026-autoformalization
- Bundle: autoformalization/AF-S01
- Parallel lane: autoformalization
- Outputs: papers/completion/autoformalization/evidence/source_audit_private.json, papers/completion/autoformalization/evidence/runtime_capability_matrix.json, papers/completion/autoformalization/config/environment_manifest.json, papers/completion/autoformalization/receipts/AF-003.json
- Predicted files: papers/completion/autoformalization/evidence/source_audit_private.json, papers/completion/autoformalization/evidence/runtime_capability_matrix.json, papers/completion/autoformalization/config/environment_manifest.json, papers/completion/autoformalization/receipts/AF-003.json, papers/completion/autoformalization/receipts/snapshots/AF-003/
- Allowed paths: 
- Resource class: cpu-medium
- Resource stage: execution
- Implementation timeout seconds: 7200
- Validation: python3 scripts/paper_supervisors.py verify-task --paper autoformalization --task AF-003
- Acceptance: All 40 roles have resolved mappings or a concrete unresolved status and recovery task.; Runtime matrix separates implemented, documented-only, fixture-only, unsupported and unavailable routes; importability is not credited as end-to-end success.; Chosen model/solver entry points, feature flags and resource constraints are pinned in a manifest.; Private repository identities stay in an internal ledger for later anonymization.
- Paper evidence: pp. 11–13, App. A, Table 2 and lines 412–416; p. 15, App. E, lines 479–483; pp. 6, 22–24: route-specific capability limits
- Reuse candidates: external/ipfs_datasets/ipfs_datasets_py/optimizers/logic_theorem_optimizer/modal_autoencoder.py, external/ipfs_datasets/ipfs_datasets_py/optimizers/logic_theorem_optimizer/modal_autoencoder_cuda.py, external/ipfs_datasets/scripts/ops/logic/probe_itp_hammer_environment.py, external/ipfs_datasets/ipfs_datasets_py/logic/tactician/planner.py, external/ipfs_datasets/ipfs_datasets_py/logic/TDFOL/tdfol_converter.py
- Receipt: papers/completion/autoformalization/receipts/AF-003.json

Resolve each anonymous source role to the current exact module, commit/blob, relevant lines and evidence class; distinguish current checkout from the unknown manuscript snapshot. Record dirty overlays and imported paths, dependency versions, solver/native checker availability, real embedding producer and selected profile. Inspect the official template and local artifact requirements. Probe existing installations without launching expensive training.

Acceptance criteria:

1. All 40 roles have resolved mappings or a concrete unresolved status and recovery task.
2. Runtime matrix separates implemented, documented-only, fixture-only, unsupported and unavailable routes; importability is not credited as end-to-end success.
3. Chosen model/solver entry points, feature flags and resource constraints are pinned in a manifest.
4. Private repository identities stay in an internal ledger for later anonymization.

Record dependencies, exact code/data/model/tool versions, actual command logs, failures and claim limitations in the receipt. Expand this task into bounded follow-ups when discovery requires it; preserve its goal and evidence obligations.

## AF-004 Build versioned corpus and enforce source-family/time partitions

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: autoformalization
- Depends on: AF-002, AF-003
- Goal id: AF-S02
- Parent goal: AF-G000
- Objective heap: papers/completion/autoformalization/paper.objectives.md
- Board namespace: vericodegen-2026-autoformalization
- Bundle: autoformalization/AF-S02
- Parallel lane: autoformalization
- Outputs: papers/completion/autoformalization/data/corpus_manifest.json, papers/completion/autoformalization/data/splits.json, papers/completion/autoformalization/data/teacher_manifest.json, papers/completion/autoformalization/evidence/split_audit.json, papers/completion/autoformalization/receipts/AF-004.json
- Predicted files: papers/completion/autoformalization/data/corpus_manifest.json, papers/completion/autoformalization/data/splits.json, papers/completion/autoformalization/data/teacher_manifest.json, papers/completion/autoformalization/evidence/split_audit.json, papers/completion/autoformalization/receipts/AF-004.json, papers/completion/autoformalization/receipts/snapshots/AF-004/
- Allowed paths: 
- Resource class: cpu-medium
- Resource stage: execution
- Implementation timeout seconds: 7200
- Validation: python3 scripts/paper_supervisors.py verify-task --paper autoformalization --task AF-004
- Acceptance: Counts and exclusions are reported per domain/source family/time group and split.; Exact/near-duplicate, paraphrase, adjacent-section and cross-view leakage checks pass or excluded cases are documented.; Final-test source IDs/labels cannot enter training, hyperparameter selection, canary tuning or patch generation.; Dataset and vector/teacher manifests are content hashed and do not invent corpus counts or licenses.
- Paper evidence: p. 2, §2.2; p. 5, §4.3, lines 164–168; p. 15, App. E, lines 484–494; p. 18, App. I, Table 8
- Reuse candidates: external/ipfs_datasets/ipfs_datasets_py/optimizers/logic_theorem_optimizer/legal_samples.py, external/ipfs_datasets/ipfs_datasets_py/optimizers/logic_theorem_optimizer/spacy_modal_codec.py, external/ipfs_datasets/tests/fixtures/semantic_roundtrip/pilot_cases.json
- Receipt: papers/completion/autoformalization/receipts/AF-004.json

Inventory existing licensed natural legal/policy documents, coding requirements, implementation snippets and trace material; freeze admitted populations with source identity, version, licensing and provenance. Build grouped train/selection/fixed-canary/final-test manifests with near-duplicate and derivative grouping. Separate synthetic stress tests from natural held-out data. Record every vector producer and teacher target version; exclude mock targets from real semantic-embedding claims.

Acceptance criteria:

1. Counts and exclusions are reported per domain/source family/time group and split.
2. Exact/near-duplicate, paraphrase, adjacent-section and cross-view leakage checks pass or excluded cases are documented.
3. Final-test source IDs/labels cannot enter training, hyperparameter selection, canary tuning or patch generation.
4. Dataset and vector/teacher manifests are content hashed and do not invent corpus counts or licenses.

Record dependencies, exact code/data/model/tool versions, actual command logs, failures and claim limitations in the receipt. Expand this task into bounded follow-ups when discovery requires it; preserve its goal and evidence obligations.

## AF-005 Prepare independent annotation and adjudication evidence

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: autoformalization
- Depends on: AF-004
- Goal id: AF-S02
- Parent goal: AF-G000
- Objective heap: papers/completion/autoformalization/paper.objectives.md
- Board namespace: vericodegen-2026-autoformalization
- Bundle: autoformalization/AF-S02
- Parallel lane: autoformalization
- Outputs: papers/completion/autoformalization/data/annotation_guidelines.md, papers/completion/autoformalization/data/annotation_packets.jsonl, papers/completion/autoformalization/data/gold_facets.jsonl, papers/completion/autoformalization/evidence/annotation_provenance.json, papers/completion/autoformalization/receipts/AF-005.json
- Predicted files: papers/completion/autoformalization/data/annotation_guidelines.md, papers/completion/autoformalization/data/annotation_packets.jsonl, papers/completion/autoformalization/data/gold_facets.jsonl, papers/completion/autoformalization/evidence/annotation_provenance.json, papers/completion/autoformalization/receipts/AF-005.json, papers/completion/autoformalization/receipts/snapshots/AF-005/
- Allowed paths: 
- Resource class: cpu-medium
- Resource stage: execution
- Implementation timeout seconds: 7200
- Validation: python3 scripts/paper_supervisors.py verify-task --paper autoformalization --task AF-005
- Acceptance: Gold/admissible-alternative schema and annotation instructions are frozen before scored model outputs are inspected.; Agreement/disagreement counts and adjudication are based on real records; automatic teacher-derived labels are identified separately.; Unavailable independent review is recorded as pending and causes affected semantic claims to remain unmeasured.
- Paper evidence: p. 2, lines 76–80: teacher labels are not source gold; p. 9, lines 350–355; p. 15, lines 489–494
- Reuse candidates: external/ipfs_datasets/benchmarks/bench_semantic_logic_roundtrip.py, external/ipfs_datasets/tests/fixtures/semantic_roundtrip/
- Receipt: papers/completion/autoformalization/receipts/AF-005.json

Create annotation guidelines and candidate-blind labeling packets covering propositions, modality, negation, actor/recipient roles, quantifiers, exceptions, temporal interpretation, ambiguity, source spans and admissible assumptions. Reuse independently reviewed labels only after provenance audit. Record actual annotations, disagreements, adjudication and annotator independence. If independent human review is required but unavailable, prepare the packet and explicitly leave that dependency pending rather than inventing review.

Acceptance criteria:

1. Gold/admissible-alternative schema and annotation instructions are frozen before scored model outputs are inspected.
2. Agreement/disagreement counts and adjudication are based on real records; automatic teacher-derived labels are identified separately.
3. Unavailable independent review is recorded as pending and causes affected semantic claims to remain unmeasured.

Record dependencies, exact code/data/model/tool versions, actual command logs, failures and claim limitations in the receipt. Expand this task into bounded follow-ups when discovery requires it; preserve its goal and evidence obligations.

## AF-006 Reproduce reference semantics and build adversarial minimal pairs

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: autoformalization
- Depends on: AF-002, AF-003
- Goal id: AF-S02
- Parent goal: AF-G000
- Objective heap: papers/completion/autoformalization/paper.objectives.md
- Board namespace: vericodegen-2026-autoformalization
- Bundle: autoformalization/AF-S02
- Parallel lane: autoformalization
- Outputs: papers/completion/autoformalization/evaluation/reference_semantics.py, papers/completion/autoformalization/evaluation/reference_results.json, papers/completion/autoformalization/data/minimal_pairs.jsonl, papers/completion/autoformalization/evidence/reference_provenance.json, papers/completion/autoformalization/receipts/AF-006.json
- Predicted files: papers/completion/autoformalization/evaluation/reference_semantics.py, papers/completion/autoformalization/evaluation/reference_results.json, papers/completion/autoformalization/data/minimal_pairs.jsonl, papers/completion/autoformalization/evidence/reference_provenance.json, papers/completion/autoformalization/receipts/AF-006.json, papers/completion/autoformalization/receipts/snapshots/AF-006/
- Allowed paths: 
- Resource class: cpu-medium
- Resource stage: execution
- Implementation timeout seconds: 7200
- Validation: python3 scripts/paper_supervisors.py verify-task --paper autoformalization --task AF-006
- Acceptance: All twelve checks retain enumerated case counts, expected logical outcomes and actual outputs; any mismatch updates the claim.; Every minimal-pair family has an independently specified distinction and expected supported/unsupported behavior.; Recovered historical output and newly executed output are not conflated; no unbounded soundness claim is inferred.
- Paper evidence: pp. 14–15, Tables 3–4; p. 8, §7, Equations 9–11; p. 21, lines 675–677
- Reuse candidates: external/ipfs_datasets/ipfs_datasets_py/logic/TDFOL/tdfol_converter.py, external/ipfs_datasets/benchmarks/bench_semantic_logic_roundtrip.py
- Receipt: papers/completion/autoformalization/receipts/AF-006.json

Recover the original reference suite when available; otherwise recreate it with explicit new provenance and independent expected witnesses. Check the twelve finite cases and the claimed 26 strong-until/conjunction disagreements among 64 trace pairs. Expand semantic stress cases for modality, implication direction, exception/quantifier scope, identity mismatch, trace completeness and shared round-trip omissions. These are conformance/adversarial cases, not natural-distribution accuracy.

Acceptance criteria:

1. All twelve checks retain enumerated case counts, expected logical outcomes and actual outputs; any mismatch updates the claim.
2. Every minimal-pair family has an independently specified distinction and expected supported/unsupported behavior.
3. Recovered historical output and newly executed output are not conflated; no unbounded soundness claim is inferred.

Record dependencies, exact code/data/model/tool versions, actual command logs, failures and claim limitations in the receipt. Expand this task into bounded follow-ups when discovery requires it; preserve its goal and evidence obligations.

## AF-007 Implement provenance-preserving evaluation and result accounting

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: autoformalization
- Depends on: AF-002, AF-003, AF-004
- Goal id: AF-S03
- Parent goal: AF-G000
- Objective heap: papers/completion/autoformalization/paper.objectives.md
- Board namespace: vericodegen-2026-autoformalization
- Bundle: autoformalization/AF-S03
- Parallel lane: autoformalization
- Outputs: papers/completion/autoformalization/evaluation/run_benchmark.py, papers/completion/autoformalization/evaluation/result_schema.json, papers/completion/autoformalization/evaluation/test_result_accounting.py, papers/completion/autoformalization/config/metrics.json, papers/completion/autoformalization/receipts/AF-007.json
- Predicted files: papers/completion/autoformalization/evaluation/run_benchmark.py, papers/completion/autoformalization/evaluation/result_schema.json, papers/completion/autoformalization/evaluation/test_result_accounting.py, papers/completion/autoformalization/config/metrics.json, papers/completion/autoformalization/receipts/AF-007.json, papers/completion/autoformalization/receipts/snapshots/AF-007/
- Allowed paths: 
- Resource class: cpu-medium
- Resource stage: execution
- Implementation timeout seconds: 7200
- Validation: python3 scripts/paper_supervisors.py verify-task --paper autoformalization --task AF-007
- Acceptance: Every eligible source remains in coverage denominators, including unavailable, unsupported, abstained and timed-out cases.; Result schema distinguishes native checked proof, solver-local result, countermodel, bounded observation, failure and no-run.; Invalid/no-run/fixture results cannot be admitted as measured table rows.; Tables can be regenerated deterministically from raw records with artifact hashes and denominator checks.
- Paper evidence: p. 16, lines 495–504; p. 26, lines 841–849; p. 9, Table 1
- Reuse candidates: external/ipfs_datasets/benchmarks/bench_semantic_logic_roundtrip.py, external/ipfs_datasets/benchmarks/bench_semantic_roundtrip_compositions.py, external/ipfs_datasets/benchmarks/logic_pipeline/content_addressing.py
- Receipt: papers/completion/autoformalization/receipts/AF-007.json

Adapt existing benchmark interfaces into this paper’s harness. Record parse/elaboration success, independent source-facet fidelity, ambiguity, source maps, forward/cycle/final reconstruction, consistency, proof/false-transfer outcomes and all execution statuses. Retain raw per-example artifacts, elapsed/resource costs, model/tool identity and experiment arm. Add meaningful negative controls for metric denominators and result admission.

Acceptance criteria:

1. Every eligible source remains in coverage denominators, including unavailable, unsupported, abstained and timed-out cases.
2. Result schema distinguishes native checked proof, solver-local result, countermodel, bounded observation, failure and no-run.
3. Invalid/no-run/fixture results cannot be admitted as measured table rows.
4. Tables can be regenerated deterministically from raw records with artifact hashes and denominator checks.

Record dependencies, exact code/data/model/tool versions, actual command logs, failures and claim limitations in the receipt. Expand this task into bounded follow-ups when discovery requires it; preserve its goal and evidence obligations.

## AF-008 Enforce inference-time and source-withheld leakage controls

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: autoformalization
- Depends on: AF-004, AF-007
- Goal id: AF-S03
- Parent goal: AF-G000
- Objective heap: papers/completion/autoformalization/paper.objectives.md
- Board namespace: vericodegen-2026-autoformalization
- Bundle: autoformalization/AF-S03
- Parallel lane: autoformalization
- Outputs: papers/completion/autoformalization/evaluation/inference_isolation.py, papers/completion/autoformalization/evaluation/test_inference_isolation.py, papers/completion/autoformalization/evidence/leakage_control_report.json, papers/completion/autoformalization/receipts/AF-008.json
- Predicted files: papers/completion/autoformalization/evaluation/inference_isolation.py, papers/completion/autoformalization/evaluation/test_inference_isolation.py, papers/completion/autoformalization/evidence/leakage_control_report.json, papers/completion/autoformalization/receipts/AF-008.json, papers/completion/autoformalization/receipts/snapshots/AF-008/
- Allowed paths: external/ipfs_datasets/ipfs_datasets_py/optimizers/logic_theorem_optimizer/modal_autoencoder.py, external/ipfs_datasets/ipfs_datasets_py/logic/legal_ir/canonical_roundtrip.py
- Resource class: cpu-medium
- Resource stage: execution
- Implementation timeout seconds: 7200
- Validation: python3 scripts/paper_supervisors.py verify-task --paper autoformalization --task AF-008
- Acceptance: Adversarial attempts to recover withheld source/gold through each documented channel are rejected or the affected condition is explicitly non-blind.; Main generalization arms disable sample-indexed memory for update and evaluation.; Forward, cycle and final reconstruction scores remain distinct and parser-assisted features are disclosed.
- Paper evidence: p. 3, §3.2, lines 104–115; p. 18, lines 574–579; p. 20, lines 628–645
- Reuse candidates: external/ipfs_datasets/ipfs_datasets_py/optimizers/logic_theorem_optimizer/modal_autoencoder.py, external/ipfs_datasets/ipfs_datasets_py/logic/legal_ir/canonical_roundtrip.py, external/ipfs_datasets/benchmarks/bench_semantic_logic_roundtrip.py
- Receipt: papers/completion/autoformalization/receipts/AF-008.json

Build separate inference views for source-only, parser-assisted and source-withheld realization arms. Prevent the realizer from recovering raw text through source maps/locators, filesystem, retrieval, parser state or sample memory. Exclude reference/gold decoder fallbacks from blind-prediction credit. Record feature provenance and costs; inspect shared sample IDs and cache keys for memory shortcuts.

Acceptance criteria:

1. Adversarial attempts to recover withheld source/gold through each documented channel are rejected or the affected condition is explicitly non-blind.
2. Main generalization arms disable sample-indexed memory for update and evaluation.
3. Forward, cycle and final reconstruction scores remain distinct and parser-assisted features are disclosed.

Record dependencies, exact code/data/model/tool versions, actual command logs, failures and claim limitations in the receipt. Expand this task into bounded follow-ups when discovery requires it; preserve its goal and evidence obligations.

## AF-009 Validate packed training numerics and explicit parameter updates

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: autoformalization
- Depends on: AF-003, AF-007
- Goal id: AF-S03
- Parent goal: AF-G000
- Objective heap: papers/completion/autoformalization/paper.objectives.md
- Board namespace: vericodegen-2026-autoformalization
- Bundle: autoformalization/AF-S03
- Parallel lane: autoformalization
- Outputs: papers/completion/autoformalization/evidence/training_correctness.json, papers/completion/autoformalization/config/training_backend.json, papers/completion/autoformalization/receipts/AF-009.json
- Predicted files: papers/completion/autoformalization/evidence/training_correctness.json, papers/completion/autoformalization/config/training_backend.json, papers/completion/autoformalization/receipts/AF-009.json, papers/completion/autoformalization/receipts/snapshots/AF-009/
- Allowed paths: 
- Resource class: cpu-medium
- Resource stage: execution
- Implementation timeout seconds: 7200
- Validation: python3 scripts/paper_supervisors.py verify-task --paper autoformalization --task AF-009
- Acceptance: Actual test outputs and environment IDs are retained; skipped tests are labeled skipped.; A training update demonstrates nonzero admissible gradients and changed shared parameters; no-op paths remain explicit.; Equation normalization and SGD-style semantics match the current audited implementation or the manuscript is corrected.
- Paper evidence: p. 4, §4.2, Equation 5; pp. 18–19, App. J, Equations 12–14; p. 8, lines 333–337
- Reuse candidates: external/ipfs_datasets/ipfs_datasets_py/optimizers/logic_theorem_optimizer/modal_autoencoder_cuda.py, external/ipfs_datasets/ipfs_datasets_py/optimizers/logic_theorem_optimizer/modal_autoencoder_state_transaction.py, external/ipfs_datasets/tests/unit/optimizers/logic_theorem_optimizer/test_modal_autoencoder_cuda_training.py, external/ipfs_datasets/tests/unit/optimizers/logic_theorem_optimizer/test_modal_autoencoder_checkpoint.py
- Receipt: papers/completion/autoformalization/receipts/AF-009.json

Run relevant existing CPU tests for active/masked objectives, globally normalized microbatches, zero norms, clipping, nonfinite rejection, transaction rollback and changed-row scatter. Check checkpoint reload and update-group activation. If suitable CUDA already exists, perform targeted CPU/FP32/BF16 parity before GPU research runs; otherwise record GPU unavailability and proceed with permitted CPU scope.

Acceptance criteria:

1. Actual test outputs and environment IDs are retained; skipped tests are labeled skipped.
2. A training update demonstrates nonzero admissible gradients and changed shared parameters; no-op paths remain explicit.
3. Equation normalization and SGD-style semantics match the current audited implementation or the manuscript is corrected.

Record dependencies, exact code/data/model/tool versions, actual command logs, failures and claim limitations in the receipt. Expand this task into bounded follow-ups when discovery requires it; preserve its goal and evidence obligations.

## AF-010 Implement matched A–E pipeline conditions

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: autoformalization
- Depends on: AF-002, AF-003, AF-007, AF-008
- Goal id: AF-S03
- Parent goal: AF-G000
- Objective heap: papers/completion/autoformalization/paper.objectives.md
- Board namespace: vericodegen-2026-autoformalization
- Bundle: autoformalization/AF-S03
- Parallel lane: autoformalization
- Outputs: papers/completion/autoformalization/evaluation/pipeline_arms.py, papers/completion/autoformalization/config/pipeline_arms.json, papers/completion/autoformalization/evidence/pipeline_arm_preflight.json, papers/completion/autoformalization/receipts/AF-010.json
- Predicted files: papers/completion/autoformalization/evaluation/pipeline_arms.py, papers/completion/autoformalization/config/pipeline_arms.json, papers/completion/autoformalization/evidence/pipeline_arm_preflight.json, papers/completion/autoformalization/receipts/AF-010.json, papers/completion/autoformalization/receipts/snapshots/AF-010/
- Allowed paths: external/ipfs_datasets/ipfs_datasets_py/logic/legal_ir/canonical_roundtrip.py, external/ipfs_datasets/ipfs_datasets_py/logic/integration/reasoning/legal_ir_learned_guidance.py
- Resource class: cpu-medium
- Resource stage: execution
- Implementation timeout seconds: 7200
- Validation: python3 scripts/paper_supervisors.py verify-task --paper autoformalization --task AF-010
- Acceptance: Each arm exposes a executable entry point/configuration and its exact feature/oracle access.; C cannot accidentally consume D bridge evidence; E is separately identifiable and does not silently alter its checker.; Unavailable implementations are reported and prevent related performance claims rather than returning synthetic success.
- Paper evidence: p. 15, Table 5; p. 16, Table 6; p. 3, §3.1: frozen canonical profile disables guidance
- Reuse candidates: external/ipfs_datasets/ipfs_datasets_py/logic/legal_ir/canonical_roundtrip.py, external/ipfs_datasets/ipfs_datasets_py/logic/integration/reasoning/legal_ir_learned_guidance.py, external/ipfs_datasets/benchmarks/bench_semantic_roundtrip_compositions.py
- Receipt: papers/completion/autoformalization/receipts/AF-010.json

Implement explicit adapters for A direct-model formalization, B deterministic bounded compiler, C typed source-grounded multiview without proof transfer, D checked bridges and compatible premise assembly, and E D with pinned bounded learned advice. Use identical source tasks, supplied vocabulary, checker and resource envelope where the comparison calls for it. Wire real direct-model inference and stable-guidance paths only when available; publish capability status before runs.

Acceptance criteria:

1. Each arm exposes a executable entry point/configuration and its exact feature/oracle access.
2. C cannot accidentally consume D bridge evidence; E is separately identifiable and does not silently alter its checker.
3. Unavailable implementations are reported and prevent related performance claims rather than returning synthetic success.

Record dependencies, exact code/data/model/tool versions, actual command logs, failures and claim limitations in the receipt. Expand this task into bounded follow-ups when discovery requires it; preserve its goal and evidence obligations.

## AF-011 Execute deterministic, memory, and shared-only training baselines

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: autoformalization
- Depends on: AF-004, AF-005, AF-006, AF-007, AF-008, AF-009
- Goal id: AF-S04
- Parent goal: AF-G000
- Objective heap: papers/completion/autoformalization/paper.objectives.md
- Board namespace: vericodegen-2026-autoformalization
- Bundle: autoformalization/AF-S04
- Parallel lane: autoformalization
- Outputs: papers/completion/autoformalization/runs/training_baselines/manifest.json, papers/completion/autoformalization/runs/training_baselines/results.jsonl, papers/completion/autoformalization/checkpoints/baselines/manifest.json, papers/completion/autoformalization/receipts/AF-011.json
- Predicted files: papers/completion/autoformalization/runs/training_baselines/manifest.json, papers/completion/autoformalization/runs/training_baselines/results.jsonl, papers/completion/autoformalization/checkpoints/baselines/manifest.json, papers/completion/autoformalization/receipts/AF-011.json, papers/completion/autoformalization/receipts/snapshots/AF-011/
- Allowed paths: 
- Resource class: cpu-medium
- Resource stage: execution
- Implementation timeout seconds: 7200
- Validation: python3 scripts/paper_supervisors.py verify-task --paper autoformalization --task AF-011
- Acceptance: Every executed seed has dataset/config/initial/final checkpoint identities, learning logs, update counts and termination reason.; Counts and real results exist for all executed arms; missing or budget-exhausted runs stay unrun/partial.; T2 update/evaluation memory is demonstrably disabled and no final-test outcome selects model settings.; A budget-constrained alternative narrows claims explicitly without fabricating a training gain.
- Paper evidence: p. 21, Table 10 T0–T2 and Table 11; p. 5, §4.3; p. 18, Table 8
- Reuse candidates: external/ipfs_datasets/ipfs_datasets_py/optimizers/logic_theorem_optimizer/modal_autoencoder.py, external/ipfs_datasets/ipfs_datasets_py/optimizers/logic_theorem_optimizer/modal_autoencoder_cuda.py, external/ipfs_datasets/ipfs_datasets_py/optimizers/logic_theorem_optimizer/modal_autoencoder_checkpoint.py
- Receipt: papers/completion/autoformalization/receipts/AF-011.json

Run frozen T0 deterministic, T1 adaptive with sample memory, and T2 shared-parameter-only conditions with the prespecified seeds and resource limits. Keep selection data explicit, targets frozen, and final test untouched until model freeze. Report vector MSE/cosine, family/view CE, target entropy/excess CE, source fidelity and coverage separately; identify seen-source memory diagnostics rather than presenting them as generalization.

Acceptance criteria:

1. Every executed seed has dataset/config/initial/final checkpoint identities, learning logs, update counts and termination reason.
2. Counts and real results exist for all executed arms; missing or budget-exhausted runs stay unrun/partial.
3. T2 update/evaluation memory is demonstrably disabled and no final-test outcome selects model settings.
4. A budget-constrained alternative narrows claims explicitly without fabricating a training gain.

Record dependencies, exact code/data/model/tool versions, actual command logs, failures and claim limitations in the receipt. Expand this task into bounded follow-ups when discovery requires it; preserve its goal and evidence obligations.

## AF-012 Train and evaluate isolated trusted proof heads

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: autoformalization
- Depends on: AF-011, AF-015
- Goal id: AF-S04
- Parent goal: AF-G000
- Objective heap: papers/completion/autoformalization/paper.objectives.md
- Board namespace: vericodegen-2026-autoformalization
- Bundle: autoformalization/AF-S04
- Parallel lane: autoformalization
- Outputs: papers/completion/autoformalization/data/proof_feedback_manifest.json, papers/completion/autoformalization/runs/proof_heads/results.jsonl, papers/completion/autoformalization/evidence/proof_head_isolation.json, papers/completion/autoformalization/receipts/AF-012.json
- Predicted files: papers/completion/autoformalization/data/proof_feedback_manifest.json, papers/completion/autoformalization/runs/proof_heads/results.jsonl, papers/completion/autoformalization/evidence/proof_head_isolation.json, papers/completion/autoformalization/receipts/AF-012.json, papers/completion/autoformalization/receipts/snapshots/AF-012/
- Allowed paths: 
- Resource class: cpu-medium
- Resource stage: execution
- Implementation timeout seconds: 7200
- Validation: python3 scripts/paper_supervisors.py verify-task --paper autoformalization --task AF-012
- Acceptance: Proof feedback never changes protected primary representation/anti-copy state under the declared isolation contract.; Calibration and routing metrics use actual eligible labels and matched route budgets, not predicted proof success as certification.; Missing native feedback or insufficient labels yields a documented unrun/limited-scope T3 outcome.
- Paper evidence: p. 5, §4.4; p. 19, App. J.3; p. 21, Table 10 T3
- Reuse candidates: external/ipfs_datasets/ipfs_datasets_py/optimizers/logic_theorem_optimizer/modal_autoencoder.py, external/ipfs_datasets/tests/unit/optimizers/logic_theorem_optimizer/test_modal_autoencoder_proof_heads.py, external/ipfs_datasets/tests/unit/optimizers/logic_theorem_optimizer/test_modal_autoencoder_trusted_feature_bus.py
- Receipt: papers/completion/autoformalization/receipts/AF-012.json

Construct admitted verifier-feedback training records from the permitted partitions and pinned compiler/checker versions. Train T3 from the matched T2 checkpoint with isolated heads. Evaluate calibration, abstention, class/family coverage, route value and actual checker outcomes against T2. Track rejected/duplicate/version-mismatched feedback and protected parameter/objective fingerprints.

Acceptance criteria:

1. Proof feedback never changes protected primary representation/anti-copy state under the declared isolation contract.
2. Calibration and routing metrics use actual eligible labels and matched route budgets, not predicted proof success as certification.
3. Missing native feedback or insufficient labels yields a documented unrun/limited-scope T3 outcome.

Record dependencies, exact code/data/model/tool versions, actual command logs, failures and claim limitations in the receipt. Expand this task into bounded follow-ups when discovery requires it; preserve its goal and evidence obligations.

## AF-013 Evaluate source-free guidance promotion and actual consumer activation

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: autoformalization
- Depends on: AF-012, AF-008
- Goal id: AF-S04
- Parent goal: AF-G000
- Objective heap: papers/completion/autoformalization/paper.objectives.md
- Board namespace: vericodegen-2026-autoformalization
- Bundle: autoformalization/AF-S04
- Parallel lane: autoformalization
- Outputs: papers/completion/autoformalization/runs/guidance_promotion/results.jsonl, papers/completion/autoformalization/evidence/guidance_export.json, papers/completion/autoformalization/evidence/consumer_activation.json, papers/completion/autoformalization/evidence/rollback_receipt.json, papers/completion/autoformalization/receipts/AF-013.json
- Predicted files: papers/completion/autoformalization/runs/guidance_promotion/results.jsonl, papers/completion/autoformalization/evidence/guidance_export.json, papers/completion/autoformalization/evidence/consumer_activation.json, papers/completion/autoformalization/evidence/rollback_receipt.json, papers/completion/autoformalization/receipts/AF-013.json, papers/completion/autoformalization/receipts/snapshots/AF-013/
- Allowed paths: 
- Resource class: cpu-medium
- Resource stage: execution
- Implementation timeout seconds: 7200
- Validation: python3 scripts/paper_supervisors.py verify-task --paper autoformalization --task AF-013
- Acceptance: Canary population and thresholds are fixed before comparison and are distinct from final test.; Either actual consumer activation is evidenced by a matching loaded digest or the route is reported unactivated; export alone earns no downstream credit.; Promotion rejection and rollback retain their genuine result and are analyzed rather than bypassed.
- Paper evidence: p. 5, §4.5, lines 188–193; p. 20, App. K.2; p. 21, T4; p. 26, Table 13 guidance comparison
- Reuse candidates: external/ipfs_datasets/ipfs_datasets_py/logic/integration/reasoning/legal_ir_learned_guidance.py, external/ipfs_datasets/tests/unit/logic/integration/test_legal_ir_learned_guidance_promotion.py, external/ipfs_datasets/docs/implementation/runbooks/leanstral_legal_ir_rollout.md
- Receipt: papers/completion/autoformalization/receipts/AF-013.json

Export eligible shared features from T3; reject raw-source/sample-memory channels and resolve canonical contracts. Evaluate paired fixed canaries with anti-copy and symbolic-validity guards, freeze admitted guidance, and run matched guidance-off/on consumers for T4. Save an explicit loaded-guidance identity, rollback receipt and untouched-source fidelity outcomes; remain within an isolated experiment profile.

Acceptance criteria:

1. Canary population and thresholds are fixed before comparison and are distinct from final test.
2. Either actual consumer activation is evidenced by a matching loaded digest or the route is reported unactivated; export alone earns no downstream credit.
3. Promotion rejection and rollback retain their genuine result and are analyzed rather than bypassed.

Record dependencies, exact code/data/model/tool versions, actual command logs, failures and claim limitations in the receipt. Expand this task into bounded follow-ups when discovery requires it; preserve its goal and evidence obligations.

## AF-014 Run bounded compiler/decompiler repair ablation

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P1
- Track: autoformalization
- Depends on: AF-013, AF-006
- Goal id: AF-S04
- Parent goal: AF-G000
- Objective heap: papers/completion/autoformalization/paper.objectives.md
- Board namespace: vericodegen-2026-autoformalization
- Bundle: autoformalization/AF-S04
- Parallel lane: autoformalization
- Outputs: papers/completion/autoformalization/runs/compiler_repair/results.jsonl, papers/completion/autoformalization/evidence/repair_task_trace.json, papers/completion/autoformalization/evidence/compiler_patch.diff, papers/completion/autoformalization/evidence/repair_validation.json, papers/completion/autoformalization/receipts/AF-014.json
- Predicted files: papers/completion/autoformalization/runs/compiler_repair/results.jsonl, papers/completion/autoformalization/evidence/repair_task_trace.json, papers/completion/autoformalization/evidence/compiler_patch.diff, papers/completion/autoformalization/evidence/repair_validation.json, papers/completion/autoformalization/receipts/AF-014.json, papers/completion/autoformalization/receipts/snapshots/AF-014/
- Allowed paths: external/ipfs_datasets/ipfs_datasets_py/optimizers/logic_theorem_optimizer/spacy_modal_codec.py, external/ipfs_datasets/ipfs_datasets_py/logic/modal/codec.py
- Resource class: cpu-medium
- Resource stage: execution
- Implementation timeout seconds: 7200
- Validation: python3 scripts/paper_supervisors.py verify-task --paper autoformalization --task AF-014
- Acceptance: Trace connects observed defect, task/proposal, actual patch, validation evidence, activation configuration and rollback identity.; Final-test examples never choose the patch; shared source errors are not removed merely to make a proof easy.; No accepted improvement is a valid measured outcome; unexecuted synthesis remains unrun with narrowed corresponding claims.
- Paper evidence: p. 5, lines 181–187; p. 20, App. K.3, lines 646–656; p. 21, Table 10 T5
- Reuse candidates: external/ipfs_datasets/ipfs_datasets_py/optimizers/logic_theorem_optimizer/spacy_modal_codec.py, external/ipfs_datasets/ipfs_datasets_py/logic/modal/codec.py, external/ipfs_datasets/docs/implementation/runbooks/leanstral_legal_ir_rollout.md
- Receipt: papers/completion/autoformalization/receipts/AF-014.json

Choose development-set semantic defects from actual introspection, generate bounded repair tasks, and apply candidate patches in an isolated worktree. Pin the pre-repair T4 or protocol-defined baseline, preserve loss-aware contracts, run independent semantic regressions and paired fixed-canary checks, then evaluate the frozen T5 patch on untouched test data. Distinguish parameter actions from executable changes and record rejected patches and review cost.

Acceptance criteria:

1. Trace connects observed defect, task/proposal, actual patch, validation evidence, activation configuration and rollback identity.
2. Final-test examples never choose the patch; shared source errors are not removed merely to make a proof easy.
3. No accepted improvement is a valid measured outcome; unexecuted synthesis remains unrun with narrowed corresponding claims.

Record dependencies, exact code/data/model/tool versions, actual command logs, failures and claim limitations in the receipt. Expand this task into bounded follow-ups when discovery requires it; preserve its goal and evidence obligations.

## AF-015 Validate supported bridges and execute policy–code–trace case

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: autoformalization
- Depends on: AF-003, AF-006, AF-007
- Goal id: AF-S05
- Parent goal: AF-G000
- Objective heap: papers/completion/autoformalization/paper.objectives.md
- Board namespace: vericodegen-2026-autoformalization
- Bundle: autoformalization/AF-S05
- Parallel lane: autoformalization
- Outputs: papers/completion/autoformalization/evaluation/bridge_cases.py, papers/completion/autoformalization/data/policy_code_trace_cases.json, papers/completion/autoformalization/runs/bridge_validation/results.jsonl, papers/completion/autoformalization/evidence/translation_receipts.jsonl, papers/completion/autoformalization/receipts/AF-015.json
- Predicted files: papers/completion/autoformalization/evaluation/bridge_cases.py, papers/completion/autoformalization/data/policy_code_trace_cases.json, papers/completion/autoformalization/runs/bridge_validation/results.jsonl, papers/completion/autoformalization/evidence/translation_receipts.jsonl, papers/completion/autoformalization/receipts/AF-015.json, papers/completion/autoformalization/receipts/snapshots/AF-015/
- Allowed paths: external/ipfs_datasets/ipfs_datasets_py/logic/security_ir/formalization_adapter.py
- Resource class: cpu-medium
- Resource stage: execution
- Implementation timeout seconds: 7200
- Validation: python3 scripts/paper_supervisors.py verify-task --paper autoformalization --task AF-015
- Acceptance: Every accepted transfer carries the preserved property/direction, bridge assumptions, supported fragment and independently checked proof/countermodel.; Safe, unsafe, delayed-audit, incomplete-window, wrong-tenant and inconsistent-premise examples have justified distinct outcomes.; The conditional paper proposition is not represented as blanket machine-checked compiler soundness.; Missing native checkers or unsupported fragments are included in coverage/status reports.
- Paper evidence: pp. 7–8, §6.2–§7, Equations 7–11; p. 13, Proposition 1 and proposed receipt; p. 20, Table 9
- Reuse candidates: external/ipfs_datasets/ipfs_datasets_py/logic/TDFOL/tdfol_converter.py, external/ipfs_datasets/ipfs_datasets_py/logic/security_ir/formalization_adapter.py, external/ipfs_datasets/benchmarks/bench_semantic_roundtrip_compositions.py, external/ipfs_datasets/benchmarks/bench_itp_hammer.py
- Receipt: papers/completion/autoformalization/receipts/AF-015.json

Select explicit logical profiles and supported query fragments; implement or verify the needed source/target signatures, premise preservation, goal reflection, related-model existence and consistency evidence. Execute guarded/unsafe protected-write code and audit traces, including incomplete capture and identity mismatches. Bind actual extraction/refinement and native theorem/checker receipts. Include lossy TDFOL modal erasure as a negative control.

Acceptance criteria:

1. Every accepted transfer carries the preserved property/direction, bridge assumptions, supported fragment and independently checked proof/countermodel.
2. Safe, unsafe, delayed-audit, incomplete-window, wrong-tenant and inconsistent-premise examples have justified distinct outcomes.
3. The conditional paper proposition is not represented as blanket machine-checked compiler soundness.
4. Missing native checkers or unsupported fragments are included in coverage/status reports.

Record dependencies, exact code/data/model/tool versions, actual command logs, failures and claim limitations in the receipt. Expand this task into bounded follow-ups when discovery requires it; preserve its goal and evidence obligations.

## AF-016 Execute matched A–E source-to-proof benchmark

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: autoformalization
- Depends on: AF-005, AF-006, AF-010, AF-011, AF-013, AF-015
- Goal id: AF-S05
- Parent goal: AF-G000
- Objective heap: papers/completion/autoformalization/paper.objectives.md
- Board namespace: vericodegen-2026-autoformalization
- Bundle: autoformalization/AF-S05
- Parallel lane: autoformalization
- Outputs: papers/completion/autoformalization/runs/pipeline_comparison/manifest.json, papers/completion/autoformalization/runs/pipeline_comparison/results.jsonl, papers/completion/autoformalization/receipts/AF-016.json
- Predicted files: papers/completion/autoformalization/runs/pipeline_comparison/manifest.json, papers/completion/autoformalization/runs/pipeline_comparison/results.jsonl, papers/completion/autoformalization/receipts/AF-016.json, papers/completion/autoformalization/receipts/snapshots/AF-016/
- Allowed paths: 
- Resource class: cpu-medium
- Resource stage: execution
- Implementation timeout seconds: 7200
- Validation: python3 scripts/paper_supervisors.py verify-task --paper autoformalization --task AF-016
- Acceptance: Each of the 20 Table 6 cells is backed by actual raw measurements and definition, or an explicit unavailable/unrun status tied to narrowed claims.; Raw candidates and accepted checker evidence use identical pinned goal/premise/source identities.; No cross-paper numbers, dry-run fixtures, default configuration values or historical unpinned runs enter the result table.
- Paper evidence: pp. 15–16, Tables 5–6; p. 9, lines 347–355
- Reuse candidates: external/ipfs_datasets/benchmarks/bench_semantic_logic_roundtrip.py, external/ipfs_datasets/benchmarks/bench_semantic_roundtrip_compositions.py, external/ipfs_datasets/benchmarks/bench_itp_hammer.py
- Receipt: papers/completion/autoformalization/receipts/AF-016.json

Run available prespecified A–E configurations on the frozen tasks after baseline/guidance checkpoints and bridges are fixed. Preserve original-source, first-IR, reconstructed-text, second-IR, bridge and checker evidence per example. Score independent fidelity, uncertainty, correct/false transfer, coverage, and total latency/cost with identical denominators and explicit execution status.

Acceptance criteria:

1. Each of the 20 Table 6 cells is backed by actual raw measurements and definition, or an explicit unavailable/unrun status tied to narrowed claims.
2. Raw candidates and accepted checker evidence use identical pinned goal/premise/source identities.
3. No cross-paper numbers, dry-run fixtures, default configuration values or historical unpinned runs enter the result table.

Record dependencies, exact code/data/model/tool versions, actual command logs, failures and claim limitations in the receipt. Expand this task into bounded follow-ups when discovery requires it; preserve its goal and evidence obligations.

## AF-017 Measure retrieval and premise-selection contributions

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P1
- Track: autoformalization
- Depends on: AF-004, AF-005, AF-007, AF-015
- Goal id: AF-S05
- Parent goal: AF-G000
- Objective heap: papers/completion/autoformalization/paper.objectives.md
- Board namespace: vericodegen-2026-autoformalization
- Bundle: autoformalization/AF-S05
- Parallel lane: autoformalization
- Outputs: papers/completion/autoformalization/data/retrieval_judgments.jsonl, papers/completion/autoformalization/runs/retrieval/results.jsonl, papers/completion/autoformalization/runs/premise_selection/results.jsonl, papers/completion/autoformalization/config/retrieval_manifest.json, papers/completion/autoformalization/receipts/AF-017.json
- Predicted files: papers/completion/autoformalization/data/retrieval_judgments.jsonl, papers/completion/autoformalization/runs/retrieval/results.jsonl, papers/completion/autoformalization/runs/premise_selection/results.jsonl, papers/completion/autoformalization/config/retrieval_manifest.json, papers/completion/autoformalization/receipts/AF-017.json, papers/completion/autoformalization/receipts/snapshots/AF-017/
- Allowed paths: 
- Resource class: cpu-medium
- Resource stage: execution
- Implementation timeout seconds: 7200
- Validation: python3 scripts/paper_supervisors.py verify-task --paper autoformalization --task AF-017
- Acceptance: Relevance recall/ranking and admitted-premise yield have independent label provenance and full corpus/query counts.; Vector route is executed against real backend/dependencies; mock vectors or declared-only CLI modes cannot count as measured retrieval.; Hand-authored selector weights and proxy labels are disclosed; any unavailable conditions narrow only their associated claims.
- Paper evidence: pp. 5–6, §5.1; pp. 22–23, App. N; p. 24, App. O.3; p. 26, Table 13 first two rows
- Reuse candidates: external/ipfs_datasets/ipfs_datasets_py/vector_stores/faiss_store.py, external/ipfs_datasets/benchmarks/bench_itp_hammer_premise_selection.py, external/ipfs_datasets/ipfs_datasets_py/logic/hammers/learned_selector.py, external/ipfs_datasets/ipfs_datasets_py/optimizers/logic_theorem_optimizer/legal_samples.py
- Receipt: papers/completion/autoformalization/receipts/AF-017.json

Freeze a common corpus/query pool and real relevance/usefulness judgments; compare lexical, real vector, graph and any prespecified combined route under matched context budgets. Use actual vector-store dispatch with pinned encoder/index metadata. Compare deterministic and optional graph selectors on explicit dependency/usefulness labels where available; retain import-overlap proxy results as separately labeled diagnostics. A claim of trained selector weights requires an actual independent train/split artifact.

Acceptance criteria:

1. Relevance recall/ranking and admitted-premise yield have independent label provenance and full corpus/query counts.
2. Vector route is executed against real backend/dependencies; mock vectors or declared-only CLI modes cannot count as measured retrieval.
3. Hand-authored selector weights and proxy labels are disclosed; any unavailable conditions narrow only their associated claims.

Record dependencies, exact code/data/model/tool versions, actual command logs, failures and claim limitations in the receipt. Expand this task into bounded follow-ups when discovery requires it; preserve its goal and evidence obligations.

## AF-018 Compare bounded planning, Hammer, and Leanstral assistance

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P1
- Track: autoformalization
- Depends on: AF-007, AF-015, AF-017
- Goal id: AF-S05
- Parent goal: AF-G000
- Objective heap: papers/completion/autoformalization/paper.objectives.md
- Board namespace: vericodegen-2026-autoformalization
- Bundle: autoformalization/AF-S05
- Parallel lane: autoformalization
- Outputs: papers/completion/autoformalization/runs/proof_assistance/results.jsonl, papers/completion/autoformalization/runs/planning/results.jsonl, papers/completion/autoformalization/evidence/native_checker_receipts.jsonl, papers/completion/autoformalization/receipts/AF-018.json
- Predicted files: papers/completion/autoformalization/runs/proof_assistance/results.jsonl, papers/completion/autoformalization/runs/planning/results.jsonl, papers/completion/autoformalization/evidence/native_checker_receipts.jsonl, papers/completion/autoformalization/receipts/AF-018.json, papers/completion/autoformalization/receipts/snapshots/AF-018/
- Allowed paths: 
- Resource class: cpu-medium
- Resource stage: execution
- Implementation timeout seconds: 7200
- Validation: python3 scripts/paper_supervisors.py verify-task --paper autoformalization --task AF-018
- Acceptance: Plans replay deterministically with pinned guidance/inputs and never count as executed proofs.; Candidate and accepted-proof rates, native coverage, failure categories and all-attempt costs are reported separately.; Generated Lean with sorry/admit/unapproved axioms is rejected; method-essential model identity/prompt settings are retained.; Any unavailable assistance arm remains an explicit limitation, with no invented model calls or fine-tuning claim.
- Paper evidence: p. 6, §5.2–§5.3; pp. 23–24, Table 12 and App. O; p. 26, Table 13 planning/assistance rows
- Reuse candidates: external/ipfs_datasets/ipfs_datasets_py/logic/tactician/planner.py, external/ipfs_datasets/benchmarks/bench_itp_hammer.py, external/ipfs_datasets/ipfs_datasets_py/logic/modal/leanstral_verifier.py, external/ipfs_datasets/docs/logic/itp_hammer_user_guide.md
- Receipt: papers/completion/autoformalization/receipts/AF-018.json

On fixed admitted goals, compare unguided/guided plans and the available Hammer/Leanstral proposal routes under the same checker and resource envelope. Separate deterministic plan replay, candidate generation, solver response, native reconstruction, accepted proof, timeout, unsupported and unavailable outcomes. Use existing permitted model/tool installations and shared-service quotas; do not bypass proof policies for success.

Acceptance criteria:

1. Plans replay deterministically with pinned guidance/inputs and never count as executed proofs.
2. Candidate and accepted-proof rates, native coverage, failure categories and all-attempt costs are reported separately.
3. Generated Lean with sorry/admit/unapproved axioms is rejected; method-essential model identity/prompt settings are retained.
4. Any unavailable assistance arm remains an explicit limitation, with no invented model calls or fine-tuning claim.

Record dependencies, exact code/data/model/tool versions, actual command logs, failures and claim limitations in the receipt. Expand this task into bounded follow-ups when discovery requires it; preserve its goal and evidence obligations.

## AF-019 Evaluate or explicitly bound cross-domain statistical transfer

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P1
- Track: autoformalization
- Depends on: AF-004, AF-005, AF-011, AF-015
- Goal id: AF-S05
- Parent goal: AF-G000
- Objective heap: papers/completion/autoformalization/paper.objectives.md
- Board namespace: vericodegen-2026-autoformalization
- Bundle: autoformalization/AF-S05
- Parallel lane: autoformalization
- Outputs: papers/completion/autoformalization/runs/domain_transfer/results.jsonl, papers/completion/autoformalization/evidence/domain_scope_matrix.json, papers/completion/autoformalization/receipts/AF-019.json
- Predicted files: papers/completion/autoformalization/runs/domain_transfer/results.jsonl, papers/completion/autoformalization/evidence/domain_scope_matrix.json, papers/completion/autoformalization/receipts/AF-019.json, papers/completion/autoformalization/receipts/snapshots/AF-019/
- Allowed paths: 
- Resource class: cpu-medium
- Resource stage: execution
- Implementation timeout seconds: 7200
- Validation: python3 scripts/paper_supervisors.py verify-task --paper autoformalization --task AF-019
- Acceptance: Each evaluated domain has a supported profile, source population, ground-truth provenance, checkpoint and baseline.; Structural compatibility, learned transfer and valid semantic proof transfer are separately scored/described.; No multimodal OCR/ASR performance is claimed without a concrete measured extraction route.
- Paper evidence: p. 3, §3.3, lines 122–126; pp. 24–25, App. P.1; p. 15, App. E evaluation populations
- Reuse candidates: external/ipfs_datasets/ipfs_datasets_py/logic/security_ir/formalization_adapter.py, external/ipfs_datasets/ipfs_datasets_py/logic/legal_ir/canonical_roundtrip.py, external/ipfs_datasets/ipfs_datasets_py/optimizers/logic_theorem_optimizer/modal_autoencoder_feature_transfer.py
- Receipt: papers/completion/autoformalization/receipts/AF-019.json

Evaluate legal-trained shared parameters against relevant deterministic/domain-specific controls on frozen Security/Intent/software examples, with separately reviewed adapter, entity and time mappings. Report per-domain fidelity and proof coverage so infrastructure compatibility is not mistaken for transfer. For domains/media lacking supported extractors or independent labels, retain explicit limitations and remove unmeasured transfer claims from the submission.

Acceptance criteria:

1. Each evaluated domain has a supported profile, source population, ground-truth provenance, checkpoint and baseline.
2. Structural compatibility, learned transfer and valid semantic proof transfer are separately scored/described.
3. No multimodal OCR/ASR performance is claimed without a concrete measured extraction route.

Record dependencies, exact code/data/model/tool versions, actual command logs, failures and claim limitations in the receipt. Expand this task into bounded follow-ups when discovery requires it; preserve its goal and evidence obligations.

## AF-020 Measure total cost and optional CPU/CUDA execution economics

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P1
- Track: autoformalization
- Depends on: AF-007, AF-009, AF-011, AF-015
- Goal id: AF-S06
- Parent goal: AF-G000
- Objective heap: papers/completion/autoformalization/paper.objectives.md
- Board namespace: vericodegen-2026-autoformalization
- Bundle: autoformalization/AF-S06
- Parallel lane: autoformalization
- Outputs: papers/completion/autoformalization/evaluation/aggregate_costs.py, papers/completion/autoformalization/runs/costs/results.jsonl, papers/completion/autoformalization/evidence/cost_accounting.md, papers/completion/autoformalization/receipts/AF-020.json
- Predicted files: papers/completion/autoformalization/evaluation/aggregate_costs.py, papers/completion/autoformalization/runs/costs/results.jsonl, papers/completion/autoformalization/evidence/cost_accounting.md, papers/completion/autoformalization/receipts/AF-020.json, papers/completion/autoformalization/receipts/snapshots/AF-020/
- Allowed paths: external/ipfs_datasets/ipfs_datasets_py/optimizers/logic_theorem_optimizer/runtime_telemetry.py
- Resource class: cpu-medium
- Resource stage: execution
- Implementation timeout seconds: 7200
- Validation: python3 scripts/paper_supervisors.py verify-task --paper autoformalization --task AF-020
- Acceptance: Cost units, measured versus estimated/provider costs, cache state, hardware and precision are explicit.; Phase totals reconcile with retained run/usage records, including setup and failures.; Any throughput/speedup is based on matched actual runs; unavailable hardware is not a zero-cost result.
- Paper evidence: p. 9, Table 1 economics; p. 16, lines 502–504; p. 26, lines 845–846
- Reuse candidates: external/ipfs_datasets/benchmarks/bench_modal_autoencoder_cycle.py, external/ipfs_datasets/ipfs_datasets_py/optimizers/logic_theorem_optimizer/runtime_telemetry.py, external/ipfs_datasets/ipfs_datasets_py/optimizers/logic_theorem_optimizer/cycle_throughput_benchmark.py
- Receipt: papers/completion/autoformalization/receipts/AF-020.json

Instrument actual preparation, annotation, target construction, features, indexing, updates/selection, model calls, failed attempts, proof reconstruction, validation and review. Derive per-task/arm total and phase costs and latency distributions from real runs. If claiming CUDA or residency benefit, execute matched cold/warm CPU/CUDA/precision conditions on appropriate hardware; otherwise state those values unmeasured. Reject dry-run synthetic throughput summaries as evidence.

Acceptance criteria:

1. Cost units, measured versus estimated/provider costs, cache state, hardware and precision are explicit.
2. Phase totals reconcile with retained run/usage records, including setup and failures.
3. Any throughput/speedup is based on matched actual runs; unavailable hardware is not a zero-cost result.

Record dependencies, exact code/data/model/tool versions, actual command logs, failures and claim limitations in the receipt. Expand this task into bounded follow-ups when discovery requires it; preserve its goal and evidence obligations.

## AF-021 Analyze frozen results and regenerate every results table

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: autoformalization
- Depends on: AF-011, AF-012, AF-013, AF-014, AF-016, AF-017, AF-018, AF-019, AF-020
- Goal id: AF-S06
- Parent goal: AF-G000
- Objective heap: papers/completion/autoformalization/paper.objectives.md
- Board namespace: vericodegen-2026-autoformalization
- Bundle: autoformalization/AF-S06
- Parallel lane: autoformalization
- Outputs: papers/completion/autoformalization/evaluation/analyze_results.py, papers/completion/autoformalization/results/table6_pipeline.tex, papers/completion/autoformalization/results/table11_training.tex, papers/completion/autoformalization/results/table13_assistance.tex, papers/completion/autoformalization/results/summary.json, papers/completion/autoformalization/results/hypothesis_report.md, papers/completion/autoformalization/receipts/AF-021.json
- Predicted files: papers/completion/autoformalization/evaluation/analyze_results.py, papers/completion/autoformalization/results/table6_pipeline.tex, papers/completion/autoformalization/results/table11_training.tex, papers/completion/autoformalization/results/table13_assistance.tex, papers/completion/autoformalization/results/summary.json, papers/completion/autoformalization/results/hypothesis_report.md, papers/completion/autoformalization/receipts/AF-021.json, papers/completion/autoformalization/receipts/snapshots/AF-021/
- Allowed paths: 
- Resource class: cpu-medium
- Resource stage: execution
- Implementation timeout seconds: 7200
- Validation: python3 scripts/paper_supervisors.py verify-task --paper autoformalization --task AF-021
- Acceptance: All 44 original TBD cells are replaced by audited measurements/intervals or explicit unavailable/unrun explanations with correspondingly narrowed claims.; Raw counts, denominators, seeds, grouping, missingness and confidence-interval method are reproducible.; Zero observed false transfers is not generalized to universal soundness.; Negative/inconclusive results are retained and no post-hoc test selection is represented as prespecified.
- Paper evidence: p. 16, Table 6 and lines 498–504; p. 21, Table 11; p. 26, Table 13; p. 9, completion field
- Reuse candidates: external/ipfs_datasets/benchmarks/bench_semantic_logic_roundtrip.py, external/ipfs_datasets/benchmarks/bench_modal_autoencoder_cycle.py
- Receipt: papers/completion/autoformalization/receipts/AF-021.json

Aggregate the frozen raw experiment records with prespecified document-grouped paired effects and confidence intervals, seed variability, uncertainty and coverage. Report per-family/facet/domain results and false-transfer/abstention counts. Generate Table 6, Table 11 and retained Table 13 results directly from evidence; record every hypothesis as supported, unsupported, inconclusive or unrun. Update manifests/checkpoint/split/provenance fields.

Acceptance criteria:

1. All 44 original TBD cells are replaced by audited measurements/intervals or explicit unavailable/unrun explanations with correspondingly narrowed claims.
2. Raw counts, denominators, seeds, grouping, missingness and confidence-interval method are reproducible.
3. Zero observed false transfers is not generalized to universal soundness.
4. Negative/inconclusive results are retained and no post-hoc test selection is represented as prespecified.

Record dependencies, exact code/data/model/tool versions, actual command logs, failures and claim limitations in the receipt. Expand this task into bounded follow-ups when discovery requires it; preserve its goal and evidence obligations.

## AF-022 Rewrite contribution, claims, equations, and related work

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: autoformalization
- Depends on: AF-001, AF-003, AF-006, AF-021
- Goal id: AF-S06
- Parent goal: AF-G000
- Objective heap: papers/completion/autoformalization/paper.objectives.md
- Board namespace: vericodegen-2026-autoformalization
- Bundle: autoformalization/AF-S06
- Parallel lane: autoformalization
- Outputs: papers/completion/autoformalization/manuscript/main.tex, papers/completion/autoformalization/manuscript/references.bib, papers/completion/autoformalization/evidence/final_claim_audit.json, papers/completion/autoformalization/evidence/bibliography_audit.md, papers/completion/autoformalization/receipts/AF-022.json
- Predicted files: papers/completion/autoformalization/manuscript/main.tex, papers/completion/autoformalization/manuscript/references.bib, papers/completion/autoformalization/evidence/final_claim_audit.json, papers/completion/autoformalization/evidence/bibliography_audit.md, papers/completion/autoformalization/receipts/AF-022.json, papers/completion/autoformalization/receipts/snapshots/AF-022/
- Allowed paths: 
- Resource class: cpu-medium
- Resource stage: execution
- Implementation timeout seconds: 7200
- Validation: python3 scripts/paper_supervisors.py verify-task --paper autoformalization --task AF-022
- Acceptance: Abstract/conclusion match the measured scope and use no invented checkpoint, deployment, transfer or training results.; Every material claim maps to a source or raw result; finite illustrations and conditional propositions are labeled accurately.; The final narrative distinguishes A–E pipeline comparisons from T0–T5 learning comparisons.; References are verified and missing material comparisons addressed without claiming unrelated benchmarks were run.
- Paper evidence: pp. 1–2, abstract/contributions; pp. 7–8, semantics and coding example; pp. 9–10, related work/references; pp. 17–21, terminology and learning anatomy
- Reuse candidates: papers/autoformalization_training_methods_revised-1.pdf
- Receipt: papers/completion/autoformalization/receipts/AF-022.json

Rewrite the paper around the actual measured contribution and clear coding-verification use case. Compress descriptive material to make room for results within nine main pages. Audit equations, proof-transfer quantification/nonvacuity, vector-versus-text terminology, source-grounding versus truth, planning versus proof and implemented-versus-executed tense. Verify bibliography against primary sources and compare the final contribution with relevant verified-coding/autoformalization work. Preserve negative findings and explicit unavailable conditions.

Acceptance criteria:

1. Abstract/conclusion match the measured scope and use no invented checkpoint, deployment, transfer or training results.
2. Every material claim maps to a source or raw result; finite illustrations and conditional propositions are labeled accurately.
3. The final narrative distinguishes A–E pipeline comparisons from T0–T5 learning comparisons.
4. References are verified and missing material comparisons addressed without claiming unrelated benchmarks were run.

Record dependencies, exact code/data/model/tool versions, actual command logs, failures and claim limitations in the receipt. Expand this task into bounded follow-ups when discovery requires it; preserve its goal and evidence obligations.

## AF-023 Assemble anonymous implementation and reproducibility package

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: autoformalization
- Depends on: AF-003, AF-021, AF-022
- Goal id: AF-S07
- Parent goal: AF-G000
- Objective heap: papers/completion/autoformalization/paper.objectives.md
- Board namespace: vericodegen-2026-autoformalization
- Bundle: autoformalization/AF-S07
- Parallel lane: autoformalization
- Outputs: papers/completion/autoformalization/artifact/README.md, papers/completion/autoformalization/artifact/manifest.json, papers/completion/autoformalization/artifact/S01_S40_map.json, papers/completion/autoformalization/submission/supplement.zip, papers/completion/autoformalization/evidence/anonymization_report.json, papers/completion/autoformalization/receipts/AF-023.json
- Predicted files: papers/completion/autoformalization/artifact/README.md, papers/completion/autoformalization/artifact/manifest.json, papers/completion/autoformalization/artifact/S01_S40_map.json, papers/completion/autoformalization/submission/supplement.zip, papers/completion/autoformalization/evidence/anonymization_report.json, papers/completion/autoformalization/receipts/AF-023.json, papers/completion/autoformalization/receipts/snapshots/AF-023/
- Allowed paths: 
- Resource class: cpu-medium
- Resource stage: execution
- Implementation timeout seconds: 7200
- Validation: python3 scripts/paper_supervisors.py verify-task --paper autoformalization --task AF-023
- Acceptance: An independent clean environment can locate every retained-claim input and regenerate reported tables using documented commands.; All exported logs/configuration paths/artifact links are audited for double-blind requirements and sensitive credentials.; Supplement ZIP is at most 100 MB; large artifacts have an allowed anonymous access strategy and exact checksums.; No public upload/publication or fabricated human review occurs.
- Paper evidence: p. 11, lines 405–411; p. 17, lines 539–544; p. 27, lines 857–859
- Reuse candidates: external/ipfs_datasets/docs/logic/itp_hammer_receipts.md, external/ipfs_datasets/docs/implementation/runbooks/leanstral_legal_ir_rollout.md
- Receipt: papers/completion/autoformalization/receipts/AF-023.json

Freeze exact implementation/checkpoints/configurations, datasets or lawful retrieval manifests, annotation provenance, raw results and regenerators needed for retained claims. Provide anonymous S01–S40 mapping to reproducible files; keep private repository/author ledger outside submission material. Remove author-revealing paths, metadata, URLs, histories and secrets from exported artifacts. Build anonymous reproduction instructions and supplemental ZIP within workshop limits.

Acceptance criteria:

1. An independent clean environment can locate every retained-claim input and regenerate reported tables using documented commands.
2. All exported logs/configuration paths/artifact links are audited for double-blind requirements and sensitive credentials.
3. Supplement ZIP is at most 100 MB; large artifacts have an allowed anonymous access strategy and exact checksums.
4. No public upload/publication or fabricated human review occurs.

Record dependencies, exact code/data/model/tool versions, actual command logs, failures and claim limitations in the receipt. Expand this task into bounded follow-ups when discovery requires it; preserve its goal and evidence obligations.

## AF-024 Apply official template, questionnaire, and actual LLM disclosure

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: autoformalization
- Depends on: AF-001, AF-022, AF-023
- Goal id: AF-S07
- Parent goal: AF-G000
- Objective heap: papers/completion/autoformalization/paper.objectives.md
- Board namespace: vericodegen-2026-autoformalization
- Bundle: autoformalization/AF-S07
- Parallel lane: autoformalization
- Outputs: papers/completion/autoformalization/manuscript/checklist.tex, papers/completion/autoformalization/manuscript/llm_disclosure.tex, papers/completion/autoformalization/submission/paper.pdf, papers/completion/autoformalization/evidence/format_check.json, papers/completion/autoformalization/evidence/author_questions.md, papers/completion/autoformalization/manuscript/neurips_2026_vericode.sty, papers/completion/autoformalization/submission/template_inputs.json, papers/completion/autoformalization/receipts/AF-024.json
- Predicted files: papers/completion/autoformalization/manuscript/checklist.tex, papers/completion/autoformalization/manuscript/llm_disclosure.tex, papers/completion/autoformalization/submission/paper.pdf, papers/completion/autoformalization/evidence/format_check.json, papers/completion/autoformalization/evidence/author_questions.md, papers/completion/autoformalization/manuscript/neurips_2026_vericode.sty, papers/completion/autoformalization/submission/template_inputs.json, papers/completion/autoformalization/receipts/AF-024.json, papers/completion/autoformalization/receipts/snapshots/AF-024/
- Allowed paths: 
- Resource class: cpu-medium
- Resource stage: execution
- Implementation timeout seconds: 7200
- Validation: python3 scripts/paper_supervisors.py verify-task --paper autoformalization --task AF-024
- Acceptance: Main text is 4–9 pages excluding references/appendices and PDF is at most 50 MB, with official style unchanged.; No invented questionnaire, unexplained scientific TBD/To complete/TODO or broken reference remains; the official style-generated anonymous Affiliation/Address/email block is retained.; Official disclosure/checklist answers agree with logs and distinguish known facts from author information still needed.; PDF metadata and any linked artifacts pass the anonymity audit.; The build loads the local research neurips_2026_vericode.sty unchanged, in its anonymous default mode; competition, single-blind, final, preprint, nonanonymous, and generic-style substitutions are absent.; The per-paper checklist copy contains all 16 official questions and preserved guidelines, with no answerTODO/justificationTODO fields and with actual Yes/No/N/A answers plus 1–2 sentence evidence-backed justifications; only its instruction block is removed.; The shared user templates are unmodified and their recorded input checksums match; the final anonymous author block may retain the Affiliation/Address/email strings generated by the official style.; Final build retains the workshop footer, anonymous behavior and review line numbers; source/PDF placeholder checks distinguish unanswered scientific fields from official style-generated anonymous text.
- Paper evidence: p. 17, lines 533–544; p. 27, entire checklist placeholder; main text occupies pp. 1–9; Local research template line 10 loads neurips_2026_vericode; line 461 includes checklist.tex. Research style lines 343–350 generate the anonymous Affiliation/Address/email block. Local checklist contains 16 official questions.
- Reuse candidates: papers/autoformalization_training_methods_revised-1.pdf, papers/neurips_2026_vericode_workshop.tex, papers/neurips_2026_vericode.sty, papers/checklist.tex
- Receipt: papers/completion/autoformalization/receipts/AF-024.json

Use the now-supplied local 2026 research template/style/questionnaire and verify their provenance against the workshop CFP, preserving the local style and completing answers only from actual evidence. Record methodology-essential models/providers/dates/prompt/code/annotation/experiment assistance without inventing model versions. Build and inspect all pages for page limits, legibility, broken cross-references, missing fonts and residual draft placeholders. Provide author-dependent unanswered items in a separate review packet. Build from the supplied local research shell papers/neurips_2026_vericode_workshop.tex and an unchanged copy of papers/neurips_2026_vericode.sty, using the supplied default \usepackage{neurips_2026_vericode} with no final, preprint, nonanonymous, or sglblindworkshop option. Do not use the competition/single-blind variant or the generic neurips_2026.sty. Copy papers/checklist.tex into this paper's manuscript directory, include it after references and optional appendices, remove only its BEGIN/END INSTRUCTIONS block, preserve the heading/questions/subheadings/guidelines, and replace all 16 \answerTODO{} and 16 \justificationTODO{} fields with actual evidence-backed \answerYes{}, \answerNo{}, or \answerNA{} and 1–2 sentence justifications. Do not edit the user's shared template/style/checklist originals or fabricate author-dependent answers. Pin input checksums. The style intentionally prints Anonymous Author(s), Affiliation, Address, and email: preserve this official anonymous block and exclude it from unresolved-placeholder failures.

Acceptance criteria:

1. Main text is 4–9 pages excluding references/appendices and PDF is at most 50 MB, with official style unchanged.
2. No invented questionnaire, unexplained scientific TBD/To complete/TODO or broken reference remains; the official style-generated anonymous Affiliation/Address/email block is retained.
3. Official disclosure/checklist answers agree with logs and distinguish known facts from author information still needed.
4. PDF metadata and any linked artifacts pass the anonymity audit.
5. The build loads the local research neurips_2026_vericode.sty unchanged, in its anonymous default mode; competition, single-blind, final, preprint, nonanonymous, and generic-style substitutions are absent.
6. The per-paper checklist copy contains all 16 official questions and preserved guidelines, with no answerTODO/justificationTODO fields and with actual Yes/No/N/A answers plus 1–2 sentence evidence-backed justifications; only its instruction block is removed.
7. The shared user templates are unmodified and their recorded input checksums match; the final anonymous author block may retain the Affiliation/Address/email strings generated by the official style.
8. Final build retains the workshop footer, anonymous behavior and review line numbers; source/PDF placeholder checks distinguish unanswered scientific fields from official style-generated anonymous text.

Record dependencies, exact code/data/model/tool versions, actual command logs, failures and claim limitations in the receipt. Expand this task into bounded follow-ups when discovery requires it; preserve its goal and evidence obligations.

## AF-025 Perform independent reproduction and prepare final author review packet

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: autoformalization
- Depends on: AF-023, AF-024
- Goal id: AF-S07
- Parent goal: AF-G000
- Objective heap: papers/completion/autoformalization/paper.objectives.md
- Board namespace: vericodegen-2026-autoformalization
- Bundle: autoformalization/AF-S07
- Parallel lane: autoformalization
- Outputs: papers/completion/autoformalization/evidence/final_reproduction.json, papers/completion/autoformalization/submission/author_review_packet.md, papers/completion/autoformalization/submission/checksums.json, papers/completion/autoformalization/receipts/AF-025.json
- Predicted files: papers/completion/autoformalization/evidence/final_reproduction.json, papers/completion/autoformalization/submission/author_review_packet.md, papers/completion/autoformalization/submission/checksums.json, papers/completion/autoformalization/receipts/AF-025.json, papers/completion/autoformalization/receipts/snapshots/AF-025/
- Allowed paths: 
- Resource class: cpu-medium
- Resource stage: execution
- Implementation timeout seconds: 7200
- Validation: python3 scripts/paper_supervisors.py verify-task --paper autoformalization --task AF-025
- Acceptance: Reproduction result includes exact commands/environment, expected versus actual tables, and explicit unavailable checks; mere LaTeX compilation is not empirical validation.; Final packet links manuscript, supplement, claim audit and raw evidence with version/checksum identities.; Supervisor marks the empirical objective complete only if required evidence exists; scope-reduced alternatives and pending author choices are explicit.; No claim that authors approved or the paper was submitted/published is made without real evidence.
- Paper evidence: p. 27, lines 857–859: final review/artifact/evidence unfinished; p. 17, lines 533–538: author verification required
- Reuse candidates: external/ipfs_datasets/benchmarks/bench_semantic_logic_roundtrip.py, external/ipfs_datasets/benchmarks/bench_itp_hammer.py
- Receipt: papers/completion/autoformalization/receipts/AF-025.json

Run the documented clean-environment reproduction at the declared feasible level, verify table hashes and example/native-checker receipts, and inspect the final PDF and supplement against the claim ledger. Prepare a concise concrete packet identifying finished work, measured failures, deliberately unrun conditions, any remaining independent annotation/author questions, deadlines and submission files. Keep human author sign-off and actual workshop submission outside autonomous task completion. Verify research-template input checksums, all 16 completed checklist answers/justifications, preserved official style/anonymous block and workshop footer. Exempt only style-generated anonymous Affiliation/Address/email text from the residual-placeholder scan; scientific/checklist placeholders remain failures.

Acceptance criteria:

1. Reproduction result includes exact commands/environment, expected versus actual tables, and explicit unavailable checks; mere LaTeX compilation is not empirical validation.
2. Final packet links manuscript, supplement, claim audit and raw evidence with version/checksum identities.
3. Supervisor marks the empirical objective complete only if required evidence exists; scope-reduced alternatives and pending author choices are explicit.
4. No claim that authors approved or the paper was submitted/published is made without real evidence.

Record dependencies, exact code/data/model/tool versions, actual command logs, failures and claim limitations in the receipt. Expand this task into bounded follow-ups when discovery requires it; preserve its goal and evidence obligations.
