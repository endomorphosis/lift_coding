"""Authored report-consistency controls; no receipt origin or owner attestation.

Fixtures below declare a complete fault shape only to exercise its checker.
No native fault process is run and no such fixture is published as evidence.
Actual origin requires the runner's retained producer/process integrity checks.
"""
from copy import deepcopy
import json

import pytest

import packing_verify as subject
from packing_io import FALSE, sha, wire
from test_packing_integration import authored_closed_result

TASKS = ('headless-terminal', 'llm-inference-batching-scheduler',
         'feal-differential-cryptanalysis', 'break-filter-js-from-html')
CONTROLS = {
    'rechecksummed_promoted_provider_claim': 'ReferenceCodecError',
    'rechecksummed_changed_decoded_hash': 'ReferenceCodecError',
    'reencoded_changed_lift_slot_hash': 'NestedContextError',
    'reencoded_changed_full_instruction': 'NestedContextError',
    'reencoded_weakened_native_requiredness': 'NestedContextError',
    'reencoded_changed_restoration_guidance': 'NestedContextError',
    'caller_context_changed_after_packing': 'ValueError',
}


@pytest.fixture
def declared_receipt():
    from ipfs_datasets_py.duckdb_control.codebase_catalog import CodebaseHead
    from ipfs_datasets_py.logic.software_contracts.content import cid_for_structured
    repository = 'authored-report-fixture-no-owner-attestation'
    snapshot = cid_for_structured({'fixture': 'snapshot data only'})
    head = CodebaseHead(repository_id=repository, generation=1,
        manifest_cid=cid_for_structured({'fixture': 'manifest data only'}), snapshot_cid=snapshot,
        ast_revision_id=f'rev:{repository}:snapshot:{snapshot}',
        receipt_cid=cid_for_structured({'fixture': 'receipt spelling only'})).to_dict()
    result = authored_closed_result()
    result['native_head'] = deepcopy(head)
    result['artifact_pins'] = [{'relative_path': name, 'bytes': 17, 'sha256': '0' * 64}
                               for name in sorted(subject.FILES)]
    raw_result = wire(result)
    # Cold caller supplies the directory join separately from immutable result.
    result['selected_run'] = 'authored-report-fixture'
    fault = {'schema': 'terminal-reference-packing-fault-controls@1', 'qualified': True,
        'selected_run': result['selected_run'], 'selected_result_sha256': sha(raw_result),
        'native_head': deepcopy(head), 'selected_artifact_pins_sha256': sha(wire(result['artifact_pins'])),
        'packet_controls': [{
            'task_id': task, 'positive_byte_exact_variants': 3,
            'controls': [{'control': control, 'refused': True, 'error_class': error_class,
                'message': 'Authored diagnostic fixture; no actual fault observed.', **FALSE}
                for control, error_class in CONTROLS.items()],
            'codec_processes_are_pure_data': True, **FALSE} for task in TASKS],
        'native_owner_controls': {
            'native_entry_observation_passed': True, 'mutation_inside_callback': True,
            'private_provisional_candidate_created': True, 'candidate_returned_to_caller': False,
            'stale_source_exit_error_class': 'StaleCodebaseError',
            'stale_source_exit_error_message': 'Authored diagnostic fixture; no owner observed.',
            'exact_original_source_restored': True, 'baseline_native_owner_reobserved_after_restore': True,
            'wrong_full_head_error_class': 'StaleCodebaseError',
            'wrong_full_head_error_message': 'Authored diagnostic fixture; no owner observed.',
            'wrong_full_head_callback_entered': False, 'native_head_unchanged': deepcopy(head),
            'owner_head_update_performed': False, **FALSE},
        'pure_packet_negative_controls': 28, 'positive_exact_variant_roundtrips': 12,
        'selected_run_artifacts_unchanged': True, 'source_body_execution': False,
        'provider_invocations': 0, 'optimizer_updates': 0, 'prover_invocations': 0, **FALSE}
    return fault, result, raw_result


def validate(data):
    fault, result, raw = data
    return subject.validate_fault_report(fault, result=result, result_raw=raw)


def test_complete_authored_shape_establishes_consistency_only(declared_receipt):
    assert validate(declared_receipt) is None
    fault, result, raw = declared_receipt
    assert subject.validate_fault_report(json.loads(wire(fault)), result=result, result_raw=raw) is None
    assert all(fault[name] is False for name in FALSE)
    assert 'origin_authenticated' not in fault


