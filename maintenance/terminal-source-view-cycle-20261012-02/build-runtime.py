#!/usr/bin/env python3
"""Preflight, then explicitly build a source-frozen generic Terminal Bench runtime.

Default execution only records local asset checks. After source freeze, run with
--build --expected-source-head <full commit>. No container, provider, auth file,
benchmark task input, learned model, or historical Codex cache is used here.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import time
from pathlib import Path

EVIDENCE = Path(__file__).resolve().parent
SOURCE = Path('/home/barberb/lift_coding_worktrees/terminal-source-view-recovery-20261012')
DATASETS = Path('/home/barberb/lift_coding_worktrees/indexed-worker-context-datasets-20261011')
KIT = Path('/home/barberb/lift_coding/.worktrees/publication-main-20261004/kit')
ASSETS = Path('/home/barberb/lift_coding/maintenance/terminal-frontier-runtime-20261011-01/pinned-assets-v8')
PINNED_DATASETS = 'd24e15ee73659a5d4cff20e8f1cbf1c5ab92a234'
PINNED_KIT = '8ac00bb1974b1378e12091d546d8425af34049e0'
ROOTS = {'source': SOURCE, 'datasets': DATASETS, 'kit': KIT}


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def command(*args):
    return subprocess.check_output(args, text=True, timeout=60).strip()


def repository(path):
    return {
        'path': str(path),
        'head': command('git', '-C', str(path), 'rev-parse', 'HEAD'),
        'status': command('git', '-C', str(path), 'status', '--porcelain=v1', '--untracked-files=all'),
    }


def regular(path):
    if not path.is_file() or path.is_symlink():
        raise ValueError('regular asset required: ' + str(path))
    return {'bytes': path.stat().st_size, 'sha256': sha(path)}


def preflight():
    if platform.machine() != 'aarch64':
        raise ValueError('these pinned native assets require Linux aarch64')
    sys.path[:0] = [str(SOURCE), str(DATASETS), str(KIT)]
    from benchmarks.agent_supervisor.container_coding import terminal_deployment as deployment
    from benchmarks.agent_supervisor.container_coding.benchmark_provider_profile import CLI_VERSION
    from benchmarks.agent_supervisor.container_coding.benchmark_resource_profile import (
        EXTENDED_SOURCE384_PROFILE, execution_budget, resource_environment,
    )
    if Path(deployment.__file__).resolve() != SOURCE / 'benchmarks/agent_supervisor/container_coding/terminal_deployment.py':
        raise ValueError('runtime builder import differs from selected source worktree')
    if CLI_VERSION != '0.160.0' or 'duckdb==1.5.5' not in deployment.BASE_REQUIREMENTS:
        raise ValueError('re-review native assets after a provider or DuckDB pin change')
    repos = {name: repository(root) for name, root in ROOTS.items()}
    for name, expected in (('datasets', PINNED_DATASETS), ('kit', PINNED_KIT)):
        if repos[name]['head'] != expected or repos[name]['status']:
            raise ValueError(name + ' must remain at its clean pinned revision')
    extensions = {}
    for name in ('httpfs', 'quack', 'ducklake'):
        path = ASSETS / 'extensions' / (name + '.duckdb_extension')
        info = regular(path)
        with path.open('rb') as stream:
            stream.seek(-512, 2)
            trailer = stream.read()
        if b'v1.5.5\0' not in trailer or b'linux_arm64\0' not in trailer:
            raise ValueError('DuckDB extension version/platform differs: ' + name)
        extensions[name] = dict(info, duckdb_version='1.5.5', platform='linux_arm64')
    lean = ASSETS / 'toolchains/lean/bin/lean'
    lean_info = regular(lean)
    lean_info['version'] = command(str(lean), '--version')
    if 'version 4.34.1, aarch64-' not in lean_info['version']:
        raise ValueError('Lean asset differs from the reviewed aarch64 toolchain')
    free = shutil.disk_usage(EVIDENCE).free
    if free < 10 * 1024**3:
        raise ValueError('reserve at least 10 GiB free before packaging the Lean runtime')
    return {
        'schema': 'terminal-indexed-context-runtime-preflight@1',
        'source_repositories': repos, 'host_architecture': platform.machine(),
        'extensions': extensions, 'lean': lean_info,
        'base_requirements': list(deployment.BASE_REQUIREMENTS),
        'runtime_python_version': deployment.RUNTIME_PYTHON_VERSION,
        'codex_version': CLI_VERSION, 'codex_installation': 'fresh source-owned pinned npm installation at deployment',
        'historical_codex_bundle_included': False, 'setup_cache_policy': None,
        'learned_models_selected': False, 'torch_required': False,
        'prompt_tokenizer_selected': False,
        'prompt_tokenizer_limitation': 'No tokenizer runtime or descriptor is selected; provider usage remains the total-token authority.',
        'resource_profile': EXTENDED_SOURCE384_PROFILE,
        'resource_environment': resource_environment(EXTENDED_SOURCE384_PROFILE),
        'execution_budget': execution_budget(EXTENDED_SOURCE384_PROFILE),
        'free_disk_bytes': free, 'provider_calls': 0, 'containers_launched': 0,
        'credentials_read': False, 'task_inputs_read': False,
    }


def build(report, expected_source_head, output):
    from benchmarks.agent_supervisor.container_coding.terminal_deployment import build_runtime_archive
    if not re.fullmatch(r'[0-9a-f]{40}', expected_source_head or ''):
        raise ValueError('--build requires a complete --expected-source-head after source freeze')
    source = report['source_repositories']['source']
    if source['head'] != expected_source_head or source['status']:
        raise ValueError('source checkout must be clean and match the explicitly frozen commit')
    if output.exists():
        raise ValueError('a fresh output directory is required; previous evidence is preserved')
    started = time.monotonic()
    manifest = build_runtime_archive(
        output=output, source=SOURCE, datasets=DATASETS, kit=KIT,
        extension_dir=ASSETS / 'extensions', lean_toolchain=ASSETS / 'toolchains/lean',
    )
    if (manifest['credentials_in_archive'] is not False or manifest['task_inputs_in_archive'] is not False
            or manifest['codex_version'] != '0.160.0' or manifest.get('torch_cpu_requirement')
            or manifest.get('setup_cache') or manifest.get('native_codex_bundle')):
        raise ValueError('archive includes an unexpected runtime selection')
    records = {row['path']: row for row in manifest['files']}
    if len(records) != len(manifest['files']):
        raise ValueError('duplicate inventory path')
    archive_path = output / 'runtime.tar.gz'
    if sha(archive_path) != manifest['archive_sha256']:
        raise ValueError('archive digest differs from manifest')
    seen = set()
    with tarfile.open(archive_path, 'r:gz') as archive:
        for entry in archive:
            if entry.name in seen or entry.name not in records or not entry.isfile():
                raise ValueError('unexpected, duplicate, or nonregular archive entry')
            seen.add(entry.name)
            row = records[entry.name]
            if entry.size != row['bytes'] or entry.mode != row['mode'] or entry.uid != 0 or entry.gid != 0:
                raise ValueError('archive entry metadata differs')
            with archive.extractfile(entry) as stream:
                if hashlib.file_digest(stream, 'sha256').hexdigest() != row['sha256']:
                    raise ValueError('archive entry digest differs')
            prefix, relative = entry.name.split('/', 1)
            if prefix in ROOTS:
                original = ROOTS[prefix] / relative
            elif prefix == 'extensions':
                original = ASSETS / entry.name
            elif entry.name.startswith('toolchains/lean/'):
                original = ASSETS / entry.name
            else:
                raise ValueError('unselected archive asset prefix')
            if original.is_symlink() or not original.is_file() or sha(original) != row['sha256']:
                raise ValueError('source or native asset changed after packaging')
    if seen != set(records):
        raise ValueError('manifest inventory is not exactly the archive population')
    after = {name: repository(root) for name, root in ROOTS.items()}
    if after != report['source_repositories']:
        raise ValueError('source checkout changed during archive build')
    receipt = {
        'schema': 'terminal-runtime-archive-file-verification@1',
        'source_repositories': after, 'archive_sha256': manifest['archive_sha256'],
        'files_verified': len(seen), 'archive_bytes': archive_path.stat().st_size,
        'total_uncompressed_bytes': sum(row['bytes'] for row in records.values()),
        'all_archive_entries_match_inventory': True,
        'all_packaged_source_matches_checkout_after_build': True,
        'credentials_in_archive': False, 'task_inputs_in_archive': False,
        'provider_calls': 0, 'containers_launched': 0,
        'elapsed_seconds': time.monotonic() - started,
    }
    (output / 'verification.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', action='store_true')
    parser.add_argument('--expected-source-head')
    parser.add_argument('--output', type=Path, default=EVIDENCE / 'runtime-archive')
    args = parser.parse_args()
    if not args.build and args.expected_source_head:
        parser.error('--expected-source-head is only meaningful with --build')
    report = preflight()
    (EVIDENCE / 'runtime-preflight.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    if args.build:
        print(json.dumps(build(report, args.expected_source_head, args.output.absolute()), sort_keys=True))
    else:
        print(json.dumps({'preflight': 'passed', 'report': str(EVIDENCE / 'runtime-preflight.json'),
                          'archive_built': False, 'source_dirty': bool(report['source_repositories']['source']['status'])}))


if __name__ == '__main__':
    main()
