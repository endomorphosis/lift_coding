"""Prepare authored compositional sources and blank human annotation envelopes."""

import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path('/home/barberb/lift_coding')
CAMPAIGN = ROOT / 'artifacts/autoformalization-alignment-20261003'
OUTPUT = CAMPAIGN / 'binding-review-packet-01'
PRIOR_SHA = 'd38b0cf7e628a2e9a552735f0e7280ac2d19b635b41df6138368e3e29cddd20f'
ACTORS = ('clerk', 'custodian', 'officer', 'registrar')
ACTION_OBJECT_PAIRS = (('notify', 'the applicant'), ('retain', 'the filing'),
                       ('audit', 'the application'), ('authorize', 'the application'))
TEMPLATES = (
    'The {actor} must {action} {object} before the review deadline if fees have been paid.',
    'If the application is complete and fees have been paid, the {actor} may {action} {object} within 48 hours unless a court order applies.',
    'The {actor} must not {action} {object} unless a court order applies or a legal hold applies.',
    'If fees have been paid and the application is complete, the {actor} must {action} {object} within 48 hours and before the review deadline unless a legal hold applies.',
)
ANNOTATION_FIELDS = ('interpretation_status', 'ambiguity', 'unsupported_meaning', 'normative_rules',
                     'freeform_qualifier_scope', 'notes', 'reviewer_id', 'reviewed_at_utc')
FALSE = dict(independent_semantic_review_completed=False, source_fidelity_established=False,
             qualified=False, proof_authority=False, accepted=False, training_executed=False)


def raw(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                      allow_nan=False).encode('utf-8')


def digest(value):
    return hashlib.sha256(raw(value)).hexdigest()


def binding(path):
    path = Path(path).resolve()
    data = path.read_bytes()
    return dict(path=str(path), bytes=len(data), sha256=hashlib.sha256(data).hexdigest())


def load(path, *, sealed=False):
    value = json.loads(Path(path).read_bytes())
    if sealed:
        assert value['content_sha256'] == digest({key: item for key, item in value.items()
                                                 if key != 'content_sha256'})
    return value


def seal(value):
    return {**value, 'content_sha256': digest(value)}


