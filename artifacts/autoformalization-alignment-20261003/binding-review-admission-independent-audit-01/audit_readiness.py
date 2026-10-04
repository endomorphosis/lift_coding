"""Recompute saved zero-submission recording with bounded stdlib operations."""

import builtins
import hashlib
import json
import stat
import sys
from collections import Counter
from pathlib import Path

ROOT = Path('/home/barberb/lift_coding')
BASE = ROOT / 'artifacts/autoformalization-alignment-20261003'
STAGE = BASE / 'binding-review-admission-01'
HERE = Path(__file__).resolve().parent
REPO = ROOT / 'external/ipfs_datasets'
MAX_BYTES = 16 * 1024 * 1024
FALSE = {name: False for name in (
    'qualified', 'accepted', 'production_admitted', 'independent_fidelity_available',
    'source_fidelity_established', 'source_semantics_verified', 'proof_authority',
    'independent_semantic_review_completed', 'reviewer_identity_authenticated',
    'reviewer_independence_authenticated', 'source_author_independence_authenticated',
    'reviewer_identity_attestations_created', 'reviewer_attestations_created',
    'semantic_gold_created', 'actual_training_or_evaluation_admission')}
MASKS = dict.fromkeys(('weak_decoder_fit', 'strong_semantic_fit', 'contrastive_supervision',
                       'proof_supervision', 'fidelity_evaluation'), 0)
CALLS = dict.fromkeys(('model_calls', 'provider_calls', 'encoder_calls', 'prover_calls'), 0)
ITEM_STATUSES = ('pending', 'single_review', 'agreed_multiple_reviews', 'disputed', 'ambiguous', 'unsupported')
INTERPRETATION_STATUSES = ('normative', 'no_normative_rule', 'ambiguous', 'unsupported')
RECIPE = 'sha256_sorted_compact_utf8_json_no_nan_no_newline'
SKIP = 'mutable_main_plan_historical_reference'
checked = {}


def raw(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                      allow_nan=False).encode('utf-8')


def digest(value):
    return hashlib.sha256(raw(value)).hexdigest()


