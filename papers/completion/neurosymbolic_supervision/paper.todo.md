# Proof-Carrying Neurosymbolic Supervision: State, Logic-Governed Decisions, and Test-Evidence Reuse — implementation taskboard

Read `papers/completion/neurosymbolic_supervision/review.md` and `papers/completion/README.md` before work.
Objective heap: `papers/completion/neurosymbolic_supervision/paper.objectives.md`. Board namespace: `vericodegen-2026-neurosymbolic_supervision`.

All tasks start open. P0 is submission-critical, P1 supports the full study, P2 is optional extension.
Dependencies still apply across priority levels. A blocked experiment remains blocked until run or explicitly rescoped with a recorded claim change.
Never turn estimates, mocks, dry runs, or missing values into measured results.
Implement in native ephemeral worktrees. Coordinate shared library changes through the supervisor merge queue.
Each task must write its receipt using the contract in the runbook; this is provenance validation, not scientific peer review.

## NS-001 Recover or reconstruct editable LaTeX and preserve the PDF baseline

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: neurosymbolic_supervision
- Depends on: 
- Goal id: NS-SG1
- Parent goal: NS-G000
- Objective heap: papers/completion/neurosymbolic_supervision/paper.objectives.md
- Board namespace: vericodegen-2026-neurosymbolic_supervision
- Bundle: neurosymbolic_supervision/NS-SG1
- Parallel lane: neurosymbolic_supervision
- Outputs: papers/completion/neurosymbolic_supervision/manuscript/main.tex, papers/completion/neurosymbolic_supervision/manuscript/references.bib, papers/completion/neurosymbolic_supervision/manuscript/BUILD.md, papers/completion/neurosymbolic_supervision/audit/source_recovery.md, papers/completion/neurosymbolic_supervision/audit/reconstruction_discrepancies.json, papers/completion/neurosymbolic_supervision/receipts/NS-001.json
- Predicted files: papers/completion/neurosymbolic_supervision/manuscript/main.tex, papers/completion/neurosymbolic_supervision/manuscript/references.bib, papers/completion/neurosymbolic_supervision/manuscript/BUILD.md, papers/completion/neurosymbolic_supervision/audit/source_recovery.md, papers/completion/neurosymbolic_supervision/audit/reconstruction_discrepancies.json, papers/completion/neurosymbolic_supervision/receipts/NS-001.json, papers/completion/neurosymbolic_supervision/receipts/snapshots/NS-001/
- Allowed paths: 
- Resource class: cpu-medium
- Resource stage: execution
- Implementation timeout seconds: 7200
- Validation: python3 scripts/paper_supervisors.py verify-task --paper neurosymbolic_supervision --task NS-001
- Acceptance: Editable source builds to PDF with one documented command.; All sections, equations, tables, and references are either recovered or explicitly reconciled against the baseline.; A source-origin record distinguishes original recovery from reconstruction and lists unresolved author-owned material.; Overleaf source provenance and project-to-paper identity are verified if accessible; otherwise access remains explicitly unresolved and reconstruction proceeds without blocking protocol/code work.; Manuscript-specific source recovery is distinguished from the now-available local research template and checklist; reconstruction uses the local research shell without modifying shared inputs.
- Paper evidence: PDF pp. 1–28: supplied manuscript exists only as a PDF in papers/; PDF p. 28, checklist: official checklist source absent from prior template; User-supplied Overleaf project https://www.overleaf.com/project/6a7b4742e20ac910c422a7e0; its contained paper(s) and source accessibility are unverified.; Local user-provided research template/style/checklist inspected 2026-09-11; no manuscript-specific .tex or .bib exists under papers/.
- Reuse candidates: papers/vericodegen_neurosymbolic_supervision_workshop_draft.pdf, papers/completion/neurosymbolic_supervision/paper_extracted.txt, https://www.overleaf.com/project/6a7b4742e20ac910c422a7e0, papers/neurips_2026_vericode_workshop.tex, papers/neurips_2026_vericode.sty, papers/checklist.tex
- Receipt: papers/completion/neurosymbolic_supervision/receipts/NS-001.json

Inspect the user-supplied Overleaf project https://www.overleaf.com/project/6a7b4742e20ac910c422a7e0 using available authorized access, first verifying which paper(s) it contains. Access/authentication and source download are not established. Search accessible repository history, attachments/artifacts, and source locations for the original LaTeX, BibTeX, figures, and template. If unavailable, reconstruct editable sources from the PDF and extracted text, recording equation/table/citation discrepancies. Source access must not block independent inventory, protocol, or runner work. Preserve the original PDF and do not invent author details. The user has now provided local research-format inputs: papers/neurips_2026_vericode_workshop.tex, papers/neurips_2026_vericode.sty, and papers/checklist.tex. These are formatting/checklist sources, not recovered manuscript text or bibliography; the three manuscript LaTeX/BibTeX sources remain absent. Use the local research shell for any reconstruction, keeping its style unchanged, and preserve the originals. Do not substitute papers/neurips_2026_vericode_workshop_competition.tex, its competition style, or the generic papers/neurips_2026.sty.

Acceptance criteria:

1. Editable source builds to PDF with one documented command.
2. All sections, equations, tables, and references are either recovered or explicitly reconciled against the baseline.
3. A source-origin record distinguishes original recovery from reconstruction and lists unresolved author-owned material.
4. Overleaf source provenance and project-to-paper identity are verified if accessible; otherwise access remains explicitly unresolved and reconstruction proceeds without blocking protocol/code work.
5. Manuscript-specific source recovery is distinguished from the now-available local research template and checklist; reconstruction uses the local research shell without modifying shared inputs.

Record dependencies, exact code/data/model/tool versions, actual command logs, failures and claim limitations in the receipt. Expand this task into bounded follow-ups when discovery requires it; preserve its goal and evidence obligations.

## NS-002 Inventory the actual loaded forest and reproduce provenance of preliminary artifacts

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: neurosymbolic_supervision
- Depends on: 
- Goal id: NS-SG1
- Parent goal: NS-G000
- Objective heap: papers/completion/neurosymbolic_supervision/paper.objectives.md
- Board namespace: vericodegen-2026-neurosymbolic_supervision
- Bundle: neurosymbolic_supervision/NS-SG1
- Parallel lane: neurosymbolic_supervision
- Outputs: papers/completion/neurosymbolic_supervision/artifacts/source_forest.json, papers/completion/neurosymbolic_supervision/artifacts/capabilities.json, papers/completion/neurosymbolic_supervision/audit/implementation_inventory.json, papers/completion/neurosymbolic_supervision/audit/preliminary_evidence.json, papers/completion/neurosymbolic_supervision/receipts/NS-002.json
- Predicted files: papers/completion/neurosymbolic_supervision/artifacts/source_forest.json, papers/completion/neurosymbolic_supervision/artifacts/capabilities.json, papers/completion/neurosymbolic_supervision/audit/implementation_inventory.json, papers/completion/neurosymbolic_supervision/audit/preliminary_evidence.json, papers/completion/neurosymbolic_supervision/receipts/NS-002.json, papers/completion/neurosymbolic_supervision/receipts/snapshots/NS-002/
- Allowed paths: 
- Resource class: cpu-medium
- Resource stage: execution
- Implementation timeout seconds: 7200
- Validation: python3 scripts/paper_supervisors.py verify-task --paper neurosymbolic_supervision --task NS-002
- Acceptance: Manifest captures loaded __file__ locations, source digests, commits/overlays, interpreter/dependency versions, native binaries, and rollout flags.; Each draft mechanism receives independent location/implementation/integration/validation/rollout statuses.; Table 5 values are traceable to raw artifacts; absence of live model receipts and measured prover timing is retained.; No optional unavailable component is described as operational or used to block unrelated work.
- Paper evidence: PDF pp. 1–2, §1: final artifact must freeze exact multi-repository forest; PDF p. 8, Table 5: 40 controlled tasks and 40 sealer transitions; PDF p. 9, §9.1; p. 20, §H.2: standalone heads differ from consumer pins
- Reuse candidates: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/semantic_state/, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/incremental_sealing/, external/ipfs_accelerate/docs/benchmarks/semantic_compression_harness_results.md, external/ipfs_accelerate/artifacts/agent_supervisor/incremental_proof_sealer/summary.json, external/ipfs_datasets/ipfs_datasets_py/logic/software_contracts/
- Receipt: papers/completion/neurosymbolic_supervision/receipts/NS-002.json

Map every retained mechanism to code commit/path, gitlink, overlay, import path, dependency lock, runtime mode, capability, and original evidence. Resolve duplicate external and hallucinate_app copies. Locate ProcedureCegis, CompositionEdge, incremental SMT, CEGAR, and abstract-interpreter claims in their actual worktrees or mark unresolved/specification-only. Recompute the preliminary table arithmetic from existing raw artifacts without treating it as a new live experiment; record estimated versus measured provenance. Work in a paper-specific isolated checkout and coordinate with active code owners.

Acceptance criteria:

1. Manifest captures loaded __file__ locations, source digests, commits/overlays, interpreter/dependency versions, native binaries, and rollout flags.
2. Each draft mechanism receives independent location/implementation/integration/validation/rollout statuses.
3. Table 5 values are traceable to raw artifacts; absence of live model receipts and measured prover timing is retained.
4. No optional unavailable component is described as operational or used to block unrelated work.

Record dependencies, exact code/data/model/tool versions, actual command logs, failures and claim limitations in the receipt. Expand this task into bounded follow-ups when discovery requires it; preserve its goal and evidence obligations.

## NS-003 Freeze a claim-to-evidence matrix and a bounded submission scope

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: neurosymbolic_supervision
- Depends on: NS-002
- Goal id: NS-SG1
- Parent goal: NS-G000
- Objective heap: papers/completion/neurosymbolic_supervision/paper.objectives.md
- Board namespace: vericodegen-2026-neurosymbolic_supervision
- Bundle: neurosymbolic_supervision/NS-SG1
- Parallel lane: neurosymbolic_supervision
- Outputs: papers/completion/neurosymbolic_supervision/audit/claim_evidence_matrix.json, papers/completion/neurosymbolic_supervision/protocol/scope.md, papers/completion/neurosymbolic_supervision/protocol/deadline_plan.md, papers/completion/neurosymbolic_supervision/receipts/NS-003.json
- Predicted files: papers/completion/neurosymbolic_supervision/audit/claim_evidence_matrix.json, papers/completion/neurosymbolic_supervision/protocol/scope.md, papers/completion/neurosymbolic_supervision/protocol/deadline_plan.md, papers/completion/neurosymbolic_supervision/receipts/NS-003.json, papers/completion/neurosymbolic_supervision/receipts/snapshots/NS-003/
- Allowed paths: 
- Resource class: cpu-medium
- Resource stage: execution
- Implementation timeout seconds: 7200
- Validation: python3 scripts/paper_supervisors.py verify-task --paper neurosymbolic_supervision --task NS-003
- Acceptance: Every main-text claim and Table 17/18 row has an evidence obligation or an explicit removal/narrowing decision.; Required core tasks are separated from optional implementation campaigns; unavailable optional backends have a truthful closure path.; The paper goal cannot pass by emptying a queue or changing the oracle/acceptance standard.; No author identity, consent, model-use facts, or positive results are inferred.
- Paper evidence: PDF pp. 1–2, §1: mechanism and measured status distinguished; PDF pp. 15–21, Appendices D–H: optional world/refactor/learning programs; PDF p. 25, §K.2: final author actions
- Reuse candidates: papers/completion/neurosymbolic_supervision/review.md, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/semantic_state/, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/semantic_governor/
- Receipt: papers/completion/neurosymbolic_supervision/receipts/NS-003.json

List every empirical, formal, implementation, deployment, and novelty claim with required evidence and owning task. Prioritize the semantic-context/routing/reuse/publication core. For each optional solver, Groth16, learned world model, procedure/refactoring, federation, and semantic editing extension, choose retained-and-qualified or explicitly future-work/unavailable wording. Preserve prior no-go results. Record a deadline-aware plan against the current CFP/portal, with no automatic submission or undocumented scope inflation.

Acceptance criteria:

