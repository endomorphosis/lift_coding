"""Authored retention checks; no provider calls or benchmark task data."""
import copy
import importlib.util
import json
from pathlib import Path
import sys

import pytest


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ROOT = Path(__file__).resolve().parent
collector = load(ROOT / 'collect-live-telemetry.py', 'collector')
helper = load(collector.SOURCE / 'ipfs_accelerate_py/agent_supervisor/runtime/codex_interaction_telemetry.py', 'helper')


@pytest.fixture
def authored():
    tokens = {'input_tokens': 100, 'cached_input_tokens': 50, 'output_tokens': 20, 'total_tokens': 120}
    telemetry = helper.build_interaction_telemetry([
        {'type': 'response_item', 'payload': {'type': 'function_call', 'name': 'exec_command',
            'call_id': 'PRIVATE_CALL_ID', 'arguments': 'PRIVATE_COMMAND'}},
        {'type': 'response_item', 'payload': {'type': 'function_call_output',
            'call_id': 'PRIVATE_CALL_ID', 'output': 'PRIVATE_OUTPUT'}},
        {'type': 'event_msg', 'payload': {'type': 'token_count', 'info': {'total_token_usage': tokens}}},
        {'type': 'event_msg', 'payload': {'type': 'task_complete'}},
    ], completed=True, malformed=0)
    invocations = []
    for index, phase in enumerate(('planning', 'coding')):
        invocations.append({'invocation_id': phase, 'phase': phase, 'provider': 'codex_cli',
            'model': 'gpt-6.1-sol', 'status': 'provider_returned', 'model_prompt_sha256': 'a' * 64,
            'native_prompt_sha256': 'a' * 64, 'model_prompt_bytes': 123,
            'native_rollout_usage': {'schema': 'native-codex-cumulative-usage@1',
                'task_complete_observed': True, 'usage_available': True, 'cache_included_in_input': True,
                'thread_id': 'thread-' + phase, 'usage': copy.deepcopy(tokens),
                'rollout_sha256': 'b' * 64, 'interaction_telemetry': copy.deepcopy(telemetry)}})
    report = {'task_completed': True, 'worker_cleanup_returncode': 0, 'remaining_processes': 0,
        'provider_invocations': invocations, 'planning': {'model_request_sha256': 'a' * 64},
        'context_input_audit': {'status': 'verified_all_observed_model_inputs',
            'all_observed_coding_inputs_verified': True, 'read_errors': [],
            'invocations': [{'invocation_id': 'coding', 'status': 'verified_exact_model_input', 'model_input_verified': True}],
            'matches': [{'invocation_id': 'coding', 'model_input_verified': True,
                'model_prompt_sha256': 'a' * 64, 'model_prompt_bytes': 123, 'model_input_checks': {'digest': True}}]}}
    receipt = {'complete_single_trial_receipt': True, 'trial_count': 1, 'harbor_returncode': 0,
        'original_task_inputs_unchanged': True, 'trials': [{'reward': {'reward': 1.0},
            'exception_type': None, 'supervisor': report}]}
    protocol = {'source_commit': collector.SOURCE_HEAD, 'archive_sha256': 'c' * 64,
                'task_input_sha256': {'public': 'd' * 64}, 'model': 'gpt-6.1-sol',
                'reasoning_effort': 'high', 'cli_version': '0.160.0'}
    prepared = {**protocol, 'semantic_context_profile': 'indexed-default@1'}
    return receipt, protocol, prepared, {}


def test_qualified_observations_keep_native_totals_once_and_no_raw_ids(authored):
    result = collector.evaluate(*authored)
    assert result['status'] == 'verified'
    assert result['native_aggregate_usage']['total_tokens'] == 240
    assert result['native_aggregate_usage']['input_tokens'] == 200
    assert result['native_aggregate_usage']['cached_input_tokens'] == 100
    assert result['native_aggregate_usage']['cache_write_input_tokens'] is None
    text = json.dumps(result)
    assert 'PRIVATE_' not in text and 'thread-planning' not in text
    assert result['new_token_savings_comparison'] is False


@pytest.mark.parametrize('mutation', ['usage', 'input_audit', 'official_reward', 'duplicate_native',
                                     'pending_cleanup', 'checkpoint_drift', 'unreceipted', 'planning_digest'])
