"""Freeze one fresh telemetry qualification; this does not execute a model."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
SOURCE = Path('/home/barberb/lift_coding_worktrees/indexed-worker-context-20261011')
DATASET = Path('/home/barberb/lift_coding/.benchmarks/terminal-bench-2')
NAME = 'mjcf-telemetry-01'


def write(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-commit', required=True)
    parser.add_argument('--archive-sha256', required=True)
    args = parser.parse_args()
    head = subprocess.check_output(['git', '-C', str(SOURCE), 'rev-parse', 'HEAD'], text=True).strip()
    dirty = subprocess.check_output(['git', '-C', str(SOURCE), 'status', '--porcelain'], text=True).strip()
    if head != args.source_commit or dirty:
        raise ValueError('explicit clean source pin required')
    archive = ROOT / 'runtime-archive-v1'
    verification = json.loads((archive / 'verification.json').read_text())
    if verification['source_repositories']['source']['head'] != head:
        raise ValueError('archive source pin differs')
    with (archive / 'runtime.tar.gz').open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    if digest != args.archive_sha256 or digest != verification['archive_sha256']:
        raise ValueError('archive pin differs')
    if any((ROOT / name).exists() for name in ('comparison-protocol.json', 'launcher-protocol.json')):
        raise ValueError('qualification already frozen')
    sys.path.insert(0, str(SOURCE))
    from benchmarks.agent_supervisor.container_coding.full_supervisor_benchmark import prepare
    result = prepare(dataset=DATASET, output=ROOT / 'trials' / NAME,
        archive=archive, arm='full', task_name='tune-mjcf', task_profile=ROOT / 'profiles/tune-mjcf.json',
        semantic_context_profile='indexed-default@1', semantic_metadata_view='legacy',
        resource_profile='source384-5cpu-16gib-extended@1')
    if (result.get('prepared') is not True or result.get('archive_sha256') != digest
            or result.get('model') != 'gpt-6.1-sol' or result.get('reasoning_effort') != 'high'
            or result.get('cli_version') != '0.160.0'):
        raise ValueError('preparation or provider controls differ')
    pins = {'schema': 'terminal-indexed-context-launcher-protocol@1', 'source_head': head,
        'datasets_head': verification['source_repositories']['datasets']['head'],
        'kit_head': verification['source_repositories']['kit']['head'],
        'archive_sha256': digest, 'native_cli_version': '0.160.0'}
    write(ROOT / 'launcher-protocol.json', pins)
    write(ROOT / 'comparison-protocol.json', {
        'schema': 'terminal-interaction-telemetry-qualification-protocol@1',
        'source_commit': head, 'archive_sha256': digest,
        'trials': [{'name': NAME, 'task': 'tune-mjcf', 'semantic_context_profile': 'indexed-default@1',
                    'semantic_metadata_view': 'legacy'}],
        'purpose': 'Qualify default passive telemetry through a real native CLI invocation and official task verifier.',
        'model': result['model'], 'reasoning_effort': result['reasoning_effort'], 'cli_version': result['cli_version'],
        'task_input_sha256': result['task_input_sha256'], 'host_source_sha256': result['host_source_sha256'],
        'config_sha256': result['config_sha256'], 'resource_profile': 'source384-5cpu-16gib-extended@1',
        'telemetry_schema': 'native-codex-interaction-telemetry@1',
        'experimental_prompt_change': False, 'new_token_savings_comparison': False,
        'max_concurrent_trials': 1, 'task_solutions_not_read': True, 'verifier_files_hashed_only': True})
    print(json.dumps({'prepared': True, 'trial': NAME, 'provider_calls': 0, 'containers_launched': 0}))


if __name__ == '__main__':
    main()
