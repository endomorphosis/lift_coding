# AF-002: frozen research protocol

**Protocol version:** `AF-002/v1`, frozen 2026-09-11 UTC before any AF-002 outcome inspection. **Execution state:** no A–E or T0–T5 condition has run. This is a prespecification, not an empirical result or submission decision.

## Questions and claim boundary

The primary question is whether compiler-guided shared representations improve independently judged **source-facet fidelity** and **useful native-checker proof coverage**, per total cost, on unseen source-family/time groups. Embedding MSE/cosine, family/view cross-entropy, and teacher/checker self-consistency are secondary diagnostics, never semantic gold.

| Family | Conditions | Question | Primary comparisons |
| --- | --- | --- | --- |
| Pipeline | A–E | Which source-to-proof pipeline is useful under a matched envelope? | E–D, D–C, C–B, B–A where available |
| Learning/transfer | T0–T5 | Do learning, feedback, consumed guidance, and repair add value? | T2–T0, T3–T2, T4–T3, T5–sealed T4 |

T1 is a memorization diagnostic: seen-source reconstruction and unseen-source inference are always separate. The two families are never silently merged.

## Frozen population, test access, and analysis

AF-004/AF-005 must first create content-hashed corpus/split/teacher manifests and independent candidate-blind facet annotations. Until then populations and teachers are unavailable, not zero-sized. Source derivatives, paraphrases, translations, adjacent sections, and views remain in one source-family/time group. Minimal pairs, natural documents/code/traces, and extracted media (only after a measured route) are separately reported.

The final-test lock prohibits its source IDs, labels, maps, candidate outputs, and outcomes from training, teacher fitting, prompt/hyperparameter/threshold/grammar selection, canary admission, patch selection, retrieval tuning, or manual inspection. Only a sealed harness may evaluate it after checkpoint/configuration/patch lock; it writes append-only records. The planned full-route minimum is 100 independently adjudicated natural final-test source units from at least 20 source-family/time groups. This is a precision/heterogeneity floor, not an asserted corpus count.

Learned arms use seeds 104729, 130363, and 155921. Deterministic arms replay three times only to detect nondeterminism. Report 95% source-family/time-group cluster-bootstrap intervals (10,000 resamples), seed-level summaries, all eligible denominator statuses, and negative/inconclusive results. Primary metrics are adjudicated all-facet fidelity, native-checker accepted useful-proof coverage, false-transfer rate, coverage, and total CPU/GPU/provider/human-review cost. Parse/elaboration, abstention, unsupported, unavailable, timeout, countermodel, and checker class remain separate.

## Common controls and resources

Matched comparisons use the same frozen task IDs, vocabulary, logical profile, independent labels, checker version, final-test lock, and per-item limits. The planned envelope is 3 seeds × 100 natural units per learned arm, 30 minutes per seed, 10 minutes search/validation per item, 16 GiB RAM, and zero unrecorded provider calls. One shared GPU/model-service slot may be used only after AF-003 preflight and scheduler reservation. Current availability of GPU, native checker, external model service, independent annotation, and teachers is **unavailable pending AF-003/AF-004/AF-005**; no availability is claimed.

The machine-readable plan supplies every A–E/T0–T5 input, teacher availability, checker, budget, metrics, and control. Budget exhaustion is `partial` or `unrun`: retain attempts and cost, narrow only affected claims, and never convert it to zero, success, or full-goal completion.

## Completion and deviations

A condition is `measured`, `partial`, `unrun`, `unavailable`, or `unsupported`; only retained raw per-item records with pinned identities, command log, and stated checker receipt are measured evidence. Full empirical completion requires explicit statuses for A–E/T0–T5 and admissible evidence for every retained empirical claim.

The permitted fallback is a methods/protocol artifact: retain architecture and conformance boundaries, label all empirical claims unmeasured, and omit performance, coverage, training-gain, activation, and deployment claims. It requires author choice and does not mark any run executed or the full empirical objective complete. A scope change must be versioned before affected outcome inspection, name affected claims, and preserve the final-test lock; post-outcome changes are exploratory only.

No submission, OpenReview upload, public release, or author sign-off is authorized by this protocol.
