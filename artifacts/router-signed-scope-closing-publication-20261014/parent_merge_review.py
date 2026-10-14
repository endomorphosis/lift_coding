"""Audit a retained parent merge and datasets qualification; never rerun tests.

Original publication receipts remain historical and immutable. A new run whose
only failed guard is an observed shared-ref change may qualify its fixed source
and test outcome; that exception never rewrites or relabels the raw run status.
"""
from __future__ import annotations

import collections
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import stat
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
PHASE = Path(__file__).resolve().parent
ACCEL = Path('/home/barberb/lift_coding/.worktrees/router-signed-scope-closing-20261014')
DATASETS = Path('/home/barberb/lift_coding/.worktrees/router-signed-scope-closing-datasets-20261014')
OLD_DATASETS = Path('/home/barberb/lift_coding/.worktrees/repository-proof-context-datasets-20261014')
KIT = Path('/home/barberb/lift_coding/.worktrees/repository-proof-context-kit-20261014')
QUALIFIED = '52d841321acf2369d8c5fa33fd0fb4ec7717d93c'
BASE = '67778aeb76dcac7ae19671643255c5b871b2e879'
INCOMING = '012ae8b4af4184784688d694c076572ca1db9b85'
MERGED = 'c507236ed16298543f98b8b13d8c6349fb6e075a'
CHILD = 'cb104896f55a28352feb8cd35c4b9991144c933a'
DATASETS_PIN = 'eb18ab0d24557de46d9bd804e8da69d41049874f'
OLD_EXECUTION = 'a0f60d42f836571a0023515e92dfb0e5724f0d79'
OLD_PARENT_PIN = 'b1fd77597867ad31f1687edc8bff090caf3d3b7d'
KIT_PIN = '40c98c71b95be750509ffdb21e7e5494d91b4e79'
CHILD_PHASE = 'docs/agent_supervisor/evidence/router-signed-scope-closing-20261014/'
NOTE = 'implementation_plan/docs/127-supervisor-signed-scope-closing-2026-10-14.md'
ATTEMPT = PHASE / 'dependency-qualification-01'
OUTPUT = PHASE / 'parent-merge-review.json'
RUNNER = PHASE / 'dataset_qualification_runner.py'
LINK_CHECKER_SHA256 = '596a0038b18d592f2e605643890afc85e457558f7b887932a474557d7586819e'
MAX_BYTES = 64 * 1024 * 1024
NEW_SUITE = 'benchmarks.agent_supervisor.container_coding.test_terminal_signed_working_set_closing'
CHANGED_DATASETS = {
    'ipfs_datasets_py/logic/software_contracts/semantic_index/' + name + '.py'
    for name in ('pytest_analysis', 'python_analysis', 'scanner', 'snapshot', 'symbol_graph')
} | {'ipfs_datasets_py/logic/software_contracts/semantic_state/models.py'}
sys.dont_write_bytecode = True


def need(value, message):
    if not value:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def git(root, *args):
    result = subprocess.run(['git', '--no-optional-locks', *args], cwd=root,
                            capture_output=True, timeout=60)
    need(result.returncode == 0, 'Git observation failed: ' + repr(args))
    need(len(result.stdout) <= MAX_BYTES, 'Git observation exceeds bound')
    return result.stdout


def load(raw, kind=dict):
    need(type(raw) is bytes and len(raw) <= MAX_BYTES, 'bounded JSON bytes required')
    def pairs(rows):
        value = {}
        for key, item in rows:
            need(key not in value, 'duplicate JSON key')
            value[key] = item
        return value
    def nonfinite(_value):
        raise ValueError('nonfinite JSON number')
    value = json.loads(raw, object_pairs_hook=pairs, parse_constant=nonfinite)
    need(type(value) is kind, 'JSON root shape differs')
    return value


