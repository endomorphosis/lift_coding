# AF-005 independent source-facet annotation guidelines

**Schema version:** `autoformalization-gold-facet/v1`  
**Packet version:** `autoformalization-annotation-packet/v1`  
**Guideline freeze:** `AF-005/v1`  
**Preparation input boundary:** listed pinned inputs only; no scored candidate output input  
**Independent human review at freeze:** pending / unavailable  
**Semantic claims at freeze:** unmeasured

These instructions freeze the gold and admissible-alternative schema, the candidate-blind packet contract, and the adjudication rules. They are not an annotation result, not a kappa, and not a substitute for independent human review.

## 1. Purpose and claim boundary

The evaluation question that these labels would eventually support is independently judged **source-facet fidelity** of a candidate formalization to a natural source, including admissible alternative readings, with abstention retained. Compiler/adaptor/view targets, mock or hashed embeddings, rights-review flags, cycle-equal IRs, and constructed minimal-pair witnesses are **not** this gold.

Until independent human review exists, every semantic fidelity, transfer, and proof-meaning claim that depends on these labels remains **unmeasured**. Preparing this packet does not complete annotation.

## 2. Freeze-before-outputs rule

The schema, facet inventory, admissible-alternative rule and these instructions must be fixed **before** scored model outputs are inspected. Freeze the intended propositions, logical profile, exceptions, temporal intervals, ambiguous readings, source-map spans, and admissible assumptions before evaluating model output.

Annotators, adjudicators, and packet authors must not:

- inspect A–E or T0–T5 candidate outputs, scores, or leaderboards
- inspect teacher IR, compiler/view targets, proof-feedback labels, or learned-advice dumps
- use candidate generation as the oracle for the intended meaning
- read final-test identities, bodies, or outcomes in a provider, training, selection, canary, or patch channel

Source-withheld realization remains a later harness obligation (AF-008). These guidelines do not authorize that access.

## 3. Populations and what may be reused

| Population | Role here | Gold status |
| --- | --- | --- |
| 100 provisional slots based on the public record histogram | Unbound annotation templates; not selected units | No source binding or independent labels |
| 1,913 unique final-test units in 20 operational groups | Private eligible population; sample membership remains unbound | Unmeasured; no unsampled count established |
| 69 train / 15 selection / 38 fixed-canary development units | Calibration packets only | Not evaluation gold |
| AF-006 constructed minimal pairs | Conformance witnesses with independently specified distinctions | Not natural-distribution gold |
| Semantic-roundtrip fixtures | Excluded synthetic fixtures | Not gold |
| Teacher/compiler/view/proof-feedback labels | Automatic teacher-derived supervision | Identified separately; never gold |
| Upstream rights_review | Redistribution/license review | Not semantic review |

Reuse independently reviewed labels only after a provenance audit that records annotator identity/independence, guideline version, blinding, disagreement, and adjudication. The AF-004/AF-005 inventory found **no** such reusable independent semantic labels (`existing_semantic_labels_used = 0`). Do not invent them.

## 4. Candidate-blind packet contract

Each packet contains only:

- packet identity and role (`planned_final_annotation_slot` or `development_calibration`)
- split/group-slot metadata or a development source locator
- the facet list to fill
- a pointer to this guideline freeze

Packets must not contain model outputs, teacher IR, gold values, proof scores, or retrieval hits. Final-test source bodies and identifiers stay in owner-only research inputs until an authorized annotator workstation, not a model provider, binds a slot. Development source bodies remain in the AF-004 snapshot exports; calibration packets cite those files by path and content hash rather than inlining text.

## 5. Frozen gold / admissible-alternative schema

The JSON object below is the frozen schema. Later scoring may add a candidate side-car; it may not change these fields after outcome inspection.