1. Every main-text claim and Table 17/18 row has an evidence obligation or an explicit removal/narrowing decision.
2. Required core tasks are separated from optional implementation campaigns; unavailable optional backends have a truthful closure path.
3. The paper goal cannot pass by emptying a queue or changing the oracle/acceptance standard.
4. No author identity, consent, model-use facts, or positive results are inferred.

Record dependencies, exact code/data/model/tool versions, actual command logs, failures and claim limitations in the receipt. Expand this task into bounded follow-ups when discovery requires it; preserve its goal and evidence obligations.

## NS-004 Preregister the matched protocol, metrics, budgets, and statistical criteria

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: neurosymbolic_supervision
- Depends on: NS-003
- Goal id: NS-SG2
- Parent goal: NS-G000
- Objective heap: papers/completion/neurosymbolic_supervision/paper.objectives.md
- Board namespace: vericodegen-2026-neurosymbolic_supervision
- Bundle: neurosymbolic_supervision/NS-SG2
- Parallel lane: neurosymbolic_supervision
- Outputs: papers/completion/neurosymbolic_supervision/protocol/preregistered_protocol.md, papers/completion/neurosymbolic_supervision/protocol/experiment_manifest.json, papers/completion/neurosymbolic_supervision/protocol/measurement_schema.json, papers/completion/neurosymbolic_supervision/receipts/NS-004.json
- Predicted files: papers/completion/neurosymbolic_supervision/protocol/preregistered_protocol.md, papers/completion/neurosymbolic_supervision/protocol/experiment_manifest.json, papers/completion/neurosymbolic_supervision/protocol/measurement_schema.json, papers/completion/neurosymbolic_supervision/receipts/NS-004.json, papers/completion/neurosymbolic_supervision/receipts/snapshots/NS-004/
- Allowed paths: 
- Resource class: cpu-medium
- Resource stage: execution
- Implementation timeout seconds: 7200
- Validation: python3 scripts/paper_supervisors.py verify-task --paper neurosymbolic_supervision --task NS-004
- Acceptance: Protocol has an immutable version/hash before final runs, with model settings, all arms, metrics, and data-access boundaries.; Noninferiority margin, minimum useful completion threshold, CI method, and promotion/no-promotion criteria are specified before final outcomes.; Actual versus estimated/unavailable cost fields and amortization horizons are defined.; Simulations and checked-in oracle patches cannot count as live repair results.
- Paper evidence: PDF pp. 7–8, §8 and Table 4; PDF p. 8, §8.3: noninferiority margin and useful-completion threshold; PDF p. 24, Table 17: A–D comparison
- Reuse candidates: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/semantic_state/baseline.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/semantic_state/benchmark.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/semantic_state/receipts.py
- Receipt: papers/completion/neurosymbolic_supervision/receipts/NS-004.json

Specify A raw/lexical + full validation, B semantic + same validation, C added symbolic routing/reuse, D governed lifecycle with matched models/revisions, tasks, budgets, environments, and acceptance criteria. Define one-factor ablations, deny-all diagnostic, cold/warm cache states, randomized paired run order, repetitions, timeouts, exclusions, failure/abstention denominators, false accept/deny units, and an independent scoring plan. Choose final sample sizes from a documented feasibility/uncertainty rationale; use a separate pilot to finalize before seeing final outcomes. Set explicit provider/compute limits from available authorized resources and surface missing capacity honestly.

Acceptance criteria:

1. Protocol has an immutable version/hash before final runs, with model settings, all arms, metrics, and data-access boundaries.
2. Noninferiority margin, minimum useful completion threshold, CI method, and promotion/no-promotion criteria are specified before final outcomes.
3. Actual versus estimated/unavailable cost fields and amortization horizons are defined.
4. Simulations and checked-in oracle patches cannot count as live repair results.

Record dependencies, exact code/data/model/tool versions, actual command logs, failures and claim limitations in the receipt. Expand this task into bounded follow-ups when discovery requires it; preserve its goal and evidence obligations.

## NS-005 Freeze historical tasks, holdouts, adversarial cases, and independent oracles

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: neurosymbolic_supervision
- Depends on: NS-004
- Goal id: NS-SG2
- Parent goal: NS-G000
- Objective heap: papers/completion/neurosymbolic_supervision/paper.objectives.md
- Board namespace: vericodegen-2026-neurosymbolic_supervision
- Bundle: neurosymbolic_supervision/NS-SG2
- Parallel lane: neurosymbolic_supervision
- Outputs: papers/completion/neurosymbolic_supervision/benchmark/tasks.jsonl, papers/completion/neurosymbolic_supervision/benchmark/splits.json, papers/completion/neurosymbolic_supervision/benchmark/oracle_manifest.json, papers/completion/neurosymbolic_supervision/benchmark/provenance.md, papers/completion/neurosymbolic_supervision/audit/leakage_audit.json, papers/completion/neurosymbolic_supervision/receipts/NS-005.json
- Predicted files: papers/completion/neurosymbolic_supervision/benchmark/tasks.jsonl, papers/completion/neurosymbolic_supervision/benchmark/splits.json, papers/completion/neurosymbolic_supervision/benchmark/oracle_manifest.json, papers/completion/neurosymbolic_supervision/benchmark/provenance.md, papers/completion/neurosymbolic_supervision/audit/leakage_audit.json, papers/completion/neurosymbolic_supervision/receipts/NS-005.json, papers/completion/neurosymbolic_supervision/receipts/snapshots/NS-005/
- Allowed paths: 
- Resource class: cpu-medium
- Resource stage: execution
- Implementation timeout seconds: 7200
- Validation: python3 scripts/paper_supervisors.py verify-task --paper neurosymbolic_supervision --task NS-005
- Acceptance: Every task has a fixed pre-fix snapshot, expected baseline condition, independent acceptance criteria, provenance, and split assignment.; Deduplication covers near-duplicate families, prior fixtures, related-paper corpora, and patch/acceptance leakage.; Invalid/valid paired cases cover all retained Table 18 boundaries and Table 12 mutation categories.; Population size and exclusions are fixed before final outcomes; no favorable-case selection is permitted.
- Paper evidence: PDF p. 7, §8.2: exact pre-fix tasks and hidden target patches/oracles; PDF p. 19, Table 12: cohort and fault-check matrix; PDF p. 16, §D.5.3: source-family splits and no-go preservation
- Reuse candidates: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/semantic_state/benchmark.py, external/ipfs_accelerate/docs/benchmarks/semantic_compression_harness_results.md, data/agent_supervisor/deterministic_contract_repair/benchmark.json
- Receipt: papers/completion/neurosymbolic_supervision/receipts/NS-005.json

Build a licensed/provenance-documented population of genuine pre-fix tasks plus controlled adversarial qualification cases. Pin each source snapshot, issue/specification, baseline-valid tests, acceptance oracle, dynamic-feature class, and task family. Split development/pilot/final and any learning holdouts by repository family and time. Keep hidden target patches and acceptance outputs outside proposal context. Reuse the 40 existing semantic fixtures as preliminary/qualification data only unless a separately justified task is independently generated.

Acceptance criteria:

1. Every task has a fixed pre-fix snapshot, expected baseline condition, independent acceptance criteria, provenance, and split assignment.
2. Deduplication covers near-duplicate families, prior fixtures, related-paper corpora, and patch/acceptance leakage.
3. Invalid/valid paired cases cover all retained Table 18 boundaries and Table 12 mutation categories.
4. Population size and exclusions are fixed before final outcomes; no favorable-case selection is permitted.

Record dependencies, exact code/data/model/tool versions, actual command logs, failures and claim limitations in the receipt. Expand this task into bounded follow-ups when discovery requires it; preserve its goal and evidence obligations.

## NS-006 Implement the paired runner and measure real provider, validation, and resource boundaries

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: neurosymbolic_supervision
- Depends on: NS-002, NS-004
- Goal id: NS-SG2
- Parent goal: NS-G000
- Objective heap: papers/completion/neurosymbolic_supervision/paper.objectives.md
- Board namespace: vericodegen-2026-neurosymbolic_supervision
- Bundle: neurosymbolic_supervision/NS-SG2
- Parallel lane: neurosymbolic_supervision
- Outputs: papers/completion/neurosymbolic_supervision/experiments/run_comparison.py, papers/completion/neurosymbolic_supervision/experiments/score_runs.py, papers/completion/neurosymbolic_supervision/experiments/README.md, papers/completion/neurosymbolic_supervision/experiments/receipt_schema.json, papers/completion/neurosymbolic_supervision/audit/runner_validation.json, papers/completion/neurosymbolic_supervision/receipts/NS-006.json
- Predicted files: papers/completion/neurosymbolic_supervision/experiments/run_comparison.py, papers/completion/neurosymbolic_supervision/experiments/score_runs.py, papers/completion/neurosymbolic_supervision/experiments/README.md, papers/completion/neurosymbolic_supervision/experiments/receipt_schema.json, papers/completion/neurosymbolic_supervision/audit/runner_validation.json, papers/completion/neurosymbolic_supervision/receipts/NS-006.json, papers/completion/neurosymbolic_supervision/receipts/snapshots/NS-006/
- Allowed paths: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/semantic_state/harness.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/semantic_state/providers.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/semantic_state/receipts.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/semantic_state/durable_state.py
- Resource class: cpu-medium
- Resource stage: execution
- Implementation timeout seconds: 7200
- Validation: python3 scripts/paper_supervisors.py verify-task --paper neurosymbolic_supervision --task NS-006
- Acceptance: Runner exposes reproducible commands for one task, one arm, paired runs, and rescoring.; Provider receipts identify actual model/provider/revision and separate simulated/development from admitted production paths.; Attempt outcomes distinguish solved/unsolved/rejected/abstained/timed-out/unavailable/cancelled; end-to-end elapsed is measured directly.; Results bind task/protocol/source forest/evidence IDs and survive interruption without duplicate provider charging or fabricated completion.
- Paper evidence: PDF p. 8, lines 262–270: actual provider boundaries and net cost; PDF p. 19, §G.1: stage costs and elapsed time; PDF p. 27, Algorithm 1: intended composed loop
- Reuse candidates: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/semantic_state/harness.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/semantic_state/providers.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/semantic_state/receipts.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/semantic_state/durable_state.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/semantic_state/verification.py
- Receipt: papers/completion/neurosymbolic_supervision/receipts/NS-006.json

Extend the existing semantic-state harness and production provider gateway in an isolated paper worktree. Implement versioned A–D configuration, immutable per-attempt receipts, fixed-budget termination, randomization/seeds, explicit terminal states, and independent scorer interfaces. Measure actual input/output/cached tokens, call counts/charges, elapsed/CPU/GPU/memory/storage, setup/call/teardown, prove/verify/persist/retry/recover, and human waits. Log actual consumed evidence and next decisions; record unavailable measurements as null with reasons. The runner must never elevate production authority or modify protected acceptance standards merely to make a benchmark pass.

Acceptance criteria:

1. Runner exposes reproducible commands for one task, one arm, paired runs, and rescoring.
2. Provider receipts identify actual model/provider/revision and separate simulated/development from admitted production paths.
3. Attempt outcomes distinguish solved/unsolved/rejected/abstained/timed-out/unavailable/cancelled; end-to-end elapsed is measured directly.
4. Results bind task/protocol/source forest/evidence IDs and survive interruption without duplicate provider charging or fabricated completion.

Record dependencies, exact code/data/model/tool versions, actual command logs, failures and claim limitations in the receipt. Expand this task into bounded follow-ups when discovery requires it; preserve its goal and evidence obligations.

