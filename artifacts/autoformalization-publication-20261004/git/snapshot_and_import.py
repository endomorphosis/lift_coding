"""Version owned source work through temporary indexes and fresh Git refs."""
from __future__ import annotations

import ast
import hashlib
import json
import os
import stat
import subprocess
from datetime import UTC, datetime
from pathlib import Path

OUT = Path(__file__).resolve().parent
SCOPE = OUT / 'publication_compact.json'
SCOPE_SHA = 'a5b0ae2bf3d6839b323b19e144dc38970f0af13065ec0de81cacdd4ca85df906'
ROOT = Path('/home/barberb/lift_coding')
CANONICAL = {str(ROOT / part) for part in ('', 'external/ipfs_datasets', 'external/ipfs_accelerate', 'external/ipfs_kit', 'Mcp-Plus-Plus', 'hallucinate_app', 'swissknife')}
RUN = OUT / 'snapshot-import-01'
MAX_BLOB = 100 * 1024**2
ENV = {key: value for key, value in os.environ.items() if key not in {'GIT_INDEX_FILE', 'GIT_DIR', 'GIT_WORK_TREE'}}
ENV.update(GIT_OPTIONAL_LOCKS='0', GIT_TERMINAL_PROMPT='0')
SOURCE_SUFFIXES = {'.py', '.pyi', '.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs', '.css', '.scss', '.html', '.sh', '.rs', '.go', '.c', '.h', '.cpp', '.hpp', '.java', '.kt', '.swift', '.lean', '.toml', '.yaml', '.yml', '.json', '.jsonl', '.md', '.mdx', '.rst', '.txt', '.xml', '.svg', '.png', '.jpg', '.jpeg', '.gif', '.ico', '.ipynb', '.sql', '.csv', '.tsv', '.cmake', '.lock', '.ini', '.cfg', '.conf', '.proto'}
SOURCE_NAMES = {'Dockerfile', 'Makefile', 'LICENSE', 'NOTICE', '.gitignore', '.gitattributes', '.gitmodules'}
SENSITIVE_NAMES = {'.env', '.env.local', '.env.production', 'credentials', 'credentials.json', '.netrc', '.git-credentials', 'id_rsa', 'id_ed25519'}
RUNTIME_PARTS = {'.git', '.venv', 'venv', '__pycache__', 'node_modules', '.cache', '.worktrees', 'worktrees', 'runtime_archives', 'runtime-archives', 'build', 'dist', 'target'}
BINARY_SUFFIXES = {'.safetensors', '.pt', '.pth', '.ckpt', '.onnx', '.gguf', '.bin', '.npy', '.npz', '.pkl', '.pickle', '.tar', '.xz', '.gz', '.zip', '.7z', '.so', '.dll', '.dylib', '.exe', '.mp4', '.mov'}
LOCAL_ORIGIN_ALIASES = {
    str(ROOT / 'external/ipfs_datasets'): 'github.com/endomorphosis/ipfs_datasets_py',
    str(ROOT / 'external/ipfs_accelerate'): 'github.com/endomorphosis/ipfs_accelerate_py',
    str(ROOT / 'external/ipfs_kit'): 'github.com/endomorphosis/ipfs_kit_py',
    str(ROOT / '.worktrees/semantic-addressed-world-model-r2/ipfs_datasets_py'): 'github.com/endomorphosis/ipfs_datasets_py',
    str(ROOT / '.worktrees/semantic-addressed-world-model-r2/ipfs_kit_py'): 'github.com/endomorphosis/ipfs_kit_py',
}


