"""Prepare a compact source/receipt candidate inventory using only reads.

No Git mutation, staging, classifier, codec, native or remote publication call
is present. Full omitted bodies remain in the separately qualified HF package.
"""
import collections
import datetime
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess

WORKSPACE = Path('/home/barberb/lift_coding')
ROOT = Path(__file__).resolve().parent
PRIOR_PREP = WORKSPACE / 'maintenance/ranker-curvature-private-git-preparation-20261005-01'
REPO = PRIOR_PREP / 'root'
ORIGINAL_STATE = PRIOR_PREP / 'original-checkout-state-01.json'
Q3 = WORKSPACE / 'qualification/codebase_ir/ranker-real-convergence-20261005-01'
P4 = WORKSPACE / 'qualification/codebase_ir/ranker-real-convergence-source-plan-20261005-01'
S2 = WORKSPACE / 'maintenance/ranker-convergence-publication-20261005-01'
PARENT = '769dc97d372ae2515b71d32a380d42de069c5d1d'
SEAL_SHA = '6ee7b5d675777e8cc9744c9072ee7f885cb8fc47a9204c1a40d9724632012648'
REVIEW_SHA = 'eebf40b5de2822faef1293a62578da208b582131e44c8a1f3e0d060071b6d0e7'
CLOSURE_SHA = '3721e16edddb301d9832001995fb9e685226cb9665852b31732bb148f8e7cdab'
ENV = dict(os.environ, GIT_OPTIONAL_LOCKS='0')
FILE_MAX = 16 * 1024**2


def need(value, message):
    if value is not True:
        raise ValueError(message)


