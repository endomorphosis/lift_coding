# Autoformalization relation mask handoff preflight

Date: 2026-10-04. This extends AFI-04 and AFI-09a in the [implementation backlog](50-autoformalization-alignment-implementation-backlog-2026-10-04.md), following the [masked contrastive loss](55-autoformalization-masked-contrastive-relations-2026-10-04.md). The [comprehensive plan](49-autoformalization-joint-embeddings-improvement-plan-2026-10-03.md) remains the architecture and experiment roadmap for the 8D spaCy, 384D GTE-small, 768D multilingual GTE and optional Leanstral embedding lanes, the decoder and the broad 40-family prover pilot.

The next dependency is explicit: review declarations, signatures, formal derivations, source fidelity and pair supervision are separate evidence. A declaration recorder cannot authenticate a reviewer by accepting a name or a `verified` flag. A loss function cannot decide whether a pair is semantically positive. This slice makes the joins between those stages executable while keeping authentic admission unavailable.

## Current review boundary

Scoped inspection found no authentic human review submissions or selected review process in the existing campaign recordings and canonical evidence intake. The 64-item recording still has zero submissions; the canonical intake has an empty evidence package and no selected process. Matching hashes establish which declaration was submitted. They do not establish identity, independence, competence or meaning.

The existing [Profile G signature verifier](../../external/ipfs_datasets/ipfs_datasets_py/logic/profile_g.py) verifies Ed25519 signatures against resolver-selected key material. Its [service](../../external/ipfs_datasets/ipfs_datasets_py/mcp_server/profile_g_service.py) also supports injected authority/policy validators. Signature mathematics binds a signing key to bytes; human identity, review role and source fidelity need independently selected process evidence. The service's trusted-local bypass must not serve as the review admission gate. The generic [admissibility service](../../external/ipfs_datasets/ipfs_datasets_py/logic/admissibility/service.py) likewise relies on application-selected verification and supplies no authentic authority for this review packet.

Existing canonical interpretation and statement-scope owners cover bounded deontic views. The 40-family catalog does not extend those annotation schemas automatically. A family-specific interpretation/derivation adapter and its limits must be qualified before that family's labels can train an alignment or decoder model.

## Closed handoff contract

The new [handoff owner](../../external/ipfs_datasets/ipfs_datasets_py/logic/formalization/autoencoder/alignment_relation_mask_handoff.py) provides three standard-library interfaces:

- `compile_train_relation_masks(declaration, snapshot, policy, *, expected_bindings)` validates exact associations and produces a detached preflight receipt.
- `validate_train_relation_mask_handoff(receipt, declaration, snapshot, policy, *, expected_bindings)` checks a saved receipt by complete deterministic replay.
- `prepare_unavailable_relation_handoff(declaration, *, expected_declaration_bindings)` constructs the current unavailable-review snapshot and its externally selected bindings without I/O or fabricated review assertions.

The input declaration is the preceding complete TRAIN lane/manifest/pair ledger. Its four selected role bindings retain their original meaning. Separate external selections bind the complete sealed declaration, snapshot and policy. The snapshot also binds the selected declaration and policy so that review metadata cannot migrate silently across a new source generation, relation policy or semantic scope.

Each endpoint binds its exact TRAIN ID, source/context input hash and formal-view hash. Each ordered pair binds both endpoints in the complete TRAIN Cartesian order. The compiler preserves unavailable rows and every pair; it does not select a smaller bank to make coverage appear complete. Stale inputs, changed formal views, substituted pair order, missing or duplicate pairs and locally resealed replacements fail their joins or selected pins.

The policy binds a whole-source/formal-view scope and separate source/target family, semantic-profile and assumption declarations. These semantic profiles are distinct from the existing lane representation profile. Matching embedding dimensions, poolers or representation hashes do not establish a common interpretation. Compatibility here concerns equality of selected fixture declarations, not qualified runtime support for a family or profile. This version performs no family coercion; a missing or incompatible semantic scope cannot enable an objective pair.

The proposed pair meaning is direct compatibility between source row `i` and formal row `j`. It does not imply that author groups are equivalence classes, that formal digest equality establishes source fidelity, or that relations must be symmetric or transitively closed. This semantic-supervision objective is also distinct from the usefulness of a retrieved TRAIN demonstration. Those are separate experiment outcomes in the comprehensive plan.

## Two supported preflight modes

| Mode | Allowed input assertions | Objective matrices | Admitted matrices and fitting |
| --- | --- | --- | --- |
| `unavailable_verification/v1` | Complete bound TRAIN endpoints and unknown pairs, with unavailable fidelity and null review references. | Entirely false. | Entirely false; real fitting blocked. |
| `synthetic_engineering_only/v1` | Explicitly authored fixture fidelity, pair review and adjudication references. | Eligible fixture pairs can be true after exact joins and scope checks. | Entirely false; real fitting blocked. |

There is no supported authenticated-human mode in this version. Caller-supplied authentication flags and unsupported provenance are rejected. The compiler performs no signature verification, callback discovery, identity authentication, formal derivation, source review, model call or optimizer update. Hash-shaped fixture review references are structural test values, not review evidence.

