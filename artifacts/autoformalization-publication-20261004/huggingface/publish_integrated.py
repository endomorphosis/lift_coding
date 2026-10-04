"""Verify externally selected integrated tips and publish ordinary main updates.

No force/delete push, reset, checkout, merge or working-tree edits are used.
Normal origin fetch updates its local tracking cache. Operation receipts remain
available on rejection, including attempted pushes with uncertain outcomes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import signal
import stat
import subprocess
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from urllib.parse import urljoin

MAX_JSON = 64 * 1024 ** 2
MAX_BLOB = 100 * 1024 ** 2
OID = re.compile(r'[0-9a-f]{40}')


def require(value, message):
    if not value:
        raise ValueError(message)


def raw(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def selected_json(path, expected):
    path = Path(path).absolute()
    require(all(not p.is_symlink() for p in (path, *path.parents)), 'nonsymlink selected JSON required')
    with path.open('rb') as stream:
        before = os.fstat(stream.fileno())
        require(stat.S_ISREG(before.st_mode) and 0 < before.st_size <= MAX_JSON, 'bounded ordinary JSON required')
        data = stream.read(MAX_JSON + 1)
        after = os.fstat(stream.fileno())
    require((before.st_ino, before.st_size, before.st_mtime_ns) ==
            (after.st_ino, after.st_size, after.st_mtime_ns), 'selected JSON changed during read')
    require(hashlib.sha256(data).hexdigest() == expected, 'external selected JSON file SHA differs')

    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'duplicate JSON key')
            result[key] = value
        return result

    value = json.loads(data.decode('utf-8'), object_pairs_hook=pairs,
                       parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite JSON')))
    require(type(value) is dict, 'selected JSON object required')
    return value, {'path': str(path), 'bytes': len(data), 'sha256': expected}


def normalized_origin(value):
    value = value.strip().removesuffix('/').removesuffix('.git')
    for prefix in ('https://', 'http://', 'ssh://git@', 'git@'):
        if value.startswith(prefix):
            value = value[len(prefix):]
            break
    return value.replace('github.com:', 'github.com/')


def safe_path(value):
    require(type(value) is str and value and '\0' not in value, 'ordinary relative Git path required')
    parsed = PurePosixPath(value)
    require(not parsed.is_absolute() and '..' not in parsed.parts and str(parsed) == value, 'canonical relative Git path required')
    return value


def sealed_save(path, value):
    value = dict(value)
    value['content_sha256'] = hashlib.sha256(raw(value)).hexdigest()
    data = raw(value) + b'\n'
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, 'wb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    return {'path': str(path), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


class GitOperations:
    def __init__(self, directory):
        self.path = directory / 'operations.jsonl'
        self.fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        self.count = 0
        self.push_attempted = False

    def close(self):
        os.close(self.fd)

    def run(self, repo, args, *, accepted=(0,), timeout=180, limit=64 * 1024 ** 2,
            input_data=None, hash_only=False):
        command = ['git', '-c', 'gc.auto=0', '-C', str(repo), *args]
        if args and args[0] == 'push':
            self.push_attempted = True
        start = time.monotonic()
        process = None
        timed_out = False
        exceeded = False
        error = None
        with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr, tempfile.TemporaryFile() as stdin:
            try:
                if input_data is not None:
                    require(len(input_data) <= 64 * 1024 ** 2, 'Git operation input bound exceeded')
                    stdin.write(input_data)
                    stdin.seek(0)
                process = subprocess.Popen(command, stdin=stdin if input_data is not None else subprocess.DEVNULL,
                    stdout=stdout, stderr=stderr, start_new_session=True,
                    env={**os.environ, 'GIT_TERMINAL_PROMPT': '0', 'GIT_MERGE_AUTOEDIT': 'no'})
                while process.poll() is None:
                    timed_out = time.monotonic() - start > timeout
                    exceeded = os.fstat(stdout.fileno()).st_size > limit or os.fstat(stderr.fileno()).st_size > 8 * 1024 ** 2
                    if timed_out or exceeded:
                        break
                    time.sleep(.05)
            except Exception as exc:
                error = type(exc).__name__
            finally:
                cleanup_error = None
                if process is not None and process.poll() is None:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    except Exception as exc:
                        cleanup_error = type(exc).__name__
                    try:
                        process.wait(timeout=5)
                    except Exception as exc:
                        cleanup_error = type(exc).__name__
                sizes = {'stdout': os.fstat(stdout.fileno()).st_size, 'stderr': os.fstat(stderr.fileno()).st_size}
                hashes = {}
                hashed_bytes = {}
                for name, stream in [('stdout', stdout), ('stderr', stderr)]:
                    stream.seek(0)
                    digest = hashlib.sha256()
                    remaining = min(sizes[name], limit if name == 'stdout' else 8 * 1024 ** 2)
                    hashed_bytes[name] = remaining
                    while remaining:
                        data = stream.read(min(128 * 1024, remaining))
                        if not data:
                            break
                        digest.update(data)
                        remaining -= len(data)
                    hashes[name] = digest.hexdigest()
                record = {'index': self.count, 'command': command, 'returncode': process.returncode if process else None,
                          'wall_seconds': time.monotonic() - start, 'timed_out': timed_out,
                          'output_limit_exceeded': exceeded, 'launch_or_poll_error': error,
                          'cleanup_error': cleanup_error, 'output_bytes': sizes, 'output_sha256': hashes,
                          'hashed_output_bytes': hashed_bytes,
                          'output_hash_truncated': {name: hashed_bytes[name] != sizes[name] for name in sizes},
                          'output_bodies_retained': False}
                os.write(self.fd, raw(record) + b'\n')
                os.fsync(self.fd)
                self.count += 1
            require(not error and not cleanup_error and not timed_out and not exceeded, 'Git operation launch/resource/cleanup failure recorded')
            require(process.returncode in accepted, f'Git operation failed with exit {process.returncode}; inspect operation hashes and status')
            require(sizes['stdout'] <= limit and sizes['stderr'] <= 8 * 1024 ** 2, 'Git operation output bound exceeded')
            if hash_only:
                return {'sha256': hashes['stdout'], 'bytes': sizes['stdout'], 'returncode': process.returncode}
            stdout.seek(0)
            return stdout.read(limit + 1), process.returncode

    def text(self, repo, args):
        return self.run(repo, args)[0].decode('utf-8', 'strict').strip()


def committed_tree(ops, repo, tip):
    entries = {}
    for line in ops.run(repo, ['ls-tree', '-r', '-z', tip])[0].split(b'\0'):
        if not line:
            continue
        properties, path = line.split(b'\t', 1)
        mode, kind, oid = properties.decode().split()
        name = path.decode('utf-8', 'surrogateescape')
        entries[name] = {'mode': mode, 'kind': kind, 'oid': oid}
    return entries


def check_prepared(ops, plan, prepared):
    require(prepared.get('schema') == 'worktree-main-integration-prepublication/v1', 'prepared report schema differs')
    require(prepared.get('eligible_for_root_prepublication_review') is True and prepared.get('python_syntax_errors') == [], 'prepared syntax qualification failed')
    require(prepared.get('origin_push_executed') is False, 'prepared report already claims a push')
    canonical = Path(plan['canonical_repository']).resolve(strict=True)
    repo = Path(plan['fresh_worktree']).resolve(strict=True)
    origin = plan['normalized_origin']
    require(re.fullmatch(r'github\.com/endomorphosis/[A-Za-z0-9_.-]+', origin), 'explicit owned GitHub origin required')
    require(normalized_origin(ops.text(canonical, ['remote', 'get-url', 'origin'])) == origin, 'canonical origin differs')
    require(normalized_origin(ops.text(repo, ['remote', 'get-url', 'origin'])) == origin, 'integration origin differs')
    require(Path(prepared['canonical_repository']).resolve() == canonical and Path(prepared['fresh_worktree']).resolve() == repo
            and prepared['normalized_origin'] == origin, 'prepared repository selection differs')
    require(Path(ops.text(repo, ['rev-parse', '--show-toplevel'])).resolve() == repo, 'selected integration root differs')
    require(ops.text(repo, ['symbolic-ref', '--short', 'HEAD']) == plan['integration_branch'], 'prepared integration branch differs')
    tip = prepared['integrated_tip']
    require(type(tip) is str and OID.fullmatch(tip), 'exact Git tip OID required')
    require(ops.text(repo, ['rev-parse', 'HEAD']) == tip, 'selected prepared tip advanced')
    require(not ops.text(repo, ['status', '--porcelain', '--untracked-files=normal']), 'integration worktree is not clean')
    baseline = plan['origin_main_sha256_or_git_oid']
    require(OID.fullmatch(baseline) and prepared['baseline_origin_main'] == baseline, 'baseline identity differs')
    require(prepared.get('baseline_remote_ref', 'origin/main') == plan.get('baseline_remote_ref', 'origin/main'), 'baseline reference differs')
    for head in plan['heads']:
        require(OID.fullmatch(head['oid']), 'selected ancestor OID required')
        ops.run(repo, ['merge-base', '--is-ancestor', head['oid'], tip])
    require(prepared['selected_head_count'] == len(plan['heads']), 'prepared head count differs')
    source = plan.get('authoritative_source', {})
    if source:
        require(OID.fullmatch(source['snapshot_commit']), 'authoritative snapshot commit required')
        ops.run(repo, ['merge-base', '--is-ancestor', source['snapshot_commit'], tip])
    return repo, origin, tip, baseline, committed_tree(ops, repo, tip)


def check_source_pins(ops, repo, tree, plan):
    checks = []
    cached = {}
    for selected in plan.get('authoritative_source', {}).get('selected_files', []):
        name = safe_path(selected['path'])
        entry = tree.get(name)
        if selected['state'] in {'absent', 'deleted'}:
            require(entry is None and not any(p.startswith(name + '/') for p in tree), 'deleted authoritative Git path remains')
            checks.append({'path': name, 'state': 'absent'})
            continue
        require(entry is not None and entry['kind'] == 'blob' and entry['mode'] == selected['mode'], 'committed source mode/type differs')
        if entry['oid'] not in cached:
            cached[entry['oid']] = ops.run(repo, ['cat-file', 'blob', entry['oid']], hash_only=True, limit=1024 ** 3)
        actual = cached[entry['oid']]
        require(actual['sha256'] == selected['sha256'], 'committed source blob SHA differs')
        if 'bytes' in selected:
            require(actual['bytes'] == selected['bytes'], 'committed source blob size differs')
        checks.append({'path': name, **entry, 'sha256': actual['sha256'], 'bytes': actual['bytes']})
    return checks


def remote_heads(ops, repo):
    result = {}
    for row in ops.text(repo, ['ls-remote', '--heads', 'origin']).splitlines():
        oid, ref = row.split('\t', 1)
        require(OID.fullmatch(oid) and ref.startswith('refs/heads/'), 'remote branch declaration malformed')
        result[ref] = oid
    return result


def check_remote_baseline(plan, baseline, heads):
    main = heads.get('refs/heads/main')
    if main is None:
        require(plan.get('baseline_remote_ref', 'origin/main') == 'origin/master'
                and heads.get('refs/heads/master') == baseline, 'absent main requires exact selected master baseline')
    else:
        require(plan.get('baseline_remote_ref', 'origin/main') == 'origin/main' and main == baseline,
                'remote main advanced; prepare a new integration plan')
    return main


def committed_submodule_origins(ops, repo, tip, origin):
    _, exists = ops.run(repo, ['cat-file', '-e', f'{tip}:.gitmodules'], accepted=(0, 1, 128))
    if exists:
        return {}
    data, _ = ops.run(repo, ['config', '--blob', f'{tip}:.gitmodules', '--null', '--get-regexp',
                            r'^submodule\..*\.(path|url)$'])
    groups = {}
    for row in data.split(b'\0'):
        if not row:
            continue
        key, value = row.decode('utf-8', 'strict').split('\n', 1)
        group, field = key.rsplit('.', 1)
        require(field not in groups.setdefault(group, {}), 'duplicate submodule declaration field')
        groups[group][field] = value
    result = {}
    for declaration in groups.values():
        require(set(declaration) == {'path', 'url'}, 'complete committed submodule declaration required')
        path = safe_path(declaration['path'])
        value = declaration['url']
        if value.startswith(('./', '../')):
            value = urljoin(f'https://{origin}/', value)
        require(path not in result, 'duplicate committed submodule path')
        result[path] = normalized_origin(value)
    return result


def new_blob_sizes(ops, repo, tip):
    # Preserve stale local refs, but exclude objects only through live remote heads.
    ops.run(repo, ['fetch', '--no-tags', '--no-prune', '--recurse-submodules=no', '--no-auto-maintenance',
                   'origin', '+refs/heads/*:refs/remotes/origin/*'])
    cached_refs = {}
    for row in ops.text(repo, ['for-each-ref', '--format=%(refname) %(objectname)', 'refs/remotes/origin/']).splitlines():
        name, oid = row.split(' ', 1)
        if name == 'refs/remotes/origin/HEAD':
            continue
        require(OID.fullmatch(oid), 'origin tracking OID malformed')
        cached_refs[name] = oid
    live = remote_heads(ops, repo)
    refs = {}
    for name, oid in live.items():
        tracking = 'refs/remotes/origin/' + name.removeprefix('refs/heads/')
        require(cached_refs.get(tracking) == oid, 'remote branches advanced after fetch; select a new preflight')
        refs[tracking] = oid
    require(refs, 'current live fetched origin branch references required')
    raw_objects = ops.run(repo, ['rev-list', '--objects', '--no-object-names', tip, '--not', *sorted(set(refs.values()))])[0]
    objects = raw_objects.decode().splitlines()
    require(all(OID.fullmatch(oid) for oid in objects), 'new object enumeration malformed')
    # --batch-check receives only hash IDs, never path or revision expressions.
    data, _ = ops.run(repo, ['cat-file', '--batch-check=%(objectname) %(objecttype) %(objectsize)'],
                      input_data=('\n'.join(objects) + ('\n' if objects else '')).encode())
    parsed = []
    for row in data.decode().splitlines():
        oid, kind, size = row.split()
        require(OID.fullmatch(oid) and size.isdecimal(), 'object-size response malformed')
        parsed.append((oid, kind, int(size)))
    require([p[0] for p in parsed] == objects, 'complete new-object size joins required')
    oversized = [{'oid': oid, 'bytes': size} for oid, kind, size in parsed if kind == 'blob' and size > MAX_BLOB]
    return {'tracking_refs': refs, 'live_remote_heads': live,
            'excluded_stale_tracking_ref_count': len(set(cached_refs) - set(refs)),
            'exclusion_scope': 'live_remote_heads_exactly_joined_to_fetched_tracking_refs',
            'fetch_scope': 'non_recursive_no_auto_maintenance_no_pruning', 'new_object_count': len(parsed),
            'new_blob_count': sum(kind == 'blob' for _, kind, _ in parsed),
            'maximum_new_blob_bytes': max((size for _, kind, size in parsed if kind == 'blob'), default=0),
            'blob_limit_bytes': MAX_BLOB, 'oversized_new_blobs': oversized}


def publish(args):
    output = args.output.absolute()
    require(not output.exists() and all(not p.is_symlink() for p in output.parents), 'fresh nonsymlink output directory required')
    output.mkdir(parents=True, mode=0o700)
    ops = GitOperations(output)
    report = {'schema': 'git-integrated-main-publication/v1', 'created_utc': datetime.now(UTC).isoformat(),
              'status': 'failed_before_verified_publication', 'push_attempted': False, 'remote_publication_verified': False,
              'force_push_used': False, 'remote_refs_deleted': False, 'working_tree_mutated': False,
              'model_calls_by_publisher': 0, 'training_executed_by_publisher': False,
              'local_git_hooks_disabled': False}
    try:
        plan, plan_binding = selected_json(args.plan, args.plan_sha)
        prepared, prepared_binding = selected_json(args.prepared, args.prepared_sha)
        report.update({'plan_binding': plan_binding, 'prepared_binding': prepared_binding})
        repo, origin, tip, baseline, tree = check_prepared(ops, plan, prepared)
        report.update({'canonical_repository': plan['canonical_repository'], 'fresh_worktree': str(repo),
                       'normalized_origin': origin, 'integrated_tip': tip, 'baseline_oid': baseline})
        proposed = plan.get('published_gitlinks', [])
        require(prepared.get('published_gitlinks', []) == proposed, 'prepared gitlink proposal differs')
        selected_receipts = {safe_path(path): (file, sha) for path, file, sha in args.published_gitlink}
        require(len(selected_receipts) == len(args.published_gitlink) and set(selected_receipts) == {safe_path(p['path']) for p in proposed},
                'each proposed gitlink needs an independent publication receipt selection')
        gitlinks = []
        submodule_origins = committed_submodule_origins(ops, repo, tip, origin) if proposed else {}
        for item in proposed:
            path = safe_path(item['path'])
            file, sha = selected_receipts[path]
            receipt, binding = selected_json(file, sha)
            require(receipt.get('schema') == 'git-integrated-main-publication/v1'
                    and receipt.get('status') == 'published_and_verified'
                    and receipt.get('remote_publication_verified') is True
                    and receipt.get('integrated_tip') == receipt.get('remote_main_after') == item['oid'], 'gitlink publication evidence differs')
            require(submodule_origins.get(path) == receipt.get('normalized_origin'), 'gitlink receipt origin differs from committed .gitmodules')
            require(tree.get(path) == {'mode': '160000', 'kind': 'commit', 'oid': item['oid']}, 'committed gitlink differs')
            gitlinks.append({'path': path, 'oid': item['oid'], 'publication_receipt': binding,
                             'normalized_origin': receipt['normalized_origin']})
        report['gitlink_checks'] = gitlinks
        sizes = new_blob_sizes(ops, repo, tip)
        report['newly_reachable_object_preflight'] = sizes
        # Persist the evidence even when a large historical branch blob blocks main.
        preflight = sealed_save(output / 'blob-preflight.json', sizes)
        report['blob_preflight_binding'] = preflight
        require(not sizes['oversized_new_blobs'], 'newly reachable blob exceeds GitHub 100MiB boundary')
        report['authoritative_source_checks'] = check_source_pins(ops, repo, tree, plan)
        before = remote_heads(ops, repo)
        main = check_remote_baseline(plan, baseline, before)
        ops.run(repo, ['merge-base', '--is-ancestor', baseline, tip])
        report['remote_main_before'] = main
        for binding in [plan_binding, prepared_binding, *[item['publication_receipt'] for item in gitlinks]]:
            selected_json(binding['path'], binding['sha256'])
        require(ops.text(repo, ['rev-parse', 'HEAD']) == tip and ops.text(repo, ['symbolic-ref', '--short', 'HEAD']) == plan['integration_branch'],
                'prepared branch moved before push')
        require(normalized_origin(ops.text(repo, ['remote', 'get-url', 'origin'])) == origin, 'selected push origin changed')
        # Ordinary Git performs the remote fast-forward check. No lease/force/delete option is used.
        ops.run(repo, ['push', '--porcelain', 'origin', f'{tip}:refs/heads/main'], timeout=300)
        after = remote_heads(ops, repo)
        report['remote_main_after'] = after.get('refs/heads/main')
        require(report['remote_main_after'] == tip, 'remote main does not match selected committed tip after push')
        report.update({'status': 'published_and_verified', 'remote_publication_verified': True,
                       'selected_heads_ancestor_checks_completed': len(plan['heads']),
                       'url': f'https://{origin}/commit/{tip}',
                       'preservation_scope': 'selected_committed_source_bytes_modes_and_reachable_selected_history',
                       'concurrent_remote_advance_transaction_guarantee': False})
    except Exception as error:
        report['error_type'] = type(error).__name__
        report['error'] = str(error)
    finally:
        report['push_attempted'] = ops.push_attempted
        report['git_operation_count'] = ops.count
        ops.close()
        data = ops.path.read_bytes()
        report['operation_journal'] = {'path': str(ops.path), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
        selected_source = Path(__file__).resolve()
        report['publisher_source'] = {'path': str(selected_source), 'bytes': selected_source.stat().st_size,
                                      'sha256': hashlib.sha256(selected_source.read_bytes()).hexdigest()}
        result = sealed_save(output / 'publication.json', report)
        print(json.dumps({'publication': result, 'status': report['status'], 'push_attempted': report['push_attempted']}, sort_keys=True), flush=True)
    return 0 if report['remote_publication_verified'] else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--plan-sha', required=True)
    parser.add_argument('--prepared', type=Path, required=True)
    parser.add_argument('--prepared-sha', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--published-gitlink', nargs=3, action='append', default=[], metavar=('PATH', 'RECEIPT', 'SHA256'))
    raise SystemExit(publish(parser.parse_args()))