def now():
    return datetime.now(UTC).isoformat()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def raw(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def save(path, value):
    data = raw(value) + b'\n'
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, 'wb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    return {'path': str(path), 'bytes': len(data), 'sha256': sha(data)}


def marker_gitdir(path):
    marker = path / '.git'
    if marker.is_dir():
        return marker.resolve()
    data = marker.read_text().strip()
    if not data.startswith('gitdir: '):
        raise ValueError('existing Git pointer required')
    return (path / data[8:]).resolve()


def git(path, *args, index=None, data=None, timeout=120, allowed=(0,)):
    directory = marker_gitdir(path)
    env = dict(ENV)
    if index is not None:
        env['GIT_INDEX_FILE'] = str(index)
    command = ['git', '-C', str(path), '--git-dir=' + str(directory), '--work-tree=' + str(path),
               '-c', 'core.fsmonitor=false', '-c', 'commit.gpgsign=false', *args]
    result = subprocess.run(command, input=data, capture_output=True,
                            env=env, timeout=timeout, check=False)
    if result.returncode not in allowed:
        raise RuntimeError('Git ' + args[0] + ' exited ' + str(result.returncode) + ': ' + result.stderr.decode('utf-8', 'replace')[:1000])
    return result.stdout


def text_git(path, *args, **kwargs):
    return git(path, *args, **kwargs).decode().strip()


def file_state(path):
    try:
        info = path.lstat()
    except FileNotFoundError:
        return {'exists': False}, None
    if stat.S_ISLNK(info.st_mode):
        data = os.fsencode(os.readlink(path))
        mode = '120000'
    elif stat.S_ISREG(info.st_mode):
        if info.st_size > MAX_BLOB:
            return {'exists': True, 'bytes': info.st_size, 'oversized': True}, None
        descriptor = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0))
        with os.fdopen(descriptor, 'rb') as stream:
            data = stream.read(MAX_BLOB + 1)
        mode = '100755' if info.st_mode & stat.S_IXUSR else '100644'
    else:
        return {'exists': True, 'ordinary_source_file': False}, None
    after = path.lstat()
    before_identity = (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)
    after_identity = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns)
    if before_identity != after_identity or len(data) > MAX_BLOB:
        raise ValueError('selected file changed while reading: ' + str(path))
    return {'exists': True, 'bytes': len(data), 'sha256': sha(data), 'mode': mode,
            'mtime_ns': info.st_mtime_ns, 'inode': info.st_ino}, data


def index_state(path):
    state, _data = file_state(marker_gitdir(path) / 'index')
    return state


def exclude_reason(root, relative, tracked):
    item = Path(relative)
    if item.is_absolute() or '..' in item.parts:
        return 'unsafe_relative_path'
    if item.name in SENSITIVE_NAMES or item.name.startswith('.env.') or item.suffix.lower() in {'.pem', '.key', '.p12', '.pfx'}:
        return 'credential_filename'
    if RUNTIME_PARTS.intersection(item.parts):
        return 'runtime_or_build_tree'
    if item.suffix.lower() in BINARY_SUFFIXES:
        return 'model_binary_archive_or_runtime_binary'
    for parent in (root / item).parents:
        if parent == root:
            break
        if (parent / '.git').exists():
            return 'embedded_repository_copy'
    if not tracked and item.suffix.lower() not in SOURCE_SUFFIXES and item.name not in SOURCE_NAMES:
        return 'untracked_non_source_type'
    return None


def fetch_ref(target, source_common, commit, ref):
    existing = text_git(target, 'rev-parse', '--verify', ref, allowed=(0, 128))
    if existing:
        raise ValueError('publication ref already exists: ' + ref)
    git(target, 'fetch', '--no-tags', '--no-write-fetch-head', '--no-auto-maintenance', str(source_common), commit + ':' + ref)
    observed = text_git(target, 'rev-parse', '--verify', ref)
    if observed != commit:
        raise ValueError('imported commit differs')
    text_git(target, 'cat-file', '-e', commit + '^{commit}')
    return {'target_worktree': str(target), 'source_common_dir': str(source_common), 'commit': commit,
            'ref': ref, 'commit_verified': True, 'force_used': False, 'origin_push_performed': False}