def test_incomplete_or_conflicting_evidence_cannot_qualify(authored, mutation):
    receipt = authored[0]
    trial = receipt['trials'][0]
    report = trial['supervisor']
    rows = report['provider_invocations']
    if mutation == 'usage': rows[1]['native_rollout_usage']['task_complete_observed'] = False
    elif mutation == 'input_audit': report['context_input_audit']['matches'][0]['model_prompt_bytes'] += 1
    elif mutation == 'official_reward': trial['reward']['reward'] = 0
    elif mutation == 'duplicate_native': rows[1]['native_rollout_usage']['thread_id'] = rows[0]['native_rollout_usage']['thread_id']
    elif mutation == 'pending_cleanup': report['remaining_processes'] = 1
    elif mutation == 'checkpoint_drift': rows[1]['native_rollout_usage']['usage'].update(input_tokens=101, total_tokens=121)
    elif mutation == 'unreceipted': report['unreceipted_provider_attempt'] = {'phase': 'coding'}
    elif mutation == 'planning_digest': report['planning']['model_request_sha256'] = 'f' * 64
    assert collector.evaluate(*authored)['status'] == 'unverified'


@pytest.mark.parametrize('label', ['PRIVATE_TOOL_NAME', ['PRIVATE_TOOL_NAME'], {'PRIVATE_TOOL_NAME': True}])
def test_projection_cannot_export_arbitrary_tool_names_or_unknown_fields(authored, label):
    native = authored[0]['trials'][0]['supervisor']['provider_invocations'][1]['native_rollout_usage']
    telemetry = native['interaction_telemetry']
    telemetry['PRIVATE_TOP_LEVEL'] = 'PRIVATE_OUTPUT'
    telemetry['tool_pairs'][0].update(tool_name=label, raw_output='PRIVATE_OUTPUT', call_id='PRIVATE_ID')
    result = collector.evaluate(*authored)
    assert 'PRIVATE_' not in json.dumps(result)
    assert result['observations'][1]['telemetry']['tool_pairs'][0]['tool_name'] == 'other'


def test_no_retained_receipt_reports_pending_without_source_or_provider_access(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, 'argv', ['collect-live-telemetry.py', '--root', str(tmp_path)])
    monkeypatch.setattr(collector.subprocess, 'check_output', lambda *a, **k: pytest.fail('pending must not execute tools'))
    assert collector.main() == 0
    result = json.loads((tmp_path / 'live-telemetry.json').read_text())
    assert result['status'] == 'pending' and result['observations'] == []
    assert result['provider_calls_by_collector'] == 0


@pytest.mark.parametrize('mutation', ['missing', 'tool_numeric', 'checkpoint_numeric', 'delta', 'oversized'])
def test_invalid_or_missing_telemetry_does_not_qualify(authored, mutation):
    native = authored[0]['trials'][0]['supervisor']['provider_invocations'][1]['native_rollout_usage']
    telemetry = native['interaction_telemetry']
    if mutation == 'missing':
        del native['interaction_telemetry']
    elif mutation == 'tool_numeric':
        telemetry['tool_pairs'][0]['observed_output_bytes'] = 'PRIVATE_NUMERIC_PAYLOAD'
    elif mutation == 'checkpoint_numeric':
        telemetry['token_observations'][0]['record_ordinal'] = True
    elif mutation == 'delta':
        second = copy.deepcopy(telemetry['token_observations'][0])
        second.update(observation_ordinal=2, record_ordinal=5, interval_status='repeated_snapshot',
                      adjacent_counter_delta={'input_tokens': 1, 'cached_input_tokens': 0,
                                              'output_tokens': 1, 'total_tokens': 2})
        telemetry['token_observations'].append(second)
        telemetry['observed_token_checkpoints'] = 2
    elif mutation == 'oversized':
        telemetry['tool_pairs'] *= 129
    result = collector.evaluate(*authored)
    assert result['status'] == 'unverified'
    assert 'PRIVATE_' not in json.dumps(result)
    assert len(result['observations'][1]['telemetry']['tool_pairs']) <= 128


def test_complete_receipt_with_multiple_output_chunks_discloses_incomplete_census(authored):
    telemetry = authored[0]['trials'][0]['supervisor']['provider_invocations'][1]['native_rollout_usage']['interaction_telemetry']
    telemetry['tool_pairs'][0].update(output_event_count=2, pairing_status='multiple_output_chunks_observed')
    telemetry['observed_tool_output_events'] = 2
    telemetry['tool_observations_complete'] = False
    result = collector.evaluate(*authored)
    assert result['status'] == result['receipt_verification_status'] == 'verified'
    assert result['all_observation_censuses_complete'] is False
    observed = result['observations'][1]['telemetry']
    assert observed['counts']['observed_tool_output_events'] == 2
    assert 'some_tool_records_lack_single_call_output_pairing' in observed['limitations']