## NS-007 Qualify semantic context, invalidation, and source-preserving repair parity

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: neurosymbolic_supervision
- Depends on: NS-006
- Goal id: NS-SG3
- Parent goal: NS-G000
- Objective heap: papers/completion/neurosymbolic_supervision/paper.objectives.md
- Board namespace: vericodegen-2026-neurosymbolic_supervision
- Bundle: neurosymbolic_supervision/NS-SG3
- Parallel lane: neurosymbolic_supervision
- Outputs: papers/completion/neurosymbolic_supervision/qualification/context_cases.json, papers/completion/neurosymbolic_supervision/qualification/context_results.jsonl, papers/completion/neurosymbolic_supervision/qualification/context_report.md, papers/completion/neurosymbolic_supervision/receipts/NS-007.json
- Predicted files: papers/completion/neurosymbolic_supervision/qualification/context_cases.json, papers/completion/neurosymbolic_supervision/qualification/context_results.jsonl, papers/completion/neurosymbolic_supervision/qualification/context_report.md, papers/completion/neurosymbolic_supervision/receipts/NS-007.json, papers/completion/neurosymbolic_supervision/receipts/snapshots/NS-007/
- Allowed paths: 
- Resource class: cpu-medium
- Resource stage: execution
- Implementation timeout seconds: 7200
- Validation: python3 scripts/paper_supervisors.py verify-task --paper neurosymbolic_supervision --task NS-007
- Acceptance: All retained context cases preserve mandatory acceptance material and expose unknown/opaque frontiers.; Cold/incremental roots and selected/full validation agree within the declared profile; mismatches receive failures and cause fixes or explicit limitations.; Valid source-bound patches apply and stale/out-of-scope preimages reject.; Context reduction is measured with the same actual tokenizer for both modes, with fallback rates retained.
- Paper evidence: PDF pp. 2, 5, §§2.3/5.1/5.2: unknown frontier and non-truncatable acceptance core; PDF p. 19, Table 12: state and selection parity; PDF p. 20, PCSM row: stale-map and round-trip tests
- Reuse candidates: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/semantic_state/context_pack.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/semantic_state/worktree.py, external/ipfs_datasets/ipfs_datasets_py/logic/software_contracts/semantic_index/, external/ipfs_datasets/ipfs_datasets_py/logic/software_contracts/semantic_state/
- Receipt: papers/completion/neurosymbolic_supervision/receipts/NS-007.json

Exercise the current semantic producer and context consumer on unchanged, localized, renamed/deleted, configuration/dependency, fixture, dynamic/native, and stale-map changes. Verify cold versus incremental roots, edited target source, preserved goal/scope/authority/test/proof obligations, explicit expansion references, and exact patch preimages in fenced worktrees. Compare raw/semantic selection against full regressions. Qualify only the actual source-linked edit path; keep unsupported CST/alias/IR linking out of the implemented claim.

Acceptance criteria:

1. All retained context cases preserve mandatory acceptance material and expose unknown/opaque frontiers.
2. Cold/incremental roots and selected/full validation agree within the declared profile; mismatches receive failures and cause fixes or explicit limitations.
3. Valid source-bound patches apply and stale/out-of-scope preimages reject.
4. Context reduction is measured with the same actual tokenizer for both modes, with fallback rates retained.

Record dependencies, exact code/data/model/tool versions, actual command logs, failures and claim limitations in the receipt. Expand this task into bounded follow-ups when discovery requires it; preserve its goal and evidence obligations.

## NS-008 Exercise deterministic closure and authorized residual dispatch through the real caller

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: neurosymbolic_supervision
- Depends on: NS-006
- Goal id: NS-SG3
- Parent goal: NS-G000
- Objective heap: papers/completion/neurosymbolic_supervision/paper.objectives.md
- Board namespace: vericodegen-2026-neurosymbolic_supervision
- Bundle: neurosymbolic_supervision/NS-SG3
- Parallel lane: neurosymbolic_supervision
- Outputs: papers/completion/neurosymbolic_supervision/qualification/provider_gate_cases.json, papers/completion/neurosymbolic_supervision/qualification/provider_gate_receipts.jsonl, papers/completion/neurosymbolic_supervision/qualification/provider_gate_report.md, papers/completion/neurosymbolic_supervision/receipts/NS-008.json
- Predicted files: papers/completion/neurosymbolic_supervision/qualification/provider_gate_cases.json, papers/completion/neurosymbolic_supervision/qualification/provider_gate_receipts.jsonl, papers/completion/neurosymbolic_supervision/qualification/provider_gate_report.md, papers/completion/neurosymbolic_supervision/receipts/NS-008.json, papers/completion/neurosymbolic_supervision/receipts/snapshots/NS-008/
- Allowed paths: 
- Resource class: cpu-medium
- Resource stage: execution
- Implementation timeout seconds: 7200
- Validation: python3 scripts/paper_supervisors.py verify-task --paper neurosymbolic_supervision --task NS-008
- Acceptance: At least one valid residual request reaches the intended real provider and produces a traceable independently checked outcome.; At least one deterministic closure progresses without a provider call and passes the fixed oracle.; Each invalid pair fails for the expected binding/authority reason; missing capabilities stay unavailable.; No workflow-level savings are inferred from zero hooks inside the kernel, and deny-all cannot pass useful-progress criteria.
- Paper evidence: PDF p. 4, §4.2: positive-path witness and closes_claim limitation; PDF p. 23, §I.3.4: deny-all diagnostic; PDF p. 25, Table 18: provider-gate row
- Reuse candidates: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/todo_daemon/pre_implementation_kernel.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/todo_daemon/implementation_disposition.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/semantic_state/providers.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/control/authorization_logic.py
- Receipt: papers/completion/neurosymbolic_supervision/receipts/NS-008.json

Construct caller-level paired cases with exact task/forest/plan/doctor/obligation/authority bindings. Demonstrate a real permitted residual provider request, a downstream-validated deterministic repair, and minimally altered stale/missing/mismatched requests that reject or defer. Cover ambiguity, unavailable capabilities, repeated requests, and unknown provider effects. Count model invocations at the actual provider boundary and independently validate candidates rather than trusting a boolean claim-closure flag.

Acceptance criteria:

1. At least one valid residual request reaches the intended real provider and produces a traceable independently checked outcome.
2. At least one deterministic closure progresses without a provider call and passes the fixed oracle.
3. Each invalid pair fails for the expected binding/authority reason; missing capabilities stay unavailable.
4. No workflow-level savings are inferred from zero hooks inside the kernel, and deny-all cannot pass useful-progress criteria.

Record dependencies, exact code/data/model/tool versions, actual command logs, failures and claim limitations in the receipt. Expand this task into bounded follow-ups when discovery requires it; preserve its goal and evidence obligations.

## NS-009 Validate translation preservation and retained symbolic checker admission

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: neurosymbolic_supervision
- Depends on: NS-006
- Goal id: NS-SG3
- Parent goal: NS-G000
- Objective heap: papers/completion/neurosymbolic_supervision/paper.objectives.md
- Board namespace: vericodegen-2026-neurosymbolic_supervision
- Bundle: neurosymbolic_supervision/NS-SG3
- Parallel lane: neurosymbolic_supervision
- Outputs: papers/completion/neurosymbolic_supervision/qualification/logic_cases.json, papers/completion/neurosymbolic_supervision/qualification/logic_receipts.jsonl, papers/completion/neurosymbolic_supervision/qualification/logic_profiles.json, papers/completion/neurosymbolic_supervision/qualification/logic_report.md, papers/completion/neurosymbolic_supervision/receipts/NS-009.json
- Predicted files: papers/completion/neurosymbolic_supervision/qualification/logic_cases.json, papers/completion/neurosymbolic_supervision/qualification/logic_receipts.jsonl, papers/completion/neurosymbolic_supervision/qualification/logic_profiles.json, papers/completion/neurosymbolic_supervision/qualification/logic_report.md, papers/completion/neurosymbolic_supervision/receipts/NS-009.json, papers/completion/neurosymbolic_supervision/receipts/snapshots/NS-009/
- Allowed paths: 
- Resource class: cpu-medium
- Resource stage: execution
- Implementation timeout seconds: 7200
- Validation: python3 scripts/paper_supervisors.py verify-task --paper neurosymbolic_supervision --task NS-009
- Acceptance: Valid supported translations can progress; unjustified lifting from modal-erasing or otherwise lossy projections cannot admit the source claim.; Actual caller receipts bind exact formulas/source/theory/solver/environment and reject stale or unvalidated results.; Vacuity, unknown, unsupported, and budget-exhausted cases remain distinct from meaningful proof.; Any claimed CEGAR/interpolant/composition behavior is supported by located code and actual evidence; no unavailable mechanism is silently simulated.
- Paper evidence: PDF p. 3, §3.2: lossy projection and SMT limits; PDF p. 13, §B.2: assertion/formula-root/replay tests; PDF p. 22, §§I.1–I.2; pp. 25–26, Appendix L
- Reuse candidates: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/logic_translation_validation.py, external/ipfs_datasets/ipfs_datasets_py/logic/TDFOL/tdfol_converter.py, external/ipfs_datasets/ipfs_datasets_py/logic/admissibility/enforcement.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/solver_readiness.py
- Receipt: papers/completion/neurosymbolic_supervision/receipts/NS-009.json

Use the actual converter, translation contract, caller, and resolved solver modules. Add modal/temporal countermodels where source truth differs despite identical projection. Exercise supported positive translations, unsupported clauses, inconsistent guarantees, reachability, cyclic composition closure, duplicate named assertions/assumptions, stale formula roots and solver fingerprints, SAT/UNSAT/unknown/timeout, and invalid interpolants. Record solver versus reconstruction/kernel evidence classes and whether assertions are replayed or solver state is retained. If named draft modules remain unavailable, qualify the present profile and narrow the corresponding assertions.

Acceptance criteria:

1. Valid supported translations can progress; unjustified lifting from modal-erasing or otherwise lossy projections cannot admit the source claim.
2. Actual caller receipts bind exact formulas/source/theory/solver/environment and reject stale or unvalidated results.
3. Vacuity, unknown, unsupported, and budget-exhausted cases remain distinct from meaningful proof.
4. Any claimed CEGAR/interpolant/composition behavior is supported by located code and actual evidence; no unavailable mechanism is silently simulated.

Record dependencies, exact code/data/model/tool versions, actual command logs, failures and claim limitations in the receipt. Expand this task into bounded follow-ups when discovery requires it; preserve its goal and evidence obligations.

## NS-010 Implement or close the fixture-instance and phase-aware reuse seam

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: neurosymbolic_supervision
- Depends on: NS-006
- Goal id: NS-SG3
- Parent goal: NS-G000
- Objective heap: papers/completion/neurosymbolic_supervision/paper.objectives.md
- Board namespace: vericodegen-2026-neurosymbolic_supervision
- Bundle: neurosymbolic_supervision/NS-SG3
- Parallel lane: neurosymbolic_supervision
- Outputs: papers/completion/neurosymbolic_supervision/qualification/reuse_profile.json, papers/completion/neurosymbolic_supervision/qualification/reuse_adapter_report.md, papers/completion/neurosymbolic_supervision/qualification/reuse_phase_cases.json, papers/completion/neurosymbolic_supervision/receipts/NS-010.json
- Predicted files: papers/completion/neurosymbolic_supervision/qualification/reuse_profile.json, papers/completion/neurosymbolic_supervision/qualification/reuse_adapter_report.md, papers/completion/neurosymbolic_supervision/qualification/reuse_phase_cases.json, papers/completion/neurosymbolic_supervision/receipts/NS-010.json, papers/completion/neurosymbolic_supervision/receipts/snapshots/NS-010/
- Allowed paths: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/validation/proof_cached_test_validation.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/test_proof_cache.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/test_certificate_store.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/integrations/ipfs_datasets_test_certificate_provider.py, external/ipfs_datasets/ipfs_datasets_py/logic/software_contracts/semantic_state/test_selection.py
- Resource class: cpu-medium
- Resource stage: execution
- Implementation timeout seconds: 7200
- Validation: python3 scripts/paper_supervisors.py verify-task --paper neurosymbolic_supervision --task NS-010
- Acceptance: Reuse lookup cannot itself become a passing outcome.; Changed fixture definitions/values/plugins/policy/runtime/external snapshots invalidate or force execution even when the test body is unchanged.; Call reuse after setup still runs required teardown; teardown failure prevents whole-item pass.; An unchanged eligible case demonstrably reuses a prior admitted result, while unknown/effectful cases use an explicit fallback.
- Paper evidence: PDF p. 6, §§6.2–6.3; PDF pp. 13–14, Appendix C, Table 8: staged identity and lifecycle protocol
- Reuse candidates: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/validation/proof_cached_test_validation.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/test_proof_cache.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/test_certificate_store.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/integrations/ipfs_datasets_test_certificate_provider.py, external/ipfs_datasets/ipfs_datasets_py/logic/software_contracts/semantic_state/test_selection.py
- Receipt: papers/completion/neurosymbolic_supervision/receipts/NS-010.json

