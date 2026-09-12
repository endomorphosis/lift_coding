# AF-021 hypothesis report

Prespecified claims from `evidence/claim_task_map.json` (AF-002/v1 freeze) and the AF-028/v1
reporting amendment. Statuses are `supported`, `unsupported`, `inconclusive`, or `unrun`.
Human-dependent hypotheses stay outside supported paper conclusions. Exploratory diagnostics
are labeled as such and are not represented as prespecified natural held-out tests.

- Analysis identity: `e33d2ea1febda9b666deafdbecf12f427dfccf3ee25cd7bd4140fd365796b189`
- CI method (prespecified, not computed on the unrun final-test population): 95% source-family/time-group cluster bootstrap, 10000 resamples; seed summaries separate.
- Seeds: [104729, 130363, 155921]
- Grouping: 20 source-family/time groups on 1913 final-test units
- Hypothesis statuses: {'unrun': 6, 'inconclusive': 1, 'supported': 1, 'unsupported': 1}

## Guardrails

- Independent human agreement and source-semantic fidelity are unmeasured, not zeros.
- Unrun and unavailable are not measured zeros.
- Teacher agreement, reconstruction, and prover success are not original-source gold.
- Zero observed false transfers is not generalized to universal soundness.
- Negative and inconclusive results are retained.
- Post-hoc test selection is not represented as prespecified.

## Prespecified primary claims

### C1: unrun

**Claim.** A source-grounded pipeline improves independently adjudicated source-facet fidelity on unseen natural source-family/time groups.

- Prespecified: True
- Experiments: A, B, C, D, E, T0, T2
- Controls: C_vs_B, D_vs_C, E_vs_D, T2_vs_T0
- Metrics: all-facet fidelity, coverage
- Human-dependent: True

Independently adjudicated source-facet fidelity was not collected. Final-test 1913 units remain no_run. Teacher/prover/reconstruction scores are not this claim.

*Narrowing rule (frozen):* Without independent labels and measured controls, retain only method description; teacher loss cannot support this claim.

### C2: unrun

**Claim.** Checked bridges and bounded learned advice improve useful native-checker proof coverage without increased false transfer.

- Prespecified: True
- Experiments: C, D, E
- Controls: D_vs_C, E_vs_D
- Metrics: native checked useful-proof coverage, false transfer rate, coverage, total cost
- Human-dependent: False

Native-checked useful-proof coverage on natural held-out sources is unavailable. Constructed Q1 transfer and solver-local encodings are not this claim. Zero observed false transfers on a finite constructed set is not universal soundness.

*Narrowing rule (frozen):* Solver-local or fixture outcomes cannot establish native proof coverage; unavailable proof routes remove this claim only.

### C3: unrun

**Claim.** Shared learning generalizes beyond sample memory.

- Prespecified: True
- Experiments: T0, T1, T2
- Controls: T2_vs_T0, T1_vs_T2
- Metrics: unseen all-facet fidelity, seen versus unseen diagnostic, coverage, cost
- Human-dependent: True

No held-out all-facet fidelity exists. Actual AF-029 T2 completed all three seeds. AF-029 packed_cpu updates are measured train/selection execution and do not support unseen source-family generalization.

*Narrowing rule (frozen):* T1 is a memorization diagnostic; no final-test/trained-checkpoint evidence means no gain claim.

### C4: unrun

**Claim.** Isolated trusted proof feedback improves routing/calibration without harming source fidelity.

- Prespecified: True
- Experiments: T2, T3
- Controls: T3_vs_T2
- Metrics: calibration, route value, protected-objective invariance, all-facet fidelity
- Human-dependent: True

Actual AF-029 T3 applied 256 compiler-structural feedback updates per seed. Earlier AF-012 isolation probes remain constructed history. Protected parameters were preserved, but source fidelity remains unmeasured.

*Narrowing rule (frozen):* A predictive head or checker-derived target without isolated update/checker evidence does not support this claim.

### C5: unrun

**Claim.** Promoted guidance improves a real compiler/realizer consumer on unseen material.

- Prespecified: True
- Experiments: T3, T4
- Controls: T4_vs_T3
- Metrics: consumer activation, unseen fidelity, native checked coverage, regressions
- Human-dependent: True

AF-013 reports T4 unactivated/unavailable with e_locked. Export identity is not applied learned guidance. Independent source fidelity is unmeasured.

*Narrowing rule (frozen):* An export or canary-only result without load receipt and locked-test evaluation does not support deployment improvement.

