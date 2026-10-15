"""Curate the isolated source patch, incremental checks and public measurements."""
import ast
import difflib
import hashlib
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
CHECKOUT = Path('/home/barberb/lift_coding/maintenance/terminal-token-reduction-20261007-01/checkout')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def save(name, value):
    target = ROOT / name
    if target.exists():
        raise FileExistsError(target)
    target.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


before = {}
origins = {}


def baseline(relative, raw, expected, origin):
    assert (sha(raw) if raw is not None else None) == expected
    if relative in before:
        assert before[relative] == raw
    before[relative] = raw
    origins[relative] = origin


for row in json.loads((ROOT / 'baseline.json').read_text())['files']:
    relative = row['path']
    raw = (ROOT / 'baseline' / relative).read_bytes() if row['exists'] else None
    baseline(relative, raw, row['sha256'], 'baseline.json')
for name in ('library-baseline.json', 'selector-baseline.json'):
    for row in json.loads((ROOT / name).read_text())['files']:
        baseline(row['path'], Path(row['snapshot']).read_bytes(), row['sha256'], name)
control = json.loads((ROOT / 'control-baseline.json').read_text())
for relative, row in control['files'].items():
    baseline(relative, Path(row['baseline']).read_bytes(), row['sha256'], 'control-baseline.json')
for relative in control['absent_files']:
    baseline(relative, None, None, 'control-baseline.json')
for row in json.loads((ROOT / 'frontier-qualification-baseline/baseline.json').read_text())['files']:
    relative = row['path']
    raw = (ROOT / 'frontier-qualification-baseline' / relative).read_bytes() if row['exists'] else None
    baseline(relative, raw, row.get('sha256'), 'frontier-qualification-baseline/baseline.json')
baseline('test/api/semantic_state/test_code_retrieval_frontier_dispatch.py', None, None,
         'root created this new test with apply_patch during this turn')

scratch = ROOT / 'patch-baseline-check'
scratch.mkdir(exist_ok=False)
parts = []
changes = []
for relative, old in sorted(before.items()):
    source = CHECKOUT / relative
    current = source.read_bytes() if source.exists() else None
    if current == old:
        continue
    assert current is not None, 'No deletions belong to this implementation'
    if relative.endswith('.py'):
        ast.parse(current, filename=relative)
    if old is not None:
        target = scratch / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(old)
    parts.append(''.join(difflib.unified_diff(old.decode().splitlines(keepends=True) if old is not None else [],
        current.decode().splitlines(keepends=True), fromfile='a/' + relative if old is not None else '/dev/null',
        tofile='b/' + relative)))
    changes.append({'path': relative, 'before_sha256': sha(old) if old is not None else None,
        'after_sha256': sha(current), 'after_bytes': len(current), 'baseline_provenance': origins[relative]})
assert len(changes) == 17, len(changes)
patch = ''.join(parts).encode()
patch_path = ROOT / 'changes.patch'
assert not patch_path.exists()
patch_path.write_bytes(patch)
check = subprocess.run(['git', 'apply', '--check', '--whitespace=error', str(patch_path)],
                       cwd=scratch, capture_output=True, text=True)
assert check.returncode == 0, check.stderr
save('source-manifest.json', {'schema': 'terminal-bounded-context-source-manifest@1',
    'checkout': str(CHECKOUT), 'baseline_is_saved_overlay_not_git_head': True,
    'checkout_base_head': '03eb84149cac3de7e16a99148466e4ad9327cb79', 'files': changes,
    'patch': {'path': str(patch_path), 'sha256': sha(patch), 'bytes': len(patch), 'apply_check_passed': True},
    'python_source_syntax_parsed': True, 'fixture_state_exported': False,
    'committed': False, 'pushed': False, 'new_runtime_archive_built_or_deployed': False})

reports = ['library-validation-02.xml', 'selector-validation-01.xml', 'control-validation-01.xml',
    'control-integration-validation-01.xml', 'comparison-validation-01.xml',
    'dispatch-validation-01.xml', 'dispatch-validation-02.xml',
    'frontier-tests-03/tests.xml', 'frontier-tests-04/tests.xml']
identities = set()
suites = []
for relative in reports:
    path = ROOT / relative
    raw = path.read_bytes()
    cases = list(ET.fromstring(raw).iter('testcase'))
    current_ids = {(case.get('classname', '').removeprefix('test.'), case.get('name', '')) for case in cases}
    counts = {tag: sum(len(case.findall(tag)) for case in cases) for tag in ('failure', 'error', 'skipped')}
    assert not any(counts.values()), (relative, counts)
    suites.append({'path': str(path), 'sha256': sha(raw), 'passing_records': len(cases),
                   'overlap_with_earlier_suites': len(current_ids & identities), **counts})
    identities |= current_ids
save('validation.json', {'schema': 'terminal-bounded-context-validation@1', 'suites': suites,
    'distinct_logical_passing_cases_across_incremental_runs': len(identities),
    'passing_records': sum(row['passing_records'] for row in suites),
    'deduplication': 'classname with optional test. prefix removed plus parametrized testcase name',
    'final_source_frontier_qualification': {'path': str(ROOT / 'frontier-tests-04/result.json'), 'passed': 13,
        'loaded_producers_unchanged': True, 'coverage': ['positive selection', 'exact fallback',
            'all deferred hits recovered exactly', 'read-only cache and configured metadata witness',
            'real expansion CLI from another working directory without inherited Python path',
            'native task/source bindings', 'suppression restoration on success/error', 'forged source selectors']},
    'incremental_provenance': [
        'The earlier full frontier suite has 58 passing cases on its recorded loaded producers; the vector source and test file changed on disk during that run.',
        'The final frozen-source subset has 13 passing cases, including the three new forged selector cases; union is 61 frontier cases.',
        'Eight native dispatch cases were repeated after metadata-owner suppression; the preceding 22-case route/default integration result is retained.',
        'The transport test docstring changed after the 22-case actual native preparation run; exact behavioral source equivalence is recorded in control-integration-validation-final.json.'],
    'scope': 'Focused incremental validation, not the whole repository suite',
    'real_provider_calls': 0, 'superseded_failed_attempts_preserved': True})

