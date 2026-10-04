"""Read-only, bounded Git publication inventory; writes only new inventory files."""
from __future__ import annotations

import concurrent.futures
import hashlib
import json
import os
import re
import selectors
import shutil
import stat
import subprocess
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

ROOT = Path('/home/barberb/lift_coding')
OUT = ROOT / 'artifacts/autoformalization-publication-20261004/git'
ENV = {**os.environ, 'GIT_OPTIONAL_LOCKS': '0', 'GIT_TERMINAL_PROMPT': '0'}
LIMIT = 32 * 1024**2
SOURCE_EXTENSIONS = {'.py', '.js', '.jsx', '.ts', '.tsx', '.sh', '.rs', '.go', '.c', '.h', '.cpp', '.java', '.lean', '.toml', '.yaml', '.yml'}
SENSITIVE_NAMES = {'.env', '.env.local', '.env.production', 'credentials', 'credentials.json', 'id_rsa', 'id_ed25519', '.netrc', '.git-credentials'}
DISCOVERY_ERRORS = []


def git_command(path, *args):
    marker = path / '.git'
    directory = marker if marker.is_dir() else None
    if marker.is_file() and marker.stat().st_size <= 4096:
        text = marker.read_text().strip()
        if text.startswith('gitdir: '):
            directory = (path / text[8:]).resolve()
    selection = [] if directory is None else ['--git-dir=' + str(directory), '--work-tree=' + str(path)]
    return ['git', '-C', str(path), *selection, *args]


def sanitize_url(value):
    value = value.strip()
    if '://' in value:
        parsed = urlsplit(value)
        host = parsed.hostname or '<redacted-host>'
        if parsed.port:
            host += ':' + str(parsed.port)
        return urlunsplit((parsed.scheme, host, parsed.path, '', ''))
    return re.sub(r'^[^/@\s]+@', '', value)


def sanitize_error(value):
    return re.sub(r'(?:https?|ssh|git)://[^\s]+', lambda match: sanitize_url(match.group(0)), value)[:2000]


def git(path, *args, timeout=30):
    process = subprocess.run(git_command(path, *args), env=ENV, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, timeout=timeout, check=False)
    if len(process.stdout) > LIMIT:
        raise RuntimeError('bounded Git output exceeded')
    if process.returncode:
        raise RuntimeError(sanitize_error(process.stderr.decode('utf-8', 'replace')))
    return process.stdout


def optional_git(path, *args):
    try:
        return git(path, *args).decode('utf-8', 'replace').strip()
    except (RuntimeError, subprocess.TimeoutExpired):
        return None


def snapshot_file(path):
    try:
        info = path.stat()
        if not stat.S_ISREG(info.st_mode):
            return {'exists': True, 'ordinary_file': False}
        digest = hashlib.sha256()
        with path.open('rb') as stream:
            while block := stream.read(1024 * 1024):
                digest.update(block)
        return {'exists': True, 'bytes': info.st_size, 'mtime_ns': info.st_mtime_ns,
                'sha256': digest.hexdigest()}
    except FileNotFoundError:
        return {'exists': False}


def worktrees(path):
    text = git(path, 'worktree', 'list', '--porcelain').decode('utf-8', 'replace')
    result = []
    for block in text.strip().split('\n\n'):
        item = {}
        for line in block.splitlines():
            key, _, value = line.partition(' ')
            item[key] = value if value else True
        if 'worktree' in item:
            result.append(item)
    common = optional_git(path, 'rev-parse', '--path-format=absolute', '--git-common-dir')
    actual_top = optional_git(path, 'rev-parse', '--show-toplevel')
    for item in result:
        if common and actual_top and Path(item['worktree']).resolve() == Path(common).resolve():
            item['reported_primary_git_directory'] = item['worktree']
            item['worktree'] = actual_top
    return result


def gitlinks(path):
    rows = []
    for entry in git(path, 'ls-files', '--stage', '-z').split(b'\0'):
        if entry.startswith(b'160000 '):
            metadata, name = entry.split(b'\t', 1)
            mode, oid, stage = metadata.decode().split()
            relative = name.decode('utf-8', 'replace')
            actual = path / relative
            rows.append({'path': relative, 'index_commit': oid, 'index_stage': int(stage),
                         'initialized': (actual / '.git').exists(),
                         'working_head': optional_git(actual, 'rev-parse', 'HEAD') if (actual / '.git').exists() else None})
    return rows