def wire(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode()


def read(path):
    need(path.is_absolute() and path.resolve(strict=True) == path and not path.is_symlink(), 'canonical regular source required')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        need(stat.S_ISREG(before.st_mode) and before.st_size <= FILE_MAX, 'bounded regular source required')
        blocks, count = [], 0
        while block := os.read(fd, 1024**2):
            count += len(block)
            need(count <= FILE_MAX, 'source grew beyond bound')
            blocks.append(block)
        keys = ('st_dev', 'st_ino', 'st_mode', 'st_nlink', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
        signature = lambda info: tuple(getattr(info, key) for key in keys)
        need(signature(before) == signature(os.fstat(fd)) == signature(path.lstat()) and count == before.st_size, 'source changed during read')
        return b''.join(blocks)
    finally:
        os.close(fd)


def pin(path):
    raw = read(path)
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def git(*args, repo=REPO):
    return subprocess.check_output(['git', '-C', str(repo), *args], env=ENV)


def guards():
    original = json.loads(read(ORIGINAL_STATE))
    now = {}
    for name, old in original['original_checkouts'].items():
        raw = read(Path(old['index_path']))
        row = {'head': git('rev-parse', 'HEAD', repo=old['path']).decode().strip(), 'index_bytes': len(raw), 'index_sha256': hashlib.sha256(raw).hexdigest()}
        need(all(row[key] == old[key] for key in row), 'original root/child HEAD or index changed')
        now[name] = row
    links = []
    for line in git('ls-files', '--stage', repo=WORKSPACE).decode().splitlines():
        if line.startswith('160000 '):
            metadata, path = line.split('\t', 1)
            mode, oid, stage = metadata.split()
            links.append({'mode': mode, 'blob': oid, 'stage': int(stage), 'path': path})
    need(links == original['root_index_gitlinks'], 'original index Git links changed')
    return now


def omitted_reason(row):
    path = Path(row['path'])
    if path.is_relative_to(Q3):
        relative = path.relative_to(Q3)
        safe_metadata_receipts = {
            'evidence/metadata-convergence-01/metadata/manifest.json',
            'evidence/metadata-convergence-01/metadata/lake/history.json',
        }
        if relative.parts[:3] == ('evidence', 'metadata-convergence-01', 'metadata') and str(relative) not in safe_metadata_receipts:
            return 'native_metadata_payload_body'
    if path.name in ('environment-manifest.json', 'metadata-inputs.json'):
        return 'raw_environment_manifest_or_metadata_inputs'
    if path.suffix not in ('.py', '.lean', '.md', '.json', '.xml'):
        return 'binary_log_or_lock'
    if path.suffix == '.json' and row['bytes'] > 1024**2:
        return 'json_over_1MiB'
    return None


def main():
    before = guards()
    need(git('rev-parse', 'HEAD').decode().strip() == PARENT, 'private parent changed')
    need(git('status', '--porcelain=v1', '--untracked-files=all') == b'', 'reused private checkout must be clean')
    remote = git('ls-remote', 'origin', 'refs/heads/main').decode().strip().split()
    need(remote == [PARENT, 'refs/heads/main'], 'GitHub main advanced; preserve fresh parent before staging')
    seal_path = Q3 / 'file-only-seal-01.json'
    review_path = Q3 / 'qualified-review-01.json'
    seal_pin, review_pin, closure_pin = pin(seal_path), pin(review_path), pin(S2 / 'closed-inputs.json')
    need(seal_pin['sha256'] == SEAL_SHA and review_pin['sha256'] == REVIEW_SHA and closure_pin['sha256'] == CLOSURE_SHA, 'root final seal/review/closure pins differ')
    seal = json.loads(read(seal_path))
    need(seal['regular_file_count'] == len(seal['files']) == 378 and seal['regular_file_bytes'] == sum(row['bytes'] for row in seal['files']) == 147093916 and
        hashlib.sha256(wire(seal['files'])).hexdigest() == seal['file_inventory_sha256'] and seal['fixture_symlinks'] == [] and seal['excluded_dependency_roots'] == [], 'exact complete no-alias final Q3 census required')
    closure = json.loads(read(S2 / 'closed-inputs.json'))
    selection_pin = pin(S2 / 'final-selection.json')
    need(selection_pin == closure['final_selection'], 'frozen final selection pin differs')
    selection = json.loads(read(S2 / 'final-selection.json'))
    need(len(selection['files']) == 401 and sum(row['bytes'] for row in selection['files']) == 147838468 and selection['exclusions'] == [], 'complete frozen publication population differs')
    selected, omitted = [], []
    sealed_by_path = {row['path']: row for row in seal['files']}
    for row in selection['files']:
        path = Path(row['path'])
        need(path.is_relative_to(Q3) or path.is_relative_to(P4) or path.is_relative_to(S2), 'new owned selected source scope required')
        bound = {key: row[key] for key in ('path', 'bytes', 'sha256')}
        if str(path) in sealed_by_path:
            need(bound == sealed_by_path[str(path)], 'package selection changed a final sealed descriptor')
        reason = omitted_reason(bound)
        if reason:
            omitted.append({**bound, 'reason': reason})
        else:
            need(pin(path) == bound, 'compact source pin differs')
            selected.append({**bound, 'binding_origin': 'frozen_full_package_selection'})
    for name in ('plan.json', 'closed-inputs.json', 'final-selection.json'):
        path = S2 / name
        row = pin(path)
        need(omitted_reason(row) is None and str(path) not in {item['path'] for item in selected}, 'new safe final planning receipt required')
        selected.append({**row, 'binding_origin': 'externally_pinned_frozen_planning_receipt'})
    selected.sort(key=lambda row: os.fsencode(str(Path(row['path']).relative_to(WORKSPACE))))
    need(len(selected) == len({row['path'] for row in selected}), 'unique compact candidates required')
    parent_paths = set(git('ls-tree', '-r', '--name-only', PARENT).decode().splitlines())
    need(all(str(Path(row['path']).relative_to(WORKSPACE)) not in parent_paths for row in selected), 'all increment paths must be new in published parent')
    links = []
    for line in git('ls-tree', '-r', PARENT).decode().splitlines():
        if line.startswith('160000 '):
            metadata, path = line.split('\t', 1)
            mode, kind, oid = metadata.split()
            links.append({'path': path, 'mode': mode, 'oid': oid})
    need(len(links) == 9, 'fresh parent nine Git links required')
    after = guards()
    need(before == after, 'original checkouts changed during read-only preparation')
    result = {'schema': 'ranker-convergence-compact-private-git-candidate-selection@1', 'status': 'prepared_read_only_no_stage_commit_or_push',
        'created_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'producer': pin(Path(__file__).resolve()), 'parent': PARENT,
        'private_checkout': str(REPO), 'private_checkout_clean': True, 'reuse_private_checkout_recommended': True,
        'final_seal': seal_pin, 'qualified_review': review_pin, 'frozen_closed_inputs': closure_pin, 'frozen_full_selection': selection_pin,
        'selected_files': selected, 'selected_file_count': len(selected), 'selected_file_bytes': sum(row['bytes'] for row in selected),
        'omitted_full_package_files': omitted, 'omitted_file_count': len(omitted), 'omitted_file_bytes': sum(row['bytes'] for row in omitted),
        'omitted_reasons': dict(collections.Counter(row['reason'] for row in omitted)), 'full_omitted_bodies': 'retained in the separately frozen full HF increment; never omitted from its denominator',
        'parent_gitlinks': links, 'original_guard_before': before, 'original_guard_after': after, 'future_safe_package_HF_ledger_receipts_pending': True,
        'required_verified_HF_commit_before_stage_or_publish': True, 'raw_SDK_logs_excluded': True, 'native_classifier_codec_calls': 0,
        'Git_index_HEAD_or_ref_mutations': 0, 'stage_calls': 0, 'commit_calls': 0, 'push_calls': 0,
        'proof_authority': False, 'execution_authority': False, 'completion_authority': False, 'full_task_satisfaction': 'unknown'}
    target = ROOT / 'compact-candidate-selection-01.json'
    with target.open('xb') as stream:
        stream.write((json.dumps(result, sort_keys=True, indent=2, allow_nan=False)+'\n').encode())
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps({'status': result['status'], 'receipt': pin(target), 'selected_files': len(selected), 'selected_bytes': result['selected_file_bytes'],
        'omitted_files': len(omitted), 'omitted_bytes': result['omitted_file_bytes'], 'original_guards_unchanged': True, 'parent': PARENT}))


if __name__ == '__main__':
    main()