@pytest.mark.parametrize('damage', ['extra_top', 'missing_top', 'unqualified', 'wrong_schema', 'wrong_run',
    'wrong_result', 'wrong_head', 'wrong_artifact_pins', 'changed_run_artifact', 'source_execution',
    'missing_task', 'extra_task', 'foreign_task', 'duplicate_task', 'extra_packet', 'missing_packet',
    'packet_positive', 'packet_positive_bool', 'not_pure_data', 'missing_control', 'extra_control',
    'foreign_control', 'duplicate_control', 'control_not_refused', 'control_refused_one', 'wrong_error_class',
    'missing_control_field', 'extra_control_field', 'empty_diagnostic', 'oversize_diagnostic',
    'extra_owner', 'missing_owner', 'source_exit_wrong_error', 'head_entry_wrong_error',
    'owner_source_empty_diagnostic', 'owner_head_empty_diagnostic', 'owner_head_changed',
    'owner_head_bool_generation', 'head_ast_revision', 'head_bool_generation', 'head_missing_receipt'])
def test_incomplete_or_rebound_declared_fault_scope_refuses(declared_receipt, damage):
    fault, result, raw = declared_receipt
    packet, owner = fault['packet_controls'][0], fault['native_owner_controls']
    control = packet['controls'][0]
    if damage == 'extra_top': fault['invented_origin_attestation'] = True
    elif damage == 'missing_top': fault.pop('packet_controls')
    elif damage == 'unqualified': fault['qualified'] = False
    elif damage == 'wrong_schema': fault['schema'] = 'invented-fault-receipt@1'
    elif damage == 'wrong_run': fault['selected_run'] = 'other-run'
    elif damage == 'wrong_result': fault['selected_result_sha256'] = '0' * 64
    elif damage == 'wrong_head': fault['native_head']['generation'] += 1
    elif damage == 'wrong_artifact_pins': fault['selected_artifact_pins_sha256'] = '0' * 64
    elif damage == 'changed_run_artifact': fault['selected_run_artifacts_unchanged'] = False
    elif damage == 'source_execution': fault['source_body_execution'] = True
    elif damage == 'missing_task': fault['packet_controls'].pop()
    elif damage == 'extra_task': fault['packet_controls'].append(deepcopy(packet))
    elif damage == 'foreign_task': packet['task_id'] = 'unseen-private-task'
    elif damage == 'duplicate_task': fault['packet_controls'][1]['task_id'] = packet['task_id']
    elif damage == 'extra_packet': packet['unseen_complete_task'] = True
    elif damage == 'missing_packet': packet.pop('codec_processes_are_pure_data')
    elif damage == 'packet_positive': packet['positive_byte_exact_variants'] = 2
    elif damage == 'packet_positive_bool': packet['positive_byte_exact_variants'] = True
    elif damage == 'not_pure_data': packet['codec_processes_are_pure_data'] = False
    elif damage == 'missing_control': packet['controls'].pop()
    elif damage == 'extra_control': packet['controls'].append(deepcopy(control))
    elif damage == 'foreign_control': control['control'] = 'unobserved-new-proof'
    elif damage == 'duplicate_control': packet['controls'][1]['control'] = control['control']
    elif damage == 'control_not_refused': control['refused'] = False
    elif damage == 'control_refused_one': control['refused'] = 1
    elif damage == 'wrong_error_class': control['error_class'] = 'OSError'
    elif damage == 'missing_control_field': control.pop('message')
    elif damage == 'extra_control_field': control['authenticated_provider_receipt'] = True
    elif damage == 'empty_diagnostic': control['message'] = ''
    elif damage == 'oversize_diagnostic': control['message'] = 'x' * 4097
    elif damage == 'extra_owner': owner['owner_receipt_authenticated'] = True
    elif damage == 'missing_owner': owner.pop('mutation_inside_callback')
    elif damage == 'source_exit_wrong_error': owner['stale_source_exit_error_class'] = 'LeaseTimeoutError'
    elif damage == 'head_entry_wrong_error': owner['wrong_full_head_error_class'] = 'LeaseCancelledError'
    elif damage == 'owner_source_empty_diagnostic': owner['stale_source_exit_error_message'] = ''
    elif damage == 'owner_head_empty_diagnostic': owner['wrong_full_head_error_message'] = ''
    elif damage == 'owner_head_changed': owner['native_head_unchanged']['generation'] += 1
    elif damage == 'owner_head_bool_generation': owner['native_head_unchanged']['generation'] = True
    elif damage in {'head_ast_revision', 'head_bool_generation', 'head_missing_receipt'}:
        # Rebind both dictionaries to exercise typed-head validation after the
        # early exact result/head join, not merely mismatched input rejection.
        if damage == 'head_ast_revision': fault['native_head']['ast_revision_id'] = 'rev:unbound-snapshot'
        elif damage == 'head_bool_generation': fault['native_head']['generation'] = True
        else: fault['native_head'].pop('receipt_cid')
        result['native_head'] = deepcopy(fault['native_head'])
    with pytest.raises(ValueError):
        validate(declared_receipt)