def snapshot(item, target, number):
    path = Path(item['worktree'])
    captured = item['head']
    identifier = sha((item['git_common_dir'] + '\0' + str(path)).encode())[:24]
    receipt_path = RUN / 'snapshots' / (identifier + '.json')
    started = now()
    before_index = index_state(path)
    before_head = text_git(path, 'rev-parse', 'HEAD')
    before_branch = text_git(path, 'symbolic-ref', '-q', 'HEAD', allowed=(0, 1))
    if before_head != captured:
        return save(receipt_path, {'status': 'blocked_captured_head_changed', 'worktree': str(path),
                                  'captured_head': captured, 'observed_head': before_head, 'git_mutations_performed': False})
    head_entries = {}
    for entry in git(path, 'ls-tree', '-r', '-z', captured).split(b'\0'):
        if entry:
            metadata, name = entry.split(b'\t', 1)
            head_entries[os.fsdecode(name)] = metadata.decode().split()
    if git(path, 'ls-files', '--unmerged', '-z'):
        raise ValueError('current worktree has unmerged index entries')
    current_gitlinks = {}
    for entry in git(path, 'ls-files', '--stage', '-z').split(b'\0'):
        if entry.startswith(b'160000 '):
            metadata, relative = entry.split(b'\t', 1)
            current_gitlinks[os.fsdecode(relative)] = metadata.decode().split()[1]
    tracked = {os.fsdecode(entry) for entry in git(path, 'diff', '--no-ext-diff', '--no-textconv', captured, '--name-only', '-z', '--').split(b'\0') if entry}
    sources = [name for name in item['source_roots'] if (path / name).exists()]
    sources += [entry.name for entry in path.iterdir() if entry.is_file() and (entry.suffix.lower() in SOURCE_SUFFIXES or entry.name in SOURCE_NAMES)]
    untracked = {os.fsdecode(entry) for entry in git(path, 'ls-files', '--others', '--exclude-standard', '-z', '--', *sorted(set(sources))).split(b'\0') if entry} if sources else set()
    selected, excluded, syntax = [], [], []
    temporary = RUN / 'temporary-indexes' / identifier
    temporary.mkdir(mode=0o700)
    index = temporary / 'index'
    git(path, 'read-tree', captured, index=index)
    entries = []
    for relative in sorted(tracked | untracked):
        old = head_entries.get(relative)
        if (old and old[0] == '160000') or relative in current_gitlinks:
            excluded.append({'path': relative, 'reason': 'gitlink_for_root_leaf_resolution',
                             'captured_pointer': old[2] if old else None, 'index_pointer': current_gitlinks.get(relative)})
            continue
        reason = exclude_reason(path, relative, relative in tracked)
        if reason:
            excluded.append({'path': relative, 'reason': reason})
            continue
        state, data = file_state(path / relative)
        if state.get('oversized') or state.get('ordinary_source_file') is False:
            excluded.append({'path': relative, 'reason': 'new_blob_over_100MiB' if state.get('oversized') else 'nonordinary_source_path', 'bytes': state.get('bytes')})
            continue
        if data is None:
            if old is None:
                continue
            entries.append(b'0 ' + b'0' * len(captured) + b'\t' + os.fsencode(relative) + b'\0')
            blob = None
        else:
            if relative.endswith('.py') and old is None:
                try:
                    if len(data) > 2 * 1024**2:
                        syntax.append({'path': relative, 'status': 'not_checked_size_bound_2MiB'})
                    else:
                        compile(data, str(path / relative), 'exec', flags=ast.PyCF_ONLY_AST, dont_inherit=True)
                        syntax.append({'path': relative, 'status': 'passed_python3_syntax'})
                except (SyntaxError, UnicodeError, ValueError) as error:
                    syntax.append({'path': relative, 'status': 'syntax_finding_preserved_archival_source', 'error_type': type(error).__name__, 'line': getattr(error, 'lineno', None)})
            blob = text_git(path, 'hash-object', '-w', '--stdin', data=data)
            entries.append(state['mode'].encode() + b' ' + blob.encode() + b'\t' + os.fsencode(relative) + b'\0')
        selected.append({'path': relative, 'selection': 'tracked_change' if relative in tracked else 'untracked_source', 'file_state_before': state, 'git_blob': blob})
    if entries:
        git(path, 'update-index', '-z', '--index-info', index=index, data=b''.join(entries))
    tree = text_git(path, 'write-tree', index=index)
    original_tree = text_git(path, 'rev-parse', captured + '^{tree}')
    for entry in selected:
        after, _data = file_state(path / entry['path'])
        if after != entry['file_state_before']:
            raise ValueError('selected source changed before snapshot commit')
        entry['file_state_after'] = after
    if before_head != text_git(path, 'rev-parse', 'HEAD') or before_index != index_state(path) or before_branch != text_git(path, 'symbolic-ref', '-q', 'HEAD', allowed=(0, 1)):
        raise ValueError('active worktree HEAD/index/branch changed concurrently')
    commit, source_ref, imported, created_commit_binding = None, None, None, None
    if tree != original_tree:
        source_ref = 'refs/heads/publication/wip-20261004/' + identifier
        if text_git(path, 'rev-parse', '--verify', source_ref, allowed=(0, 128)):
            raise ValueError('snapshot publication ref already exists')
        message = ('Snapshot retained source work for publication\n\nWorktree identity: ' + identifier + '\nSelected-source manifest SHA256: ' + sha(raw(selected)) + '\n').encode()
        commit = text_git(path, 'commit-tree', tree, '-p', captured, data=message)
        git(path, 'update-ref', source_ref, commit, '0' * len(commit))
        created_commit_binding = save(RUN / 'created-source-commits' / (identifier + '.json'), {
            'worktree': str(path), 'source_common_dir': item['git_common_dir'], 'captured_parent': captured,
            'tree': tree, 'commit': commit, 'ref': source_ref, 'selected_source_manifest_sha256': sha(raw(selected)),
            'created_utc': now(), 'origin_push_performed': False, 'main_merge_performed': False})
        imported = fetch_ref(target, Path(item['git_common_dir']), commit,
                             'refs/remotes/publication-wip-20261004/' + identifier)
    after_index = index_state(path)
    after_head = text_git(path, 'rev-parse', 'HEAD')
    after_branch = text_git(path, 'symbolic-ref', '-q', 'HEAD', allowed=(0, 1))
    for entry in selected:
        after, _data = file_state(path / entry['path'])
        if after != entry['file_state_before']:
            raise ValueError('selected source changed after snapshot commit')
    if before_index != after_index or before_head != after_head or before_branch != after_branch:
        raise ValueError('active worktree state changed during publication')
    receipt = {'schema': 'read-only-active-worktree-source-snapshot/v1', 'status': 'source_snapshot_created' if commit else 'no_meaningful_source_tree_change',
               'started_utc': started, 'finished_utc': now(), 'number': number, 'worktree': str(path), 'normalized_origin': item['normalized_origin'],
               'source_common_dir': item['git_common_dir'], 'captured_parent': captured, 'tree': tree, 'source_commit': commit, 'source_ref': source_ref,
               'created_commit_binding': created_commit_binding,
               'imported_snapshot': imported, 'selected_source_files': selected, 'excluded_files': excluded, 'python_syntax_checks': syntax,
               'untracked_source_roots': sorted(set(sources)), 'untracked_full_repository_walk_performed': False,
               'original_index_before': before_index, 'original_index_after': after_index, 'original_head_before': before_head, 'original_head_after': after_head,
               'original_branch_before': before_branch, 'original_branch_after': after_branch, 'active_worktree_index_head_branch_and_selected_bytes_preserved': True,
               'temporary_index': str(index), 'original_files_modified': False, 'main_merge_performed': False, 'origin_push_performed': False,
               'source_blob_filters_executed': False, 'snapshot_content_scope': 'exact_working_file_bytes_no_model_or_semantic_admission',
               'optimizer_updates': 0, 'production_model_calls': 0, 'credentials_contents_read': False}
    return save(receipt_path, receipt)