def save(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n')
    return binding(path)


def main():
    assert not OUTPUT.exists(), 'fresh review preparation required'
    prior_path = CAMPAIGN / 'typed-anchor-decoder-validation-01/validation.json'
    prior_binding = binding(prior_path)
    assert prior_binding['sha256'] == PRIOR_SHA
    prior = load(prior_path, sealed=True)
    preserved = [*prior['checked_file_bindings'], *prior['new_implementation_test_bindings']]
    assert prior['checked_file_count'] == 444
    for reference in preserved:
        assert binding(reference['path']) == reference
    old_sources_path = CAMPAIGN / 'canonical-codec-01/target_free_inputs.json'
    old_sources = load(old_sources_path, sealed=True)
    exposed_hashes = {row['source_sha256'] for row in old_sources['rows']}
    assert len(exposed_hashes) <= 34
    private_rows, public_rows = [], []
    empty_hash = hashlib.sha256(b'').hexdigest()
    for actor_index, actor in enumerate(ACTORS):
        for pair_index, (action, object_text) in enumerate(ACTION_OBJECT_PAIRS):
            group_id = f'authored-binding-composition-v1:{actor_index}:{pair_index}'
            split = 'proposed_train' if (actor_index - pair_index) % 4 in (0, 1) else 'proposed_development'
            for variant_index, template in enumerate(TEMPLATES):
                source = template.format(actor=actor, action=action, object=object_text)
                source_hash = hashlib.sha256(source.encode('utf-8')).hexdigest()
                assert source_hash not in exposed_hashes, 'new packet duplicates old exact source'
                context = dict(role='none_required', text='', bindings={}, sha256=empty_hash)
                input_hash = digest(dict(source_text=source, context=context))
                item_id = 'binding-review-item-' + hashlib.sha256(
                    b'authored-binding-review-v1\0' + bytes.fromhex(input_hash)).hexdigest()[:24]
                public = dict(item_id=item_id, source_text=source, source_sha256=source_hash,
                              input_sha256=input_hash, context=context,
                              annotation={field: None for field in ANNOTATION_FIELDS})
                public_rows.append(public)
                private_rows.append(dict(item_id=item_id, group_id=group_id, proposed_split=split,
                    variant_index=variant_index, actor_surface=actor, action_surface=action,
                    object_surface=object_text, source_sha256=source_hash, input_sha256=input_hash,
                    source_origin='programmatically_authored_controlled_English_fixture',
                    review_status='pending', natural_source=False, semantic_gold_created=False,
                    masks=dict(weak_decoder_fit=0, strong_semantic_fit=0, contrastive_supervision=0,
                               proof_supervision=0, fidelity_evaluation=0)))
    assert len(public_rows) == len({row['source_sha256'] for row in public_rows}) == 64
    assert len({row['item_id'] for row in public_rows}) == 64
    group_counts = Counter(row['group_id'] for row in private_rows)
    split_counts = Counter(row['proposed_split'] for row in private_rows)
    assert len(group_counts) == 16 and set(group_counts.values()) == {4}
    assert split_counts == dict(proposed_train=32, proposed_development=32)
    # IDs and source envelopes, rather than group or split labels, determine
    # reviewer order. Annotation slots remain entirely blank.
    public_rows.sort(key=lambda row: row['item_id'])
    payload = dict(schema='symbol-binding-source-reviewer/v1', instructions=dict(
        task='Interpret each exact authored source independently. No model output or expected answer is supplied.',
        context='No additional assumptions are supplied. Identify missing information and competing interpretations.',
        normative_rules='Describe every normative rule and its modality, actor, action, object and qualifiers in your own terms.',
        qualifier_scope='Explain condition conjunctions, exception disjunctions, timing, attachment and any limitations of flat facets.',
        blank_annotations='Null means unanswered. Use an explicit interpretation status and rationale when you find no rule, ambiguity or unsupported meaning.',
        identity='Fill identity and UTC time only after an actual review. A declared identity does not authenticate independence.',
        provenance='These are controlled-language authored fixtures, not natural-source evidence or independently reviewed meanings.'),
        items=public_rows)
    prohibited = {'proposal', 'canonical_ir', 'target', 'reference', 'group_id', 'proposed_split',
                  'variant_index', 'masks', 'actor_surface', 'action_surface', 'object_surface'}
    assert not prohibited.intersection(payload)
    assert all(not prohibited.intersection(row) and all(value is None for value in row['annotation'].values())
               for row in payload['items'])
    OUTPUT.mkdir()
    plan_binding = save(OUTPUT / 'plan.json', seal(dict(schema='symbol-binding-review-preparation-plan/v1',
        runner_binding=binding(__file__), prior_validation_binding=prior_binding,
        original_target_free_sources_binding=binding(old_sources_path), source_groups=16, items=64,
        variants_per_group=4, proposed_split_counts=dict(split_counts),
        group_split_rule='(actor_index-pair_index) mod 4 in {0,1} proposes TRAIN; other groups propose DEV',
        source_group_assignments_frozen_before_annotation=True, semantic_targets_created=False,
        actual_fit_or_evaluation_admission=False, sealed_final_test_created=False,
        previously_exposed_compositions_possible=True, source_author_independence_authenticated=False,
        paraphrase_equivalence_created=False, existing_review_admission_adapter_compatible=False,
        next_admission_requirement='Actual independent reviews, adjudication, and a separately versioned adapter for this payload.',
        **FALSE)))
    public_binding = save(OUTPUT / 'reviewer_items.json', payload)
    private_binding = save(OUTPUT / 'organizer_manifest_private.json', seal(dict(
        schema='symbol-binding-review-organizer/v1', rows=private_rows, source_groups=16,
        semantic_gold_created=False, model_candidates_included=False, original_reviews_completed=0,
        source_author_independence_authenticated=False, **FALSE)))
    manifest_binding = save(OUTPUT / 'reviewer_manifest.json', seal(dict(
        schema='symbol-binding-review-audience-manifest/v1', audience='reviewer',
        reviewer_payload_binding=public_binding, candidate_reference_blind=True, split_and_group_blind=True,
        item_count=64, blank_annotations=True, reviewer_submissions_created=False,
        reviewer_identity_attestations_created=False, natural_source_corpus=False, **FALSE)))
    for reference in preserved:
        assert binding(reference['path']) == reference
    report = seal(dict(schema='symbol-binding-review-preparation-report/v1', status='prepared_pending_human_review',
        runner_binding=binding(__file__), plan_binding=plan_binding, reviewer_payload_binding=public_binding,
        reviewer_manifest_binding=manifest_binding, organizer_manifest_binding=private_binding,
        prior_validation_binding=prior_binding, source_bindings=prior['checked_file_bindings'],
        extra_prior_bindings=prior['new_implementation_test_bindings'],
        items=64, source_groups=16, proposed_split_counts=dict(split_counts),
        exact_source_overlap_with_previous_34=0, existing_34_reviews_completed=0,
        new_64_reviews_completed=0, model_calls=0, new_encoder_calls=0, prover_calls=0,
        qualified_training_pairs=0, semantic_gold_created=False, actual_training_or_evaluation_admission=False,
        natural_source_corpus=False, previously_exposed_compositions_possible=True,
        existing_review_admission_adapter_compatible=False, **FALSE))
    report_binding = save(OUTPUT / 'report.json', report)
    print(json.dumps(dict(report_binding=report_binding, prepared_items=64, groups=16), sort_keys=True))


if __name__ == '__main__':
    main()