measurement_path = ROOT / 'measurement-public-bottle-04/measurement.json'
measurement = json.loads(measurement_path.read_text())
assert measurement['producer_pins_before'] == measurement['producer_pins_after']
matches = {name: sha(Path(row['path']).read_bytes()) == row['sha256']
           for name, row in measurement['producer_pins_after'].items()}
assert all(matches.values()), matches
final_frontier = json.loads((ROOT / 'frontier-tests-04/result.json').read_text())
assert final_frontier['pytest_exit_code'] == 0 and final_frontier['sources_unchanged'] is True
save('token-reduction-summary.json', {'schema': 'terminal-bounded-retrieval-token-summary@1',
    'measurement': str(measurement_path), 'measurement_sha256': sha(measurement_path.read_bytes()),
    'stages': measurement['stages'], 'native_bindings': measurement['native_bindings'],
    'preservation': measurement['preservation'], 'claims': measurement['claims'],
    'producer_pins_match_final_sources': matches, 'limitations': measurement['limitations'],
    'no_combination_with_prior_compact_intent_percentages': True,
    'actual_full_coding_prompt_or_cumulative_provider_usage_measured': False})
save('next-work.json', {'schema': 'terminal-bounded-context-next-work@1', 'implemented': [
    'Explicit full/frontier retrieval control through benchmark, Harbor, native preparation and signed nominations',
    'Complete task-bound DuckDB manifest, bounded initial advisory hits and explicit recoverable frontier',
    'Native source/index/query replay and full manifest equality independent of cache claims',
    'Exact source selector checks, mandatory census and complete packet budgets',
    'Read-only public expansion without metadata-owner activation', 'Separate experiment accounting'],
    'remaining': [
        {'order': 1, 'work': 'Build a new pinned runtime and qualify the actual installed worker expansion command',
         'checks': ['worker UID can read only public candidate metadata', 'runtime interpreter/imports are pinned',
                    'owner key/state paths remain inaccessible', 'read-only cache and metadata behavior witnessed']},
        {'order': 2, 'work': 'Run matched live full/frontier trials with the coding route exercised',
         'checks': ['same runtime/model/CLI/Doctor/planner/source/learning policies',
                    'capture every planning/coding/retry/failed attempt and expansion cost',
                    'input tokens include cached input exactly once', 'task completion and verifier reward remain distinct',
                    'report unknown setup/usage as unknown; never infer total savings from local token percentages']},
        {'order': 3, 'work': 'Extend bounded disclosure to world and semantic metadata only after qualifying required closure',
         'checks': ['preserve native task/goal constraints, dependencies and literal acceptance commands',
                    'new projection must independently bind and replay the producer inventory',
                    'all deferred source/proof references remain bounded and source-scoped',
                    'metadata projections and neural encoders cannot create proof or completion authority']},
        {'order': 4, 'work': 'Reuse scoped formal proof receipts and train task/codebase encoders for evidence nomination',
         'checks': ['bind source/task/query/index/toolchain/premise/kernel versions before cache reuse',
                    'separate empirical held-out quality from formal source equivalence or convergence claims',
                    'measure avoided provider calls and total tokens per independent verifier success']}],
    'ducklake_scope': 'Existing catalog projections remain available; this new frontier uses a fresh local DuckDB manifest cache. The read-only lake witness is a configured directory sentinel, not a new DuckLake-extension hydration qualification.'})
save('implementation.json', {'schema': 'terminal-bounded-context-implementation@1',
    'checkout': str(CHECKOUT), 'changed_source_files': len(changes),
    'change': 'Task-bound progressive disclosure of advisory code retrieval through persisted manifests and source-replayed public expansion',
    'opt_in': '--code-retrieval-transport frontier', 'default': 'full', 'requires_full_indexed_arm': True,
    'initial_hit_limit': 2, 'complete_query_hit_bound': 20,
    'unchanged_required_paths': ['literal instruction', 'task IntentIR', 'semantic producer capsules',
                                 'world context', 'native acceptance and validation'],
    'source_manifest': 'source-manifest.json', 'reviewable_patch': 'changes.patch',
    'validation': 'validation.json', 'distinct_logical_passing_cases_across_incremental_runs': len(identities),
    'measurements': 'token-reduction-summary.json', 'next_work': 'next-work.json',
    'actual_native_preparation_and_signed_bundle_tested': True,
    'actual_expansion_cli_from_other_directory_tested': True,
    'actual_installed_container_worker_qualified': False, 'new_runtime_archive_built_or_deployed': False,
    'provider_calls': 0, 'live_trial_run': False, 'committed_or_pushed': False,
    'scope': 'Changes restricted to the isolated checkout and this evidence directory; original repository changes preserved.',
    'limitations': measurement['limitations']})
print(json.dumps({'changed_files': len(changes), 'patch_apply_check': True,
    'distinct_logical_passing_cases': len(identities), 'final_measurement_producers_match': all(matches.values())}))