def discover():
    pending = [ROOT, *(item for item in (ROOT / 'external').iterdir() if (item / '.git').exists())]
    repos = {}
    while pending:
        path = pending.pop(0)
        if not path.is_dir() or not (path / '.git').exists():
            continue
        common = optional_git(path, 'rev-parse', '--path-format=absolute', '--git-common-dir')
        if common is None or common in repos:
            continue
        trees = worktrees(path)
        repos[common] = {'representative': str(path), 'git_common_dir': common, 'worktrees': trees}
        for tree in trees:
            current = Path(tree['worktree'])
            if not current.is_dir():
                continue
            try:
                links = gitlinks(current)
            except (RuntimeError, subprocess.TimeoutExpired) as error:
                DISCOVERY_ERRORS.append({'worktree': str(current), 'phase': 'gitlink_discovery',
                                         'error_type': type(error).__name__, 'error': sanitize_error(str(error))})
                links = []
            for link in links:
                if link['initialized']:
                    pending.append(current / link['path'])
            external = current / 'external'
            if external.is_dir():
                pending.extend(item for item in external.iterdir() if (item / '.git').exists())
        if len(repos) > 256:
            raise RuntimeError('repository discovery exceeds explicit safety bound')
    return repos


def status_summary(path):
    entries = git(path, 'status', '--porcelain=v2', '-z', '--untracked-files=normal', '--ignore-submodules=dirty').split(b'\0')
    counts, conflicts, samples, untracked = Counter(), [], [], []
    position = 0
    while position < len(entries):
        item = entries[position].decode('utf-8', 'replace')
        position += 1
        if not item:
            continue
        kind = item[0]
        counts[kind] += 1
        if kind in {'1', '2', 'u'}:
            fields = item.split(' ', {'1': 8, '2': 9, 'u': 10}[kind])
            relative = fields[-1]
            xy = fields[1]
            counts['staged'] += xy[0] != '.'
            counts['unstaged'] += xy[1] != '.'
            if kind == 'u':
                conflicts.append({'path': relative, 'status': xy})
            if len(samples) < 200:
                samples.append({'path': relative, 'status': xy, 'record_type': kind})
            if kind == '2':
                position += 1
        elif kind == '?':
            if len(untracked) < 200:
                untracked.append(item[2:])
    return {'record_counts': dict(counts), 'conflict_count': len(conflicts), 'conflicts': conflicts[:1000],
            'conflict_paths_truncated': len(conflicts) > 1000, 'tracked_change_samples': samples,
            'untracked_normal_entries': untracked, 'untracked_normal_entry_count': counts['?'],
            'submodule_dirty_contents_separately_inventoried': True}


def untracked_summary(path):
    """Target source roots only; never revisit huge artifact/runtime archives."""
    targets = [name for name in ('ipfs_datasets_py', 'ipfs_accelerate_py', 'ipfs_kit_py', 'tests', 'docs', 'scripts', 'tools', 'src', 'packages', 'implementation_plan', '.github') if (path / name).is_dir()]
    targets += [item.name for item in path.iterdir() if item.is_file() and item.suffix.lower() in SOURCE_EXTENSIONS | {'.md', '.rst'}]
    if not targets:
        return {'complete': False, 'scope': 'no_standard_source_roots_found', 'full_untracked_tree_walk_performed': False}
    process = subprocess.Popen(git_command(path, 'ls-files', '--others', '--exclude-standard', '-z', '--', *targets),
                               env=ENV, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    started, pending, count = time.monotonic(), b'', 0
    top, categories, largest, sensitive = Counter(), Counter(), [], []
    complete = True
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ)
    os.set_blocking(process.stdout.fileno(), False)
    while True:
        if time.monotonic() - started > 15:
            complete = False
            process.terminate()
            break
        if not selector.select(timeout=1):
            continue
        block = os.read(process.stdout.fileno(), 65536)
        if not block:
            break
        pending += block
        pieces = pending.split(b'\0')
        pending = pieces.pop()
        for piece in pieces:
            relative = piece.decode('utf-8', 'replace')
            count += 1
            top[relative.split('/', 1)[0]] += 1
            suffix = Path(relative).suffix.lower()
            category = 'source' if suffix in SOURCE_EXTENSIONS else 'documentation' if suffix in {'.md', '.rst'} else 'artifact_or_data' if relative.startswith(('artifacts/', 'data/', 'workspace/')) else 'other'
            categories[category] += 1
            if Path(relative).name in SENSITIVE_NAMES or suffix in {'.pem', '.key', '.p12'}:
                if len(sensitive) < 100:
                    sensitive.append(relative)
            try:
                info = (path / relative).lstat()
                if stat.S_ISREG(info.st_mode) and info.st_size >= 10 * 1024**2:
                    largest.append({'path': relative, 'bytes': info.st_size})
                    largest = sorted(largest, key=lambda item: (-item['bytes'], item['path']))[:30]
            except OSError:
                pass
        if count > 100_000:
            complete = False
            process.terminate()
            break
    selector.close()
    process.stdout.close()
    try:
        returncode = process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        returncode = process.wait()
    return {'file_count_observed': count, 'selected_source_roots_complete': complete and returncode == 0, 'returncode': returncode,
            'scope': 'selected_standard_source_roots_only', 'source_roots': targets,
            'complete_full_repository_inventory': False, 'full_untracked_tree_walk_performed': False,
            'top_level_counts': dict(top.most_common(40)), 'category_counts': dict(categories),
            'largest_files_at_least_10MiB': largest, 'sensitive_filename_candidates_exclude_from_publication': sensitive,
            'sensitive_file_contents_read': False, 'ignored_files_included': False}