def main():
    data = SCOPE.read_bytes()
    if sha(data) != SCOPE_SHA:
        raise ValueError('externally selected compact inventory differs')
    scope = json.loads(data)
    RUN.mkdir(mode=0o700)
    for name in ('snapshots', 'imports', 'temporary-indexes', 'failures', 'created-source-commits'):
        (RUN / name).mkdir(mode=0o700)
    groups = [group for group in scope['normalized_origin_groups'] if group['endomorphosis_owned']]
    groups_by_origin = {group['normalized_origin']: group for group in groups}
    full_data = (OUT / 'git_inventory.json').read_bytes()
    if sha(full_data) != scope['full_inventory_binding']['sha256']:
        raise ValueError('full inventory binding differs')
    full = json.loads(full_data)
    local_items = []
    for local_group in scope['normalized_origin_groups']:
        owned_origin = LOCAL_ORIGIN_ALIASES.get(local_group['normalized_origin'])
        if owned_origin is None:
            continue
        group = groups_by_origin[owned_origin]
        common_dirs = {row['common_dir'] for row in local_group['repositories']}
        for repo in full['repositories']:
            if repo['git_common_dir'] not in common_dirs:
                continue
            for branch in repo['local_branches']:
                group['pending_head_source'].setdefault(branch['commit'], {'common_dir': repo['git_common_dir'], 'ref': branch['ref']})
            for tree in repo['worktrees']:
                if tree.get('detached'):
                    group['pending_head_source'].setdefault(tree['HEAD'], {'common_dir': repo['git_common_dir'], 'detached_worktree': tree['worktree']})
                if tree.get('available') and (sum(tree['status']['record_counts'].get(key, 0) for key in ('1', '2', 'u')) or tree['untracked'].get('file_count_observed', 0)):
                    local_items.append({'worktree': tree['worktree'], 'normalized_origin': owned_origin,
                                        'git_common_dir': repo['git_common_dir'], 'head': tree['HEAD'],
                                        'source_roots': tree['untracked'].get('source_roots', []),
                                        'original_local_origin': local_group['normalized_origin']})
    targets = {}
    for group in groups:
        target = group.get('canonical_path')
        if target is None:
            target = next((row['representative'] for row in group['repositories'] if Path(row['representative']).is_dir() and (Path(row['representative']) / '.git').exists()), None)
        if target:
            targets[group['normalized_origin']] = Path(target)
    items = [item for item in [*scope['owned_dirty_source_worktrees'], *local_items] if item['worktree'] not in CANONICAL]
    items = list({item['worktree']: item for item in items}.values())
    target_roles = {}
    for origin, target in targets.items():
        remote_head = text_git(target, 'symbolic-ref', '-q', 'refs/remotes/origin/HEAD', allowed=(0, 1, 128))
        candidates = ['refs/remotes/origin/main', 'refs/remotes/origin/master'] if str(target) in CANONICAL else [remote_head, 'refs/remotes/origin/main', 'refs/remotes/origin/master']
        selected_head = None
        for candidate in candidates:
            if candidate and text_git(target, 'rev-parse', '--verify', candidate, allowed=(0, 128)):
                selected_head = candidate
                break
        ancestors = set(text_git(target, 'rev-list', selected_head).splitlines()) if selected_head else set()
        group = groups_by_origin[origin]
        group['pending_head_source'] = {head: source for head, source in group.get('pending_head_source', {}).items() if head not in ancestors}
        target_roles[origin] = {'canonical_worktree': str(target), 'observed_default_remote_ref': selected_head,
                               'pending_unique_existing_heads': len(group['pending_head_source']), 'remote_write_permission_verified': False}
    plan = {'schema': 'source-snapshot-and-local-history-import-plan/v1', 'created_utc': now(), 'scope_file_sha256': SCOPE_SHA,
            'helper_file_sha256': sha(Path(__file__).read_bytes()), 'snapshot_worktrees': items, 'canonical_checkouts_excluded': sorted(CANONICAL),
            'targets': {key: str(value) for key, value in targets.items()}, 'original_indexes_heads_files_preserved': True,
            'target_roles': target_roles, 'local_origin_aliases_explicitly_authorized_by_root': LOCAL_ORIGIN_ALIASES,
            'new_blob_max_bytes': MAX_BLOB, 'main_merges_authorized_for_this_helper': False, 'origin_pushes_authorized_for_this_helper': False}
    save(RUN / 'plan.json', plan)
    receipts, failures, imports = [], [], []
    for group in groups:
        target = targets.get(group['normalized_origin'])
        if target is None:
            continue
        for commit, source in group.get('pending_head_source', {}).items():
            identifier = sha((group['normalized_origin'] + '\0' + commit).encode())[:24]
            try:
                value = fetch_ref(target, Path(source['common_dir']), commit, 'refs/remotes/publication-history-20261004/' + identifier)
                value.update(normalized_origin=group['normalized_origin'], original_source=source, imported_utc=now())
                imports.append(save(RUN / 'imports' / (identifier + '.json'), value))
            except Exception as error:
                failures.append(save(RUN / 'failures' / ('history-' + identifier + '.json'), {'kind': 'history_import', 'normalized_origin': group['normalized_origin'], 'commit': commit, 'source': source, 'error_type': type(error).__name__, 'error': str(error)[:1500]}))
        print(json.dumps({'phase': 'history_import', 'origin': group['normalized_origin'], 'total_imported': len(imports), 'failures': len(failures)}), flush=True)
    for number, item in enumerate(items, 1):
        try:
            target = targets[item['normalized_origin']]
            receipts.append(snapshot(item, target, number))
        except Exception as error:
            identifier = sha((item['git_common_dir'] + '\0' + item['worktree']).encode())[:24]
            failures.append(save(RUN / 'failures' / ('snapshot-' + identifier + '.json'), {'kind': 'source_snapshot', 'worktree': item['worktree'], 'captured_head': item['head'], 'error_type': type(error).__name__, 'error': str(error)[:1500], 'main_merge_performed': False, 'origin_push_performed': False}))
        if number % 10 == 0 or number == len(items):
            print(json.dumps({'phase': 'source_snapshots', 'processed': number, 'total': len(items), 'receipts': len(receipts), 'failures': len(failures)}), flush=True)
    summary = {'schema': 'source-snapshot-and-local-history-import-results/v1', 'finished_utc': now(), 'snapshot_worktree_count': len(items),
               'snapshot_receipt_bindings': receipts, 'history_import_receipt_bindings': imports, 'failure_receipt_bindings': failures,
               'canonical_targets': {key: str(value) for key, value in targets.items()}, 'main_merges_performed': False, 'origin_pushes_performed': False,
               'original_checkout_reset_or_stash_performed': False, 'original_refs_deleted_or_rewritten': False}
    binding = save(RUN / 'results.json', summary)
    print(json.dumps({'results_binding': binding, 'snapshot_receipts': len(receipts), 'history_imports': len(imports), 'failure_count': len(failures)}), flush=True)


if __name__ == '__main__':
    main()
