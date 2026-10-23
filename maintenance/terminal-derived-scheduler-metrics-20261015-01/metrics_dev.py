"""Retain real native metric compiler development attempts and their input pins."""
import argparse
import json
from pathlib import Path
import traceback
from jsonl_io import ROOT, PREDECESSOR, PREDECESSOR_MANIFEST_SHA, inputs, read, write, sha, pin


def main(label, smoke):
    if Path(label).name != label or not label.startswith('dev-metrics-'):
        raise ValueError('fresh metric development label required')
    report_path = ROOT / (label + '-development-report.json')
    if report_path.exists() or (ROOT / label).exists():
        raise ValueError('exclusive development attempt required')
    from metrics_lean import build_metrics_theory, compile_metrics_theory, producer_paths, _kernel, _run_lean
    paths = set(producer_paths()) | {ROOT / name for name in (
        'metrics_dev.py', 'env_run.py', 'launch.py', 'jsonl_io.py', 'source_profile.py', 'source_metrics.py',
        'source_metric_bridge.py', 'source_metric_cases.py', 'jsonl_cases.py', 'observed_files.py', 'strict_jsonl.py')}
    before = [pin(path) for path in sorted(paths)]
    write(ROOT / (label + '-producer-pins.json'), {'before': before, 'qualification_evidence': False,
        'complete_loaded_code_closure': False})
    try:
        if not smoke:
            manifest_raw = read(PREDECESSOR / 'evidence-manifest.json', 1024**2)
            if sha(manifest_raw) != PREDECESSOR_MANIFEST_SHA:
                raise ValueError('sealed predecessor changed')
            inventory = {row['path']: row for row in json.loads(manifest_raw)['files']}
            name = 'experiment-01/base-materials.json'
            raw = read(PREDECESSOR / name, 32 * 1024**2)
            if len(raw) != inventory[name]['bytes'] or sha(raw) != inventory[name]['sha256']:
                raise ValueError('selected public predecessor base changed')
            base = json.loads(raw)
            from source_profile import build_source_profile
            from source_metric_bridge import SOURCE_PATH
            from source_metric_cases import run_metric_cases
            source_raw = inputs()[1][SOURCE_PATH]
            profile = build_source_profile(source_raw, source_path=SOURCE_PATH, head=base['contract']['head'])
            cases = run_metric_cases(output=ROOT / (label + '-files'), contract=base['contract'],
                                     source_profile=profile, source_raw=source_raw)
            write(ROOT / (label + '-case-report.json'), cases)
            theory = build_metrics_theory(report=cases)
            write(ROOT / (label + '-theory.json'), theory)
        from native_structural_ir import _scheduler
        from ipfs_datasets_py.optimizers.logic_theorem_optimizer.resource_scheduler import ResourceLane
        with _scheduler().acquire(ResourceLane.ORCHESTRATION, cpu_slots=1, memory_mb=2048,
                child_process_slots=1, timeout=30, request_id='terminal-derived-metrics:' + label) as lease:
            if smoke:
                output = ROOT / label
                output.mkdir(mode=0o700)
                source = _kernel() + '\nnamespace DecoderKernel\n' + \
                    'theorem metric_smoke : prefillCost 64 = 270336 := by decide\n' + \
                    '#print axioms metric_smoke\nend DecoderKernel\n'
                evidence = _run_lean(source=source, label='metric-smoke', output=output, lease=lease, expected_success=True)
                if evidence['matches_expectation'] is not True:
                    raise ValueError('native metric kernel smoke did not pass')
            else:
                evidence = compile_metrics_theory(theory, output=ROOT / label, lease=lease)
        report = {'completed': True, 'native_evidence': evidence, 'smoke_only': smoke,
            'qualification_evidence': False, 'source_body_execution': False,
            'external_provider_calls': 0, 'new_optimizer_updates': 0}
    except BaseException as error:
        report = {'completed': False, 'exception_class': type(error).__name__, 'message': str(error),
            'smoke_only': smoke, 'qualification_evidence': False, 'source_body_execution': False,
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
    parser.add_argument('--smoke', action='store_true')
    args = parser.parse_args()
    main(args.label, args.smoke)
