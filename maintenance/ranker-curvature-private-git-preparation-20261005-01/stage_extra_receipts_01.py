"""Add only the twelve reviewed source and publication receipts to private Git."""
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
REVIEW_SHA = '8efb546b20108415ef669a0b08858fec70649f5baeaa8d94206e2e6b2a502c1e'


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
    return subprocess.check_output(['git', '-C', str(repo), *args], input=input, env=ENV)


def guards():
    original = json.loads(read(ROOT / 'original-checkout-state-01.json'))
    result = {}
    for name, old in original['original_checkouts'].items():
        raw = read(Path(old['index_path']))
        current = {'head': git('rev-parse', 'HEAD', repo=old['path']).decode().strip(), 'index_bytes': len(raw), 'index_sha256': hashlib.sha256(raw).hexdigest()}
        need(all(current[key] == old[key] for key in current), 'original HEAD or index changed')
        result[name] = current
    return result


def main():
    review_path = ROOT / 'prepublication-review-01.json'
    need(pin(review_path)['sha256'] == REVIEW_SHA, 'review pin changed')
    review = json.loads(read(review_path))
    previous = json.loads(read(ROOT / 'compact-stage-closed-01.json'))
    before = guards()
    parent = review['parent']
    need(git('rev-parse', 'HEAD').decode().strip() == parent, 'private parent changed')
    need(git('ls-remote', 'origin', 'refs/heads/main').decode().strip().split() == [parent, 'refs/heads/main'], 'remote main advanced')
    originals = previous['staged_source_blobs']
    extras = review['extra_candidates']
    paths = [row['path'] for row in originals]
    expected = [('A', path) for path in paths]
    wire = git('diff', '--cached', '--name-status', '-z').split(b'\0')
    need([(wire[i].decode(), os.fsdecode(wire[i + 1])) for i in range(0, len(wire) - 1, 2)] == expected, 'baseline staging changed')
    need(len(extras) == 12 and sum(row['bytes'] for row in extras) == 1601877, 'candidate inventory changed')
    for row in extras:
        source = Path(row['path'])
        need(pin(source) == {key: row[key] for key in ('path', 'bytes', 'sha256')}, 'approved source pin changed')
        relative = source.relative_to(WORKSPACE)
        need(str(relative) == row['relative_path'] and relative.parts[0] == 'maintenance' and source.suffix in ('.json', '.py'), 'extra owned public receipt required')
        target = REPO / relative
        need(not target.exists() and not target.is_symlink(), 'extra must be a new parent path')
        target.parent.mkdir(parents=True, exist_ok=True)
        need(target.parent.resolve(strict=True) == target.parent, 'canonical private parent required')
        with target.open('xb') as stream:
            stream.write(read(source))
        target.chmod(0o644)
        need(pin(target)['sha256'] == row['sha256'], 'private copy differs')
    extra_paths = [row['relative_path'] for row in extras]
    git('-c', 'core.autocrlf=false', 'add', '--pathspec-from-file=-', '--pathspec-file-nul', input=b''.join(os.fsencode(path) + b'\0' for path in extra_paths))
    all_expected = sorted(paths + extra_paths)
    wire = git('diff', '--cached', '--name-status', '-z').split(b'\0')
    need([(wire[i].decode(), os.fsdecode(wire[i + 1])) for i in range(0, len(wire) - 1, 2)] == [('A', path) for path in all_expected], 'exact combined additions required')
    index = {}
    links = []
    for row in git('ls-files', '--stage').decode().splitlines():
        metadata, path = row.split('\t', 1)
        mode, oid, stage = metadata.split()
        need(stage == '0', 'unmerged index refused')
        index[path] = (mode, oid)
        if mode == '160000':
            links.append({'path': path, 'mode': mode, 'oid': oid})
    need(links == previous['parent_gitlinks'], 'all nine parent Git links must remain unchanged')
    expected_rows = {row['path']: row for row in originals}
    expected_rows.update({row['relative_path']: row for row in extras})
    stream = io.BytesIO(git('cat-file', '--batch', input=''.join(index[path][1] + '\n' for path in all_expected).encode()))
    staged = []
    for path in all_expected:
        oid, kind, size = stream.readline().decode().strip().split()
        raw = stream.read(int(size))
        need(stream.read(1) == b'\n' and kind == 'blob' and oid == index[path][1] and index[path][0] == '100644', 'regular staged blob required')
        row = {'path': path, 'mode': '100644', 'git_blob_oid': oid, 'bytes': int(size), 'sha256': hashlib.sha256(raw).hexdigest()}
        need(all(row[key] == expected_rows[path][key] for key in ('bytes', 'sha256')), 'staged pin differs')
        staged.append(row)
    need(stream.read() == b'', 'unexpected readback tail')
    for row in extras:
        need(pin(Path(row['path'])) == {key: row[key] for key in ('path', 'bytes', 'sha256')}, 'extra source changed during staging')
    after = guards()
    need(before == after, 'original checkouts changed')
    result = {'schema': 'ranker-curvature-private-git-extra-stage@1', 'status': 'passed_exact_new_receipt_additions_no_commit_or_push', 'created_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'producer': pin(Path(__file__).resolve()), 'review': pin(review_path), 'parent': parent, 'extra_files': extras, 'staged_source_blobs': staged, 'staged_file_count': len(staged), 'staged_file_bytes': sum(row['bytes'] for row in staged), 'parent_gitlinks': links, 'all_nine_parent_gitlinks_unchanged': True, 'original_guard_before': before, 'original_guard_after': after, 'publication_ledger_additions_pending': True, 'native_model_solver_test_fit_codec_jobs': 0, 'project_imports': 0, 'stage_calls': 1, 'commit_calls': 0, 'push_calls': 0}
    target = ROOT / 'extra-stage-closed-01.json'
    with target.open('xb') as handle:
        handle.write((json.dumps(result, sort_keys=True, indent=2, allow_nan=False) + '\n').encode())
    print(json.dumps({'status': result['status'], 'receipt': pin(target), 'staged_files': len(staged), 'staged_bytes': result['staged_file_bytes']}))


if __name__ == '__main__':
    main()
