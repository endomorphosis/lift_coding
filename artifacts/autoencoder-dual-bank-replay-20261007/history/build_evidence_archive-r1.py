"""Retain completed replay evidence without checkpoint tensor bodies.

Only explicit execution creates the deterministic archive. It imports no model
owners and performs no resource, Git, Hub, proof or training operation.
"""
import gzip
import hashlib
import json
from pathlib import Path
import os
import stat
import tarfile

W = Path('/home/barberb/lift_coding')
R = W / 'artifacts/autoencoder-dual-bank-replay-20261007'
RUN = W / 'external/ipfs_datasets/workspace/test-logs/decoder-dual-bank-replay-20261007'
MAX_SOURCE_BYTES = 512_000_000
MAX_ARCHIVE_BYTES = 100_000_000
MAX_MEMBERS = 4096


def identity(value):
    return (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns)


def sha(path):
    path = Path(path)
    before = path.stat()
    if not stat.S_ISREG(before.st_mode) or path.is_symlink():
        raise ValueError('regular nonsymbolic evidence required')
    h = hashlib.sha256()
    size = 0
    with path.open('rb') as stream:
        if identity(os.fstat(stream.fileno())) != identity(before):
            raise ValueError('opened evidence was replaced')
        for data in iter(lambda: stream.read(1048576), b''):
            h.update(data)
            size += len(data)
        if identity(os.fstat(stream.fileno())) != identity(before):
            raise ValueError('opened evidence changed while hashing')
    if size != before.st_size or identity(path.stat()) != identity(before):
        raise ValueError('evidence pathname or size changed while hashing')
    return h.hexdigest()


class BoundedArchive:
    def __init__(self, stream):
        self.stream = stream
        self.bytes_written = 0

    def write(self, data):
        if self.bytes_written + len(data) > MAX_ARCHIVE_BYTES:
            raise ValueError('compressed evidence byte cap exceeded')
        written = self.stream.write(data)
        if written != len(data):
            raise ValueError('incomplete archive write')
        self.bytes_written += written
        return written

    def flush(self):
        self.stream.flush()


class AuthenticSource:
    def __init__(self, stream):
        self.stream = stream
        self.digest = hashlib.sha256()
        self.bytes_read = 0

    def read(self, size=-1):
        data = self.stream.read(size)
        self.digest.update(data)
        self.bytes_read += len(data)
        return data


def main():
    output = R / 'publication'
    output.mkdir(exist_ok=True)
    archive = output / 'replay-evidence.tar.gz'
    manifest_path = output / 'replay-evidence-manifest.json'
    if archive.exists() or manifest_path.exists():
        raise ValueError('completed archive and manifest must be fresh')
    for phase in ['preflight-384-r1', 'training-384-r1', 'evaluation-r1']:
        if json.loads((RUN / (phase + '-guardian-exit.json')).read_bytes())['returncode'] != 0:
            raise ValueError('successful completed phases required')
    if json.loads((R / 'postfit-comparison.json').read_bytes())['complete'] is not True:
        raise ValueError('complete saved-output comparison required')
    selected, excluded = {}, []
    for prefix, root in [('owned-run', RUN), ('review-and-source', R)]:
        for path in sorted(root.rglob('*')):
            if not path.is_file() or path.is_symlink():
                continue
            relative = path.relative_to(root)
            if root == R and relative.parts[0] in ['publication', 'pipeline']:
                continue
            if '__pycache__' in relative.parts or path.suffix in ['.pyc', '.index']:
                continue
            name = prefix + '/' + relative.as_posix()
            if path.name.endswith('-state.json'):
                excluded.append(dict(member=name, path=str(path),
                    sha256=sha(path), bytes=path.stat().st_size,
                    reason='checkpoint tensor body remains a local immutable reference; no promotion or upload'))
                continue
            before = path.stat()
            selected[name] = dict(path=str(path), sha256=sha(path), bytes=before.st_size,
                source_identity=list(identity(before)))
            if identity(path.stat()) != identity(before):
                raise ValueError('source changed while selecting archive members')
    if len(selected) > MAX_MEMBERS or sum(v['bytes'] for v in selected.values()) > MAX_SOURCE_BYTES:
        raise ValueError('archive member/source byte cap exceeded')
    with archive.open('xb') as raw:
        with gzip.GzipFile(fileobj=BoundedArchive(raw), mode='wb', filename='', mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode='w', format=tarfile.PAX_FORMAT) as tar:
                for name, record in sorted(selected.items()):
                    path = Path(record['path'])
                    info = tarfile.TarInfo(name)
                    info.size = record['bytes']
                    info.mode = 0o644
                    info.uid = info.gid = 0
                    info.mtime = 0
                    with path.open('rb') as stream:
                        if list(identity(os.fstat(stream.fileno()))) != record['source_identity']:
                            raise ValueError('opened source changed before tar copy')
                        authentic = AuthenticSource(stream)
                        tar.addfile(info, authentic)
                        if (authentic.bytes_read != record['bytes'] or authentic.digest.hexdigest() != record['sha256']
                                or list(identity(os.fstat(stream.fileno()))) != record['source_identity']):
                            raise ValueError('opened source changed during tar copy')
                    if list(identity(path.stat())) != record['source_identity']:
                        raise ValueError('source changed while archiving: ' + str(path))
        raw.flush()
        os.fsync(raw.fileno())
    result = dict(schema='dual-bank-replay-evidence-archive/v1',
        archive=dict(path=str(archive), sha256=sha(archive), bytes=archive.stat().st_size),
        members=selected, member_count=len(selected), source_bytes=sum(v['bytes'] for v in selected.values()),
        limits=dict(source_bytes=MAX_SOURCE_BYTES, compressed_bytes=MAX_ARCHIVE_BYTES, members=MAX_MEMBERS),
        excluded_checkpoint_bodies=excluded,
        retained_vector_policy='Saved source-bank and scalar/reconstruction observations may contain cached or normalized vectors; the archive is not vector-free.',
        historical_numerical_sources_and_caches='Referenced by complete immutable manifests; earlier balanced-wording archive/main publication preserves their evidence. This archive retains the new owned phases and reviews only.',
        all_phase_outputs_complete=True, checkpoint_promoted=False, qualified=False,
        admitted=False, proof_authority=False, Constitution_formalized=False)
    with manifest_path.open('x') as stream:
        json.dump(result, stream, sort_keys=True, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps(dict(archive=result['archive'], members=len(selected), source_bytes=result['source_bytes'])))


if __name__ == '__main__':
    main()
