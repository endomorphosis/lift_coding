"""Read a closed derivative and verify its physical chunk exclusion boundary.

This is an independent file reader, not another credential classifier. It checks
the bounded classifier's recorded scope and every published compressed chunk.
It never grants proof or planning authority and never prints payload values.
"""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import tarfile
import time

SAFE = {'scanned_no_named_candidates', 'approved_exact_public_fixture',
        'approved_exact_public_container_provenance'}
REPO = 'Publicus/codebase-ir-proof-index'
PREFIX = 'releases/20261004-terminal-codebase-ir-evidence-v1/archive-payload-v1'


def wire(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=True, allow_nan=False).encode('ascii')


def save(path, value):
    with path.open('xb') as stream:
        stream.write(wire(value) + b'\n'); stream.flush(); os.fsync(stream.fileno())


def pin(path):
    digest = hashlib.sha256(); count = 0
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        first = os.fstat(fd)
        while block := os.read(fd, 8 * 1024**2):
            digest.update(block); count += len(block)
        last = os.fstat(fd)
        fields = ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
        if any(getattr(first, key) != getattr(last, key) for key in fields):
            raise ValueError('review input changed during read')
    finally:
        os.close(fd)
    return {'path': str(path), 'bytes': count, 'sha256': digest.hexdigest()}


def require_pin(binding):
    if pin(Path(binding['path'])) != binding:
        raise ValueError('review input pin mismatch')


class Reader:
    def __init__(self, executable, deadline, output):
        self.executable, self.deadline, self.output = executable, deadline, output
        self.children = []

    def check(self):
        if time.monotonic() > self.deadline:
            raise TimeoutError('independent review wall bound')

    def decoded(self, path):
        self.check()
        errors = (self.output / 'decoder-stderr.log').open('ab')
        child = subprocess.Popen([self.executable, '-dc', '--', str(path)],
                                 stdout=subprocess.PIPE, stderr=errors)
        self.children.append((child, errors))
        return child

    def finish(self, child):
        remaining = max(0.1, self.deadline - time.monotonic())
        if child.wait(timeout=remaining):
            raise ValueError('review zstd decoder failed')

    def lines(self, rows):
        for row in rows:
            require_pin({key: row[key] for key in ('path', 'bytes', 'sha256')})
            child = self.decoded(Path(row['path']))
            while line := child.stdout.readline(4 * 1024**2 + 1):
                self.check()
                if len(line) > 4 * 1024**2:
                    raise ValueError('public index line exceeds reader bound')
                yield line
            self.finish(child)

    def close(self):
        errors = []
        for child, stream in self.children:
            try:
                if child.poll() is None:
                    child.terminate()
                    try: child.wait(timeout=5)
                    except subprocess.TimeoutExpired: child.kill(); child.wait(timeout=5)
                if child.stdout: child.stdout.close()
                stream.close()
            except Exception as problem:
                errors.append(type(problem).__name__)
        return errors


