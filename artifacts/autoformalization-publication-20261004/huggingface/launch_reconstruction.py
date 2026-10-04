"""Explicit native-site bootstrap for the frozen reconstruction CLI.

This launcher creates no publication gate and provides no parent wall watcher.
It adds one selected site directory without invoking its .pth files. It is not
an OS sandbox or a complete verified-before-execution dependency closure.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
import os
import runpy
import stat
import sys
from pathlib import Path

NATIVE_SITE = Path('/home/barberb/.local/lib/python3.12/site-packages')
HELPER = Path('/home/barberb/lift_coding/artifacts/autoformalization-publication-20261004/training/train_reconstruction.py')
HELPER_SHA = '387c0335549374a98e1d5458d9746733fe385dd760584fdf059f6266c44873d3'
PLAN = HELPER.with_name('run-plan-02.json')
PLAN_SHA = 'b02b0b35a9f2d82abd5422643f9034bea30e1d83f0c21772aa0a609c234ead3b'
PROVIDERS = {
    'torch': {'version': '2.13.0', 'bytes': 111841,
              'sha256': 'cf40c075c95864036e835795756d69b8cccfafa76f3bcde5eba9d06065ccd3d1'},
    'safetensors': {'version': '0.7.0', 'bytes': 194,
                    'sha256': 'c1bcca66501582702c8c79aaaf2b922428800efa4367134609f8fc57363402dd'},
}


def checked_bytes(path, expected_sha, expected_size=None):
    path = Path(path)
    if not path.is_absolute() or any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('absolute nonsymlink selected file required')
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or not 0 < before.st_size <= 32 * 1024 * 1024:
            raise ValueError('bounded nonempty regular selected file required')
        with os.fdopen(descriptor, 'rb', closefd=False) as stream:
            data = stream.read(32 * 1024 * 1024 + 1)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    if (before.st_ino, before.st_size, before.st_mtime_ns) != (
            after.st_ino, after.st_size, after.st_mtime_ns):
        raise ValueError('selected file changed during read')
    if hashlib.sha256(data).hexdigest() != expected_sha or (
            expected_size is not None and len(data) != expected_size):
        raise ValueError('selected file pin mismatch')
    return data


def select_native_site():
    if not sys.flags.isolated or not sys.dont_write_bytecode:
        raise ValueError('launch with the selected interpreter -I -B')
    if not NATIVE_SITE.is_dir() or any(p.is_symlink() for p in (NATIVE_SITE, *NATIVE_SITE.parents)):
        raise ValueError('selected native site unavailable or symlinked')
    if 'torch' in sys.modules or 'safetensors' in sys.modules:
        raise ValueError('numerical providers imported before selection')
    sys.path.insert(0, str(NATIVE_SITE))
    references = {}
    for name, expected in PROVIDERS.items():
        selected = NATIVE_SITE / name / '__init__.py'
        checked_bytes(selected, expected['sha256'], expected['bytes'])
        spec = importlib.util.find_spec(name)
        if spec is None or Path(spec.origin) != selected:
            raise ValueError('selected provider module path differs')
        distribution = importlib.metadata.distribution(name)
        if distribution.version != expected['version'] or Path(distribution.locate_file('')) != NATIVE_SITE:
            raise ValueError('selected provider distribution differs')
        references[name] = {'path': str(selected), **expected}
    return references


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--metadata-only', action='store_true')
    parser.add_argument('--lane', choices=('legacy8', 'native384', 'native768'))
    parser.add_argument('--seed', type=int, choices=(1729, 1730, 1731))
    parser.add_argument('--output-directory')
    parser.add_argument('--publication-gate')
    parser.add_argument('--publication-gate-sha256')
    args = parser.parse_args()
    helper_data = checked_bytes(HELPER, HELPER_SHA)
    plan_data = checked_bytes(PLAN, PLAN_SHA)
    compile(helper_data, str(HELPER), 'exec')
    providers = select_native_site()
    if args.metadata_only:
        print(json.dumps({'status': 'selected_native_metadata_ready_no_provider_imports',
                          'helper_sha256': HELPER_SHA, 'plan_sha256': PLAN_SHA,
                          'providers': providers, 'numerical_provider_imports': 0,
                          'training_executed': False, 'qualification': False,
                          'site_pth_processing': False,
                          'dependency_closure': 'selected_entrypoints_only'}, sort_keys=True))
        return
    if any(value is None for value in (args.lane, args.seed, args.output_directory,
                                       args.publication_gate, args.publication_gate_sha256)):
        parser.error('a selected lane/seed, fresh output and externally pinned publication gate are required')
    # Validate exact gate bytes before delegating to the existing closed gate validator.
    checked_bytes(args.publication_gate, args.publication_gate_sha256)
    for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
        os.environ[key] = '1'
    os.environ['CUDA_VISIBLE_DEVICES'] = ''
    sys.argv = [str(HELPER), '--plan', str(PLAN), '--plan-sha256', PLAN_SHA,
                '--lane', args.lane, '--seed', str(args.seed), '--output-directory', args.output_directory,
                '--publication-gate', args.publication_gate,
                '--publication-gate-sha256', args.publication_gate_sha256]
    try:
        # The owner checks its source/config pins again before any Torch import.
        # runpy reads the selected frozen path; this does not claim OS race isolation.
        runpy.run_path(str(HELPER), run_name='__main__')
    finally:
        if checked_bytes(HELPER, HELPER_SHA) != helper_data or checked_bytes(PLAN, PLAN_SHA) != plan_data:
            raise ValueError('selected helper or plan changed during execution')
        for name, expected in PROVIDERS.items():
            checked_bytes(NATIVE_SITE / name / '__init__.py', expected['sha256'], expected['bytes'])


if __name__ == '__main__':
    main()
