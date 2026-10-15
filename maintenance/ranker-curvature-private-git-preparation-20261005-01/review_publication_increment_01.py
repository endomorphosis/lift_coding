"""Recheck the compact private index and approved publication receipt candidates.

This performs file hashing and Git reads only. It does not import project code,
run native tools or codecs, stage, commit, push, or alter sealed inputs.
"""
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
ENV = dict(os.environ, GIT_OPTIONAL_LOCKS='0')
PARENT = '73e98e1a839086b26b30533e4d72a9306f1306a0'
EXTRAS = [
    'maintenance/ranker-curvature-publication-source-plan-20261005-01/closed-inputs.json',
    'maintenance/ranker-curvature-publication-source-plan-20261005-01/final-selection.json',
    'maintenance/ranker-curvature-publication-input-review-20261005-01/review_inputs.py',
    'maintenance/ranker-curvature-publication-input-review-20261005-01/plan-review-01.json',
    'maintenance/ranker-curvature-publication-input-review-20261005-01/selection-review-01.json',
    'maintenance/ranker-curvature-publication-package-20261005-01/package/manifest.json',
    'maintenance/ranker-curvature-publication-package-20261005-01/closed.json',
    'maintenance/ranker-curvature-publication-package-20261005-01/package-review-01.json',
    'maintenance/ranker-curvature-publication-root-20261005-01/hf-plan-01.json',
    'maintenance/ranker-curvature-publication-root-20261005-01/scan_final_upload.py',
    'maintenance/ranker-curvature-publication-root-20261005-01/final-upload-scan-01.json',
    'maintenance/ranker-curvature-publication-root-20261005-01/package-outer-01/closed.json',
]


def need(value, message):
    if value is not True:
        raise ValueError(message)