### C6: unrun

**Claim.** A bounded executable repair improves a sealed starting arm without test-selected patches.

- Prespecified: True
- Experiments: T4, T5
- Controls: T5_vs_sealed_T4
- Metrics: unseen fidelity, native checked coverage, regressions, repair cost
- Human-dependent: True

AF-014 records T5-NO-MEASURED-IMPROVEMENT as no_run. The accepted exception-scoping compiler contract on constructed witnesses is not held-out fidelity or native coverage.

*Narrowing rule (frozen):* A proposed or unexecuted patch is methods evidence only and does not complete T5.

### C7: inconclusive

**Claim.** Retrieval, premise selection, planning, and proof assistance have separable matched-budget utility.

- Prespecified: True
- Experiments: table13_retrieval, table13_premise, table13_planning, table13_assistance, T3, T4
- Controls: lexical_vector_graph, baseline_graph_selector, unguided_guided, hammer_leanstral, proof_heads_off_on, guidance_off_promoted
- Metrics: independent relevance, accepted-premise yield, replay/coverage, native acceptance, cost
- Human-dependent: False

AF-017/AF-018 provide constructed automatic-label/structural diagnostics only. Natural Table 13 cells remain unrun/unavailable. Hand-authored weights and proxy labels are disclosed; they were not represented as prespecified natural utility results.

*Narrowing rule (frozen):* Proxy labels, hand-authored selector weights, or declared-only routes stay qualified and cannot support utility claims.

## Prespecified learning diagnostics (not Table 11 fidelity)

### H-T1-memory-diagnostic: supported

**Claim.** Apparent T1 gain on seen sources is a sample-memory diagnostic rather than unseen generalization.

AF-011 T1 train vector-cosine values [0.9911507677701417, 0.7087377301225305, 0.9931928982847245, 0.6737862577372341, 0.9916045745511602, 0.7553396933029255] versus selection [0.41048516576800165, 0.6248541963978193, 0.46407742342545605] on mock:stable-sha256 embeddings. This supports the prespecified memorization diagnostic only. It does not fill Table 11 held-out fidelity and is claim_admissible=false.

This diagnostic is not a post-hoc substitute for held-out source-facet fidelity.

### H-T2-shared-learner: unsupported

**Claim.** Shared-parameter learning generalizes to unseen source-family/time groups.

AF-011 T2 update_counts=[0] with claim_admissible=False. Earlier no-update history is retained separately from the later successful native training. AF-029 packed_cpu parameter changes are not relabeled as this prespecified held-out test.

This diagnostic is not a post-hoc substitute for held-out source-facet fidelity.

## Per-family / facet / domain accounting

Final-test natural units by domain (all unrun for Tables 6/11/13 primary metrics):

- `cfr`: 993 units
- `guidance`: 7 units
- `mpep`: 738 units
- `uscode`: 175 units

Facets (propositions, modality, negation, actor/recipient, quantifiers, exceptions,
temporal interpretation, ambiguity, source spans, admissible assumptions) remain
unmeasured. Zero agreement is an inventory of missing records, not a reliability statistic.

## False transfer and abstention

- Table 6/11 false-transfer numerator: null (unrun/unavailable), denominator 1913.
- AF-016 selection false_transfer=true count: 0.
- AF-016 selection useful=true count: 0.
- AF-016 native_checked_proof count: 0.
- AF-016 selection statuses: {'A': {'unavailable': 15}, 'B': {'abstained': 4, 'measured': 11}, 'C': {'measured': 15}, 'D': {'unsupported': 15}, 'E': {'unavailable': 15}}.

Constructed Q1 records a guarded accepted transfer and an unguarded countermodel on a
finite witness. That is not compiler soundness and is not Table 6. Zero observed false
transfers there is not generalized to universal soundness.

## AF-029 training and failed attempts (carried, not double-counted)

AF-029 native training executed T0/T1/shared-only T2 and isolated T3 on train/selection
with MiniLM teacher targets. Failed encoder-preparation attempts 1--4 are retained with
their costs. Source fidelity remains null. These rows do not fill Table 11 held-out
fidelity or native-proof cells. AF-020 already accounts retained historical costs;
this analysis cites those totals and does not re-sum item rows into Table 6/11.

- AF-029 executed arms: ['T0', 'T1', 'T2', 'T3']
- AF-029 claim_admissible: False
- AF-020 measured elapsed across retained phases: 481.585523993
- Human-review table status: unmeasured
