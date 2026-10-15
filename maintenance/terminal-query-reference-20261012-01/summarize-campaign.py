"""Summarize finalized structured evidence without provider transcripts or task code."""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent


def read(relative):
    path = ROOT / relative
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 64 * 1024**2:
        raise ValueError('bounded regular structured evidence required')
    return json.loads(path.read_bytes())


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    live = read('live-comparison.json')
    frozen = read('source-bindings.json')
    protocol = read('comparison-protocol.json')
    offline = read('offline-summary.json')
    if {row['name'] for row in live['trials']} != {row['name'] for row in protocol['trials']}:
        raise ValueError('requested trial population changed')
    if any(row['state'] in ('unstarted', 'running_or_unresolved', 'claimed_without_observed_process') for row in live['trials']):
        raise ValueError('campaign still has unresolved requested trials')
    pairs = []
    dispatches, deployments, samples, events = [], [], [], []
    provider_calls = 0
    for task in sorted({row['task'] for row in live['trials']}):
        rows = {row['requested_arm']: row for row in live['trials'] if row['task'] == task}
        if set(rows) != {'legacy', 'required-instruction-ref@1'}:
            raise ValueError('exact paired population required')
        baseline, reference = rows['legacy'], rows['required-instruction-ref@1']
        before = baseline['native_usage']['complete_total_tokens']
        after = reference['native_usage']['complete_total_tokens']
        known = before is not None and after is not None
        pairs.append({'task': task, 'baseline_total_tokens': before, 'reference_total_tokens': after,
            'total_tokens_change': after - before if known else None,
            'total_tokens_change_percent': 100 * (after - before) / before if known and before else None,
            'baseline_official_reward': baseline['official_reward'],
            'reference_official_reward': reference['official_reward'],
            'reference_input_observed': reference['effective_reference_input_observed'],
            'repeats_per_arm': 1, 'causal_improvement_established': False})
    for requested in protocol['trials']:
        name = requested['name']
        receipt = read(f'trials/{name}/receipt.json')
        row = receipt['trials'][0]
        outcome = read(f'launcher-state/{name}/outcome.json')
        usage = outcome.get('supervisor_usage') or {}
        observed_calls = usage.get('provider_calls')
        if type(observed_calls) is not int or observed_calls < 0:
            raise ValueError('explicit observed provider call population required')
        provider_calls += observed_calls
        for invocation in row.get('supervisor', {}).get('provider_invocations', []):
            if invocation.get('phase') != 'coding':
                continue
            binding = invocation.get('query_reference_view') or {}
            dispatches.append({'trial': name, 'model_prompt_bytes': invocation.get('model_prompt_bytes'),
                'reference_selected': invocation.get('query_reference_selected'),
                'reference_provider_attempted': invocation.get('query_reference_provider_attempted'),
                'reference_dispatched': invocation.get('query_reference_dispatched'),
                'within_input_codec_bytes_saved': binding.get('byte_savings'),
                'query_literal_bytes': binding.get('query_bytes'),
                'exact_input_audit': row.get('supervisor', {}).get('context_input_audit', {}).get('status')})
        for path in (ROOT / 'trials' / name).glob('jobs/*/*/agent/deployment/deployment.json'):
            value = read(path.relative_to(ROOT))
            deployments.append({'trial': name, 'qualified': value.get('qualified'),
                'archive_sha256': value.get('archive_sha256'), 'codex_installed': value.get('codex_installed'),
                'credential_contents_recorded': value.get('credential_contents_recorded'),
                'seconds': value.get('seconds')})
        path = ROOT / 'launcher-state' / name / 'events.jsonl'
        for line in path.read_text().splitlines():
            value = json.loads(line)
            events.append(value)
            if isinstance(value.get('sample'), dict):
                samples.append(value['sample'])
    source = Path(frozen['source'])
    head = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
    clean = not subprocess.check_output(['git', '-C', str(source), 'status', '--porcelain'], text=True).strip()
    source_matches = head == frozen['source_commit'] and all(digest(source / name) == sha for name, sha in frozen['files'].items())
    archive_matches = digest(ROOT / 'runtime-archive-v1/runtime.tar.gz') == protocol['archive_sha256']
    if not clean or not source_matches or not archive_matches:
        raise ValueError('frozen campaign source or archive changed')
    resources = [json.loads(line) for line in (ROOT / 'container-resource-observations.jsonl').read_text().splitlines()]
    if {row['trial'] for row in resources} != {row['name'] for row in protocol['trials']}:
        raise ValueError('all four owned container limits must be observed')
    result = {'schema': 'terminal-query-reference-campaign-summary@1',
        'source_commit': head, 'source_path': str(source), 'source_clean': clean,
        'frozen_source_files_match': source_matches, 'archive_sha256': protocol['archive_sha256'],
        'archive_digest_still_matches': archive_matches, 'publication': 'local commit only',
        'repository_tests_passed': frozen['repository_test_cases_passed'], 'campaign_utility_tests_passed': 17,
        'live_pairs': pairs, 'native_arms': live['arms'], 'coding_inputs': dispatches,
        'all_native_usage_complete': live['all_requested_trials_have_complete_native_usage'],
        'official_passes': sum(row['official_success'] is True for row in live['trials']),
        'official_rewards_known': live['all_requested_official_success_observed'],
        'observed_provider_invocations': provider_calls,
        'deployments': deployments, 'offline_input_metrics': offline['tasks'],
        'resource_observations': {'serial_trials': True, 'container_samples': resources,
            'minimum_host_available_gib': min(row['mem_available_bytes'] for row in samples) / 1024**3,
            'minimum_host_free_disk_gib': min(row['disk_free_bytes'] for row in samples) / 1024**3,
            'maximum_host_load_1m': max(row['load_1m'] for row in samples),
            'samples': len(samples), 'resource_backoff_events': sum(row.get('event') == 'resource_backoff' for row in events)},
        'provider_stops_observed': [row['provider_stop'] for row in live['trials'] if row['provider_stop'] is not None],
        'provider_gate_reset': False, 'failed_task_automatic_retries': False,
        'raw_provider_logs_inspected': False, 'hidden_verifier_or_solution_contents_inspected': False,
        'policy_default': 'legacy', 'treatment_opt_in': 'required-instruction-ref@1',
        'statistical_or_causal_token_advantage_established': False,
        'decision': 'Keep opt-in. Exact prompt reduction is verified; total session usage must be evaluated independently.',
        'next_phase': 'next-phase-plan.json',
        'limitations': ['One repeat per arm per task; stochastic planning and coding behavior differ.',
            'Cached input is already included in input; total equals input plus output.',
            'Local tokenizer proxies measure prompt representation, not provider usage or billing.',
            'Rate-limit/backoff behavior is covered by authored tests; no live stop is inferred when absent.',
            'Resource pressure backoff tests are separate from bounded live execution.'],
        'evidence_sha256': {name: digest(ROOT / name) for name in (
            'source-bindings.json', 'comparison-protocol.json', 'live-comparison.json',
            'public-final/qualification.json', 'independent-public-replay.json',
            'next-phase-composition-census.json', 'next-phase-plan.json')}}
    with (ROOT / 'summary.json').open('x') as stream:
        json.dump(result, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')
    print(json.dumps({'source_commit': head, 'official_passes': result['official_passes'],
        'usage_complete': result['all_native_usage_complete'], 'pairs': pairs, 'source_clean': clean}, sort_keys=True))


if __name__ == '__main__':
    main()
