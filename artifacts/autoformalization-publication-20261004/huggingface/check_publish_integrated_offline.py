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
    source = WORK / 'publish_integrated.py'
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
    target = WORK / 'publish_integrated_offline_fixture.json'
    require_absent = not target.exists()
    if not require_absent:
        raise ValueError('fresh fixture evidence file required')
    result = subject.sealed_save(target, receipt)
    os.chmod(target, 0o600)
    print(json.dumps({'fixture': result, 'checks': len(checks)}, sort_keys=True))


if __name__ == '__main__':
    main()
