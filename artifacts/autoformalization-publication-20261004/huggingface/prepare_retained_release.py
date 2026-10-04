"""Prepare retained authorial checkpoints without importing numerical runtimes."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import stat
from pathlib import Path

ROOT = Path('/home/barberb/lift_coding')
REPO = ROOT / 'external/ipfs_datasets'
WORK = Path(__file__).resolve().parent
CAMPAIGN = ROOT / 'artifacts/autoformalization-alignment-20261003'
PREFIX = 'releases/20261004-autoformalization-lanes-v1'
REPOS = {
    'legal_ir': 'Publicus/legal-ir-autoencoder',
    'intent_ir': 'Publicus/intent-ir-autoencoder',
    'security_ir': 'Publicus/security-ir-autoencoder',
    'ui_ux_ir': 'Publicus/ui-ux-ir-autoencoder',
}
SOURCE384 = {
    'legal_ir': ('6e3f4d731d798aa2732afc37bd74fec34da3267a323844975d2dab78f59f9c61', 614534),
    'intent_ir': ('e8470c66411798f0368755ca379ba4ec8c022595118ed259df6a45b0d8999410', 612649),
    'security_ir': ('cae15b8907664d0ff21f1acfd8f9a7b13657126455847dbc33d839172f4f28cf', 624892),
    'ui_ux_ir': ('e4500483c685b46192ea7994a14d3237d42026f86dfe73723029da20d29b24aa', 611168),
}
LINGUISTIC = {
    'historical_blank_en': {
        'manifest.json': ('b319b73a0d0b1cf3f49a71dab647d1a47183b2dfa201ae791654ac67e3b74610', 5112),
        'core.state.json': ('f91a22f33839dd0e59c635f5f4a5679676124ae5dcae4d04b50ece6083019d1e', 452745),
    },
    'local_en_core_web_sm': {
        'manifest.json': ('d0657114967d2019889d8b39b2581107bd4a3affcd07f2555fe8f73fbe5e9a39', 5241),
        'core.state.json': ('498fa1029c349903a38ca58ef20115a45c3248d2258aaae8a013f69ce2a5ef94', 453998),
    },
}
SPAN_PINS = {
    (1729, 400): ('fd6bd55ba3a7698401c7b8201f8ebe195f364f8295e98a13d833f420c0add2fc', 3433326),
    (1729, 800): ('a6d0c8e1428358be6f5601ff75eb62962611184f4b5cbae1747a31253640ccbe', 3430828),
    (1730, 400): ('6a70108d76a548c04076d3cfb35eaa8e29f1b325ffafdd13a5fb5cf099205a0b', 3432437),
    (1730, 800): ('be269a0b0648063fe14ce0a291c474dd6c3aefbf3465b8adb2573346dc2315ba', 3431987),
    (1731, 400): ('adb17a04854ea865ee0433d75405e15f62c1e7dedd4c60f8c889ed087958a2ef', 3432783),
    (1731, 800): ('ff41c3199ca3b84f10e4d3574103cf01051a42b33639fc50e748f1ae19bea3a0', 3431123),
}
TEACHER = {
    'repo_id': 'justicedao/legal-ir-autoencoder-checkpoints', 'repo_type': 'dataset',
    'revision': '94ca549d102e3e31781370aec1247f91365440eb',
    'path': 'checkpoints/20260630T221836Z/state/legal-ir-autoencoder-canonical.state.json',
    'bytes': 398209746,
    'sha256': '7236de26bd3d7f8414ffa04805f1b6e8a8849f9e0103cec6edb4985b911658be',
    'remote_verification': 'fixed_revision_public_LFS_size_and_sha256_metadata',
    'original_semantic_encoder_provenance': 'unrecorded',
    'copied_into_release': False,
}
FLAGS = {'qualified': False, 'accepted': False, 'source_fidelity_established': False,
         'proof_authority': False, 'semantic_gold_created': False,
         'training_or_evaluation_admission': False}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'),
                       allow_nan=False) + '\n').encode('utf-8')


def read(path, expected=None):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size > 32 * 1024 * 1024:
            raise ValueError(f'unsafe input: {path}')
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            data = stream.read(32 * 1024 * 1024 + 1)
        after = os.fstat(fd)
        if (before.st_ino, before.st_size, before.st_mtime_ns) != (
                after.st_ino, after.st_size, after.st_mtime_ns):
            raise ValueError('input changed while reading')
    finally:
        os.close(fd)
    if expected is not None and (digest(data), len(data)) != expected:
        raise ValueError(f'input pin mismatch: {path}')
    return data


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def ordinary_json(data):
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out:
                raise ValueError('duplicate JSON key')
            out[key] = value
        return out
    value = json.loads(data.decode('utf-8', errors='strict'), object_pairs_hook=pairs,
                       parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite JSON')))
    def check(node, depth=0):
        if depth > 64:
            raise ValueError('JSON nesting too deep')
        if isinstance(node, float) and not math.isfinite(node):
            raise ValueError('nonfinite number')
        if isinstance(node, dict):
            for item in node.values():
                check(item, depth + 1)
        elif isinstance(node, list):
            for item in node:
                check(item, depth + 1)
    check(value)
    return value


def metadata384(checkpoint):
    training = checkpoint['training']
    return {
        'asset_type': 'source384_joint_reconstruction_and_typed_formula_decoder',
        'schema': checkpoint['schema'], 'architecture': checkpoint['architecture'],
        'native_input_width': 384, 'residual_projection_width': 8,
        'residual_requires_original_vector_skip': True,
        'input_normalization': checkpoint['config']['input_normalization'],
        'producer': {k: checkpoint['config']['embedding_provenance'][k]
                     for k in ['model_id', 'revision', 'dimension', 'dtype', 'normalized', 'truncated']},
        'selected_epoch': training['selected_epoch'],
        'selected_optimizer_steps': training['selected_optimizer_steps'],
        'attempted_optimizer_steps': training['optimizer_steps'],
        'selection': training['selection'],
        'implementation': checkpoint['implementation'],
        'optimizer_resume_available': False,
        'current_loader_known_dependency_mismatch': 'ui_ux_ir.decoder changed from retained pin',
        **FLAGS,
    }


CARD384 = """This retained source-vector autoencoder has a 384D input, an 8D learned residual projection, a reconstruction branch, and a GRU typed-formula decoder. The residual uses the original vector as a skip connection; its 8D output is not a complete compressed representation. Training combined reconstruction MSE (weight 0.1) with reference cross-entropy. The input producer was pinned thenlper/gte-small; its normalized source embeddings are supplied separately, with no further checkpoint input normalization. Upstream backbone weights are not included.