def instructions(path):
    found = []
    for parent in reversed((path, *path.parents)):
        candidate = parent / 'AGENTS.md'
        if candidate.is_file():
            data = candidate.read_bytes()
            if len(data) <= 256 * 1024:
                found.append({'path': str(candidate), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
                              'text': data.decode('utf-8', 'replace')})
    return found


def inspect_tree(tree):
    path = Path(tree['worktree'])
    if not path.is_dir():
        return {**tree, 'available': False}
    gitdir = Path(git(path, 'rev-parse', '--absolute-git-dir').decode().strip())
    before = snapshot_file(gitdir / 'index')
    operations = {name: (gitdir / name).exists() for name in ('MERGE_HEAD', 'CHERRY_PICK_HEAD', 'REVERT_HEAD', 'rebase-merge', 'rebase-apply', 'BISECT_LOG')}
    result = {**tree, 'available': True, 'git_dir': str(gitdir), 'active_operations': operations,
              'status': status_summary(path), 'untracked': untracked_summary(path), 'gitlinks': gitlinks(path),
              'instructions': instructions(path), 'index_before': before}
    result['head_vs_cached_origin_main_left_right'] = optional_git(path, 'rev-list', '--left-right', '--count', 'HEAD...refs/remotes/origin/main')
    result['index_after'] = snapshot_file(gitdir / 'index')
    result['index_unchanged_during_inventory'] = before == result['index_after']
    return result


def inspect_repo(repo):
    path = Path(repo['representative'])
    refs = []
    for line in git(path, 'for-each-ref', '--format=%(refname)%09%(objectname)%09%(upstream)%09%(upstream:track)', 'refs/heads').decode().splitlines():
        name, oid, upstream, track = line.split('\t')
        refs.append({'ref': name, 'commit': oid, 'upstream': upstream or None, 'upstream_track': track or None})
    merged = optional_git(path, 'for-each-ref', '--merged=refs/remotes/origin/main', '--format=%(refname)', 'refs/heads')
    if merged is not None:
        known = set(merged.splitlines())
        for row in refs:
            row['already_merged_into_cached_origin_main'] = row['ref'] in known
    remotes = {}
    for name in git(path, 'remote').decode().splitlines():
        urls = optional_git(path, 'remote', 'get-url', '--all', name)
        push = optional_git(path, 'remote', 'get-url', '--push', '--all', name)
        remotes[name] = {'fetch_urls': [sanitize_url(item) for item in (urls or '').splitlines()],
                         'push_urls': [sanitize_url(item) for item in (push or '').splitlines()]}
    large_blobs = []
    tracked = 0
    for line in git(path, 'ls-tree', '-r', '-l', 'HEAD').decode('utf-8', 'replace').splitlines():
        metadata, relative = line.split('\t', 1)
        fields = metadata.split()
        tracked += 1
        if fields[1] == 'blob' and fields[3].isdigit() and int(fields[3]) >= 10 * 1024**2:
            large_blobs.append({'path': relative, 'bytes': int(fields[3]), 'object': fields[2]})
    return {**repo, 'local_branches': refs, 'local_branch_count': len(refs), 'sanitized_remotes': remotes,
            'cached_origin_main': optional_git(path, 'rev-parse', '--verify', 'refs/remotes/origin/main'),
            'representative_HEAD_tree_entry_count': tracked, 'tracked_blobs_at_least_10MiB': large_blobs,
            'credential_helper_configured': optional_git(path, 'config', '--get-all', 'credential.helper') is not None}


