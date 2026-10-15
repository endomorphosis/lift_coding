#!/usr/bin/env python3
"""Prepare a frozen ABBA metadata comparison; never launch providers or containers.

Without --prepare this prints the plan and does not import the benchmark harness.
Preparation requires final clean source and archive pins supplied explicitly.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from aggregate_trials import CONTEXT_PROFILE, REMOVED_AXES, CANONICALIZED_AXES, normalize_config, validate_protocol


def planned_trials(task='tune-mjcf'):
    return [dict(name=f'{task}-{label}-{repeat:02}', task=task, repeat=repeat,
        semantic_context_profile=CONTEXT_PROFILE, semantic_metadata_view=mode)
        for label, mode, repeat in [('legacy', 'legacy', 1), ('factored', 'common-bindings@1', 1),
            ('factored', 'common-bindings@1', 2), ('legacy', 'legacy', 2)]]


def protocol_skeleton(task='tune-mjcf'):
    return {'schema': 'terminal-metadata-context-comparison-protocol@1',
        'trials': planned_trials(task), 'preparations': {}, 'requested_axis': 'semantic_metadata_view',
        'semantic_context_profile_fixed': CONTEXT_PROFILE, 'repeats_per_arm': 2,
        'execution_order': 'ABBA: legacy, common-bindings, common-bindings, legacy',
        'pairs_match_except': list(REMOVED_AXES), 'unordered_list_canonicalizations': list(CANONICALIZED_AXES),
        'max_concurrent_trials': 1, 'force_native_arm64_build': True,
        'failures_in_token_numerator': True, 'cached_input_is_subset': True,
        'fallback_accounting': 'Retain valid fallbacks in the requested arm; report actual per-invocation effective selection separately.',
        'plain_native_baseline_included': False, 'live_token_savings_claimed_before_execution': False,
        'resource_profile': 'source384-5cpu-16gib-extended@1',
        'model': 'gpt-6.1-sol', 'reasoning_effort': 'high', 'codex_version': '0.160.0',
        'fixed_controls': ['task', 'public task profile', 'model', 'reasoning effort', 'CLI', 'runtime archive',
            'semantic context profile, capsule count and byte limits', 'semantic transport schema',
            'coding reply mode', 'resource profile', 'retrieval and planning settings', 'original task inputs'],
        'sampling_limitations': ['Two repeats on one task are observational; this does not establish statistical or causal improvement.',
            'Offline local tokenizer improvements are not provider-native cumulative token savings.']}


def source_pin(source):
    return subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=source, text=True).strip()


def prepare_campaign(args):
    root, source, archive = args.root.resolve(), args.source.resolve(), args.archive.resolve()
    if not re.fullmatch('[a-f0-9]{40}', args.source_commit or ''): raise ValueError('explicit source commit required')
    if not re.fullmatch('[a-f0-9]{64}', args.archive_sha256 or ''): raise ValueError('explicit archive SHA256 required')
    if source_pin(source) != args.source_commit: raise ValueError('source HEAD differs from final pin')
    if subprocess.check_output(['git', 'status', '--porcelain'], cwd=source, text=True).strip(): raise ValueError('source must be clean')
    path = archive / 'runtime.tar.gz'
    with path.open('rb') as stream:
        if hashlib.file_digest(stream, 'sha256').hexdigest() != args.archive_sha256: raise ValueError('archive differs from final pin')
    protocol = protocol_skeleton(args.task)
    protocol['source_commit'] = args.source_commit
    protocol['archive_sha256'] = args.archive_sha256
    protocol['qualification_evidence'] = str(args.qualification.resolve()) if args.qualification else None
    if args.qualification:
        protocol['qualification_sha256'] = hashlib.sha256(args.qualification.read_bytes()).hexdigest()
    for row in protocol['trials']:
        if (root / 'trials' / row['name']).exists(): raise ValueError('trial directory exists; never overwrite: ' + row['name'])
    if (root / 'comparison-protocol.json').exists(): raise ValueError('frozen comparison protocol already exists')
    sys.path.insert(0, str(source))
    from benchmarks.agent_supervisor.container_coding.full_supervisor_benchmark import prepare
    for row in protocol['trials']:
        output = root / 'trials' / row['name']
        result = prepare(dataset=args.dataset.resolve(), output=output, archive=archive, arm='full',
            task_name=row['task'], task_profile=args.task_profile.resolve(),
            semantic_context_profile=CONTEXT_PROFILE, semantic_metadata_view=row['semantic_metadata_view'],
            resource_profile=protocol['resource_profile'])
        if not result.get('prepared'): raise ValueError('preparation did not complete: ' + row['name'])
        if result.get('archive_sha256') != args.archive_sha256: raise ValueError('prepared archive drift')
        if result.get('model') != protocol['model'] or result.get('reasoning_effort') != protocol['reasoning_effort'] or result.get('cli_version') != protocol['codex_version']:
            raise ValueError('provider settings drift')
        config = json.loads((output / 'config.json').read_text())
        frozen = {key: result[key] for key in ('archive_sha256', 'task_input_sha256', 'host_source_sha256')}
        frozen['normalized_configuration'] = normalize_config(config)
        previous = protocol['preparations'].setdefault(row['task'], frozen)
        if previous != frozen: raise ValueError('non-metadata comparison controls differ')
        print(json.dumps({'trial': row['name'], 'prepared': True, 'requested_metadata_view': row['semantic_metadata_view']}), flush=True)
    if source_pin(source) != args.source_commit or subprocess.check_output(['git', 'status', '--porcelain'], cwd=source, text=True).strip():
        raise ValueError('source changed during preparation')
    validate_protocol(protocol)
    with (root / 'comparison-protocol.json').open('x') as stream:
        json.dump(protocol, stream, indent=2, sort_keys=True)
        stream.write('\n')
    return protocol


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument('--task', default='tune-mjcf')
    parser.add_argument('--prepare', action='store_true')
    parser.add_argument('--source', type=Path)
    parser.add_argument('--source-commit')
    parser.add_argument('--archive', type=Path)
    parser.add_argument('--archive-sha256')
    parser.add_argument('--dataset', type=Path)
    parser.add_argument('--task-profile', type=Path)
    parser.add_argument('--qualification', type=Path)
    args = parser.parse_args()
    if not args.prepare:
        value = protocol_skeleton(args.task)
        validate_protocol(value)
        print(json.dumps(value, indent=2, sort_keys=True))
        return
    if any(getattr(args, key) is None for key in ('source', 'source_commit', 'archive', 'archive_sha256', 'dataset', 'task_profile')):
        parser.error('--prepare requires --source, --source-commit, --archive, --archive-sha256, --dataset and --task-profile')
    prepare_campaign(args)

if __name__ == '__main__': main()
