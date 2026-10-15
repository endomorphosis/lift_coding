#!/usr/bin/env python3
"""Fresh public npm installation in an owned, resource-bounded container."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
SOURCE = Path('/home/barberb/lift_coding_worktrees/indexed-worker-context-20261011')
NAME = 'compact-fresh-installer-20261012-02'
IMAGE = 'python:3.13-slim-bookworm'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true')
    args = parser.parse_args()
    if not args.run:
        print(json.dumps({'image': IMAGE, 'cpus': 2, 'memory_bytes': 2 * 1024**3,
                          'provider_calls': 0, 'auth_injected': False}))
        return
    out = ROOT / 'fresh-installer-probe'
    out.mkdir(exist_ok=False)
    sys.path.insert(0, str(SOURCE))
    from benchmarks.agent_supervisor.container_coding.terminal_deployment import (
        native_codex_install_script, native_codex_exposure_script,
    )
    for filename, script in [('install.py', native_codex_install_script()),
                             ('expose.py', native_codex_exposure_script())]:
        (out / filename).write_text(script)
    report = {'schema': 'authored-fresh-native-installer-probe@1', 'image': IMAGE,
              'cpus': 2, 'memory_bytes': 2 * 1024**3, 'pids_limit': 256,
              'provider_calls': 0, 'auth_injected': False, 'host_home_mounted': False,
              'task_files_mounted': False, 'fresh_npm_cache': True,
              'steps': [], 'completed': False,
              'source_commit': subprocess.check_output(
                  ['git', '-C', str(SOURCE), 'rev-parse', 'HEAD'], text=True).strip(),
              'source_dirty': bool(subprocess.check_output(
                  ['git', '-C', str(SOURCE), 'status', '--porcelain'], text=True).strip()),
              'installer_script_sha256': digest(out / 'install.py'),
              'exposure_script_sha256': digest(out / 'expose.py')}

    def run(label, argv, timeout):
        start = time.monotonic()
        log = out / (label + '.log')
        row = {'label': label, 'timeout_seconds': timeout}
        try:
            with log.open('xb') as stream:
                result = subprocess.run(argv, stdin=subprocess.DEVNULL,
                                        stdout=stream, stderr=subprocess.STDOUT, timeout=timeout)
            row['returncode'] = result.returncode
        except subprocess.TimeoutExpired:
            row['timed_out'] = True
            raise
        finally:
            row['elapsed_seconds'] = time.monotonic() - start
            row['log_sha256'] = digest(log)
            row['log_bytes'] = log.stat().st_size
            report['steps'].append(row)
            print(json.dumps(row), flush=True)
        if result.returncode:
            raise RuntimeError('probe step failed: ' + label)
        return log.read_text() if log.stat().st_size < 65536 else None

    # Never acquire or remove an existing container, even if the name matches.
    if subprocess.check_output(['docker', 'ps', '-aq', '--filter',
                                'name=^/' + NAME + '$'], text=True).strip():
        raise ValueError('fresh owned container name required')
    started = time.monotonic()
    container_id = None
    try:
        report['image_id'] = run('image', ['docker', 'image', 'inspect', IMAGE,
                                        '--format', '{{.Id}}'], 10).strip()
        container_id = run('create', ['docker', 'run', '--detach', '--rm', '--name', NAME,
            '--label', 'codex.campaign=terminal-output-compact-20261012-02',
            '--cpus=2', '--memory=2g', '--pids-limit=256', IMAGE, 'sleep', '900'], 30).strip()
        report['container_id'] = container_id
        run('apt-update', ['docker', 'exec', NAME, 'timeout', '--signal=TERM',
            '--kill-after=5s', '60s', 'apt-get', '-o', 'Acquire::Retries=1',
            '-o', 'Acquire::http::Timeout=30', '-o', 'Acquire::https::Timeout=30', 'update'], 75)
        run('node-dependencies', ['docker', 'exec', NAME, 'timeout', '--signal=TERM',
            '--kill-after=5s', '120s', 'env', 'DEBIAN_FRONTEND=noninteractive', 'apt-get',
            '-o', 'Acquire::Retries=1', '-o', 'Acquire::http::Timeout=30',
            '-o', 'Acquire::https::Timeout=30', 'install', '-y', '--no-install-recommends',
            'nodejs', 'npm'], 140)
        run('account', ['docker', 'exec', NAME, 'sh', '-c',
            'mkdir -p /opt/ipfs-supervisor && useradd --uid 1000 --create-home '
            '--home-dir /opt/ipfs-supervisor/home --shell /bin/bash supervisor'], 10)
        for name in ('install.py', 'expose.py'):
            run('copy-' + name, ['docker', 'cp', str(out / name), NAME + ':/' + name], 10)
        raw = run('install', ['docker', 'exec', '--user', 'supervisor', NAME,
                             'python3', '-I', '/install.py'], 210)
        report['install_receipt'] = json.loads(raw)
        raw = run('expose', ['docker', 'exec', '--user', 'root', NAME,
                            'python3', '-I', '/expose.py'], 40)
        report['exposure_receipt'] = json.loads(raw)
        version = run('user-version', ['docker', 'exec', '--user', 'supervisor', NAME,
                      '/opt/ipfs-supervisor/provider-bin/codex', '--version'], 15).strip()
        if version != 'codex-cli 0.160.0' or not report['install_receipt']['completed']:
            raise ValueError('native pin or installer completion differs')
        report['completed'] = True
    except Exception as exc:
        report['error_type'] = type(exc).__name__
    finally:
        if container_id is not None:
            try:
                run('cleanup', ['docker', 'rm', '--force', container_id], 20)
            except Exception as exc:
                report['cleanup_error_type'] = type(exc).__name__
        remaining = subprocess.check_output(['docker', 'ps', '-aq', '--filter',
                    'name=^/' + NAME + '$'], text=True).strip()
        report['owned_container_absent'] = not remaining
        report['elapsed_seconds'] = time.monotonic() - started
        (out / 'report.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    raise SystemExit(0 if report['completed'] and report['owned_container_absent'] else 1)


if __name__ == '__main__':
    main()