The checkpoint includes a fixed, TRAIN-fit target vocabulary and synthetic authored training/selection manifests. Selection used an exposed teacher-forced tuning objective. It does not establish source fidelity, held-out generalization, proof truth, or acceptance. All release authority flags remain false.

Historical load route in a compatible canonical ipfs_datasets installation:
```python
from ipfs_datasets_py.logic.formalization.autoencoder.source_training_v2 import load_checkpoint
runtime = load_checkpoint(checkpoint_path, expected_sha256=checkpoint_sha256, expected_domain=domain_id)
```
The current repository loader rejects a changed ui_ux_ir.decoder implementation pin. The release includes the 14 exact archived owner/dependency files declared by the retained checkpoint, under `source384_code/`; they are a source capsule, not a complete standalone package. Use a compatible historical installation and retain the owner's pin checks. The stdlib integrity route below does not load a numerical model.
"""
CARD8 = """These are two retained 8D spaCy linguistic sparse-autoencoder training bundles after two epochs. The historical_blank_en profile uses a blank English pipeline with a sentencizer; local_en_core_web_sm uses the local spaCy 3.8.0 English model with spaCy 3.8.14. The states contain learned categorical feature/family/semantic-slot heads. Their vector embedding-weight tables and memorized decoded-vector table are empty. These states are not learned dense reconstruction bottlenecks and contain no independent learned formula head. The upstream English language-model assets are not copied.

The original operational study checked checkpoint, fresh reload and deterministic training continuation. Those checks do not establish semantic fidelity or independent formula generation. The separately referenced historical 398MB teacher has unrecorded original encoder provenance; it is not represented as a proven spaCy-produced teacher.