```json
{
  "schema": "autoformalization-gold-facet/v1",
  "facet_ids": [
    "propositions",
    "modality",
    "negation",
    "actor_recipient_roles",
    "quantifiers",
    "exceptions",
    "temporal_interpretation",
    "ambiguity",
    "source_spans",
    "admissible_assumptions"
  ],
  "required_proposition_slots": [
    "predicate",
    "polarity",
    "source_span"
  ],
  "modality_inventory": [
    "obligation_O",
    "permission_P",
    "prohibition_F",
    "claim_fact",
    "knowledge_K",
    "belief_B",
    "other_declared",
    "absent_no_normative_force"
  ],
  "negation_inventory": [
    "factual_negation",
    "prohibition",
    "observed_absence_incomplete_trace",
    "scope_over_quantifier",
    "scope_over_condition",
    "none"
  ],
  "quantifier_inventory": [
    "none",
    "universal",
    "existential",
    "numerical",
    "order_universal_then_existential",
    "order_existential_then_universal",
    "unresolved_scope"
  ],
  "temporal_inventory": [
    "untimed",
    "event_time",
    "interval_window",
    "deadline_within",
    "always_G",
    "eventually_F",
    "next_X",
    "until_U",
    "since",
    "unresolved"
  ],
  "ambiguity_status": [
    "single_supported_reading",
    "multiple_admissible_readings",
    "unresolvable_from_source",
    "annotator_abstain"
  ],
  "adjudication_status": [
    "pending_independent_review",
    "not_applicable_single_annotator_pending",
    "agreed",
    "disagreed_unresolved",
    "adjudicated"
  ],
  "label_origin": [
    null,
    "independent_human_review",
    "automatic_teacher_derived",
    "constructed_conformance_witness",
    "rights_review_not_semantic"
  ],
  "unique_string_match_required": false,
  "abstention_permitted": true,
  "teacher_derived_admitted_as_gold": false
}
```

A gold record is complete only when every `facet_ids` entry has an independent-human value or an explicit abstention, disagreement and adjudication fields are filled from real annotator records, and `label_origin` is `independent_human_review`. Empty pending records are not complete gold.

## 6. Facet instructions

Work source-first. Quote or span-ground every non-abstaining value. If the source does not support a slot, mark abstention rather than completing the teacher vocabulary.

### 6.1 Propositions

Record the source-supported atomic contents (who must/may/does what to whom, under what claim). Do not add unstated conjuncts. Predicate sense must be source-grounded; ontology IDs are optional links, never a replacement for the source proposition. A cycle-reconstructed IR that drops a proposition is a fidelity failure even if I1 equals I2.

### 6.2 Modality

Distinguish obligation, permission, prohibition, bare factual claim, knowledge, and belief. “Must file” is not “filed.” “May export” is not an observed export. Do not recode a normal deontic O as a fact, or a nonfactive belief as knowledge. If several clauses carry different forces, label each proposition separately.

### 6.3 Negation

Keep (i) factual negation, (ii) prohibition, and (iii) unobserved events in an incomplete trace distinct. “Must not export” can be true in a violation model where export occurred. “No audit appears in a partial log” is unknown unless capture completeness is source-supported. Record the scope of negation over quantifiers and conditions.

### 6.4 Actor and recipient roles

Bind actors, recipients, objects, and authorities as they appear, including tenant or office identity when the source supplies it. Surface-string equality is not identity. Unaligned names stay unresolved; do not merge them to satisfy a frame.

### 6.5 Quantifiers

Record binder sequence, domain, and bound variables. “Every user has some key” is not “there is one key for every user.” Numerical thresholds (“transactions exceeding $10,000”) are quantifiers, not decorative adjectives. If order is ambiguous after applying §6.8, list admissible orders rather than picking one to match a compiler.

### 6.6 Exceptions and conditions

“Unless,” “except,” “only if,” and ordinary preconditions have different directions. “Must audit unless exempt” is a guard on the obligation, not an unconditional audit and not an audit required only of the exempt. “Write only if approved” is write → approved, not the converse. Dropping an exception is a source-meaning change even when a round trip remains IR-equal.

### 6.7 Temporal interpretation

