"""Bounded stdlib evidence reader. No runtime authority or network operations."""
import hashlib
import json
import os
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path('/home/barberb/lift_coding')
OUT = Path(__file__).absolute().parent
AUTH = json.loads((OUT/'authorization.json').read_text())

class Reader:
    def __init__(self, worker):
        self.worker = worker
        self.limit = AUTH['allocations'][worker]
        self.log = OUT/'workstreams'/f'{worker}_inputs.jsonl'
        self.seen = {r['path']: r for r in (json.loads(s) for s in self.log.read_text().splitlines())} if self.log.exists() else {}

    def read(self, path, role='original_evidence'):
        p = Path(path).absolute()
        if not p.is_relative_to(ROOT) or p.resolve() != p or not p.is_file():
            raise ValueError('Missing, symlinked or unauthorized evidence: '+str(p))
        if p.stat().st_size > AUTH['limits']['per_json_text_file_bytes']:
            raise ValueError('Evidence file exceeds bound')
        if str(p) not in self.seen and len(self.seen) >= self.limit['files']:
            raise ValueError('File allocation exhausted')
        data = p.read_bytes()
        if len(data) > AUTH['limits']['per_json_text_file_bytes']:
            raise ValueError('Evidence grew beyond bound')
        sha = hashlib.sha256(data).hexdigest()
        if str(p) in self.seen:
            if self.seen[str(p)]['sha256'] != sha: raise ValueError('Evidence changed: '+str(p))
        else:
            if sum(r['bytes'] for r in self.seen.values()) + len(data) > self.limit['bytes']:
                raise ValueError('Byte allocation exhausted')
            row = {'path':str(p),'sha256':sha,'bytes':len(data),'role':role,'worker':self.worker,
                   'observed_at':datetime.now(timezone.utc).isoformat(),'signature_verification':'not_performed'}
            fd = os.open(self.log,os.O_WRONLY|os.O_APPEND|os.O_CREAT,0o600)
            with os.fdopen(fd,'w') as f:f.write(json.dumps(row,sort_keys=True)+'\n')
            self.seen[str(p)] = row
        return data

    def json(self,path,role='original_evidence'):return json.loads(self.read(path,role))
    def text(self,path,role='original_evidence'):return self.read(path,role).decode('utf-8')

def write_json(name,obj):
    p=OUT/name
    assert p.resolve()==p and p.is_relative_to(OUT)
    with p.open('x') as f:json.dump(obj,f,indent=2,sort_keys=True);f.write('\n')
    p.chmod(0o600)

def write_jsonl(name,rows):
    p=OUT/name
    assert p.resolve()==p and p.is_relative_to(OUT)
    with p.open('x') as f:
        for row in rows:f.write(json.dumps(row,sort_keys=True)+'\n')
    p.chmod(0o600)
