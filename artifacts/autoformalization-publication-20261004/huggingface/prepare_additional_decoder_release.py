"""Prepare an exact six-lineage decoder release; never fit or run a model."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

WORK = Path(__file__).resolve().parent
ROOT = Path('/home/barberb/lift_coding/external/ipfs_datasets')
INVENTORY_SHA = '034e0c4fd1f303dfccfe6766a5c0f95ad11d787d618e345e9b1ff57eab6a0fed'
PREFIX = 'releases/20261004-additional-decoder-cutoff-v1'


def require(value, reason):
    if not value:
        raise ValueError(reason)


def raw(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()


def decode(data):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'duplicate JSON key rejected')
            result[key] = value
        return result
    return json.loads(data.decode('utf-8', 'strict'), object_pairs_hook=pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite JSON rejected')))


def binding(path, data):
    return {'path': str(path), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def read(path, expected=None):
    path = path.absolute()
    require(not any(p.is_symlink() for p in (path, *path.parents)), 'nonsymlink source required')
    require(path.is_file() and 0 < path.stat().st_size <= 32 * 1024 ** 2, 'bounded ordinary source required')
    data = path.read_bytes()
    item = binding(path, data)
    require(expected is None or item['sha256'] == expected, 'externally selected source differs')
    return data, item


def sealed(value):
    value = dict(value)
    value['content_sha256'] = hashlib.sha256(raw(value)).hexdigest()
    return raw(value) + b'\n'


def put(path, data):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    return binding(path, data)


def prepare():
    inventory_data, inventory_binding = read(WORK / 'additional_decoder_cutoff_inventory.json', INVENTORY_SHA)
    inventory = decode(inventory_data)
    require(hashlib.sha256(raw({k: v for k, v in inventory.items() if k != 'content_sha256'})).hexdigest()
            == inventory['content_sha256'], 'inventory seal differs')
    require(inventory['weight_endpoint_count'] == 24 and inventory['historical_completed_optimizer_updates'] == 2040,
            'fixed-cutoff counts differ')
    directory = WORK / 'additional-decoder-cutoff-v1'
    require(not directory.exists(), 'fresh release directory required')
    directory.mkdir(mode=0o700)
    inputs = {inventory_binding['path']: inventory_binding}
    states = []
    sources = []
    capsule_by_sha = {}

    def selected(path, expected=None):
        data, item = read(path, expected)
        inputs[item['path']] = item
        return data

    def publish(relative, data):
        return put(directory / relative, data)

    def source(lineage, key, path, expected):
        data = selected(path, expected)
        require(len(data) <= 2 * 1024 ** 2, 'bounded capsule source required')
        if expected not in capsule_by_sha:
            relative = 'source-capsule/' + expected + '-' + path.name
            publish(relative, data)
            capsule_by_sha[expected] = relative
        sources.append({'lineage': lineage, 'producer_source_key': key, 'path': capsule_by_sha[expected],
                        'bytes': len(data), 'sha256': expected})

    for group in inventory['selected_lineages']:
        summary = decode(selected(Path(group['summary_binding']['path']), group['summary_binding']['sha256']))
        lineage = group['lineage']
        if lineage.startswith('native4096-'):
            parent = ROOT / 'workspace/test-logs' / lineage
            manifest = decode(selected(parent / 'training-manifest.json'))
            for key, expected in manifest['extensions'].items():
                relative = Path(key)
                require(not relative.is_absolute() and '..' not in relative.parts, 'safe historical source path required')
                source(lineage, key, parent / 'experiment-source' / relative, expected)
        else:
            for key, expected in summary['source_dependencies'].items():
                if key.startswith('/'):
                    path = Path(key)
                    require(path.is_relative_to(ROOT), 'source capsule escaped selected repository')
                else:
                    category, relative = key.split(':', 1)
                    require(category in {'dependency', 'extension', 'parent_extension', 'previous_extension'},
                            'known historical source category required')
                    path = WORK / 'formula-sidecars-v1/source-capsule' / category / relative
                source(lineage, key, path, expected)

    for row in inventory['weights']:
        src = row['source_file_binding']
        data = selected(Path(src['path']), src['sha256'])
        value = decode(data)
        if row['checkpoint_extraction_needed']:
            parts = row['model_state_JSON_pointer'].strip('/').split('/')
            payload = value
            for part in parts:
                payload = payload[int(part)] if type(payload) is list else payload[part]
            arm = value if parts == ['model_state'] else value['arms'][int(parts[1])]
            normal = value['fit']['normalization'] if parts == ['model_state'] else arm['normalization']
            normalization = {key: normal[key] for key in ('mean', 'scale', 'statistics_dtype', 'model_dtype', 'source_l1_bound')
                             if key in normal}
            provenance = value['native_provenance']
            retained_provenance = {key: provenance[key] for key in ('dimension', 'profile', 'model_sha256',
                'owner_source_sha256', 'worker_sha256', 'worker_source_sha256', 'receipt_sha256', 'request_sha256')}
            checkpoint = {'schema': 'experimental-native4096-formula-weight-checkpoint/v1',
                'lineage': row['lineage'], 'arm': row['arm'], 'dimension': 4096, 'role': row['role'],
                'model_state': payload, 'weights_sha256': row['weights_sha256'],
                'architecture': {'source_width': 4096, 'hidden_width': len(payload['condition.bias']),
                    'target_embedding_width': len(payload['target_embedding.weight'][0]),
                    'vocabulary_size': len(payload['target_embedding.weight']),
                    'source_projection': 'identity_no_learned_embedding_reconstruction',
                    'source_conditioning': 'hidden_initialization_and_persistent_token_embedding_bias'},
                'codec': value['codec'], 'normalization': normalization,
                'producer_declared_native_provenance': retained_provenance,
                'producer_declared_runtime_tensor_sha256': arm.get('final_tensor_sha256', value.get('fit', {}).get('final_tensor_sha256')),
                'runtime_tensor_digest_independently_recomputed': False,
                'historical_completed_optimizer_steps': row['completed_optimizer_steps'],
                'training_report_file_sha256': src['sha256'], 'model_state_JSON_pointer': row['model_state_JSON_pointer'],
                'learned_embedding_reconstruction': False, 'optimizer_resumable': False,
                'training_report_body_included': False, 'runtime_restore_smoke_executed': False,
                'complete_runtime_or_native_producer_closure_claimed': False,
                'admitted': False, 'qualified': False, 'proof_authority': False,
                'source_semantics_verified': False, 'checkpoint_promoted': False}
            data = sealed(checkpoint)
        else:
            checkpoint = value
        require(hashlib.sha256(raw(checkpoint['model_state'])).hexdigest() == row['weights_sha256'],
                'exact selected weight payload differs')
        relative = f'checkpoints/{row["lineage"]}/{row["arm"]}/{row["role"]}-state.json'
        publish(relative, data)
        states.append({'path': relative, 'lineage': row['lineage'], 'arm': row['arm'], 'dimension': row['dimension'],
                       'role': row['role'], 'weights_sha256': row['weights_sha256'],
                       'extracted_weights_only': row['checkpoint_extraction_needed'],
                       'saved_weight_numeric_leaf_count': row['finite_saved_numerical_leaf_count']})

    license_data = selected(ROOT / 'LICENSE')
    publish('SOURCE_REPOSITORY_LICENSE', license_data)
    publish('LICENSE_SCOPE.md', b'Authorial source/checkpoint assets originate in an AGPL-3.0 repository.\nNo upstream backbone weights are included or relicensed. No new content rights\nor semantic review authority are asserted by this experimental release.\n')
    checker = WORK / 'verify_additional_decoder_release.py'
    publish(checker.name, selected(checker))
    readme = '''---
license: agpl-3.0
tags:
- formal-logic
- experimental-decoder
---

# Additional experimental formula decoders: fixed six-lineage cutoff

This release preserves 24 endpoints from six explicitly selected historical
lineages. It contains six final 4096D source-conditioned formula heads, six 8D
head-rate comparison states, six 8D preconditioning comparison states, and six
selected-parent continuation states at 384D/768D. These are formula decoders;
no learned vector reconstruction autoencoder or embedding backbone is included.

The retained budget is 2,040 historical updates: a 20-update 4096D pilot,
three 200-update conditioning arms, two 200-update balanced-cohort arms, and
six 170-update arms across the other three comparisons. Initial and selected
endpoints do not each inherit the final fit's optimizer age. The two continuation
arms are 384D and 768D. No optimizer moments or exact optimizer resume are supplied.

The 4096D states were extracted from saved report model_state fields, preserving
the exact canonical JSON weight digest. Their compact envelopes retain the
32-token codec, native-input normalization statistics, structural geometry and
producer-declared provenance hashes. Whole training reports, source vectors,
reference banks, generated predictions and update histories are excluded.
The source path is explicitly identity reconstruction; two learned source
paths condition hidden initialization and every token embedding. The declared
native profile is last-pool/L2/single-sequence/512 tokens with layer reclamation.
Serialized hashes do not create a fresh native-owner capability or establish
batch/order/token-policy independence. No Leanstral backbone weights are included.

The remaining 18 checkpoint files are exact saved JSON bytes, including the
architecture, codec and preprocessing metadata. Their source interface requires
the saved transformed vector and explicit clause-context contract; input width
alone does not make checkpoints interchangeable.

## Integrity and restore scope

Download the complete release, select the manifest SHA256 from its publication
receipt, then run:

```sh
python -I -B verify_additional_decoder_release.py --directory . --expected-manifest-sha256 SELECTED_SHA256
```

The checker verifies files, seals, finite JSON weights and canonical weight
digests without an ML import or forward pass. Runtime tensor hashes remain
producer declarations. The capsule retains exact selected producer/dependency
versions, with explicit per-lineage associations in the manifest. It is not an
installable complete native runtime, dependency or private-input closure.
No numerical downloaded-checkpoint restore smoke was executed. Native producer
entry points require live runtime results; archived metadata cannot authorize
those calls. Production-loader compatibility remains unqualified.

These exposed authored diagnostic lineages do not establish fresh-holdout gain,
global logic-family support, authentic semantic-label admission, source fidelity,
proof authority or production qualification. All authority flags remain false.
This cutoff excludes later experiments and makes no claim that it contains all
models that might subsequently become available.
'''
    publish('README.md', readme.encode())
    lineage_rows = []
    for group in inventory['selected_lineages']:
        row = {key: group[key] for key in ('lineage', 'retained_weight_endpoints', 'completed_optimizer_updates')}
        lineage_rows.append(row)
        text = f'# {row["lineage"]}\n\nRetained endpoints: {row["retained_weight_endpoints"]}. Historical completed updates: {row["completed_optimizer_updates"]}.\n\n'
        text += 'Experimental formula decoder; no vector reconstruction, optimizer resume, semantic/proof authority or production qualification is claimed.\n'
        publish('cards/' + row['lineage'] + '.md', text.encode())
    files = []
    for path in sorted(directory.rglob('*')):
        if path.is_file():
            data = path.read_bytes()
            files.append({'path': str(path.relative_to(directory)), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
    public = {'schema': 'additional-experimental-decoder-release/v1', 'repo_id': 'Publicus/legal-ir-autoencoder',
              'prefix': PREFIX, 'lineages': lineage_rows, 'states': states, 'source_capsule': sources,
              'unique_capsule_file_count': len(capsule_by_sha), 'files': files,
              'historical_completed_optimizer_updates': 2040, 'new_optimizer_updates': 0,
              'model_loads': 0, 'model_calls': 0, 'training_executed': False, 'qualified': False,
              'source_fidelity_established': False, 'proof_authority': False, 'semantic_gold_created': False,
              'complete_runtime_or_private_input_closure_claimed': False, 'runtime_tensor_digest_recomputed': False,
              'training_report_bodies_or_reference_banks_uploaded': False}
    manifest_binding = publish('release_manifest.json', sealed(public))
    files.append({'path': 'release_manifest.json', 'bytes': manifest_binding['bytes'], 'sha256': manifest_binding['sha256']})
    for item in list(inputs.values()):
        require(binding(Path(item['path']), selected(Path(item['path']), item['sha256'])) == item, 'source changed during preparation')
    for path in (Path(__file__).resolve(), WORK / 'publish_append_release_v2.py'):
        selected(path)
    plan = {'schema': 'append-only-HF-publication-plan/v1', 'repo_id': 'Publicus/legal-ir-autoencoder',
            'repo_type': 'model', 'prefix': PREFIX, 'directory': str(directory), 'files': files,
            'original_input_bindings': list(inputs.values()), 'public_manifest_binding': manifest_binding,
            'create_if_missing': False, 'tracking_metadata_policy': 'allow_only_exact_selected_path_LFS_additions',
            'new_model_calls': 0, 'new_optimizer_updates': 0, 'qualified': False,
            'source_fidelity_established': False, 'proof_authority': False}
    return put(WORK / 'additional_decoder_publication_plan.json', sealed(plan)), manifest_binding


if __name__ == '__main__':
    plan, manifest = prepare()
    print(json.dumps({'plan': plan, 'manifest': manifest}, sort_keys=True))