Inspect current cache/certificate/provider code and fill only the staged identity gaps needed for the frozen reuse profile. Bind collection and fixture definitions, transitive/autouse fixtures, parametrization, plugins/hooks/conftest, reviewed DI instance commitments, interpreter/dependency/policy/external snapshots, and setup/call/teardown outcomes. Distinguish full-item reuse before setup from call-only reuse after setup. Retain required finalizers/effects, bound xdist/session ownership, reject arbitrary opaque serialization, and fall back to execution for incomplete closures.

Acceptance criteria:

1. Reuse lookup cannot itself become a passing outcome.
2. Changed fixture definitions/values/plugins/policy/runtime/external snapshots invalidate or force execution even when the test body is unchanged.
3. Call reuse after setup still runs required teardown; teardown failure prevents whole-item pass.
4. An unchanged eligible case demonstrably reuses a prior admitted result, while unknown/effectful cases use an explicit fallback.

Record dependencies, exact code/data/model/tool versions, actual command logs, failures and claim limitations in the receipt. Expand this task into bounded follow-ups when discovery requires it; preserve its goal and evidence obligations.

## NS-011 Independently cold-score reuse and adversarial dependency mutations

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: neurosymbolic_supervision
- Depends on: NS-005, NS-010
- Goal id: NS-SG3
- Parent goal: NS-G000
- Objective heap: papers/completion/neurosymbolic_supervision/paper.objectives.md
- Board namespace: vericodegen-2026-neurosymbolic_supervision
- Bundle: neurosymbolic_supervision/NS-SG3
- Parallel lane: neurosymbolic_supervision
- Outputs: papers/completion/neurosymbolic_supervision/qualification/cold_oracle_results.jsonl, papers/completion/neurosymbolic_supervision/qualification/reuse_mutation_results.jsonl, papers/completion/neurosymbolic_supervision/qualification/reuse_analysis.json, papers/completion/neurosymbolic_supervision/receipts/NS-011.json
- Predicted files: papers/completion/neurosymbolic_supervision/qualification/cold_oracle_results.jsonl, papers/completion/neurosymbolic_supervision/qualification/reuse_mutation_results.jsonl, papers/completion/neurosymbolic_supervision/qualification/reuse_analysis.json, papers/completion/neurosymbolic_supervision/receipts/NS-011.json, papers/completion/neurosymbolic_supervision/receipts/snapshots/NS-011/
- Allowed paths: 
- Resource class: cpu-medium
- Resource stage: execution
- Implementation timeout seconds: 7200
- Validation: python3 scripts/paper_supervisors.py verify-task --paper neurosymbolic_supervision --task NS-011
- Acceptance: Cold execution and reuse are independently recorded for every scored case; skipped/unavailable oracle cases cannot count as safe agreement.; Each required mutation has an expected invalidation/fallback decision and a genuine unchanged positive reuse witness.; False-reuse rate includes all attempted reuse cases and reports exact counts/uncertainty, including observed failures.; Any discovered unsound reuse blocks the affected profile until fixed/requalified or explicitly excluded from the paper claim.
- Paper evidence: PDF p. 6, §6.3: projection completeness is the hard premise; PDF pp. 13–14, §C.2; p. 19, Table 12: cold oracle and phase faults; PDF p. 23, §I.3.2: runtime traces do not prove closure
- Reuse candidates: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/semantic_state/selection_execution.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/semantic_state/verification.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/validation/proof_cached_test_validation.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/test_certificate_store.py
- Receipt: papers/completion/neurosymbolic_supervision/receipts/NS-011.json

Run the frozen reuse qualification cohort through both admitted reuse and an independent cold full runner. Mutate fixtures/instances/finalizers/plugins/hooks/config/policies/keys/runtime/external snapshots, include test removal, stale cache, incomplete traces, changed external effects, and nontrivial unchanged cases. Score every attempted false reuse, false denial, oracle disagreement, lifecycle outcome, cache hit, and fallback with explicit denominators. Keep the full oracle unavailable to candidate generation.

Acceptance criteria:

1. Cold execution and reuse are independently recorded for every scored case; skipped/unavailable oracle cases cannot count as safe agreement.
2. Each required mutation has an expected invalidation/fallback decision and a genuine unchanged positive reuse witness.
3. False-reuse rate includes all attempted reuse cases and reports exact counts/uncertainty, including observed failures.
4. Any discovered unsound reuse blocks the affected profile until fixed/requalified or explicitly excluded from the paper claim.

Record dependencies, exact code/data/model/tool versions, actual command logs, failures and claim limitations in the receipt. Expand this task into bounded follow-ups when discovery requires it; preserve its goal and evidence obligations.

## NS-012 Qualify complete inventories, parallel sealing, CAS, and useful restart recovery

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: neurosymbolic_supervision
- Depends on: NS-006
- Goal id: NS-SG3
- Parent goal: NS-G000
- Objective heap: papers/completion/neurosymbolic_supervision/paper.objectives.md
- Board namespace: vericodegen-2026-neurosymbolic_supervision
- Bundle: neurosymbolic_supervision/NS-SG3
- Parallel lane: neurosymbolic_supervision
- Outputs: papers/completion/neurosymbolic_supervision/qualification/sealer_fault_matrix.json, papers/completion/neurosymbolic_supervision/qualification/sealer_results.jsonl, papers/completion/neurosymbolic_supervision/qualification/recovery_receipts.jsonl, papers/completion/neurosymbolic_supervision/qualification/sealer_recovery_report.md, papers/completion/neurosymbolic_supervision/receipts/NS-012.json
- Predicted files: papers/completion/neurosymbolic_supervision/qualification/sealer_fault_matrix.json, papers/completion/neurosymbolic_supervision/qualification/sealer_results.jsonl, papers/completion/neurosymbolic_supervision/qualification/recovery_receipts.jsonl, papers/completion/neurosymbolic_supervision/qualification/sealer_recovery_report.md, papers/completion/neurosymbolic_supervision/receipts/NS-012.json, papers/completion/neurosymbolic_supervision/receipts/snapshots/NS-012/
- Allowed paths: 
- Resource class: cpu-medium
- Resource stage: execution
- Implementation timeout seconds: 7200
- Validation: python3 scripts/paper_supervisors.py verify-task --paper neurosymbolic_supervision --task NS-012
- Acceptance: Sequential/parallel bytes, roots, inventories, and dispositions match on identical inputs; worker order cannot alter authority.; An empty or incomplete manifest cannot pass a mandatory obligation; membership alone is never completeness.; Stale/late/failed writers cannot replace the accepted root or invent task success.; Restart retains admitted evidence and resumes a useful valid task without unobserved duplicate effects; external exactly-once behavior is not claimed beyond the tested boundary.; Prepare/verify/persist/CAS CPU/memory/storage/elapsed measurements are real and separately labeled.
- Paper evidence: PDF pp. 6–7, §7: complete manifests and accepted publication; PDF pp. 11–14, Appendix A.1 and Table 9; PDF pp. 18–19, §F.4 and Table 12: concurrency/federation fault cases
- Reuse candidates: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/incremental_sealing/, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/semantic_state/durable_state.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/semantic_state/harness.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/merge/worktree_lifecycle.py, external/ipfs_kit/ipfs_kit_py/proof_certificate_store.py
- Receipt: papers/completion/neurosymbolic_supervision/receipts/NS-012.json

Run deterministic sequential/parallel preparation at multiple worker counts with exact canonical profile/order. Inject missing/duplicate required units, corrupt blocks/hash memo, stale parent/generation/fence, interrupted persistence, CAS conflict, crashes around artifact/task publication, duplicated/reordered events, unknown provider results, and store unavailability. Assert durable reconciliation across artifact, operational, and Git state. Include a valid continuation after recovery. Restrict federation/network claims to the tested deployment and retain unavailable remote faults explicitly.

Acceptance criteria:

1. Sequential/parallel bytes, roots, inventories, and dispositions match on identical inputs; worker order cannot alter authority.
2. An empty or incomplete manifest cannot pass a mandatory obligation; membership alone is never completeness.
3. Stale/late/failed writers cannot replace the accepted root or invent task success.
4. Restart retains admitted evidence and resumes a useful valid task without unobserved duplicate effects; external exactly-once behavior is not claimed beyond the tested boundary.
5. Prepare/verify/persist/CAS CPU/memory/storage/elapsed measurements are real and separately labeled.

Record dependencies, exact code/data/model/tool versions, actual command logs, failures and claim limitations in the receipt. Expand this task into bounded follow-ups when discovery requires it; preserve its goal and evidence obligations.

## NS-013 Record one complete state-to-repair-to-certificate-to-publication witness

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: neurosymbolic_supervision
- Depends on: NS-007, NS-008, NS-009, NS-010, NS-012
- Goal id: NS-SG3
- Parent goal: NS-G000
- Objective heap: papers/completion/neurosymbolic_supervision/paper.objectives.md
- Board namespace: vericodegen-2026-neurosymbolic_supervision
- Bundle: neurosymbolic_supervision/NS-SG3
- Parallel lane: neurosymbolic_supervision
- Outputs: papers/completion/neurosymbolic_supervision/qualification/end_to_end_witness.json, papers/completion/neurosymbolic_supervision/qualification/end_to_end_trace.jsonl, papers/completion/neurosymbolic_supervision/qualification/end_to_end_case_study.md, papers/completion/neurosymbolic_supervision/receipts/NS-013.json
- Predicted files: papers/completion/neurosymbolic_supervision/qualification/end_to_end_witness.json, papers/completion/neurosymbolic_supervision/qualification/end_to_end_trace.jsonl, papers/completion/neurosymbolic_supervision/qualification/end_to_end_case_study.md, papers/completion/neurosymbolic_supervision/receipts/NS-013.json, papers/completion/neurosymbolic_supervision/receipts/snapshots/NS-013/
- Allowed paths: 
- Resource class: cpu-medium
- Resource stage: execution
- Implementation timeout seconds: 7200
- Validation: python3 scripts/paper_supervisors.py verify-task --paper neurosymbolic_supervision --task NS-013
- Acceptance: A genuine task progresses from authorized input to independently accepted patch and matching published post-root.; Every step links current source/task/plan/obligation/evidence IDs; relevant symbolic/context evidence visibly changes the route or admission decision.; The valid permitted action still works while the specified denied-effect violation is repaired/rejected.; A rejected or incomplete path cannot report completion, and simulation-only runs remain labeled qualification rather than live success.
- Paper evidence: PDF p. 11, Appendix A, Table 6: illustrative guard-before-write cycle; PDF p. 26, §L.4: evidence must change control decisions; PDF p. 27, Algorithm 1: intended composition not yet observed
- Reuse candidates: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/semantic_state/harness.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/semantic_state/work_loop.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/todo_daemon/pre_implementation_kernel.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/incremental_sealing/sealer.py
- Receipt: papers/completion/neurosymbolic_supervision/receipts/NS-013.json

Turn the bounded guard-before-write example or an equivalently frozen genuine historical task into a complete integrated run. Capture actual pre-state/obligation/counterexample, admitted plan and route, candidate patch, independent validation/reuse, complete requirement manifest, accepted parent-bound publication, and operational completion. Include permitted writes, denied no-write behavior, exceptions/finalization, API scope, and a minimally altered invalid case. Use exact source/receipt identifiers instead of schematic R0/P0/T0 labels.

Acceptance criteria:

1. A genuine task progresses from authorized input to independently accepted patch and matching published post-root.
2. Every step links current source/task/plan/obligation/evidence IDs; relevant symbolic/context evidence visibly changes the route or admission decision.
3. The valid permitted action still works while the specified denied-effect violation is repaired/rejected.
4. A rejected or incomplete path cannot report completion, and simulation-only runs remain labeled qualification rather than live success.

