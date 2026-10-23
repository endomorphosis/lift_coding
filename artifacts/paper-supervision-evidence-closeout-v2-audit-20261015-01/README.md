# Proof-Carrying Neurosymbolic Supervision: evidence closeout

This directory is the bounded evidence audit for **Proof-Carrying Neurosymbolic Supervision: State, Reasoning, and Evidence Reuse**. It recovers existing observations and proposes evidence-supported manuscript changes. It does not report new benchmark, training, solver, grader or model executions.

The user authorized direct local inspection after the existing supervisor handoff was found unavailable. `paper-supervision-evidence-closeout-v2` remains an **unsubmitted objective**; this directory is a projection of evidence, not a new runtime authority. The supervisor, original reports, manuscript sources, services, acceptance thresholds and repository histories were not changed. Nothing was pushed or uploaded.

## Paper identity and working base

The supplied original PDF and v2 revision package were not recovered. The user authorized making a package. The declared working base is the exact-title **increment-016** snapshot, reconstructed in [the adjacent package](../paper-supervision-evidence-closeout-v2-reconstructed-20261015-01/README.md). Its 37-page PDF SHA256 is `51a72d60c7dcb23faa17918091fe172f6cbacf8f25df10e94d1b4071dce05ce7`; its abstract SHA256 is `666d0da1c0242cba4b6113be1ea0e76cc6ada16fe276cc0f03347dda4ae261b8`. These establish the selected bytes, **not identity with the unavailable supplied PDF**. An author decision on the revision base remains necessary.

The paper's architecture remains source-linked semantic state G(F), operational state O, durable evidence B, obligation-guided reasoning, authorized neural residuals, applicable test/proof reuse and accepted-state publication. Context reduction, avoided model calls and validation reuse have different evidence. The prompt → IntentIR → grounded CodebaseIR → SecurityIR/LegalIR/UI/UX joins → counterexample checks → separately authorized action chain remains part of the design. Which stages each trial exercised is recorded independently.

## Recovered evidence

The audit hashed **108 distinct inputs, 5,796,427 bytes**. Its 85 run-ledger rows have different units: **39 Terminal-Bench rows** (37 identified invoked trials, one invoked observation lacking its original trial ID, and one uninvoked slot) plus 46 historical event/case/control rows. They are not 85 independent benchmark experiments. There are 24 study groupings, 62 session-or-call records, 195 per-trial/domain observations and 18 separate encoder deployment/training descriptors.

- **T1:** the final original-receipt pair records 720,840 versus 445,333 tokens, both reward 1 and supervisor completion, with actual `decision_packet@2` delivery. Four native sessions reconcile without duplicate wrappers. The observed reduction is 38.22%; first-message bytes fall only 10.56%, and tools/cache trajectories differ. This is a native-input-supervisor comparison, not native Codex. The nine historical invoked attempts retain three missing-usage failures; 2,523,452 is only their known subtotal. Earlier native fallback and later failed/unaudited retrieval attempts remain separate.
- **T2:** native Codex 228,630, indexed 22,749, and fresh corrected no-index 282,802 all retain their own identities and reward 1. The earlier no-index failure and 359,845-token corrected success are retained. The indexed receipt supports a narrow Doctor guard contract, materialization and task completion; full static analysis, complete SecurityIR discharge and final accepted-root publication are not established.
- **T3/T4/X1:** unfavorable numerical observations remain visible. The later native/no-index/indexed totals are 113,883/358,492/333,973. Grok's reported 1,310,764/1,621,661/2,452,634 lack explicit usage completeness. Independently recovered Source384 receipts in the relevant indexed cohorts use zero target-training steps and unsupported predictions. They diagnose an unadapted path; they do not evaluate the intended qualified repository-adapted deployment.
- **Historical paper studies:** the 32-cell population has 9 useful completions and usage for 16 cells; the separate 24-cell pilot has 10 useful labels. Fourteen reuse cases contain two positive call-reuse admissions, both cold audited, with five separate positive timing pairs. The original 1/26 false reuse remains report-supported. Original development scorers admitted 5/6 crafted incorrect candidates; supplementary rescoring distinguishes 10 unique bodies from 14 records. Both Requests cohorts have zero complete trajectories. Simple retrieval/template controls and native proof limitations are retained.
- **Cross-IR/training:** no single qualified five-domain execution trace was recovered. Both final T1 Intent advisors failed open without checkpoints. T1 local code adaptation is distinct from Source384 and lacks held-out qualification. The separate Intent development run reports 75/75 authored holdouts and 0/3 weak-public holdouts, using an inherited 8D lexical branch, not demonstrated 384D deployment. Loading a checkpoint, indexing, adapting and independently qualifying it remain different events.

## Deliverables

