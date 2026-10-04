# Compositional review recording readiness

Date: 2026-10-04. Status: source-only recorder implemented and readiness check completed; actual review and semantic label admission pending.

The [new adapter](../../external/ipfs_datasets/ipfs_datasets_py/logic/legal_ir/canonical_binding_review.py) and [file workflow](../../external/ipfs_datasets/ipfs_datasets_py/logic/legal_ir/canonical_binding_review_workflow.py) now accept the prepared 64-source review packet. This removes its schema incompatibility with the older review recorder. The new workflow records typed declarations and disagreements, without enabling any training or evaluation masks or treating declared names as authenticated reviewers.

## Recording contract

The adapter accepts only the pinned public blank packet and submitted copies. It validates exact source/context identities, the derived item IDs, closed instructions and blank annotation fields before recording submissions. It reuses the unchanged richer-review annotation and meaning-signature helpers; it never constructs an old private bundle or loads authored answers. The current context contract accepts only the exact empty `none_required` envelope. New context profiles require a separate version.

An actual reviewer may submit a nonempty subset of items or reorder them, preserving every input envelope. Partial fields and whole rule facets remain pending; explicit empty rule or qualifier lists retain their declared meanings. Duplicate payloads, item IDs or declared reviewer IDs for the same input are rejected. Ordered rules, repeated qualifiers and exact freeform scope determine mechanical agreement, excluding notes, names and timestamps. Differences remain recorded for external adjudication; no candidate or reference breaks a tie.

The [command line](../../external/ipfs_datasets/scripts/ops/legal_ir/record_binding_reviews.py) pins original file bytes separately from the adapter's canonical-content pin. It rejects duplicate JSON keys, nonfinite values, UTF16/32, BOM-prefixed JSON, symlinks, nonregular files, stale hashes and altered envelopes. The dictionary contract also bounds ordinary JSON, depth, node count and aggregate bytes. The workflow verifies dependency import paths and rechecks its five explicit owner/helper files and input bytes before writing fresh evidence. This is a partial dependency manifest. Outputs use a private directory with mode `0700` and files with mode `0600`.

## Executed readiness

The [machine report](binding-review-admission-01/report_private.json) records one execution of the real file workflow with an empty submission list. The [saved receipt](binding-review-admission-01/recording/receipt_private.json) and its public-validator recomputation agree exactly.

| Evidence | Observed result |
| --- | ---: |
| Exact source/context/input receipt joins | 64 |
| Pending items | 64 |
| Submitted payloads and completed declarations | 0 |
| Authenticated reviews and completed adjudications | 0 |
| Zero receipt mask values | 320 of 320 |
| Zero private organizer mask values | 320 of 320 |
| Preserved preceding file bindings | 483 |
| Model, provider, encoder, prover and fitting calls | 0 |

The wrapper checks the private organizer's 16 groups and proposed 32/32 TRAIN/DEV split separately. The actual recording API receives none of that metadata. The [neutral submission guide](binding-review-admission-01/recording/submission_guide.json) contains no source-specific answer, item/group identity or private split value. The original packet retains all 512 blank annotation cells. Hash preservation streams historical artifact bytes; those artifacts are not deserialized as candidate/reference inputs to the recorder.

A fresh child worker completes in 0.885 seconds wall and 0.332 seconds CPU. Its process peak is 26,140 KiB and Linux high-water memory is 27,340 KiB, under the declared 512 MiB worker cap. The durable journal contains 25 observations; launcher usage is recorded separately. No previous owner, test, packet, checkpoint or historical report is modified.

## Verification and remaining evidence

The final combined suite passes **224 tests in 3.36 seconds** across the new dictionary adapter and file workflow plus the existing richer annotation and command-line tests. Synthetic annotations are confined to tests; none enters the campaign's readiness run. The tests cover blank packets, partial declarations, exact ordered agreement, disagreements, integrity checks, strict file parsing, drift before publication, receipt replay and refusal to grant authority. Ruff passes seven new implementation, test, assay and validation files. Earlier fixture-path and expected-count assumptions in the new workflow tests were corrected before this final suite.

The [independent engineering audit](binding-review-admission-independent-audit-01/audit.json) checks saved inputs, joins, receipts and resource observations. The [root validation](binding-review-admission-validation-01/validation.json) binds the frozen outputs and new documentation, verifies local links and confirms the isolated decoder checkout remains clean. These checks validate recording behavior rather than source interpretation.

The [runbook](../../external/ipfs_datasets/docs/autoencoders/alignment_binding_review_recording.md) contains the usable readiness command, submission format and annotation requirements. For actual review, distribute the original public packet, its reviewer manifest and the neutral guide; keep organizer metadata and recording receipts private. No reviewer is contacted by this increment.

The [improvement plan](../../implementation_plan/docs/49-autoformalization-joint-embeddings-improvement-plan-2026-10-03.md) now marks schema-specific recording as implemented. All old 34 and new 64 review items still await independent interpretation. Authenticated provenance and adjudication must precede a separately versioned semantic label-admission contract; this recorder has no operation to enable masks. A disjoint natural-source corpus and independent fidelity measurement remain prerequisites for comparing binding objectives, learned representations and new conditioning arms. The three native encoder lanes and planned Leanstral roles retain their previous status.
