"""Check frozen source-delivery publication evidence; never rerun qualification."""
from __future__ import annotations

import argparse
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
CHILD = Path('/home/barberb/lift_coding/.worktrees/router-source-delivery-fences-20261014')
DATASETS = Path('/home/barberb/lift_coding/.worktrees/router-source-delivery-fences-datasets-20261014')
KIT = Path('/home/barberb/lift_coding/.worktrees/repository-proof-context-kit-20261014')
INITIAL_PARENT_BASE = '0bb1beb9330f4e6122f9c6debde9af0ffeb524c6'
CHILD_BASE = '09ad10bd0e6694db7b0570614ab289184a0713c5'
DS = '4b50ae4aac65da9166bd3b24608f32ba7e9fb23d'
KIT_REVISION = '40c98c71b95be750509ffdb21e7e5494d91b4e79'
CHILD_PHASE = 'docs/agent_supervisor/evidence/source-worker-delivery-fences-20261014/'
NOTE = ROOT / 'implementation_plan/docs/128-supervisor-source-delivery-fences-2026-10-14.md'
CHECKS, MANIFEST = PHASE / 'parent-checks.json', PHASE / 'manifest.json'
LINK_CHECKER = 'scripts/docs/check_current_docs_links.py'
LINK_SHA = '596a0038b18d592f2e605643890afc85e457558f7b887932a474557d7586819e'
WORKFLOW_SHA = '0a46fa5b8905600cb9f74adaaec8b8aeb5f89878612a43fb7a847e586bde3763'
NEW_SUITE = 'test.api.test_native_source_worker_delivery'
MAX_BYTES = 64 * 1024 * 1024
sys.dont_write_bytecode = True


def need(value, message):
    if not value:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def git(root, *args):
    result = subprocess.run(['git', '--no-optional-locks', *args], cwd=root,
                            capture_output=True, timeout=60)
    need(result.returncode == 0 and len(result.stdout) <= MAX_BYTES,
         'bounded Git observation failed: ' + repr(args))
    return result.stdout


def load(raw, kind=dict):
    def pairs(rows):
        result = {}
        for key, value in rows:
            need(key not in result, 'duplicate JSON key')
            result[key] = value
        return result
    def nonfinite(_value):
        raise ValueError('nonfinite JSON number')
    need(type(raw) is bytes and len(raw) <= MAX_BYTES, 'bounded JSON bytes required')
    value = json.loads(raw, object_pairs_hook=pairs, parse_constant=nonfinite)
    need(type(value) is kind, 'JSON root shape differs')
    return value


def read(path):
    need(path.is_absolute() and path.resolve(strict=True) == path, 'canonical file required')
    before = path.lstat()
    need(stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and before.st_size <= MAX_BYTES,
         'bounded regular evidence required')
    raw, after = path.read_bytes(), path.lstat()
    fields = ('st_dev', 'st_ino', 'st_mode', 'st_size', 'st_mtime_ns', 'st_ctime_ns', 'st_nlink')
    need(len(raw) == before.st_size and all(getattr(before, field) == getattr(after, field) for field in fields),
         'file changed during read')
    return raw


def path_name(value):
    need(type(value) is str and value and not value.startswith('/')
         and '..' not in Path(value).parts and str(Path(value)) == value, 'relative canonical path required')
    return value


def matches(raw, row):
    return type(row.get('bytes')) is int and len(raw) == row['bytes'] and sha(raw) == row.get('sha256')


def binding(path):
    raw = read(path)
    return dict(path=str(path.relative_to(ROOT)), bytes=len(raw), sha256=sha(raw))


def state(root):
    return dict(head=git(root, 'rev-parse', 'HEAD').decode().strip(),
                index_sha256=sha(git(root, 'ls-files', '--stage', '-z')),
                refs_sha256=sha(git(root, 'for-each-ref', '--format=%(refname) %(objectname)')))


def tree(root, revision, prefix=None):
    result = {}
    args = ('ls-tree', '-r', '-z', revision) + (('--', prefix) if prefix else ())
    for row in git(root, *args).split(b'\0'):
        if row:
            metadata, name = row.split(b'\t', 1)
            mode, _kind, oid = metadata.split()
            need(name not in result, 'duplicate Git tree path')
            result[name.decode()] = (mode.decode(), oid.decode())
    return result


