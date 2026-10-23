#!/usr/bin/env python3
"""Verify the anonymous payload, reproduce component metrics, and regenerate tables."""
import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent

def sha(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(chunk)
    return value.hexdigest()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--proofs', action='store_true', help='Also replay admitted proofs using Lean 4.33.1 on PATH')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    manifest = json.loads((HERE / 'MANIFEST.json').read_text())
    for item in manifest['files']:
        assert sha(HERE / item['path']) == item['sha256'], item['path']
    for table_path, component_path in json.loads((HERE / 'TABLE_COMPONENT_LINKS.json').read_text()).items():
        assert json.loads((HERE / 'table_inputs' / table_path).read_text()) == json.loads((HERE / component_path).read_text()), ('Table/component summary differs', table_path)
    proof_cost = json.loads((HERE / 'table_inputs/assistance/paper_ready_numbers.json').read_text())
    qualification = json.loads((HERE / 'proof/qualification/summary.json').read_text())
    assert proof_cost['qualification_inference_seconds'] == qualification['inference_wall_seconds']
    with tempfile.TemporaryDirectory(prefix='af-reproduction-') as temporary:
        work = Path(temporary)
        commands = [
            ([sys.executable, 'reproduce.py'], HERE / 'pipeline'),
            ([sys.executable, 'reproduce.py', '--output', str(work / 'autoencoder')], HERE / 'autoencoder'),
            ([sys.executable, 'reproduce_guidance.py', '--output', str(work / 'guidance.json')], HERE / 'guidance'),
            ([sys.executable, 'verify_counts.py'], HERE / 'natural'),
            ([sys.executable, 'verify_counts.py'], HERE / 'proof'),
            ([sys.executable, str(HERE / 'generate_paper_tables.py'), '--root', str(HERE / 'table_inputs'), '--output', str(work / 'tables')], HERE),
        ]
        if args.proofs:
            commands.append(([sys.executable, 'verify_proofs.py', '--output', str(work / 'proofs.json')], HERE / 'proof'))
        runs = []
        for index, (command, cwd) in enumerate(commands):
            result = subprocess.run(command, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=300)
            runs.append({'component': cwd.name, 'returncode': result.returncode, 'output': result.stdout})
            if result.returncode:
                print(result.stdout)
                raise RuntimeError(f'Reproduction failed for {cwd.name}')
        tables = []
        for expected in sorted((HERE / 'published_tables').glob('*.tex')):
            actual = work / 'tables' / expected.name
            assert actual.read_bytes() == expected.read_bytes(), expected.name
            tables.append({'name': expected.name, 'sha256': sha(actual)})
        report = {'all_payload_hashes_match': True, 'all_component_reproductions_passed': True,
                  'tables_exact_match': tables, 'proof_replay_requested': args.proofs, 'runs': runs,
                  'fresh_model_inference_performed': False}
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps({k: v for k, v in report.items() if k != 'runs'}, indent=2))

if __name__ == '__main__':
    main()