def review(args, state, reader):
    manifest_pin = pin(args.manifest)
    if manifest_pin['sha256'] != args.expected_manifest_sha256:
        raise ValueError('closed manifest pin mismatch')
    manifest = json.loads(args.manifest.read_bytes())
    if manifest['status'] != 'closed_public_derivative_requires_root_classification_review':
        raise ValueError('closed classifier derivative required')
    require_pin(manifest['input_archive_manifest']); require_pin(manifest['approvals'])
    original = json.loads(Path(manifest['input_archive_manifest']['path']).read_bytes())
    approvals = json.loads(Path(manifest['approvals']['path']).read_bytes())
    require_pin(original['zstd_executable'])
    if original['zstd_executable']['path'] != reader.executable:
        raise ValueError('review decoder executable differs from pinned producer')
    if (manifest['source_enumeration_errors'] or original['unresolved_source_nodes'] or
            manifest['unique_files_classified'] <= 0):
        raise ValueError('original capture/classification incomplete')
    for binding in original['source_scope_declarations']['strict_pinned_inputs']:
        require_pin(binding)
    approval_rows = {row['file_sha256']: row for row in approvals['public_fixture_files']}
    database = args.classification_database.resolve(strict=True)
    database_pin = pin(database); expected_classifications = {}
    connection = sqlite3.connect(database.as_uri() + '?mode=ro', uri=True)
    try:
        forbidden = {row[0] for row in connection.execute('SELECT sha256 FROM forbidden')}
        if len(forbidden) != manifest['forbidden_unique_chunks']:
            raise ValueError('forbidden chunk census mismatch')
        counts = Counter(); rows_count = 0
        for digest, record_encoded, encoded in connection.execute('SELECT sha256,record,result FROM files'):
            reader.check(); result = json.loads(encoded); record = json.loads(record_encoded); rows_count += 1
            if digest != result['file_sha256']:
                raise ValueError('classification identity mismatch')
            counts[result['status']] += 1
            expected_classifications[digest] = hashlib.sha256(wire(result)).hexdigest()
            if result['status'] in SAFE:
                if any(chunk['sha256'] in forbidden for chunk in record['chunks']):
                    raise ValueError('safe private file intersects forbidden closure')
            elif any(chunk['sha256'] not in forbidden for chunk in record['chunks']):
                raise ValueError('unsafe private file incompletely excluded')
            hits = result['candidate_hits']
            if result['status'] in SAFE and any(x['pattern'] == 'exact_available_credential' for x in hits):
                raise ValueError('active credential veto violated')
            if result['status'] == 'approved_exact_public_fixture':
                approval = approval_rows.get(digest)
                if (not approval or result['approval'] != approval or result['error'] is not None or
                        {x['match_sha256'] for x in hits} - set(approval['approved_match_sha256'])):
                    raise ValueError('exact public fixture approval mismatch')
        if rows_count != manifest['unique_files_classified'] or dict(counts) != manifest['classification_counts']:
            raise ValueError('classification census mismatch')
    finally:
        connection.close()

    index = {}; chunk_root = hashlib.sha256()
    for line in reader.lines(manifest['chunk_index_shards']):
        chunk_root.update(line); row = json.loads(line); digest = row['sha256']
        if digest in forbidden or digest in index:
            raise ValueError('excluded or duplicate chunk present in public index')
        index[digest] = row
    if chunk_root.hexdigest() != manifest['chunk_jsonl_sha256']:
        raise ValueError('public chunk index root mismatch')

    path_root = hashlib.sha256(); nodes = 0; included = 0; excluded = 0
    captured_bytes = 0; metadata_regular = 0; path_counts = Counter()
    for line in reader.lines(manifest['path_manifest_shards']):
        path_root.update(line); record = json.loads(line); nodes += 1
        if record.get('node_type') != 'regular': continue
        if 'full_sha256' not in record:
            metadata_regular += 1; continue
        classification = record.get('public_classification')
        if not classification or classification['file_sha256'] != record['full_sha256']:
            raise ValueError('public path missing exact classification')
        if hashlib.sha256(wire(classification)).hexdigest() != expected_classifications.get(record['full_sha256']):
            raise ValueError('public classification differs from private closed producer')
        status = classification['status']; path_counts[status] += 1
        if status not in SAFE:
            excluded += 1
            if 'chunks' in record or record['public_original_bytes_included'] is not False:
                raise ValueError('excluded file remains reconstructable')
            continue
        included += 1; captured_bytes += record['bytes']
        chunks = record.get('chunks', [])
        if not record['public_original_bytes_included'] or sum(x['bytes'] for x in chunks) != record['bytes']:
            raise ValueError('included file reconstruction length mismatch')
        for chunk in chunks:
            if chunk['sha256'] in forbidden or chunk['sha256'] not in index:
                raise ValueError('included path references excluded/missing chunk')
            if chunk['bytes'] != index[chunk['sha256']]['raw_bytes']:
                raise ValueError('included path chunk size mismatch')
    if (nodes != manifest['original_selected_nodes_preserved_as_path_metadata'] or
            path_root.hexdigest() != manifest['path_jsonl_sha256'] or
            included + excluded != manifest['captured_regular_snapshot_paths'] or
            metadata_regular != manifest['publication_administration_or_other_regular_metadata_only_paths']):
        raise ValueError('public path census/root mismatch')

    seen = set(); stored_bytes = 0
    for shard in manifest['data_shards']:
        reader.check(); path = Path(shard['source_path']); binding = pin(path)
        if any(binding[key] != shard[key] for key in ('bytes', 'sha256')):
            raise ValueError('public data shard pin mismatch')
        child = reader.decoded(path)
        with tarfile.open(fileobj=child.stdout, mode='r|') as archive:
            for member in archive:
                reader.check()
                if not member.isfile() or not member.name.startswith('chunks/') or not member.name.endswith('.zst'):
                    raise ValueError('unexpected physical data member')
                digest = member.name[len('chunks/'):-len('.zst')]
                if digest in forbidden or digest in seen or digest not in index:
                    raise ValueError('excluded/duplicate/unindexed physical chunk')
                row = index[digest]
                if row['archive'] != shard['archive'] or row['member'] != member.name or row['stored_bytes'] != member.size:
                    raise ValueError('physical chunk location mismatch')
                body = archive.extractfile(member); body_hash = hashlib.sha256(); count = 0
                while block := body.read(8 * 1024**2):
                    reader.check(); body_hash.update(block); count += len(block)
                if count != row['stored_bytes'] or body_hash.hexdigest() != row['stored_sha256']:
                    raise ValueError('physical compressed chunk digest mismatch')
                seen.add(digest); stored_bytes += count
        # Consume tar end padding before closing the decoder's pipe.
        while child.stdout.read(8 * 1024**2): reader.check()
        reader.finish(child)
        if pin(path) != binding: raise ValueError('data shard changed during review')
    if seen != set(index): raise ValueError('public index has nonphysical chunks')
    for binding in original['source_scope_declarations']['strict_pinned_inputs']:
        require_pin(binding)
    require_pin(original['zstd_executable'])
    if pin(database) != database_pin: raise ValueError('closed classification database changed')
    if pin(args.manifest) != manifest_pin: raise ValueError('closed manifest changed')
    state.update({'status': 'PHYSICAL_EXCLUSION_AND_BOUNDED_SCOPE_VERIFIED',
        'archive_manifest': manifest_pin, 'archive_manifest_sha256': manifest_pin['sha256'],
        'classification_approvals': manifest['approvals'], 'classification_counts': dict(counts),
        'closed_classification_database': database_pin,
        'path_classification_counts': dict(path_counts), 'included_captured_file_paths': included,
        'excluded_captured_file_paths': excluded, 'included_logical_file_bytes': captured_bytes,
        'metadata_only_regular_paths': metadata_regular, 'path_nodes_verified': nodes,
        'physical_unique_chunks_verified': len(seen), 'physical_stored_chunk_bytes_hashed': stored_bytes,
        'forbidden_chunks_absent_physically_and_from_indexes': len(forbidden),
        'original_strict_pins_verified_before_and_after': len(original['source_scope_declarations']['strict_pinned_inputs']),
        'credential_classification_complete': True, 'classification_scope':
            'All captured bodies accounted for by the bounded named-pattern decoder; unresolved or unsafe bodies remain explicitly excluded.',
        'unresolved_files_remain_unresolved': manifest['unresolved_unique_files'],
        'quarantine_originals_retained_local': True, 'universal_secret_free_claim': False,
        'raw_chunk_redecode_performed_by_reader': False,
        'original_path_identity_join_independently_replayed': False,
        'path_identity_scope': 'Public index root/census and exact classification joins checked here; original path identities depend on the pinned reviewed classifier.',
        'physical_verification_scope': 'Every stored compressed chunk SHA256/size and placement; raw chunk verification is the pinned classifier producer.',
        'source_atomic': False, 'model_training_calls': 0, 'prover_calls': 0, 'remote_mutations': 0,
        'proof_authority': False, 'repo_id': REPO, 'release_prefix': PREFIX})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('manifest', 'classification-database', 'output'):
        parser.add_argument('--' + name, required=True, type=Path)
    parser.add_argument('--expected-manifest-sha256', required=True)
    parser.add_argument('--wall-seconds', type=float, default=1200)
    args = parser.parse_args(); start = time.monotonic()
    args.output = args.output.resolve(); args.output.mkdir(parents=True, exist_ok=False)
    state = {'schema': 'terminal-ir-independent-public-archive-physical-review@1',
             'status': 'STARTED', 'primary_error_type': None}
    save(args.output / 'started.json', {'script': pin(Path(__file__).resolve()),
        'argv': {key: str(value) if isinstance(value, Path) else value for key, value in vars(args).items()}})
    reader = Reader('/usr/bin/zstd', start + args.wall_seconds, args.output)
    try:
        review(args, state, reader)
    except BaseException as problem:
        state.update({'status': 'FAILED_REVIEW_PRESERVED', 'primary_error_type': type(problem).__name__})
        raise
    finally:
        state['cleanup_errors'] = reader.close(); state['elapsed_seconds'] = time.monotonic() - start
        if state['cleanup_errors']: state['status'] = 'FAILED_REVIEW_CLEANUP_PRESERVED'
        save(args.output / 'review.json', state)
    if state['cleanup_errors']: raise RuntimeError('independent review cleanup failed')
    print(json.dumps({key: state[key] for key in ('status', 'elapsed_seconds', 'included_captured_file_paths', 'excluded_captured_file_paths')}))


if __name__ == '__main__': main()