Record dependencies, exact code/data/model/tool versions, actual command logs, failures and claim limitations in the receipt. Expand this task into bounded follow-ups when discovery requires it; preserve its goal and evidence obligations.

## NS-014 Qualify the named native proof profile or explicitly close its scope as unavailable

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P1
- Track: neurosymbolic_supervision
- Depends on: NS-002, NS-003
- Goal id: NS-SG3
- Parent goal: NS-G000
- Objective heap: papers/completion/neurosymbolic_supervision/paper.objectives.md
- Board namespace: vericodegen-2026-neurosymbolic_supervision
- Bundle: neurosymbolic_supervision/NS-SG3
- Parallel lane: neurosymbolic_supervision
- Outputs: papers/completion/neurosymbolic_supervision/qualification/native_profile.json, papers/completion/neurosymbolic_supervision/qualification/native_results.jsonl, papers/completion/neurosymbolic_supervision/qualification/native_scope_decision.md, papers/completion/neurosymbolic_supervision/receipts/NS-014.json
- Predicted files: papers/completion/neurosymbolic_supervision/qualification/native_profile.json, papers/completion/neurosymbolic_supervision/qualification/native_results.jsonl, papers/completion/neurosymbolic_supervision/qualification/native_scope_decision.md, papers/completion/neurosymbolic_supervision/receipts/NS-014.json, papers/completion/neurosymbolic_supervision/receipts/snapshots/NS-014/
- Allowed paths: 
- Resource class: cpu-medium
- Resource stage: execution
- Implementation timeout seconds: 7200
- Validation: python3 scripts/paper_supervisors.py verify-task --paper neurosymbolic_supervision --task NS-014
- Acceptance: A retained native result includes genuine proof payload, exact statement/public input binding, verified key/circuit/profile, backend version, and measured generation/verification evidence.; Outer source/test metadata, key/profile changes, missing mandatory tests, and simulated/test-only artifacts receive explicit dispositions.; Unavailable native proving is reported as unavailable, not zero cost or successful simulation.; No arbitrary CPython/pytest execution or full temporal/deontic semantics are inferred from the Horn-fragment adapter.
- Paper evidence: PDF p. 5, §6.1; pp. 23–24, Appendix J; PDF p. 24, Table 16: inner/outer binding and key attacks; PDF p. 25, Table 18: native theorem/circuit row
- Reuse candidates: external/ipfs_datasets/ipfs_datasets_py/logic/zkp/backends/groth16.py, external/ipfs_datasets/ipfs_datasets_py/logic/zkp/backends/groth16_ffi.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/incremental_sealing/provers.py
- Receipt: papers/completion/neurosymbolic_supervision/receipts/NS-014.json

For a retained native-proof claim, establish actual compiled backend/circuit version/verification key/setup origin/public inputs and permitted relation, then run positive proof generation/verification and Table 16 adversarial boundary cases with measured costs. Distinguish atoms/implications derivation, runner attestation, and direct runtime execution statements. If resources or an appropriate backend/profile are absent, create an unavailable/untested evidence record and revise this optional claim/row to the supported mechanism-only scope; do not launch an unrelated circuit implementation campaign.

Acceptance criteria:

1. A retained native result includes genuine proof payload, exact statement/public input binding, verified key/circuit/profile, backend version, and measured generation/verification evidence.
2. Outer source/test metadata, key/profile changes, missing mandatory tests, and simulated/test-only artifacts receive explicit dispositions.
3. Unavailable native proving is reported as unavailable, not zero cost or successful simulation.
4. No arbitrary CPython/pytest execution or full temporal/deontic semantics are inferred from the Horn-fragment adapter.

Record dependencies, exact code/data/model/tool versions, actual command logs, failures and claim limitations in the receipt. Expand this task into bounded follow-ups when discovery requires it; preserve its goal and evidence obligations.

## NS-015 Qualify retained procedures/world consumption/refactoring or narrow extensions

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P1
- Track: neurosymbolic_supervision
- Depends on: NS-002, NS-003
- Goal id: NS-SG3
- Parent goal: NS-G000
- Objective heap: papers/completion/neurosymbolic_supervision/paper.objectives.md
- Board namespace: vericodegen-2026-neurosymbolic_supervision
- Bundle: neurosymbolic_supervision/NS-SG3
- Parallel lane: neurosymbolic_supervision
- Outputs: papers/completion/neurosymbolic_supervision/qualification/extensions_scope.json, papers/completion/neurosymbolic_supervision/qualification/extension_holdout_protocol.md, papers/completion/neurosymbolic_supervision/qualification/extension_results.jsonl, papers/completion/neurosymbolic_supervision/qualification/extensions_report.md, papers/completion/neurosymbolic_supervision/receipts/NS-015.json
- Predicted files: papers/completion/neurosymbolic_supervision/qualification/extensions_scope.json, papers/completion/neurosymbolic_supervision/qualification/extension_holdout_protocol.md, papers/completion/neurosymbolic_supervision/qualification/extension_results.jsonl, papers/completion/neurosymbolic_supervision/qualification/extensions_report.md, papers/completion/neurosymbolic_supervision/receipts/NS-015.json, papers/completion/neurosymbolic_supervision/receipts/snapshots/NS-015/
- Allowed paths: 
- Resource class: cpu-medium
- Resource stage: execution
- Implementation timeout seconds: 7200
- Validation: python3 scripts/paper_supervisors.py verify-task --paper neurosymbolic_supervision --task NS-015
- Acceptance: Every retained extension has an actual located implementation, independent holdout protocol, and consumed-result evidence.; Training/synthesis cannot inspect final acceptance outputs; applicability failures, abstentions, bad predictions, and rollback costs remain visible.; Guarded/required consumption is distinguished from shadow writing/reading, with no worker self-promotion or protected-validator edits.; Unevaluated broad W1–W4, graph learning, or remodularization claims are removed/narrowed without blocking the measured core.
- Paper evidence: PDF p. 5, §5.3; p. 7, §7.4; PDF pp. 15–21, Appendices D–H; PDF p. 25, Table 18: required world/procedure consumption
- Reuse candidates: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/planning/, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/autonomous_repair/, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/semantic_state/world_view.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/semantic_state/world_snapshot_builder.py, implementation_plan/proof_grounded_ir_learning_fabric/
- Receipt: papers/completion/neurosymbolic_supervision/receipts/NS-015.json

Resolve source and active-owner status before extending procedure/world/refactoring work. For retained claims, define a bounded operator/task family, current applicability and authority checks, held-out family/time splits, independent validation/rollback, static/history/lexical/embedding/template controls, negative memory, and actual consumed pre/post evidence. Measure downstream repair/usefulness rather than sidecar logging. Evaluate learned candidates only if a distinct frozen learned artifact exists. Otherwise preserve earlier no-go status and mark these optional mechanisms as planned future work, closing their Table 18 obligations with explicit untested scope.

Acceptance criteria:

1. Every retained extension has an actual located implementation, independent holdout protocol, and consumed-result evidence.
2. Training/synthesis cannot inspect final acceptance outputs; applicability failures, abstentions, bad predictions, and rollback costs remain visible.
3. Guarded/required consumption is distinguished from shadow writing/reading, with no worker self-promotion or protected-validator edits.
4. Unevaluated broad W1–W4, graph learning, or remodularization claims are removed/narrowed without blocking the measured core.

Record dependencies, exact code/data/model/tool versions, actual command logs, failures and claim limitations in the receipt. Expand this task into bounded follow-ups when discovery requires it; preserve its goal and evidence obligations.

## NS-016 Pilot on development data and freeze final runtime, protocol, and task population

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: neurosymbolic_supervision
- Depends on: NS-005, NS-011, NS-013, NS-014, NS-015
- Goal id: NS-SG4
- Parent goal: NS-G000
- Objective heap: papers/completion/neurosymbolic_supervision/paper.objectives.md
- Board namespace: vericodegen-2026-neurosymbolic_supervision
- Bundle: neurosymbolic_supervision/NS-SG4
- Parallel lane: neurosymbolic_supervision
- Outputs: papers/completion/neurosymbolic_supervision/pilot/results.jsonl, papers/completion/neurosymbolic_supervision/pilot/readiness_report.md, papers/completion/neurosymbolic_supervision/artifacts/final_experiment_freeze.json, papers/completion/neurosymbolic_supervision/protocol/final_run_manifest.json, papers/completion/neurosymbolic_supervision/receipts/NS-016.json
- Predicted files: papers/completion/neurosymbolic_supervision/pilot/results.jsonl, papers/completion/neurosymbolic_supervision/pilot/readiness_report.md, papers/completion/neurosymbolic_supervision/artifacts/final_experiment_freeze.json, papers/completion/neurosymbolic_supervision/protocol/final_run_manifest.json, papers/completion/neurosymbolic_supervision/receipts/NS-016.json, papers/completion/neurosymbolic_supervision/receipts/snapshots/NS-016/
- Allowed paths: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/semantic_state/harness.py
- Resource class: cpu-medium
- Resource stage: execution
- Implementation timeout seconds: 7200
- Validation: python3 scripts/paper_supervisors.py verify-task --paper neurosymbolic_supervision --task NS-016
- Acceptance: Pilot tasks are excluded from final holdouts and labeled developmental.; Each retained arm has a valid useful path and completed independent scoring, or is explicitly removed with claims updated before final runs.; All receipts required by Tables 17/18 and cost analysis can be produced; missing provider/resources have honest readiness statuses.; Final source/task/protocol/scorer manifests are immutable and hashed before the first final attempt.
- Paper evidence: PDF p. 7, §8.1: freeze before paired conditions; PDF p. 20, §H.1: qualify seams before combined attribution
- Reuse candidates: papers/completion/neurosymbolic_supervision/experiments/run_comparison.py, papers/completion/neurosymbolic_supervision/experiments/score_runs.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/semantic_state/harness.py
- Receipt: papers/completion/neurosymbolic_supervision/receipts/NS-016.json

Run a small separate development pilot to validate all retained arms, oracle isolation, receipt completeness, resource estimates, model availability, and interruption handling. Fix harness defects through the existing owners; update the protocol only before the final freeze. Confirm sample-size/repetition feasibility and explicitly record any scoped-down but scientifically valid design before final outcomes. Freeze code, dependencies, model settings, data/splits, costs/limits, scoring scripts, and analysis plan.

Acceptance criteria:

1. Pilot tasks are excluded from final holdouts and labeled developmental.
2. Each retained arm has a valid useful path and completed independent scoring, or is explicitly removed with claims updated before final runs.
3. All receipts required by Tables 17/18 and cost analysis can be produced; missing provider/resources have honest readiness statuses.
4. Final source/task/protocol/scorer manifests are immutable and hashed before the first final attempt.

Record dependencies, exact code/data/model/tool versions, actual command logs, failures and claim limitations in the receipt. Expand this task into bounded follow-ups when discovery requires it; preserve its goal and evidence obligations.

