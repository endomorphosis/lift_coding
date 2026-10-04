"""Read-only Git variant capture. Raw suspicious bytes remain LOCAL quarantine."""
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import time

BASE = Path('/home/barberb/lift_coding')
OUT = BASE / 'maintenance/terminal-ir-publication-20261004-01/datasets/nested-patches-02'
AUDIT = OUT.parent / 'nested-git-readonly-audit.json'
PATTERNS = [
    ('github_token', rb'gh[pousr]_[A-Za-z0-9]{20,}'),
    ('github_fine_grained_token', rb'github_pat_[A-Za-z0-9_]{40,}'),
    ('huggingface_token', rb'hf_[A-Za-z0-9]{24,}'),
    ('openai_token', rb'(?<![A-Za-z0-9_-])sk-(?:proj-)?[A-Za-z0-9_-]{24,}'),
    ('aws_access_key', rb'AKIA[0-9A-Z]{16}'),
    ('slack_token', rb'xox[baprs]-[A-Za-z0-9-]{20,}'),
    ('private_key_block', rb'-----BEGIN (?:[A-Z0-9 ]+ )?PRIVATE KEY-----[\s\S]{0,100000}?-----END (?:[A-Z0-9 ]+ )?PRIVATE KEY-----'),
    ('private_key_header', rb'-----BEGIN (?:[A-Z0-9 ]+ )?PRIVATE KEY-----'),
]
REGEXES = [(kind, re.compile(pattern)) for kind, pattern in PATTERNS]
SECRET_NAMES = re.compile(r'(^|/)(?:\.env(?:\.[^/]*)?|id_rsa|id_ed25519|credentials(?:\.[^/]*)?|secrets?\.(?:yaml|yml|json|toml)|[^/]+\.(?:p12|pfx|key))$', re.I)

def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + '\n')

def pin(path):
    h = hashlib.sha256()
    n = 0
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
            n += len(chunk)
    return {'path': str(path), 'bytes': n, 'sha256': h.hexdigest()}