def index(root):
    result = {}
    for row in git(root, 'ls-files', '--stage', '-z').split(b'\0'):
        if row:
            metadata, name = row.split(b'\t', 1)
            mode, oid, stage = metadata.decode().split()
            need(stage == '0' and name.decode() not in result, 'unmerged or duplicate index path')
            result[name.decode()] = (mode, oid)
    return result


def workflow_blocks(raw):
    lines, result, position, name = raw.decode().splitlines(), [], 0, None
    while position < len(lines):
        line = lines[position]
        if line.startswith('      - name: '):
            name = line.removeprefix('      - name: ')
        match = re.fullmatch(r'        run: (.+)', line)
        if match:
            if match[1] == '|':
                body = []
                position += 1
                while position < len(lines) and (not lines[position] or lines[position].startswith('          ')):
                    body.append(lines[position][10:] if lines[position] else '')
                    position += 1
                script, form = '\n'.join(body).rstrip() + '\n', 'indented_block'
            else:
                need(not match[1].startswith(('|', '>')), 'unsupported workflow scalar')
                script, form = match[1] + '\n', 'single_command'
                position += 1
            result.append(dict(name=name, form=form, script=script, script_sha256=sha(script.encode())))
            continue
        need(not line.lstrip().startswith('run:'), 'unsupported workflow run indentation')
        position += 1
    need([row['name'] for row in result] == ['Supervisor primary-doc vocabulary',
         'Maintained-surface relative links', 'Packaging version pin alignment', 'Closeout navigation markers']
         and [row['form'] for row in result] == ['single_command', 'single_command', 'indented_block', 'indented_block'],
         'four reviewed workflow blocks differ')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--child-revision', required=True)
    parser.add_argument('--parent-base', default=INITIAL_PARENT_BASE)
    args = parser.parse_args()
    publication, parent_base = args.child_revision, args.parent_base
    need(re.fullmatch(r'[0-9a-f]{40}', publication)
         and re.fullmatch(r'[0-9a-f]{40}', parent_base), 'independent immutable child/parent SHA required')
    need(not CHECKS.exists() and not MANIFEST.exists(), 'refusing to overwrite parent evidence')
    roots = (ROOT, CHILD, DATASETS, KIT)
    before = {str(root): state(root) for root in roots}
    need(before[str(ROOT)]['head'] == parent_base and before[str(CHILD)]['head'] == publication
         and before[str(DATASETS)]['head'] == DS and before[str(KIT)]['head'] == KIT_REVISION,
         'fixed publication or execution HEAD differs')
    need(all(not git(root, 'status', '--porcelain') for root in roots[1:]), 'dirty execution checkout')
    git(ROOT, 'merge-base', '--is-ancestor', INITIAL_PARENT_BASE, parent_base)
    git(CHILD, 'merge-base', '--is-ancestor', CHILD_BASE, publication)
    remote = git(CHILD, 'ls-remote', 'origin', 'refs/heads/main').decode().split()
    need(len(remote) == 2 and remote[1] == 'refs/heads/main'
         and re.fullmatch(r'[0-9a-f]{40}', remote[0]), 'unambiguous published child main required')
    git(CHILD, 'merge-base', '--is-ancestor', publication, remote[0])
    base_tree, staged = tree(ROOT, parent_base), index(ROOT)
    pins = {'external/ipfs_accelerate': publication, 'external/ipfs_datasets': DS,
            'external/ipfs_kit': KIT_REVISION}
    old_mode, old_child = base_tree['external/ipfs_accelerate']
    need(old_mode == '160000' and re.fullmatch(r'[0-9a-f]{40}', old_child), 'incoming accelerator pin differs')
    git(CHILD, 'merge-base', '--is-ancestor', old_child, publication)
    need(all(base_tree[name] == ('160000', revision) for name, revision in pins.items()
             if name != 'external/ipfs_accelerate')
         and all(staged[name] == ('160000', revision) for name, revision in pins.items()),
         'parent dependency pins differ')
    need(all(staged.get(name) == row for name, row in base_tree.items()
             if name != 'external/ipfs_accelerate'), 'parent base tree object or mode changed')
    phase_name, note_name = str(PHASE.relative_to(ROOT)), str(NOTE.relative_to(ROOT))
    def own(name):
        return name == note_name or name.startswith(phase_name + '/')
    need(note_name not in base_tree and not any(name.startswith(phase_name + '/') for name in base_tree),
         'parent publication scope already exists')
    need(all(own(name) for name in set(staged) - set(base_tree)), 'foreign staged addition')
    for row in git(ROOT, 'status', '--porcelain=v1', '-z', '--untracked-files=all').split(b'\0'):
        if row:
            name = row[3:].decode()
            need(row[:2] not in {b'R ', b' R', b'C ', b' C'}
                 and (own(name) or name == 'external/ipfs_accelerate'), 'foreign parent dirty path')
    note_raw = read(NOTE)
    need(all(line.rstrip() == line for line in note_raw.decode().splitlines()), 'parent note trailing whitespace')
    child_tree = tree(CHILD, publication)
    child_manifest_raw = git(CHILD, 'show', publication + ':' + CHILD_PHASE + 'manifest.json')
    manifest = load(child_manifest_raw)
    selected, selected_docs = manifest['selected_qualification'], manifest['selected_documentation']
    need(re.fullmatch(r'qualification-[0-9]{2,3}', selected)
         and re.fullmatch(r'documentation-checks(?:-[0-9]{2})?\.json', selected_docs)
         and manifest['accelerator_base'] == manifest['preserved_evidence_revision'] == CHILD_BASE
         and manifest['manifest_self_excluded'] is True
         and (manifest['selected_tests'], manifest['new_cases'], manifest['suites'], manifest['source_bindings'])
             == (166, 22, 8, 273), 'selected child manifest identity or counts differ')
    files = manifest['files']
    need(type(files) is list and files and len({row['path'] for row in files}) == len(files)
         and CHILD_PHASE + 'manifest.json' not in {row['path'] for row in files}, 'manifest file population differs')
    for row in files:
        name = path_name(row['path'])
        raw = git(CHILD, 'show', publication + ':' + name)
        need(matches(raw, row) and raw == read(CHILD / name), 'child manifest object or current bytes differ')
    phase_files = {name for name in child_tree if name.startswith(CHILD_PHASE)} - {CHILD_PHASE + 'manifest.json'}
    need(phase_files == {row['path'] for row in files if row['path'].startswith(CHILD_PHASE)},
         'child phase manifest omits or invents an artifact')
    prior = tree(CHILD, CHILD_BASE, 'docs/agent_supervisor/evidence/')
    need(prior and all(child_tree.get(name) == row for name, row in prior.items()), 'historical evidence changed')
    for name in ('reversible_source_view.py', 'source_view_edits.py'):
        path = 'ipfs_accelerate_py/agent_supervisor/runtime/' + name
        need(child_tree[path] == tree(CHILD, CHILD_BASE)[path], 'original codec/edit mapper changed')
    targets = load(git(CHILD, 'show', publication + ':' + CHILD_PHASE + 'targets.json'), list)
    need(len(targets) == len(set(targets)) == 8
         and all(type(name) is str and name.endswith('.py') and '::' not in name for name in targets),
         'eight complete suite targets required')
    q_path = CHILD_PHASE + selected + '/commands.json'
    q_raw = git(CHILD, 'show', publication + ':' + q_path)
    q = load(q_raw)
    execution_head = q['accelerator_execution_head']
    need(type(execution_head) is str and re.fullmatch(r'[0-9a-f]{40}', execution_head),
         'independently captured immutable execution HEAD required')
    git(CHILD, 'merge-base', '--is-ancestor', CHILD_BASE, execution_head)
    git(CHILD, 'merge-base', '--is-ancestor', execution_head, publication)
    passing = []
    for name in child_tree:
        match = re.fullmatch(re.escape(CHILD_PHASE) + r'(qualification-[0-9]{2,3})/commands\.json', name)
        if match:
            candidate = load(git(CHILD, 'show', publication + ':' + name))
            if candidate['status'] == 'pass' and candidate['targets'] == targets:
                passing.append(match[1])
    need(passing and selected == max(passing, key=lambda value: int(value.split('-')[1])),
         'selected qualification is not latest passing full roster')
    need(q['status'] == 'pass' and q['pytest_exit_code'] == 0 and q['targets'] == targets
         and q['accelerator_base'] == CHILD_BASE
         and q['datasets_execution_revision'] == DS and q['kit_execution_revision'] == KIT_REVISION
         and q['before'] == q['after'] and q['source_before_after_equal'] is True
         and q['fixed_heads_and_indexes_unchanged'] is True
         and q['pytest_invocations'] == 1 and q['separate_collection'] is False and q['baseline_control'] is False,
         'selected qualification identity or execution guards differ')
    rows = q['before']
    inventory = load(git(CHILD, 'show', publication + ':' + CHILD_PHASE + 'source-inventory.json'), list)
    need(len(rows) == 273 and len({(row['repository'], row['path']) for row in rows}) == 273
         and collections.Counter(row['repository'] for row in rows) == {'accelerator': 222, 'datasets_execution_checkout': 51}
         and len(inventory) == 273 and len({(row['repository'], row['path']) for row in inventory}) == 273
         and {(row['repository'], row['path']) for row in rows}
             == {(row['repository'], row['path']) for row in inventory}, 'source binding roster differs')
    for row in rows:
        root, revision = (CHILD, publication) if row['repository'] == 'accelerator' else (DATASETS, DS)
        raw = git(root, 'show', revision + ':' + path_name(row['path']))
        need(row['source_checkout'] == str(root) and matches(raw, row) and raw == read(root / row['path']),
             'qualified source Git/current bytes differ')
    q_before, q_after = q['git_state_before'], q['git_state_after']
    expected_heads = {str(CHILD): execution_head, str(DATASETS): DS, str(KIT): KIT_REVISION}
    need(set(q_before) == set(q_after) == set(expected_heads), 'execution Git guard population differs')
    ref_changes = []
    for name, revision in expected_heads.items():
        first, last = q_before[name], q_after[name]
        need(set(first) == set(last) == {'head', 'index_sha256', 'refs_sha256'}
             and first['head'] == last['head'] == revision
             and first['index_sha256'] == last['index_sha256'], 'qualification HEAD/index guard changed')
        if first['refs_sha256'] != last['refs_sha256']:
            ref_changes.append(dict(path=name, before=first['refs_sha256'], after=last['refs_sha256'], actor_attributed=False))
    need(q['observed_shared_ref_changes'] == ref_changes, 'shared-ref observations differ')
    raw_tests = {name: git(CHILD, 'show', publication + ':' + CHILD_PHASE + selected + '/' + name)
                 for name in ('junit.xml', 'tests.stdout.log', 'tests.stderr.log')}
    need(all(matches(raw, q[name]) for name, raw in raw_tests.items()), 'raw qualification artifact differs')
    xml = ET.fromstring(raw_tests['junit.xml'])
    cases = [(item.get('classname'), item.get('name')) for item in xml.iter('testcase')]
    outcome = dict(tests=len(cases), failures=sum(1 for _ in xml.iter('failure')),
                   errors=sum(1 for _ in xml.iter('error')), skipped=sum(1 for _ in xml.iter('skipped')))
    suites = dict(collections.Counter(suite for suite, _ in cases))
    counts = re.findall(r'^(?:collecting \.\.\. )?collected ([0-9]+) items?\s*$',
                        raw_tests['tests.stdout.log'].decode('utf-8', 'replace'), re.M)
    need(outcome == q['junit'] == dict(tests=166, failures=0, errors=0, skipped=0)
         and len(cases) == len(set(cases)) == q['distinct_junit_cases'] == q['collected_tests'] == 166
         and counts == ['166'] and suites.get(NEW_SUITE) == 22 and q['suites'] == suites
         and set(suites) == {name[:-3].replace('/', '.') for name in targets}, 'raw test counts or suite coverage differ')
    snapshots = q['frozen_changed_source_snapshots']
    expected_snapshots = {'ipfs_accelerate_py/agent_supervisor/runtime/source_lookup_worker_broker.py',
                          'test/api/test_native_source_worker_delivery.py', CHILD_PHASE + 'qualification_runner.py'}
    need(type(snapshots) is list and len(snapshots) == 3
         and {row['path'] for row in snapshots} == expected_snapshots, 'tested changed-source snapshot roster differs')
    for row in snapshots:
        current = git(CHILD, 'show', publication + ':' + path_name(row['path']))
        snapshot = git(CHILD, 'show', publication + ':' + path_name(row['snapshot']))
        need(matches(current, row) and current == snapshot, 'tested source snapshot differs from publication')
    need(all(q[name] == 0 for name in ('provider_calls', 'model_calls', 'training_steps', 'solver_calls', 'target_program_executions'))
         and all(q[name] is False for name in ('docker_run', 'worker_uid_qualified', 'production_coding_child_adoption',
             'universal_cas_callback_safety', 'proof_authority', 'execution_authority', 'completion_authority',
             'runtime_databases_published', 'previous_counts_added', 'total_session_token_savings_established'))
         and q['authored_listener_and_deployment_metadata_seams'] is True and q['actual_inert_child_probes'] is True
         and q['official_task_result'] is None, 'qualification scope/authority flags differ')
    docs_raw = git(CHILD, 'show', publication + ':' + CHILD_PHASE + selected_docs)
    docs = load(docs_raw)
    guard = docs['before']
    need(docs['schema'] == 'source-worker-delivery-documentation@1' and docs['status'] == 'pass' and guard == docs['after']
         and guard['qualification_path'] == CHILD_PHASE + selected and guard['qualification_sha256'] == sha(q_raw)
         and guard['qualification_binding']['path'] == q_path and matches(q_raw, guard['qualification_binding'])
         and guard['source_bindings'] == rows and guard['source_binding_scope'] == q['source_binding_scope']
         and (guard['selected_tests'], guard['suites'], guard['new_cases']) == (166, 8, 22),
         'documentation guard does not bind selected qualification')
    workflow = git(CHILD, 'show', publication + ':.github/workflows/documentation-gates.yml')
    need(docs['workflow_sha256'] == WORKFLOW_SHA
         and sha(workflow) == WORKFLOW_SHA
         and docs['exact_workflow_run_blocks'] == workflow_blocks(workflow)
         and len(docs['exact_workflow_run_blocks']) == len(docs['steps']) == 4
         and all(step['exit_code'] == 0 for step in docs['steps']), 'four passing reviewed workflow blocks required')
    for block, step in zip(docs['exact_workflow_run_blocks'], docs['steps']):
        need(step['name'] == block['name'] and step['script_sha256'] == block['script_sha256']
             and sha(block['script'].encode()) == block['script_sha256']
             and step['argv'] == ['bash', '--noprofile', '--norc', '-euo', 'pipefail', '-c', block['script']],
             'documentation workflow execution block differs')
    for key in ('documents', 'documentation_inputs', 'read_guards', 'current_evidence'):
        inputs = guard[key]
        need(type(inputs) is list and inputs and len({row['path'] for row in inputs}) == len(inputs),
             'documentation input inventory differs')
        for row in inputs:
            need(matches(git(CHILD, 'show', publication + ':' + path_name(row['path'])), row),
                 'documentation read guard object changed')
    need(matches(git(CHILD, 'show', publication + ':' + path_name(docs['log_binding']['path'])), docs['log_binding']),
         'documentation log differs')
    parent_inputs = [NOTE, *sorted(path for path in PHASE.rglob('*') if path.is_file())]
    need(Path(__file__).resolve() in parent_inputs, 'parent checker is outside owned inputs')
    guards = [binding(path) for path in parent_inputs]
    ci_binding = None
    ci_path = PHASE / 'child-ci-observation.json'
    if ci_path.exists():
        ci = load(read(ci_path))
        need(ci['schema'] == 'source-worker-delivery-exact-hosted-ci@1'
             and ci['head_sha'] == ci['run']['head_sha'] == publication
             and type(ci['run_id']) is int and ci['run_id'] > 0
             and ci['run_id'] == ci['run']['id'],
             'optional raw CI observation names another child or run')
        ci_binding = binding(ci_path)
    for name in set(staged) - set(base_tree):
        need(git(ROOT, 'show', ':' + name) == read(ROOT / name), 'staged owned file differs from current bytes')
    checker_path = CHILD / LINK_CHECKER
    need(sha(read(checker_path)) == LINK_SHA, 'pinned local documentation utility changed')
    spec = importlib.util.spec_from_file_location('source_delivery_parent_links', checker_path)
    checker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checker)
    checker.ROOT = ROOT
    # Exclusive empty files support the note's future local links. The output
    # contains a pass only after all closing Git and read guards succeed.
    with CHECKS.open('x') as check_handle, MANIFEST.open('x') as manifest_handle:
        need(not checker.check_file(NOTE, check_anchors=True), 'parent note relative links/anchors failed')
        after = {str(root): state(root) for root in roots}
        need(before == after and guards == [binding(path) for path in parent_inputs]
             and sha(read(checker_path)) == LINK_SHA, 'publication Git or read guards changed')
        need(all(not git(root, 'status', '--porcelain') for root in roots[1:]), 'execution checkout became dirty')
        result = dict(schema='source-worker-delivery-parent-publication@1', status='pass',
            checked_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), parent_base=parent_base,
            initial_parent_research_base=INITIAL_PARENT_BASE, initial_parent_base_preserved_as_ancestor=True,
            incoming_parent_accelerator_pin=old_child, accelerator_execution_head=execution_head,
            accelerator_publication=publication, observed_child_origin_main=remote[0], preserved_parent_gitlinks=pins,
            all_prior_parent_index_objects_preserved_except_accelerator=True,
            selected_qualification=selected, qualification_sha256=sha(q_raw), selected_documentation=selected_docs,
            documentation_sha256=sha(docs_raw), retained_tests=166, retained_new_cases=22, retained_suites=8,
            retained_source_bindings=273, datasets_execution_revision=DS, kit_execution_revision=KIT_REVISION,
            prior_child_evidence_objects_preserved=len(prior), historical_codec_and_edit_mapper_unchanged=True,
            child_manifest=dict(path=CHILD_PHASE + 'manifest.json', bytes=len(child_manifest_raw), sha256=sha(child_manifest_raw)),
            qualification_shared_ref_changes=ref_changes, shared_ref_actor_attributed=False,
            four_local_documentation_blocks_passed=True, documentation_link_counts={
                key: docs.get(key) for key in ('manual_links', 'relative_links', 'anchors')},
            parent_inputs=guards, git_state_before=before, git_state_after=after,
            authored_listener_and_deployment_metadata_seams=True, actual_inert_child_probes=True,
            worker_uid_qualified=False, production_coding_child_adoption=False, universal_cas_callback_safety=False,
            complete_import_closure_attested=False, tests_or_workflow_rerun=False, hosted_ci_qualified_here=False,
            optional_raw_child_ci_binding=ci_binding,
            additional_provider_model_training_solver_docker_calls=0, proof_authority=False,
            execution_authority=False, completion_authority=False, total_session_token_savings_established=False,
            git_refs_and_index_mutated=False, original_qualification_counts_added=False, output_self_excluded=True)
        json.dump(result, check_handle, sort_keys=True, indent=2)
        check_handle.write('\n')
        check_handle.flush()
        seal = dict(schema='source-worker-delivery-parent-manifest@1', parent_base=parent_base,
                    initial_parent_research_base=INITIAL_PARENT_BASE,
                    accelerator_publication=publication, files=[*guards, binding(CHECKS)],
                    preserved_parent_gitlinks={name: revision for name, revision in pins.items()
                                              if name != 'external/ipfs_accelerate'},
                    manifest_self_excluded=True, child_manifest=result['child_manifest'])
        json.dump(seal, manifest_handle, sort_keys=True, indent=2)
        manifest_handle.write('\n')
    print(json.dumps(dict(status='pass', tests=166, new_cases=22, suites=8, bindings=273,
                         child_revision=publication)))


if __name__ == '__main__':
    main()