| Concern | Files |
|---|---|
| Identities and provenance | `source_manifest.json`, `source_worktree_manifest.json`, `report_commit_manifest.json`, `runtime_manifest.json`, `artifacts.jsonl` |
| Studies, runs, counters and relationships | `studies.json`, `runs.jsonl`, `sessions.jsonl`, `evidence_graph.jsonl`, `claim_evidence_map.csv` |
| Results and contrary observations | [results.md](results.md), `results.csv`, `contradictions.md`, `failed_uninvoked_missing_observations.jsonl`, `aggregate_failures_and_preparation_inventory.json` |
| Per-study reconciliation | [T1](workstreams/t1_report.md), [T2/T3/T4/X1](workstreams/t2_t4_report.md), [historical studies](workstreams/historical_report.md) |
| Implemented versus exercised | `source_to_caller_to_claim.csv`, `cross_ir_implementation_matrix.csv`, `cross_ir_trace.jsonl`, `encoder_deployment_ledger.jsonl`, `logic_family_inventory.json` |
| Proofs, scorers, reuse and failure causes | `proof_scorer_reuse_audit.json`, [proof_scope.md](proof_scope.md), [failure_taxonomy.md](failure_taxonomy.md) |
| Reviewer closeout and remaining evidence | [reviewer_matrix.md](reviewer_matrix.md), [missing_evidence.md](missing_evidence.md), `missing_evidence.jsonl` |
| Next experiments, proposed only | [next_experiments.yaml](next_experiments.yaml); all approvals false |
| Manuscript changes, unapplied | [evidence_addendum.md](proposed_manuscript/evidence_addendum.md), `proposed_manuscript/changed_sentences.csv`, `proposed_manuscript/main.md.patch` |
| Format and anonymity | [build_page_anonymity_report.md](build_page_anonymity_report.md), `private/`, `anonymous/release_inventory.json` |
| Verification and review | `audit/numerical_audit.json`, `audit/native_usage_reconciliation.json`, `audit/integrity_report.json`, `review_historical.md`, `audit/final_projection_review.md` |

`null` means unavailable, not zero or false. Original receipt commitments, independently rehashed files, expected checks and actual recorded results stay separate. Source-present code is not proof of a historical caller. Current/reporting commits are not joined into an invented executed source forest. The partial run forests, module origins, timings and checkpoint details remain in each row's `source_observation` and the workstream ledgers.

## Reproduction levels and exact commands

Run from this directory. Python 3 and its standard library suffice. Output destinations must be new; scripts refuse overwrites. No dependency install or package-root import is needed.

```bash
python ../paper-supervision-evidence-closeout-v2-reconstructed-20261015-01/author_materials/verify_reported_numbers.py \
  --trials ../paper-supervision-evidence-closeout-v2-reconstructed-20261015-01/author_materials/reported_trials.jsonl \
  --audit-spec ../paper-supervision-evidence-closeout-v2-reconstructed-20261015-01/author_materials/numerical_audit.json \
  --output-dir /tmp/paper-closeout-transcribed-01
python assemble_audit.py --output /tmp/paper-closeout-reproduction-01
python reconcile_native_usage.py --output /tmp/paper-closeout-native-usage-01.json
python verify_audit.py --output /tmp/paper-closeout-integrity-01.json
```

The first command reruns the newly authored reconstruction audit; its original invocation and result are retained in the adjacent package's audit records. The missing supplied audit was not recovered. This command verifies transcribed aggregates only. `assemble_audit.py` freshly regenerates 69 arithmetic/count/schema checks and tables from the bounded projections. It needs the full private audit tree; the tiny anonymous CSV alone cannot reproduce all joins. The aggregate quantities can be recomputed without authenticating original runs.

`reconcile_native_usage.py` additionally requires the two exact original T1 receipts and the hash-reviewed native arithmetic module at their retained local paths. It executes that standalone standard-library module, selects each `supervisor.provider_invocations` entry once, excludes duplicate wrapper paths and checks exact agreement. It does not read rollouts or establish total pipeline accounting. `verify_audit.py` checks the original input hashes and audit file manifest; it performs no behavior/solver/model execution.

Raw-log authenticity, missing cumulative counters, complete runtime archive closure, unavailable theorem/axiom transcripts and missing original cell records require further explicitly bounded artifact recovery. New behavioral claims, builds, solvers, training and model experiments require the separate proposals and operator approval. No rate snapshot or settlement was recovered, so no dollar total is calculated. Overlapping clocks are never added; lease occupancy is not treated as CPU/GPU use.

## Stopping condition and author decisions

Existing evidence has been reconciled within the declared read bounds. The 27 remaining evidence gaps identify exact paths or fields, attempted routes and smallest remedies. The complete runtime archive (1.35 GB), 6.3 MB manifest and 2.24 MB Intent backend exceed this inspection's per-file bound; reported hashes are not fresh byte authentication. This is not a claim that unrecovered experiments never occurred.

The author must confirm the declared paper base and missing H1/D1–D6/R1/R2 label mapping, review the proposed sentences, and choose whether any narrowly specified additional evidence collection or experiment is warranted. The retained PDF has **10 main-text pages**, exceeding the requested nine; no new build or official-style qualification was run. The full audit contains private provenance and is not an anonymous supplement. Even anonymized exact counts can correlate with public runs.

The separate disk-capacity request remains constrained by the inspected storage geometry: no usable unallocated capacity was found on the existing device. No filesystem expansion, cleanup, reserve adjustment or admission-threshold change was performed as part of this audit.
