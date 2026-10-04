# Source-symbol consistency and compositional review preparation

Date: 2026-10-04. Status: opt-in static checker implemented; saved-candidate audit completed; independent semantic review pending.

The new [source-symbol checker](../../external/ipfs_datasets/ipfs_datasets_py/logic/legal_ir/canonical_symbol_bindings.py) catches a concrete failure of the preceding learned-anchor baseline: a candidate copies the exact coordinates of “retain” and “the filing” but assigns the canonical symbols `notify` and `applicant`. A correct span can carry an incorrect interpretation. This increment adds a limited consistency check and prepares broader human review; it does not establish generalization or semantic accuracy.

## Implemented contract

`fit_profile` aggregates facet/literal-to-symbol observations from the 16 existing weak TRAIN proposals, producing 20 observed aliases from 124 anchors across four groups. The profile records its TRAIN manifest and content checksum. Its labels originate in the previously exposed grammar and are not independent gold. The caller must enforce TRAIN membership; the checker cannot authenticate a cohort's split from its supplied records alone.

`assess_bindings` first validates the complete anchored proposal against the exact source, then checks each leaf against the frozen profile. Literal normalization only casefolds and collapses Unicode whitespace. Punctuation, articles and other lexical differences remain significant. Recognized single-alias contradictions produce `binding_inconsistent`; unknown or colliding aliases remain `binding_unassessed`; agreement produces `binding_consistent`. The receipt binds the source, candidate and profile. It constructs no corrected answer and grants no fidelity, proof or acceptance authority.

The optional filtering policy withholds recognized contradictions and retains other candidates for unqualified review. This does not check unanchored source coverage, omitted qualifiers, connective scope, binders, domains or context interpretation. A mistaken TRAIN correspondence can pass, as can a candidate omitting meaningful source text. Those limits are covered by focused tests. The new owner remains opt-in; previous generators and saved candidate files retain their bytes.

## Saved-candidate assay

The [completed static report](symbol-binding-recovery-02/report.json) applies the frozen profile to 12 saved primary receipts covering all 34 requests, plus three matching private repeat receipts. These are repeated candidate slots from an exposed development panel, not independent examples.

| Scope | Receipt slots | Complete candidates | Consistent | Inconsistent | Unavailable |
| --- | ---: | ---: | ---: | ---: | ---: |
| Primary | 408 | 49 | 48 | 1 | 359 |
| Private repeats | 102 | 49 | 48 | 1 | 53 |

The primary complete candidates contain 379 anchored leaves. Two recognized alias contradictions occur in the same seed1729 DEV candidate: `retain → notify` and `the filing → applicant`. The new filter withholds that one candidate and leaves 48 TRAIN candidates available for unqualified review. All three private repeats match exactly. Candidates without a full anchor contract remain unavailable; no missing anchors or negative targets are invented. Neither the 48 agreements nor the withheld case measures an independent false-acceptance rate.

The original attempt completed one deterministic TRAIN profile aggregation, then stopped at its 512 MiB resource guard before candidate-body reads. Its peak and underlying cause were not recorded. The first recovery stopped before input reads: process `ru_maxrss` reported 1,719,700 KiB while Linux current RSS and high-water memory both reported 18,736 KiB. The cause of this startup discrepancy is unestablished. Both attempts and all partial files remain preserved.

A fresh child worker reused the frozen profile and completed in 0.836 seconds wall and 0.441 seconds CPU. Its process peak was 30,260 KiB and Linux high-water memory was 30,760 KiB, under the unchanged 512 MiB worker cap; the launcher's distinct counter is recorded separately. The durable journal contains 111 observations. Recovery performs zero profile fitting, candidate redecoding, model, encoder, optimizer or prover calls. The root validator separately reaggregates the profile and recomputes receipts using standard-library code.

The [provenance clarification](symbol-binding-recovery-02/provenance_scope_addendum.json) records that a prior validation JSON container includes one historical posthoc weak DEV reference rule and was deserialized for file-binding metadata. That rule was not supplied to profile fitting, assessment or withholding. The report's false reference-access fields describe algorithmic query-reference use; they do not assert that historical metadata containers contained no reference values. The profile was frozen before this parse. The counterexample was already exposed, so this is a static policy assay rather than a blind quality study.

## New review packet

The [candidate-blind reviewer payload](binding-review-packet-01/reviewer_items.json) contains 64 new authored statements, organized privately into 16 source groups with four variants each. The variants combine actors, action/object pairs, modalities, multiple conditions, exceptions and deadlines. Group assignment precedes derivatives; the private draft split proposes 32 TRAIN and 32 DEV items. Reviewers receive only source/context identities and eight blank annotation fields per item: all 512 cells remain blank. They receive no candidate, expected IR, split or group assignment.

The [packet preparation report](binding-review-packet-01/report.json) verifies zero exact-text overlap with the old 34 sources. These controlled templates still reuse exposed components and are not a natural-source corpus or sealed confirmation test. They create no semantic gold or equivalence labels; some variants intentionally express different meanings. All fit and evaluation masks remain zero. Independent reviewers, disagreement adjudication and a separately versioned admission adapter are still required: the existing review adapter does not accept this new schema. No reviewer has been contacted or identity authenticated. The old 34 and new 64 items all await review.

## Validation and resulting priorities

The [independent engineering audit](symbol-binding-independent-audit-01/audit.json) checks 480 file bindings, all 510 row joins, 98 complete-candidate assessments and private-repeat parity. Its [scope addendum](symbol-binding-independent-audit-01/provenance_scope_audit_addendum.json) independently confirms the historical metadata exposure. This is independent implementation review, not independent source interpretation.

The combined eight-file contract suite passes **613 tests in 6.03 seconds** with explicit CPU isolation. An earlier unisolated attempt passed 599 tests and encountered 14 fixture setup errors when Torch's optimizer health check attempted a CUDA allocation; the CPU-isolated rerun passed without modifying the old owners or tests. Ruff passes the seven new implementation, test and assay/preparation/validation files. The frozen independent audit runner is outside that Ruff result. The [root validation](symbol-binding-validation-01/validation.json) binds this report and the updated plan, checks local links, preserves the preceding 444 checked bindings and confirms the isolated decoder checkout remains clean.

The [comprehensive improvement plan](../../implementation_plan/docs/49-autoformalization-joint-embeddings-improvement-plan-2026-10-03.md) now makes the next evidence requirements explicit: obtain independent reviews and admit their labels; collect disjoint natural sources; compare binding losses and source-grounded symbol inventories on novel compositions; then test separate 8D, 384D and native multilingual 768D conditioning under matched controls. Keep raw retrieval baselines, distinguish aliases from full semantic gates, and evaluate Leanstral generation/repair and pooled hidden embeddings separately. No checkpoint or runtime lane is promoted by this increment.
