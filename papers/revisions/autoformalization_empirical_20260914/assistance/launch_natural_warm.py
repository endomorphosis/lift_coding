#!/usr/bin/env python3
"""Launch one explicitly bounded warm model for all remaining natural attempts.

Do not run against an active instance. This is the prospective entry point;
the current adopted model continues without being restarted by this file.
"""
import argparse
import datetime
import json
import os
import socket
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    command = ['flock', '-F', '-n', '/tmp/autoformalization-empirical-heavy.lock',
               '/usr/bin/python3', '-B', str(ROOT / 'scripts/run_leanstral_ephemeral.py'),
               '--wall-seconds', '10000', '--startup-seconds', '360',
               '--memory-gib', '90', '--reserve-gib', '12', '--cpus', '4',
               '--context', '4096', '--chat-template-file', str(HERE / 'leanstral_v15.jinja'),
               '--server-log', str(HERE / f'natural_server_warm_{stamp}.log'),
               '--', '/usr/bin/python3', '-B', str(HERE / 'run_natural_workload.py')]
    print(json.dumps(dict(event='natural_warm_launch_configuration', total_wall_seconds=10000,
                         startup_readiness_seconds=360, keep_warm_between_client_batches=True,
                         command=command, dry_run=args.dry_run)), flush=True)
    if args.dry_run:
        return 0
    results_path = HERE / 'natural_model/results.jsonl'
    results = [json.loads(line) for line in results_path.read_text().splitlines()] if results_path.exists() else []
    ids = {r['record_id'] for r in results}
    if len(ids) != len(results):
        raise RuntimeError('Duplicate terminal attempts require audit before launch')
    if len(ids) >= 100:
        print('All 100 attempts already complete; no model launch is needed.', flush=True)
        return 0
    # An interrupted request remains attempted. Reconcile its saved evidence
    # before allowing a resume, so the frozen client cannot repeat the request.
    for started in (HERE / 'natural_model').glob('record-*/started.json'):
        if json.loads(started.read_text())['record_id'] not in ids:
            raise RuntimeError(f'Unreconciled started attempt: {started.parent.name}; preserve as terminal before resuming')
    with socket.socket() as sock:
        sock.settimeout(1)
        if sock.connect_ex(('127.0.0.1', 8080)) == 0:
            raise RuntimeError('An endpoint is already active; continue its owned workload instead of reloading')
    os.chdir(ROOT)
    os.execvp(command[0], command)


if __name__ == '__main__':
    raise SystemExit(main())