def auth_availability():
    result = {'gh_installed': shutil.which('gh') is not None,
              'token_environment_present': any(bool(os.environ.get(key)) for key in ('GH_TOKEN', 'GITHUB_TOKEN')),
              'ssh_agent_socket_present': bool(os.environ.get('SSH_AUTH_SOCK')),
              'credential_content_read_or_saved': False, 'remote_write_permission_verified': False}
    if result['gh_installed']:
        try:
            process = subprocess.run(['gh', 'auth', 'status', '--active', '--hostname', 'github.com'],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15, check=False)
            result['gh_auth_status_exit_code'] = process.returncode
        except subprocess.TimeoutExpired:
            result['gh_auth_status_timed_out'] = True
    return result


def save_new(name, value):
    data = json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2).encode() + b'\n'
    descriptor = os.open(OUT / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, 'wb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    return {'path': str(OUT / name), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def main():
    started = datetime.now(UTC).isoformat()
    repos = discover()
    all_trees = {item['worktree']: item for repo in repos.values() for item in repo['worktrees']}
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        repo_futures = {executor.submit(inspect_repo, repo): common for common, repo in repos.items()}
        tree_futures = {executor.submit(inspect_tree, tree): path for path, tree in all_trees.items()}
        repo_results, tree_results, errors = {}, {}, list(DISCOVERY_ERRORS)
        for future, key in repo_futures.items():
            try:
                repo_results[key] = future.result()
            except Exception as error:
                errors.append({'repository': key, 'error_type': type(error).__name__, 'error': sanitize_error(str(error))})
        for future, key in tree_futures.items():
            try:
                tree_results[key] = future.result()
            except Exception as error:
                errors.append({'worktree': key, 'error_type': type(error).__name__, 'error': sanitize_error(str(error))})
    for repo in repo_results.values():
        repo['worktrees'] = [tree_results.get(tree['worktree'], {**tree, 'inventory_error': True}) for tree in repo['worktrees']]
    result = {'schema': 'autoformalization-readonly-git-publication-inventory/v1', 'started_utc': started,
              'finished_utc': datetime.now(UTC).isoformat(), 'repository_count': len(repos), 'worktree_count': len(all_trees),
              'repositories': list(repo_results.values()), 'errors': errors, 'auth_availability': auth_availability(),
              'git_optional_locks': '0', 'git_mutations_performed': False, 'fetch_performed': False,
              'explicit_working_tree_selected_from_existing_git_marker': True,
              'remote_refs_scope': 'cached_local_remote_tracking_refs_not_fetched',
              'discovery_scope': 'registered_worktrees_and_initialized_index_gitlinks_plus_direct_external_repositories_no_recursive_artifact_walk',
              'global_atomic_snapshot': False, 'inventory_files_created_after_status_sampling': True}
    binding = save_new('git_inventory.json', result)
    summary = {'inventory_binding': binding, 'repository_count': len(repos), 'worktree_count': len(all_trees),
               'error_count': len(errors), 'repository_summaries': []}
    for repo in repo_results.values():
        summary['repository_summaries'].append({'representative': repo['representative'], 'branches': repo['local_branch_count'],
            'branches_already_merged_into_cached_origin_main': sum(row.get('already_merged_into_cached_origin_main') is True for row in repo['local_branches']),
            'worktrees': len(repo['worktrees']), 'conflicted_worktrees': [tree['worktree'] for tree in repo['worktrees'] if tree.get('status', {}).get('conflict_count')],
            'active_operations': [{'worktree': tree['worktree'], 'operations': [key for key, value in tree.get('active_operations', {}).items() if value]} for tree in repo['worktrees'] if any(tree.get('active_operations', {}).values())],
            'large_tracked_blob_count': len(repo['tracked_blobs_at_least_10MiB'])})
    save_new('git_inventory_summary.json', summary)
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))


if __name__ == '__main__':
    main()
