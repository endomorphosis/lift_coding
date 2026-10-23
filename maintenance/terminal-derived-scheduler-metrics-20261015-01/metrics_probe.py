"""Owned, bounded native reduction diagnostics; not qualification evidence."""
import argparse
from pathlib import Path
import metrics_lean as M


def main(label, probe):
    from jsonl_io import write, pin
    from native_structural_ir import _scheduler
    from ipfs_datasets_py.optimizers.logic_theorem_optimizer.resource_scheduler import ResourceLane
    if Path(label).name != label or not label.startswith('dev-metric-probe-'):
        raise ValueError('fresh owned diagnostic label required')
    output = M.ROOT / label
    if output.exists():
        raise ValueError('exclusive diagnostic output required')
    before = [pin(path) for path in M.producer_paths() + [Path(__file__)]]
    request = '{ id := [114], prompt := 64, generated := 1 }'
    row = '{ id := [114], batch := [98], shape := { seq := 64, heads := 32, hidden := 4096 } }'
    metrics = '{ cost := {numerator:=12977792,denominator:=1}, padding := {numerator:=0,denominator:=65}, latency := {numerator:=5179024,denominator:=2500}, sequential := {numerator:=5179024,denominator:=2500} }'
    expressions = {
        'empty': 'derivedMetrics [] [] = some { cost:={numerator:=0,denominator:=1},padding:={numerator:=0,denominator:=1},latency:={numerator:=0,denominator:=2500},sequential:={numerator:=0,denominator:=2500} }',
        'single': 'derivedMetrics [' + request + '] [' + row + '] = some ' + metrics,
        'lookup': '(metricBatches [' + request + '] [' + row + ']).isSome = true',
        'square': 'sumSquares 4096 1024 = 21828032000',
        'batch': '(batchFromRequests [98] {seq:=64,heads:=32,hidden:=4096} [' + request + ']).cost = 405504',
        'latency': 'p95Units [5179024] = 5179024',
    }
    if probe in ('shard0', 'shard3', 'case0', 'case0kernel', 'case0decode', 'case0calc', 'case0metric', 'case0both', 'case0outcome', 'model0'):
        import json
        source = M.build_metrics_theory(report=json.loads(M._read(M.ROOT / 'dev-metrics-07-case-report.json')))['sources'][3 if probe == 'shard3' else 0]['source']
        if probe.startswith('case0'):
            source = source.split('def metricRaw4')[0] + '\nend DecoderKernel\n'
        if probe == 'case0kernel':
            source = source.replace('by decide', 'by decide +kernel').replace('\n  decide\n', '\n  decide +kernel\n')
        elif probe == 'case0decode':
            source = source.split('def metricCase0Bucket1')[0] + '\nend DecoderKernel\n'
        elif probe == 'case0calc':
            source = source.split('theorem exact_metrics_0_1')[0] + '\nend DecoderKernel\n'
        elif probe == 'case0metric':
            source = source.split('def metricCase0Bucket2')[0] + '\nend DecoderKernel\n'
        elif probe == 'case0both':
            source = source.split('theorem exact_derived_outcome_0')[0] + '\nend DecoderKernel\n'
        elif probe == 'case0outcome':
            source = source.split('def decodedDerivedOutcome0')[0] + '\nend DecoderKernel\n'
        elif probe == 'model0':
            from copy import deepcopy
            report = json.loads(M._read(M.ROOT / 'dev-metrics-07-case-report.json'))
            entry = report['entries'][0]
            buckets = deepcopy(entry['model']['case']['buckets'])
            for bucket in buckets:
                bucket['metrics'] = M._raw_metrics(entry['derived_metrics'][str(bucket['bucket_id'])])
            source = M._kernel() + '\nnamespace DecoderKernel\n'
            source += 'theorem reduction_probe : modelAccept ' + M.D._bucket(buckets[0]) + ' ' + M.D._bucket(buckets[1]) + ' = true := by decide +kernel\n#print axioms reduction_probe\nend DecoderKernel\n'
    elif probe.startswith('quotient'):
        n = int(probe[8:])
        dividend = n * (n - 1) * (2 * n - 1)
        quotient = dividend // 6
        expected = n*64*64 + 64*n*(n-1) + quotient
        source = M._kernel() + '\nnamespace DecoderKernel\n'
        source += 'theorem quotient_probe : (' + str(n) + '*(' + str(n) + '-1)*(2*' + str(n) + '-1))/6 = ' + str(quotient) + ' := Nat.div_eq_of_lt_le (by decide) (by decide)\n'
        source += 'theorem reduction_probe : sumSquares 64 ' + str(n) + ' = ' + str(expected) + ' := by\n  unfold sumSquares\n  rw [quotient_probe]\n#print axioms reduction_probe\nend DecoderKernel\n'
    else:
        tactic = 'decide +kernel' if probe == 'square' else 'decide'
        source = M._kernel() + '\nnamespace DecoderKernel\ntheorem reduction_probe : ' + expressions[probe] + ' := by ' + tactic + '\n#print axioms reduction_probe\nend DecoderKernel\n'
    output.mkdir(mode=0o700)
    with _scheduler().acquire(ResourceLane.ORCHESTRATION, cpu_slots=1, memory_mb=2048,
            child_process_slots=1, timeout=30, request_id='terminal-metric-reduction:' + label) as lease:
        result = M._run_lean(source=source, label=probe, output=output, lease=lease, expected_success=True)
    after = [pin(path) for path in M.producer_paths() + [Path(__file__)]]
    write(output / 'diagnostic.json', {'qualification_evidence': False, 'before': before,
        'after': after, 'selected_producers_unchanged': before == after, 'result': result})
    print({key: result[key] for key in ('status','elapsed_seconds','resource_exhausted','stdout')})


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--label', required=True)
    parser.add_argument('--probe', choices=('empty','single','lookup','square','batch','latency','shard0','shard3','case0','case0kernel','case0decode','case0calc','case0metric','case0both','case0outcome','model0','quotient147','quotient1024'), required=True)
    args = parser.parse_args()
    main(args.label, args.probe)
