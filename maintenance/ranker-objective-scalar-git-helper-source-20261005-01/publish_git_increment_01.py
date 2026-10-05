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
import re
import stat
import subprocess

WORKSPACE = Path('/home/barberb/lift_coding')
ROOT = None  # Explicit fresh preparation root is required at execution.
REPO = None
ORIGINAL_STATE = WORKSPACE / 'maintenance/ranker-curvature-private-git-preparation-20261005-01/original-checkout-state-01.json'
OUTPUT = None  # Explicit durable external output namespace is required.
ENV = dict(os.environ, GIT_OPTIONAL_LOCKS='0')
STAGE_SHA = None  # Required independent final-stage SHA256 is supplied at execution.
TITLE = 'Qualify exact-real objective scalar leaves and publish proof-index evidence'
STATE = {'commit_calls': 0, 'push_calls': 0, 'observed_commit': None}


def need(value, message):
    if value is not True:
        raise ValueError(message)


def read(path):
    need(path.is_absolute() and path.resolve(strict=True) == path and not path.is_symlink(), 'canonical regular file required')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        need(stat.S_ISREG(before.st_mode) and before.st_size <= 16 * 1024**2, 'bounded regular file required')
        parts, size = [], 0
        while block := os.read(fd, 1024**2):
            size += len(block)
            need(size <= 16 * 1024**2, 'source grew beyond read bound')
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


def git(*args, repo=None, input=None):
    return subprocess.check_output(['git', '-c', 'core.fsmonitor=false', '-c', 'core.hooksPath=/dev/null', '-C', str(REPO if repo is None else repo), *args], input=input, env=ENV, stderr=subprocess.PIPE)


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