@pytest.mark.parametrize('key', ['pure_packet_negative_controls', 'positive_exact_variant_roundtrips',
                               'provider_invocations', 'optimizer_updates', 'prover_invocations'])
@pytest.mark.parametrize('value', [True, 0.0, -1, 999])
def test_exact_integer_fault_counters_cannot_be_substituted(declared_receipt, key, value):
    fault, _, _ = declared_receipt
    fault[key] = value
    with pytest.raises(ValueError, match='counters'):
        validate(declared_receipt)


@pytest.mark.parametrize('location', ['top', 'packet', 'control', 'owner'])
@pytest.mark.parametrize('key', list(FALSE))
def test_every_nested_false_authority_flag_requires_exact_false(declared_receipt, location, key):
    fault, _, _ = declared_receipt
    targets = {'top': fault, 'packet': fault['packet_controls'][0],
               'control': fault['packet_controls'][0]['controls'][0], 'owner': fault['native_owner_controls']}
    targets[location][key] = 0
    with pytest.raises(ValueError, match='authority'):
        validate(declared_receipt)


@pytest.mark.parametrize('key', ['native_entry_observation_passed', 'mutation_inside_callback',
    'private_provisional_candidate_created', 'exact_original_source_restored',
    'baseline_native_owner_reobserved_after_restore'])
def test_native_entry_exit_restore_declarations_cannot_be_omitted_or_weakened(declared_receipt, key):
    fault, _, _ = declared_receipt
    fault['native_owner_controls'][key] = False
    with pytest.raises(ValueError, match='entry/exit'):
        validate(declared_receipt)


@pytest.mark.parametrize('key', ['candidate_returned_to_caller', 'wrong_full_head_callback_entered',
                                'owner_head_update_performed'])
def test_candidate_escape_and_head_mutation_are_disallowed(declared_receipt, key):
    fault, _, _ = declared_receipt
    fault['native_owner_controls'][key] = True
    with pytest.raises(ValueError, match='escaped'):
        validate(declared_receipt)


def test_precondition_preserves_early_wrong_result_join_for_minimal_report(tmp_path, monkeypatch):
    monkeypatch.setattr(subject, 'ROOT', tmp_path)
    minimal = {'schema': 'terminal-reference-packing-fault-controls@1', 'qualified': True,
        'selected_run': 'authored-run', 'selected_result_sha256': '0' * 64}
    (tmp_path/'fault.json').write_bytes(wire(minimal))
    with pytest.raises(ValueError, match='exact result'):
        subject.fault_precondition('fault.json', {'selected_run': 'authored-run', 'native_head': {'generation': 1}},
                                   b'authored result')


def test_minimal_same_result_flags_are_insufficient_for_positive_precondition(declared_receipt):
    fault, result, raw = declared_receipt
    minimal = {key: fault[key] for key in ('schema', 'qualified', 'selected_run', 'selected_result_sha256', 'native_head')}
    minimal.update(FALSE)
    with pytest.raises(ValueError, match='closed'):
        subject.validate_fault_report(minimal, result=result, result_raw=raw)


def test_canonical_fault_report_bytes_are_pinned_without_origin_claim(declared_receipt, tmp_path, monkeypatch):
    monkeypatch.setattr(subject, 'ROOT', tmp_path)
    fault, result, raw_result = declared_receipt
    raw = wire(fault)
    (tmp_path/'fault.json').write_bytes(raw)
    acquired, pin = subject.fault_precondition('fault.json', result, raw_result)
    assert acquired == raw and pin == {'relative_path': 'fault.json', 'bytes': len(raw), 'sha256': sha(raw)}
    assert set(pin) == {'relative_path', 'bytes', 'sha256'}
    (tmp_path/'fault.json').write_bytes(raw + b'\n')
    with pytest.raises(ValueError, match='canonical'):
        subject.fault_precondition('fault.json', result, raw_result)
    # Duplicate keys never become a new canonical receipt through json.loads.
    (tmp_path/'fault.json').write_bytes(raw[:-1] + b',"qualified":true}')
    with pytest.raises(ValueError, match='canonical'):
        subject.fault_precondition('fault.json', result, raw_result)
