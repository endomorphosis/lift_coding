"""Prepare immutable evidence shards locally; this program has no upload API.

All source reads are no-follow. Content chunks enter public tar/zstd shards only
after an entire regular-file read is stable and its credential scan is clear.
Later source drift is reported separately from that file-specific snapshot.
"""
from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import stat
import subprocess
import tarfile
import tempfile
import time

SCHEMA = 'terminal-codebase-ir-evidence-archive@1'
CHUNK_BYTES = 8 * 1024**2
TAR_BYTES = 252 * 1024**2
MANIFEST_BYTES = 127 * 1024**2
FINAL_TAR_BYTES = 256 * 1024**2
FINAL_MANIFEST_BYTES = 128 * 1024**2
PATTERNS = (
    ('github_classic_token', re.compile(rb'gh[pousr]_[A-Za-z0-9]{36}(?![A-Za-z0-9])')),
    ('github_fine_grained_token', re.compile(rb'github_pat_[A-Za-z0-9_]{22,255}(?![A-Za-z0-9_])')),
    ('huggingface_token', re.compile(rb'hf_[A-Za-z0-9]{30,100}(?![A-Za-z0-9])')),
    ('private_key_pem', re.compile(rb'-----BEGIN (?:RSA |EC |DSA |OPENSSH |ENCRYPTED )?PRIVATE KEY-----')),
)


def wire(value):
    # ASCII escaping preserves POSIX surrogate-escaped names without decoding
    # arbitrary source bytes as UTF-8. Public payload bodies remain opaque.
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True,
                      allow_nan=False).encode('ascii')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save(path, value):
    raw = wire(value) + b'\n'
    with path.open('xb') as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    return {'path': str(path), 'bytes': len(raw), 'sha256': sha(raw)}


def signature(value):
    return {key: getattr(value, 'st_' + key) for key in
            ('dev', 'ino', 'mode', 'nlink', 'uid', 'gid', 'size', 'mtime_ns', 'ctime_ns', 'rdev')}


def kind(mode):
    return ('regular' if stat.S_ISREG(mode) else 'directory' if stat.S_ISDIR(mode)
            else 'symlink' if stat.S_ISLNK(mode) else 'socket' if stat.S_ISSOCK(mode)
            else 'fifo' if stat.S_ISFIFO(mode) else 'character_device' if stat.S_ISCHR(mode)
            else 'block_device' if stat.S_ISBLK(mode) else 'other')


def container_format(prefix):
    for name, magic in (('gzip', b'\x1f\x8b'), ('zip', b'PK\x03\x04'),
                        ('xz', b'\xfd7zXZ\x00'), ('zstd', b'\x28\xb5\x2f\xfd'),
                        ('bzip2', b'BZh'), ('7zip', b'7z\xbc\xaf\x27\x1c'), ('rar', b'Rar!')):
        if prefix.startswith(magic): return name
    return 'tar' if len(prefix) > 262 and prefix[257:262] == b'ustar' else None


def fingerprint(path):
    digest = hashlib.sha256(); count = 0
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode): raise ValueError('regular pinned input required')
        while block := os.read(fd, CHUNK_BYTES): digest.update(block); count += len(block)
        if signature(before) != signature(os.fstat(fd)): raise ValueError('pinned input changed')
    finally:
        os.close(fd)
    return {'path': str(path), 'bytes': count, 'sha256': digest.hexdigest()}


class Scanner:
    def __init__(self):
        self.known = []
        for name in ('GH_TOKEN', 'GITHUB_TOKEN', 'HF_TOKEN', 'HUGGING_FACE_HUB_TOKEN'):
            value = os.environ.get(name, '')
            if len(value) >= 16: self.known.append(value.encode())
        for path in (Path.home() / '.cache/huggingface/token', Path.home() / '.huggingface/token'):
            if path.is_file():
                value = path.read_bytes().strip()
                if 16 <= len(value) <= 4096: self.known.append(value)

    def hits(self, value):
        found = set()
        for label, pattern in PATTERNS:
            found.update((label, sha(match.group())) for match in pattern.finditer(value))
        found.update(('exact_available_credential', sha(token)) for token in self.known if token in value)
        return found


