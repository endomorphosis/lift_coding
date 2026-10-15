"""Stage exactly authorized compact additions in an isolated private checkout.

No commit, push, solver, codec, model, test, native prover or dependency import.
"""
import collections
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
QUALIFIER = WORKSPACE / 'qualification/codebase_ir/ranker-real-curvature-20261005-01'
TOOLING = WORKSPACE / 'maintenance/ranker-curvature-publication-source-plan-20261005-01'
SOURCE_REVIEW = WORKSPACE / 'maintenance/ranker-curvature-publication-source-review-20261005-01'
SEAL_SHA = '6c281bd21da026b27797f78f98d0932bad4e7a115779a4fc348ee6987f30af15'
REVIEW_SHA = '2c98df30a37fecffff99340d447dcf548c6c244a53223cbed39c914bb0e9238c'
PARENT = '73e98e1a839086b26b30533e4d72a9306f1306a0'
MAINTENANCE_PINS = {
    'build_package.py': '4e14c08fc6d680e5fcbf755f649284f750353b73b42dd08b926398f4c43c9a93',
    'review_package.py': 'cdb6dbea925e3bc3ae8d62c6b7c069bfcbe1fd79bf07282e32ed06a68daf88f9',
    'freeze_inputs.py': '830d457108a95a8ccd29ee8a75af9742bc749336df1e87dabccaf8327aa2c041',
    'build_package-v1.py': '39901e6427019ea17f9a3cbbc12889e8319945b2f0431775e573fad52f2d52c9',
    'review_package-v1.py': '50e3635f9b9b1d2d86ca7d323aa000d40843bae789f5ab8215189ae3c2bbc5eb',
    'freeze_inputs-v1.py': '904e13e8651f06c06e8511d45f6d2dd2c5b192322a71561c7bfb93029ea349c1',
    'API.md': '3e66da5ea15246cb27cfefe79514cd533e14342b763614446cc6c9cacf0039ca',
    'publication-profile-authorization.json': '3b0c8fd91ccd62fdc65e2cf557da6175eb6e48aef8b95996315113ff534bc638',
    'publication-profile-authorization-v1.json': '4561cf1aedb6c98e29f70110013f2f4ef7923e6ae20dde6aa452c3c2d21e9160',
    'plan.json': '80c269c217d867be827060d50fc86cf272b53e9607c397d54055effcb20783a7',
    'required-facts.json': '50deb4972264d45a543de861d9c51e72b9862d10c5ce7664810e3f3e277aeecf',
    'prepare_final_plan.py': 'aca580441a45c89080c34229c35981f328af631db0b0cedaa85dd67ba4c19b26',
}
REVIEW_PINS = {
    'review_source_01.py': '06937f20a178fc583bab170ca9f716e14f2d13964ac505592d8f03a61d6cd898',
    'source-review-01.json': '20b0de9eb6f118bc418ccc4ffb478ca56b2f99023afb063d08f11d21b3502b14',
}
ENV = dict(os.environ, GIT_OPTIONAL_LOCKS='0')


def need(condition, message):
    if condition is not True:
        raise ValueError(message)


def read(path):
    need(path.is_absolute() and path.resolve(strict=True) == path and not path.is_symlink(), 'canonical source required')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        need(stat.S_ISREG(before.st_mode) and before.st_size <= 16 * 1024**2, 'bounded regular source required')
        blocks, count = [], 0
        while block := os.read(fd, 1024**2):
            count += len(block)
            need(count <= 16 * 1024**2, 'source grew beyond bound')
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


def git(*args, repo=REPO, input=None):
    return subprocess.check_output(['git', '-C', str(repo), *args], env=ENV, input=input)


def original_guards():
    original = json.loads(read(ROOT / 'original-checkout-state-01.json'))
    now = {}
    for name, old in original['original_checkouts'].items():
        raw = read(Path(old['index_path']))
        row = {'head': git('rev-parse', 'HEAD', repo=old['path']).decode().strip(),
               'index_bytes': len(raw), 'index_sha256': hashlib.sha256(raw).hexdigest()}
        need(all(row[key] == old[key] for key in row), 'original HEAD or raw index changed')
        now[name] = row
    links = []
    for row in git('ls-files', '--stage', repo=WORKSPACE).decode().splitlines():
        if row.startswith('160000 '):
            before, path = row.split('\t', 1)
            mode, blob, stage = before.split()
            links.append({'mode': mode, 'blob': blob, 'stage': int(stage), 'path': path})
    need(links == original['root_index_gitlinks'], 'original gitlinks changed')
    return now


