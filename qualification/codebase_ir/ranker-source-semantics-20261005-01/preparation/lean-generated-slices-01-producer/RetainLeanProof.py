"""Pinned private-workspace helper: execute Lean once and retain bounded chunks.

No process runs on import. The enclosing BoundedToolRunner owns all process,
CPU, wall, workspace, and per-file capture limits. This helper changes only the
representation of complete compiler outputs, without compressing or discarding
any bytes of an accepted object.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys

PROFILE = {
    'format': 'bounded_lean_chunks@1', 'native_per_file_capture_bytes': 65536,
    'native_max_declared_outputs': 64, 'chunk_bytes': 65536, 'max_chunk_files': 61,
    'max_raw_object_bytes': 61 * 65536, 'max_manifest_bytes': 65536,
    'max_object_files': 4, 'object_suffixes': ['.olean', '.olean.private', '.olean.server', '.ir'],
    'native_cpu_seconds': 20, 'native_wall_seconds': 20,
    'native_workspace_bytes': 16 * 1024**2, 'native_max_source_bytes': 262144,
    'compression': 'none', 'chunk_order': 'consecutive-global-index-and-object-concatenation',
}
PROFILE_SHA256 = hashlib.sha256(json.dumps(PROFILE, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
MANIFEST_NAME = 'LeanProofChunks.json'


def _write_manifest(body):
    raw = (json.dumps(body, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()
    if len(raw) > PROFILE['max_manifest_bytes']:
        raise ValueError('retention manifest exceeds fixed capture bound')
    with Path(MANIFEST_NAME).open('xb') as stream:
        stream.write(raw)


def retain_objects(filename):
    """Split known regular compiler companions into exact sequential chunks."""
    stem = filename[:-5]
    objects, chunks, total = [], [], 0
    for suffix in PROFILE['object_suffixes']:
        name = stem + suffix
        path = Path(name)
        if not path.exists():
            continue
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        try:
            before = os.fstat(fd)
            if not stat.S_ISREG(before.st_mode) or before.st_size <= 0:
                raise ValueError('nonempty regular compiler companion required')
            if total + before.st_size > PROFILE['max_raw_object_bytes']:
                raise ValueError('complete object population exceeds fixed raw-byte bound')
            digest, size, names = hashlib.sha256(), 0, []
            while True:
                pieces, remaining = [], PROFILE['chunk_bytes']
                while remaining:
                    piece = os.read(fd, remaining)
                    if not piece:
                        break
                    pieces.append(piece)
                    remaining -= len(piece)
                block = b''.join(pieces)
                if not block:
                    break
                if len(chunks) >= PROFILE['max_chunk_files']:
                    raise ValueError('complete object population exceeds fixed chunk-count bound')
                chunk_name = 'LeanProofChunk%03d.bin' % len(chunks)
                with Path(chunk_name).open('xb') as stream:
                    stream.write(block)
                chunks.append({'name': chunk_name, 'bytes': len(block),
                               'sha256': hashlib.sha256(block).hexdigest()})
                names.append(chunk_name)
                digest.update(block)
                size += len(block)
            signature = lambda s: (s.st_dev, s.st_ino, s.st_mode, s.st_nlink,
                                    s.st_size, s.st_mtime_ns, s.st_ctime_ns)
            if size != before.st_size or signature(before) != signature(os.fstat(fd)) or signature(before) != signature(path.lstat()):
                raise ValueError('compiler output changed during retention')
            total += size
            objects.append({'name': name, 'bytes': size, 'sha256': digest.hexdigest(), 'chunks': names})
        finally:
            os.close(fd)
    if not objects or objects[0]['name'] != stem + '.olean':
        raise ValueError('complete main Lean object absent')
    return {'schema': 'bounded_lean_chunks@1', 'status': 'complete',
            'retention_profile_sha256': PROFILE_SHA256, 'native_lean_invocations': 1,
            'native_lean_returncode': 0, 'objects': objects, 'chunks': chunks,
            'aggregate_raw_object_bytes': total}


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 3 or args[2] not in ('positive', 'negative'):
        raise ValueError('exact lean/source/mode arguments required')
    executable, filename, mode = args
    if not Path(executable).is_absolute() or re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*\.lean', filename) is None:
        raise ValueError('absolute Lean executable and portable source required')
    command = [executable, '-o', filename[:-5] + '.olean', filename] if mode == 'positive' else [executable, filename]
    result = subprocess.run(command, check=False)
    if result.returncode != 0:
        _write_manifest({'schema': 'bounded_lean_chunks@1', 'status': 'native_nonzero',
                         'retention_profile_sha256': PROFILE_SHA256, 'native_lean_invocations': 1,
                         'native_lean_returncode': result.returncode})
        return result.returncode
    try:
        if mode != 'positive':
            raise ValueError('negative control unexpectedly compiled')
        _write_manifest(retain_objects(filename))
    except (ValueError, OSError) as error:
        _write_manifest({'schema': 'bounded_lean_chunks@1', 'status': 'retention_inconclusive',
                         'retention_profile_sha256': PROFILE_SHA256, 'native_lean_invocations': 1,
                         'native_lean_returncode': 0, 'error': type(error).__name__ + ': ' + str(error)})
        return 70
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
