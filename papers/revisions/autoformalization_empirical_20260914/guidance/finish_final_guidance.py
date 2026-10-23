#!/usr/bin/env python3
"""Wait for final T3 receipts, execute the frozen collector, and publish its bundle.

This orchestration adds no predictions, selection rules, or scientific settings.
It refuses to overwrite any existing final collector or bundle manifest.
"""
import fcntl
import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXPERIMENT = HERE.parent
SEEDS = (104729, 130363, 155921)


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    started = time.monotonic()
    with (HERE / 'completion.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        predictions = [EXPERIMENT / f'autoencoder/final/T3-{seed}.predictions.jsonl' for seed in SEEDS]
        receipts = [Path(str(path) + '.receipt.json') for path in predictions]
        final = HERE / 'final_join'
        bundle = EXPERIMENT / 'supplement_staging/guidance'
        if final.exists() or (bundle / 'MANIFEST.json').exists():
            raise FileExistsError('Final execution or bundle already exists; inspect before proceeding')
        deadline = time.monotonic() + 1800
        while not all(path.is_file() for path in predictions + receipts):
            if time.monotonic() >= deadline:
                raise TimeoutError('Final T3 receipts not ready within bounded wait')
            print(json.dumps({'at': datetime.now(timezone.utc).isoformat(),
                              'waiting_for_T3_receipts': [p.name for p in receipts if not p.is_file()]}), flush=True)
            time.sleep(30)
        for path, receipt_path in zip(predictions, receipts):
            receipt = json.loads(receipt_path.read_text())
            if receipt['count'] != 1913 or receipt['split'] != 'final' or receipt['predictions_sha256'] != sha(path):
                raise ValueError('Final prediction/receipt identity mismatch: ' + path.name)
        commands = [
            [sys.executable, '-B', str(HERE / 'evaluate_guidance.py'),
             '--sources', str(EXPERIMENT / 'pipeline/final.sources.jsonl'),
             '--c-results', str(EXPERIMENT / 'pipeline/final_C.jsonl'),
             '--predictions', *map(str, predictions), '--output', str(final),
             '--freeze', str(HERE / 'final_join_inputs.json'), '--split', 'final'],
            [sys.executable, '-B', str(HERE / 'audit_final_heads.py'),
             '--predictions', *map(str, predictions), '--output', str(final / 'head_distribution_audit.json')],
            [sys.executable, '-B', str(HERE / 'build_guidance_bundle.py')],
            [sys.executable, '-B', str(bundle / 'reproduce_guidance.py'),
             '--output', str(HERE / 'portable_reproduction.json')],
        ]
        runs = []
        for index, command in enumerate(commands):
            before = time.monotonic()
            with (HERE / f'final_stage_{index + 1}.log').open('x') as output:
                result = subprocess.run(command, cwd=EXPERIMENT.parents[2], stdout=output,
                                        stderr=subprocess.STDOUT, timeout=1800)
            runs.append({'stage': index + 1, 'returncode': result.returncode,
                         'wall_seconds': time.monotonic() - before})
            print(json.dumps(runs[-1]), flush=True)
            if result.returncode:
                raise RuntimeError(f'Final guidance stage {index + 1} failed; retained log requires inspection')
        report = {'schema': 'autoformalization-final-guidance-execution-completion/v1',
                  'completed_at': datetime.now(timezone.utc).isoformat(),
                  'orchestrator_sha256': sha(Path(__file__)), 'runs': runs,
                  'elapsed_seconds_including_wait': time.monotonic() - started,
                  'summary_sha256': sha(final / 'summary.json'),
                  'bundle_manifest_sha256': sha(bundle / 'MANIFEST.json'),
                  'portable_reproduction_sha256': sha(HERE / 'portable_reproduction.json'),
                  'scientific_settings_changed': False}
        with (HERE / 'completion.json').open('x') as output:
            output.write(json.dumps(report, indent=2) + '\n')
        print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
