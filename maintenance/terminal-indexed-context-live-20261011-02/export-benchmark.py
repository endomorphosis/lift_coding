"""Export the retained comparison with explicit measurement scope and limits."""
import csv
import hashlib
import json
from pathlib import Path

campaign = Path(__file__).resolve().parent
raw = (campaign / 'aggregate.json').read_bytes()
aggregate = json.loads(raw)
rows = []
for trial in aggregate['trials']:
    attempts = trial['attempts']
    final = attempts[-1] if attempts else {}
    projection = final.get('projection', {})
    coding = [call for attempt in attempts for call in attempt['provider_usage']['calls']
              if call['phase'] == 'coding']
    rows.append({
        'trial': trial['name'], 'task': trial['task'],
        'profile': trial['semantic_context_profile'], 'state': trial['state'],
        'official_reward': final.get('official_reward'), 'solved': trial['solved'],
        'usage_complete': trial['usage_complete'],
        **trial['complete_tokens'],
        'selected_capsules': projection.get('selected_capsule_count'),
        'worker_payload_bytes': projection.get('worker_payload_bytes'),
        'coding_model_prompt_bytes': coding[0]['input_bytes'].get('model_prompt_bytes')
            if len(coding) == 1 else None,
        'coding_invocations': len(coding),
        'input_audit': final.get('context_input_audit', {}).get('status'),
        'agent_seconds': final.get('supervisor_seconds'),
        'tokens_per_solved_task': trial['tokens_per_solved_task'],
        'comparison_eligible': trial['model_context_comparison_eligible'],
    })
comparison = {}
by_profile = {row['profile']: row for row in rows}
compact, default = (by_profile.get(key) for key in ('indexed-compact@1', 'indexed-default@1'))
if (compact and default and compact['comparison_eligible'] and default['comparison_eligible']
        and compact['selected_capsules'] != default['selected_capsules']):
    for metric in ('total_tokens', 'coding_model_prompt_bytes', 'worker_payload_bytes', 'agent_seconds'):
        before, after = default[metric], compact[metric]
        if isinstance(before, (float, int)) and before > 0 and isinstance(after, (float, int)):
            comparison[metric] = {'default': before, 'compact': after,
                'compact_minus_default': after - before,
                'compact_change_percent': (after - before) * 100 / before}
result = {
    'schema': 'terminal-indexed-context-benchmark@1',
    'source_commit': aggregate['source_commit'],
    'aggregate_sha256': hashlib.sha256(raw).hexdigest(),
    'trials': rows, 'observed_comparison': comparison,
    'measurement_scope': 'Observed native session cumulative input plus output tokens, including every recorded planning and coding attempt.',
    'cached_input_is_subset': True, 'billing_total_verified': False,
    'statistically_established_improvement': False,
    'limitations': [
        'One repeat per profile on one task; model trajectories and system load may differ.',
        'Capsule limits are ceilings; the byte limit leaves three versus two capsules on this task.',
        'This pair compares two indexed profiles; no plain native or unindexed baseline was run.',
        'Unknown or incomplete usage is never counted as zero. Failed attempts remain in the numerator.',
        'Batching was excluded from the live pair because both profiles retained one capsule.',
        'Host resource usage was sampled; pressure was not deliberately injected. Backoff was tested with controlled offline samples.',
    ],
    'evidence': {'aggregate': 'aggregate.json', 'protocol': 'comparison-protocol.json',
        'validation': 'validation-summary.json', 'resources': 'resource-observations.json',
        'context_shape': 'context-shape-analysis.json'},
}
(campaign / 'benchmark.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
with (campaign / 'benchmark.csv').open('w', newline='') as stream:
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
print(json.dumps(result, indent=2, sort_keys=True))
