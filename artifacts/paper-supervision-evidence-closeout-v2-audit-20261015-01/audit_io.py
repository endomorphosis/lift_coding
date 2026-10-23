"""Bounded local evidence reader, with per-workstream provenance projections.

This module owns no runtime state. It imports no project packages and makes no
network calls. Each workstream has a separate append-only audit input log.
"""
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path('/home/barberb/lift_coding')
OUT = Path(__file__).absolute().parent
MAX_FILE = 2 * 1024 * 1024

class Reader:
    def __init__(self, worker):
        self.worker = worker
        self.limits = json.loads((OUT / 'authorization.json').read_text())['workstream_allocations'][worker]
        self.log = OUT / 'workstreams' / (worker + '_inputs.jsonl')
        self.seen = {}
        if self.log.exists():
            for line in self.log.read_text().splitlines():
                row = json.loads(line)
                self.seen[row['path']] = row

    def read(self, path, role='evidence'):
        path = Path(path).absolute()
        if not path.is_relative_to(ROOT) or path.resolve() != path:
            raise ValueError('Path outside authorized root or through symlink: ' + str(path))
        if not path.is_file() or path.stat().st_size > MAX_FILE:
            raise ValueError('Missing or oversized evidence: ' + str(path))
        raw = path.read_bytes()
        if len(raw) > MAX_FILE:
            raise ValueError('Evidence grew beyond bound')
        digest = hashlib.sha256(raw).hexdigest()
        prior = self.seen.get(str(path))
        if prior:
            if prior['sha256'] != digest:
                raise ValueError('Evidence changed during audit: ' + str(path))
        else:
            if len(self.seen) >= self.limits['files'] or sum(x['bytes'] for x in self.seen.values()) + len(raw) > self.limits['bytes']:
                raise ValueError('Workstream read bound reached')
            row = {'path': str(path), 'bytes': len(raw), 'sha256': digest,
                   'role': role, 'worker': self.worker,
                   'observed_at_utc': datetime.now(timezone.utc).isoformat(),
                   'artifact_id': 'sha256:' + digest,
                   'signature_verification': 'not_performed', 'key_provenance': None}
            fd = os.open(self.log, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
            with os.fdopen(fd, 'w') as stream:
                stream.write(json.dumps(row, sort_keys=True) + '\n')
            self.seen[str(path)] = row
        return raw

    def text(self, path, role='evidence'):
        return self.read(path, role).decode('utf-8')

    def json(self, path, role='evidence'):
        return json.loads(self.read(path, role))

def write_json(relative, value):
    path = OUT / relative
    if path.resolve() != path or not path.is_relative_to(OUT):
        raise ValueError('Unsafe output')
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')
    path.chmod(0o600)

def write_jsonl(relative, rows):
    path = OUT / relative
    if path.resolve() != path or not path.is_relative_to(OUT):
        raise ValueError('Unsafe output')
    with path.open('x') as stream:
        for row in rows:
            stream.write(json.dumps(row, sort_keys=True) + '\n')
    path.chmod(0o600)
