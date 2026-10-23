"""SOURCE-ONLY: immutable historical qualification closure replay.

This is a file-integrity checkpoint, not a mathematical theorem or proof
admission service. The caller supplies an externally reviewed manifest pin.
Each replay reads all bodies afresh and performs the same physical censuses;
no historical helper executes, and no digest cache survives a replay phase.
Current native ownership, import admission and whole environment validation
remain independent requirements of the native qualification entry point.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import time

WORKSPACE = Path('/home/barberb/lift_coding')
AUTHORITY = {key: False for key in
             ('proof_authority', 'execution_authority', 'completion_authority', 'planner_activation')}
STAT_FIELDS = ('st_dev', 'st_ino', 'st_mode', 'st_nlink', 'st_size', 'st_mtime_ns', 'st_ctime_ns')


def need(value, message):
    if value is not True:
        raise ValueError(message)


def parse(raw):
    def unique(items):
        result = {}
        for key, value in items:
            need(key not in result, 'duplicate JSON field')
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=unique)


def wire(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=True, allow_nan=False).encode()


def exact(row, capture=False):
    need(type(row) is dict and set(row) == {'path', 'bytes', 'sha256'}
         and type(row['path']) is str and type(row['bytes']) is int and row['bytes'] >= 0
         and type(row['sha256']) is str and re.fullmatch('[0-9a-f]{64}', row['sha256']) is not None,
         'exact canonical descriptor required')
    path = Path(row['path'])
    need(path.is_absolute() and path.resolve(strict=True) == path and not path.is_symlink(),
         'canonical nonsymlink input required')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        need(stat.S_ISREG(before.st_mode) and before.st_nlink == 1
             and before.st_size == row['bytes'], 'exact unaliased regular body required')
        need(not capture or before.st_size <= 32 * 1024**2, 'parsed body exceeds fixed capture cap')
        signature = lambda info: tuple(getattr(info, key) for key in STAT_FIELDS)
        digest, total, blocks = hashlib.sha256(), 0, []
        while block := os.read(fd, 1024**2):
            total += len(block)
            need(total <= before.st_size, 'body grew during read')
            digest.update(block)
            if capture:
                blocks.append(block)
        need(signature(before) == signature(os.fstat(fd)) == signature(path.lstat())
             and path.resolve(strict=True) == path and not path.is_symlink()
             and total == row['bytes'] and digest.hexdigest() == row['sha256'],
             'same-buffer body/hash/stat changed')
    finally:
        os.close(fd)
    return b''.join(blocks)


def descriptors(value):
    if type(value) is dict:
        # Reviewed witness rows may append readback facts to their three-field
        # descriptor. Preserve the referenced body, not only bare pin records.
        if {'path', 'bytes', 'sha256'} <= set(value):
            yield {key: value[key] for key in ('path', 'bytes', 'sha256')}
        for child in value.values():
            yield from descriptors(child)
    elif type(value) is list:
        for child in value:
            yield from descriptors(child)


def add_rows(rows, additions):
    for row in additions:
        need(type(row) is dict and set(row) == {'path', 'bytes', 'sha256'}, 'closed descriptor required')
        need(row['path'] not in rows or rows[row['path']] == row, 'overlapping checkpoint body differs')
        rows[row['path']] = row


def checkout_guards(wanted):
    need(set(wanted) == {'root', 'child'}, 'fixed checkout guard roles required')
    actual = {}
    for role, cwd, index in (
        ('root', WORKSPACE, WORKSPACE / '.git/index'),
        ('child', WORKSPACE / 'external/ipfs_accelerate',
         WORKSPACE / '.git/modules/external/ipfs_accelerate/index'),
    ):
        need(set(wanted[role]) == {'head', 'index'} and wanted[role]['index']['path'] == str(index),
             'fixed original checkout/index path required')
        head = subprocess.check_output(
            ['git', '-c', 'core.fsmonitor=false', '-C', str(cwd), 'rev-parse', 'HEAD'],
            text=True, timeout=30).strip()
        exact(wanted[role]['index'])
        need(head == wanted[role]['head'], 'original checkout HEAD changed')
        actual[role] = {'head': head, 'index': wanted[role]['index']}
    return actual


def census(policy, seal):
    """Exact per-seal policies are themselves fixed in the reviewed manifest.

    The sole link/exclusion policy preserves the existing curvature fixture
    convention. The C05 copied foreign-scope seal is immutable forensic input
    only and is never treated as a scope or as admitted proof evidence.
    """
    need(set(policy) == {'seal', 'schema', 'scope_root', 'kind', 'file_count', 'file_bytes',
                         'inventory_sha256', 'fixture_symlinks', 'excluded_dependency_subtrees'},
         'closed reviewed physical policy required')
    need(seal['schema'] == policy['schema'] and seal['files']
         and len(seal['files']) == policy['file_count']
         and sum(row['bytes'] for row in seal['files']) == policy['file_bytes']
         and seal['file_inventory_sha256'] == policy['inventory_sha256']
         and hashlib.sha256(wire(seal['files'])).hexdigest() == policy['inventory_sha256'],
         'exact historical inventory metadata differs')
    root = Path(policy['scope_root'])
    paths = {row['path'] for row in seal['files']}
    need(len(paths) == policy['file_count'] and policy['seal']['path'] not in paths
         and all(Path(path).is_relative_to(root) for path in paths), 'unique confined inventory required')
    if policy['kind'] == 'forensic_foreign_scope_copy':
        need(policy['seal']['path'] == str(WORKSPACE / 'qualification/codebase_ir/'
             'ranker-objective-prefix-evaluation-candidate-20261006-05/file-only-seal-01.json')
             and policy['seal']['sha256'] == 'a6ca32c167c0cc444b3fde1b905fa83a36c7df70cbbe77f5afdcbc4a0d7dc641'
             and root == WORKSPACE / 'qualification/codebase_ir/ranker-objective-prefix-evaluation-candidate-20261006-03'
             and seal['scope_root'] == str(root) and policy['fixture_symlinks'] == []
             and policy['excluded_dependency_subtrees'] == [], 'only exact known skipped C05 forensic copy allowed')
        return
    need(policy['kind'] in ('regular_only', 'legacy_curvature_nofollow_fixtures'),
         'only closed audited physical schema policies allowed')
    need(root.resolve(strict=True) == root and not root.is_symlink() and root.is_dir()
         and Path(policy['seal']['path']).parent == root, 'canonical exact seal scope required')
    if 'scope_root' in seal:
        need(seal['scope_root'] == str(root), 'declared canonical seal root differs')
    if 'regular_file_count' in seal:
        need(seal['regular_file_count'] == policy['file_count'], 'historical regular count differs')
    elif 'file_count' in seal:
        need(seal['file_count'] == policy['file_count'], 'historical file count differs')
    if 'regular_file_bytes' in seal:
        need(seal['regular_file_bytes'] == policy['file_bytes'], 'historical regular bytes differ')
    if 'seal_self_excluded_from_files' in seal:
        need(seal['seal_self_excluded_from_files'] is True, 'seal must exclude its own body')
    links = policy['fixture_symlinks']
    excluded = policy['excluded_dependency_subtrees']
    if policy['kind'] == 'regular_only':
        need(links == excluded == [] and seal.get('fixture_symlinks', []) == []
             and seal.get('excluded_dependency_subtrees', []) == [], 'regular-only scope cannot relax census')
    else:
        need(policy['seal']['path'] == str(WORKSPACE / 'qualification/codebase_ir/'
             'ranker-real-curvature-20261005-01/file-only-seal-01.json')
             and policy['seal']['sha256'] == '6c281bd21da026b27797f78f98d0932bad4e7a115779a4fc348ee6987f30af15'
             and len(links) == 19 and policy['file_count'] == 1080
             and links == seal['fixture_symlinks'] and excluded == seal['excluded_dependency_subtrees']
             and excluded == [str(root / 'environment/mathlib4'), str(root / 'environment/cache')]
             and hashlib.sha256(wire(links)).hexdigest() == seal['fixture_symlink_inventory_sha256'],
             'only exact legacy curvature link/exclusion convention allowed')
    expected_links = {row['path']: row for row in links}
    need(len(expected_links) == len(links) and not paths.intersection(expected_links), 'disjoint exact links required')
    found_files, found_links, found_excluded = set(), set(), set()
    pending = [root]
    while pending:
        directory = pending.pop()
        with os.scandir(directory) as entries:
            for entry in entries:
                path = str(Path(entry.path))
                info = entry.stat(follow_symlinks=False)
                if path in excluded:
                    need(stat.S_ISDIR(info.st_mode), 'excluded dependency root changed type')
                    found_excluded.add(path)
                elif stat.S_ISLNK(info.st_mode):
                    need(path in expected_links, 'undeclared symlink in sealed scope')
                    row = expected_links[path]
                    target = os.readlink(path)
                    body = os.fsencode(target)
                    need(set(row) == {'path', 'bytes', 'sha256', 'stat', 'target'}
                         and target == row['target'] and len(body) == row['bytes']
                         and hashlib.sha256(body).hexdigest() == row['sha256']
                         and [getattr(info, key) for key in STAT_FIELDS] == row['stat']
                         and [getattr(os.lstat(path), key) for key in STAT_FIELDS] == row['stat'],
                         'exact nofollow fixture link body/stat differs')
                    found_links.add(path)
                elif stat.S_ISDIR(info.st_mode):
                    pending.append(Path(path))
                elif stat.S_ISREG(info.st_mode):
                    found_files.add(path)
                else:
                    raise ValueError('special file in sealed scope')
    need(found_files == paths | {policy['seal']['path']} and found_links == set(expected_links)
         and found_excluded == set(excluded), 'complete fresh sealed-scope census differs')


def replay(manifest_pin):
    started = time.monotonic()
    manifest = parse(exact(manifest_pin, True))
    need(set(manifest) == {'schema', 'accepted_request', 'accepted_guard_count', 'accepted_witness',
                          'inventory_policies', 'closure', 'closure_count', 'closure_sha256',
                          'original_checkout_guards', 'protected_live_sources', 'scope_count',
                          'physical_scope_count', 'independent_closure_review', *AUTHORITY}
         and manifest['schema'] == 'ranker-qualified-history-checkpoint@1'
         and all(manifest[key] is False for key in AUTHORITY), 'closed reviewed unprivileged checkpoint required')
    review = parse(exact(manifest['independent_closure_review'], True))
    need(review['status'] == 'passed_file_only' and review['findings'] == []
         and review['conditional_equivalence_review']['conditionally_safe'] is True
         and review['conditional_equivalence_review']['no_cap_widening'] is True
         and review['conditional_equivalence_review']['no_namespace_override'] is True
         and review['conditional_equivalence_review']['no_old_private_helper_execution_required'] is True
         and review['conditional_equivalence_review']['no_persistent_body_or_digest_cache'] is True
         and review['accepted_request'] == manifest['accepted_request']
         and review['actual_accepted_native_readback_witness'] == manifest['accepted_witness']
         and all(review[key] is False for key in AUTHORITY), 'independent complete closure audit required')
    before = checkout_guards(manifest['original_checkout_guards'])
    request = parse(exact(manifest['accepted_request'], True))
    witness = parse(exact(manifest['accepted_witness'], True))
    need(request['strict_guard_count'] == len(request['strict_old_inputs']) == manifest['accepted_guard_count'] == 3676
         and witness['status'] == 'passed_file_only' and witness['findings'] == []
         and request['original_checkout_guards'] == manifest['original_checkout_guards']
         and request['protected_live_sources'] == manifest['protected_live_sources']
         and all(request[key] is witness[key] is False for key in AUTHORITY),
         'exact accepted request/readback/checkout/context checkpoint required')
    rows = {}
    add_rows(rows, [manifest['accepted_request'], manifest['accepted_witness']])
    add_rows(rows, request['strict_old_inputs'])
    add_rows(rows, descriptors(request))
    add_rows(rows, descriptors(witness))
    policies = manifest['inventory_policies']
    need(len(policies) == manifest['scope_count'] == 48
         and len({p['seal']['path'] for p in policies}) == 48
         and len(review['inventory_policies']) == 48
         and sum(p['kind'] != 'forensic_foreign_scope_copy' for p in policies)
             == manifest['physical_scope_count'] == 47, 'complete fixed inventory population required')
    for policy in policies:
        audited = next(p for p in review['inventory_policies'] if p['descriptor'] == policy['seal'])
        if policy['kind'] == 'forensic_foreign_scope_copy':
            need(audited['policy'] == 'literal_foreign_scope_forensic_file_only'
                 and audited['schema'] == policy['schema']
                 and audited['declared_scope_root'] == policy['scope_root']
                 and audited['native_or_source_admission'] is False,
                 'copied scope stays exact unadmitted forensic data')
        else:
            need(audited['schema'] == policy['schema']
                 and audited['scope_root'] == policy['scope_root']
                 and audited['regular_file_count'] == policy['file_count']
                 and audited['regular_file_bytes'] == policy['file_bytes']
                 and audited['file_inventory_sha256'] == policy['inventory_sha256']
                 and audited['fixture_symlink_count'] == len(policy['fixture_symlinks'])
                 and audited['excluded_dependency_subtrees'] == policy['excluded_dependency_subtrees'],
                 'physical census policy must match the independent inventory audit')
        seal = parse(exact(policy['seal'], True))
        census(policy, seal)
        add_rows(rows, [policy['seal'], *seal['files']])
    forensic = review['forensic_skipped_source_copy']
    need(forensic['copied_seal_not_a_closure_or_admission'] is True
         and len(forensic['files']) == 5 and forensic['physical_five_file_population_verified'] is True,
         'preserved skipped-source forensic body population required')
    add_rows(rows, [forensic['receipt'], *forensic['files']])
    basis = [rows[path] for path in sorted(rows)]
    need(len(basis) == review['expanded_checkpoint_basis_count'] == 3919
         and hashlib.sha256(wire(basis)).hexdigest() == review['expanded_checkpoint_basis_sha256'],
         'entire historical predicate-input basis must match independent closure audit')
    add_rows(rows, [manifest['independent_closure_review']])
    wanted = [rows[path] for path in sorted(rows)]
    need(wanted == manifest['closure'] and len(wanted) == manifest['closure_count']
         and hashlib.sha256(wire(wanted)).hexdigest() == manifest['closure_sha256'],
         'complete rederived historical predicate-input closure differs')
    for row in wanted:
        exact(row)
    need(checkout_guards(manifest['original_checkout_guards']) == before, 'checkout changed during checkpoint replay')
    return {'schema': 'ranker-qualified-history-checkpoint-replay@1', 'status': 'passed_file_only',
            'manifest': manifest_pin, 'closure_count': len(wanted),
            'scope_count': len(policies), 'physical_scope_count': manifest['physical_scope_count'],
            'closure_sha256': manifest['closure_sha256'], 'original_checkout_guards': before,
            'protected_live_source_count': len(manifest['protected_live_sources']),
            'elapsed_seconds': time.monotonic() - started, 'historical_helpers_executed': 0,
            'native_jobs': 0, 'test_cases': 0, 'model_jobs': 0, 'metadata_jobs': 0,
            'digest_cache_used': False, **AUTHORITY}