## NS-017 Execute the frozen paired A–D main comparison with real outcomes

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: neurosymbolic_supervision
- Depends on: NS-016
- Goal id: NS-SG4
- Parent goal: NS-G000
- Objective heap: papers/completion/neurosymbolic_supervision/paper.objectives.md
- Board namespace: vericodegen-2026-neurosymbolic_supervision
- Bundle: neurosymbolic_supervision/NS-SG4
- Parallel lane: neurosymbolic_supervision
- Outputs: papers/completion/neurosymbolic_supervision/runs/main/manifest.json, papers/completion/neurosymbolic_supervision/runs/main/attempts.jsonl, papers/completion/neurosymbolic_supervision/runs/main/provider_receipts.jsonl, papers/completion/neurosymbolic_supervision/runs/main/resource_measurements.jsonl, papers/completion/neurosymbolic_supervision/runs/main/deviations.md, papers/completion/neurosymbolic_supervision/receipts/NS-017.json
- Predicted files: papers/completion/neurosymbolic_supervision/runs/main/manifest.json, papers/completion/neurosymbolic_supervision/runs/main/attempts.jsonl, papers/completion/neurosymbolic_supervision/runs/main/provider_receipts.jsonl, papers/completion/neurosymbolic_supervision/runs/main/resource_measurements.jsonl, papers/completion/neurosymbolic_supervision/runs/main/deviations.md, papers/completion/neurosymbolic_supervision/receipts/NS-017.json, papers/completion/neurosymbolic_supervision/receipts/snapshots/NS-017/
- Allowed paths: 
- Resource class: cpu-medium
- Resource stage: execution
- Implementation timeout seconds: 7200
- Validation: python3 scripts/paper_supervisors.py verify-task --paper neurosymbolic_supervision --task NS-017
- Acceptance: All planned task-arm-repeat units have an actual terminal record or explicitly documented missingness; denominator changes are prohibited after outcomes.; Useful completions are independently validated and linked to admitted publication where the arm requires it.; Actual provider and stage measurements support the final cost fields; estimated/unavailable data remain distinct.; Raw records and deviations bind the immutable final experiment freeze and are sufficient for independent rescoring.
- Paper evidence: PDF p. 24, Table 17: all main results TBD; PDF pp. 7–8, §8: useful progress and net cost
- Reuse candidates: papers/completion/neurosymbolic_supervision/experiments/run_comparison.py, papers/completion/neurosymbolic_supervision/protocol/final_run_manifest.json
- Receipt: papers/completion/neurosymbolic_supervision/receipts/NS-017.json

Execute the final paired conditions using the fixed population, randomized order, repetitions, resource limits, and exact source/model/runtime versions. Preserve raw prompts or permitted summaries, provider responses/receipts, patches, independent validation, publication and terminal-state receipts, cold/warm identities, and resource logs. Resume from durable run state without silently retrying unknown paid effects. Record all unsolved/unavailable/timeout outcomes and deviations; never replace failed tasks or replay fixture patches to improve the table.

Acceptance criteria:

1. All planned task-arm-repeat units have an actual terminal record or explicitly documented missingness; denominator changes are prohibited after outcomes.
2. Useful completions are independently validated and linked to admitted publication where the arm requires it.
3. Actual provider and stage measurements support the final cost fields; estimated/unavailable data remain distinct.
4. Raw records and deviations bind the immutable final experiment freeze and are sufficient for independent rescoring.

Record dependencies, exact code/data/model/tool versions, actual command logs, failures and claim limitations in the receipt. Expand this task into bounded follow-ups when discovery requires it; preserve its goal and evidence obligations.

## NS-018 Run isolated component ablations and warm/cold cost comparisons

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: neurosymbolic_supervision
- Depends on: NS-016
- Goal id: NS-SG4
- Parent goal: NS-G000
- Objective heap: papers/completion/neurosymbolic_supervision/paper.objectives.md
- Board namespace: vericodegen-2026-neurosymbolic_supervision
- Bundle: neurosymbolic_supervision/NS-SG4
- Parallel lane: neurosymbolic_supervision
- Outputs: papers/completion/neurosymbolic_supervision/runs/ablations/manifest.json, papers/completion/neurosymbolic_supervision/runs/ablations/attempts.jsonl, papers/completion/neurosymbolic_supervision/runs/ablations/resource_measurements.jsonl, papers/completion/neurosymbolic_supervision/runs/ablations/deviations.md, papers/completion/neurosymbolic_supervision/receipts/NS-018.json
- Predicted files: papers/completion/neurosymbolic_supervision/runs/ablations/manifest.json, papers/completion/neurosymbolic_supervision/runs/ablations/attempts.jsonl, papers/completion/neurosymbolic_supervision/runs/ablations/resource_measurements.jsonl, papers/completion/neurosymbolic_supervision/runs/ablations/deviations.md, papers/completion/neurosymbolic_supervision/receipts/NS-018.json, papers/completion/neurosymbolic_supervision/receipts/snapshots/NS-018/
- Allowed paths: 
- Resource class: cpu-medium
- Resource stage: execution
- Implementation timeout seconds: 7200
- Validation: python3 scripts/paper_supervisors.py verify-task --paper neurosymbolic_supervision --task NS-018
- Acceptance: Each retained efficiency mechanism has a matched isolated comparison or an explicit non-attributable limitation.; Controls differ only in declared factors; enabled checks and acceptance standards are recorded.; Deny-all contributes only diagnostic safety/cost evidence and cannot satisfy useful-progress promotion.; Ablation failures, extra fallback, proof/index/setup/training costs, and slower workloads remain in outputs.
- Paper evidence: PDF p. 7, §8.1: orthogonal component ablations; PDF p. 8, Table 4 and §8.3; PDF p. 19, Table 12
- Reuse candidates: papers/completion/neurosymbolic_supervision/experiments/run_comparison.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/semantic_state/baseline.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/incremental_sealing/metrics.py
- Receipt: papers/completion/neurosymbolic_supervision/receipts/NS-018.json

Execute preregistered one-factor comparisons for translation checks, symbolic routing, semantic context selection, test/proof reuse, parallel preparation, and procedures if retained. Include cold/warm state, full cold validation, sequential/parallel sealer, and route-level deterministic/model outcomes. Unsafe disabled-check controls must stay in the isolated adversarial harness with publication disabled. Use the same independent oracle, task pairs, model limits, and evidence schema; report package effects separately from isolated effects.

Acceptance criteria:

1. Each retained efficiency mechanism has a matched isolated comparison or an explicit non-attributable limitation.
2. Controls differ only in declared factors; enabled checks and acceptance standards are recorded.
3. Deny-all contributes only diagnostic safety/cost evidence and cannot satisfy useful-progress promotion.
4. Ablation failures, extra fallback, proof/index/setup/training costs, and slower workloads remain in outputs.

Record dependencies, exact code/data/model/tool versions, actual command logs, failures and claim limitations in the receipt. Expand this task into bounded follow-ups when discovery requires it; preserve its goal and evidence obligations.

## NS-019 Independently score main outcomes, confidence intervals, and net economics

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: neurosymbolic_supervision
- Depends on: NS-017, NS-018
- Goal id: NS-SG5
- Parent goal: NS-G000
- Objective heap: papers/completion/neurosymbolic_supervision/paper.objectives.md
- Board namespace: vericodegen-2026-neurosymbolic_supervision
- Bundle: neurosymbolic_supervision/NS-SG5
- Parallel lane: neurosymbolic_supervision
- Outputs: papers/completion/neurosymbolic_supervision/analysis/analyze.py, papers/completion/neurosymbolic_supervision/analysis/results.json, papers/completion/neurosymbolic_supervision/analysis/statistical_report.md, papers/completion/neurosymbolic_supervision/analysis/cost_report.md, papers/completion/neurosymbolic_supervision/manuscript/generated/table17.tex, papers/completion/neurosymbolic_supervision/manuscript/generated/ablations.tex, papers/completion/neurosymbolic_supervision/manuscript/generated/figures/, papers/completion/neurosymbolic_supervision/receipts/NS-019.json
- Predicted files: papers/completion/neurosymbolic_supervision/analysis/analyze.py, papers/completion/neurosymbolic_supervision/analysis/results.json, papers/completion/neurosymbolic_supervision/analysis/statistical_report.md, papers/completion/neurosymbolic_supervision/analysis/cost_report.md, papers/completion/neurosymbolic_supervision/manuscript/generated/table17.tex, papers/completion/neurosymbolic_supervision/manuscript/generated/ablations.tex, papers/completion/neurosymbolic_supervision/manuscript/generated/figures/, papers/completion/neurosymbolic_supervision/receipts/NS-019.json, papers/completion/neurosymbolic_supervision/receipts/snapshots/NS-019/
- Allowed paths: 
- Resource class: cpu-medium
- Resource stage: execution
- Implementation timeout seconds: 7200
- Validation: python3 scripts/paper_supervisors.py verify-task --paper neurosymbolic_supervision --task NS-019
- Acceptance: One documented analysis command regenerates main and ablation tables from immutable raw records.; All counts reconcile to the run manifest, including failed/unsolved/timeout/abstained/unavailable cases.; Confidence intervals and quality gates follow the preregistered plan; deviations and inconclusive outcomes are explicit.; No estimated preliminary number is labeled measured, no missing cost is zero, and overlapping stage times are not summed as elapsed.
- Paper evidence: PDF p. 8, §8.3; p. 19, §G.1; PDF p. 24, Table 17; p. 1 abstract results placeholder
- Reuse candidates: papers/completion/neurosymbolic_supervision/experiments/score_runs.py, papers/completion/neurosymbolic_supervision/runs/main/, papers/completion/neurosymbolic_supervision/runs/ablations/
- Receipt: papers/completion/neurosymbolic_supervision/receipts/NS-019.json

Run the fixed independent scorer over all attempts. Compute accepted solved/total, false acceptance and denial with denominators, dispatch-conditional solve rates, useful-progress/replan latency, fallback/churn/manual intervention, paired differences, median/distribution and confidence intervals, stratified dynamic/task classes, and noninferiority/useful-completion decisions. Measure tokens/charges/resources, directly observed elapsed/human time, cold-start setup and break-even amortization. Explain unavailable GPU/prover/currency observations and finite zero-failure bounds. Generate tables/plots solely from raw evidence.

Acceptance criteria:

1. One documented analysis command regenerates main and ablation tables from immutable raw records.
2. All counts reconcile to the run manifest, including failed/unsolved/timeout/abstained/unavailable cases.
3. Confidence intervals and quality gates follow the preregistered plan; deviations and inconclusive outcomes are explicit.
4. No estimated preliminary number is labeled measured, no missing cost is zero, and overlapping stage times are not summed as elapsed.

Record dependencies, exact code/data/model/tool versions, actual command logs, failures and claim limitations in the receipt. Expand this task into bounded follow-ups when discovery requires it; preserve its goal and evidence obligations.

## NS-020 Resolve all six boundary rows and finish the empirical claim ledger

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: neurosymbolic_supervision
- Depends on: NS-011, NS-012, NS-013, NS-014, NS-015, NS-019
- Goal id: NS-SG5
- Parent goal: NS-G000
- Objective heap: papers/completion/neurosymbolic_supervision/paper.objectives.md
- Board namespace: vericodegen-2026-neurosymbolic_supervision
- Bundle: neurosymbolic_supervision/NS-SG5
- Parallel lane: neurosymbolic_supervision
- Outputs: papers/completion/neurosymbolic_supervision/analysis/boundary_witnesses.json, papers/completion/neurosymbolic_supervision/manuscript/generated/table18.tex, papers/completion/neurosymbolic_supervision/audit/final_claim_evidence_matrix.json, papers/completion/neurosymbolic_supervision/analysis/failure_cases.md, papers/completion/neurosymbolic_supervision/receipts/NS-020.json
- Predicted files: papers/completion/neurosymbolic_supervision/analysis/boundary_witnesses.json, papers/completion/neurosymbolic_supervision/manuscript/generated/table18.tex, papers/completion/neurosymbolic_supervision/audit/final_claim_evidence_matrix.json, papers/completion/neurosymbolic_supervision/analysis/failure_cases.md, papers/completion/neurosymbolic_supervision/receipts/NS-020.json, papers/completion/neurosymbolic_supervision/receipts/snapshots/NS-020/
- Allowed paths: 
- Resource class: cpu-medium
- Resource stage: execution
- Implementation timeout seconds: 7200
- Validation: python3 scripts/paper_supervisors.py verify-task --paper neurosymbolic_supervision --task NS-020
- Acceptance: Every Table 18 cell has an evidence-backed outcome/ID or explicit untested/unavailable scope; no TBD or synthetic proof of progress remains.; All retained claims point to code/runtime/population and reproducible measured artifacts.; False-admission, false-reuse, inability to dispatch, and recovery failures remain visible and trigger narrowed conclusions where required.; Author-only plans and old campaign success labels cannot override current evidence.
- Paper evidence: PDF p. 25, Table 18: 18 TBD cells; PDF p. 24, Table 16: native boundary mutations; PDF p. 25, §K.2: report negative/missing results
- Reuse candidates: papers/completion/neurosymbolic_supervision/qualification/, papers/completion/neurosymbolic_supervision/analysis/results.json
- Receipt: papers/completion/neurosymbolic_supervision/receipts/NS-020.json