def text_sha(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def binding(path):
    path = Path(path).resolve()
    checksum, count = hashlib.sha256(), 0
    with path.open('rb') as stream:
        while chunk := stream.read(1024 * 1024):
            checksum.update(chunk)
            count += len(chunk)
    return dict(path=str(path), bytes=count, sha256=checksum.hexdigest())


def verify(reference):
    actual = binding(reference['path'])
    assert actual['sha256'] == reference['sha256'], reference['path']
    assert 'bytes' not in reference or actual['bytes'] == reference['bytes'], reference['path']
    if actual['path'] in checked:
        assert checked[actual['path']] == actual
    checked[actual['path']] = actual
    return actual


def refs(value):
    if type(value) is dict:
        if {'path', 'sha256'} <= set(value):
            verify(value)
        for key, child in value.items():
            if key != SKIP:
                refs(child)
    elif type(value) is list:
        for child in value:
            refs(child)


def unique(pairs):
    result = {}
    for key, value in pairs:
        assert key not in result, key
        result[key] = value
    return result


def nonfinite(value):
    raise ValueError('nonfinite JSON: ' + value)


def read(path, checksum='content_sha256'):
    path = Path(path)
    actual = verify(binding(path))
    assert actual['bytes'] <= MAX_BYTES
    value = json.loads(path.read_bytes().decode('utf-8'), object_pairs_hook=unique, parse_constant=nonfinite)
    raw(value)
    if checksum:
        assert value[checksum] == digest({k: v for k, v in value.items() if k != checksum}), str(path)
    return value


def zero_masks(masks):
    assert type(masks) is dict and masks == MASKS
    assert all(type(value) is int and value == 0 for value in masks.values())


def zero_authority(value):
    assert all(value[key] is False for key in FALSE)


def main():
    report = read(STAGE / 'report_private.json')
    assert binding(STAGE / 'report_private.json')['sha256'] == 'efffb660b7fff05c5a8164a2d2f7f73e039d5dfbb55ac12fb86fda4a0d1f5db9'
    plan = read(STAGE / 'plan.json')
    workflow = read(STAGE / 'recording/report_private.json')
    receipt = read(STAGE / 'recording/receipt_private.json', 'receipt_sha256')
    guide = read(STAGE / 'recording/submission_guide.json', None)
    join_report = read(STAGE / 'packet_joins_private.json')
    for value in (report, plan, workflow, join_report):
        refs(value)
    assert len(report['source_bindings']) == report['preserved_prior_checked_file_count'] == 483
    assert len({r['path'] for r in report['source_bindings']}) == 483
    assert report['source_bindings'] == plan.get('source_bindings', report['source_bindings'])
    assert len(report['new_implementation_test_bindings']) == 5 and len(report['helper_bindings']) == 2
    assert len(workflow['source_bindings']) == 5
    assert all(ref in report['source_bindings'] for ref in report['helper_bindings'])
    assert all(ref in report['source_bindings'] for ref in report['previous_new_owner_test_bindings'])
    assert workflow['source_bindings'] == [
        report['new_implementation_test_bindings'][1], report['new_implementation_test_bindings'][0],
        report['helper_bindings'][1], report['helper_bindings'][0], report['new_implementation_test_bindings'][2]]
    assert report['mutable_main_plan_preservation_required'] is False
    assert report['mutable_main_plan_file_accessed'] is plan['mutable_main_plan_file_accessed'] is False
    packet_ref = workflow['packet_binding']
    packet = read(packet_ref['path'], None)
    organizer_ref = join_report['organizer_manifest_binding']
    organizer = read(organizer_ref['path'])
    assert packet_ref['sha256'] == report['packet_file_sha256'] == '8a8303ea83fe22899f798703e7931b1f48a8aa0afb01c7d6980a7d3e9301701e'
    packet_pin = digest(packet)
    assert packet_pin == report['reviewer_packet_sha256'] == workflow['reviewer_packet_sha256'] == 'a8f465c7950e34ce11f69a5a900d79895f5e19545a2082da75eb9ddf59815655'
    assert packet_pin != packet_ref['sha256']
    assert set(packet) == {'schema', 'instructions', 'items'}
    assert packet['schema'] == 'symbol-binding-source-reviewer/v1'
    assert set(packet['instructions']) == {'task', 'context', 'normative_rules', 'qualifier_scope',
                                           'blank_annotations', 'identity', 'provenance'}
    assert len(packet['items']) == len(organizer['rows']) == 64
    packet_map = {row['item_id']: row for row in packet['items']}
    private_map = {row['item_id']: row for row in organizer['rows']}
    assert len(packet_map) == len(private_map) == 64 and set(packet_map) == set(private_map)
    assert len({row['source_sha256'] for row in packet_map.values()}) == 64
    assert len({row['input_sha256'] for row in packet_map.values()}) == 64
    expected_items, expected_private_joins, expected_receipt_joins = [], [], []
    annotations = {'interpretation_status', 'ambiguity', 'unsupported_meaning', 'normative_rules',
                   'freeform_qualifier_scope', 'notes', 'reviewer_id', 'reviewed_at_utc'}
    groups, splits = Counter(), Counter()
    for identity, row in sorted(packet_map.items()):
        assert set(row) == {'item_id', 'source_text', 'source_sha256', 'input_sha256', 'context', 'annotation'}
        assert set(row['annotation']) == annotations and all(v is None for v in row['annotation'].values())
        assert row['source_sha256'] == text_sha(row['source_text'])
        assert row['context'] == dict(role='none_required', text='', bindings={}, sha256=text_sha(''))
        assert row['input_sha256'] == digest(dict(source_text=row['source_text'], context=row['context']))
        assert identity == 'binding-review-item-' + hashlib.sha256(
            b'authored-binding-review-v1\0' + bytes.fromhex(row['input_sha256'])).hexdigest()[:24]
        envelope = {k: v for k, v in row.items() if k != 'annotation'}
        expected_item = dict(**envelope, review_input_envelope_sha256=digest(envelope), status='pending',
            consensus_interpretation_status=None, complete_declaration_count=0, pending_declaration_count=0,
            meaning_signature_count=0, received_declarations=[], external_adjudication_status='pending',
            independent_adjudication_completed=False, masks=MASKS, **FALSE)
        expected_items.append(expected_item)
        metadata = private_map[identity]
        assert metadata['source_sha256'] == row['source_sha256'] and metadata['input_sha256'] == row['input_sha256']
        assert metadata['review_status'] == 'pending' and metadata['natural_source'] is False
        assert metadata['semantic_gold_created'] is False
        zero_masks(metadata['masks'])
        prefix, actor, pair = metadata['group_id'].split(':')
        assert prefix == 'authored-binding-composition-v1' and actor in '0123' and pair in '0123'
        assert metadata['proposed_split'] == ('proposed_train' if (int(actor) - int(pair)) % 4 in (0, 1)
                                               else 'proposed_development')
        groups[metadata['group_id']] += 1
        splits[metadata['proposed_split']] += 1
        expected_private_joins.append(dict(item_id=identity, source_sha256=row['source_sha256'],
            context_sha256=row['context']['sha256'], input_sha256=row['input_sha256'],
            immutable_envelope_sha256=digest(envelope), group_id=metadata['group_id'],
            proposed_split=metadata['proposed_split'], variant_index=metadata['variant_index'], masks=MASKS,
            blank_annotation=True, review_status='pending'))
        expected_receipt_joins.append(dict(item_id=identity, source_sha256=row['source_sha256'],
            input_sha256=row['input_sha256'], review_input_envelope_sha256=digest(envelope), status='pending', masks=MASKS))
    assert len(groups) == 16 and set(groups.values()) == {4}
    assert splits == {'proposed_train': 32, 'proposed_development': 32}
    assert all({r['variant_index'] for r in expected_private_joins if r['group_id'] == group} == {0, 1, 2, 3}
               for group in groups)
    assert join_report['rows'] == expected_private_joins
    assert report['exact_source_context_input_receipt_joins'] == expected_receipt_joins
    assert report['exact_source_context_input_receipt_join_count'] == 64
    manifest = [{name: row[name] for name in ('item_id', 'source_sha256', 'input_sha256')} for row in expected_items]
    manifest_pin = digest(manifest)
    preparation = dict(schema='canonical-binding-review-packet-validation/v1',
        status='validated_blank_source_only_packet', reviewer_packet_sha256=packet_pin,
        input_manifest_sha256=manifest_pin, item_count=64, digest_recipe=RECIPE,
        input_manifest_order='item_id_sorted', **FALSE)
    expected_receipt = dict(schema='canonical-binding-review-recording/v1', status='pending', organizer_private=True,
        evaluation_role='authored_composition_review_readiness_only', reviewer_packet_sha256=packet_pin,
        input_manifest_sha256=manifest_pin, digest_recipe=RECIPE,
        annotation_helper_owner='ipfs_datasets_py.logic.formalization.autoencoder.alignment_richer_review_admission',
        annotation_helper_names=['_annotation', '_meaning_signature'],
        agreement_scope='exact_complete_declared_meaning_not_semantic_correctness',
        item_count=64, submission_count=0, submissions=[], items=expected_items,
        status_counts={name: 64 if name == 'pending' else 0 for name in ITEM_STATUSES},
        interpretation_status_counts=dict.fromkeys(INTERPRETATION_STATUSES, 0),
        declared_completed_annotation_count=0, human_reviews_authenticated=0, independent_reviews_authenticated=0,
        masks=MASKS, qualified_training_pairs=0, candidate_aware_computation=False,
        authored_reference_scoring_executed=False, reference_used_to_resolve_disputes=False,
        automatic_adjudication=False, training_executed=False, submissions_created=False,
        reviewer_identity_evidence=dict(status='unavailable', authenticated=False),
        source_author_independence_evidence=dict(status='unavailable', authenticated=False),
        reviewer_attestation_evidence=dict(status='unavailable', authenticated=False),
        primary_independently_adjudicated_fidelity=dict(status='unavailable', value=None),
        native_useful_proof_coverage=dict(status='unrun', value=None), **CALLS, **FALSE)
    expected_receipt['receipt_sha256'] = digest(expected_receipt)
    assert raw(receipt) == raw(expected_receipt)
    zero_authority(receipt)
    assert receipt['items'] == expected_items
    for item in receipt['items']:
        zero_authority(item)
        zero_masks(item['masks'])
    expected_validation = dict(schema='canonical-binding-review-validation/v1',
        status='validated_declaration_recording_only', receipt_sha256=receipt['receipt_sha256'],
        reviewer_packet_sha256=packet_pin, input_manifest_sha256=manifest_pin, digest_recipe=RECIPE,
        item_count=64, submission_count=0, status_counts=receipt['status_counts'],
        declared_completed_annotation_count=0, human_reviews_authenticated=0, independent_reviews_authenticated=0,
        masks=MASKS, source_meaning_adjudicated=False, automatic_adjudication=False, training_executed=False,
        submissions_created=False, **CALLS, **FALSE)
    assert workflow['preparation_validation'] == report['packet_preparation_validation'] == preparation
    assert workflow['recording_validation'] == report['saved_recording_validation'] == expected_validation
    assert report['workflow_runs'] == report['saved_receipt_validation_runs'] == 1
    assert workflow['submission_bindings'] == plan['submission_bindings'] == []
    assert workflow['source_only_packet'] is True
    assert workflow['organizer_manifest_accessed'] is workflow['candidate_or_reference_accessed'] is False
    assert report['workflow_organizer_manifest_accessed'] is False
    assert report['wrapper_organizer_manifest_accessed_for_private_joins'] is True
    assert report['group_and_split_metadata_supplied_to_recording_api'] is False
    assert report['candidate_reference_payloads_supplied_to_recording'] is False
    assert report['independent_blind_quality_study'] is False
    assert report['query_reference_used_to_establish_meaning'] is False
    assert report['natural_source_corpus'] is report['sealed_final_test_created'] is False
    assert report['previously_exposed_compositions_possible'] is True
    assert workflow['complete_dependency_manifest'] is False
    assert all(type(report[name]) is int and report[name] == 0 for name in (
        *CALLS, 'optimizer_updates', 'profile_fit_calls', 'candidate_redecoding_calls', 'submission_count',
        'actual_reviews_created', 'adjudications_completed', 'human_reviews_authenticated',
        'independent_reviews_authenticated', 'declared_completed_annotation_count'))
    assert report['model_import_attempts'] == report['model_execution_stacks_loaded'] == []
    assert report['blank_original_annotation_count'] == report['input_item_count'] == 64
    assert report['all320_organizer_draft_mask_values_zero'] is report['all320_receipt_mask_values_zero'] is True
    journal = [json.loads(line) for line in Path(report['resource_journal_binding']['path']).read_text().splitlines()]
    assert journal == report['resource_observations'] and len(journal) == 25
    assert all(0 <= row['elapsed_wall_seconds'] < 60 for row in journal)
    assert all(a['elapsed_wall_seconds'] <= b['elapsed_wall_seconds'] for a, b in zip(journal, journal[1:], strict=False))
    assert all(0 < row[name] < 524288 for row in journal for name in
               ('resource_ru_maxrss_kib', 'linux_current_rss_kib', 'linux_peak_hwm_kib'))
    assert report['worker_resource_ru_maxrss_kib'] == 26140
    assert report['worker_linux_peak_hwm_kib'] == 27340
    assert report['wall_seconds'] < 60 and report['cpu_seconds'] < 60
    assert report['resource_measurement_scope'] == 'fresh_forked_static_worker'
    for directory in (STAGE, STAGE / 'recording'):
        assert stat.S_IMODE(directory.stat().st_mode) == 0o700
    stage_files = [path for path in STAGE.rglob('*') if path.is_file()]
    assert len(stage_files) == 7
    assert all(stat.S_IMODE(path.stat().st_mode) == 0o600 for path in stage_files)
    original_import = builtins.__import__
    forbidden = {'torch', 'numpy', 'spacy', 'transformers', 'sentence_transformers',
                 'tensorflow', 'jax', 'requests', 'httpx', 'openai', 'z3', 'cvc5'}

    def guarded(name, *args, **kwargs):
        assert name.split('.')[0] not in forbidden, name
        return original_import(name, *args, **kwargs)

    builtins.__import__ = guarded
    sys.path.insert(0, str(REPO))
    from ipfs_datasets_py.logic.legal_ir import canonical_binding_review as adapter

    assert Path(adapter.__file__).resolve() == REPO / 'ipfs_datasets_py/logic/legal_ir/canonical_binding_review.py'
    assert adapter.validate_blank_packet(packet, expected_packet_sha256=packet_pin) == preparation
    assert adapter.validate_recording(receipt, packet, [], expected_packet_sha256=packet_pin) == expected_validation
    assert adapter.submission_guide() == guide
    zero_authority(guide)
    assert guide['generated_reviews'] == 0 and guide['training_executed'] is False
    guide_text = raw(guide).decode('utf-8')
    assert all(row['source_text'] not in guide_text for row in packet['items'])
    assert all(value not in guide_text for value in groups)
    assert all(value not in guide_text for value in splits)
    assert report['public_guide_contains_candidates_or_source_specific_answers'] is False
    assert report['public_guide_contains_private_group_split_values'] is False
    assert not any(name.split('.')[0] in forbidden for name in sys.modules)
    verify(binding(__file__))
    result = dict(schema='binding-review-admission-independent-stdlib-audit/v1', status='passed',
        audit_runner_binding=binding(__file__), outer_report_binding=binding(STAGE / 'report_private.json'),
        workflow_report_binding=binding(STAGE / 'recording/report_private.json'),
        receipt_binding=binding(STAGE / 'recording/receipt_private.json'), guide_binding=binding(STAGE / 'recording/submission_guide.json'),
        checked_file_count=len(checked), checked_file_bindings=sorted(checked.values(), key=lambda r: r['path']),
        prior483_verified=True, explicit_new_owner_test_pin_count=5, unchanged_helper_pin_count=2,
        mutable_main_plan_historical_key_exempted=SKIP, mutable_main_plan_file_read=False,
        exact_independent_full_receipt_reconstruction=True, public_validator_replay_runs=1,
        packet_file_sha256=packet_ref['sha256'], canonical_packet_sha256=packet_pin,
        input_manifest_sha256=manifest_pin, receipt_sha256=receipt['receipt_sha256'],
        exact_source_context_input_join_count=64, blank_annotation_cell_count=512,
        item_count=64, pending_items=64, submitted_payloads=0, complete_declarations=0,
        receipt_zero_mask_values=320, organizer_draft_zero_mask_values=320,
        group_count=16, variants_per_group=4, proposed_split_counts=dict(splits),
        recording_workflow_private_permissions_verified=True, all_seven_stage_files_private=True,
        guide_replayed_exactly=True, guide_source_specific_answers_or_private_group_split_values=False,
        wrapper_organizer_parse_for_private_joins=True, workflow_organizer_or_candidate_reference_inputs=False,
        preservation_stream_hashing_can_read_saved_candidate_bytes=True,
        saved_candidate_deserialization_for_recording=False, query_reference_use_to_establish_meaning=False,
        model_imports_or_numerical_execution_performed=False, model_calls=0, encoder_calls=0, prover_calls=0,
        resource_journal_snapshots=25, worker_ru_maxrss_kib=26140, worker_Linux_HWM_kib=27340,
        preserved_parent_launch_accounting_scope='outside_fresh_worker_measurement_not_independent_cause_attestation',
        audit_scope='source_packet_integrity_and_zero_submission_workflow_readiness_not_human_review_or_semantic_admission',
        independent_blind_quality_study=False, source_meaning_adjudicated=False,
        human_reviews_authenticated=0, independent_reviews_authenticated=0, **FALSE)
    result['content_sha256'] = digest(result)
    with (HERE / 'audit.json').open('x', encoding='utf-8') as stream:
        json.dump(result, stream, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n')
    print(json.dumps(dict(audit_binding=binding(HERE / 'audit.json'), checked_file_count=len(checked),
        pending_items=64, submissions=0, source_joins=64, mask_values_zero=320), sort_keys=True))


if __name__ == '__main__':
    main()
