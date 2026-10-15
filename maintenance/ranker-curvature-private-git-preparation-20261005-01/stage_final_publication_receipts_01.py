"""Stage eleven approved HF receipts and scan the complete private Git increment."""
import datetime
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import tempfile
import types

WORKSPACE = Path('/home/barberb/lift_coding')
ROOT = Path(__file__).resolve().parent
REPO = ROOT / 'root'
ENV = dict(os.environ, GIT_OPTIONAL_LOCKS='0')
EXTRA_STAGE_SHA = '89a053746fd8cde145d59f7320bc672e0c3b361902b11f66d1c490c1c842833d'
PUBLICATION = WORKSPACE / 'maintenance/ranker-curvature-publication-root-20261005-01'
FINAL = [
    'review_hf_readback_01.py', 'hf-public-readback-01.json',
    'release-publication-ledger-01.json', 'hf-publication-invocation-01.json',
    'hf-publication-outer-01/closed.json', 'hf-publication-01/started.json',
    'hf-publication-01/remote-before.json', 'hf-publication-01/commit-observed.json',
    'hf-publication-01/verified-files.json', 'hf-publication-01/closed.json',
    'package-review-outer-01/closed.json',
]
KNOWN = {
    'hf-public-readback-01.json': (3373, '0987396d5e3e1c51d3ac7e09f672e86c740b4fe11099905e9d42013a1dd57ccd'),
    'release-publication-ledger-01.json': (6400, 'f8c1b5d511974bac4fa655c157bd2244e2cccc555801a2ed31145000c964ae15'),
    'hf-publication-invocation-01.json': (433397, '87a9346a639adbe7734617e9dd09e64264a2a47aee85b17738210f2750d4773c'),
}
HF = WORKSPACE / 'maintenance/terminal-ir-publication-20261004-01/huggingface'
HELPERS = {
    'archive': (HF / 'build_evidence_archive_02.py', 'f72c1ea8efb3d04a67eca31af333d73b2079fd9cfbcfd7439580f87d56e53036'),
    'classifier': (HF / 'classify_and_prepare_public_archive_07.py', 'dd457cb927270f53617781de1f576d1de1fac76b86191d769f4f923fa966a1f8'),
}


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


def load_helper(name):
    path, expected = HELPERS[name]
    need(pin(path)['sha256'] == expected, 'credential classifier helper changed')
    module = types.ModuleType('held_private_git_scan_' + name)
    module.__file__ = str(path)
    exec(compile(read(path), str(path), 'exec'), module.__dict__)
    return module