Generate Table 18 from actual paired valid/invalid evidence at provider, translation, retained native, fixture lifecycle, restart publication, and retained world/procedure boundaries. For optional unclaimed mechanisms, use a clear untested/unavailable/out-of-scope disposition and matching text changes. Reconcile every numerical/implementation/deployment assertion against the frozen evidence; preserve negative results and specify which acceptance assumptions remain trusted or untested.

Acceptance criteria:

1. Every Table 18 cell has an evidence-backed outcome/ID or explicit untested/unavailable scope; no TBD or synthetic proof of progress remains.
2. All retained claims point to code/runtime/population and reproducible measured artifacts.
3. False-admission, false-reuse, inability to dispatch, and recovery failures remain visible and trigger narrowed conclusions where required.
4. Author-only plans and old campaign success labels cannot override current evidence.

Record dependencies, exact code/data/model/tool versions, actual command logs, failures and claim limitations in the receipt. Expand this task into bounded follow-ups when discovery requires it; preserve its goal and evidence obligations.

## NS-021 Verify references, anonymous artifact citations, and distinct contribution

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: neurosymbolic_supervision
- Depends on: NS-003
- Goal id: NS-SG6
- Parent goal: NS-G000
- Objective heap: papers/completion/neurosymbolic_supervision/paper.objectives.md
- Board namespace: vericodegen-2026-neurosymbolic_supervision
- Bundle: neurosymbolic_supervision/NS-SG6
- Parallel lane: neurosymbolic_supervision
- Outputs: papers/completion/neurosymbolic_supervision/audit/reference_audit.md, papers/completion/neurosymbolic_supervision/audit/artifact_citation_map.json, papers/completion/neurosymbolic_supervision/audit/related_paper_overlap.md, papers/completion/neurosymbolic_supervision/audit/verified_references.bib, papers/completion/neurosymbolic_supervision/receipts/NS-021.json
- Predicted files: papers/completion/neurosymbolic_supervision/audit/reference_audit.md, papers/completion/neurosymbolic_supervision/audit/artifact_citation_map.json, papers/completion/neurosymbolic_supervision/audit/related_paper_overlap.md, papers/completion/neurosymbolic_supervision/audit/verified_references.bib, papers/completion/neurosymbolic_supervision/receipts/NS-021.json, papers/completion/neurosymbolic_supervision/receipts/snapshots/NS-021/
- Allowed paths: 
- Resource class: cpu-medium
- Resource stage: execution
- Implementation timeout seconds: 7200
- Validation: python3 scripts/paper_supervisors.py verify-task --paper neurosymbolic_supervision --task NS-021
- Acceptance: Every citation resolves to a primary bibliographic source or accessible anonymous artifact and supports the adjacent statement.; No unresolvable internal shorthand or identifying repository link remains in the submission.; Claims of novelty are bounded by the literature and the experiment, without invented first-of-kind claims.; Shared data/code/evaluation across the three submissions is disclosed appropriately and not double-counted as independent replication.
- Paper evidence: PDF pp. 9–10, §9.2 and references 1–12; PDF throughout: internal D/A/N/K/P/W labels; PDF p. 21, §H.3: author-only companion reconciliation handoff
- Reuse candidates: papers/completion/neurosymbolic_supervision/paper_extracted.txt, papers/completion/neurosymbolic_supervision/audit/claim_evidence_matrix.json
- Receipt: papers/completion/neurosymbolic_supervision/receipts/NS-021.json

Verify all 12 bibliography entries, identifiers, and attributed technical statements against primary sources. Resolve internal workstream labels to concise anonymous artifact citations or remove them; replace author-only review/reconciliation history with scientific descriptions. State the novelty as the tested supervision/evidence composition, with direct comparisons to relevant agent, regression-testing/build/reuse, formalization and proof-carrying methods. Coordinate a nonidentifying overlap/distinct-contribution audit with the autoformalization and law-to-action papers without implying independent evidence when datasets/code are shared.

Acceptance criteria:

1. Every citation resolves to a primary bibliographic source or accessible anonymous artifact and supports the adjacent statement.
2. No unresolvable internal shorthand or identifying repository link remains in the submission.
3. Claims of novelty are bounded by the literature and the experiment, without invented first-of-kind claims.
4. Shared data/code/evaluation across the three submissions is disclosed appropriately and not double-counted as independent replication.

Record dependencies, exact code/data/model/tool versions, actual command logs, failures and claim limitations in the receipt. Expand this task into bounded follow-ups when discovery requires it; preserve its goal and evidence obligations.

## NS-022 Rewrite the manuscript around measured results and remove every placeholder

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: neurosymbolic_supervision
- Depends on: NS-001, NS-019, NS-020, NS-021, NS-023
- Goal id: NS-SG6
- Parent goal: NS-G000
- Objective heap: papers/completion/neurosymbolic_supervision/paper.objectives.md
- Board namespace: vericodegen-2026-neurosymbolic_supervision
- Bundle: neurosymbolic_supervision/NS-SG6
- Parallel lane: neurosymbolic_supervision
- Outputs: papers/completion/neurosymbolic_supervision/manuscript/main.tex, papers/completion/neurosymbolic_supervision/manuscript/paper.pdf, papers/completion/neurosymbolic_supervision/audit/manuscript_result_checks.json, papers/completion/neurosymbolic_supervision/audit/revision_notes.md, papers/completion/neurosymbolic_supervision/receipts/NS-022.json
- Predicted files: papers/completion/neurosymbolic_supervision/manuscript/main.tex, papers/completion/neurosymbolic_supervision/manuscript/paper.pdf, papers/completion/neurosymbolic_supervision/audit/manuscript_result_checks.json, papers/completion/neurosymbolic_supervision/audit/revision_notes.md, papers/completion/neurosymbolic_supervision/receipts/NS-022.json, papers/completion/neurosymbolic_supervision/receipts/snapshots/NS-022/
- Allowed paths: 
- Resource class: cpu-medium
- Resource stage: execution
- Implementation timeout seconds: 7200
- Validation: python3 scripts/paper_supervisors.py verify-task --paper neurosymbolic_supervision --task NS-022
- Acceptance: Abstract numbers and conclusions exactly match generated results and their population/uncertainty/limitations.; No TBD, TO BE FILLED, RESULTS placeholder, unsupported success assertion, or unresolved internal artifact label remains in scientific text.; The main text clearly states research question, novel composition, trusted assumptions, matched method/baseline, results, and negative cases.; Supplemental breadth cannot be mistaken for evaluated implementation; final scientific scope matches the claim ledger.
- Paper evidence: PDF p. 1 abstract [RESULTS]; p. 8 [TO BE FILLED]; PDF pp. 24–25, Tables 17–18; PDF pp. 15–21: implementation-plan material; PDF p. 27, Algorithm 1: intended versus executed composition
- Reuse candidates: papers/completion/neurosymbolic_supervision/manuscript/, papers/completion/neurosymbolic_supervision/analysis/, papers/completion/neurosymbolic_supervision/audit/final_claim_evidence_matrix.json
- Receipt: papers/completion/neurosymbolic_supervision/receipts/NS-022.json

Rewrite abstract/introduction/method/evaluation/conclusion around the supported core and actual findings. Integrate generated Tables 17/18 and useful ablations/figures into a 4–9 main-page narrative. Separate preliminary estimates from live measurements and proof sketches from implementation enforcement. Convert the schematic cycle into the evidence-backed example if qualified. Narrow optional extensions and move/remove author-only campaign directives, duplicated explanations, and unsupported deployment assertions. Replace all result/benchmark placeholders, while factual author-owned disclosure content is handled in the artifact/disclosure task. Integrate the verified bibliography from audit/verified_references.bib into the recovered manuscript in this task so independent source recovery and reference auditing do not edit the same bibliography concurrently.

Acceptance criteria:

1. Abstract numbers and conclusions exactly match generated results and their population/uncertainty/limitations.
2. No TBD, TO BE FILLED, RESULTS placeholder, unsupported success assertion, or unresolved internal artifact label remains in scientific text.
3. The main text clearly states research question, novel composition, trusted assumptions, matched method/baseline, results, and negative cases.
4. Supplemental breadth cannot be mistaken for evaluated implementation; final scientific scope matches the claim ledger.

Record dependencies, exact code/data/model/tool versions, actual command logs, failures and claim limitations in the receipt. Expand this task into bounded follow-ups when discovery requires it; preserve its goal and evidence obligations.

## NS-023 Audit the conditional acceptance and reuse arguments against actual gates

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: neurosymbolic_supervision
- Depends on: NS-009, NS-012
- Goal id: NS-SG5
- Parent goal: NS-G000
- Objective heap: papers/completion/neurosymbolic_supervision/paper.objectives.md
- Board namespace: vericodegen-2026-neurosymbolic_supervision
- Bundle: neurosymbolic_supervision/NS-SG5
- Parallel lane: neurosymbolic_supervision
- Outputs: papers/completion/neurosymbolic_supervision/audit/formal_argument_review.md, papers/completion/neurosymbolic_supervision/audit/assumption_gate_map.json, papers/completion/neurosymbolic_supervision/manuscript/formal_arguments.tex, papers/completion/neurosymbolic_supervision/receipts/NS-023.json
- Predicted files: papers/completion/neurosymbolic_supervision/audit/formal_argument_review.md, papers/completion/neurosymbolic_supervision/audit/assumption_gate_map.json, papers/completion/neurosymbolic_supervision/manuscript/formal_arguments.tex, papers/completion/neurosymbolic_supervision/receipts/NS-023.json, papers/completion/neurosymbolic_supervision/receipts/snapshots/NS-023/
- Allowed paths: 
- Resource class: cpu-medium
- Resource stage: execution
- Implementation timeout seconds: 7200
- Validation: python3 scripts/paper_supervisors.py verify-task --paper neurosymbolic_supervision --task NS-023
- Acceptance: Each formal statement has precise scope, premises, conclusion, and a valid argument reviewed independently of generated prose.; Implementation evidence supports only tested premises; external side-effect atomicity and universal dependency closure are not inferred.; Unknown/inconsistent specifications and incomplete projections cannot be silently discharged by the argument.; The final algorithm is labeled executed composition only where the integrated witness supports it.
- Paper evidence: PDF p. 7, Eq. 2 and §7.3; PDF pp. 22–23, §I.3.1–I.3.3; PDF p. 27, Algorithm 1
- Reuse candidates: papers/completion/neurosymbolic_supervision/qualification/logic_report.md, papers/completion/neurosymbolic_supervision/qualification/sealer_recovery_report.md, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/semantic_state/durable_state.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/incremental_sealing/admission.py
- Receipt: papers/completion/neurosymbolic_supervision/receipts/NS-023.json

Check the accepted-lineage induction and dependency-projection reuse argument for precise hypotheses, nonvacuity, statement scope, and consistency with implemented call chains. State initial-root policy, complete-manifest/checker/translation/current-parent/exclusive-publication/protected-authority assumptions and deterministic observation/effect projection requirements. Map each assumption to qualification evidence or trusted limitation. Explain separate behavioral correctness, action permission, and publication decisions. Keep sketches explicitly unmachine-checked unless actual proof artifacts are independently checked; do not initiate unnecessary universal-Python proof work.

Acceptance criteria:

1. Each formal statement has precise scope, premises, conclusion, and a valid argument reviewed independently of generated prose.
2. Implementation evidence supports only tested premises; external side-effect atomicity and universal dependency closure are not inferred.
3. Unknown/inconsistent specifications and incomplete projections cannot be silently discharged by the argument.
4. The final algorithm is labeled executed composition only where the integrated witness supports it.

Record dependencies, exact code/data/model/tool versions, actual command logs, failures and claim limitations in the receipt. Expand this task into bounded follow-ups when discovery requires it; preserve its goal and evidence obligations.