def validate_HF_gate(read_file, gate):
    need(type(gate) is dict and set(gate) == {'commit', 'publication_closed', 'public_readback', 'ledger'} and
         type(gate['commit']) is str and re.fullmatch('[0-9a-f]{40}', gate['commit']) is not None,
         'actual complete verified HF gate required')
    gate_root = WORKSPACE / 'maintenance/ranker-objective-scalar-publication-root-20261005-01'
    expected_paths = {'publication_closed': gate_root / 'hf-publication-01/closed.json',
                      'public_readback': gate_root / 'hf-public-readback-01.json',
                      'ledger': gate_root / 'release-publication-ledger-01.json'}
    documents = {}
    for key, path in expected_paths.items():
        row = gate[key]
        need(type(row) is dict and set(row) == {'path', 'bytes', 'sha256'} and row['path'] == str(path) and
             type(row['bytes']) is int and 0 < row['bytes'] <= 16 * 1024**2 and
             type(row['sha256']) is str and re.fullmatch('[0-9a-f]{64}', row['sha256']) is not None,
             'exact safe HF gate descriptor required')
        raw = read_file(path)
        need({'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()} == row,
             'HF gate parsed bytes differ from exact descriptor')
        documents[key] = json.loads(raw)
    closed, public, ledger = [documents[key] for key in ('publication_closed', 'public_readback', 'ledger')]
    parent = 'fae2e38dc882929edb2bcd2226560f0da3dfcd9e'
    commit = gate['commit']
    files, total = closed.get('files'), closed.get('selected_bytes')
    need(type(files) is int and 0 < files <= 100 and type(total) is int and 0 < total <= 256 * 1024**2,
         'bounded exact actual HF upload population')
    need(closed.get('schema') == 'terminal-ir-HF-successor-publication@1' and closed.get('status') == 'PUBLISHED_AND_VERIFIED' and
         closed.get('commit') == commit and closed.get('parent') == parent and closed.get('remote_readback_verified') is True and
         type(closed.get('prior_immutable_remote_files_preserved')) is int and closed['prior_immutable_remote_files_preserved'] == 329,
         'actual successful HF publication and prior329 preservation required')
    need(public.get('schema') == 'ranker-objective-scalar-public-HF-readback-join@1' and public.get('status') == 'passed' and
         public.get('commit') == commit and public.get('parent') == parent and public.get('fresh_public_main_matches_commit') is True and
         public.get('fresh_public_main_after_tree_matches_commit') is True and public.get('all_selected_local_pins_rechecked') is True and
         type(public.get('prior_immutable_files_preserved')) is int and public['prior_immutable_files_preserved'] == 329 and
         type(public.get('selected_files')) is int and public['selected_files'] == files and
         type(public.get('selected_bytes')) is int and public['selected_bytes'] == total and
         type(public.get('committed_total_regular_files')) is int and public['committed_total_regular_files'] == 331 + files - 2,
         'independent public HF tree and exact population join required')
    hf = ledger.get('huggingface', {}); inputs = ledger.get('input_receipts', {})
    need(ledger.get('schema') == 'ranker-objective-scalar-release-publication-ledger@1' and
         ledger.get('status') == 'HF_PUBLISHED_AND_VERIFIED_GITHUB_PUBLICATION_PENDING' and
         hf.get('commit') == commit and hf.get('parent') == parent and hf.get('status') == 'PUBLISHED_AND_VERIFIED' and
         type(hf.get('selected_files')) is int and hf['selected_files'] == files and type(hf.get('selected_bytes')) is int and
         hf['selected_bytes'] == total and type(hf.get('prior_immutable_files_preserved')) is int and
         hf['prior_immutable_files_preserved'] == 329 and hf.get('committed_total_regular_files') == 331 + files - 2 and
         hf.get('public_readback') == gate['public_readback'] and inputs.get('hf_closed') == gate['publication_closed'] and
         inputs.get('public_readback') == gate['public_readback'] and inputs.get('hf_plan') == closed.get('plan') and
         all(ledger.get(key) is False for key in ('proof_authority', 'execution_authority', 'completion_authority', 'planner_activation')) and
         ledger.get('full_task_satisfaction') == 'unknown' and ledger.get('all32_governing_RPI_exits') == 'OPEN',
         'actual HF ledger exact joins and unchanged authority boundaries required')
    return documents


def main():
    need(__debug__, 'optimized Python refused')
    stage_path = ROOT / 'final-stage-closed-01.json'
    stage_raw = read(stage_path)
    need(hashlib.sha256(stage_raw).hexdigest() == STAGE_SHA, 'parsed final stage receipt changed')
    stage = json.loads(stage_raw)
    gate = stage.get('verified_HF_publication_gate')
    need(type(gate) is dict and gate.get('commit') == stage['hf_commit'], 'actual staged HF commit required')
    validate_HF_gate(read, gate)
    peer_raw = read(PEER_PATH)
    peer_pin = {'path': str(PEER_PATH), 'bytes': len(peer_raw), 'sha256': hashlib.sha256(peer_raw).hexdigest()}
    need(peer_pin['sha256'] == PEER_SHA, 'independent poststage peer changed')
    peer = json.loads(peer_raw)
    need(not PEER_PATH.is_relative_to(REPO) and
         str(PEER_PATH.relative_to(WORKSPACE)) not in {row['path'] for row in stage['staged_source_blobs']},
         'poststage peer must remain external to the staged increment to avoid a digest cycle')
    need(peer['schema'] == 'ranker-objective-scalar-independent-final-Git-input-review@1' and
         peer['status'] == 'passed_file_only_actual_HF_gate_and_exact_compact_selection' and peer['findings'] == [] and
         peer['actual_HF_commit'] == gate['commit'] and type(peer['combined_selected_files']) is int and
         peer['combined_selected_files'] == stage['staged_file_count'] and type(peer['combined_selected_bytes']) is int and
         peer['combined_selected_bytes'] == stage['staged_file_bytes'] and
         all(peer.get(key) is False for key in ('proof_authority', 'execution_authority', 'completion_authority', 'planner_activation')),
         'exact independent poststage peer and population required before commit')
    need(type(peer['reviewed_input_pins']) is list and
         all(row in peer['reviewed_input_pins'] for row in
             (pin(stage_path), gate['publication_closed'], gate['public_readback'], gate['ledger'])),
         'poststage peer must bind this exact final stage and all three actual HF gate receipts')
    need(0 < stage['staged_file_count'] <= 10000 and stage['staged_file_bytes'] <= 256 * 1024**2,
         'bounded complete compact Git population')
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
    started_pin = write_new('started.json', {'schema': 'ranker-objective-scalar-private-git-publication-started@1', 'created_at_utc': timestamp(), 'producer': pin(Path(__file__).resolve()), 'final_stage': pin(stage_path), 'independent_final_input_review': peer_pin, 'initial_parent': initial_parent, 'fresh_remote_parent': fresh_parent, 'title': TITLE, 'target': 'origin/main', 'original_guard_before': before, 'force_push_authorized_or_used': False, 'original_mutations_authorized_or_used': False})
    git('-c', 'core.hooksPath=/dev/null', 'commit', '-m', TITLE)
    commit_calls = 1
    STATE['commit_calls'] = 1
    commit = git('rev-parse', 'HEAD').decode().strip()
    STATE['observed_commit'] = commit
    parent, tree, verified = verify_commit(commit, stage)
    need(parent == initial_parent and tree == stage['tree'], 'initial observed commit differs from approved stage tree')
    observations = []
    observations.append(write_new('commit-observed-01.json', {'schema': 'ranker-objective-scalar-private-git-observed-commit@1', 'created_at_utc': timestamp(), 'commit': commit, 'parent': parent, 'tree': tree, 'title': TITLE, 'staged_file_count': len(verified), 'staged_file_bytes': sum(row['bytes'] for row in verified), 'final_stage': pin(stage_path), 'original_guard_after_commit': guards(), 'durable_before_any_push': True, 'push_calls': 0}))
    push_calls = 0
    rebases = 0
    remote = fetch_main()
    need(remote == parent, 'remote parent advanced before push; retain observed commit and renew a fresh reviewed checkout')
    need(guards() == before and pin(PEER_PATH) == peer_pin and pin(stage_path)['sha256'] == STAGE_SHA,
         'original guards, exact final stage and poststage peer required before push')
    validate_HF_gate(read, gate)
    outcome = subprocess.run(['git', '-c', 'core.fsmonitor=false', '-c', 'core.hooksPath=/dev/null',
                              '-C', str(REPO), 'push', 'origin', 'HEAD:refs/heads/main'],
                             env=ENV, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    push_calls = 1
    STATE['push_calls'] = 1
    write_new('push-attempt-01.json', {'schema': 'ranker-objective-scalar-normal-git-push-attempt@1',
        'created_at_utc': timestamp(), 'commit': commit, 'parent': parent, 'target': 'origin/main',
        'force_used': False, 'returncode': outcome.returncode, 'observed_commit': observations[-1],
        'original_guard_after_push': guards()})
    remote = fetch_main()
    need(ancestor(commit, remote), 'publication commit is not reachable from refreshed main')
    parent, tree, committed_rows = verify_commit(commit, stage)
    _, remote_tree, remote_rows = verify_commit(remote, stage, check_parent=False)
    need(committed_rows == remote_rows and len(remote_rows) == stage['staged_file_count'], 'complete new population changed during remote readback')
    need(git('status', '--porcelain=v1', '--untracked-files=all') == b'', 'private publication checkout not clean')
    validate_HF_gate(read, gate)
    need(pin(PEER_PATH) == peer_pin and pin(stage_path)['sha256'] == STAGE_SHA, 'final peer/stage changed during publication')
    after = guards()
    need(before == after, 'original root or child changed during publication')
    result = {'schema': 'ranker-objective-scalar-GitHub-complete-publication-closure@1', 'status': 'PUBLISHED_AND_VERIFIED', 'created_at_utc': timestamp(), 'producer': pin(Path(__file__).resolve()), 'started': started_pin, 'final_stage': pin(stage_path), 'independent_final_input_review': peer_pin, 'observed_commits': observations, 'commit': commit, 'parent': parent, 'tree': tree, 'remote_main': remote, 'remote_tree': remote_tree, 'remote_target': 'origin/main', 'commit_reachable_from_remote_main': True, 'title': TITLE, 'committed_source_blobs': committed_rows, 'remote_readback_source_blobs': remote_rows, 'new_file_count': len(remote_rows), 'new_file_bytes': sum(row['bytes'] for row in remote_rows), 'parent_gitlinks': tree_links(parent), 'commit_gitlinks': tree_links(commit), 'all_nine_fresh_parent_gitlinks_preserved': True, 'full_new_population_remote_Git_blobs_verified': True, 'hf_commit': stage['hf_commit'], 'original_guard_before': before, 'original_guard_after': after, 'private_checkout_clean': True, 'original_root_or_child_HEAD_index_mutations': 0, 'sealed_Q5_P6_S4_mutations': 0, 'raw_SDK_logs_archives_caches_private_worktrees_added': 0, 'native_model_solver_test_fit_codec_jobs': 0, 'project_imports': 0, 'commit_calls': commit_calls, 'push_calls': push_calls, 'concurrency_rebases': rebases, 'force_push_calls': 0, 'proof_authority': False, 'execution_authority': False, 'completion_authority': False, 'planner_activation': False, 'full_task_satisfaction': 'unknown'}
    result_pin = write_new('closed.json', result)
    print(json.dumps({'status': result['status'], 'commit': commit, 'parent': parent, 'remote_main': remote, 'tree': tree, 'new_files': len(remote_rows), 'new_bytes': result['new_file_bytes'], 'closure': result_pin, 'original_guards_unchanged': True, 'normal_push_calls': push_calls, 'force_push_calls': 0}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preparation-root', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--expected-final-stage-sha256', required=True)
    parser.add_argument('--independent-review', required=True, type=Path)
    parser.add_argument('--expected-independent-review-sha256', required=True)
    args = parser.parse_args()
    ROOT = args.preparation_root
    need(ROOT.is_absolute() and ROOT.resolve(strict=True)==ROOT and ROOT.parent==WORKSPACE/'maintenance' and
         re.fullmatch('ranker-objective-scalar-private-git-preparation-20261005-[0-9]{2}',ROOT.name) is not None, 'fresh canonical private preparation namespace')
    REPO = ROOT/'root'
    need(REPO.resolve(strict=True)==REPO and REPO.is_dir(), 'isolated private checkout required')
    OUTPUT = args.output
    need(OUTPUT.is_absolute() and OUTPUT.resolve()==OUTPUT and OUTPUT.parent==WORKSPACE/'maintenance' and
         re.fullmatch('ranker-objective-scalar-git-publication-20261005-[0-9]{2}',OUTPUT.name) is not None, 'new durable external publication namespace')
    STAGE_SHA = args.expected_final_stage_sha256
    PEER_PATH, PEER_SHA = args.independent_review, args.expected_independent_review_sha256
    need(PEER_PATH.is_absolute() and PEER_PATH.resolve(strict=True) == PEER_PATH and PEER_PATH.is_relative_to(WORKSPACE/'maintenance'),
         'canonical durable external peer receipt required')
    need(all(re.fullmatch('[0-9a-f]{64}', value) is not None for value in (STAGE_SHA, PEER_SHA)), 'external stage/peer SHA256 required')
    try:
        main()
    except Exception as error:
        if OUTPUT.exists() and not (OUTPUT/'closed.json').exists() and not (OUTPUT/'failed.json').exists():
            write_new('failed.json', {'schema': 'ranker-objective-scalar-Git-publication-retained-failure@1',
                'status': 'failed_retained_without_force_or_rebase', 'created_at_utc': timestamp(),
                'producer': pin(Path(__file__).resolve()), 'final_stage_sha256': STAGE_SHA,
                'independent_review_sha256': PEER_SHA, 'reason': str(error)[:2048] if isinstance(error, ValueError) else type(error).__name__,
                **STATE, 'force_push_calls': 0, 'concurrency_rebases': 0,
                'proof_authority': False, 'execution_authority': False, 'completion_authority': False, 'planner_activation': False})
        raise
