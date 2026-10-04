"""Publish bounded source through an isolated index; preserve earlier attempts."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import re
import stat
import subprocess
import time

ROOT = Path('/home/barberb/lift_coding')
OUT = Path(__file__).resolve().parent
INDEX = OUT / 'private-index-03'
MAX_BYTES = 8 * 1024 * 1024
SECRET = re.compile(rb'(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|hf_[A-Za-z0-9]{30,}|xai-[A-Za-z0-9]{35,}|sk-ant-api[A-Za-z0-9_-]{30,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)')


def signature(info):
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns


def git(args, raw=None):
    result = subprocess.run(['git', '-c', 'gc.auto=0', '-c', 'maintenance.auto=false', *args],
                            cwd=ROOT, env={**os.environ, 'GIT_INDEX_FILE': str(INDEX),
                            'GIT_TERMINAL_PROMPT': '0', 'GIT_OPTIONAL_LOCKS': '0'},
                            input=raw, capture_output=True, timeout=120)
    if result.returncode:
        raise RuntimeError((args[:2], result.returncode, result.stderr[:500].decode(errors='replace')))
    return result.stdout


def stable_read(path, kind):
    before = path.lstat()
    if kind == 'link':
        assert stat.S_ISLNK(before.st_mode)
        raw = os.fsencode(os.readlink(path))
        mode = '120000'
    else:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(fd, 'rb') as stream:
            first = os.fstat(stream.fileno())
            assert stat.S_ISREG(first.st_mode)
            raw = stream.read(MAX_BYTES + 1)
            after = os.fstat(stream.fileno())
        assert len(raw) <= MAX_BYTES
        assert signature(before) == signature(first) == signature(after)
        mode = '100755' if first.st_mode & 0o111 else '100644'
        assert not SECRET.search(raw), str(path.relative_to(ROOT))
    assert signature(before) == signature(path.lstat())
    return raw, mode


def main():
    started = time.monotonic()
    source = json.loads((OUT / 'selection.json').read_bytes())
    drift = json.loads((OUT / 'concurrent-drift-03.json').read_bytes())
    assert not INDEX.exists()
    assert git(['rev-parse', 'HEAD']).decode().strip() == source['head'] == drift['head']
    original = source['original_index']
    assert hashlib.sha256(Path(original['path']).read_bytes()).hexdigest() == original['sha256']
    allowed = {row['path']: row for row in drift['concurrent_drifts']}
    assert set(allowed) == {'.gitignore'}
    git(['read-tree', source['head']])
    files = []
    evidence = []
    entries = []
    for row in source['selected']:
        name = row['path']
        if name.startswith(('papers/revisions/', 'papers/completion/', 'artifacts/', '.pgir_campaign/runtime/')):
            evidence.append(row)
            continue
        path = ROOT / name
        if row['type'] == 'deleted':
            assert not path.exists() and not path.is_symlink()
            entries.append(b'0 ' + b'0' * 40 + b'\t' + os.fsencode(name) + b'\0')
            files.append(row)
            continue
        raw, mode = stable_read(path, row['type'])
        digest = hashlib.sha256(raw).hexdigest()
        if name in allowed:
            assert digest == allowed[name]['current_sha256']
        else:
            assert digest == row['sha256'] and len(raw) == row['bytes'], name
        oid = git(['hash-object', '-w', '--stdin'], raw).strip()
        assert git(['cat-file', 'blob', oid.decode()]) == raw
        entries.append(mode.encode() + b' ' + oid + b'\t' + os.fsencode(name) + b'\0')
        files.append({**row, 'mode': mode, 'bytes': len(raw), 'sha256': digest,
                      'git_blob': oid.decode(), 'original_selected_sha256': row['sha256']})
    git(['update-index', '--add', '-z', '--index-info'], b''.join(entries))
    tree = git(['write-tree']).decode().strip()
    assert hashlib.sha256(Path(original['path']).read_bytes()).hexdigest() == original['sha256']
    assert git(['rev-parse', 'HEAD']).decode().strip() == source['head']
    result = {'schema': 'terminal-ir-root-source-tree@3', 'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'tree': tree, 'parent': source['head'], 'private_index': str(INDEX), 'source_files': files,
              'source_files_count': len(files), 'source_bytes': sum(r.get('bytes', 0) for r in files),
              'evidence_files_huggingface': len(evidence), 'evidence_bytes_huggingface': sum(r.get('bytes', 0) for r in evidence),
              'explicit_concurrent_drift': allowed, 'original_index_unchanged': True,
              'source_scope': 'prior frozen selection only, apart from explicitly pinned .gitignore drift',
              'published': False, 'elapsed_seconds': time.monotonic() - started}
    with (OUT / 'source-tree-03.json').open('x') as stream:
        json.dump(result, stream, sort_keys=True, indent=2)
        stream.write('\n')
    print(json.dumps({k: result[k] for k in ('tree', 'source_files_count', 'source_bytes', 'elapsed_seconds')}))


if __name__ == '__main__':
    main()
