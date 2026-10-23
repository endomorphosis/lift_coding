#!/usr/bin/env python3
"""Independently check frozen controls before reading any live trial results."""
import argparse
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import tomllib

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('independent_primitives', ROOT / 'verify-benchmark-review.py')
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source-commit', required=True)
parser.add_argument('--archive-sha256', required=True)
args = parser.parse_args()
if not re.fullmatch(r'[0-9a-f]{40}', args.source_commit) or not re.fullmatch(r'[0-9a-f]{64}', args.archive_sha256):
    raise ValueError('explicit exact source/archive pins required')
protocol = review.read(ROOT / 'comparison-protocol.json')
checks = {
    'protocol_source': protocol['source_commit'] == args.source_commit,
    'protocol_archive': protocol['archive_sha256'] == args.archive_sha256,
    'abba_order': [(row['name'], row['tool_output_policy'], row['repeat'])
                   for row in protocol['trials']] == review.ORDER,
    'clean_source': subprocess.check_output(['git', '-C', str(review.SOURCE), 'rev-parse', 'HEAD'],
                    text=True, timeout=15).strip() == args.source_commit
                    and not subprocess.check_output(['git', '-C', str(review.SOURCE), 'status', '--porcelain'],
                    text=True, timeout=15).strip(),
    'single_concurrent_trial': protocol['max_concurrent_trials'] == 1,
    'no_format_adoption_inferred': protocol['helper_adoption_guaranteed'] is False,
}
for row in protocol['trials']:
    name = row['name']
    folder = ROOT / 'trials' / name
    config = review.read(folder / 'config.json')
    prepared = review.read(folder / 'preparation.json')
    frozen = protocol['preparations']['tune-mjcf']
    checks[name + '.normalized_controls'] = review.normalized(config) == frozen['normalized_configuration']
    checks[name + '.frozen_config'] = (review.sha((folder / 'config.json').read_bytes())
                                     == row['config_sha256'] == prepared['config_sha256'])
    checks[name + '.frozen_input_pins'] = all(prepared[key] == frozen[key]
        for key in ('archive_sha256', 'task_input_sha256', 'host_source_sha256'))
    checks[name + '.policy'] = (config['agents'][0]['kwargs'].get('tool_output_policy', 'legacy')
                               == prepared.get('tool_output_policy', 'legacy') == row['tool_output_policy'])
    task_path = Path(config['tasks'][0]['path'])
    public = task_path / 'task.toml'
    if public.is_symlink() or not public.is_file() or not 0 < public.stat().st_size <= 256000:
        raise ValueError('bounded regular public task metadata required')
    raw = public.read_bytes()
    checks[name + '.canonical_task_identity'] = (
        review.sha(raw) == prepared['task_input_sha256']['task.toml']
        and tomllib.loads(raw.decode()).get('task', {}).get('name', task_path.name) == 'terminal-bench/tune-mjcf'
        and row['task'] == prepared['task'] == 'tune-mjcf')
    environment = config['environment']
    checks[name + '.resource_limits'] = (environment['override_cpus'] == 5
        and environment['override_memory_mb'] == 16384
        and environment['cpu_enforcement_policy'] == environment['memory_enforcement_policy'] == 'limit')

result = {
    'schema': 'independent-compact-preparation-review@1',
    'source_commit': args.source_commit, 'archive_sha256': args.archive_sha256,
    'protocol_sha256': review.sha((ROOT / 'comparison-protocol.json').read_bytes()),
    'verifier_sha256': review.sha(Path(__file__).read_bytes()),
    'all_checks_passed': all(checks.values()), 'check_count': len(checks), 'checks': checks,
    'provider_calls': 0, 'raw_provider_data_exported': False,
    'hidden_task_test_contents_read': False,
    'compact_format_adoption_established': False,
}
(ROOT / 'independent-preparation-review.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
print(json.dumps({key: result[key] for key in ('all_checks_passed', 'check_count', 'protocol_sha256')}))
raise SystemExit(0 if result['all_checks_passed'] else 1)
