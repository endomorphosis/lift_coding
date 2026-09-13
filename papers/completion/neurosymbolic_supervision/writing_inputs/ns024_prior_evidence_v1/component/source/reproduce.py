"""Unsigned numerical replay only; no original signature, source-tree or oracle replay."""
import argparse
import ast
import collections
import datetime as dt
from pathlib import Path
from common import decode, digest, encoded, number, public_check, read_bytes

ANALYZER_SHA = 'a8bcf67cccb9c4175b1ac1a2186994d9497e176e79c4fae1ad495d4db9d519db'
SUMMARY_FIELDS = ('complete', 'planned_cells', 'terminal_cells', 'unissued_or_nonterminal',
                  'actual_provider_posts', 'actual_cold_scores', 'outcomes', 'useful_completions',
                  'observed_api_usage', 'gateway_proposal_elapsed_sum_seconds',
                  'gateway_score_elapsed_known_sum_seconds', 'groups', 'batch_sha256')

def summarize_pilot(rows, source, batch):
    assert digest(source) == ANALYZER_SHA
    assert len(rows) == 24 and len({r['cell_id'] for r in rows}) == 24
    assert [r['number'] for r in rows] == list(range(1, 25))
    assert all(r['terminal'] is True for r in rows)
    assert len({r['unit'] for r in rows}) == 4
    for unit in {r['unit'] for r in rows}:
        for arm in ('A', 'B'):
            group = [r for r in rows if r['unit'] == unit and r['arm'] == arm]
            assert len(group) == 3 and len({r['repetition'] for r in group}) == 3
    for row in rows:
        assert type(row['useful_completion']) is bool and type(row['actual_cold_scored']) is bool
        assert row['useful_completion'] == (row['outcome'] == 'full_cold_pass')
        assert not row['useful_completion'] or row['actual_cold_scored']
        number(row['gateway_proposal_elapsed_seconds'], False)
        number(row['gateway_score_elapsed_seconds'])
    # Execute only the exact original group/usage/summary arithmetic, never its
    # main(), private-file reader, provider/client imports or command-line path.
    main = next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == 'main')
    def assignment(node, name):
        return isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets)
    begin = next(i for i, n in enumerate(main.body) if assignment(n, 'groups'))
    end = next(i for i, n in enumerate(main.body) if assignment(n, 'summary'))
    code = compile(ast.fix_missing_locations(ast.Module(body=main.body[begin:end+1], type_ignores=[])), '<exact-original-pilot-arithmetic>', 'exec')
    env = dict(rows=rows, terminal_rows=rows, collections=collections, dt=dt, a={'batch': {'sha256': batch}})
    exec(code, env)
    summary = {k: env['summary'][k] for k in SUMMARY_FIELDS}
    summary['legacy_child_overruns_595'] = [{'number': r['number'], 'seconds': r['provider_child_elapsed_seconds'],
                                          'excess_seconds': r['provider_child_elapsed_seconds']-595}
                                         for r in rows if r['provider_child_elapsed_seconds'] is not None and r['provider_child_elapsed_seconds'] > 595]
    summary['legacy_wrapper_or_gateway_overruns_600'] = [r['number'] for r in rows if r['http_wrapper_elapsed_seconds'] > 600 or r['gateway_proposal_elapsed_seconds'] > 600]
    summary['resource_reclassification_applied'] = False
    return summary

def cost_summary(records):
    assert len({r['record_id'] for r in records}) == len(records)
    summary = {}
    for record in records:
        assert record['clock_relation'] in ('nested_do_not_add', 'separate_interval', 'lifecycle_not_compute')
        group = summary.setdefault(record['scope'], dict(records=0, clocks={}))
        group['records'] += 1
        for key, value in record['measurements'].items():
            number(value)
            memory = 'memory' in key
            aggregate = 'maximum_observed' if memory else 'known_sum'
            item = group['clocks'].setdefault(key, {aggregate: None if memory else 0, 'observed_records':0, 'unknown_records':0})
            if value is None:
                item['unknown_records'] += 1
            else:
                item[aggregate] = max(value, item[aggregate]) if memory and item[aggregate] is not None else value if memory else item[aggregate]+value
                item['observed_records'] += 1
    return dict(schema='ns-prior-separated-cost-summary/v1', scopes=summary,
                grand_total=None, cross_clock_or_cross_scope_addition=False,
                known_sums_are_partial_measurements_not_complete_experiment_cost=True)

def replay(root):
    root = Path(root)
    manifest = decode(read_bytes(root/'manifest.json'))
    assert manifest['schema'] == 'ns-anonymous-prior-component/v1'
    assert manifest['signature_authentication_of_derived_records'] is False
    expected = set(manifest['members']) | {'manifest.json'}
    actual = {str(p.relative_to(root)) for p in root.rglob('*') if p.is_file() or p.is_symlink()}
    assert expected == actual, 'component inventory differs'
    for name, row in manifest['members'].items():
        assert not Path(name).is_absolute() and '..' not in Path(name).parts
        raw = read_bytes(root/name, row['sha256'])
        assert len(raw) == row['bytes']
        public_check(raw)
    rows = [decode(line) for line in read_bytes(root/'pilot/rows.jsonl').splitlines()]
    expected_pilot = decode(read_bytes(root/'pilot/summary.json'))
    actual_pilot = summarize_pilot(rows, read_bytes(root/'source/original_pilot_analyze.py'), expected_pilot['batch_sha256'])
    assert actual_pilot == expected_pilot, 'pilot numerical replay differs'
    records = [decode(line) for line in read_bytes(root/'costs/records.jsonl').splitlines()]
    assert cost_summary(records) == decode(read_bytes(root/'costs/summary.json')), 'cost arithmetic differs'
    return dict(success=True, pilot_cells=24, families=4, useful=actual_pilot['useful_completions'],
                cost_records=len(records), indexed_members=len(manifest['members']),
                all_files=len(expected), original_signature_reverification=False,
                new_provider_scorer_native_calls=0)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('component', type=Path, nargs='?', default=Path(__file__).resolve().parent.parent)
    args = parser.parse_args()
    print(encoded(replay(args.component)).decode(), end='')
