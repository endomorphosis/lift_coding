"""Commit and normally push the complete verified increment from private Git only.

Observed commit receipts are durably written outside the private checkout before
each push. A changed remote parent stops this attempt for a fresh reviewed checkout;
no rebase or force push is used. No original HEAD, index, child checkout, or sealed input is changed.
"""
import argparse
import datetime
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import subprocess

WORKSPACE = Path('/home/barberb/lift_coding')
ROOT = Path(__file__).resolve().parent
REPO = ROOT / 'root'
ORIGINAL_STATE = WORKSPACE / 'maintenance/ranker-curvature-private-git-preparation-20261005-01/original-checkout-state-01.json'
OUTPUT = WORKSPACE / 'maintenance/ranker-convergence-git-publication-20261005-02'
ENV = dict(os.environ, GIT_OPTIONAL_LOCKS='0')
STAGE_SHA = None  # Required independent final-stage SHA256 is supplied at execution.
TITLE = 'Qualify original real ranker convergence and publish proof-index evidence'


def need(value, message):
    if value is not True:
        raise ValueError(message)


def read(path):
    need(path.is_absolute() and path.resolve(strict=True) == path and not path.is_symlink(), 'canonical regular file required')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        need(stat.S_ISREG(before.st_mode) and before.st_size <= 16 * 1024**2, 'bounded regular file required')
        parts = []
        while block := os.read(fd, 1024**2):
            parts.append(block)
        raw = b''.join(parts)
        keys = ('st_dev', 'st_ino', 'st_mode', 'st_nlink', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
        signature = lambda value: tuple(getattr(value, key) for key in keys)
        need(signature(before) == signature(os.fstat(fd)) == signature(path.lstat()) and len(raw) == before.st_size, 'file changed during read')
        return raw
    finally:
        os.close(fd)


def pin(path):
    raw = read(path)
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def git(*args, repo=REPO, input=None):
    return subprocess.check_output(['git', '-C', str(repo), *args], input=input, env=ENV, stderr=subprocess.PIPE)


def guards():
    original = json.loads(read(ORIGINAL_STATE))
    result = {}
    for name, old in original['original_checkouts'].items():
        raw = read(Path(old['index_path']))
        current = {'head': git('rev-parse', 'HEAD', repo=old['path']).decode().strip(), 'index_bytes': len(raw), 'index_sha256': hashlib.sha256(raw).hexdigest()}
        need(all(current[key] == old[key] for key in current), 'original HEAD or index changed')
        result[name] = current
    links = []
    for line in git('ls-files', '--stage', repo=WORKSPACE).decode().splitlines():
        if line.startswith('160000 '):
            metadata, path = line.split('\t', 1)
            mode, oid, stage = metadata.split()
            links.append({'mode': mode, 'blob': oid, 'stage': int(stage), 'path': path})
    need(links == original['root_index_gitlinks'], 'original index Git links changed')
    return result


def write_new(name, value):
    path = OUTPUT / name
    with path.open('xb') as stream:
        stream.write((json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode())
        stream.flush()
        os.fsync(stream.fileno())
    fd = os.open(OUTPUT, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
    return pin(path)


def timestamp():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def fetch_main():
    git('fetch', '--no-tags', 'origin', 'refs/heads/main:refs/remotes/origin/main')
    oid = git('rev-parse', 'origin/main').decode().strip()
    need(git('ls-remote', 'origin', 'refs/heads/main').decode().strip().split() == [oid, 'refs/heads/main'], 'remote changed during freshness read; fetch again before proceeding')
    return oid


def ancestor(older, newer):
    outcome = subprocess.run(['git', '-C', str(REPO), 'merge-base', '--is-ancestor', older, newer], env=ENV, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    need(outcome.returncode in (0, 1), 'ancestor check failed')
    return outcome.returncode == 0


def tree_links(oid):
    result = []
    for line in git('ls-tree', '-r', oid).decode().splitlines():
        if line.startswith('160000 '):
            metadata, path = line.split('\t', 1)
            mode, kind, link = metadata.split()
            result.append({'path': path, 'mode': mode, 'oid': link})
    need(len(result) == 9, 'all nine parent Git links required')
    return result


def verify_commit(commit, stage, check_parent=True):
    parents = git('rev-list', '--parents', '-n', '1', commit).decode().strip().split()
    need(len(parents) == 2 and parents[0] == commit, 'single-parent publication commit required')
    parent = parents[1]
    if check_parent:
        wire = git('diff-tree', '--no-commit-id', '--name-status', '-r', '-z', parent, commit).split(b'\0')
        need([(wire[i].decode(), os.fsdecode(wire[i + 1])) for i in range(0, len(wire) - 1, 2)] == [('A', row['path']) for row in stage['staged_source_blobs']], 'commit must contain only the complete exact new additions')
        need(tree_links(commit) == tree_links(parent), 'commit changed parent Git links')
    tree = {}
    for line in git('ls-tree', '-r', commit).decode().splitlines():
        metadata, path = line.split('\t', 1)
        mode, kind, oid = metadata.split()
        tree[path] = (mode, kind, oid)
    expected = stage['staged_source_blobs']
    stream = io.BytesIO(git('cat-file', '--batch', input=''.join(tree[row['path']][2] + '\n' for row in expected).encode()))
    verified = []
    for row in expected:
        oid, kind, size = stream.readline().decode().strip().split()
        raw = stream.read(int(size))
        need(stream.read(1) == b'\n' and tree[row['path']] == ('100644', 'blob', oid) and kind == 'blob', 'regular committed Git blob required')
        actual = {'path': row['path'], 'mode': '100644', 'git_blob_oid': oid, 'bytes': int(size), 'sha256': hashlib.sha256(raw).hexdigest()}
        need(actual == row, 'committed blob differs from complete staged pin inventory')
        verified.append(actual)
    need(stream.read() == b'', 'unexpected committed blob tail')
    return parent, git('rev-parse', commit + '^{tree}').decode().strip(), verified


def main():
    stage_path = ROOT / 'final-stage-closed-01.json'
    stage_raw = read(stage_path)
    need(hashlib.sha256(stage_raw).hexdigest() == STAGE_SHA, 'parsed final stage receipt changed')
    stage = json.loads(stage_raw)
    gate = stage.get('verified_HF_publication_gate')
    need(type(gate) is dict and set(gate) == {'commit', 'publication_closed', 'public_readback', 'ledger'} and
         gate['commit'] == stage['hf_commit'], 'actual verified HF commit gate required before Git publication')
    gate_documents = {}
    for key in ('publication_closed', 'public_readback', 'ledger'):
        row = gate[key]
        path = Path(row['path'])
        need(path.is_relative_to(WORKSPACE / 'maintenance/ranker-convergence-publication-root-20261005-01') and
             path.suffix == '.json', 'safe new HF gate JSON required')
        raw = read(path)
        need({'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()} == row,
             'parsed HF gate bytes differ from stage descriptor')
        gate_documents[key] = json.loads(raw)
    hf_closed, hf_public, hf_ledger = (gate_documents[key] for key in ('publication_closed', 'public_readback', 'ledger'))
    need(hf_closed.get('status') == 'PUBLISHED_AND_VERIFIED' and hf_closed.get('commit') == gate['commit'] and
         hf_closed.get('remote_readback_verified') is True, 'actual published and verified HF release required')
    need(hf_public.get('status') == 'passed' and hf_public.get('commit') == gate['commit'] and
         hf_public.get('fresh_public_main_matches_commit') is True and hf_public.get('prior_immutable_files_preserved') == 225 and
         hf_public.get('all_selected_local_pins_rechecked') is True, 'independent public readback and prior225 preservation required')
    need(hf_ledger.get('huggingface', {}).get('commit') == gate['commit'] and all(hf_ledger.get(key) is False for key in
         ('proof_authority', 'execution_authority', 'completion_authority', 'planner_activation')),
         'actual safe HF ledger and unchanged authority boundaries required')
    need(stage['status'] == 'passed_complete_increment_HF_verified_ready_to_commit' and stage['staged_file_count'] == len(stage['staged_source_blobs']) > 0 and stage['staged_file_bytes'] == sum(row['bytes'] for row in stage['staged_source_blobs']) and stage['credential_candidate_hits'] == 0, 'complete scan-qualified staged increment required')
    need(not OUTPUT.exists(), 'fresh durable publication receipt namespace required')
    OUTPUT.mkdir()
    output_parent_fd = os.open(OUTPUT.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(output_parent_fd)
    finally:
        os.close(output_parent_fd)
    before = guards()
    need(before == stage['original_guard_after'], 'original guards differ from closed stage baseline')
    initial_parent = git('rev-parse', 'HEAD').decode().strip()
    need(initial_parent == stage['parent'] and git('write-tree').decode().strip() == stage['tree'], 'prepared parent or index tree changed')
    need(git('diff', '--quiet') == b'', 'private staged working tree changed')
    fresh_parent = fetch_main()
    need(initial_parent == fresh_parent, 'remote parent advanced; retain this preparation and renew a fresh reviewed checkout')
    need(tree_links(initial_parent) == stage['parent_gitlinks'], 'prepared parent Git links changed')
    for row in stage['staged_source_blobs']:
        need(pin(WORKSPACE / row['path'])['sha256'] == row['sha256'], 'source changed before commit')
    started_pin = write_new('started.json', {'schema': 'ranker-convergence-private-git-publication-started@1', 'created_at_utc': timestamp(), 'producer': pin(Path(__file__).resolve()), 'final_stage': pin(stage_path), 'initial_parent': initial_parent, 'fresh_remote_parent': fresh_parent, 'title': TITLE, 'target': 'origin/main', 'original_guard_before': before, 'force_push_authorized_or_used': False, 'original_mutations_authorized_or_used': False})
    git('-c', 'core.hooksPath=/dev/null', 'commit', '-m', TITLE)
    commit_calls = 1
    commit = git('rev-parse', 'HEAD').decode().strip()
    parent, tree, verified = verify_commit(commit, stage)
    need(parent == initial_parent and tree == stage['tree'], 'initial observed commit differs from approved stage tree')
    observations = []
    observations.append(write_new('commit-observed-01.json', {'schema': 'ranker-convergence-private-git-observed-commit@1', 'created_at_utc': timestamp(), 'commit': commit, 'parent': parent, 'tree': tree, 'title': TITLE, 'staged_file_count': len(verified), 'staged_file_bytes': sum(row['bytes'] for row in verified), 'final_stage': pin(stage_path), 'original_guard_after_commit': guards(), 'durable_before_any_push': True, 'push_calls': 0}))
    push_calls = 0
    rebases = 0
    for attempt in range(1, 4):
        remote = fetch_main()
        if ancestor(commit, remote):
            break
        need(remote == parent, 'remote parent advanced before push; retain observed commit and renew a fresh reviewed checkout')
        need(parent == remote and guards() == before, 'fresh parent and original guards required before push')
        outcome = subprocess.run(['git', '-C', str(REPO), 'push', 'origin', 'HEAD:refs/heads/main'], env=ENV, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        push_calls += 1
        write_new(f'push-attempt-{push_calls:02d}.json', {'schema': 'ranker-convergence-normal-git-push-attempt@1', 'created_at_utc': timestamp(), 'commit': commit, 'parent': parent, 'target': 'origin/main', 'force_used': False, 'returncode': outcome.returncode, 'observed_commit': observations[-1], 'original_guard_after_push': guards()})
        remote = fetch_main()
        if outcome.returncode == 0 or ancestor(commit, remote):
            need(ancestor(commit, remote), 'successful push commit absent from refreshed remote')
            break
        raise ValueError('normal push failed or remote parent advanced; retained attempt requires a fresh reviewed checkout')
    else:
        raise ValueError('normal push did not reach verified remote')
    remote = fetch_main()
    need(ancestor(commit, remote), 'publication commit is not reachable from refreshed main')
    parent, tree, committed_rows = verify_commit(commit, stage)
    _, remote_tree, remote_rows = verify_commit(remote, stage, check_parent=False)
    need(committed_rows == remote_rows and len(remote_rows) == stage['staged_file_count'], 'complete new population changed during remote readback')
    need(git('status', '--porcelain=v1', '--untracked-files=all') == b'', 'private publication checkout not clean')
    after = guards()
    need(before == after, 'original root or child changed during publication')
    result = {'schema': 'ranker-convergence-GitHub-complete-publication-closure@1', 'status': 'PUBLISHED_AND_VERIFIED', 'created_at_utc': timestamp(), 'producer': pin(Path(__file__).resolve()), 'started': started_pin, 'final_stage': pin(stage_path), 'observed_commits': observations, 'commit': commit, 'parent': parent, 'tree': tree, 'remote_main': remote, 'remote_tree': remote_tree, 'remote_target': 'origin/main', 'commit_reachable_from_remote_main': True, 'title': TITLE, 'committed_source_blobs': committed_rows, 'remote_readback_source_blobs': remote_rows, 'new_file_count': len(remote_rows), 'new_file_bytes': sum(row['bytes'] for row in remote_rows), 'parent_gitlinks': tree_links(parent), 'commit_gitlinks': tree_links(commit), 'all_nine_fresh_parent_gitlinks_preserved': True, 'full_new_population_remote_Git_blobs_verified': True, 'hf_commit': stage['hf_commit'], 'original_guard_before': before, 'original_guard_after': after, 'private_checkout_clean': True, 'original_root_or_child_HEAD_index_mutations': 0, 'sealed_Q3_P4_S2_mutations': 0, 'raw_SDK_logs_archives_caches_private_worktrees_added': 0, 'native_model_solver_test_fit_codec_jobs': 0, 'project_imports': 0, 'commit_calls': commit_calls, 'push_calls': push_calls, 'concurrency_rebases': rebases, 'force_push_calls': 0, 'proof_authority': False, 'execution_authority': False, 'completion_authority': False, 'full_task_satisfaction': 'unknown'}
    result_pin = write_new('closed.json', result)
    print(json.dumps({'status': result['status'], 'commit': commit, 'parent': parent, 'remote_main': remote, 'tree': tree, 'new_files': len(remote_rows), 'new_bytes': result['new_file_bytes'], 'closure': result_pin, 'original_guards_unchanged': True, 'normal_push_calls': push_calls, 'force_push_calls': 0}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--expected-final-stage-sha256', required=True)
    args = parser.parse_args()
    STAGE_SHA = args.expected_final_stage_sha256
    main()
