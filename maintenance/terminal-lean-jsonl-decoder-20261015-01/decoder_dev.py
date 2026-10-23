"""Retain development compiler attempts under the original shared native policy."""
import argparse
import json
from pathlib import Path
import traceback
from jsonl_io import ROOT, PREDECESSOR, PREDECESSOR_MANIFEST_SHA, read, write, sha, pin


def main(label):
    if Path(label).name != label or not label.startswith('dev-decoder-'):
        raise ValueError('fresh named decoder development attempt required')
    report_path = ROOT / (label + '-development-report.json')
    if report_path.exists() or (ROOT / label).exists():
        raise ValueError('development attempt must be exclusive')
    manifest_raw = read(PREDECESSOR / 'evidence-manifest.json', 1024**2)
    if sha(manifest_raw) != PREDECESSOR_MANIFEST_SHA:
        raise ValueError('sealed predecessor changed')
    inventory = {row['path']: row for row in json.loads(manifest_raw)['files']}
    name = 'experiment-01/file-case-report.json'
    raw = read(PREDECESSOR / name, 32 * 1024**2)
    if len(raw) != inventory[name]['bytes'] or sha(raw) != inventory[name]['sha256']:
        raise ValueError('named public predecessor fixture changed')
    from decoder_witnesses import build_decoder_witnesses
    from decoder_lean import build_decoder_theory, compile_decoder_theory, producer_paths
    paths = set(producer_paths()) | {ROOT / name for name in (
        'decoder_dev.py', 'env_run.py', 'launch.py', 'decoder_witnesses.py',
        'strict_jsonl.py', 'jsonl_lean.py', 'jsonl_io.py')}
    before = [pin(path) for path in sorted(paths)]
    write(ROOT / (label + '-producer-pins.json'), {'before': before, 'complete_loaded_code_closure': False,
        'input': {'path': str(PREDECESSOR / name), 'bytes': len(raw), 'sha256': sha(raw)},
        'qualification_evidence': False})
    try:
        witnesses = build_decoder_witnesses(filecases=json.loads(raw))
        theory = build_decoder_theory(witnesses=witnesses)
        from native_structural_ir import _scheduler
        from ipfs_datasets_py.optimizers.logic_theorem_optimizer.resource_scheduler import ResourceLane
        with _scheduler().acquire(ResourceLane.ORCHESTRATION, cpu_slots=1, memory_mb=2048,
                child_process_slots=1, timeout=30, request_id='terminal-lean-jsonl-decoder:' + label) as lease:
            evidence = compile_decoder_theory(theory, output=ROOT / label, lease=lease)
        report = {'completed': True, 'native_evidence': evidence,
            'qualification_evidence': False, 'source_body_execution': False,
            'external_provider_calls': 0, 'new_optimizer_updates': 0}
    except BaseException as error:
        report = {'completed': False, 'exception_class': type(error).__name__, 'message': str(error),
            'qualification_evidence': False, 'source_body_execution': False,
            'external_provider_calls': 0, 'new_optimizer_updates': 0}
        traceback.print_exc()
    after = [pin(path) for path in sorted(paths)]
    report['selected_producers_unchanged'] = before == after
    report['after'] = after
    write(report_path, report)
    print(json.dumps({key: value for key, value in report.items() if key not in {'after', 'native_evidence'}}))
    if not report['completed'] or not report['selected_producers_unchanged']:
        raise SystemExit(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--label', required=True)
    main(parser.parse_args().label)
