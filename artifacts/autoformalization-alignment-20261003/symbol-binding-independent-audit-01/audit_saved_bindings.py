"""Independently recompute immutable static receipts using only the stdlib."""

import ast
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path('/home/barberb/lift_coding')
BASE = ROOT / 'artifacts/autoformalization-alignment-20261003'
HERE = Path(__file__).resolve().parent
ASSAY = BASE / 'symbol-binding-recovery-02'
REVIEW = BASE / 'binding-review-packet-01'
SKIP = {'mutable_main_plan_prior_reference', 'mutable_main_plan_observed_before_binding'}
FALSE = {name: False for name in ('model_executed', 'prover_executed', 'neural_training_executed',
                                  'encoder_executed', 'source_fidelity_established', 'qualified',
                                  'proof_authority', 'accepted', 'independent_semantic_review_completed')}
CHECKER_FALSE = {name: False for name in ('model_executed', 'prover_executed',
    'source_fidelity_established', 'qualified', 'proof_authority', 'accepted',
    'independent_semantic_review_completed')}
TRANSPORT_FALSE = {name: False for name in ('target_access', 'model_executed',
    'source_fidelity_established', 'qualified', 'proof_authority', 'accepted')}
NORMALIZATION = 'unicode-casefold-whitespace-collapse-no-lexical-expansion/v1'
RECIPE = 'sha256_canonical_sorted_compact_UTF8_JSON_without_content_sha256'
checked = {}


def raw(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                      allow_nan=False).encode('utf-8')


def digest(value):
    return hashlib.sha256(raw(value)).hexdigest()


