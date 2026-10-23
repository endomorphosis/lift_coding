#!/usr/bin/env python3
"""Export every retained repeat plus arm totals; never collapse rows by profile."""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
from pathlib import Path


def export_report(aggregate):
    rows = []
    for trial in aggregate['trials']:
        attempts = trial['attempts']
        calls = [call for attempt in attempts for call in attempt['provider_usage']['calls']]
        coding = [call for call in calls if call['phase'] == 'coding']
        dispatches = [attempt['semantic_metadata_dispatch'] for attempt in attempts]
        rows.append({'trial': trial['name'], 'task': trial['task'], 'repeat': trial['repeat'],
            'requested_metadata_view': trial['semantic_metadata_view'], 'context_profile': trial['semantic_context_profile'],
            'state': trial['state'], 'solved': trial['solved'], 'usage_complete': trial['usage_complete'],
            **trial['complete_tokens'], 'attempts_observed': len(attempts), 'coding_invocations': len(coding),
            'requested_arm_comparison_eligible': trial['requested_arm_comparison_eligible'],
            'effective_treatment_observed': trial['effective_treatment_observed'],
            'effective_treatment_comparison_eligible': trial['effective_treatment_comparison_eligible'],
            'effective_modes': ';'.join(sorted({mode for dispatch in dispatches for mode in dispatch['selected_modes']})),
            'fallback_reasons': ';'.join(sorted({reason for dispatch in dispatches for reason in dispatch['fallback_reasons']})),
            'input_audits': ';'.join(str(attempt['context_input_audit']['status']) for attempt in attempts),
            'selected_capsules': attempts[-1]['projection']['selected_capsule_count'] if attempts else None,
            'coding_model_prompt_bytes_sum': sum(call['input_bytes']['model_prompt_bytes'] for call in coding)
                if coding and all(call['input_bytes']['model_prompt_bytes'] is not None for call in coding) else None,
            'tokens_per_solved_trial': trial['tokens_per_solved_task']})
    comparisons = {}
    baseline, candidate = (aggregate['arms'].get(mode) for mode in ('legacy', 'common-bindings@1'))
    if baseline and candidate:
        for metric in ('complete_tokens_all_attempts', 'tokens_per_solved_task_including_failures'):
            before, after = baseline[metric], candidate[metric]
            if metric == 'complete_tokens_all_attempts': before, after = before['total_tokens'], after['total_tokens']
            qualified = (aggregate.get('requested_arm_populations_match') is True
                and baseline['requested_arm_comparison_eligible'] and candidate['requested_arm_comparison_eligible'])
            numeric = type(before) in (int, float) and type(after) in (int, float) and before > 0
            comparisons[metric] = {'legacy': before, 'requested_common_bindings': after,
                'requested_arm_comparison_eligible': qualified,
                'matched_task_repeat_populations': aggregate.get('requested_arm_populations_match'),
                'effective_treatment_comparison_eligible': qualified and baseline['effective_treatment_comparison_eligible'] and candidate['effective_treatment_comparison_eligible'],
                'candidate_minus_legacy': after - before if qualified and numeric else None,
                'candidate_change_percent': (after - before) * 100 / before if qualified and numeric else None}
    return {'schema': 'terminal-metadata-context-benchmark@1', 'source_commit': aggregate['source_commit'],
        'trials': rows, 'arms': aggregate['arms'],
        'requested_arm_populations_match': aggregate.get('requested_arm_populations_match'),
        'requested_arm_populations': aggregate.get('requested_arm_populations'), 'observed_requested_arm_comparison': comparisons,
        'measurement_scope': 'Native cumulative input plus output across every observed planning/coding attempt, including failures.',
        'cached_input_is_subset': True, 'billing_total_verified': False,
        'statistically_established_improvement': False, 'limitations': aggregate['caveats']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    raw = (args.root / 'aggregate.json').read_bytes()
    result = export_report(json.loads(raw))
    result['aggregate_sha256'] = hashlib.sha256(raw).hexdigest()
    (args.root / 'benchmark.json').write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + '\n')
    with (args.root / 'benchmark.csv').open('w', newline='') as stream:
        rows = result['trials']
        if rows:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    print(json.dumps({'trials_exported': len(result['trials']), 'comparison': result['observed_requested_arm_comparison']}, indent=2))

if __name__ == '__main__': main()
