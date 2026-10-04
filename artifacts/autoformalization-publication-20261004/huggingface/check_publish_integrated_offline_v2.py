"""Exercise committed-source and remote-baseline guards with a disposable repo."""

import hashlib
import importlib.util
import json
import os
import subprocess
import tempfile
from pathlib import Path

WORK = Path(__file__).resolve().parent


def main():
    source = WORK / 'publish_integrated_v2.py'
    source_bytes = source.read_bytes()
    spec = importlib.util.spec_from_file_location('offline_publisher', source)
    subject = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(subject)
    checks = []
    with tempfile.TemporaryDirectory(prefix='autoformalization-publisher-offline-') as temporary:
        repo = Path(temporary) / 'repo'
        evidence = Path(temporary) / 'evidence'
        repo.mkdir()
        evidence.mkdir()

        def git(*args):
            # Only this disposable fixture suppresses hooks. The publisher preserves hooks.
            return subprocess.run(['git', '-c', 'core.hooksPath=/dev/null', '-C', str(repo), *args],
                                  capture_output=True, check=True, timeout=30).stdout.decode().strip()

        git('init', '-q', '-b', 'fixture-integration')
        git('config', 'user.name', 'Engineering fixture')
        git('config', 'user.email', 'fixture@invalid')
        git('remote', 'add', 'origin', 'https://github.com/endomorphosis/example-fixture.git')
        (repo / 'source.py').write_bytes(b'value = 1\n')
        (repo / 'source.py').chmod(0o755)
        (repo / 'link.py').symlink_to('source.py')
        (repo / 'unchanged.py').write_text('unchanged_canonical = True\n')
        (repo / '.gitmodules').write_text('[submodule "child"]\n\tpath = external/child\n\turl = ../child.git\n')
        git('add', '.')
        git('commit', '-q', '-m', 'Offline source verification fixture')
        tip = git('rev-parse', 'HEAD')
        selected = [
            {'path': 'source.py', 'state': 'present', 'mode': '100755',
             'sha256': hashlib.sha256(b'value = 1\n').hexdigest(), 'bytes': 10},
            {'path': 'link.py', 'state': 'present', 'mode': '120000',
             'sha256': hashlib.sha256(b'source.py').hexdigest(), 'bytes': 9},
            {'path': 'deleted.py', 'state': 'deleted'},
        ]
        plan = {'canonical_repository': str(repo), 'fresh_worktree': str(repo),
                'normalized_origin': 'github.com/endomorphosis/example-fixture',
                'integration_branch': 'fixture-integration', 'origin_main_sha256_or_git_oid': tip,
                'heads': [{'oid': tip, 'kind': 'canonical_current_source'}],
                'authoritative_source': {'snapshot_commit': tip, 'selected_files': selected}}
        prepared = {'schema': 'worktree-main-integration-prepublication/v1',
                    'eligible_for_root_prepublication_review': True, 'python_syntax_errors': [],
                    'origin_push_executed': False, 'canonical_repository': str(repo),
                    'fresh_worktree': str(repo), 'normalized_origin': plan['normalized_origin'],
                    'integrated_tip': tip, 'baseline_origin_main': tip, 'selected_head_count': 1}
        operations = subject.GitOperations(evidence)
        try:
            actual_repo, origin, current, baseline, tree = subject.check_prepared(operations, plan, prepared)
            assert actual_repo == repo and current == baseline == tip
            assert len(subject.check_source_pins(operations, repo, tree, plan)) == 3
            checks.append('committed_source_bytes_executable_symlink_modes_and_deleted_path')
            assert subject.committed_submodule_origins(operations, repo, tip, origin) == {
                'external/child': 'github.com/endomorphosis/child'}
            checks.append('relative_submodule_origin_from_committed_blob')
            for field, replacement in [('mode', '100644'), ('sha256', 'a' * 64)]:
                previous = selected[0][field]
                selected[0][field] = replacement
                try:
                    subject.check_source_pins(operations, repo, tree, plan)
                except ValueError:
                    checks.append(f'wrong_committed_source_{field}_rejected')
                else:
                    raise AssertionError('source substitution accepted')
                selected[0][field] = previous
            assert subject.check_remote_baseline(plan, tip, {'refs/heads/main': tip}) == tip
            assert subject.check_remote_baseline({**plan, 'baseline_remote_ref': 'origin/master'}, tip,
                                                 {'refs/heads/master': tip}) is None
            checks.append('exact_main_and_absent_main_with_exact_master_baselines')
            for remote in ({'refs/heads/main': 'a' * 40}, {'refs/heads/master': 'a' * 40}, {}):
                try:
                    subject.check_remote_baseline(plan, tip, remote)
                except ValueError:
                    pass
                else:
                    raise AssertionError('remote baseline transplant accepted')
            checks.append('advanced_or_missing_remote_baseline_rejected')
            canonical_rows = []
            for name, entry in sorted(tree.items()):
                data = subprocess.run(['git', '-C', str(repo), 'cat-file', 'blob', entry['oid']],
                                      capture_output=True, check=True, timeout=30).stdout
                canonical_rows.append({'state': 'present', 'path': name, 'mode': entry['mode'],
                                       'git_oid': entry['oid'], 'bytes': len(data),
                                       'sha256': hashlib.sha256(data).hexdigest()})

            def full_binding(filename, manifest):
                target = evidence / filename
                data = subject.raw(manifest) + b'\n'
                target.write_bytes(data)
                return {'path': str(target), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}

            blob_manifest = {
                'schema': 'complete-canonical-snapshot-blob-pins/v1', 'name': 'fixture', 'repository': str(repo),
                'snapshot_commit': tip, 'snapshot_ref': 'refs/heads/fixture-integration',
                'snapshot_report_binding': {'path': '/fixture/declared-only', 'sha256': 'a' * 64, 'bytes': 1},
                'authoritative_source': {'snapshot_commit': tip, 'selected_files': [*canonical_rows, {'state': 'deleted', 'path': 'deleted.py'}]},
                'canonical_blob_path_count': len(canonical_rows), 'unique_blob_count': len({r['git_oid'] for r in canonical_rows}),
                'intentional_deleted_path_count': 1, 'canonical_gitlinks_deferred': [],
                'unique_branch_only_additions_remain_allowed': True, 'scope': 'engineering_fixture_only',
                'origin_push_executed': False, 'training_executed': False,
            }
            blob_manifest['content_sha256'] = hashlib.sha256(subject.raw(blob_manifest)).hexdigest()
            selected_full = {'snapshot_commit': tip, 'manifest_binding': full_binding('canonical-blobs.json', blob_manifest)}
            full_plan = {**plan, 'authoritative_full_tree_snapshot': selected_full}
            receipt = subject.check_full_canonical_tree(operations, repo, tree, full_plan, tip)
            assert receipt['canonical_blob_paths_verified'] == len(canonical_rows)
            assert receipt['intentional_deleted_paths_verified'] == 1
            checks.append('sealed_complete_canonical_blob_profile_verified')
            current_manifest = {
                'schema': 'full-current-git-tree-qualification/v1', 'canonical_repository': str(repo),
                'canonical_snapshot_commit': tip, 'integrated_tip': tip,
                'source_bindings': [{'path': name, 'mode': row['mode'], 'kind': row['kind'], 'source_git_oid': row['oid']}
                                    for name, row in sorted(tree.items())],
                'source_binding_count': len(tree), 'canonical_entries_missing_or_changed': [],
                'full_current_tree_exactly_preserved': True, 'metadata_only_no_source_credentials_or_model_bytes_read': True,
                'normalized_origin': origin, 'origin_push_performed': False,
                'qualification_binding': {'path': '/fixture/declared-only', 'sha256': 'a' * 64, 'bytes': 1},
                'source_git_oid_recipe': 'fixture_committed_ls_tree',
            }
            current_plan = {**plan, 'authoritative_full_tree_snapshot': {
                'snapshot_commit': tip, 'manifest_binding': full_binding('current-tree.json', current_manifest)}}
            subject.check_full_canonical_tree(operations, repo, tree, current_plan, tip)
            checks.append('externally_pinned_complete_current_tree_profile_verified')
            trimmed = dict(current_manifest)
            trimmed['source_bindings'] = current_manifest['source_bindings'][1:]
            trimmed['source_binding_count'] -= 1
            try:
                subject.check_full_canonical_tree(operations, repo, tree, {**plan, 'authoritative_full_tree_snapshot': {
                    'snapshot_commit': tip, 'manifest_binding': full_binding('trimmed-tree.json', trimmed)}}, tip)
            except ValueError:
                checks.append('externally_resealed_incomplete_canonical_tree_rejected')
            else:
                raise AssertionError('trimmed source scope accepted')
            try:
                subject.check_full_canonical_tree(operations, repo, tree, plan, tip)
            except ValueError:
                checks.append('missing_mandatory_external_fulltree_selection_rejected')
            else:
                raise AssertionError('dirty-only qualification accepted')
            git('rm', '-q', 'unchanged.py')
            git('commit', '-q', '-m', 'Engineering reproduction of archival canonical deletion')
            missing_tip = git('rev-parse', 'HEAD')
            missing_tree = subject.committed_tree(operations, repo, missing_tip)
            subject.check_source_pins(operations, repo, missing_tree, plan)
            try:
                subject.check_full_canonical_tree(operations, repo, missing_tree, full_plan, missing_tip)
            except ValueError:
                checks.append('unchanged_canonical_deletion_missed_by_dirty_pins_rejected_by_fulltree')
            else:
                raise AssertionError('archival deletion escaped fulltree check')
            assert not operations.push_attempted
            assert not any('fetch' in json.loads(line)['command'] or 'ls-remote' in json.loads(line)['command']
                           for line in operations.path.read_text().splitlines())
        finally:
            operations.close()
    assert source.read_bytes() == source_bytes
    script = Path(__file__).resolve()
    receipt = {
        'schema': 'git-publisher-offline-fixture/v1', 'status': 'passed', 'checks': checks,
        'publisher_source': {'path': str(source), 'bytes': len(source_bytes),
                             'sha256': hashlib.sha256(source_bytes).hexdigest()},
        'fixture_source': {'path': str(script), 'bytes': script.stat().st_size,
                           'sha256': hashlib.sha256(script.read_bytes()).hexdigest()},
        'network_calls': 0, 'pushes': 0, 'model_calls': 0, 'training_executed': False,
        'existing_repository_mutations': 0, 'temporary_fixture_deleted': True,
        'coverage_scope': 'offline_source_and_baseline_guards_not_real_push_or_network_failure_paths',
    }
    target = WORK / 'publish_integrated_offline_fixture_v2.json'
    require_absent = not target.exists()
    if not require_absent:
        raise ValueError('fresh fixture evidence file required')
    result = subject.sealed_save(target, receipt)
    os.chmod(target, 0o600)
    print(json.dumps({'fixture': result, 'checks': len(checks)}, sort_keys=True))


if __name__ == '__main__':
    main()