Historical load route in a compatible canonical installation with the indicated local spaCy backend:
```python
from ipfs_datasets_py.optimizers.logic_theorem_optimizer.autoencoder_lineages.legacy_v1.linguistic import load_training_checkpoint
model = load_training_checkpoint(checkpoint_directory)
```
The loader validates the bundle, backend and frozen source identity. The release carries selected pinned linguistic/numerical source files under `legacy8_code/`; it is not a complete standalone package or an automatic spaCy model installer.
"""
CARD768 = """These six retained JSON checkpoints are 768D-conditioned source-span decoders: selected update 400 and final update 800 for seeds 1729, 1730 and 1731. Their byte-token bidirectional GRU extracts exact spans and uses a 768D FiLM conditioning adapter. They do not reconstruct embedding vectors and are not a 768D reconstruction autoencoder or an embedding-only decoder. Their narrow grammar describes one canonical deontic rule; arbitrary multi-rule source coverage is not established.

The separately supplied conditioning profile is Alibaba-NLP/gte-multilingual-base@9bbca17d9273fd0d03d5725c7a4b0f6b45142062 with remote code Alibaba-NLP/new-impl@40ced75c3017eb27626c9d4ea981bde21a2662f4, CLS pooling, L2 normalization, float32 CPU, max 8192 tokens with overlength rejection. Neither Alibaba backbone weights nor code assets are copied. Consult their upstream licensing and execution instructions separately.

The saved alignment campaign observed extensive abstention and no established source-fidelity improvement from conditioning. Optimizer state is serialized; optimizer-resume equivalence was not replayed. These are unqualified research snapshots.

