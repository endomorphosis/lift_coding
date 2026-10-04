# Autoformalization review evidence intake

Date: 2026-10-04. This implements the first diagnostic evidence boundary in the [implementation backlog](50-autoformalization-alignment-implementation-backlog-2026-10-04.md), using the existing source-only recorder. It checks declared evidence against the exact packet, original submissions and recording generation. Identity verification, independent semantic adjudication and label admission remain separate work.

The [broad pilot](../../artifacts/autoformalization-alignment-20261003/implementation-backlog-02/pilot-family-coverage.json) still covers 40 catalog families. This first adapter is deliberately scoped to the current canonical normative packet. Its seven-facet interpretation schema cannot represent every family, nested statement scope or nonempty context. The later scope and coverage work must supply the appropriate richer contracts before other pilot strata can use them.

## Implemented dictionary boundary

The [core owner](../../external/ipfs_datasets/ipfs_datasets_py/logic/legal_ir/canonical_label_evidence_intake.py) exports:

```python
validate_label_evidence_intake(
    packet,
    recording,
    package,
    *,
    expected_bindings,
    selected_process_binding,
)
```

`recording` is a closed object containing `receipt` and `reviewed_payloads`. The original payload list and each payload's item order are preserved. The unchanged [recorder validator](../../external/ipfs_datasets/ipfs_datasets_py/logic/legal_ir/canonical_binding_review.py) replays the complete receipt. A self-sealed receipt alone is insufficient because it does not retain each submitted payload's item order.

`expected_bindings` has exactly `packet`, `receipt`, `submissions`, `organizer`, `process` and `cohort`. Each scalar binding contains `content_sha256`, `file_sha256` and `file_bytes`; `submissions` is an ordered list of those bindings. Organizer/process/cohort bindings are null for empty readiness checks. A nonempty package requires their externally selected bindings and a separate process selection containing `process_id`, `organizer_id` and `content_sha256`.

The package uses `canonical-binding-label-evidence/v1`, with the fields specified in the [evidence design](../../artifacts/autoformalization-alignment-20261003/label_admission_contract_design.md). Its item references bind the exact item, submission index and submission digest, the complete annotation digest and its separate meaning signature. Complete annotations are required for referenced declarations. Changes to notes, identity or time still change the complete annotation binding even when the meaning signature remains unchanged.

Inline provenance records bind the selected process/organizer, declared principal and role, annotation, exposure, assessment time, method, rationale and limitations. Reviewer principals must match the referenced annotation's declared reviewer. Adjudicator provenance instead joins the declared adjudication principal and the declarations being assessed. A different name does not establish a different person or independence.

Interpretations retain rule and qualifier order, multiplicity, scope wording, declared coverage and unrepresented meaning. Their family is deontic in this version; profile labels remain unqualified declarations. Declared adjudication can reference known interpretation alternatives, with acceptance counts checked mechanically. Its presence does not mark adjudication completed.

Formal targets and derivations are unavailable in this version: `formal_target_binding` must be null and `derivation_refs` empty. `supersedes_package_sha256` must also be null until a separate externally pinned revision owner exists. These reserved fields cannot bypass later derivation or revision checks.

The returned receipt covers every original packet item in deterministic item-ID order, including omitted evidence. It retains declared evidence as detached values, pending verification/admission, all five masks at integer zero and all authority flags false. Reordered subsets are allowed; foreign, duplicate, partial or stale references reject the whole request. No model, encoder, prover or network operation belongs to this boundary.

## Digest and file semantics

| Binding | What it establishes here |
| --- | --- |
| Full canonical content digest | Exact ordinary JSON value. Whole annotations include notes, reviewer and time; the whole recording value includes its internal receipt checksum. |
| Package content checksum | Canonical package body excluding `content_sha256`. It detects changes but supplies no provenance or admission. |
| Existing meaning signature | Mechanical agreement on the retained meaning fields. It is not interchangeable with a full annotation digest. |
| File digest and byte count | External pins in the dictionary API; actual bytes are checked by the file workflow. Pretty-printed and compact files may have different file digests for the same value. |

The dictionary receipt explicitly reports `file_bindings_verified=false` and `metadata_content_verified=false`. The dictionary API cannot inspect files or establish that externally supplied process identifiers describe a file's contents. It checks packet, recording and submission values against supplied canonical pins.

## Pinned file workflow

The [file owner](../../external/ipfs_datasets/ipfs_datasets_py/logic/legal_ir/canonical_label_evidence_intake_workflow.py) and [CLI](../../external/ipfs_datasets/scripts/ops/legal_ir/intake_binding_label_evidence.py) take explicit file hashes for the public packet, inner recording report and evidence package. The inner report selects its exact receipt and original submissions. The outer campaign readiness report is not the recording input.

Nonempty evidence also requires explicitly pinned organizer, selected-process and cohort-policy files. The process selection file contains schema `canonical-label-review-process-selection/v1`, `process_id` and `organizer_id`. These are selected process declarations, not verification results. Organizer and cohort file contents are bound as ordinary JSON; this version supplies no semantic policy validator or human-provenance verifier.

The workflow reuses existing strict UTF8 readers and filesystem helpers. It rejects duplicate JSON keys, nonfinite values, unsafe file kinds, symlinks, incorrect pins and changed inputs. It enforces per-file and aggregate input bounds, checks the executing checkout and explicit implementation dependencies, and publishes only after validation into a fresh private directory. Its implementation manifest is deliberately partial, not a complete dependency or execution attestation.

The outer report can establish observed local file integrity and a consistent selected-process declaration. It preserves the core receipt's narrower flags and cannot promote reviewer authenticity, source fidelity, adjudication, semantic gold or training masks. Older generations are preserved.

## Verification and next work

Functional evidence and the saved empty-packet replay are recorded in the [validation receipt](../../artifacts/autoformalization-alignment-20261003/label-evidence-intake-01/validation.json). Test declarations are synthetic; the real run supplies an empty evidence package and selects no human-review process.

The targeted suite passed 205 tests across the new core/workflow/CLI and the unchanged recorder core/workflow. Ruff passed for the five new implementation and test files. The real CLI run preserved all 64 pending items and 320 zero per-item mask values, with no evidence items, authenticated reviews or admitted targets. This completes the diagnostic intake portion of AFI-04; its separate semantic label-admission gate remains unimplemented.

The next bounded changes are the richer scope/coverage payload, representation identity boundary and separated fit/rank/score interfaces. Broad source acquisition and real semantic reviews can proceed independently once their process and cohort policy are selected. This intake supplies declaration integrity for that work; it does not authorize fitting on the pending canonical labels.