def git(repo, *args):
    p = subprocess.run(['git', '-C', str(repo), *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if p.returncode:
        raise RuntimeError('git command failed: ' + repr(args) + ' returncode=' + str(p.returncode))
    return p.stdout

def secret_matches(data):
    found = []
    for kind, pattern in REGEXES:
        for m in pattern.finditer(data):
            found.append({'kind': kind, 'offset': m.start(), 'bytes': len(m.group()), 'value_sha256': hashlib.sha256(m.group()).hexdigest()})
    return found

def raw_and_public_patch(repo, args, destination):
    with destination.open('xb') as f:
        p = subprocess.run(['git', '-C', str(repo), 'diff', '--no-ext-diff', '--binary', *args], stdout=f, stderr=subprocess.PIPE, check=False)
    if p.returncode:
        raise RuntimeError('git diff failed returncode=' + str(p.returncode))
    data = destination.read_bytes()
    found = secret_matches(data)
    entry = pin(destination)
    entry['secret_findings'] = found
    public = destination.with_suffix('.public.patch')
    for kind, pattern in REGEXES:
        data = pattern.sub(lambda m: ('[REDACTED_' + kind.upper() + '_SHA256_' + hashlib.sha256(m.group()).hexdigest() + ']').encode(), data)
    public.write_bytes(data)
    entry['public_derivative'] = pin(public)
    entry['public_derivative_scope'] = 'review-only derivative; redacted diffs are not asserted replay-applicable'
    entry['raw_policy'] = 'LOCAL_ONLY_QUARANTINE' if found else 'unflagged_by_scoped_pattern_scan'
    return entry

def safe_components(repo, relative):
    parts = Path(relative).parts
    if not parts or Path(relative).is_absolute() or any(p in ('..', '') for p in parts):
        raise ValueError('invalid relative Git path')
    cur = repo
    for part in parts[:-1]:
        cur = cur / part
        if stat.S_ISLNK(cur.lstat().st_mode):
            raise ValueError('symlink ancestor refused')
    return repo / relative

def snapshot_stat(s):
    return {'device': s.st_dev, 'inode': s.st_ino, 'mode': s.st_mode, 'size': s.st_size, 'mtime_ns': s.st_mtime_ns, 'ctime_ns': s.st_ctime_ns}

def capture_file(repo, relative, category, objects):
    try:
        path = safe_components(repo, relative)
        before = path.lstat()
    except FileNotFoundError:
        return {'path': relative, 'category': category, 'kind': 'missing'}
    row = {'path': relative, 'category': category, 'before_stat': snapshot_stat(before), 'sensitive_filename': bool(SECRET_NAMES.search(relative))}
    if stat.S_ISLNK(before.st_mode):
        link = os.readlink(path)
        raw = os.fsencode(link)
        row.update(kind='symlink_no_follow', link_target=link, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
    elif stat.S_ISREG(before.st_mode):
        temp = objects / ('.tmp-' + str(os.getpid()))
        h = hashlib.sha256()
        findings = []
        tail = b''
        total = 0
        with path.open('rb') as source, temp.open('xb') as output:
            opened = os.fstat(source.fileno())
            if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
                raise RuntimeError('file identity changed before open')
            for chunk in iter(lambda: source.read(1024 * 1024), b''):
                h.update(chunk)
                output.write(chunk)
                scan = tail + chunk
                for match in secret_matches(scan):
                    match['offset'] += total - len(tail)
                    if not any(x['kind'] == match['kind'] and x['offset'] == match['offset'] for x in findings):
                        findings.append(match)
                total += len(chunk)
                tail = scan[-100256:]
        digest = h.hexdigest()
        target = objects / digest[:2] / digest
        target.parent.mkdir(exist_ok=True)
        if target.exists():
            temp.unlink()
        else:
            temp.rename(target)
        row.update(kind='regular', bytes=total, sha256=digest, object_path=str(target), secret_findings=findings, raw_policy='LOCAL_ONLY_QUARANTINE' if findings else 'unflagged_by_scoped_pattern_scan')
    elif stat.S_ISDIR(before.st_mode):
        row.update(kind='directory', scope='expanded separately without following symlinks; .git metadata omitted and declared nested repositories captured independently')
    else:
        row.update(kind='unsupported_special_file')
    after = path.lstat()
    row['after_stat'] = snapshot_stat(after)
    row['stable'] = row['before_stat'] == row['after_stat']
    return row

def expand(repo, relative):
    try:
        path = safe_components(repo, relative)
    except FileNotFoundError:
        yield relative
        return
    if not path.is_symlink() and path.is_dir():
        yield relative
        for directory, dirs, files in os.walk(path, followlinks=False):
            dirs.sort()
            files.sort()
            for name in list(dirs):
                child = Path(directory) / name
                rel = child.relative_to(repo).as_posix()
                if name == '.git':
                    dirs.remove(name)
                elif child.is_symlink():
                    dirs.remove(name)
                    yield rel
            for name in files:
                if name != '.git':
                    yield (Path(directory) / name).relative_to(repo).as_posix()
    else:
        yield relative

def repo_path(audit, identifier):
    node = audit['parents'][str(identifier)]
    parent = BASE if node['parent'] is None else repo_path(audit, node['parent'])
    return parent / node['relative']

def main():
    started = time.monotonic()
    OUT.mkdir(mode=0o700)
    objects = OUT / 'objects'
    objects.mkdir(mode=0o700)
    audit = json.loads(AUDIT.read_text())
    summary = {'schema': 'nested-git-variant-capture@1', 'started_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'audit': pin(AUDIT), 'scope': '89 declared dirty initialized repositories; no LIVE mutation; no symlink following; ignored files and .git internal metadata are outside this Git-variant capture and require separate whole-tree HF scope; pattern scan is scoped and not a guarantee of no credentials', 'repositories': [], 'errors': [], 'secret_findings': [], 'sensitive_filename_findings': []}
    try:
        for number, declared in enumerate(audit['dirty']):
            repo = repo_path(audit, declared['id'])
            relative_repo = repo.relative_to(BASE).as_posix()
            folder = OUT / ('repo-' + str(declared['id']).zfill(3))
            folder.mkdir()
            row = {'declared': declared, 'workspace_relative': relative_repo, 'path': str(repo), 'errors': []}
            try:
                toplevel = git(repo, 'rev-parse', '--show-toplevel').decode().strip()
                if Path(toplevel).resolve() != repo.resolve():
                    raise RuntimeError('Git worktree root differs from declared repository')
                head = git(repo, 'rev-parse', 'HEAD').decode().strip()
                status = git(repo, 'status', '--porcelain=v1', '-z', '--untracked-files=all')
                (folder / 'status-before.z').write_bytes(status)
                row['HEAD_before'] = head
                row['status_before'] = pin(folder / 'status-before.z')
                row['patches'] = [raw_and_public_patch(repo, args, folder / name) for args, name in [(('HEAD',), 'head.patch'), (('--cached', 'HEAD'), 'index.patch'), ((), 'unstaged.patch')]]
                tracked = [os.fsdecode(p) for p in git(repo, 'diff', '--name-only', '-z', 'HEAD').split(b'\0') if p]
                untracked = [os.fsdecode(p) for p in git(repo, 'ls-files', '--others', '--exclude-standard', '-z').split(b'\0') if p]
                gitlinks = {}
                for item in git(repo, 'ls-files', '--stage', '-z').split(b'\0'):
                    if item:
                        metadata, name = item.split(b'\t', 1)
                        mode, oid, stage = metadata.split()
                        if mode == b'160000':
                            gitlinks[os.fsdecode(name)] = {'index_oid': oid.decode(), 'index_stage': stage.decode()}
                entries = {}
                for category, names in [('tracked_current_delta', tracked), ('untracked', untracked)]:
                    for relative in names:
                        try:
                            if relative in gitlinks:
                                entries[relative] = {'path': relative, 'category': category, 'kind': 'gitlink', **gitlinks[relative], 'scope': 'declared child variant captured independently; no parent traversal of child contents'}
                                continue
                            for expanded in expand(repo, relative):
                                if expanded not in entries:
                                    entries[expanded] = capture_file(repo, expanded, category, objects)
                        except BaseException as exc:
                            (objects / ('.tmp-' + str(os.getpid()))).unlink(missing_ok=True)
                            row['errors'].append({'path': relative, 'error_type': type(exc).__name__, 'message': str(exc)})
                row['files'] = list(entries.values())
                row['HEAD_after'] = git(repo, 'rev-parse', 'HEAD').decode().strip()
                after_status = git(repo, 'status', '--porcelain=v1', '-z', '--untracked-files=all')
                (folder / 'status-after.z').write_bytes(after_status)
                row['status_after'] = pin(folder / 'status-after.z')
                row['stable_git_identity'] = row['HEAD_before'] == row['HEAD_after'] and status == after_status
                row['stable_all_files'] = all(f.get('stable', True) for f in row['files'])
                row['counts'] = {'file_entries': len(row['files']), 'regular_bytes_including_duplicates': sum(f.get('bytes', 0) for f in row['files'] if f['kind'] == 'regular'), 'regular_files': sum(f['kind'] == 'regular' for f in row['files']), 'symlinks_no_follow': sum(f['kind'] == 'symlink_no_follow' for f in row['files'])}
                for patch in row['patches']:
                    if patch['secret_findings']:
                        summary['secret_findings'].append({'repo': relative_repo, 'patch': patch['path'], 'findings': patch['secret_findings'], 'raw_policy': 'LOCAL_ONLY_QUARANTINE'})
                for f in row['files']:
                    if f.get('secret_findings'):
                        summary['secret_findings'].append({'repo': relative_repo, 'path': f['path'], 'object_path': f['object_path'], 'findings': f['secret_findings'], 'raw_policy': 'LOCAL_ONLY_QUARANTINE'})
                    if f.get('sensitive_filename'):
                        summary['sensitive_filename_findings'].append({'repo': relative_repo, 'path': f['path']})
            except BaseException as exc:
                row['errors'].append({'error_type': type(exc).__name__, 'message': str(exc)})
            dump(folder / 'manifest.json', row)
            summary['repositories'].append({'id': declared['id'], 'relative': relative_repo, 'manifest': pin(folder / 'manifest.json'), 'counts': row.get('counts'), 'stable_git_identity': row.get('stable_git_identity'), 'stable_all_files': row.get('stable_all_files'), 'errors': row['errors']})
            summary['errors'].extend({'repo': relative_repo, **error} for error in row['errors'])
            dump(OUT / 'progress.json', summary)
            if (number + 1) % 10 == 0:
                print(json.dumps({'repositories_closed': number + 1, 'errors': len(summary['errors']), 'secret_flagged_records': len(summary['secret_findings'])}), flush=True)
    finally:
        summary['actual_outer_elapsed_seconds'] = time.monotonic() - started
        summary['closed_utc'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        summary['status'] = 'captured' if len(summary['repositories']) == 89 and not summary['errors'] else 'failed_or_partial'
        summary['objects'] = {'unique_count': 0, 'bytes': 0}
        for folder in objects.iterdir():
            if folder.is_dir():
                for path in folder.iterdir():
                    summary['objects']['unique_count'] += 1
                    summary['objects']['bytes'] += path.stat().st_size
        dump(OUT / 'summary.json', summary)
        print(json.dumps({'status': summary['status'], 'repos': len(summary['repositories']), 'objects': summary['objects'], 'elapsed': summary['actual_outer_elapsed_seconds'], 'errors': len(summary['errors']), 'secret_flagged_records': len(summary['secret_findings'])}), flush=True)

if __name__ == '__main__':
    main()
