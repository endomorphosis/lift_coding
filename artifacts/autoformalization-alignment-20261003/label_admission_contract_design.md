# Semantic label admission evidence contract

Date: 2026-10-04. Design only; no reviews, verification, adjudication, labels or mask changes.

## Existing boundary

`legal_review_admission.validate_submission` checks bytes, source slices, declared roles, attachments and decisions. Its `evidence_receipt` is nonempty text; identity, independence, authenticity, semantic correctness and admission remain false. The recorders authenticate no person. Targeted legal/review searches found no verifier for this packet. Signatures bind keys; proof attestation preserves prior authority. Neither establishes meaning.

Use a trusted organizer/research process selected outside submitted data. Documented contact and relationship checks can establish review provenance; signatures are optional transport integrity. A package cannot choose its own verifier or assert `verified=True`. Authenticated agreement still does not prove meaning.

## Proposed closed intake

Propose `validate_label_evidence_intake(packet, recording, package, *, expected_bindings, selected_process_binding)`: bound diagnostic evidence, zero masks. Verification and admission remain separate, unavailable operations. Require strict finite UTF8 JSON, duplicate-key rejection, recording bounds, closed objects and detached replay. Bind file SHA, canonical-content SHA and bytes separately.

| Record | Exact fields |
| --- | --- |
| Package `canonical-binding-label-evidence/v1` | `schema`, `packet_binding`, `recording_binding`, `organizer_binding`, `review_process_binding`, `cohort_policy_binding`, `supersedes_package_sha256`, `items`, `content_sha256` |
| Item | `item_id`, `source_sha256`, `input_sha256`, `declaration_refs`, `provenance_refs`, `interpretations`, `adjudication_ref` |
| Declaration reference | `submission_binding`, `item_id`, `annotation_content_sha256`, `meaning_signature_sha256` |
| Organizer provenance receipt | `process_id`, `responsible_organizer`, `principal_id`, `role`, `identity_method`, `author_model_relationship`, `independence_assessment`, `inputs_exposed`, `annotation_binding`, `assessed_at_utc`, `rationale`, `limitations` |
| Interpretation | `interpretation_id`, `family`, `profile`, `ordered_rules`, `qualifier_scope`, `coverage_assessment`, `unrepresented_meaning`, `formal_target_binding`, `derivation_refs` |
| Adjudication | `principal_id`, `declaration_refs`, `interpretation_refs`, `decision`, `accepted_interpretation_ids`, `unresolved_scope`, `rationale`, `adjudicated_at_utc`, `provenance_ref` |

Type and bound every field. Provenance states who reviewed, how identity was established, relationships to authors, exposed inputs and exact annotation. Bind the whole annotation; meaning signatures remain mechanical. Different names do not establish different people. Two independent meaning/formal reviewers plus a distinct adjudicator are a proposed pilot policy; the legacy legal profile separately requires its own roles.

## Decisions and use

Preserve rule order, qualifier multiplicity/attachment and scope. Coverage explicitly addresses omitted clauses, connectives, negation, binders, timing and representation loss. Exact spans or flat facets cannot establish those meanings. A formal target requires a separate reviewed derivation and remains null until available. Extra context requires a new input/profile, never altered assumptions in this frozen empty-context packet.

Decisions: `accept_unique`, `accept_alternatives`, `no_normative_rule`, `needs_context`, `unsupported`, `abstain`, `reject`, `unresolved`. Alternatives stay a set, not an arbitrary single target. Lossy/uncertain cases get no invented formula; explicit absence differs from unanswered fields. New interpretations require reviewed generations; revisions supersede without overwriting. Candidate-aware corrections stay exposed repair supervision.

Future semantic-fit eligibility requires authentic provenance, supported adjudication and complete representation. Contrastive use also needs reviewed equivalence/non-equivalence; proof supervision needs separate actual proof evidence for the exact faithful statement. No production acceptance follows. All five current masks stay zero.

## Cohort and failures

Pin the 16-group provisional 32/32 TRAIN/DEV policy before examining labels; keep four variants together. The 64 authored sources reuse exposed components and are not natural-source or sealed-test evidence. Only TRAIN labels may fit models, aliases, vocabularies, preprocessing or target caches. Durable target-free inference precedes reference scoring; DEV selection needs untouched confirmation.

Fail closed on altered bindings, partial reviews, unknown process, unsupported provenance, missing exposure, conflicting revisions, adjudicator overlap under policy, representation loss or cross-split use. Next select the real process, obtain actual pilot reviews, review typed schemas and exercise isolated failure fixtures.