def text_sha(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def seal(value):
    assert 'content_sha256' not in value
    return {**value, 'content_sha256': digest(value)}


def bind(path):
    path = Path(path).resolve()
    checksum, size = hashlib.sha256(), 0
    with path.open('rb') as stream:
        while chunk := stream.read(1024 * 1024):
            checksum.update(chunk)
            size += len(chunk)
    return dict(path=str(path), bytes=size, sha256=checksum.hexdigest())


def check_ref(reference):
    observed = bind(reference['path'])
    assert observed['sha256'] == reference['sha256'], reference['path']
    assert 'bytes' not in reference or observed['bytes'] == reference['bytes'], reference['path']
    if observed['path'] in checked:
        assert checked[observed['path']] == observed
    checked[observed['path']] = observed
    return observed


def refs(value):
    if isinstance(value, dict):
        if 'path' in value and 'sha256' in value:
            check_ref(value)
        for key, item in value.items():
            if key not in SKIP:
                refs(item)
    elif isinstance(value, list):
        for item in value:
            refs(item)


def load(path, *, sealed=True):
    check_ref(bind(path))
    value = json.loads(Path(path).read_bytes())
    if sealed:
        assert value == seal({k: v for k, v in value.items() if k != 'content_sha256'}), str(path)
    return value


def normalize(literal):
    return ' '.join(literal.casefold().split())


def validate_proposal(proposal, source):
    assert set(proposal) == {'schema', 'source_sha256', 'canonical_ir', 'anchors',
                             'facet_operators', 'single_rule_scope', *TRANSPORT_FALSE}
    assert proposal['schema'] == 'canonical-anchored-byte-proposal/v1'
    assert proposal['source_sha256'] == text_sha(source)
    assert proposal['single_rule_scope'] is True
    assert proposal['facet_operators'] == {'conditions': 'all', 'exceptions': 'any', 'temporal': 'all'}
    assert all(proposal[k] is False for k in TRANSPORT_FALSE)
    assert set(proposal['canonical_ir']) == {'rules'} and len(proposal['canonical_ir']['rules']) == 1
    rule = proposal['canonical_ir']['rules'][0]
    assert set(rule) == {'actor', 'action', 'object', 'modality', 'conditions', 'exceptions', 'temporal'}
    expected_leaves = {}
    for facet in ('actor', 'action', 'object', 'modality'):
        symbol = rule[facet]
        assert type(symbol) is str and len(symbol) <= 512
        assert symbol.strip() or facet == 'object' and symbol == ''
        if symbol:
            expected_leaves['/rules/0/' + facet] = (facet, symbol)
    assert rule['modality'] in ('O', 'P', 'F')
    for facet in ('conditions', 'exceptions', 'temporal'):
        symbols = rule[facet]
        assert type(symbols) is list and len(symbols) <= 64 and symbols == sorted(set(symbols))
        for index, symbol in enumerate(symbols):
            assert type(symbol) is str and symbol.strip() and len(symbol) <= 512
            expected_leaves[f'/rules/0/{facet}/{index}'] = (facet, symbol)
    assert len(proposal['anchors']) == len(expected_leaves)
    intervals = []
    for anchor, (path, (facet, symbol)) in zip(proposal['anchors'], sorted(expected_leaves.items()), strict=True):
        assert set(anchor) == {'field_path', 'facet', 'canonical_symbol', 'start', 'end', 'source_text', 'offset_unit'}
        assert (anchor['field_path'], anchor['facet'], anchor['canonical_symbol']) == (path, facet, symbol)
        start, end = anchor['start'], anchor['end']
        assert type(start) is int and type(end) is int and 0 <= start < end <= len(source)
        assert anchor['source_text'] == source[start:end]
        assert anchor['offset_unit'] == 'unicode_character_half_open'
        intervals.append((start, end))
    assert all(left[1] <= right[0] for left, right in zip(sorted(intervals), sorted(intervals)[1:]))


def assessment(proposal, source, profile, table):
    validate_proposal(proposal, source)
    counts = dict.fromkeys(('matched_single_alias', 'known_alias_mismatch', 'unknown_literal', 'ambiguous_alias'), 0)
    leaves = []
    for anchor in proposal['anchors']:
        literal = normalize(anchor['source_text'])
        known = table.get((anchor['facet'], literal), [])
        outcome = ('unknown_literal' if not known else 'ambiguous_alias' if len(known) > 1 else
                   'matched_single_alias' if known[0] == anchor['canonical_symbol'] else 'known_alias_mismatch')
        counts[outcome] += 1
        leaves.append(dict(field_path=anchor['field_path'], facet=anchor['facet'], start=anchor['start'],
            end=anchor['end'], source_text=anchor['source_text'], normalized_literal=literal,
            claimed_symbol=anchor['canonical_symbol'], recognized_symbols=list(known), outcome=outcome))
    outcome = ('binding_inconsistent' if counts['known_alias_mismatch'] else 'binding_unassessed'
               if counts['unknown_literal'] or counts['ambiguous_alias'] else 'binding_consistent')
    return seal(dict(schema='canonical-source-symbol-bindings/v1', checksum_recipe=RECIPE,
        source_sha256=text_sha(source), proposal_sha256=digest(proposal), profile_sha256=profile['content_sha256'],
        normalization=NORMALIZATION, outcome=outcome, leaf_count=len(leaves), leaf_outcome_counts=counts,
        leaves=leaves, profile_training_supervision_consumed=True, query_reference_accessed=False,
        target_access=False, target_access_scope='query_reference_only', proposal_input_scope='model_candidate_not_reference',
        assessment_scope='per_leaf_observed_TRAIN_literal_alias_agreement', proposal_changed=False,
        canonical_ir_repaired=False, training_executed=False, **CHECKER_FALSE))


def counts(rows):
    leaves = Counter()
    for row in rows:
        if row['assessment'] is not None:
            leaves.update(row['assessment']['leaf_outcome_counts'])
    result = dict(row_count=len(rows),
        original_generation_outcome_counts=dict(Counter(r['original_generation_outcome'] for r in rows)),
        binding_outcome_counts=dict(Counter(r['binding_outcome'] for r in rows)),
        binding_unavailable_reason_counts=dict(Counter(r['binding_unavailable_reason'] for r in rows
                                                     if r['binding_unavailable_reason'] is not None)),
        original_full_proposal_count=sum(r['candidate_proposal_sha256'] is not None for r in rows),
        candidate_output_withheld_count=sum(r['candidate_output_withheld'] for r in rows),
        candidate_output_available_count=sum(r['output_proposal'] is not None for r in rows),
        leaf_count=sum(r['assessment']['leaf_count'] for r in rows if r['assessment'] is not None),
        leaf_outcome_counts=dict(leaves), by_split={}, by_row_kind={})
    for dimension in ('split', 'row_kind'):
        for label in {r[dimension] for r in rows}:
            subset = [r for r in rows if r[dimension] == label]
            result['by_' + dimension][label] = dict(row_count=len(subset),
                binding_outcome_counts=dict(Counter(r['binding_outcome'] for r in subset)),
                original_full_proposal_count=sum(r['candidate_proposal_sha256'] is not None for r in subset),
                candidate_output_withheld_count=sum(r['candidate_output_withheld'] for r in subset),
                candidate_output_available_count=sum(r['output_proposal'] is not None for r in subset))
    return result


def unavailable(original, role):
    return {'source_blocked': 'source_preflight_blocked', 'clarification_required': 'context_clarification_required',
            'source_encoding_unavailable': 'retained_source_codec_OOV'}.get(original['outcome']) or (
        'canonical_only_output_has_no_anchor_contract' if role in ('source_initial', 'source_final') else
        'prior_anchor_abstention' if original['outcome'] == 'anchor_abstained' else
        'prior_parent_abstention_or_unavailability')


def main():
    report = load(ASSAY / 'report.json')
    review_report = load(REVIEW / 'report.json')
    plan = load(ASSAY / 'plan.json')
    profile = load(report['profile_binding']['path'])
    manifest = load(report['fit_manifest_binding']['path'])
    refs(report)
    refs(plan)
    refs(review_report)
    assert report['status'] == 'completed_static_saved_candidate_recovery_assay'
    assert report['mutable_main_plan_preservation_required'] is False
    assert report['source_bindings'] == review_report['source_bindings']
    assert len(report['source_bindings']) == report['preserved_prior_checked_file_count'] == 444
    assert len(report['extra_prior_typed_implementation_test_bindings']) == 2
    assert report['extra_prior_typed_implementation_test_bindings'] == review_report['extra_prior_bindings']
    assert len(report['interrupted_stage_bindings']) == 3
    assert {p.name for p in (BASE / 'symbol-binding-01').iterdir()} == {
        'plan.json', 'train_alias_profile.json', 'train_profile_manifest.json'}
    assert report['recovery_profile_fit_calls'] == 0 and report['original_completed_profile_fit_calls'] == 1
    assert report['failed_attempt'] == plan['failed_attempt']
    assert report['failed_attempt']['observed_failed_peak_rss_kib'] is None
    assert report['failed_attempt']['failure_cause'] == 'unknown'
    assert report['failed_attempt']['candidate_body_reads'] == report['failed_attempt']['gate_assessment_calls'] == 0
    assert report['failed_recovery_attempt'] == plan['failed_recovery_attempt']
    assert report['failed_recovery_attempt']['profile_fit_calls'] == 0
    assert report['failed_recovery_attempt']['candidate_body_reads'] == 0
    assert report['failed_recovery_attempt']['underlying_cause'] == 'not_independently_established'
    assert len(report['interrupted_recovery_stage_bindings']) == 1
    assert {p.name for p in (BASE / 'symbol-binding-recovery-01').iterdir()} == {'resource_observations.jsonl'}
    failed_resource = report['failed_recovery_attempt']['resource_observation']
    assert failed_resource['resource_ru_maxrss_kib'] == 1719700
    assert failed_resource['linux_current_rss_kib'] == failed_resource['linux_peak_hwm_kib'] == 18736
    assert json.loads(Path(report['interrupted_recovery_stage_bindings'][0]['path']).read_text()) == failed_resource
    assert report['resource_measurement_scope'] == 'fresh_forked_static_worker'
    assert report['launch_parent_resource_observation']['resource_measurement_scope'] == 'launcher_before_fresh_worker_fork'
    assert report['original_profile_reused_without_refitting'] is True
    requests = load(BASE / 'typed-anchor-decoder-recovery-01/inference_requests.json')['rows']
    request_map = {r['id']: r for r in requests}
    metadata = load(BASE / 'canonical-codec-01/all_request_outcomes.json')['rows']
    meta_map = {r['id']: r for r in metadata}
    train = load(BASE / 'canonical-codec-01/train_weak_supervision.json')['rows']
    examples = []
    observed = defaultdict(lambda: {'symbols': set(), 'count': 0})
    for row in train:
        request, meta = request_map[row['id']], meta_map[row['id']]
        assert meta['split'] == 'train' and meta['row_kind'] == 'positive'
        assert row['masks'] == dict(weak_decoder_fit=1, strong_semantic_fit=0,
                                  contrastive_supervision=0, proof_supervision=0, fidelity_evaluation=0)
        assert row['independent_semantic_review_completed'] is False
        validate_proposal(row['proposal'], request['source_text'])
        examples.append(dict(id=row['id'], source_text=request['source_text'], proposal=row['proposal']))
        for anchor in row['proposal']['anchors']:
            key = (anchor['facet'], normalize(anchor['source_text']))
            assert key[1]
            observed[key]['symbols'].add(anchor['canonical_symbol'])
            observed[key]['count'] += 1
    assert len(examples) == 16
    assert {r['id'] for r in examples} == {r['id'] for r in metadata if r['split'] == 'train'}
    entries = [dict(facet=facet, normalized_literal=literal, canonical_symbols=sorted(item['symbols']),
                    observation_count=item['count']) for (facet, literal), item in sorted(observed.items())]
    expected_profile = seal(dict(schema='canonical-observed-train-alias-profile/v1', normalization=NORMALIZATION,
        checksum_recipe=RECIPE, training_manifest_sha256=digest(examples), training_pair_count=16,
        training_anchor_count=124, alias_entry_count=20, ambiguous_alias_count=0, entries=entries,
        training_supervision_consumed=True, query_reference_accessed=False,
        correspondence_origin='caller_declared_TRAIN_exact_anchor_correspondences',
        fit_operation='deterministic_alias_aggregation_without_model_training',
        semantic_scope='observed_literal_facet_symbol_agreement_only', examples_persisted=False, **CHECKER_FALSE))
    assert profile == expected_profile
    assert profile['content_sha256'] == report['profile_content_sha256'] == 'b2f897a33ca3e7c43b2879db4abb651653dedab587bc6f94364a6bd80bb06324'
    assert manifest['row_count'] == 16 and manifest['training_manifest_sha256'] == digest(examples)
    assert [r['id'] for r in manifest['rows']] == [r['id'] for r in examples]
    table = {(e['facet'], e['normalized_literal']): e['canonical_symbols'] for e in entries}
    primary, private, outputs, contradictions = [], [], {}, []
    for spec in report['assessment_records']:
        record = load(spec['assessment_binding']['path'])
        original = load(spec['original_generation_binding']['path'])
        refs(record)
        assert len(record['rows']) == len(original['rows']) == 34
        assert record['seed'] == spec['seed'] and record['role'] == spec['role']
        assert record['is_private_repeat'] is spec['is_private_repeat']
        assert record['original_generation_binding'] == spec['original_generation_binding']
        assert record['profile_content_sha256'] == profile['content_sha256']
        assert all(record[k] is False for k in FALSE)
        for pos, (row, prior_row, request) in enumerate(zip(record['rows'], original['rows'], requests, strict=True)):
            assert row['id'] == prior_row['id'] == request['id'] and row['position'] == prior_row['position'] == pos
            assert row['source_sha256'] == prior_row['source_sha256'] == text_sha(request['source_text'])
            assert row['context_sha256'] == prior_row['context_sha256'] == text_sha(request['context_text'])
            assert row['request_sha256'] == digest(request)
            assert row['original_generation_row_sha256'] == digest(prior_row)
            assert row['original_generation_outcome'] == prior_row['outcome']
            assert all(row[k] == meta_map[row['id']][k] for k in ('split', 'group_id', 'row_kind', 'review_status'))
            assert all(row[k] is False for k in FALSE)
            assert row['candidate_unchanged'] is True and row['canonical_ir_repaired'] is False
            assert row['query_reference_accessed'] is False
            candidate = prior_row.get('proposal')
            if candidate is None:
                assert row['assessment'] is None and row['candidate_proposal_sha256'] is None
                assert row['binding_outcome'] == 'binding_unavailable'
                assert row['binding_unavailable_reason'] == unavailable(prior_row, spec['role'])
            else:
                expected = assessment(candidate, request['source_text'], profile, table)
                assert row['assessment'] == expected
                assert row['candidate_proposal_sha256'] == digest(candidate)
                assert row['binding_outcome'] == expected['outcome'] and row['binding_unavailable_reason'] is None
            assert row['candidate_output_withheld'] is (row['binding_outcome'] == 'binding_inconsistent')
            assert row['output_proposal'] == (None if row['candidate_output_withheld'] else candidate)
            if not spec['is_private_repeat'] and row['candidate_output_withheld']:
                contradictions.append(dict(seed=spec['seed'], position=pos, id=row['id'], split=row['split'],
                    mismatch_leaves=[l for l in row['assessment']['leaves'] if l['outcome'] == 'known_alias_mismatch']))
        assert record['counts'] == counts(record['rows']) == spec['counts']
        if spec['is_private_repeat']:
            assert raw(record['rows']) == raw(outputs[(spec['seed'], spec['role'])]['rows'])
            assert spec['private_repeat_exact_row_json_equal_primary'] is True
            private.extend(record['rows'])
        else:
            assert spec['private_repeat_exact_row_json_equal_primary'] is None
            outputs[(spec['seed'], spec['role'])] = record
            primary.extend(record['rows'])
    assert len(outputs) == 12 and len(primary) == 408 and len(private) == 102
    assert report['primary_counts'] == counts(primary)
    assert report['private_repeat_counts'] == counts(private)
    assert report['all_saved_receipt_counts'] == counts(primary + private)
    assert len(contradictions) == len(report['primary_recognized_alias_contradictions']) == 1
    contradiction = contradictions[0]
    assert contradiction['seed'] == 1729 and contradiction['split'] == 'validation'
    assert {l['facet'] for l in contradiction['mismatch_leaves']} == {'action', 'object'}
    bound_contradiction = report['primary_recognized_alias_contradictions'][0]
    assert bound_contradiction['id'] == contradiction['id']
    assert bound_contradiction['known_alias_mismatch_leaves'] == contradiction['mismatch_leaves']
    assert bound_contradiction['comparison_scope'] == 'TRAIN_alias_correspondence_not_query_gold'
    assert report['observed_calls'] == dict(profile_fitting=0, primary_assessments=49, private_repeat_assessments=49,
        saved_assessment_validation_recomputations=98, candidate_redecoding=0, model=0, encoder=0, optimizer_updates=0, prover=0)
    assert all(report[k] is False for k in FALSE)
    assert report['model_import_attempts'] == report['model_execution_stacks_loaded'] == []
    assert all(report[k] is False for k in ('query_reference_accessed', 'authored_reference_ir_accessed',
        'development_reference_ir_accessed', 'development_weak_proposal_accessed', 'weak_gold_comparison_performed'))
    journal = [json.loads(line) for line in Path(report['resource_journal_binding']['path']).read_text().splitlines()]
    assert journal == report['resource_observations']
    assert journal[0]['label'] == 'initial_resource_baseline' and journal[-1]['label'] == 'final_resource_observation'
    assert all(0 <= row['elapsed_wall_seconds'] < 60 for row in journal)
    assert all(a['elapsed_wall_seconds'] <= b['elapsed_wall_seconds'] for a, b in zip(journal, journal[1:]))
    for row in journal:
        assert all(row[k] is None or type(row[k]) is int and 0 < row[k] < 524288 for k in
                   ('resource_ru_maxrss_kib', 'linux_current_rss_kib', 'linux_peak_hwm_kib'))
    assert report['peak_rss_kib'] >= max(row['resource_ru_maxrss_kib'] for row in journal)
    assert report['peak_rss_kib'] < 524288 and report['wall_seconds'] < 60
    public = load(REVIEW / 'reviewer_items.json', sealed=False)
    organizer = load(REVIEW / 'organizer_manifest_private.json')
    review_plan = load(REVIEW / 'plan.json')
    audience = load(REVIEW / 'reviewer_manifest.json')
    for value in (organizer, review_plan, audience):
        refs(value)
    assert set(public) == {'schema', 'instructions', 'items'} and public['schema'] == 'symbol-binding-source-reviewer/v1'
    assert len(public['items']) == len(organizer['rows']) == 64
    assert public['items'] == sorted(public['items'], key=lambda r: r['item_id'])
    constants = {}
    for node in ast.parse(Path(review_report['runner_binding']['path']).read_text()).body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in {'ACTORS', 'ACTION_OBJECT_PAIRS', 'TEMPLATES'}:
                    constants[target.id] = ast.literal_eval(node.value)
    annotation_fields = {'interpretation_status', 'ambiguity', 'unsupported_meaning', 'normative_rules',
                         'freeform_qualifier_scope', 'notes', 'reviewer_id', 'reviewed_at_utc'}
    private_map = {r['item_id']: r for r in organizer['rows']}
    splits, groups, source_hashes, group_splits = Counter(), Counter(), set(), defaultdict(set)
    for row in public['items']:
        assert set(row) == {'item_id', 'source_text', 'source_sha256', 'input_sha256', 'context', 'annotation'}
        assert set(row['annotation']) == annotation_fields and all(v is None for v in row['annotation'].values())
        assert row['source_sha256'] == text_sha(row['source_text'])
        assert row['context'] == dict(role='none_required', text='', bindings={}, sha256=text_sha(''))
        assert row['input_sha256'] == digest(dict(source_text=row['source_text'], context=row['context']))
        assert row['item_id'] == 'binding-review-item-' + hashlib.sha256(
            b'authored-binding-review-v1\0' + bytes.fromhex(row['input_sha256'])).hexdigest()[:24]
        private_row = private_map[row['item_id']]
        actor_index, pair_index = map(int, private_row['group_id'].split(':')[-2:])
        action, object_text = constants['ACTION_OBJECT_PAIRS'][pair_index]
        reconstructed_source = constants['TEMPLATES'][private_row['variant_index']].format(
            actor=constants['ACTORS'][actor_index], action=action, object=object_text)
        assert reconstructed_source == row['source_text']
        assert private_row['source_sha256'] == row['source_sha256'] and private_row['input_sha256'] == row['input_sha256']
        assert private_row['proposed_split'] == ('proposed_train' if (actor_index - pair_index) % 4 in (0, 1)
                                                else 'proposed_development')
        assert private_row['review_status'] == 'pending'
        assert private_row['natural_source'] is False and private_row['semantic_gold_created'] is False
        assert private_row['masks'] == dict.fromkeys(('weak_decoder_fit', 'strong_semantic_fit',
            'contrastive_supervision', 'proof_supervision', 'fidelity_evaluation'), 0)
        source_hashes.add(row['source_sha256'])
        groups[private_row['group_id']] += 1
        splits[private_row['proposed_split']] += 1
        group_splits[private_row['group_id']].add(private_row['proposed_split'])
    assert len(private_map) == len(source_hashes) == 64 and len(groups) == 16
    assert set(groups.values()) == {4} and all(len(v) == 1 for v in group_splits.values())
    assert splits == {'proposed_train': 32, 'proposed_development': 32}
    old_sources = load(BASE / 'canonical-codec-01/target_free_inputs.json')
    assert not source_hashes.intersection(r['source_sha256'] for r in old_sources['rows'])
    assert audience['candidate_reference_blind'] is audience['split_and_group_blind'] is True
    assert audience['reviewer_submissions_created'] is audience['reviewer_identity_attestations_created'] is False
    assert review_plan['semantic_targets_created'] is review_plan['actual_fit_or_evaluation_admission'] is False
    assert review_plan['sealed_final_test_created'] is review_plan['source_author_independence_authenticated'] is False
    assert review_plan['previously_exposed_compositions_possible'] is True
    assert review_plan['existing_review_admission_adapter_compatible'] is False
    assert review_report['existing_34_reviews_completed'] == review_report['new_64_reviews_completed'] == 0
    assert all(review_report[k] is False for k in ('semantic_gold_created', 'natural_source_corpus',
        'actual_training_or_evaluation_admission', 'source_fidelity_established', 'qualified', 'proof_authority', 'accepted'))
    assert not any(name.split('.')[0] in {'torch', 'spacy', 'transformers', 'numpy', 'tensorflow', 'jax'} for name in sys.modules)
    check_ref(bind(__file__))
    result = seal(dict(schema='alignment-symbol-binding-independent-stdlib-audit/v1', status='passed',
        audit_runner_binding=bind(__file__), assay_report_binding=bind(ASSAY / 'report.json'),
        review_report_binding=bind(REVIEW / 'report.json'),
        checked_file_count=len(checked), checked_file_bindings=sorted(checked.values(), key=lambda r: r['path']),
        mutable_main_plan_historical_keys_exempted=sorted(SKIP),
        original_static_attempt=dict(saved_files=3, completed_profile_fit_calls=1, candidate_body_reads=0,
            failed_peak_rss_kib=None, failure_cause='unknown', preservation_verified=True),
        first_recovery_attempt=dict(saved_files=1, profile_fit_calls=0, input_reads=0, candidate_body_reads=0,
            observed_ru_maxrss_kib=1719700, observed_Linux_RSS_and_HWM_kib=18736,
            underlying_cause='not_independently_established', preservation_verified=True),
        recovered_static_assay=dict(profile_fit_calls=0, TRAIN_pairs=16, anchored_observations=124,
            facet_literal_keys=20, collisions=0, profile_sha256=profile['content_sha256'],
            exact_TRAIN_manifest_sha256=digest(examples), primary_receipts=12, private_repeat_receipts=3,
            primary_rows=408, private_repeat_rows=102, total_saved_row_slots=510,
            primary_counts=counts(primary), private_repeat_counts=counts(private),
            recognized_alias_contradictions=contradictions, private_row_json_parity_count=3,
            independently_recomputed_assessments=98, query_reference_comparisons=0,
            resource_journal_observations=len(journal), recovery_peak_rss_kib=report['peak_rss_kib'],
            resource_measurement_scope='fresh_forked_static_worker',
            launch_parent_resource_observation=report['launch_parent_resource_observation'],
            prior_preserved_bindings=444, extra_prior_typed_pins=2, frozen_partial_files=3,
            preserved_failed_recovery_files=1),
        reviewer_packet=dict(items=64, groups=16, variants_per_group=4, proposed_split_counts=dict(splits),
            blank_annotation_cells=512, exact_source_overlap_with_old34=0,
            public_candidate_reference_group_split_mask_fields=0, model_targets_created=0,
            fit_or_fidelity_masks_nonzero=0, old_reviews_completed=0, new_reviews_completed=0,
            natural_source_corpus=False, author_independence_authenticated=False,
            possible_composition_exposure=True, sealed_final_test=False, admission_adapter_compatible=False),
        audit_scope='immutable_bytes_and_independent_stdlib_recomputation_not_semantic_adjudication_or_execution_replay',
        known_limits=['Observed weak TRAIN aliases may encode mistakes.',
            'Per-leaf binding consistency cannot establish whole-source coverage or qualifier scope.',
            'Blank authored review preparation creates no gold, reviewer identity, or admission.',
            'Original failed RSS peak and its cause were not recorded; recovery observations do not reconstruct them.'],
        numerical_execution_performed=False, model_imports_performed=False,
        semantic_adjudication_performed=False, target_reference_accuracy_claimed=False,
        **FALSE))
    with (HERE / 'audit.json').open('x', encoding='utf-8') as stream:
        json.dump(result, stream, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n')
    print(json.dumps(dict(audit_binding=bind(HERE / 'audit.json'), checked_file_count=len(checked),
        primary_binding_outcomes=counts(primary)['binding_outcome_counts'],
        private_binding_outcomes=counts(private)['binding_outcome_counts'],
        independently_recomputed_assessments=98, review_items=64), sort_keys=True))


if __name__ == '__main__':
    main()
