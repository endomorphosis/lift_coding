"""Prepare verified published child Gitlinks without changing source blobs.

Input receipts and previous generations remain immutable. This helper commits
only mode-160000 paths in the selected private worktree, keeps normal Git hooks,
and creates no push or training authorization. Its publication evidence joins
are independently repeated by the selected publisher before any push.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path, PurePosixPath
from urllib.parse import urljoin

OID = re.compile(r'[0-9a-f]{40}')
SHA = re.compile(r'[0-9a-f]{64}')
MAX_JSON = 64 * 1024 * 1024


def require(condition, message):
    if not condition:
        raise ValueError(message)


def raw(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()


def binding(path):
    path = Path(path).absolute()
    require(path.is_file() and not path.is_symlink(), 'regular selected metadata file required')
    data = path.read_bytes()
    require(0 < len(data) <= MAX_JSON, 'bounded metadata input required')
    return {'path': str(path), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def selected(path, digest):
    require(type(digest) is str and SHA.fullmatch(digest), 'exact externally selected SHA256 required')
    pin = binding(path)
    require(pin['sha256'] == digest, 'selected metadata bytes differ')
    value = json.loads(Path(path).read_bytes())
    require(type(value) is dict, 'ordinary metadata object required')
    if 'content_sha256' in value:
        require(value['content_sha256'] == hashlib.sha256(raw({k: v for k, v in value.items()
                if k != 'content_sha256'})).hexdigest(), 'selected metadata content seal differs')
    return value, pin


def pinned(pin):
    require(type(pin) is dict and set(pin) == {'path', 'bytes', 'sha256'}, 'closed file binding required')
    value, observed = selected(pin['path'], pin['sha256'])
    require(observed == pin, 'selected file binding differs')
    return value


def save(path, value):
    value = {k: v for k, v in value.items() if k != 'content_sha256'}
    value['content_sha256'] = hashlib.sha256(raw(value)).hexdigest()
    with Path(path).open('xb') as stream:
        os.chmod(path, 0o600)
        stream.write(raw(value) + b'\n')
        stream.flush()
        os.fsync(stream.fileno())
    return binding(path)


def git(repo, *args, data=None, accepted=(0,)):
    result = subprocess.run(['git', '-c', 'gc.auto=0', '-c', 'maintenance.auto=false',
                             '-c', 'submodule.recurse=false', '-C', str(repo), *args],
                            input=data, capture_output=True, timeout=180,
                            env={**os.environ, 'GIT_TERMINAL_PROMPT': '0', 'GIT_MERGE_AUTOEDIT': 'no'})
    require(result.returncode in accepted,
            'private Git operation failed: ' + result.stderr.decode('utf-8', 'replace')[-3000:])
    return result


def text(repo, *args):
    return git(repo, *args).stdout.decode().strip()


def tree(repo, commit):
    result = {}
    for record in git(repo, 'ls-tree', '-r', '-z', commit).stdout.split(b'\0'):
        if record:
            metadata, path = record.split(b'\t', 1)
            mode, kind, oid = metadata.decode().split()
            result[os.fsdecode(path)] = {'mode': mode, 'kind': kind, 'oid': oid}
    return result


def safe_path(value):
    require(type(value) is str and value and not any(c in value for c in ('\0', '\n', '\r', '\t')),
            'ordinary Gitlink path required')
    path = PurePosixPath(value)
    require(not path.is_absolute() and str(path) == value and not set(path.parts) & {'.', '..', '.git'},
            'normalized relative Gitlink path required')
    return value


def origin(value):
    value = value.strip().removesuffix('.git').removesuffix('/')
    for prefix in ('https://', 'http://', 'ssh://git@', 'git@'):
        if value.startswith(prefix):
            value = value[len(prefix):]
            break
    return value.replace('github.com:', 'github.com/')


def submodule_origins(repo, commit, parent_origin):
    groups = {}
    for record in git(repo, 'config', '--blob', commit + ':.gitmodules', '--null', '--get-regexp',
                      r'^submodule\..*\.(path|url)$').stdout.split(b'\0'):
        if not record:
            continue
        key, value = record.decode().split('\n', 1)
        group, field = key.rsplit('.', 1)
        require(field not in groups.setdefault(group, {}), 'duplicate submodule field')
        groups[group][field] = value
    result = {}
    for row in groups.values():
        require(set(row) == {'path', 'url'}, 'complete committed submodule declaration required')
        name, url = safe_path(row['path']), row['url']
        require(name not in result, 'duplicate submodule path')
        if url.startswith(('./', '../')):
            url = urljoin('https://' + parent_origin + '/', url)
        result[name] = origin(url)
    return result


def original_index(repo):
    path = Path(text(repo, 'rev-parse', '--git-path', 'index'))
    return binding(path if path.is_absolute() else repo / path)


def check_canonical(repo, current, plan, proposals):
    selection = plan['authoritative_full_tree_snapshot']
    manifest = pinned(selection['manifest_binding'])
    canonical = tree(repo, selection['snapshot_commit'])
    if manifest['schema'] == 'converted-canonical-snapshot-blob-pins/v1':
        require(manifest['mapped_snapshot_commit'] == selection['snapshot_commit'], 'mapped snapshot differs')
        original = pinned(manifest['original_manifest_binding'])
    else:
        require(manifest['schema'] == 'complete-canonical-snapshot-blob-pins/v1', 'selected complete snapshot profile required')
        original = manifest
    for name, row in canonical.items():
        wanted = {'mode': '160000', 'kind': 'commit', 'oid': proposals[name]} if name in proposals else row
        require(name not in proposals or row['mode'] == '160000', 'Gitlink override cannot replace canonical source')
        require(current.get(name) == wanted, 'complete canonical source differs: ' + name)
    for row in original['authoritative_source']['selected_files']:
        if row['state'] == 'deleted':
            name = row['path']
            require(name not in current and not any(path.startswith(name + '/') for path in current),
                    'intentional source/payload omission differs')
    return len([row for row in canonical.values() if row['kind'] == 'blob'])


def update(args):
    plan, plan_pin = selected(args.plan, args.plan_sha)
    prepared, prepared_pin = selected(args.prepared, args.prepared_sha)
    require(prepared['plan_binding'] == plan_pin, 'previous prepared selection differs')
    repo = Path(plan['fresh_worktree']).absolute()
    original = Path(plan['canonical_repository']).absolute()
    require(repo != original and repo == Path(prepared['fresh_worktree']).absolute(), 'selected private worktree required')
    require(text(repo, 'symbolic-ref', '--short', 'HEAD') == plan['integration_branch'], 'selected private branch differs')
    before = text(repo, 'rev-parse', 'HEAD')
    require(before == prepared['integrated_tip'], 'selected candidate advanced')
    require(origin(text(repo, 'remote', 'get-url', 'origin')) == plan['normalized_origin']
            and plan['normalized_origin'].startswith('github.com/endomorphosis/'), 'owned candidate origin required')
    git(repo, 'diff', '--cached', '--quiet')
    git(repo, 'diff', '--quiet', '--ignore-submodules=all')
    original_head, original_index_pin = text(original, 'rev-parse', 'HEAD'), original_index(original)
    before_tree = tree(repo, before)
    canonical_tree = tree(repo, plan['authoritative_full_tree_snapshot']['snapshot_commit'])
    prior_proposals = {safe_path(row['path']): row['oid'] for row in plan.get('published_gitlinks', [])}
    blob_count = check_canonical(repo, before_tree, plan, prior_proposals)
    committed_origins = submodule_origins(repo, before, plan['normalized_origin'])
    proposals, checks = {}, []
    for name, receipt_path, receipt_sha in args.published_gitlink:
        name = safe_path(name)
        require(name not in proposals, 'duplicate selected child Gitlink')
        receipt, pin = selected(receipt_path, receipt_sha)
        oid = receipt.get('integrated_tip')
        require(receipt.get('schema') == 'git-integrated-main-publication/v1'
                and receipt.get('status') == 'published_and_verified'
                and receipt.get('remote_publication_verified') is True
                and type(oid) is str and OID.fullmatch(oid) and receipt.get('remote_main_after') == oid,
                'verified child publication receipt required')
        require(canonical_tree.get(name, {}).get('mode') == '160000'
                and before_tree.get(name, {}).get('mode') == '160000'
                and committed_origins.get(name) == receipt.get('normalized_origin'),
                'child origin or canonical Gitlink differs')
        proposals[name] = oid
        checks.append({'path': name, 'oid': oid, 'publication_receipt': pin,
                       'normalized_origin': receipt['normalized_origin']})
    require(set(prior_proposals) <= set(proposals), 'every previous override needs renewed exact receipt selection')
    args.output.mkdir(mode=0o700, parents=True, exist_ok=False)
    save(args.output / 'start.json', {'schema': 'published-child-gitlink-preparation-start/v1',
        'prior_plan_binding': plan_pin, 'prior_prepared_binding': prepared_pin,
        'private_worktree': str(repo), 'before_tip': before, 'selected_children': checks,
        'origin_push_executed': False, 'training_executed': False})
    changes = [name for name, oid in proposals.items() if before_tree[name]['oid'] != oid]
    if changes:
        git(repo, 'update-index', '-z', '--index-info', data=b''.join(b'160000 ' + proposals[name].encode()
            + b'\t' + os.fsencode(name) + b'\0' for name in changes))
        staged = {os.fsdecode(name) for name in git(repo, 'diff', '--cached', '--name-only', '-z').stdout.split(b'\0') if name}
        require(staged == set(changes), 'ordinary staged source changed during Gitlink selection')
        git(repo, 'commit', '-m', 'Record independently verified published child source commits')
    tip = text(repo, 'rev-parse', 'HEAD')
    final = tree(repo, tip)
    expected = {**before_tree, **{name: {'mode': '160000', 'kind': 'commit', 'oid': oid}
                                 for name, oid in proposals.items()}}
    require(final == expected, 'child update or hook changed unrelated committed source')
    git(repo, 'diff', '--quiet', '--ignore-submodules=all')
    git(repo, 'diff', '--cached', '--quiet')
    require(check_canonical(repo, final, plan, proposals) == blob_count, 'canonical blob count changed')
    for oid in {before, plan['authoritative_full_tree_snapshot']['snapshot_commit'],
                *[row['oid'] for row in plan['heads']]}:
        git(repo, 'merge-base', '--is-ancestor', oid, tip)
    require(text(original, 'rev-parse', 'HEAD') == original_head and original_index(original) == original_index_pin,
            'original checkout HEAD or index changed')
    for pin in (plan_pin, prepared_pin, *[row['publication_receipt'] for row in checks]):
        require(binding(pin['path']) == pin, 'selected metadata bytes changed during preparation')
    proposed = [{'path': name, 'oid': oid} for name, oid in sorted(proposals.items())]
    plan.update(published_gitlinks=proposed, restored_prepared_tip=tip)
    plan_new = save(args.output / 'plan.json', plan)
    prepared.update(integrated_tip=tip, published_gitlinks=proposed, plan_binding=plan_new,
                    published_child_update_prior_plan_binding=plan_pin,
                    published_child_update_prior_prepared_binding=prepared_pin,
                    published_child_update_prior_tip=before, published_child_update_prior_tip_ancestor=True,
                    published_child_update_only_mode160000_paths=True,
                    published_child_publication_checks=checks,
                    published_child_update_source_blob_modes_and_oids_preserved=True,
                    published_child_update_original_HEAD_and_index_preserved=True,
                    published_child_update_hooks_disabled=False,
                    origin_push_executed=False, training_executed=False)
    prepared_new = save(args.output / 'prepared.json', prepared)
    result = {'schema': 'published-child-gitlink-preparation/v1', 'tip': tip,
              'plan_binding': plan_new, 'prepared_binding': prepared_new, 'selected_children': checks,
              'changed_gitlinks': changes, 'canonical_blob_paths_preserved': blob_count,
              'all_previous_selected_heads_ancestors': True, 'ordinary_committed_paths_changed': [],
              'original_HEAD_and_index_preserved': True, 'local_git_hooks_disabled': False,
              'origin_push_executed': False, 'training_executed': False}
    save(args.output / 'preparation.json', result)
    print(json.dumps(result), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('plan', 'prepared', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    for name in ('plan-sha', 'prepared-sha'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--published-gitlink', nargs=3, action='append', default=[],
                        metavar=('PATH', 'RECEIPT', 'SHA256'))
    args = parser.parse_args()
    os.umask(0o077)
    try:
        update(args)
    except Exception as error:
        if args.output.is_dir() and not (args.output / 'failure.json').exists():
            save(args.output / 'failure.json', {'schema': 'published-child-gitlink-preparation-failure/v1',
                'error_type': type(error).__name__, 'message': str(error), 'origin_push_executed': False,
                'training_executed': False, 'private_partial_state_retained': True})
        raise


if __name__ == '__main__':
    main()