Record anchors (event time, effective date, accounting period), windows, deadlines, and operators (always, until, within-n). “Retained throughout the window” is not truth at the current instant. Strong until is not conjunction at time zero. Incomplete windows stay incomplete.

### 6.8 Ambiguity

If two readings are both source-supported, record both as admissible alternatives. Do not force a unique string or a unique IR. If the source cannot resolve the reading, mark `unresolvable_from_source` or abstain. Ambiguity is a first-class label, not noise.

### 6.9 Source spans

Every non-abstaining facet value must cite a source span (character offsets into the bound source unit, plus the quoted fragment). Spans may overlap. Do not cite teacher IR, neighboring sections outside the unit, or a model candidate. Adjacent-section leakage is a split issue, not an annotation shortcut.

### 6.10 Admissible assumptions

List only assumptions the source licenses (statutory cross-references that the unit itself invokes, definitions given in-unit, explicit incorporation). World knowledge, ontology defaults, compiler registries, and “the model usually treats X as Y” are inadmissible. If a proof or IR needs an extra premise, mark it inadmissible unless the source supports it.

## 7. Admissible alternatives, abstention, and scoring implications

Gold is a set of supported readings, not a single target string. A candidate matches if it is equivalent to any admissible reading under the declared logical profile and does not assert a rejected reading. Abstention, unsupported, unknown, and unresolvable remain distinct denominator statuses. Unique-string match is forbidden. Teacher self-consistency is a diagnostic, never this score.

## 8. Annotator independence, disagreement, and adjudication

Independent review means at least two humans who did not author the system, the teacher labels, or the candidate outputs, working from these frozen instructions and candidate-blind packets.

Required records, when review exists:

- annotator ids (anonymous in public artifacts)
- independence attestation (no candidate/teacher access)
- guideline version
- per-facet labels
- pairwise agreement and disagreement counts from those records
- adjudicator id, disputed facets, and the chosen admissible set

Do not impute Cohen’s kappa, majority vote, or consensus from teacher labels, from a single implementer, or from a language model. If only one annotator is available, adjudication is not complete and semantic claims stay unmeasured.

**Current real record:** zero independent annotators, zero completed double-annotated units, zero agreements, zero disagreements, zero adjudications. That zero is an observed inventory, not a measured high-agreement result.

## 9. Provisional slots and the pending sampling decision

The existing full-route floor remains at least 100 independently adjudicated distinct natural final-test units from at least 20 operational groups. AF-004 records 1,913 unique final-test units across 20 operational groups. None is bound or adjudicated by this preparation.

The generator's 100 blank slots illustrate capacity using the public **record** histogram (1,921 records including eight aliases). They are not a frozen evaluation sample, private membership commitments, or evidence that each group supplies the required unique-unit count. Their `evaluation_sample` and `evaluation_eligible` fields are false; actual label origin is null and intended human origin is stated separately.

Before source binding, an authorized annotator workflow must verify private per-group unique-unit counts, version the sample selection and the unit-versus-group estimand/weights, then bind exact units without inspecting candidate outputs or labels. A cluster bootstrap does not by itself define equal-group point weights. This preparation changes neither the existing experiment estimand nor the private partition/salt. Final-test sources and labels remain outside provider workspaces.

Any final allocation and eligible population must be fixed before outcomes. Preserve shortfalls and all selected-unit denominator statuses; do not perform outcome-driven replacement. Development calibration units cannot replace missing final-test annotations. Operational groups are correlated and do not establish 20 independent publishers or editions.

## 10. What remains pending

Independent human review is required and currently unavailable. Development locator packets, unbound final-slot templates, schema and these instructions are prepared. Actual final-source binding and sampling/weight decisions remain pending. Gold facet values, agreement statistics beyond the observed zeros, adjudication decisions, and all semantic claims that depend on them remain pending and unmeasured.

A later review task must keep this guideline digest, remain candidate-blind, and write real annotator records. It must not mark this freeze as completed annotation.