Synthetic objective positives and permitted negatives are separate from admitted positives and permitted negatives. Fixture pairs require explicit relation selection and complete fixture review/adjudication references, compatible scope, available source-lane endpoint declarations, source fidelity for the left endpoint and formal fidelity for the right endpoint. Formal-vector values and model execution are not verified by this compiler. Unsupported or incomplete fixture pairs remain excluded. Unknowns enter neither objective matrix. The compiler infers no diagonal, negative, equivalence or reverse relation.

Readiness reports positive coverage for every source row and formal column, plus the permitted-negative separation signal. Missing positives or a batch with no negatives cannot be repaired by adding implicit pairs or dropping anchors. Every returned supervision mask remains zero, and `actual_fit_authorized` remains false even when the fixture objective is structurally ready. The loss primitive's caller still owns its numerical domain and future finite-gradient update checks.

## Saved actual-data preflight

The [preflight runner](../../artifacts/autoformalization-alignment-20261003/assay_relation_mask_handoff.py) consumes the pinned preceding declaration for 16 TRAIN rows. Its [saved assay](../../artifacts/autoformalization-alignment-20261003/relation-mask-handoff-01/assay.json) retains all 256 ordered pairs. The original 16 weak structural identities supply no authentic relation evidence: all 256 objective relations therefore remain unknown, and all objective and admitted matrices remain false. Original weak decoder masks and previous checkpoints remain unchanged.

This run reads bound source/input/formal-view digests rather than formal target bodies or query reference panels. It selects no process or synthetic fixture assertions for the actual TRAIN data. There is no numerical objective, Torch import, inference, optimizer update or new checkpoint in this preflight.

The [overall verification receipt](../../artifacts/autoformalization-alignment-20261003/relation-mask-handoff-01/verification.json) records 337 passing targeted tests: 61 new [handoff tests](../../external/ipfs_datasets/tests/unit/logic/formalization/autoencoder/test_alignment_relation_mask_handoff.py) and 276 existing declaration/lane regression checks. It records complete replay of the separately saved [compiler receipt](../../artifacts/autoformalization-alignment-20261003/relation-mask-handoff-01/validation.json), source pins, lint for four new files and rechecks of the preceding 224 bound files. Exclusive writes preserved the compiler receipt when the first overall verifier attempted to reuse its filename; the corrected verifier uses `verification.json`. Synthetic test coverage establishes structural behavior only. The previously documented legacy adapter-registry mismatch and standalone numerical-launcher ordering limitation remain preserved; this slice does not repair or qualify them.

## Requirements for the authentic path

The real admission path needs a separately selected organizer/process and trust registry. It must bind process ownership, stable reviewer identities, authorized roles, independence from source/candidate authors, exposed inputs and exact submitted generations. Signature verification can provide transport integrity within that process; it cannot replace those checks. Process attestations must not be accepted from a review package merely because they contain an authentication flag.

The next process adapter should use the following proposed records. These are requirements for a future real process, not records generated or authenticated by this slice.

| Record | Selected evidence and checks |
| --- | --- |
| Process registry | Immutable process/registry/policy generations, issuer, audience, validity and revocation snapshot. The application selects its trust anchor outside submitted packages. |
| Principal and key roster | Stable person/principal ID, public-key bytes and version, authorized roles/actions/family/profile scopes, enrollment evidence and key/principal status. Two keys for one person do not count as two independent reviewers. |
| Independence and exposure assessment | Exact assessed principal, policy generation, source/model-author relationships, assessor and evidence; exact source/context/candidate/reference artifacts exposed. Unknown or conflicting assessments stay explicit. |
| Detached attestation | Signer/key, process/registry/policy generation, audience/action, issuance/expiry/replay ID and complete subject hashes. Verify actual signatures against roster-selected keys; reject package-selected providers and authentication flags. |
| Fidelity and derivation decision | Exact whole source/context, interpretation, family/profile, formal-target bytes, assumptions, derivation, coverage and adjudication generation. Preserve omissions, ambiguity and alternatives. |
| Directed relation decision | Exact source `i` and formal target `j`, their generations, fidelity/derivation receipts, intended relation and supported rationale. A demonstration-usefulness decision remains separate. |

Report signature validity, enrollment, role authorization, assessed independence/exposure, fidelity admission and relation admission as separate outcomes. An assessed independence record binds its provenance; a signature alone cannot establish its substantive correctness. Reject stale generations, revoked or wrong-purpose keys, wrong audiences, repeated principals, altered annotations, partial coverage and unresolved adjudication. Offline replay reports its selected revocation snapshot rather than claiming current online status.

For each admitted interpretation, preserve ambiguity, alternatives, omitted clauses and unsupported meaning. A selected, faithful formal target needs a reviewed derivation tied to its exact family/profile/assumptions and whole source/context input. Proof evidence for a different statement cannot resolve a source-fidelity gap. Direct source/formal relation reviews must then bind the exact endpoints, intended positive/negative meaning, review and adjudication generation, and revision/supersession policy. Uncertain relations remain unknown.

Only after that separate authority exists should a new version produce admitted masks and an authenticated tensor handoff. Fit workers still need TRAIN-only provenance, objective-bound checkpoint identities, finite-gradient update gates, private reload checks and OS-enforced reference confinement. None of this preflight qualifies Leanstral hidden states as embeddings or establishes retrieval, autoformalization or proof improvements. The broader independently reviewed pilot remains the test of those claims.