def parent_gitlinks():
    result = []
    for row in git('ls-tree', '-r', 'HEAD').decode().splitlines():
        if row.startswith('160000 '):
            before, path = row.split('\t', 1)
            mode, kind, oid = before.split()
            result.append({'path': path, 'mode': mode, 'oid': oid})
    need(len(result) == 9, 'fresh parent nine gitlinks required')
    return result


def omit_reason(row):
    relative = Path(row['path']).relative_to(QUALIFIER)
    if relative.parts[0] == 'evidence' and 'fixtures' in relative.parts:
        return 'test_fixture_body'
    if relative.parts[:3] == ('evidence', 'metadata-01', 'metadata') and relative.name != 'manifest.json':
        return 'native_metadata_body'
    if relative.name in ('environment-manifest.json', 'metadata-inputs.json'):
        return 'environment_manifest_or_metadata_inputs'
    if relative.suffix not in ('.py', '.lean', '.md', '.json', '.xml'):
        return 'binary_log_or_lock'
    if relative.suffix == '.json' and row['bytes'] > 1024**2:
        return 'json_over1MiB'
    return None


def write_new(path, value):
    with path.open('xb') as stream:
        stream.write((json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode())
        stream.flush()
        os.fsync(stream.fileno())
    return pin(path)


def main():
    closed_path = ROOT / 'compact-stage-closed-01.json'
    selection_path = ROOT / 'compact-selection-01.json'
    need(not closed_path.exists() and not selection_path.exists(), 'fresh private stage receipts required')
    guard_before = original_guards()
    need(git('rev-parse', 'HEAD').decode().strip() == PARENT == git('rev-parse', 'origin/main').decode().strip(), 'fresh parent changed; refresh and preserve concurrency first')
    need(git('status', '--porcelain=v1', '--untracked-files=all') == b'', 'private checkout must initially be clean')
    parent_links = parent_gitlinks()
    seal_path = QUALIFIER / 'file-only-seal-01.json'
    seal_pin = pin(seal_path)
    need(seal_pin['sha256'] == SEAL_SHA, 'actual final seal pin differs')
    seal = json.loads(read(seal_path))
    need(seal['schema'] == 'ranker-real-curvature-file-only-seal@1' and len(seal['files']) == 1080 and sum(row['bytes'] for row in seal['files']) == 273066128, 'final regular census differs')
    compact_wire = json.dumps(seal['files'], sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode()
    need(hashlib.sha256(compact_wire).hexdigest() == seal['file_inventory_sha256'], 'seal file inventory digest differs')
    need(seal['review']['sha256'] == REVIEW_SHA and pin(Path(seal['review']['path'])) == seal['review'], 'qualified review differs')
    selected, omitted = [], []
    for row in seal['files']:
        reason = omit_reason(row)
        if reason:
            omitted.append({**row, 'reason': reason})
        else:
            selected.append({**row, 'binding_origin': 'actual_final_qualification_seal'})
    need(len(selected) == 509 and sum(row['bytes'] for row in selected) == 5377287, 'authorized compact selection differs')
    selected.append({**seal_pin, 'binding_origin': 'externally_pinned_final_seal_self_file'})
    for directory, expected in ((TOOLING, MAINTENANCE_PINS), (SOURCE_REVIEW, REVIEW_PINS)):
        for name, sha in expected.items():
            row = pin(directory / name)
            need(row['sha256'] == sha, 'reviewed maintenance source changed')
            selected.append({**row, 'binding_origin': 'explicit_reviewed_new_maintenance_pin'})
    selected.sort(key=lambda row: os.fsencode(str(Path(row['path']).relative_to(WORKSPACE))))
    need(len(selected) == len({row['path'] for row in selected}) == 524, 'exact unique compact addition count required')
    for row in selected:
        source = Path(row['path'])
        relative = source.relative_to(WORKSPACE)
        need(source.is_relative_to(QUALIFIER) or source.is_relative_to(TOOLING) or source.is_relative_to(SOURCE_REVIEW), 'new owned scope only')
        need(pin(source) == {key: row[key] for key in ('path', 'bytes', 'sha256')}, 'selected source differs from sealed/reviewed pin')
        target = REPO / relative
        need(not target.exists() and not target.is_symlink(), 'all selected paths must be new in parent')
        target.parent.mkdir(parents=True, exist_ok=True)
        need(target.parent.resolve(strict=True) == target.parent, 'private destination parent referral refused')
        with target.open('xb') as stream:
            stream.write(read(source))
        target.chmod(0o644)
        need(pin(target)['sha256'] == row['sha256'], 'private copy differs')
    selection = {'schema': 'ranker-curvature-compact-private-git-selection@1',
                 'status': 'exact_authorized_compact_selection', 'parent': PARENT,
                 'final_seal': seal_pin, 'selected_files': selected, 'omitted_sealed_regular_files': omitted,
                 'selected_file_count': len(selected), 'selected_file_bytes': sum(row['bytes'] for row in selected),
                 'omitted_reasons': dict(collections.Counter(row['reason'] for row in omitted)),
                 'sealed_fixture_aliases_omitted_as_nodes': len(seal['fixture_symlinks']),
                 'full_omitted_regular_bodies': 'retained in the separately qualified HF bundle; not yet published here',
                 'native_jobs': 0, 'commit_calls': 0, 'push_calls': 0}
    selection_pin = write_new(selection_path, selection)
    paths = [str(Path(row['path']).relative_to(WORKSPACE)) for row in selected]
    git('-c', 'core.autocrlf=false', 'add', '--pathspec-from-file=-', '--pathspec-file-nul', input=b''.join(os.fsencode(path) + b'\0' for path in paths))
    changes = git('diff', '--cached', '--name-status', '-z').split(b'\0')
    need(changes[-1] == b'' and len(changes[:-1]) == 2 * len(paths), 'complete staged population required')
    actual_changes = [(changes[index].decode(), os.fsdecode(changes[index + 1])) for index in range(0, len(changes) - 1, 2)]
    need(actual_changes == [('A', path) for path in paths], 'only exact new additions may be staged')
    index_rows = {}
    index_links = []
    for row in git('ls-files', '--stage').decode().splitlines():
        before, path = row.split('\t', 1)
        mode, oid, stage = before.split()
        need(stage == '0', 'unmerged private index refused')
        if mode == '160000':
            index_links.append({'path': path, 'mode': mode, 'oid': oid})
        if path in paths:
            need(mode == '100644', 'exact regular staged source mode required')
            index_rows[path] = oid
    need(index_links == parent_links and len(index_rows) == len(paths), 'all nine parent gitlinks and complete source index preserved')
    objects = git('cat-file', '--batch', input=''.join(index_rows[path] + '\n' for path in paths).encode())
    objects = io.BytesIO(objects)
    staged = []
    for path, source in zip(paths, selected):
        oid, kind, size = objects.readline().decode().strip().split()
        size = int(size)
        raw = objects.read(size)
        need(objects.read(1) == b'\n' and kind == 'blob' and oid == index_rows[path], 'exact staged Git blob required')
        digest = hashlib.sha256(raw).hexdigest()
        need(size == source['bytes'] and digest == source['sha256'], 'staged Git blob differs from sealed/reviewed source')
        staged.append({'path': path, 'mode': '100644', 'git_blob_oid': oid, 'bytes': size, 'sha256': digest})
    need(objects.read() == b'', 'unexpected Git blob readback tail')
    for row in selected:
        need(pin(Path(row['path'])) == {key: row[key] for key in ('path', 'bytes', 'sha256')}, 'source changed during staging')
    need(pin(seal_path) == seal_pin and git('rev-parse', 'HEAD').decode().strip() == PARENT, 'seal or private parent changed')
    guard_after = original_guards()
    need(guard_before == guard_after, 'original checkouts changed during private staging')
    result = {'schema': 'ranker-curvature-compact-private-git-stage@1',
              'status': 'passed_exact_staged_additions_no_commit_or_push',
              'created_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'producer': pin(Path(__file__).resolve()), 'private_checkout': str(REPO),
              'parent': PARENT, 'parent_tree': git('rev-parse', 'HEAD^{tree}').decode().strip(),
              'selection': selection_pin, 'staged_source_blobs': staged,
              'staged_file_count': len(staged), 'staged_file_bytes': sum(row['bytes'] for row in staged),
              'parent_gitlinks': parent_links, 'all_nine_parent_gitlinks_unchanged': True,
              'original_guard_before': guard_before, 'original_guard_after': guard_after,
              'all_selected_source_pins_rechecked_after_staging': True,
              'native_model_solver_test_fit_codec_jobs': 0, 'project_imports': 0,
              'stage_calls': 1, 'commit_calls': 0, 'push_calls': 0,
              'child_source_or_gitlink_changes': 0, 'remote_mutations': 0,
              'future_package_and_publication_ledger_additions_pending': True,
              'proof_authority': False, 'execution_authority': False, 'completion_authority': False,
              'full_task_satisfaction': 'unknown', 'all32_governing_RPI_exits': 'OPEN'}
    print(json.dumps(write_new(closed_path, result), sort_keys=True))


if __name__ == '__main__':
    main()
