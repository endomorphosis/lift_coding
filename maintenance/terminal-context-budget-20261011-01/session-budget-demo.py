#!/usr/bin/env python3
"""Scalar-only demonstration over synthetic records; never read transcripts."""
from pathlib import Path
import hashlib
import json
import sys

C = Path('/home/barberb/lift_coding/maintenance/terminal-token-reduction-20261007-01/checkout')
H = Path('/home/barberb/lift_coding/maintenance/terminal-context-budget-20261011-01')
module = C / 'ipfs_accelerate_py/agent_supervisor/runtime/session_budget_ledger.py'
raw = module.read_bytes()
source_sha = hashlib.sha256(raw).hexdigest()
sys.path.insert(0, str(C))
from ipfs_accelerate_py.agent_supervisor.runtime.session_budget_ledger import build_session_budget_ledger


def usage(inputs, outputs, cached, reasoning):
    return {'type': 'event_msg', 'payload': {'type': 'token_count', 'info': {
        'total_token_usage': {'input_tokens': inputs, 'output_tokens': outputs,
            'total_tokens': inputs + outputs, 'cached_input_tokens': cached,
            'reasoning_output_tokens': reasoning}}}}


def call(identity, arguments):
    return {'type': 'response_item', 'payload': {
        'type': 'function_call', 'call_id': identity, 'arguments': arguments}}


def output(identity, value):
    return {'type': 'response_item', 'payload': {
        'type': 'function_call_output', 'call_id': identity, 'output': value}}


before, after = usage(10_000, 100, 7500, 30), usage(22_000, 250, 14_000, 90)
records = [before, call('synthetic-a', '{"limit":256}'), output('synthetic-a', 'x' * 65_536),
           call('synthetic-b', '{}'), output('synthetic-b', '\u03bb' * 1000), after,
           {'type': 'event_msg', 'payload': {'type': 'task_complete'}}]
ledger = build_session_budget_ledger(records, completed=True, malformed=0)
assert ledger['observed_known_output_utf8_bytes'] == 67_536
assert ledger['observed_max_output_utf8_bytes'] == 65_536
assert ledger['complete_tool_call_events'] == ledger['complete_tool_output_events'] == 2
assert ledger['primary_usage_complete'] and not ledger['all_counter_fields_complete']
assert ledger['latest_usage']['cache_write_input_tokens'] is None
assert ledger['latest_usage']['total_tokens'] == 22_250
assert ledger['usage_checkpoints'][1]['delta']['total_tokens'] == 12_150
assert ledger['verified_model_turn_count'] is ledger['individual_tool_output_tokens'] is None
unmatched = build_session_budget_ledger([call('synthetic-missing', '{}'), after], completed=True, malformed=0)
assert not unmatched['tool_census_complete'] and unmatched['complete_tool_output_events'] is None
assert unmatched['observed_tool_call_events'] == 1
regressed = build_session_budget_ledger([after, before], completed=True, malformed=0)
assert regressed['usage_regression_intervals'] == 1 and not regressed['primary_usage_complete']
assert all(value is None for value in regressed['usage_checkpoints'][1]['delta'].values())
bad = usage(22_000, 250, 22_001, 90)
inconsistent = build_session_budget_ledger([before, bad], completed=True, malformed=0)
assert all(value is None for value in inconsistent['latest_usage'].values())
assert inconsistent['usage_consistency_mismatch_records'] == 1
malformed = build_session_budget_ledger([{'type': []}, after], completed=True, malformed=0)
assert malformed['unclassified_records'] == 1 and not malformed['primary_usage_complete']
assert module.read_bytes() == raw
result = {'schema': 'session-budget-synthetic-demonstration@1', 'fixture_kind': 'synthetic_only',
    'provider_calls': 0, 'native_rollout_files_read': 0, 'raw_tool_data_exported': False,
    'ledger_source': {'path': str(module), 'sha256': source_sha, 'bytes': len(raw)},
    'ledger': ledger, 'negative_controls': {'unmatched_ids_remain_unknown': True,
        'regressed_delta_refused': True, 'inconsistent_usage_refused': True,
        'malformed_type_remains_unknown': True},
    'interpretation': 'The final observed total is 22250, not the sum of two cumulative checkpoints or total plus cached/reasoning subsets. Tool output is 67536 recorded UTF-8 bytes; its native tokens and model-turn count remain unknown.'}
destination = H / 'session-budget-demo.json'
with destination.open('x') as stream:
    json.dump(result, stream, sort_keys=True, indent=2)
    stream.write('\n')
print(json.dumps({'output': str(destination), 'latest_total_tokens': 22_250,
                  'recorded_tool_output_bytes': 67_536, 'primary_usage_complete': True,
                  'all_counter_fields_complete': False, 'negative_controls_passed': 4}, sort_keys=True))
