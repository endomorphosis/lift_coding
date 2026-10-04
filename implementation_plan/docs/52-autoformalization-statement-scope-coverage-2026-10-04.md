# Autoformalization statement scope and coverage

Date: 2026-10-04. This implements the declaration transport and compatibility diagnostics in AFI-07a of the [implementation backlog](50-autoformalization-alignment-implementation-backlog-2026-10-04.md). The [comprehensive improvement plan](49-autoformalization-joint-embeddings-improvement-plan-2026-10-03.md) remains the architecture and experiment plan. The preceding [review evidence intake](51-autoformalization-review-evidence-intake-2026-10-04.md) remains a separate boundary.

[ProofBridge v3](https://arxiv.org/html/2510.15681v3) motivates joint retrieval, generation and verifier feedback. Extending that workflow to this system requires retaining the statement being assessed before retrieval or proof repair can be credited with preserving it. This scope representation is our engineering extension; it supplies no new paper result or measured semantic improvement.

The first declared profile is deontic and normative. The broad pilot still covers [40 catalog families](../../artifacts/autoformalization-alignment-20261003/implementation-backlog-02/pilot-family-coverage.json). Other families require their own typed representations, assumptions and adapters. This implementation does not project those families into normative facets.

## Occurrences and attachment

The new [scope owner](../../external/ipfs_datasets/ipfs_datasets_py/logic/legal_ir/canonical_statement_scope.py) exports:

```python
validate_scope_declaration(request, declaration, *, expected_input_sha256)
assess_flat_profile_compatibility(declaration, *, byte_output_cap=4096)
```

Schema `canonical-normative-scope-declaration/v1`, family `deontic` and profile `normative-occurrence-scope/v1` identify an ordinary JSON declaration. Its closed fields are `schema`, `family`, `profile`, `input`, `input_sha256`, `occurrences`, `rules`, `statement_structure`, `binders`, `coverage`, `unresolved` and `content_sha256`.

The input retains exact `source_text` and a context object with `role`, `text`, empty `bindings` and the text's UTF8 SHA256. Roles are `none_required`, `declared_context` and `required_unavailable`. The full input digest uses the existing packet recipe: SHA256 of sorted compact UTF8 JSON containing source and context. The caller supplies the expected digest separately. Exact source/context strings and offsets are never normalized.

An occurrence has a unique ID, facet, opaque canonical symbol and exact anchor. Anchors contain `origin`, `start`, `end`, `text` and `offset_unit=unicode_character_half_open`. They distinguish source from supplied context and validate the exact literal slice. An occurrence may be referenced more than once; distinct IDs may retain repeated symbols and overlapping spans. Neither overlapping spans nor equal strings establish equal meanings.

Each ordered rule retains a rule ID, four core occurrence references and three qualifier expressions. An absent object is explicitly null. Qualifier expressions support leaves, ordered `all` and `any` children, and `not`; operator anchors are retained when supplied. Absent operator anchors stay null. Statement expressions retain a rule reference, ordered `all` or `any`, or a shared qualifier attachment around a statement subtree. Every rule must occur exactly once in that structure. Rule arrays and qualifier arrays retain order and multiplicity.

An inert binder records its ID, declared quantifier, variable/domain occurrences, attachment path and bound occurrence IDs. All bound uses must lie inside that attachment. Reusing a bound occurrence outside it rejects the declaration. The validator checks these associations, not variable substitution, term typing, domain semantics or capture avoidance. A future typed binder contract must establish those properties before proof or semantic use.

Coverage segments retain exact spans, dispositions, rule/occurrence associations and reasons. Cited occurrences must be physically contained in the same input origin. Represented segments require an association. Declared complete literal coverage must cover every source and context character without a gap, have no unresolved records or unsupported segments, and have no required unavailable context. These are checks on a declaration. They do not establish that punctuation, omitted obligations or ambiguous phrases have been interpreted correctly. Partial and unassessed coverage remain explicit.

The JSON payload is bounded to 65,536 UTF8 bytes, depth 20 and 25,000 JSON nodes, with at most 512 occurrences, 32 rules, 32 binders and 1,024 expression nodes. Expression depth is at most six; source and context each have a 16,384-character limit. Oversized values reject without truncation.

## Legacy compatibility

The assessment validates the embedded declaration and reports transport gaps per path for two unchanged owners: [canonical round trip IR](../../external/ipfs_datasets/ipfs_datasets_py/logic/legal_ir/canonical_contracts.py) and [byte proposal v1](../../external/ipfs_datasets/ipfs_datasets_py/logic/legal_ir/canonical_byte_codec.py).

| Construct | Declaration behavior | Legacy diagnostic |
| --- | --- | --- |
| Repeated qualifiers or a different qualifier order | Retained exactly. | Sorting or deduplication requires an unapproved normalization. |
| Ordered multiple rules | Retained exactly. | Canonical IR may reorder them; byte proposals require one rule. Duplicate rules are retained by the canonical owner. |
| Nested qualifiers, negation, changed facet connectives or statement disjunction | Retained explicitly. | Unavailable in the flat profiles. |
| Shared qualifier attachment | Retained around its subtree. | Unavailable; it is not distributed into independent rules. |
| Binder, domain or supplied context | Retained with declared associations. | Unavailable until an appropriate qualified transport and semantic contract exist. |
| Occurrence IDs, coverage and operator anchors | Retained in the scope payload. | Require the scope sidecar; legacy facets alone are insufficient. |
| Exact byte capacity | Checked through the existing byte owner when structural premises hold. | Oversized complete wires or configured output caps are unavailable. |

Qualifiers in the byte profile retain its existing operators: conditions `all`, exceptions `any`, temporal `all`. The diagnostic does not approve commutativity or idempotence. A sorting difference is not a proved logical negative, and a structurally identical declaration is not verified source meaning.

When structural conditions permit, the assessment constructs a transient private candidate for the unchanged byte owner's capacity inspection. It checks complete wire size and the configured BOS/content/EOS budget. It returns counts and diagnostics, with `lowered_ir=null`; no candidate is written, approved or admitted as a target. Partial or unassessed coverage still blocks compatibility even if the byte capacity fits.

Profile statuses are `unavailable`, `normalization_required_unapproved` and `flat_facets_fit_with_scope_sidecar`. The last describes facet transport under the checked constraints. Every profile still reports `standalone_scope_roundtrip_lossless=false` and `complete_legacy_encoding_qualified=false`. The caller must retain the richer payload. The assessment's embedded input hash is self-binding; received values first require validation against an externally expected input digest.

## Bridge carrier and digest semantics

The [bridge adapter](../../external/ipfs_datasets/ipfs_datasets_py/logic/legal_ir/canonical_statement_scope_bridge.py) exports `prepare_scope_bridge_view` and `validate_scope_bridge_view`, both requiring the source/context input and externally expected digest. It uses the unchanged `BridgeView` with name `statement_scope_v1`, kind `FAMILY_EXTENSION`, family `deontic` and the scope schema ID. Its payload is the exact declaration.

The complete serialized view, including its wrapper, must fit 65,536 bytes and depth 20. Thus a declaration at its own upper limit may not fit the carrier. The adapter rejects that case. It checks the existing payload CID and exact serialized replay; it supplies no native domain projection. A typed bridge can retain the view with an explicitly unsupported domain slice, as exercised by the bridge tests.

The declaration checksum seals the complete declaration body excluding its own `content_sha256`. The validation receipt copies the declaration separately and seals its summary excluding `declaration` and `content_sha256`; that summary includes the declaration checksum and the named checksum scope. Assessment and bridge receipts seal their complete summaries excluding their own checksum. These bindings establish data integrity, not authorship, human review or logical truth.

All receipts retain five integer-zero masks, pending verification/admission where applicable, false source-fidelity and authority flags, false normalization/lowering authorization, and zero model/prover calls. No existing intake interpretation is promoted or automatically converted into this profile. A separate reviewed interpretation-to-scope adapter remains necessary.

## Saved candidate replay and verification

The [saved candidate assay](../../artifacts/autoformalization-alignment-20261003/statement-scope-01/saved-candidate-assay.json), produced by the [persistent assay script](../../artifacts/autoformalization-alignment-20261003/assay_statement_scope.py), binds one previously saved source-only decoder generation, its separate request file and the current 64-item packet. It executes no decoder, encoder, optimizer or prover.

Of the historical 34 requests, 17 have complete saved proposals. Their exact leaves become unaccepted scope declarations, with inferred extra scope absent and coverage explicitly unassessed. All 17 retain exact payloads and CIDs through bridge serialization; their existing byte wires require 534–701 framed tokens and fit the configured 4,096 cap. Both legacy compatibility results remain unavailable for every declaration because coverage is unassessed. The other 17 requests retain their original blocked, clarification, encoding-unavailable or anchor-abstained outcomes.

There are zero exact source/context input joins to the newer 64-item review packet. Its annotation fields remain blank. The historical assay supplies no new pilot candidates, reviewed labels or gold targets. The 17 declarations retain 85 logical per-item mask values at zero.

The [validation receipt](../../artifacts/autoformalization-alignment-20261003/statement-scope-01/validation.json) binds the current implementation, assay, document and targeted test evidence, and rechecks the prior intake generation's selected file bindings. The [persistent validator](../../artifacts/autoformalization-alignment-20261003/validate_statement_scope.py) independently reconstructs candidate declarations and replays validation, compatibility and bridge round trips. Its dependency manifest remains partial; it does not rerun the earlier 554-file chain or authenticate historical predictions.

Targeted tests exercise source/context tampering, Unicode spans, repetition and ordering, nested and shared attachment, binder reuse across scope boundaries, coverage gaps, closed-schema and resource bounds, exact carrier limits, byte capacity, and unchanged legacy contracts. All test declarations are authored engineering fixtures. Test success and transport replay supply no independently measured statement fidelity.

All 115 new scope and carrier checks passed. The combined run passed 353 checks and exposed one existing registry snapshot mismatch: `test_existing_adapter_registry_is_composed_without_new_families` expects six bridge types, while the current manifest includes `ui_ux_ir_formalization` as a seventh. It fails independently when the scope suites are absent. Ruff passed all six new implementation, test and validation files. The [separate failure evidence](../../artifacts/autoformalization-alignment-20261003/statement-scope-01/independent-legacy-failure.txt) preserves that result. The registry and test are unchanged; the validation receipt reports this failure explicitly and does not claim a completely passing legacy suite.

## Next boundaries

The independent 8D spaCy, 384D GTE-small and 768D Alibaba multilingual GTE lanes remain separate. Their retained decoder checkouts and checkpoints remain the baseline. Leanstral keeps its generation/repair role; its optional final-hidden-layer embedding role still requires the runtime, pooling and batch-consistency qualification described in the comprehensive plan.

AFI-07a now has declaration preservation and compatibility diagnostics for this normative profile. Approved semantic normalization, executable richer lowering, typed binder semantics, reviewed interpretation adapters and other family profiles remain separate work. The next implementation slice is the representation identity boundary and separated fit/rank/score interfaces. Strong semantic, contrastive, proof and fidelity-evaluation training still depend on independently admitted data.
