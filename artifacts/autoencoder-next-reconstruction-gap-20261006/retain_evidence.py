"""Seal this task's bounded evidence without archiving model or vector bodies."""
from __future__ import annotations

import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import tarfile

R = Path(__file__).resolve().parent
W = R.parents[1]
RUN = W / 'external/ipfs_datasets/workspace/test-logs/decoder-train-readout-observation-20261006'
SUFFIXES = {'.py', '.json', '.jsonl', '.xml', '.diff', '.md', '.log'}
EXCLUDED_PARTS = {'__pycache__', '.pytest_cache', 'draft-r1', 'draft-r2'}
MAX_BYTES = 100_000_000


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def read_stable(path):
    def identity(stat):
        return stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns

    before = identity(path.stat())
    if path.is_symlink() or not path.is_file():
        raise ValueError('regular immutable evidence required: ' + str(path))
    with path.open('rb') as stream:
        if identity(os.fstat(stream.fileno())) != before:
            raise ValueError('evidence replaced before retention: ' + str(path))
        raw = stream.read()
        if identity(os.fstat(stream.fileno())) != before:
            raise ValueError('opened evidence changed during retention: ' + str(path))
    if before != identity(path.stat()) or len(raw) != before[2]:
        raise ValueError('evidence changed during retention: ' + str(path))
    return raw


def main():
    terminal = json.loads(read_stable(RUN / 'train-observation-r1-guardian-exit.json'))
    resource = json.loads(read_stable(RUN / 'train-observation-r1/resources-final.json'))
    if terminal['returncode'] != 0 or resource['status'] != 'released':
        raise ValueError('completed, released observation required')
    output = R / 'reconstruction-gap-evidence.tar.gz'
    manifest_path = R / 'retention-manifest.json'
    if output.exists() or manifest_path.exists():
        raise ValueError('retained evidence is immutable')
    candidates = {R / 'retain_evidence.py'}
    for name in ('diagnosis', 'qualifier-review', 'train-observation', 'training-review', 'guardian'):
        for path in (R / name).rglob('*'):
            if path.is_file() and path.suffix in SUFFIXES and not EXCLUDED_PARTS.intersection(path.parts):
                candidates.add(path)
    for path in RUN.rglob('*'):
        if path.is_file() and path.suffix in SUFFIXES and not EXCLUDED_PARTS.intersection(path.parts):
            candidates.add(path)
    entries = []
    total = 0
    with output.open('xb') as stream:
        with gzip.GzipFile(fileobj=stream, mode='wb', filename='', mtime=0, compresslevel=6) as compressed:
            with tarfile.open(fileobj=compressed, mode='w|', format=tarfile.PAX_FORMAT) as archive:
                for path in sorted(candidates):
                    relative = path.relative_to(W).as_posix()
                    if path.resolve() != path or any(parent.is_symlink() for parent in path.parents):
                        raise ValueError('symbolic evidence path refused: ' + str(path))
                    raw = read_stable(path)
                    total += len(raw)
                    if total > MAX_BYTES:
                        raise ValueError('bounded evidence archive exceeded')
                    info = tarfile.TarInfo(relative)
                    info.size = len(raw)
                    info.mode = 0o644
                    info.mtime = 0
                    archive.addfile(info, io.BytesIO(raw))
                    entries.append(dict(path=relative, bytes=len(raw), sha256=digest(raw)))
    raw_archive = read_stable(output)
    manifest = dict(schema='reconstruction-gap-evidence-retention/v1', passed=True,
                    findings=[], entries=entries, source_bytes=total,
                    archive=dict(path=output.relative_to(W).as_posix(), bytes=len(raw_archive),
                                 sha256=digest(raw_archive)),
                    tensor_and_embedding_bodies_archived=False,
                    model_execution_performed=False, source_modified=False,
                    qualification_granted=False)
    with manifest_path.open('x') as stream:
        json.dump(manifest, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps(dict(entries=len(entries), source_bytes=total, archive_bytes=len(raw_archive))))


if __name__ == '__main__':
    main()