Historical load route with a compatible canonical owner:
```python
from ipfs_datasets_py.optimizers.logic_theorem_optimizer.legal_span_dimensions import load_checkpoint
decoder = load_checkpoint(checkpoint_path, expected_sha256=checkpoint_sha256)
# decoder.decode_formal_logic(texts, latents=matching_768d_vectors)
```
Source text is a required input. Matching vectors must follow the exact pinned profile. `native768_decoder_code/` contains the five declared implementation files, not a complete package.
"""


def prepare():
    output = WORK / 'retained-lanes-v1'
    output.mkdir(mode=0o700, exist_ok=False)
    sources = {}
    plans = []
    teacher_plan = ordinary_json(read(CAMPAIGN / 'checkpoint-01/representation_plan.json'))
    spans = ordinary_json(read(CAMPAIGN / 'decoder-discovery-01/inventory.json'))['source_span_decoders']['runs']
    source384_refs = teacher_plan['teacher_binding']['sources']
    for domain, hub_repo in REPOS.items():
        folder = output / domain
        folder.mkdir(mode=0o700)
        files = []
        assets = []

        def add(name, data, source=None, *, folder=folder, files=files):
            write(folder / name, data)
            record = {'path': name, 'bytes': len(data), 'sha256': digest(data)}
            files.append(record)
            if source is not None:
                sources[str(source)] = {'path': str(source), 'bytes': len(data), 'sha256': digest(data)}
            return record

        def copy(name, source, expected=None):
            return add(name, read(source, expected), source)

        sha, size = SOURCE384[domain]
        source = ROOT / 'artifacts/source-reconstruction-v2-20261001/run-01' / domain / 'raw_ce-1729-checkpoint.json'
        checkpoint = ordinary_json(read(source, (sha, size)))
        if checkpoint['domain_id'] != domain or checkpoint['schema'] != 'shared-source-384-autoencoder/v2':
            raise ValueError('source384 identity mismatch')
        binding = copy('source384/checkpoint.json', source, (sha, size))
        assets.append({'id': f'{domain}-source384', 'checkpoint': binding, **metadata384(checkpoint)})
        add('source384/README.md', CARD384.encode())
        for ref in source384_refs:
            source = Path(ref['path'])
            relative = source.relative_to(ROOT / 'artifacts/legal-ir-inference-speed-review/audit/baseline_tree')
            copy(f'source384_code/{relative.as_posix()}', source, (ref['sha256'], ref['bytes']))
        if domain == 'legal_ir':
            legacy = REPO / 'ipfs_datasets_py/optimizers/logic_theorem_optimizer/autoencoder_lineages/legacy_v1'
            for backend, pins in LINGUISTIC.items():
                origin = REPO / 'workspace/test-logs/legacy-linguistic-20261001/release-e2e' / backend / 'checkpoint-after-two-epochs'
                bindings = {name: copy(f'legacy8/{backend}/{name}', origin / name, pin) for name, pin in pins.items()}
                native = ordinary_json(read(origin / 'manifest.json', pins['manifest.json']))
                core = ordinary_json(read(origin / 'core.state.json', pins['core.state.json']))
                if native['dimension'] != 8 or native['formula_head_present'] is not False:
                    raise ValueError('linguistic profile mismatch')
                if any(core[key] for key in core if 'embedding_weights' in key) or core['decoded_embeddings']:
                    raise ValueError('unexpected vector weights in sparse profile')
                assets.append({'id': f'legacy8-{backend}', 'asset_type': 'spacy8_linguistic_sparse_heads',
                               'native_input_width': 8, 'epochs': 2, 'dense_vector_reconstruction_trained': False,
                               'independent_formula_head': False, 'files': bindings,
                               'linguistic_identity': native['linguistic_identity'], **FLAGS})
            add('legacy8/README.md', CARD8.encode())
            for snapshot in ['_snapshot', '_linguistic_snapshot']:
                manifest = ordinary_json(read(legacy / snapshot / 'MANIFEST.json'))
                expected_manifest = ('58935518a2114e361855f8832ab4c38af5671296fde657053e15a9139baaa314'
                                     if snapshot == '_snapshot' else
                                     'f44966d10d21f6f97ef89d967f411f5d86fe7195a0aa212269e3c785e27ddfa3')
                copy(f'legacy8_code/{snapshot}/MANIFEST.json', legacy / snapshot / 'MANIFEST.json',
                     (expected_manifest, (legacy / snapshot / 'MANIFEST.json').stat().st_size))
                entries = manifest.get('files', [manifest])
                for ref in entries:
                    copy(f'legacy8_code/{snapshot}/{ref["vendored_path"]}', legacy / snapshot / ref['vendored_path'],
                         (ref['vendored_sha256'], ref['vendored_bytes']))
                init = legacy / snapshot / '__init__.py'
                if snapshot == '_snapshot':
                    copy(f'legacy8_code/{snapshot}/__init__.py', init,
                         (manifest['snapshot_init_sha256'], init.stat().st_size))
            copy('legacy8_code/linguistic.py', legacy / 'linguistic.py',
                 ('baca84b44f7eda33466ffdc75170d904f480aafb47a779131337d90ed9a7bca3', 21063))
            for run in spans:
                for steps, key in [(400, 'selected_checkpoint'), (800, 'last_checkpoint')]:
                    ref = run[key]
                    pin = SPAN_PINS[(run['seed'], steps)]
                    if (ref['sha256'], ref['bytes']) != pin:
                        raise ValueError('span discovery pin disagrees')
                    binding = copy(f'native768_decoder/seed-{run["seed"]}/checkpoint-{steps}.json', Path(ref['path']), pin)
                    assets.append({'id': f'native768-span-{run["seed"]}-{steps}',
                                   'asset_type': 'source_span_decoder_with_native768_conditioning',
                                   'native_conditioning_width': 768, 'vector_reconstruction': False,
                                   'embedding_only_decoder': False, 'checkpoint': binding,
                                   'new_optimizer_steps': steps, 'selected_for_historical_run': steps == 400,
                                   'config': run['config'], 'context_contract': run['context_contract'],
                                   'implementation': run['implementation'],
                                   'optimizer_state_serialized': True, 'optimizer_resume_replayed': False, **FLAGS})
            add('native768_decoder/README.md', CARD768.encode())
            source_map = {
                'dimensions_sha256': 'legal_span_dimensions.py', 'span': 'legal_span_formula.py',
                'codec': 'legal_formula_codec.py', 'grammar': 'legal_ir_grammar_decoder.py',
                'canonical': 'canonical_contracts.py',
            }
            pins = {'dimensions_sha256': spans[0]['implementation']['dimensions_sha256'],
                    **spans[0]['implementation']['base_span']}
            for key, name in source_map.items():
                source = REPO / ('ipfs_datasets_py/logic/legal_ir' if key == 'canonical' else
                                 'ipfs_datasets_py/optimizers/logic_theorem_optimizer') / name
                copy(f'native768_decoder_code/{name}', source, (pins[key], source.stat().st_size))
            add('historical_teacher_reference.json', encoded(TEACHER))
        copy('LICENSE', REPO / 'LICENSE')
        smoke = Path(__file__).with_name('verify_release.py')
        copy('verify_release.py', smoke)
        card = (f'---\nlicense: agpl-3.0\ntags:\n- autoencoder\n- formal-logic\n- experimental\n---\n\n'
                f'# Retained {domain} source-vector assets, 2026-10-04\n\n'
                'This append-only release preserves authorial checkpoint bytes and labels each actual model type. '
                'It does not change the repository default or previous releases. The source384 reconstruction/decoder '
                'checkpoint is present in each domain; the legal release additionally contains two sparse spaCy8 '
                'bundles and six native768-conditioned span decoders. A new 768D reconstruction autoencoder is a '
                'separate future lineage.\n\n'
                'Run the bounded stdlib integrity check after downloading this complete release directory:\n'
                '```sh\npython3 verify_release.py .\n```\n'
                'The check verifies every declared file hash and the retained checkpoint schemas; it performs no '
                'model load or inference. Per-asset README files describe compatible historical numerical load '
                'routes and limitations. Source capsules are partial dependency inventories, not an asserted complete '
                'standalone distribution. Checkpoint/code publication does not turn any trust or admission flag true.\n\n'
                'The included authorial files follow the canonical repository AGPL-3.0 license. Upstream spaCy and '
                'GTE model assets are not included or relicensed; obtain dependencies at the exact referenced revisions '
                'under their own licenses. No review, organizer, private cohort, or candidate-panel files are included.\n')
        add('README.md', card.encode())
        manifest = {'schema': 'retained-autoformalization-hub-release/v1', 'repo_id': hub_repo,
                    'release_prefix': PREFIX, 'domain_id': domain, 'files': sorted(files, key=lambda f: f['path']),
                    'assets': assets, 'upstream_backbone_weights_included': False,
                    'numerical_models_loaded_this_preparation': 0, 'model_inference_calls_this_preparation': 0,
                    'source_capsule_dependency_closure': 'partial_selected_owner_files', **FLAGS}
        manifest['content_sha256'] = digest(encoded(manifest))
        write(folder / 'manifest.json', encoded(manifest))
        selected = manifest['files'] + [{'path': 'manifest.json', 'bytes': (folder / 'manifest.json').stat().st_size,
                                        'sha256': digest(read(folder / 'manifest.json'))}]
        plans.append({'repo_id': hub_repo, 'repo_type': 'model', 'prefix': PREFIX, 'directory': str(folder),
                      'files': selected, 'file_count': len(selected), 'bytes': sum(f['bytes'] for f in selected),
                      'root_or_default_files_modified': False, 'prior_remote_files_deleted': False})
    plan = {'schema': 'retained-autoformalization-publication-plan/v1', 'releases': plans,
            'original_input_bindings': sorted(sources.values(), key=lambda f: f['path']),
            'teacher_reference': TEACHER, 'authority': FLAGS,
            'upload_executed': False, 'numerical_models_loaded': 0,
            'preparation_script': {'path': str(Path(__file__).resolve()), 'sha256': digest(read(Path(__file__))),
                                   'bytes': Path(__file__).stat().st_size}}
    plan['content_sha256'] = digest(encoded(plan))
    write(WORK / 'retained_publication_plan.json', encoded(plan))
    return {'path': str(WORK / 'retained_publication_plan.json'),
            'sha256': digest(encoded(plan)), 'releases': [{k: p[k] for k in ['repo_id', 'file_count', 'bytes']} for p in plans]}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare', action='store_true', required=True)
    parser.parse_args()
    print(json.dumps(prepare(), sort_keys=True))