def read(path):
    need(path.is_absolute() and path.resolve(strict=True) == path, 'exact evidence path required')
    first = path.lstat()
    need(stat.S_ISREG(first.st_mode) and first.st_nlink == 1 and first.st_size <= MAX_BYTES,
         'bounded single-link evidence file required')
    raw = path.read_bytes()
    last = path.lstat()
    fields = ('st_dev', 'st_ino', 'st_mode', 'st_nlink', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
    need(len(raw) == first.st_size and all(getattr(first, key) == getattr(last, key) for key in fields),
         'evidence changed during read')
    return raw


def binding(path):
    raw = read(path)
    return dict(path=str(path.relative_to(ROOT)), bytes=len(raw), sha256=sha(raw))


def matches(raw, row):
    return (type(row.get('bytes')) is int and len(raw) == row['bytes']
            and type(row.get('sha256')) is str and sha(raw) == row['sha256'])


def state(root):
    return dict(head=git(root, 'rev-parse', 'HEAD').decode().strip(),
                refs_sha256=sha(git(root, 'for-each-ref', '--format=%(refname) %(objectname)')),
                index_sha256=sha(git(root, 'ls-files', '--stage', '-z')))


def tree(root, revision):
    rows = {}
    for row in git(root, 'ls-tree', '-r', '-z', revision).split(b'\0'):
        if row:
            metadata, path = row.split(b'\t', 1)
            need(path not in rows, 'duplicate tree path')
            rows[path] = metadata
    return rows


def source_rows(rows):
    need(type(rows) is list and len(rows) == 268, 'listed source population differs')
    result = {}
    for row in rows:
        need(type(row) is dict and type(row.get('path')) is str, 'invalid source binding')
        name = Path(row['path'])
        need(not name.is_absolute() and '..' not in name.parts and str(name) == row['path'],
             'noncanonical source path')
        identity = (row['repository'], row['path'])
        need(identity not in result, 'duplicate source binding')
        result[identity] = row
    need(collections.Counter(key[0] for key in result)
         == {'accelerator': 217, 'datasets_execution_checkout': 51}, 'source repository counts differ')
    return result


def main():
    need(not OUTPUT.exists(), 'refusing to overwrite merge evidence')
    roots = (ROOT, ACCEL, DATASETS, OLD_DATASETS, KIT)
    before = {str(root): state(root) for root in roots}
    need(before[str(ROOT)]['head'] == MERGED, 'actual parent merge changed')
    parents = git(ROOT, 'rev-parse', MERGED + '^1', MERGED + '^2').decode().splitlines()
    need(parents == [QUALIFIED, INCOMING], 'actual merge parents differ')
    incoming, merged, original = (tree(ROOT, revision) for revision in (INCOMING, MERGED, QUALIFIED))
    need(incoming and all(merged.get(path) == metadata for path, metadata in incoming.items()),
         'incoming tree object or mode was not preserved')
    pins = {'external/ipfs_accelerate': CHILD, 'external/ipfs_datasets': DATASETS_PIN,
            'external/ipfs_kit': KIT_PIN}
    for name, revision in pins.items():
        need(merged[name.encode()] == ('160000 commit ' + revision).encode(), 'merged pin differs')
        need(git(ROOT, 'rev-parse', ':' + name).decode().strip() == revision, 'staged pin differs')
    old_pins = {'external/ipfs_accelerate': CHILD, 'external/ipfs_datasets': OLD_PARENT_PIN,
                'external/ipfs_kit': KIT_PIN}
    need(all(original[name.encode()] == ('160000 commit ' + revision).encode()
             for name, revision in old_pins.items()), 'original qualified dependency pins differ')
    phase_name = str(PHASE.relative_to(ROOT))
    original_files = [PHASE / name for name in (
        'child-ci-observation.json', 'fresh-main-compatibility.json', 'manifest.json',
        'observe_hosted_ci.py', 'parent-checks.json', 'publication_checker.py')]
    expected_owned = {NOTE, 'external/ipfs_accelerate'} | {
        str(path.relative_to(ROOT)) for path in original_files}
    owned = git(ROOT, 'diff', '--name-only', BASE, QUALIFIED).decode().splitlines()
    need(len(owned) == 8 and set(owned) == expected_owned
         and all(original[name.encode()] == merged[name.encode()] for name in owned),
         'original eight qualified objects changed in merge')
    historical = []
    for path in original_files:
        name = str(path.relative_to(ROOT))
        raw = git(ROOT, 'show', QUALIFIED + ':' + name)
        need(raw == read(path), 'original publication artifact changed in working state')
        historical.append(dict(path=name, bytes=len(raw), sha256=sha(raw), revision=QUALIFIED))
    old_checks = load(git(ROOT, 'show', QUALIFIED + ':' + phase_name + '/parent-checks.json'))
    need(old_checks['status'] == 'pass' and old_checks['accelerator_publication'] == CHILD
         and old_checks['datasets_execution_revision'] == OLD_EXECUTION,
         'original publication receipt identity differs')
    old_q_raw = git(ACCEL, 'show', CHILD + ':' + CHILD_PHASE + 'qualification-02/commands.json')
    old_q = load(old_q_raw)
    need(old_q['status'] == 'pass' and old_q['pytest_exit_code'] == 0
         and old_q['datasets_execution_revision'] == OLD_EXECUTION
         and old_q['kit_execution_revision'] == KIT_PIN and old_q['before'] == old_q['after'],
         'historical child qualification differs')
    old_sources = source_rows(old_q['before'])
    inventory = load(git(ACCEL, 'show', CHILD + ':' + CHILD_PHASE + 'source-inventory.json'), list)
    need(len(inventory) == 268 and len({(row['repository'], row['path']) for row in inventory}) == 268
         and {(row['repository'], row['path']) for row in inventory} == set(old_sources),
         'published source inventory differs')
    targets = load(git(ACCEL, 'show', CHILD + ':' + CHILD_PHASE + 'targets.json'), list)
    need(len(targets) == len(set(targets)) == 8 and targets == old_q['targets']
         and all(type(name) is str and name.endswith('.py') and '::' not in name for name in targets),
         'published complete suite roster differs')
    q_raw = read(ATTEMPT / 'commands.json')
    q = load(q_raw)
    need(q['schema'] == 'router-signed-scope-closing-new-datasets-qualification@1'
         and q['status'] in {'pass', 'fail'} and q['child_revision'] == CHILD
         and q['datasets_execution_revision'] == DATASETS_PIN and q['kit_execution_revision'] == KIT_PIN
         and q['parent_merge'] == MERGED and q['targets'] == targets and q['cwd'] == str(ACCEL)
         and q['before'] == q['after'] and q['source_before_after_equal'] is True,
         'new qualification is incomplete or has changed source/identity guards')
    sources = source_rows(q['before'])
    need(set(sources) == set(old_sources), 'new listed dependency population differs')
    need(all(q[name] == 0 and type(q[name]) is int for name in (
        'external_provider_calls', 'model_calls', 'training_steps', 'native_solver_or_kernel_executions'))
         and all(q[name] is False for name in (
             'worker_uid_qualified', 'production_coding_child_adoption', 'proof_authority',
             'execution_authority', 'completion_authority', 'total_session_token_savings_established',
             'previous_counts_added')) and q['official_task_result'] is None
         and q['authored_provider_stubs_exercised'] is True
         and q['actual_inert_socket_client_probes'] is True
         and q['source_binding_scope'] == 'listed_dependencies_not_complete_import_closure',
         'new qualification limits differ')
    q_roots = {str(ROOT): MERGED, str(ACCEL): CHILD, str(DATASETS): DATASETS_PIN, str(KIT): KIT_PIN}
    q_before, q_after = q['git_state_before'], q['git_state_after']
    need(type(q_before) is dict and type(q_after) is dict and set(q_before) == set(q_after) == set(q_roots),
         'qualification Git guard population differs')
    ref_changes = []
    for name, revision in q_roots.items():
        first, last = q_before[name], q_after[name]
        need(type(first) is dict and type(last) is dict
             and set(first) == set(last) == {'head', 'index_sha256', 'refs_sha256'}
             and first['head'] == last['head'] == revision
             and first['index_sha256'] == last['index_sha256']
             and all(type(row[field]) is str and re.fullmatch(r'[0-9a-f]{64}', row[field])
                     for row in (first, last) for field in ('index_sha256', 'refs_sha256')),
             'qualification HEAD/index guard changed')
        if first['refs_sha256'] != last['refs_sha256']:
            ref_changes.append(dict(path=name, before=first['refs_sha256'], after=last['refs_sha256'],
                                    actor_attributed=False))
        if name != str(ROOT):
            need(before[name]['head'] == revision
                 and before[name]['index_sha256'] == last['index_sha256'], 'execution checkout moved after tests')
    need(before[str(OLD_DATASETS)]['head'] == OLD_EXECUTION
         and all(not git(root, 'status', '--porcelain') for root in roots[1:]),
         'fixed execution checkout is dirty or historical datasets HEAD moved')
    need(q['git_state_unchanged'] is (not bool(ref_changes)), 'reported Git guard outcome differs')
    need((q['status'] == 'pass' and not ref_changes)
         or (q['status'] == 'fail' and ref_changes), 'failure is not solely the shared-ref guard')
    artifacts = [ATTEMPT / name for name in ('commands.json', 'junit.xml', 'tests.stdout.log',
                                             'tests.stderr.log', 'runner.snapshot.txt')]
    blobs = {name: read(ATTEMPT / name) for name in ('junit.xml', 'tests.stdout.log', 'tests.stderr.log')}
    need(all(matches(raw, q[name]) for name, raw in blobs.items()), 'new raw test artifact differs')
    xml = ET.fromstring(blobs['junit.xml'])
    cases = [(row.get('classname'), row.get('name')) for row in xml.iter('testcase')]
    outcome = dict(tests=len(cases), failures=sum(1 for _ in xml.iter('failure')),
                   errors=sum(1 for _ in xml.iter('error')), skipped=sum(1 for _ in xml.iter('skipped')))
    suite_counts = dict(collections.Counter(suite for suite, _ in cases))
    expected_suites = {name[:-3].replace('/', '.') for name in targets}
    collected = re.findall(r'^(?:collecting \.\.\. )?collected ([0-9]+) items?\s*$',
                           blobs['tests.stdout.log'].decode('utf-8', 'replace'), re.M)
    need(outcome == q['junit'] == dict(tests=145, failures=0, errors=0, skipped=0)
         and len(cases) == len(set(cases)) == q['distinct_junit_cases'] == 145
         and collected == ['145'] and q['collected_tests'] == 145
         and q['new_cases'] == suite_counts.get(NEW_SUITE) == 18
         and set(suite_counts) == expected_suites and q['suites'] == suite_counts
         and type(q['pytest_exit_code']) is int and q['pytest_exit_code'] == 0,
         'native test collection, raw outcome or new-case roster differs')
    runtime = Path(q['private_runtime_directory'])
    need(runtime.is_absolute(), 'private runtime path must be absolute')
    expected_argv = [q['interpreter'], '-B', '-m', 'pytest', '-c', 'pytest.ini', *targets,
        '--color=no', '--basetemp=' + str(runtime / 'pytest-temp'), '-o', 'log_cli=false',
        '-o', 'cache_dir=' + str(runtime / 'pytest-cache'), '--tb=short', '--maxfail=1',
        '--junitxml=' + str(ATTEMPT / 'junit.xml')]
    need(q['argv'] == expected_argv and q['environment_updates']['PYTHONPATH']
         == ':'.join(map(str, (ACCEL, DATASETS, KIT)))
         and q['environment_updates']['PYTEST_DISABLE_PLUGIN_AUTOLOAD'] == '1'
         and q['environment_updates']['PYTHONDONTWRITEBYTECODE'] == '1',
         'retained execution arguments or module roots differ')
    runner_raw = read(RUNNER)
    need(q['runner_snapshot']['path'] == str((ATTEMPT / 'runner.snapshot.txt').relative_to(ROOT))
         and matches(runner_raw, q['runner_snapshot'])
         and runner_raw == read(ATTEMPT / 'runner.snapshot.txt'), 'datasets runner snapshot differs')
    changed, checked = set(), []
    for identity, row in sources.items():
        repository, name = identity
        root, revision = (ACCEL, CHILD) if repository == 'accelerator' else (DATASETS, DATASETS_PIN)
        raw = git(root, 'show', revision + ':' + name)
        need(row['source_checkout'] == str(root) and row['matches_immutable_git_object'] is True
             and matches(raw, row) and raw == read(root / name), 'listed source differs from Git/current bytes')
        old = old_sources[identity]
        if repository == 'accelerator':
            need(matches(raw, old), 'unchanged published accelerator source differs')
        else:
            old_raw = git(OLD_DATASETS, 'show', OLD_EXECUTION + ':' + name)
            need(matches(old_raw, old) and old_raw == read(OLD_DATASETS / name)
                 and old_raw == git(DATASETS, 'show', OLD_PARENT_PIN + ':' + name),
                 'historical datasets binding changed')
            if raw != old_raw:
                changed.add(name)
        checked.append(dict(row, execution_revision=revision, current_source_checked=True))
    need(changed == CHANGED_DATASETS, 'changed listed datasets population differs')
    snapshots = q['changed_dataset_snapshots']
    need(type(snapshots) is list and len(snapshots) == 6
         and {row['path'] for row in snapshots} == CHANGED_DATASETS, 'changed datasets snapshot roster differs')
    for row in snapshots:
        original_row = sources[('datasets_execution_checkout', row['path'])]
        need({key: row[key] for key in original_row} == original_row,
             'snapshot metadata does not bind its qualified source')
        path = ATTEMPT / 'source-snapshot' / (row['path'] + '.snapshot.txt')
        need(row['snapshot'] == str(path.relative_to(ROOT)) and matches(read(path), row)
             and read(path) == git(DATASETS, 'show', DATASETS_PIN + ':' + row['path']),
             'changed datasets snapshot bytes differ')
        artifacts.append(path)
    need({path for path in ATTEMPT.rglob('*') if path.is_file()} == set(artifacts),
         'qualification artifact inventory differs')
    guarded_paths = [ROOT / NOTE, Path(__file__), RUNNER, *original_files, *artifacts]
    guards = [binding(path) for path in guarded_paths]
    checker_path = ACCEL / 'scripts/docs/check_current_docs_links.py'
    need(sha(read(checker_path)) == LINK_CHECKER_SHA256, 'pinned documentation utility changed')
    spec = importlib.util.spec_from_file_location('supplemental_parent_link_checker', checker_path)
    checker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checker)
    checker.ROOT = ROOT
    allowed = {str(path.relative_to(ROOT)) for path in guarded_paths} | {str(OUTPUT.relative_to(ROOT))}
    changes = git(ROOT, 'status', '--porcelain=v1', '-z', '--untracked-files=all').split(b'\0')
    for row in changes:
        if row:
            need(row[:2] not in {b'R ', b' R', b'C ', b' C'}
                 and row[3:].decode('utf-8') in allowed, 'foreign parent working change')
    # The exclusive placeholder permits checking this note's future receipt
    # link. No pass receipt is written until every closing read guard succeeds.
    with OUTPUT.open('x') as handle:
        need(not checker.check_file(ROOT / NOTE, check_anchors=True), 'parent note links failed')
        after = {str(root): state(root) for root in roots}
        need(before == after and guards == [binding(path) for path in guarded_paths]
             and sha(read(checker_path)) == LINK_CHECKER_SHA256,
             'fresh auditor Git/read guards changed')
        need(all(not git(root, 'status', '--porcelain') for root in roots[1:]),
             'execution checkout became dirty during audit')
        result = dict(schema='router-signed-scope-closing-parent-merge-review@1', status='pass',
            checked_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            qualified_parent_leaf=QUALIFIED, original_parent_base=BASE, incoming_parent=INCOMING,
            actual_merge=MERGED, actual_merge_parents=parents, merged_dependency_pins=pins,
            incoming_tree_objects_checked=len(incoming), all_incoming_tree_objects_preserved=True,
            original_qualified_objects_unchanged_in_merge=owned,
            retained_original_publication_artifacts=historical,
            original_receipts_remain_historical=True, original_datasets_execution_revision=OLD_EXECUTION,
            original_preserved_parent_datasets_pin=OLD_PARENT_PIN,
            original_child_qualification=dict(path=CHILD_PHASE + 'qualification-02/commands.json',
                sha256=sha(old_q_raw)),
            supplemental_qualification=dict(path=str((ATTEMPT / 'commands.json').relative_to(ROOT)),
                sha256=sha(q_raw), raw_status=q['status'], tests=145, new_cases=18, suites=8,
                source_bindings=268, outcome=outcome, pytest_exit_code=0,
                elapsed_seconds=q['elapsed_seconds'], datasets_execution_revision=DATASETS_PIN,
                source_before_after_equal=True, fixed_heads_and_indexes_unchanged=True,
                accepted_ref_guard_only_failure=bool(ref_changes), observed_ref_guard_changes=ref_changes,
                ref_change_actor_attributed=False, previous_counts_added=False),
            changed_listed_datasets_paths=sorted(changed), listed_source_bindings_checked=checked,
            current_note_runner_auditor_and_evidence_bindings=guards,
            documentation_checker_sha256=LINK_CHECKER_SHA256, documentation_notes_checked=[NOTE],
            git_state_before=before, git_state_after=after,
            tests_or_workflow_rerun=False, additional_provider_model_training_solver_docker_calls=0,
            native_coding_child_adoption_qualified=False, worker_uid_qualified=False,
            complete_import_closure_attested=False, proof_authority=False,
            execution_authority=False, completion_authority=False,
            total_session_token_savings_established=False, git_refs_and_index_mutated=False,
            output_self_excluded=True)
        json.dump(result, handle, sort_keys=True, indent=2)
        handle.write('\n')
    print(json.dumps(dict(status='pass', tests=145, new_cases=18, suites=8, bindings=268,
                         actual_merge=MERGED, accepted_ref_guard_only_failure=bool(ref_changes))))


if __name__ == '__main__':
    main()
