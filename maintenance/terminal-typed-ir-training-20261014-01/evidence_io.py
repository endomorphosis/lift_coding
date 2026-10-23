"""Finite public-artifact reads and exclusive writes for this successor."""
import hashlib
import json
import os
from pathlib import Path
import stat

ROOT = Path(__file__).resolve().parent
TYPED = ROOT.parent / 'terminal-typed-ir-proof-index-20261014-01'
PRIOR = ROOT.parent / 'terminal-codebase-ir-training-20261014-01'
DATASETS = ROOT.parent / 'terminal-compact-retrieval-20261011-01' / 'pinned-dependencies-v10' / 'datasets' / 'ipfs_datasets_py'
FALSE = {'proof_authority': False, 'execution_authority': False, 'completion_authority': False,
    'source_runtime_equivalence_proved': False, 'source_model_equivalence_proved': False,
    'asymptotic_optimizer_convergence_proved': False, 'full_task_satisfaction': False,
    'provider_token_savings_measured': False, 'global_durable_budget': False}

def wire(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False,
                      ensure_ascii=True).encode('ascii')

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def read(path, maximum=16*1024*1024):
    path = Path(path)
    if path.resolve(strict=True) != path:
        raise ValueError('canonical non-symlink artifact required')
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > maximum:
            raise ValueError('bounded single-link regular artifact required')
        body = bytearray()
        while len(body) <= maximum:
            block = os.read(descriptor, min(65536, maximum+1-len(body)))
            if not block:
                break
            body.extend(block)
        after = os.fstat(descriptor)
        witness = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
        if len(body) > maximum or len(body) != before.st_size or witness(before) != witness(after):
            raise ValueError('artifact changed or exceeds bound')
        return bytes(body)
    finally:
        os.close(descriptor)

def write(path, value):
    body = wire(value)
    if len(body) > 32*1024*1024:
        raise ValueError('output exceeds artifact bound')
    with Path(path).open('xb') as stream:
        stream.write(body)
        stream.flush()
        os.fsync(stream.fileno())

def pin(path):
    raw = read(path, 32*1024*1024)
    return {'path': str(path), 'bytes': len(raw), 'sha256': sha(raw)}

def predecessor_inputs():
    """Validate only explicitly selected sealed public artifacts; never open DB/CAS."""
    required = [(TYPED, 'fec478e685ac2b3f1a4412cd798d51468406cbcccbae09173c68855c41910f35'),
                (PRIOR, '204724395eaa15c1c224e84473fe89447cd0e15470abd507bba30116fdd8ae94')]
    manifests = {}
    for root, expected in required:
        raw = read(root/'evidence-manifest.json', 1024*1024)
        if sha(raw) != expected:
            raise ValueError('sealed predecessor inventory changed')
        manifests[root] = {row['path']: row for row in json.loads(raw)['files']}
    selected = []
    def selected_read(root, name, maximum):
        row = manifests[root][name]
        raw = read(root/name, maximum)
        if len(raw) != row['bytes'] or sha(raw) != row['sha256']:
            raise ValueError('selected predecessor artifact changed')
        selected.append({'path': str(root/name), 'bytes': len(raw), 'sha256': sha(raw)})
        return raw
    corpus = json.loads(selected_read(PRIOR, 'corpus-manifest-01.json', 65536))
    original = json.loads(selected_read(TYPED, 'experiment-03/result.json', 8*1024*1024))
    bodies = {}
    for task in corpus['tasks']:
        for source in task['sources']:
            raw = selected_read(TYPED, 'experiment-03/source-repository/'+source['path'], 8192)
            if len(raw) != source['bytes'] or sha(raw) != source['sha256']:
                raise ValueError('corpus source pin differs')
            bodies[source['path']] = raw
    if len(bodies) != 5 or original['completed'] is not True:
        raise ValueError('complete bounded public corpus required')
    return corpus, original, bodies, sorted(selected, key=lambda r:r['path'])
