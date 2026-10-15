"""Export a verified, single-trial telemetry qualification and parser benchmark."""
import csv
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent
SOURCE = Path('/home/barberb/lift_coding_worktrees/indexed-worker-context-20261011')


def read(name):
    return json.loads((ROOT / name).read_text())


def main():
    live = read('live-telemetry.json')
    resources = read('resource-observations.json')
    overhead = read('overhead.json')
    validation = read('source-validation.json')
    receipt = read('trials/mjcf-telemetry-01/receipt.json')
    head = subprocess.check_output(['git', '-C', str(SOURCE), 'rev-parse', 'HEAD'], text=True).strip()
    assert head == live['source_commit'] == validation['source_commit'] == overhead['active_source_head_at_start']
    assert not subprocess.check_output(['git', '-C', str(SOURCE), 'status', '--porcelain'], text=True).strip()
    assert live['status'] == live['receipt_verification_status'] == 'verified'
    assert live['all_observation_censuses_complete'] is True
    assert live['native_aggregate_usage_complete'] is True
    assert resources['all_owned_trial_containers_absent_after_completion'] is True
    assert (ROOT / 'collector-tests.log').read_text().rstrip().endswith('19 passed in 0.07s')
    trial = receipt['trials'][0]
    assert trial['reward']['reward'] == 1.0
    phases = []
    for item in live['observations']:
        telemetry = item['telemetry']
        pairs = telemetry['tool_pairs']
        assert telemetry['census_complete'] and telemetry['adjacent_deltas_independently_checked']
        assert all(type(pair['input_bytes']) is int and type(pair['observed_output_bytes']) is int for pair in pairs)
        total_output = sum(pair['observed_output_bytes'] for pair in pairs)
        largest = sorted(pairs, key=lambda pair: pair['observed_output_bytes'], reverse=True)[:3]
        phases.append({
            'phase': item['phase'], 'native_usage': item['native_usage'],
            'uncached_input_tokens': item['native_usage']['input_tokens'] - item['native_usage']['cached_input_tokens'],
            'model_prompt_bytes': item['model_prompt_bytes'],
            'observed_tool_call_events': telemetry['counts']['observed_tool_call_events'],
            'observed_token_checkpoints': telemetry['counts']['observed_token_checkpoints'],
            'tool_input_bytes': sum(pair['input_bytes'] for pair in pairs),
            'tool_output_bytes': total_output,
            'unknown_tool_category_count': sum(pair['tool_name'] == 'other' for pair in pairs),
            'tool_pairs_with_known_structured_exit_status': sum(pair['structured_exit_code'] is not None for pair in pairs),
            'largest_three_output_observation_ordinals': [pair['observation_ordinal'] for pair in largest],
            'largest_three_output_byte_share': sum(pair['observed_output_bytes'] for pair in largest) / total_output if total_output else None,
            'limitations': telemetry['limitations'],
        })
    report = {
        'schema': 'terminal-interaction-telemetry-benchmark@1', 'source_commit': head,
        'qualification': 'single fresh full-supervisor tune-mjcf task',
        'official_reward': 1.0, 'default_telemetry_enabled': True,
        'experimental_prompt_change': False, 'new_token_savings_comparison': False,
        'semantic_context_profile': 'indexed-default@1', 'semantic_metadata_view': 'legacy',
        'regression_tests_passed': validation['tests_passed'], 'collector_tests_passed': 19,
        'archive_sha256': read('comparison-protocol.json')['archive_sha256'],
        'phases': phases, 'native_aggregate_usage': live['native_aggregate_usage'],
        'native_aggregate_uncached_input_tokens': live['native_aggregate_usage']['input_tokens'] - live['native_aggregate_usage']['cached_input_tokens'],
        'durations_seconds': trial['durations_seconds'],
        'invocation_seconds': receipt['invocation_seconds'],
        'all_observation_censuses_complete': True,
        'resource_observations': {
            'sampled': resources['aggregate_sampled_resources'],
            'pressure_events': resources['pressure_events'], 'backoff_events': resources['backoff_events'],
            'owned_trial_containers_absent_after_completion': True,
            'outside_pressure_injection_performed': False,
        },
        'parser_overhead_authored_cases': [{
            'case': case['case'], 'fixture_bytes': case['fixture']['bytes'],
            'old_median_seconds_with_tracemalloc': case['old']['median_wall_seconds_with_tracemalloc'],
            'new_median_seconds_with_tracemalloc': case['new']['median_wall_seconds_with_tracemalloc'],
            'telemetry_bytes': case['new']['serialized_telemetry_bytes'],
            'native_aggregate_unchanged': case['native_aggregate_unchanged'],
        } for case in overhead['cases']],
        'interpretation': [
            'This run qualifies passive telemetry and official task success, not a token-saving intervention.',
            'Cached input is a subset of input tokens; native counters are not verified billing totals.',
            'The first cumulative observation has an unknown counter origin; checkpoint counts are not provider request counts.',
            'Tool-output sizes are decoded bytes; interval token deltas do not causally attribute tokens to an output.',
            'The three largest coding outputs dominate observed output bytes; content value and safe reduction remain untested.',
            'All seven live tool names were outside the fixed allowlist and exported as other; per-tool categories remain unknown.',
            'String outputs have no structured exit status; recorded observation elapsed times are not tool execution latency.',
            'No outside-pressure injection was performed; this live run does not establish backoff behavior under load.',
        ],
        'next_experiment': 'Evaluate bounded, task-relevant tool-output summaries with exact replayable full-output references; retain an unchanged control, repeat trials, and require official task success before claiming savings.',
    }
    evidence = ['live-telemetry.json', 'resource-observations.json', 'overhead.json',
                'source-validation.json', 'source-validation.log', 'collector-tests.log',
                'passive-dataflow-audit.json', 'comparison-protocol.json',
                'runtime-archive-v1/verification.json']
    report['evidence_sha256'] = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in evidence}
    with (ROOT / 'benchmark.json').open('x') as stream:
        json.dump(report, stream, indent=2, sort_keys=True)
        stream.write('\n')
    with (ROOT / 'benchmark.csv').open('x', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=['phase', 'input_tokens', 'cached_input_tokens',
            'uncached_input_tokens', 'output_tokens', 'total_tokens', 'observed_tool_call_events',
            'observed_token_checkpoints', 'tool_input_bytes', 'tool_output_bytes'])
        writer.writeheader()
        for phase in phases:
            values = {**phase['native_usage'], **phase}
            writer.writerow({key: values[key] for key in writer.fieldnames})
    print(json.dumps({'benchmark': str(ROOT / 'benchmark.json'), 'official_reward': 1.0,
                      'regression_tests_passed': 308, 'collector_tests_passed': 19,
                      'native_total_tokens': live['native_aggregate_usage']['total_tokens']}))


if __name__ == '__main__':
    main()
