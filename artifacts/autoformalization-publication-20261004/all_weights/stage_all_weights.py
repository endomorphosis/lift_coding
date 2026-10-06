"""Stage pinned local model weights without loading models or contacting a service."""

from __future__ import annotations

import argparse
import contextlib
import gzip
import hashlib
import json
import math
import os
import stat
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
REPO = 'Publicus/legal-ir-autoencoder'
PREFIX = 'releases/20261005-all-project-weights-v1'
CHUNK = 1024 * 1024
MASKS = {'qualified': False, 'source_fidelity_established': False,
         'proof_authority': False, 'semantic_gold_created': False}


class StagingIntegrityError(ValueError):
    """A local integrity failure with a bounded explanation."""


def require(value, message):
    if not value:
        raise StagingIntegrityError(message)


def raw(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def sealed(value):
    value = dict(value)
    require('content_sha256' not in value, 'seal already present')
    value['content_sha256'] = hashlib.sha256(raw(value)).hexdigest()
    return value


def binding(path):
    path = Path(path).absolute()
    digest = hashlib.sha256()
    count = 0
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(CHUNK), b''):
            count += len(chunk)
            digest.update(chunk)
    return {'path': str(path), 'bytes': count, 'sha256': digest.hexdigest()}


def fingerprint(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


@contextlib.contextmanager
def checked_source(selected):
    path = Path(selected['path'])
    require(path.is_absolute() and not any(p.is_symlink() for p in (path, *path.parents)),
            'absolute ordinary nonsymlink selected source required')
    require(type(selected['bytes']) is int and selected['bytes'] >= 0,
            'exact selected source byte count required')
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(descriptor, 'rb') as stream:
        before = os.fstat(stream.fileno())
        require(stat.S_ISREG(before.st_mode) and before.st_size == selected['bytes'],
                'selected source type or size differs')
        if 'inode' in selected:
            selected_inode = selected['inode']
            if isinstance(selected_inode, dict):
                require(set(selected_inode) == {'device', 'inode'}
                        and before.st_dev == selected_inode['device']
                        and before.st_ino == selected_inode['inode'], 'selected source device or inode differs')
            else:
                require(type(selected_inode) is int and before.st_ino == selected_inode,
                        'selected source inode differs')
        digest = hashlib.sha256()
        count = 0
        for chunk in iter(lambda: stream.read(CHUNK), b''):
            count += len(chunk)
            require(count <= selected['bytes'], 'selected source exceeded bound')
            digest.update(chunk)
        require(count == selected['bytes'] and digest.hexdigest() == selected['sha256'],
                'selected source SHA differs')
        require(fingerprint(before) == fingerprint(os.fstat(stream.fileno())),
                'selected source changed during initial verification')
        stream.seek(0)
        yield stream
        require(fingerprint(before) == fingerprint(os.fstat(stream.fileno()))
                == fingerprint(path.stat(follow_symlinks=False)),
                'selected source changed during preparation')
        stream.seek(0)
        after_digest = hashlib.sha256()
        after_count = 0
        for chunk in iter(lambda: stream.read(CHUNK), b''):
            after_count += len(chunk)
            require(after_count <= selected['bytes'], 'selected source exceeded final bound')
            after_digest.update(chunk)
        require(after_count == selected['bytes'] and after_digest.hexdigest() == selected['sha256']
                and fingerprint(before) == fingerprint(os.fstat(stream.fileno()))
                == fingerprint(path.stat(follow_symlinks=False)),
                'selected original source bytes changed')


def unique_object(pairs):
    output = {}
    for key, value in pairs:
        require(key not in output, 'duplicate JSON key rejected')
        output[key] = value
    return output


def reject_constant(_value):
    raise StagingIntegrityError('nonfinite JSON constant rejected')


def parse_json(data):
    return json.loads(data, object_pairs_hook=unique_object, parse_constant=reject_constant)


def load_pinned(path, digest, maximum=128 * CHUNK):
    selected = {'path': str(Path(path).absolute()), 'bytes': Path(path).stat().st_size, 'sha256': digest}
    require(selected['bytes'] <= maximum, 'bounded metadata input required')
    with checked_source(selected) as stream:
        value = parse_json(stream.read())
    require(isinstance(value, dict) and 'content_sha256' in value, 'sealed metadata input required')
    body = {key: item for key, item in value.items() if key != 'content_sha256'}
    require(hashlib.sha256(raw(body)).hexdigest() == value['content_sha256'], 'metadata content seal differs')
    return selected, value


def public_alias(path):
    path = Path(path)
    require(path.is_absolute(), 'absolute source alias required')
    try:
        alias = str(path.relative_to(ROOT))
    except ValueError:
        raise StagingIntegrityError('selected source outside project root') from None
    require(alias and '..' not in Path(alias).parts, 'safe project relative source alias required')
    return alias


def selected_binding(row):
    return {key: row[key] for key in ('path', 'bytes', 'sha256')}


def state_pointer(value, pointer):
    require(type(pointer) is str and (pointer == '' or pointer.startswith('/')), 'RFC6901 state pointer required')
    current = value
    if pointer == '':
        return current
    for encoded in pointer[1:].split('/'):
        require('~' not in encoded.replace('~0', '').replace('~1', ''), 'invalid state pointer escape')
        key = encoded.replace('~1', '/').replace('~0', '~')
        if isinstance(current, list):
            require(key.isdigit() and (key == '0' or not key.startswith('0')), 'canonical array state pointer required')
            position = int(key)
            require(position < len(current), 'array state pointer missing')
            current = current[position]
        else:
            require(isinstance(current, dict) and key in current, 'object state pointer missing')
            current = current[key]
    return current


def numeric_leaf_count(value):
    if type(value) in (int, float):
        require(type(value) is int or math.isfinite(value), 'nonfinite state tensor value rejected')
        return 1
    if isinstance(value, dict):
        return sum(numeric_leaf_count(item) for item in value.values())
    if isinstance(value, list):
        return sum(numeric_leaf_count(item) for item in value)
    require(value is None or type(value) in (str, bool), 'ordinary JSON state values required')
    return 0


def state_metadata(row):
    fields = ('json_pointer', 'key', 'numeric_leaf_count', 'canonical_json_sha256',
              'canonical_json_bytes', 'optimizer_only', 'state_parameter_key_count')
    result = {key: row[key] for key in fields if key in row}
    if 'state_parameter_keys' in row:
        value = row['state_parameter_keys']
        result['state_parameter_key_count'] = len(value) if isinstance(value, list) else value
    return result


def verify_state(document, descriptor):
    value = state_pointer(document, descriptor['json_pointer'])
    data = raw(value)
    count = numeric_leaf_count(value)
    require(count == descriptor['numeric_leaf_count'] and count > 0, 'declared state numeric count differs')
    require(len(data) == descriptor['canonical_json_bytes']
            and hashlib.sha256(data).hexdigest() == descriptor['canonical_json_sha256'],
            'declared state canonical digest differs')
    return value


def write_bytes(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, 'wb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    return binding(path)


def write_json(path, value):
    return write_bytes(path, raw(sealed(value)) + b'\n')


def verify_gzip(path, expected_bytes, expected_sha256):
    count = 0
    digest = hashlib.sha256()
    with gzip.open(path, 'rb') as stream:
        for chunk in iter(lambda: stream.read(CHUNK), b''):
            count += len(chunk)
            require(count <= expected_bytes, 'gzip roundtrip exceeds uncompressed bound')
            digest.update(chunk)
    require(count == expected_bytes and digest.hexdigest() == expected_sha256,
            'gzip roundtrip differs from selected payload')


def gzip_stream(path, stream, expected_bytes, expected_sha256):
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, 'wb') as target:
        with gzip.GzipFile(filename='', mode='wb', fileobj=target, mtime=0, compresslevel=1) as compressed:
            for chunk in iter(lambda: stream.read(CHUNK), b''):
                compressed.write(chunk)
        target.flush()
        os.fsync(target.fileno())
    verify_gzip(path, expected_bytes, expected_sha256)
    return binding(path)


def gzip_bytes(path, data):
    import io
    return gzip_stream(path, io.BytesIO(data), len(data), hashlib.sha256(data).hexdigest())


def verified_remote_index(coverage, verification):
    require(coverage['schema'] == 'all-project-model-weights-prior-publication-coverage/v1',
            'prior coverage schema differs')
    require(verification['schema'] == 'all-project-model-weights-prior-remote-verification/v1'
            and verification['status'] == 'all_prior_release_files_verified_unchanged_at_current_snapshot'
            and verification['all_prior_release_files_verified'] is True
            and verification['all_current_release_paths_preserved_exact_content'] is True,
            'complete prior remote verification required')
    expected = {(row['repo_id'], row['repo_type'], row['revision'], row['path_in_repository']): row
                for row in coverage['remote_file_references']}
    actual = {}
    for row in verification['remote_files']:
        key = (row['repo_id'], 'model', row['immutable_revision'], row['path_in_repository'])
        require(key not in actual and row['current_contents_unchanged'] is True, 'remote verification identity differs')
        actual[key] = row
    require(set(actual) == set(expected), 'prior remote complete inventory join differs')
    index = {}
    for key, row in expected.items():
        observed = actual[key]
        require(row['bytes'] == observed['bytes'] and row['sha256'] == observed['sha256'],
                'prior remote size or SHA join differs')
        reference = {field: row[field] for field in ('repo_id', 'repo_type', 'revision', 'path_in_repository', 'bytes', 'sha256')}
        index.setdefault((row['sha256'], row['bytes']), []).append(reference)
    for references in index.values():
        references.sort(key=lambda item: (item['repo_id'] != REPO, item['repo_id'], item['revision'], item['path_in_repository']))
    return index


def group_weights(weights):
    require(isinstance(weights, list) and weights, 'nonempty complete model weight inventory required')
    groups = {}
    sources = {}
    for row in weights:
        require(row['format'] in ('JSON', 'safetensors'), 'unsupported selected weight format')
        source = selected_binding(row)
        public_alias(source['path'])
        require(source['path'] not in sources or sources[source['path']] == source, 'source path binding conflict')
        sources[source['path']] = source
        groups.setdefault((row['sha256'], row['bytes'], row['format']), []).append(row)
    return sorted(groups.values(), key=lambda rows: (rows[0]['sha256'], rows[0]['bytes'], rows[0]['format'])), sources


def merged_descriptors(rows):
    descriptors = {}
    for row in rows:
        require(isinstance(row.get('json_states', []), list), 'declared state list required')
        for descriptor in row.get('json_states', []):
            pointer = descriptor['json_pointer']
            public = state_metadata(descriptor)
            if pointer in descriptors:
                require(state_metadata(descriptors[pointer]) == public, 'identical source state descriptor conflict')
            descriptors[pointer] = descriptor
    return [descriptors[key] for key in sorted(descriptors)]


def prepare_group(rows, remote_index, directory):
    first = rows[0]
    descriptors = merged_descriptors(rows)
    embedded = any(row.get('embedded_in_report') is True for row in rows)
    require(first['format'] != 'JSON' or descriptors, 'JSON weight container without declared states')
    require(not embedded or all(item['json_pointer'] for item in descriptors),
            'mixed report root state cannot be published')
    record = {'source_bytes': first['bytes'], 'source_sha256': first['sha256'], 'format': first['format'],
              'aliases': sorted({public_alias(row['path']) for row in rows}),
              'families': sorted({row['family'] for row in rows}),
              'source_schemas': sorted({str(row.get('schema')) for row in rows}),
              'states': [state_metadata(item) for item in descriptors],
              'embedded_in_report': embedded, **MASKS}
    selected = selected_binding(first)
    source_references = remote_index.get((first['sha256'], first['bytes']), [])
    with checked_source(first) as stream:
        if source_references:
            record['storage'] = {'kind': 'existing_verified_immutable_HF_file', 'references': source_references}
        elif first['format'] == 'JSON' and embedded:
            document = parse_json(stream.read())
            state_records = []
            for descriptor in descriptors:
                state_records.append({'metadata': state_metadata(descriptor), 'value': verify_state(document, descriptor)})
            capsule = sealed({'schema': 'all-project-model-weights-state-capsule/v1',
                              'source_sha256': first['sha256'], 'source_bytes': first['bytes'],
                              'states': state_records, **MASKS})
            data = raw(capsule) + b'\n'
            relative = f'weights/{first["sha256"]}.weights-only.json.gz'
            staged = gzip_bytes(directory / relative, data)
            restored = parse_json(gzip.decompress((directory / relative).read_bytes()))
            require(restored == capsule, 'state capsule roundtrip differs')
            for item, descriptor in zip(restored['states'], descriptors, strict=True):
                require(item['metadata'] == state_metadata(descriptor)
                        and raw(item['value']) == raw(state_pointer(document, descriptor['json_pointer'])),
                        'state capsule saved state differs')
            record['storage'] = {'kind': 'new_weights_only_JSON_capsule_gzip', 'path': relative,
                                 'bytes': staged['bytes'], 'sha256': staged['sha256'],
                                 'uncompressed_bytes': len(data), 'uncompressed_sha256': hashlib.sha256(data).hexdigest()}
        elif first['format'] == 'JSON':
            relative = f'weights/{first["sha256"]}.json.gz'
            staged = gzip_stream(directory / relative, stream, first['bytes'], first['sha256'])
            record['storage'] = {'kind': 'new_byte_exact_JSON_gzip', 'path': relative,
                                 'bytes': staged['bytes'], 'sha256': staged['sha256'],
                                 'uncompressed_bytes': first['bytes'], 'uncompressed_sha256': first['sha256']}
        else:
            relative = f'weights/{first["sha256"]}.safetensors'
            target = directory / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            with os.fdopen(descriptor, 'wb') as output:
                for chunk in iter(lambda: stream.read(CHUNK), b''):
                    output.write(chunk)
                output.flush()
                os.fsync(output.fileno())
            staged = binding(target)
            require(staged['bytes'] == first['bytes'] and staged['sha256'] == first['sha256'],
                    'binary tensor byte-exact copy differs')
            record['storage'] = {'kind': 'new_byte_exact_safetensors', 'path': relative,
                                 'bytes': staged['bytes'], 'sha256': staged['sha256']}
    for row in rows[1:]:
        with checked_source(row):
            pass
    require(selected_binding(first) == selected, 'source descriptor changed')
    return record


def prepare_sidecars(weights, remote_index, directory):
    weight_sources = {row['path']: selected_binding(row) for row in weights}
    sources = {}
    associations = {}
    for row in weights:
        sidecar = row.get('metadata_sidecar')
        if sidecar:
            require(row['format'] == 'safetensors', 'metadata sidecar selected for nonbinary weight')
            selected = selected_binding(sidecar)
            require(selected['path'] not in sources or sources[selected['path']] == selected,
                    'checkpoint sidecar binding conflict')
            sources[selected['path']] = selected
            associations.setdefault((selected['sha256'], selected['bytes']), {'bindings': [], 'weights': []})
            group_bindings = associations[(selected['sha256'], selected['bytes'])]['bindings']
            if selected not in group_bindings:
                group_bindings.append(selected)
            associations[(selected['sha256'], selected['bytes'])]['weights'].append(selected_binding(row))
    records = []
    for (digest, size), group in sorted(associations.items()):
        first = group['bindings'][0]
        references = remote_index.get((digest, size), [])
        record = {'source_bytes': size, 'source_sha256': digest,
                  'aliases': sorted({public_alias(item['path']) for item in group['bindings']}),
                  'associated_weight_sha256s': sorted({item['sha256'] for item in group['weights']})}
        with checked_source(first) as stream:
            require(size <= 4 * CHUNK, 'bounded checkpoint metadata sidecar required')
            source_data = stream.read()
            source = parse_json(source_data)
            require(isinstance(source, dict) and source.get('schema') == 'source-vector-reconstruction-checkpoint/v1',
                    'explicit source-vector checkpoint metadata schema required')
            expected_sidecar_keys = {'schema', 'config', 'normalization', 'model_file', 'optimizer_file',
                                    'model_state_sha256', 'optimizer_state_sha256', 'optimizer_steps',
                                    'parent_checkpoint_sha256', 'masks', 'qualified', 'source_fidelity_established',
                                    'proof_authority', 'contrastive_fit_authorized', 'semantic_fit_authorized',
                                    'reconstruction_fit_scope', 'content_sha256'}
            require(set(source) <= expected_sidecar_keys, 'checkpoint metadata contains unselected fields')
            dependencies = []
            for selected in group['bindings']:
                for role in ('model_file', 'optimizer_file'):
                    item = source.get(role)
                    require(isinstance(item, dict) and set(item) == {'path', 'bytes', 'sha256'},
                            'closed checkpoint weight dependency required')
                    dependency_path = Path(item['path'])
                    if not dependency_path.is_absolute():
                        require('..' not in dependency_path.parts, 'checkpoint dependency traversal rejected')
                        dependency_path = Path(selected['path']).parent / dependency_path
                    expected = {'path': str(dependency_path), 'bytes': item['bytes'], 'sha256': item['sha256']}
                    require(weight_sources.get(str(dependency_path)) == expected,
                            'checkpoint metadata dependency absent from complete weight inventory')
                    dependencies.append({'sidecar_alias': public_alias(selected['path']), 'role': role,
                                         'weight_alias': public_alias(dependency_path),
                                         'bytes': item['bytes'], 'sha256': item['sha256']})
            record['weight_dependencies'] = sorted(dependencies, key=lambda item: (item['sidecar_alias'], item['role']))
            if references:
                record['storage'] = {'kind': 'existing_verified_immutable_HF_file', 'references': references}
            else:
                relative = f'metadata/{digest}.checkpoint.json.gz'
                staged = gzip_bytes(directory / relative, source_data)
                record['storage'] = {'kind': 'new_byte_exact_checkpoint_metadata_gzip', 'path': relative,
                                     'bytes': staged['bytes'], 'sha256': staged['sha256'],
                                     'uncompressed_bytes': size, 'uncompressed_sha256': digest}
        for selected in group['bindings'][1:]:
            with checked_source(selected):
                pass
        records.append(record)
    return records, sources


def public_file_bindings(directory):
    output = []
    for path in sorted(directory.rglob('*')):
        if path.is_file():
            selected = binding(path)
            selected['path'] = str(path.relative_to(directory))
            output.append(selected)
    return output


def deduplicate_original_bindings(originals):
    representatives = {}
    for source in sorted(originals.values(), key=lambda item: item['path']):
        representatives.setdefault((source['sha256'], source['bytes']), source)
    return sorted(representatives.values(), key=lambda item: item['path'])


def stage(arguments):
    inventory_binding, inventory = load_pinned(arguments.inventory, arguments.inventory_sha256)
    coverage_binding, coverage = load_pinned(arguments.coverage, arguments.coverage_sha256)
    verification_binding, verification = load_pinned(arguments.remote_verification, arguments.remote_verification_sha256)
    require(inventory['schema'] == 'all-local-autoformalization-model-weight-inventory/v1', 'weight inventory schema differs')
    require(inventory.get('frozen_for_publication') is True and inventory.get('read_only_originals') is True
            and inventory.get('models_loaded') == 0 and inventory.get('training_executed') is False
            and inventory.get('uploads') == 0, 'frozen read-only no-model inventory required')
    require(inventory['prior_publication_coverage_binding'] == coverage_binding,
            'inventory prior publication coverage binding differs')
    require(verification['coverage_binding'] == coverage_binding, 'remote verification coverage binding differs')
    groups, originals = group_weights(inventory['weights'])
    remote_index = verified_remote_index(coverage, verification)
    output = arguments.output.absolute()
    require(not output.exists() and not any(path.is_symlink() for path in output.parents), 'fresh nonsymlink staging output required')
    output.mkdir(mode=0o700, parents=True)
    release = output / 'release'
    release.mkdir(mode=0o700)
    records = []
    workers = arguments.workers
    require(type(workers) is int and 1 <= workers <= 4, 'one to four preparation workers required')
    with ThreadPoolExecutor(max_workers=workers) as executor:
        pending = [executor.submit(prepare_group, rows, remote_index, release) for rows in groups]
        for completed, future in enumerate(as_completed(pending), start=1):
            records.append(future.result())
            if completed == len(groups) or completed % 25 == 0:
                print(json.dumps({'completed_unique_weight_containers': completed,
                                  'total_unique_weight_containers': len(groups)}, sort_keys=True), flush=True)
    records.sort(key=lambda row: (row['source_sha256'], row['source_bytes'], row['format']))
    sidecars, sidecar_originals = prepare_sidecars(inventory['weights'], remote_index, release)
    for path, item in sidecar_originals.items():
        require(path not in originals or originals[path] == item, 'metadata and weight source binding conflict')
        originals[path] = item
    require(sum(len(row['aliases']) for row in records) == len(originals) - len(set(sidecar_originals) -
            {row['path'] for row in inventory['weights']}), 'all weight source aliases must be retained')
    license_path = ROOT / 'LICENSE'
    license_binding = binding(license_path)
    with checked_source(license_binding) as stream:
        write_bytes(release / 'LICENSE', stream.read())
    license_scope = ('Repository-produced research artifacts retain the repository AGPL-3.0 license scope. '
                     'This release does not relicense upstream spaCy, GTE or Leanstral backbones and does not include their cached weights. '
                     'References to prior immutable public Hugging Face files preserve their recorded licensing and producer scope. '
                     'Kernel ridge support vectors, when inventoried as model parameters, are required numerical inference parameters.\n')
    write_bytes(release / 'LICENSE_SCOPE.txt', license_scope.encode())
    summary = {'schema': 'all-project-model-weights-public-catalog/v1',
               'source_container_count': len(inventory['weights']), 'unique_source_container_count': len(records),
               'unique_source_bytes': sum(row['source_bytes'] for row in records),
               'declared_JSON_state_count': sum(len(row['states']) for row in records),
               'source_aliases_complete': True, 'weight_containers': records, 'checkpoint_metadata_sidecars': sidecars,
               'maximum_preparation_workers': workers, 'gzip_recipe': 'gzip_filename_empty_mtime_0_compresslevel_1',
               'canonical_JSON_state_digest_recipe': 'sorted_compact_UTF8_JSON_ensure_ascii_false_allow_nan_false/v1',
               'original_sources_preserved': True, 'network_calls': 0, 'model_loads': 0, 'training_calls': 0,
               'prover_calls': 0, 'upstream_backbone_weights_included': False, **MASKS}
    catalog_binding = write_json(release / 'catalog.json', summary)
    new_weights = [row for row in records if row['storage']['kind'].startswith('new_')]
    existing_weights = [row for row in records if row['storage']['kind'] == 'existing_verified_immutable_HF_file']
    readme = (f'# Complete inventoried project model weights\n\n'
              f'This append-only research archive catalogs {len(inventory["weights"])} local source containers '
              f'({len(records)} distinct byte contents). It stages {len(new_weights)} previously unindexed containers '
              f'and references {len(existing_weights)} exact byte matches in verified immutable public releases.\n\n'
              'See `catalog.json` for model families, relative source aliases, saved-state digests and storage locations. '
              'Decompress `.json.gz` to recover the exact original clean checkpoint bytes. Mixed reports supply '
              'weights-only capsules whose state values are joined by their original JSON pointers and canonical hashes; '
              'training report bodies are omitted. Binary safetensors files and their clean checkpoint metadata retain '
              'exact bytes. Restore binary model/optimizer/metadata triplets using the catalog dependency aliases and '
              'original owners. Original provider, configuration and receipt availability constraints still apply; '
              'this archive does not promise arbitrary direct loading. Exact archived metadata may retain original '
              'binding paths and hashed training IDs; it contains no raw source or training report bodies.\n\n'
              'Intermediate, optimizer, initial and diagnostic states are archives of saved experiments. '
              'They are unqualified and have no established source fidelity or proof authority. The catalog does not '
              'claim that every checkpoint is a trained, deployable or independently reviewed model. '
              'Upstream spaCy, GTE and Leanstral backbones remain under their upstream distributions. '
              'Kernel ridge support vectors are retained numerical model parameters required for inference.\n')
    write_bytes(release / 'README.md', readme.encode())
    files_before_checksums = public_file_bindings(release)
    checksums = ''.join(f'{row["sha256"]}  {row["path"]}\n' for row in files_before_checksums)
    write_bytes(release / 'SHA256SUMS', checksums.encode())
    files = public_file_bindings(release)
    source_binding = binding(Path(__file__).resolve())
    for item in (inventory_binding, coverage_binding, verification_binding, license_binding, source_binding):
        require(item['path'] not in originals or originals[item['path']] == item, 'original input binding conflict')
        originals[item['path']] = item
    for item in originals.values():
        with checked_source(item):
            pass
    source_alias_bindings = write_json(output / 'source-alias-bindings.json', {
        'schema': 'all-project-model-weights-original-source-alias-bindings/v1',
        'original_sources': [originals[key] for key in sorted(originals)],
        'all_original_source_aliases_checked': True, 'all_original_source_bytes_preserved': True})
    originals[source_alias_bindings['path']] = source_alias_bindings
    publication_originals = [originals[key] for key in sorted(originals)]
    plan = {'schema': 'append-only-HF-publication-plan/v1', 'repo_id': REPO, 'repo_type': 'model',
            'prefix': PREFIX, 'directory': str(release), 'files': files,
            'original_input_bindings': publication_originals,
            'original_source_alias_bindings': source_alias_bindings,
            'create_if_missing': False, **MASKS}
    source_binding_scope = 'all_original_source_aliases_directly_rechecked_by_publisher'
    if len(raw(sealed(plan))) + 1 > 900 * 1024:
        publication_originals = deduplicate_original_bindings(originals)
        plan['original_input_bindings'] = publication_originals
        source_binding_scope = 'one_byte_identical_representative_per_content_all_aliases_bound_and_staging_checked'
    plan['publication_original_input_scope'] = source_binding_scope
    plan_binding = write_json(output / 'publication-plan.json', plan)
    require(plan_binding['bytes'] <= CHUNK, 'publisher plan exceeds retained one MiB bound')
    report = {'schema': 'all-project-model-weights-staging/v1', 'status': 'prepared_and_verified',
              'inventory_binding': inventory_binding, 'coverage_binding': coverage_binding,
              'remote_verification_binding': verification_binding, 'stager_source_binding': source_binding,
              'catalog_binding': catalog_binding, 'publication_plan_binding': plan_binding,
              'selected_file_count': len(files), 'selected_bytes': sum(row['bytes'] for row in files),
              'original_input_count': len(publication_originals), 'original_source_alias_count': len(originals) - 1,
              'original_source_alias_bindings': source_alias_bindings,
              'publication_original_input_scope': source_binding_scope,
              'source_container_count': len(inventory['weights']),
              'unique_source_container_count': len(records), 'new_weight_container_count': len(new_weights),
              'existing_exact_byte_weight_container_count': len(existing_weights),
              'checkpoint_metadata_sidecar_count': len(sidecars),
              'declared_JSON_state_count': summary['declared_JSON_state_count'],
              'all_inventory_source_weights_accounted_for': True,
              'all_original_input_bytes_preserved': True, 'all_gzip_payloads_roundtrip_verified': True,
              'network_calls': 0, 'model_loads': 0, 'training_calls': 0, 'prover_calls': 0,
              'publication_executed': False, **MASKS}
    report_binding = write_json(output / 'staging.json', report)
    print(json.dumps({'staging': report_binding, 'publication_plan': plan_binding,
                      'selected_file_count': len(files), 'selected_bytes': report['selected_bytes']}, sort_keys=True), flush=True)
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('inventory', 'coverage', 'remote-verification'):
        parser.add_argument('--' + name, type=Path, required=True)
        parser.add_argument('--' + name + '-sha256', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--workers', type=int, choices=(1, 2, 3, 4), default=2)
    arguments = parser.parse_args()
    try:
        return stage(arguments)
    except StagingIntegrityError as error:
        print(json.dumps({'status': 'staging_rejected', 'error': str(error)}, sort_keys=True), flush=True)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