def write_new(path, value):
    with path.open('xb') as stream:
        stream.write((json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode())
        stream.flush()
        os.fsync(stream.fileno())
    return pin(path)


def main():
    old_path = ROOT / 'extra-stage-closed-01.json'
    need(pin(old_path)['sha256'] == EXTRA_STAGE_SHA, 'extra-stage pin changed')
    old = json.loads(read(old_path))
    before = guards()
    parent = old['parent']
    need(git('rev-parse', 'HEAD').decode().strip() == parent, 'private parent changed')
    need(git('ls-remote', 'origin', 'refs/heads/main').decode().strip().split() == [parent, 'refs/heads/main'], 'remote main advanced')
    paths = [row['path'] for row in old['staged_source_blobs']]
    wire = git('diff', '--cached', '--name-status', '-z').split(b'\0')
    need([(wire[i].decode(), os.fsdecode(wire[i + 1])) for i in range(0, len(wire) - 1, 2)] == [('A', path) for path in paths], 'baseline staged additions changed')
    final = []
    for name in sorted(FINAL):
        source = PUBLICATION / name
        row = pin(source)
        if name in KNOWN:
            need((row['bytes'], row['sha256']) == KNOWN[name], 'root-provided final receipt pin changed')
        relative = str(source.relative_to(WORKSPACE))
        need(relative not in paths and source.suffix in ('.json', '.py'), 'new public source or JSON receipt required')
        final.append({**row, 'relative_path': relative})
    readback = json.loads(read(PUBLICATION / 'hf-public-readback-01.json'))
    ledger = json.loads(read(PUBLICATION / 'release-publication-ledger-01.json'))
    closed = json.loads(read(PUBLICATION / 'hf-publication-01/closed.json'))
    need(readback['status'] == 'passed' and readback['selected_files'] == 47 and readback['prior_immutable_files_preserved'] == 180 and readback['committed_total_regular_files'] == 227, 'HF readback qualification differs')
    need(ledger['huggingface']['commit'] == readback['commit'] == closed['commit'] == '8b7b8c896749e0ca3884114cedbed782a88f4702' and closed['status'] == 'PUBLISHED_AND_VERIFIED', 'HF commit joins differ')
    selection_pin = write_new(ROOT / 'final-receipt-selection-01.json', {'schema': 'ranker-curvature-final-private-git-receipts@1', 'parent': parent, 'files': final, 'file_count': len(final), 'file_bytes': sum(row['bytes'] for row in final), 'hf_commit': readback['commit'], 'raw_SDK_logs_excluded': True})
    for row in final:
        source = Path(row['path'])
        target = REPO / row['relative_path']
        need(not target.exists() and not target.is_symlink(), 'new private path required')
        target.parent.mkdir(parents=True, exist_ok=True)
        need(target.parent.resolve(strict=True) == target.parent, 'canonical private parent required')
        with target.open('xb') as stream:
            stream.write(read(source))
        target.chmod(0o644)
        need(pin(target)['sha256'] == row['sha256'], 'final private copy differs')
    git('-c', 'core.autocrlf=false', 'add', '--pathspec-from-file=-', '--pathspec-file-nul', input=b''.join(os.fsencode(row['relative_path']) + b'\0' for row in final))
    all_paths = sorted(paths + [row['relative_path'] for row in final])
    wire = git('diff', '--cached', '--name-status', '-z').split(b'\0')
    need([(wire[i].decode(), os.fsdecode(wire[i + 1])) for i in range(0, len(wire) - 1, 2)] == [('A', path) for path in all_paths], 'only exact combined new additions allowed')
    index = {}
    links = []
    for line in git('ls-files', '--stage').decode().splitlines():
        metadata, path = line.split('\t', 1)
        mode, oid, stage = metadata.split()
        need(stage == '0', 'unmerged index refused')
        index[path] = (mode, oid)
        if mode == '160000':
            links.append({'path': path, 'mode': mode, 'oid': oid})
    need(links == old['parent_gitlinks'], 'all nine parent Git links required')
    expected_rows = {row['path']: row for row in old['staged_source_blobs']}
    expected_rows.update({row['relative_path']: row for row in final})
    archive = load_helper('archive')
    classifier = load_helper('classifier')
    scanner = archive.Scanner()
    scanner.patterns = [(name, pattern) for name, pattern in archive.PATTERNS if name != 'private_key_pem']
    budget = classifier.Budget(seconds=120, decoded_bytes=16*1024**2, container_bytes=16*1024**2, members=1, depth=0)
    stream = io.BytesIO(git('cat-file', '--batch', input=''.join(index[path][1] + '\n' for path in all_paths).encode()))
    staged = []
    with tempfile.TemporaryDirectory(prefix='private-git-text-scan-', dir=ROOT) as temporary:
        for path in all_paths:
            oid, kind, size = stream.readline().decode().strip().split()
            raw = stream.read(int(size))
            need(stream.read(1) == b'\n' and kind == 'blob' and oid == index[path][1] and index[path][0] == '100644', 'regular staged blob required')
            row = {'path': path, 'mode': '100644', 'git_blob_oid': oid, 'bytes': int(size), 'sha256': hashlib.sha256(raw).hexdigest()}
            need(all(row[key] == expected_rows[path][key] for key in ('bytes', 'sha256')), 'staged blob pin differs')
            need(classifier.Classifier.format(raw[:512]) is None, 'all Git additions must be non-container text')
            inspection = classifier.Classifier(scanner, budget, Path(temporary))
            inspection.inspect(io.BytesIO(raw))
            need(not inspection.hits, 'final new Git text rejected by pinned credential classifier')
            need(pin(WORKSPACE / path)['sha256'] == row['sha256'], 'final source pin changed')
            need(pin(REPO / path)['sha256'] == row['sha256'], 'private working copy changed')
            staged.append(row)
    need(stream.read() == b'', 'unexpected blob readback tail')
    budget.check()
    need(budget.decoded == 0 and budget.members == 0, 'no codec/container jobs authorized for Git text review')
    for path, expected_sha in HELPERS.values():
        need(pin(path)['sha256'] == expected_sha, 'scanner helper changed during review')
    after = guards()
    need(before == after, 'original checkouts changed')
    tree = git('write-tree').decode().strip()
    result = {'schema': 'ranker-curvature-final-private-git-stage@1', 'status': 'passed_complete_increment_HF_verified_ready_to_commit', 'created_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'producer': pin(Path(__file__).resolve()), 'prior_stage': pin(old_path), 'final_receipt_selection': selection_pin, 'parent': parent, 'tree': tree, 'hf_commit': readback['commit'], 'staged_source_blobs': staged, 'staged_file_count': len(staged), 'staged_file_bytes': sum(row['bytes'] for row in staged), 'parent_gitlinks': links, 'all_nine_parent_gitlinks_unchanged': True, 'all_new_staged_text_scanned': True, 'credential_candidate_hits': 0, 'bounded_complete_PEM_and_cached_credential_veto': True, 'raw_SDK_logs_excluded': True, 'raw_archives_caches_private_worktrees_excluded': True, 'original_guard_before': before, 'original_guard_after': after, 'native_model_solver_test_fit_codec_jobs': 0, 'classifier_helpers': {name: pin(path) for name, (path, _) in HELPERS.items()}, 'project_imports': 0, 'stage_calls': 1, 'commit_calls': 0, 'push_calls': 0, 'proof_authority': False, 'execution_authority': False, 'completion_authority': False}
    result_pin = write_new(ROOT / 'final-stage-closed-01.json', result)
    print(json.dumps({'status': result['status'], 'receipt': result_pin, 'staged_files': len(staged), 'staged_bytes': result['staged_file_bytes'], 'tree': tree, 'candidate_hits': 0}))


if __name__ == '__main__':
    main()