class Zstd:
    def __init__(self, library):
        self.library = fingerprint(library)
        self.lib = ctypes.CDLL(str(library))
        self.lib.ZSTD_compressBound.argtypes = [ctypes.c_size_t]
        self.lib.ZSTD_compressBound.restype = ctypes.c_size_t
        self.lib.ZSTD_compress.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p,
                                        ctypes.c_size_t, ctypes.c_int]
        self.lib.ZSTD_compress.restype = ctypes.c_size_t
        self.lib.ZSTD_isError.argtypes = [ctypes.c_size_t]
        self.lib.ZSTD_isError.restype = ctypes.c_uint

    def compress(self, block):
        source = ctypes.create_string_buffer(block)
        output = ctypes.create_string_buffer(self.lib.ZSTD_compressBound(len(block)))
        count = self.lib.ZSTD_compress(output, len(output), source, len(block), 1)
        if self.lib.ZSTD_isError(count): raise ValueError('zstd chunk compression failed')
        return output.raw[:count]


class Shards:
    def __init__(self, output, zstd, deadline):
        self.output, self.zstd, self.deadline = output, zstd, deadline
        self.archive = None; self.raw = None; self.number = 0; self.used = 0
        self.members = []; self.finished = []

    def finish(self):
        if self.archive is None: return
        self.archive.close(); target = self.output / ('data-%06d.tar.zst' % self.number)
        info = compress_file(self.raw, target, self.zstd, self.deadline, FINAL_TAR_BYTES)
        info.update({'archive': target.name, 'members': len(self.members), 'tar_bytes': self.raw.stat().st_size})
        self.finished.append(info); self.raw.unlink(); self.number += 1
        self.archive = None; self.raw = None; self.used = 0; self.members = []

    def append(self, digest, staged, stored_size, stored_sha):
        padded = 512 + ((stored_size + 511) // 512) * 512
        if self.archive is not None and self.used + padded + 10240 > TAR_BYTES: self.finish()
        if self.archive is None:
            self.raw = self.output / ('data-%06d.tar.partial' % self.number)
            self.archive = tarfile.open(self.raw, mode='x', format=tarfile.USTAR_FORMAT)
        member = 'chunks/' + digest + '.zst'
        info = tarfile.TarInfo(member); info.size = stored_size; info.mode = 0o444
        info.uid = info.gid = info.mtime = 0
        with staged.open('rb') as stream: self.archive.addfile(info, stream)
        self.used += padded; self.members.append(digest)
        return {'archive': 'data-%06d.tar.zst' % self.number, 'member': member,
                'stored_bytes': stored_size, 'stored_sha256': stored_sha, 'codec': 'zstd'}


def compress_file(source, target, executable, deadline, maximum):
    remaining = deadline - time.monotonic()
    if remaining <= 0: raise TimeoutError('archive wall budget exhausted')
    with target.open('xb') as output:
        child = subprocess.Popen([str(executable), '--quiet', '-1', '--threads=1', '--stdout', str(source)],
                                 stdout=output, stderr=subprocess.PIPE, start_new_session=True)
        try:
            _, errors = child.communicate(timeout=min(remaining, 300))
        except BaseException:
            os.killpg(child.pid, 9); child.wait(); raise
    if child.returncode != 0: raise ValueError('zstd archive compression failed')
    if target.stat().st_size > maximum: raise ValueError('compressed shard exceeds publication bound')
    return fingerprint(target)


def jsonl_shards(values, output, prefix, executable, deadline):
    finished = []; stream = None; path = None; size = 0; number = 0
    combined_digest = hashlib.sha256()
    for encoded in values:
        line = encoded.encode('ascii') + b'\n'
        combined_digest.update(line)
        if len(line) > MANIFEST_BYTES: raise ValueError('path record exceeds manifest shard bound')
        if stream is not None and size + len(line) > MANIFEST_BYTES:
            stream.close(); finished.append(compress_file(path, output / (prefix + '-%06d.jsonl.zst' % number),
                executable, deadline, FINAL_MANIFEST_BYTES)); path.unlink(); number += 1; stream = None; size = 0
        if stream is None:
            path = output / (prefix + '-%06d.jsonl.partial' % number); stream = path.open('xb')
        stream.write(line); size += len(line)
    if stream is not None:
        stream.close(); finished.append(compress_file(path, output / (prefix + '-%06d.jsonl.zst' % number),
            executable, deadline, FINAL_MANIFEST_BYTES)); path.unlink()
    return finished, combined_digest.hexdigest()


def selected_nodes(scopes, enumeration_errors):
    for scope in scopes['recursive_roots']:
        origin = Path(scope['root']); pending = [(origin, '')]
        while pending:
            directory, relative = pending.pop()
            yield scope['namespace'], relative, directory, None
            try:
                with os.scandir(directory) as entries:
                    for entry in entries:
                        child = '/'.join(filter(None, (relative, entry.name)))
                        if entry.is_dir(follow_symlinks=False): pending.append((Path(entry.path), child))
                        else: yield scope['namespace'], child, Path(entry.path), None
            except OSError as error:
                enumeration_errors.append({'namespace': scope['namespace'], 'path': relative,
                                           'error_type': type(error).__name__})
    for scope in scopes['selection_manifests']:
        binding = scope['manifest']; origin = Path(scope['root'])
        if fingerprint(Path(binding['path'])) != binding: raise ValueError('selection manifest pin mismatch')
        document = json.loads(Path(binding['path']).read_bytes())
        if document['schema'] != scope['expected_schema']: raise ValueError('selection manifest schema mismatch')
        for field in scope['fields']:
            for item in document[field]:
                relative = item['path'].rstrip('/')
                if not relative or Path(relative).is_absolute() or '..' in Path(relative).parts:
                    raise ValueError('unsafe selected source path')
                source = Path(item[scope['source_path_field']]) if scope.get('source_path_field') else origin / relative
                if not source.is_absolute(): raise ValueError('selected source must be absolute')
                yield scope['namespace'], relative, source, item
    for scope in scopes.get('explicit_paths', []):
        yield scope['namespace'], scope['relative_path'], Path(scope['path']), scope.get('declared_inventory')


def capture_regular(source, db, zstd, shards, stage_root, scanner, deadline, expected=None):
    if source.resolve(strict=True) != source: raise ValueError('source parent symlink is not followed')
    for attempt in range(3):
        if time.monotonic() >= deadline: raise TimeoutError('archive wall budget exhausted')
        staging = None; candidates = {}
        fd = None
        try:
            fd = os.open(source, os.O_RDONLY | os.O_NOFOLLOW); before = os.fstat(fd)
            if not stat.S_ISREG(before.st_mode): raise ValueError('source changed type')
            digest = hashlib.sha256(); count = 0; chunks = []; hits = set(); tail = b''; container = None
            while block := os.read(fd, CHUNK_BYTES):
                if time.monotonic() >= deadline: raise TimeoutError('archive wall budget exhausted')
                if count == 0: container = container_format(block[:512])
                digest.update(block); count += len(block); found = scanner.hits(tail + block); hits.update(found)
                tail = (tail + block)[-4096:]; key = sha(block); chunks.append({'sha256': key, 'bytes': len(block)})
                if not hits and key not in candidates and db.execute('SELECT 1 FROM chunks WHERE sha256=?', (key,)).fetchone() is None:
                    if staging is None: staging = Path(tempfile.mkdtemp(prefix='file-', dir=stage_root))
                    compressed = zstd.compress(block); temporary = staging / (key + '.zst')
                    with temporary.open('xb') as stream: stream.write(compressed)
                    candidates[key] = (temporary, len(compressed), sha(compressed), len(block))
            stable = signature(before) == signature(os.fstat(fd)) == signature(source.lstat()) and count == before.st_size
            if not stable:
                if attempt == 2: return {'status': 'unresolved_unstable_read', 'attempts': 3}, None
                continue
            if expected and (digest.hexdigest() != expected['sha256'] or count != expected['bytes']):
                raise ValueError('selected immutable CAS content pin mismatch')
            value = {'status': 'quarantined_credential_candidate' if hits else 'captured_stable_snapshot',
                     'full_sha256': digest.hexdigest(), 'bytes': count, 'stat': signature(before),
                     'chunk_count': len(chunks), 'chunks': chunks, 'attempts': attempt + 1,
                     'opaque_container_format': container,
                     'nested_container_secret_scan': 'not_performed' if container else 'not_detected_by_magic',
                     'credential_candidates': [{'pattern': label, 'match_sha256': key} for label, key in sorted(hits)]}
            if not hits:
                for key, (temporary, stored_size, stored_sha, raw_size) in candidates.items():
                    location = shards.append(key, temporary, stored_size, stored_sha)
                    db.execute('INSERT INTO chunks VALUES (?,?,?)', (key, raw_size, wire(location).decode()))
            return value, signature(before)
        finally:
            if fd is not None: os.close(fd)
            if staging is not None: shutil.rmtree(staging)


def build(args, output, state, deadline):
    script = fingerprint(Path(__file__).resolve()); scope_binding = fingerprint(args.scopes)
    if script['sha256'] != args.expected_script_sha256 or scope_binding['sha256'] != args.expected_scopes_sha256:
        raise ValueError('external builder/scope pin mismatch')
    scopes = json.loads(args.scopes.read_bytes())
    if scopes['schema'] != 'terminal-ir-publication-scopes@1': raise ValueError('scope schema mismatch')
    for scope in scopes['recursive_roots']:
        origin = Path(scope['root'])
        if not origin.is_absolute() or origin.resolve(strict=True) != origin: raise ValueError('explicit nonsymlink source root required')
        if output == origin or origin in output.parents: raise ValueError('archive output may not be inside a source root')
    strict = scopes.get('strict_pinned_inputs', [])
    if not strict or scopes.get('selected_sealed_and_external_pins_complete') is not True:
        raise ValueError('root-selected sealed and external source pin closure required')
    for binding in strict:
        if fingerprint(Path(binding['path'])) != binding: raise ValueError('strict source pin mismatch')
    state.update({'script': script, 'scopes': scope_binding, 'destination': scopes['destination'],
                  'source_scope_declarations': scopes,
                  'scope_semantics': 'individually stable captured bytes; not an atomic whole-checkout snapshot',
                  'compression_workers_maximum': 1, 'model_training_calls': 0, 'prover_calls': 0, 'remote_mutations': 0})
    zstd_path = Path(args.zstd).resolve(strict=True); library = Path(args.zstd_library).resolve(strict=True)
    state['zstd_executable'] = fingerprint(zstd_path); zstd = Zstd(library); state['zstd_library'] = zstd.library
    public = output / 'public'; public.mkdir(); private = output / 'private'; private.mkdir()
    staging = private / 'staging'; staging.mkdir(); db = sqlite3.connect(private / 'path-index.sqlite')
    db.execute('PRAGMA journal_mode=WAL'); db.execute('PRAGMA synchronous=FULL')
    db.execute('CREATE TABLE nodes(namespace TEXT,relative_path TEXT,source TEXT,captured_stat TEXT,public_record TEXT,status TEXT,private_record TEXT,PRIMARY KEY(namespace,relative_path))')
    db.execute('CREATE TABLE chunks(sha256 TEXT PRIMARY KEY,raw_bytes INTEGER,location TEXT)')
    db.execute('CREATE TABLE final_seen(namespace TEXT,relative_path TEXT,PRIMARY KEY(namespace,relative_path))')
    scanner = Scanner(); shards = Shards(public, zstd_path, deadline); counts = {}; logical_bytes = 0; seen = 0
    first_enumeration_errors = []; final_enumeration_errors = []
    try:
        for namespace, relative, source, declared in selected_nodes(scopes, first_enumeration_errors):
            if time.monotonic() >= deadline: raise TimeoutError('archive wall budget exhausted')
            if db.execute('SELECT 1 FROM nodes WHERE namespace=? AND relative_path=?', (namespace, relative)).fetchone(): continue
            record = {'schema': 'terminal-ir-archived-path@1', 'namespace': namespace, 'path': relative,
                      'declared_inventory': declared, 'first_observed_stat': None}; captured = None
            try:
                info = source.lstat(); record['node_type'] = kind(info.st_mode); record['first_observed_stat'] = signature(info)
                is_admin = any(namespace == item['namespace'] and
                    (relative == item['path_prefix'] or relative.startswith(item['path_prefix'] + '/'))
                    for item in scopes.get('publication_administration', []))
                if is_admin:
                    captured = signature(info); record['status'] = 'publication_administration_metadata_only'
                elif stat.S_ISREG(info.st_mode):
                    expected = ({'sha256': declared['sha256'], 'bytes': declared['bytes']}
                                if declared and 'captured_object_path' in declared else None)
                    captured, signature_value = capture_regular(source, db, zstd, shards, staging, scanner, deadline, expected)
                    record.update(captured); captured = signature_value; logical_bytes += record.get('bytes', 0)
                elif stat.S_ISLNK(info.st_mode):
                    target = os.readlink(source); hits = scanner.hits(os.fsencode(target)); captured = signature(info)
                    record.update({'status': 'quarantined_link_credential_candidate' if hits else 'captured_link_metadata',
                                   'target': None if hits else target, 'target_sha256': sha(os.fsencode(target)),
                                   'target_bytes': len(os.fsencode(target))})
                else:
                    captured = signature(info); record['status'] = 'captured_directory_metadata' if stat.S_ISDIR(info.st_mode) else 'captured_special_metadata_only'
            except (FileNotFoundError, PermissionError, ValueError, OSError) as error:
                record.update({'status': 'unresolved_source_read', 'error_type': type(error).__name__})
            private_record = wire(record).decode(); metadata_hits = scanner.hits(wire(record))
            if metadata_hits:
                record = {'schema': 'terminal-ir-archived-path@1', 'namespace': namespace,
                    'path_sha256': sha(os.fsencode(relative)), 'node_type': record.get('node_type'),
                    'status': 'quarantined_metadata_credential_candidate',
                    'original_status': record['status'], 'bytes': record.get('bytes'),
                    'full_sha256': record.get('full_sha256'),
                    'credential_candidates': [{'pattern': label, 'match_sha256': key} for label,key in sorted(metadata_hits)]}
            status = record['status']; counts[status] = counts.get(status, 0) + 1
            db.execute('INSERT INTO nodes VALUES (?,?,?,?,?,?,?)', (namespace, relative, str(source),
                       wire(captured).decode() if captured is not None else None, wire(record).decode(), status, private_record))
            seen += 1
            if seen % 1000 == 0: db.commit()
            if seen % 25000 == 0: print(json.dumps({'progress_nodes': seen, 'logical_captured_bytes': logical_bytes, 'status_counts': counts}), flush=True)
        db.commit(); shards.finish()
        drift_count = 0
        drift_path = private / 'later-drift.jsonl'
        with drift_path.open('xb') as drift:
            for namespace, relative, source, _ in selected_nodes(scopes, final_enumeration_errors):
                if time.monotonic() >= deadline: raise TimeoutError('archive wall budget exhausted')
                previous = db.execute('SELECT captured_stat FROM nodes WHERE namespace=? AND relative_path=?', (namespace, relative)).fetchone()
                fresh = db.execute('INSERT OR IGNORE INTO final_seen VALUES (?,?)', (namespace, relative))
                if fresh.rowcount == 0: continue
                try: current = signature(source.lstat())
                except OSError: current = None
                reason = ('added_after_capture' if previous is None else 'deleted_after_capture'
                          if current is None and previous[0] is not None else 'changed_after_capture'
                          if previous[0] is not None and wire(current).decode() != previous[0] else None)
                if reason: drift.write(wire({'namespace': namespace, 'path': relative, 'reason': reason}) + b'\n'); drift_count += bool(reason)
            for namespace, relative in db.execute('SELECT namespace,relative_path FROM nodes EXCEPT SELECT namespace,relative_path FROM final_seen'):
                drift.write(wire({'namespace': namespace, 'path': relative, 'reason': 'deleted_after_capture'}) + b'\n'); drift_count += 1
        db.commit()
        for binding in strict:
            if fingerprint(Path(binding['path'])) != binding: raise ValueError('strict sealed/external input changed')
        if fingerprint(args.scopes) != scope_binding or fingerprint(Path(__file__).resolve()) != script:
            raise ValueError('builder/scope custody drift')
        if fingerprint(zstd_path) != state['zstd_executable'] or fingerprint(library) != state['zstd_library']:
            raise ValueError('compression tool custody drift')
        paths, path_root = jsonl_shards((row[0] for row in db.execute(
            'SELECT public_record FROM nodes ORDER BY namespace,relative_path')), public, 'paths', zstd_path, deadline)
        chunks, chunk_root = jsonl_shards((wire({'sha256': digest, 'raw_bytes': size, **json.loads(location)}).decode()
            for digest,size,location in db.execute('SELECT sha256,raw_bytes,location FROM chunks ORDER BY sha256')),
            public, 'chunks', zstd_path, deadline)
        state.update({'node_count': seen, 'status_counts': counts, 'logical_captured_bytes': logical_bytes,
                      'unique_chunks': db.execute('SELECT count(*) FROM chunks').fetchone()[0],
                      'unique_raw_chunk_bytes': db.execute('SELECT coalesce(sum(raw_bytes),0) FROM chunks').fetchone()[0],
                      'later_source_drift_count': drift_count, 'later_source_drift': fingerprint(drift_path),
                      'strict_pinned_inputs_rechecked': len(strict), 'data_shards': shards.finished,
                      'path_manifest_shards': paths, 'path_jsonl_sha256': path_root,
                      'chunk_index_shards': chunks, 'chunk_jsonl_sha256': chunk_root,
                      'first_enumeration_errors': first_enumeration_errors,
                      'final_enumeration_errors': final_enumeration_errors,
                      'credential_classification_required': any(k.startswith('quarantined') for k in counts),
                      'unresolved_source_nodes': sum(n for k,n in counts.items() if k.startswith('unresolved')),
                      'source_snapshot_atomic': False, 'runtime_special_nodes_reconstructed': False,
                      'proof_authority': False, 'execution_authority': False, 'completion_authority': False,
                      'model_dimension_claimed': False, 'semantic_equivalence_proved': False,
                      'credential_scan_scope': 'raw regular file streams, available exact credential values, symlink/index metadata; not recursively decoded container contents',
                      'nested_container_secret_scan_complete': False,
                      'public_upload_performed': False, 'public_upload_qualified': False,
                      'status': 'prepared_local_shards_requires_root_review'})
        save(public / 'archive-manifest.json', state)
    finally:
        if shards.archive is not None: shards.archive.close()
        db.commit(); db.close()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--scopes', type=Path, required=True); p.add_argument('--output', type=Path, required=True)
    p.add_argument('--expected-script-sha256', required=True); p.add_argument('--expected-scopes-sha256', required=True)
    p.add_argument('--wall-seconds', type=float, default=7200)
    p.add_argument('--zstd', default='/usr/bin/zstd')
    p.add_argument('--zstd-library', default='/lib/aarch64-linux-gnu/libzstd.so.1')
    args = p.parse_args(); start = time.monotonic(); output = args.output.resolve(); output.mkdir(parents=True, exist_ok=False)
    state = {'schema': SCHEMA, 'started_wall_time': time.time(), 'wall_seconds_budget': args.wall_seconds,
             'status': 'running', 'primary_error_type': None}
    save(output / 'invocation.json', {'schema': 'terminal-ir-archive-invocation@1', 'script': str(Path(__file__).resolve()),
        'source_scopes': str(args.scopes), 'expected_script_sha256': args.expected_script_sha256,
        'expected_scopes_sha256': args.expected_scopes_sha256, 'output': str(output),
        'wall_seconds': args.wall_seconds, 'remote_mutation_authorized_by_builder': False})
    save(output / 'started.json', state)
    try:
        build(args, output, state, start + args.wall_seconds)
    except BaseException as error:
        state.update({'status': 'failed_preserved_partial', 'primary_error_type': type(error).__name__})
        raise
    finally:
        state['elapsed_seconds'] = time.monotonic() - start
        save(output / 'closed.json', state)
    print(json.dumps({'status': state['status'], 'nodes': state['node_count'],
                      'unresolved': state['unresolved_source_nodes'], 'credential_review': state['credential_classification_required']}))


if __name__ == '__main__':
    main()