def read(path):
    need(path.is_absolute() and path.resolve(strict=True) == path and not path.is_symlink(), 'canonical regular source required')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        need(stat.S_ISREG(before.st_mode) and before.st_size <= 16 * 1024**2, 'bounded regular source required')
        raw = b''
        while block := os.read(fd, 1024**2):
            raw += block
            need(len(raw) <= 16 * 1024**2, 'source grew beyond bound')
        keys = ('st_dev', 'st_ino', 'st_mode', 'st_nlink', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
        signature = lambda value: tuple(getattr(value, key) for key in keys)
        need(signature(before) == signature(os.fstat(fd)) == signature(path.lstat()) and len(raw) == before.st_size, 'source changed during read')
        return raw
    finally:
        os.close(fd)


def pin(path):
    raw = read(path)
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def git(*args, repo=REPO, input=None):
    return subprocess.check_output(['git', '-C', str(repo), *args], input=input, env=ENV)


def guards():
    original = json.loads(read(ROOT / 'original-checkout-state-01.json'))
    result = {}
    for name, old in original['original_checkouts'].items():
        raw = read(Path(old['index_path']))
        current = {'head': git('rev-parse', 'HEAD', repo=old['path']).decode().strip(), 'index_bytes': len(raw), 'index_sha256': hashlib.sha256(raw).hexdigest()}
        need(all(current[key] == old[key] for key in current), 'original HEAD or index changed')
        result[name] = current
    links = []
    for row in git('ls-files', '--stage', repo=WORKSPACE).decode().splitlines():
        if row.startswith('160000 '):
            metadata, path = row.split('\t', 1)
            mode, oid, stage = metadata.split()
            links.append({'mode': mode, 'blob': oid, 'stage': int(stage), 'path': path})
    need(links == original['root_index_gitlinks'], 'original Git links changed')
    return result


def main():
    before = guards()
    compact = json.loads(read(ROOT / 'compact-selection-01.json'))
    closed_path = ROOT / 'compact-stage-closed-01.json'
    closed = json.loads(read(closed_path))
    need(pin(ROOT / 'compact-selection-01.json') == closed['selection'], 'compact selection receipt changed')
    need(pin(Path(compact['final_seal']['path'])) == compact['final_seal'], 'sealed qualification changed')
    need(git('rev-parse', 'HEAD').decode().strip() == PARENT == compact['parent'] == closed['parent'], 'private parent changed')
    remote = git('ls-remote', 'origin', 'refs/heads/main').decode().strip().split()
    need(remote == [PARENT, 'refs/heads/main'], 'remote main advanced; preserve concurrent work before publishing')
    changes = git('diff', '--cached', '--name-status', '-z').split(b'\0')
    need(changes[-1] == b'', 'invalid staged changes')
    actual = [(changes[i].decode(), os.fsdecode(changes[i + 1])) for i in range(0, len(changes) - 1, 2)]
    paths = [str(Path(row['path']).relative_to(WORKSPACE)) for row in compact['selected_files']]
    need(actual == [('A', path) for path in paths], 'private staged changes differ from exact compact additions')
    index = {}
    links = []
    for row in git('ls-files', '--stage').decode().splitlines():
        metadata, path = row.split('\t', 1)
        mode, oid, stage = metadata.split()
        need(stage == '0', 'unmerged private index')
        index[path] = (mode, oid)
        if mode == '160000':
            links.append({'path': path, 'mode': mode, 'oid': oid})
    need(links == closed['parent_gitlinks'], 'parent Git links changed')
    stream = io.BytesIO(git('cat-file', '--batch', input=''.join(index[path][1] + '\n' for path in paths).encode()))
    verified = []
    for path, source, original_blob in zip(paths, compact['selected_files'], closed['staged_source_blobs']):
        need(index[path][0] == '100644', 'staged source mode changed')
        oid, kind, size = stream.readline().decode().strip().split()
        raw = stream.read(int(size))
        need(stream.read(1) == b'\n' and kind == 'blob' and oid == index[path][1], 'invalid staged blob')
        actual_blob = {'path': path, 'mode': '100644', 'git_blob_oid': oid, 'bytes': int(size), 'sha256': hashlib.sha256(raw).hexdigest()}
        need(actual_blob == original_blob, 'staged blob changed')
        need(pin(WORKSPACE / path) == {key: source[key] for key in ('path', 'bytes', 'sha256')}, 'source pin changed')
        need(pin(REPO / path)['sha256'] == source['sha256'], 'private working copy changed')
        verified.append(actual_blob)
    need(stream.read() == b'', 'unexpected blob tail')
    candidates = []
    for relative in sorted(EXTRAS):
        path = WORKSPACE / relative
        need(relative not in index and not (REPO / relative).exists(), 'extra candidate must be new')
        need(path.suffix in ('.json', '.py') and not path.name.endswith(('stdout.log', 'stderr.log')), 'public source or receipt required')
        candidates.append({**pin(path), 'relative_path': relative})
    after = guards()
    need(before == after, 'original checkouts changed during review')
    result = {
        'schema': 'ranker-curvature-private-git-prepublication-review@1',
        'status': 'passed_read_only_originals_preserved',
        'created_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'producer': pin(Path(__file__).resolve()),
        'parent': PARENT,
        'remote_main': PARENT,
        'compact_selection': pin(ROOT / 'compact-selection-01.json'),
        'compact_stage_closed': pin(closed_path),
        'staged_file_count': len(verified),
        'staged_file_bytes': sum(row['bytes'] for row in verified),
        'all_staged_source_pins_and_blobs_reverified': True,
        'parent_gitlinks': links,
        'all_nine_parent_gitlinks_unchanged': True,
        'extra_candidates': candidates,
        'extra_candidate_file_count': len(candidates),
        'extra_candidate_file_bytes': sum(row['bytes'] for row in candidates),
        'original_guard_before': before,
        'original_guard_after': after,
        'sealed_qualification_or_source_plan_mutations': 0,
        'native_model_solver_test_fit_codec_jobs': 0,
        'stage_calls': 0,
        'commit_calls': 0,
        'push_calls': 0,
        'project_imports': 0,
    }
    target = ROOT / 'prepublication-review-01.json'
    with target.open('xb') as handle:
        handle.write((json.dumps(result, sort_keys=True, indent=2, allow_nan=False) + '\n').encode())
    print(json.dumps({'status': result['status'], 'receipt': pin(target), 'staged_files': len(verified), 'staged_bytes': result['staged_file_bytes'], 'extra_files': len(candidates), 'extra_bytes': result['extra_candidate_file_bytes']}))


if __name__ == '__main__':
    main()