## NS-024 Build the anonymous reproducibility bundle, official template, and accurate disclosures

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: neurosymbolic_supervision
- Depends on: NS-022
- Goal id: NS-SG7
- Parent goal: NS-G000
- Objective heap: papers/completion/neurosymbolic_supervision/paper.objectives.md
- Board namespace: vericodegen-2026-neurosymbolic_supervision
- Bundle: neurosymbolic_supervision/NS-SG7
- Parallel lane: neurosymbolic_supervision
- Outputs: papers/completion/neurosymbolic_supervision/release/README.md, papers/completion/neurosymbolic_supervision/release/manifest.json, papers/completion/neurosymbolic_supervision/release/reproduce.sh, papers/completion/neurosymbolic_supervision/release/supplement.zip, papers/completion/neurosymbolic_supervision/release/paper.pdf, papers/completion/neurosymbolic_supervision/audit/anonymity_report.md, papers/completion/neurosymbolic_supervision/audit/llm_use_disclosure.md, papers/completion/neurosymbolic_supervision/audit/author_attestations.md, papers/completion/neurosymbolic_supervision/audit/workshop_compliance.json, papers/completion/neurosymbolic_supervision/manuscript/checklist.tex, papers/completion/neurosymbolic_supervision/manuscript/neurips_2026_vericode.sty, papers/completion/neurosymbolic_supervision/submission/template_inputs.json, papers/completion/neurosymbolic_supervision/receipts/NS-024.json
- Predicted files: papers/completion/neurosymbolic_supervision/release/README.md, papers/completion/neurosymbolic_supervision/release/manifest.json, papers/completion/neurosymbolic_supervision/release/reproduce.sh, papers/completion/neurosymbolic_supervision/release/supplement.zip, papers/completion/neurosymbolic_supervision/release/paper.pdf, papers/completion/neurosymbolic_supervision/audit/anonymity_report.md, papers/completion/neurosymbolic_supervision/audit/llm_use_disclosure.md, papers/completion/neurosymbolic_supervision/audit/author_attestations.md, papers/completion/neurosymbolic_supervision/audit/workshop_compliance.json, papers/completion/neurosymbolic_supervision/manuscript/checklist.tex, papers/completion/neurosymbolic_supervision/manuscript/neurips_2026_vericode.sty, papers/completion/neurosymbolic_supervision/submission/template_inputs.json, papers/completion/neurosymbolic_supervision/receipts/NS-024.json, papers/completion/neurosymbolic_supervision/receipts/snapshots/NS-024/
- Allowed paths: 
- Resource class: cpu-medium
- Resource stage: execution
- Implementation timeout seconds: 7200
- Validation: python3 scripts/paper_supervisors.py verify-task --paper neurosymbolic_supervision --task NS-024
- Acceptance: A clean environment can install the frozen artifact and regenerate results/tables without author-private state, or limitations are explicit and scientifically acceptable.; Official checklist questions are present and honestly answered; the compilation placeholder and five disclosure placeholders are gone.; PDF metadata, author block, bibliography, URLs, source paths, logs, and supplement pass a documented double-blind audit.; Methods-essential LLM use is accurately described with actual models/versions/settings/independent checks; unresolved author-owned factual attestations are clearly listed.; PDF main text is 4–9 pages excluding references/appendices, PDF below 50 MB, supplement ZIP below 100 MB, subject to final live CFP verification.; The build loads the local research neurips_2026_vericode.sty unchanged, in its anonymous default mode; competition, single-blind, final, preprint, nonanonymous, and generic-style substitutions are absent.; The per-paper checklist copy contains all 16 official questions and preserved guidelines, with no answerTODO/justificationTODO fields and with actual Yes/No/N/A answers plus 1–2 sentence evidence-backed justifications; only its instruction block is removed.; The shared user templates are unmodified and their recorded input checksums match; the final anonymous author block may retain the Affiliation/Address/email strings generated by the official style.; Final build retains the workshop footer, anonymous behavior and review line numbers; source/PDF placeholder checks distinguish unanswered scientific fields from official style-generated anonymous text.
- Paper evidence: PDF p. 25, §K.1: five disclosure placeholders; PDF p. 25, §K.2 and p. 28 checklist TODOs; Workshop CFP: official 2026 template, double-blind artifacts, methodology-essential LLM disclosure; Local research template line 10 loads neurips_2026_vericode; line 461 includes checklist.tex. Research style lines 343–350 generate the anonymous Affiliation/Address/email block. Local checklist contains 16 official questions.
- Reuse candidates: papers/completion/neurosymbolic_supervision/manuscript/, papers/completion/neurosymbolic_supervision/artifacts/, papers/completion/neurosymbolic_supervision/benchmark/, papers/completion/neurosymbolic_supervision/analysis/, papers/neurips_2026_vericode_workshop.tex, papers/neurips_2026_vericode.sty, papers/checklist.tex
- Receipt: papers/completion/neurosymbolic_supervision/receipts/NS-024.json

Apply the supplied local research workshop template and checklist, then build an anonymous supplement containing source/locks/capabilities, protocol/data provenance/splits, model settings/prompts or allowed summaries, runner/checker commands, raw shareable receipts, analysis, and failure cases. Redact secrets/private traces/identifying paths without corrupting content identities; publishable manifests must reference the redacted release snapshot. Recover accurate author-confirmable model-use records for implementation/formalization/plans/patches/proofs/data/manuscript and remove unused roles. Document facts requiring author attestation separately; never infer consent or fabricate them. Prepare artifact hosting files for review without sending, publishing, or submitting. Build from the supplied local research shell papers/neurips_2026_vericode_workshop.tex and an unchanged copy of papers/neurips_2026_vericode.sty, using the supplied default \usepackage{neurips_2026_vericode} with no final, preprint, nonanonymous, or sglblindworkshop option. Do not use the competition/single-blind variant or the generic neurips_2026.sty. Copy papers/checklist.tex into this paper's manuscript directory, include it after references and optional appendices, remove only its BEGIN/END INSTRUCTIONS block, preserve the heading/questions/subheadings/guidelines, and replace all 16 \answerTODO{} and 16 \justificationTODO{} fields with actual evidence-backed \answerYes{}, \answerNo{}, or \answerNA{} and 1–2 sentence justifications. Do not edit the user's shared template/style/checklist originals or fabricate author-dependent answers. Pin input checksums. The style intentionally prints Anonymous Author(s), Affiliation, Address, and email: preserve this official anonymous block and exclude it from unresolved-placeholder failures.

Acceptance criteria:

1. A clean environment can install the frozen artifact and regenerate results/tables without author-private state, or limitations are explicit and scientifically acceptable.
2. Official checklist questions are present and honestly answered; the compilation placeholder and five disclosure placeholders are gone.
3. PDF metadata, author block, bibliography, URLs, source paths, logs, and supplement pass a documented double-blind audit.
4. Methods-essential LLM use is accurately described with actual models/versions/settings/independent checks; unresolved author-owned factual attestations are clearly listed.
5. PDF main text is 4–9 pages excluding references/appendices, PDF below 50 MB, supplement ZIP below 100 MB, subject to final live CFP verification.
6. The build loads the local research neurips_2026_vericode.sty unchanged, in its anonymous default mode; competition, single-blind, final, preprint, nonanonymous, and generic-style substitutions are absent.
7. The per-paper checklist copy contains all 16 official questions and preserved guidelines, with no answerTODO/justificationTODO fields and with actual Yes/No/N/A answers plus 1–2 sentence evidence-backed justifications; only its instruction block is removed.
8. The shared user templates are unmodified and their recorded input checksums match; the final anonymous author block may retain the Affiliation/Address/email strings generated by the official style.
9. Final build retains the workshop footer, anonymous behavior and review line numbers; source/PDF placeholder checks distinguish unanswered scientific fields from official style-generated anonymous text.

Record dependencies, exact code/data/model/tool versions, actual command logs, failures and claim limitations in the receipt. Expand this task into bounded follow-ups when discovery requires it; preserve its goal and evidence obligations.

## NS-025 Run an independent final readiness audit and produce the author-review handoff

- Status: todo
- Completion: auto
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: neurosymbolic_supervision
- Depends on: NS-024
- Goal id: NS-SG7
- Parent goal: NS-G000
- Objective heap: papers/completion/neurosymbolic_supervision/paper.objectives.md
- Board namespace: vericodegen-2026-neurosymbolic_supervision
- Bundle: neurosymbolic_supervision/NS-SG7
- Parallel lane: neurosymbolic_supervision
- Outputs: papers/completion/neurosymbolic_supervision/release/FINAL_REVIEW.md, papers/completion/neurosymbolic_supervision/release/checksums.sha256, papers/completion/neurosymbolic_supervision/audit/final_readiness.json, papers/completion/neurosymbolic_supervision/audit/final_placeholder_scan.json, papers/completion/neurosymbolic_supervision/receipts/NS-025.json
- Predicted files: papers/completion/neurosymbolic_supervision/release/FINAL_REVIEW.md, papers/completion/neurosymbolic_supervision/release/checksums.sha256, papers/completion/neurosymbolic_supervision/audit/final_readiness.json, papers/completion/neurosymbolic_supervision/audit/final_placeholder_scan.json, papers/completion/neurosymbolic_supervision/receipts/NS-025.json, papers/completion/neurosymbolic_supervision/receipts/snapshots/NS-025/
- Allowed paths: 
- Resource class: cpu-medium
- Resource stage: execution
- Implementation timeout seconds: 7200
- Validation: python3 scripts/paper_supervisors.py verify-task --paper neurosymbolic_supervision --task NS-025
- Acceptance: All predecessor task outcomes are backed by the declared deliverables and all required core acceptance obligations are satisfied or transparently reported as research limitations without false completion.; Fresh build/analysis reproduces final tables and no result, benchmark, checklist, or unintended author-detail placeholder remains in the reviewable manuscript; the official style-generated anonymous Affiliation/Address/email block is allowed.; Every final numerical/formal/operational claim traces to the frozen evidence ledger and no measured/estimated/unavailable categories are conflated.; Independent readiness report explicitly distinguishes submission-ready technical package from any outstanding author-owned attestations/portal action.; Handoff includes exact files, checksums, reproducibility commands, known limitations, live deadline note, and no implied external submission.
- Paper evidence: PDF p. 25, §K.2: final author actions; PDF p. 28: final experiment/source/artifact/disclosure checklist; Workshop CFP and live submission portal deadlines
- Reuse candidates: papers/completion/neurosymbolic_supervision/release/, papers/completion/neurosymbolic_supervision/audit/final_claim_evidence_matrix.json, papers/completion/neurosymbolic_supervision/tasks.json
- Receipt: papers/completion/neurosymbolic_supervision/receipts/NS-025.json

Independently rebuild the release, rerun analysis and targeted artifact checks, reconcile generated PDF tables to raw records, and search both source and extracted PDF for remaining placeholders and unsupported claims. Validate references, anonymous links or prepared hosting paths, page/size limits, checklist/disclosure answers, task evidence, and remaining author attestations. Confirm current official deadline/portal requirements. Produce a concrete ready-for-author-review package with any precise unresolved factual input rather than claiming submission or consent. Completion is scientific/readiness evidence, not an empty task queue; do not submit or publish automatically. Verify research-template input checksums, all 16 completed checklist answers/justifications, preserved official style/anonymous block and workshop footer. Exempt only style-generated anonymous Affiliation/Address/email text from the residual-placeholder scan; scientific/checklist placeholders remain failures.

Acceptance criteria:

1. All predecessor task outcomes are backed by the declared deliverables and all required core acceptance obligations are satisfied or transparently reported as research limitations without false completion.
2. Fresh build/analysis reproduces final tables and no result, benchmark, checklist, or unintended author-detail placeholder remains in the reviewable manuscript; the official style-generated anonymous Affiliation/Address/email block is allowed.
3. Every final numerical/formal/operational claim traces to the frozen evidence ledger and no measured/estimated/unavailable categories are conflated.
4. Independent readiness report explicitly distinguishes submission-ready technical package from any outstanding author-owned attestations/portal action.
5. Handoff includes exact files, checksums, reproducibility commands, known limitations, live deadline note, and no implied external submission.

Record dependencies, exact code/data/model/tool versions, actual command logs, failures and claim limitations in the receipt. Expand this task into bounded follow-ups when discovery requires it; preserve its goal and evidence obligations.
