"""Bounded CPU native source encoding of the exposed authored 64-source cohort.

No formal targets, backbone updates, decoder fitting, or downloads are part of
this worker. Selected canonical Python bytes are compiled in inert package
parents; selected native dependency entrypoints are checked without .pth files.
Those checks do not verify the entire binary dependency closure or create an OS
sandbox. An independent parent must enforce the 180-second process wall bound.
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import importlib
import importlib.abc
import importlib.machinery
import importlib.metadata
import importlib.util
import json
import os
import resource
import stat
import sys
import time
import types
from collections import Counter
from copy import deepcopy
from pathlib import Path

ROOT = Path('/home/barberb/lift_coding')
REPOSITORY = ROOT / 'external/ipfs_datasets'
NATIVE_SITE = Path('/home/barberb/.local/lib/python3.12/site-packages')
BOOTSTRAP = ROOT / 'artifacts/autoformalization-publication-20261004/huggingface/launch_reconstruction.py'
BOOTSTRAP_SHA = '910ff61a235d6e988e78b34a3b27d7ae7520f2bb10722881ab532c934be1199e'
ASSET_MANIFEST = REPOSITORY / 'configs/autoencoders/gte_multilingual_local_assets_v1.json'
ASSET_MANIFEST_SHA = '8beb874aa7b06599346173fde12e95f9f926b3028942d5014cdd2f99c4385166'
ASSET_BASE = ROOT / 'artifacts/autoformalization-alignment-20261003/richer-encoder-assets'
GTE384_SNAPSHOT = Path('/home/barberb/.cache/huggingface/hub/models--thenlper--gte-small/snapshots/17e1f347d17fe144873b1201da91788898c639cd')
AUTOENCODER = 'ipfs_datasets_py.logic.formalization.autoencoder.'
OPTIMIZER = 'ipfs_datasets_py.optimizers.logic_theorem_optimizer.'
SNAPSHOT = OPTIMIZER + 'autoencoder_lineages.legacy_v1._snapshot.'
LINGUISTIC = OPTIMIZER + 'autoencoder_lineages.legacy_v1._linguistic_snapshot'
LANES = ('legacy8', 'native384', 'native768')
MASKS = ('weak_decoder_fit', 'strong_semantic_fit', 'contrastive_supervision',
         'proof_supervision', 'fidelity_evaluation')
MAX_BYTES = 32 * 1024 * 1024
RESOURCE_LIMITS = {'address_space_bytes': 8 * 1024**3, 'cpu_soft_seconds': 120,
                   'cpu_hard_seconds': 130, 'file_size_bytes': MAX_BYTES,
                   'cpu_threads': 1, 'parent_wall_seconds': 180}
PROVIDERS = {
    'transformers': ('transformers', '4.52.1', 34338, '6b646f7212b492bacdf3fd03e4359a97d64d5661f6d539a694b8dc6a66e604ef'),
    'tokenizers': ('tokenizers', '0.21.4', 2615, '644e596a052fa1b05272b1c141d1286e1c78c2a3346ecabd17d68b62404d8d84'),
    'sentence_transformers': ('sentence-transformers', '5.4.1', 2989, '37eed39ba200824b481c2b7029d317ff94a94888eaf35da708bf16159af561eb'),
    'spacy': ('spacy', '3.8.14', 3562, '7fc49305e893ceb38da1b728c8129c350439d58220bd74748923227fb0a840ab'),
    'en_core_web_sm': ('en-core-web-sm', '3.8.0', 237, 'c8eb57079c03fc4157c227f641781fbcb3e9d11439abe1bf0b72e4c0fa78a38d'),
}
MODULES = (
    AUTOENCODER + 'alignment_richer_embeddings', AUTOENCODER + 'alignment_lane_bundle',
    AUTOENCODER + 'source_embeddings_768_complete', AUTOENCODER + 'source_embeddings_768',
    AUTOENCODER + 'gte_multilingual_profile',
    OPTIMIZER + 'autoencoder_embedding_runtime', OPTIMIZER + 'autoencoder_embedding_production',
    OPTIMIZER + 'autoencoder_corpus_manifest', OPTIMIZER + 'autoencoder_training_worker',
    OPTIMIZER + 'autoencoder_native_pool', OPTIMIZER + 'modal_autoencoder_adaptive_optimizer',
    OPTIMIZER + 'autoencoder_lineages._contract', LINGUISTIC, LINGUISTIC + '.spacy_modal_codec',
    SNAPSHOT + 'legal_modal_parser', SNAPSHOT + 'legal_samples', SNAPSHOT + 'modal_ir',
    SNAPSHOT + 'modal_registry', SNAPSHOT + 'frame_bm25_selector',
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def raw(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                      allow_nan=False).encode('utf-8')


def digest(value):
    return hashlib.sha256(raw(value)).hexdigest()


def seal(value, field='content_sha256'):
    value[field] = digest({k: v for k, v in value.items() if k != field})
    return value


def closed(value, keys, label):
    require(type(value) is dict and set(value) == set(keys), 'closed ' + label + ' required')


def check_seal(value, field='content_sha256'):
    require(value.get(field) == digest({k: v for k, v in value.items() if k != field}),
            'content seal differs')


def strict_json(data):
    def unique(items):
        result = {}
        for k, v in items:
            require(k not in result, 'duplicate JSON field')
            result[k] = v
        return result

    def invalid(_):
        raise ValueError('nonfinite JSON value')

    value = json.loads(data, object_pairs_hook=unique, parse_constant=invalid)
    raw(value)
    return value


def checked(binding):
    closed(binding, ('path', 'bytes', 'sha256'), 'file binding')
    path = Path(binding['path'])
    require(path.is_absolute() and '..' not in path.parts
            and not any(p.is_symlink() for p in (path, *path.parents)),
            'absolute nonsymlink selected path required')
    require(type(binding['bytes']) is int and 0 < binding['bytes'] <= MAX_BYTES,
            'bounded selected file size required')
    require(type(binding['sha256']) is str and len(binding['sha256']) == 64
            and all(c in '0123456789abcdef' for c in binding['sha256']), 'SHA256 required')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and before.st_size == binding['bytes'],
                'regular selected file size differs')
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            data = stream.read(MAX_BYTES + 1)
        after = os.fstat(fd)
    finally:
        os.close(fd)
    require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns)
            == (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns),
            'selected file changed during read')
    require(len(data) == binding['bytes'] and hashlib.sha256(data).hexdigest() == binding['sha256'],
            'selected file pin differs')
    return data


def binding(path):
    path = Path(path).absolute()
    data = path.read_bytes()
    return {'path': str(path), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def module_path(name):
    path = REPOSITORY / Path(*name.split('.'))
    return path / '__init__.py' if name == LINGUISTIC else path.with_suffix('.py')


def selected_source_bindings():
    """Read-only helper for an externally frozen plan; imports no canonical code."""
    return [{'module': name, 'binding': binding(module_path(name))} for name in MODULES]


def source_policy():
    return {'scope': 'exposed_authored_composition_source_reconstruction_only',
            'source_reconstruction_fit_authorized': True,
            'semantic_masks': dict.fromkeys(MASKS, 0), 'semantic_label_admission': False,
            'independent_semantic_review_completed': False, 'source_fidelity_established': False,
            'natural_sources': False, 'pristine_holdout': False, 'reused_exposed_components': True,
            'formal_targets_read': False, 'proof_authority': False, 'qualified': False}


def validate_sources(inputs, cohort):
    closed(inputs, ('schema', 'rows', 'row_count', 'input_recipe', 'policy',
                    'contains_formal_targets', 'content_sha256'), 'source inputs')
    closed(cohort, ('schema', 'rows', 'policy', 'contains_formal_targets', 'content_sha256'), 'source cohort')
    require(inputs['schema'] == 'source-only-authored-expansion-inputs/v1'
            and cohort['schema'] == 'source-only-authored-expansion-cohort/v1', 'source schema differs')
    require(raw(inputs['policy']) == raw(cohort['policy']) == raw(source_policy())
            and inputs['contains_formal_targets'] is False
            and cohort['contains_formal_targets'] is False, 'source-only policy differs')
    require(inputs['input_recipe'] == 'exact_source_only/v1', 'exact source recipe required')
    check_seal(inputs)
    check_seal(cohort)
    rows, metadata = inputs['rows'], cohort['rows']
    require(type(rows) is list and type(metadata) is list and len(rows) == len(metadata) == 64
            and type(inputs['row_count']) is int and inputs['row_count'] == 64, 'exact64 sources required')
    expected_context = {'role': 'none_required', 'text': '', 'bindings': {},
                        'sha256': hashlib.sha256(b'').hexdigest()}
    identities, split_groups, total_bytes = [], {'train': set(), 'development': set()}, 0
    split_sources, split_inputs = {'train': set(), 'development': set()}, {'train': set(), 'development': set()}
    for row, meta in zip(rows, metadata, strict=True):
        closed(row, ('id', 'input', 'input_sha256', 'source_sha256', 'group_id', 'split', 'review_item_id'), 'source row')
        closed(meta, ('id', 'split', 'group_id', 'source_sha256', 'input_sha256', 'context_role'), 'cohort row')
        closed(row['input'], ('source_text', 'context'), 'source request')
        require(raw(row['input']['context']) == raw(expected_context) and meta['context_role'] == 'none_required',
                'fixed empty unapplied context required')
        text = row['input']['source_text']
        require(type(text) is str and bool(text.strip()) and '\x00' not in text, 'source text required')
        data = text.encode('utf-8')
        total_bytes += len(data)
        require(0 < len(data) <= 65536 and total_bytes <= 2 * 1024 * 1024, 'source byte bound exceeded')
        require(row['source_sha256'] == hashlib.sha256(data).hexdigest()
                and row['input_sha256'] == digest(row['input'])
                and row['id'] == 'sha256:' + row['input_sha256'], 'source identity differs')
        require(row['split'] in split_groups and type(row['group_id']) is str
                and bool(row['group_id']) and type(row['review_item_id']) is str
                and bool(row['review_item_id']), 'split/group/review join required')
        require(meta == {k: row[k] for k in ('id', 'split', 'group_id', 'source_sha256', 'input_sha256')}
                | {'context_role': 'none_required'}, 'cohort source join differs')
        identities.append(row['id'])
        split_groups[row['split']].add(row['group_id'])
        split_sources[row['split']].add(row['source_sha256'])
        split_inputs[row['split']].add(row['input_sha256'])
    require(identities == sorted(set(identities)), 'source IDs must be unique sorted')
    require(Counter(row['split'] for row in rows) == {'train': 32, 'development': 32}, 'TRAIN32/DEV32 required')
    for sets in (split_groups, split_sources, split_inputs):
        require(not sets['train'] & sets['development'], 'train/development overlap forbidden')
    require(all(len(groups) == 8 for groups in split_groups.values()), 'eight groups per split required')
    require(all(n == 4 for n in Counter(row['group_id'] for row in rows).values()),
            'four variants per group required')
    return {'rows': 64, 'train_rows': 32, 'development_rows': 32, 'source_bytes': total_bytes,
            'train_groups': 8, 'development_groups': 8, 'group_overlap': 0, 'source_overlap': 0,
            'input_overlap': 0, 'context_forwarded_rows': 0}


def producer_inputs(inputs):
    rows = [{'id': r['id'], 'input_sha256': r['input_sha256'],
             'source_text': r['input']['source_text'], 'source_sha256': r['source_sha256'],
             'context_role': 'none_required', 'context_applied': False} for r in inputs['rows']]
    return seal({'schema': 'alignment-richer-embedding-inputs/v1', 'input_recipe': 'exact_source_only',
                 'identity_recipe': 'sha256:authored_panel_input_sha256;context_not_forwarded',
                 'rows': rows, 'row_count': 64, 'context_unapplied_rows': 0,
                 'all_context_unapplied': True, 'qualified': False, 'proof_authority': False}, 'payload_sha256')


class CapturedLoader(importlib.abc.Loader):
    def __init__(self, name, selected, data):
        self.name, self.selected, self.data = name, selected, data

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        module.__file__ = self.selected['path']
        if self.name == LINGUISTIC:
            module.__path__ = [str(Path(self.selected['path']).parent)]
        exec(compile(self.data, self.selected['path'], 'exec'), module.__dict__)


class CapturedFinder(importlib.abc.MetaPathFinder):
    def __init__(self, selected):
        self.selected = selected

    def find_spec(self, fullname, path=None, target=None):
        if fullname in self.selected:
            selected, data = self.selected[fullname]
            return importlib.util.spec_from_loader(fullname, CapturedLoader(fullname, selected, data),
                                                   is_package=fullname == LINGUISTIC)
        if fullname == 'ipfs_datasets_py' or fullname.startswith('ipfs_datasets_py.'):
            raise ImportError('unselected canonical import: ' + fullname)
        return None


def install_canonical_sources(selected):
    require(not any(name == 'ipfs_datasets_py' or name.startswith('ipfs_datasets_py.')
                    for name in sys.modules), 'canonical modules already imported')
    parents = set()
    for name in selected:
        pieces = name.split('.')
        parents.update('.'.join(pieces[:n]) for n in range(1, len(pieces)))
    for name in sorted(parents, key=lambda n: (n.count('.'), n)):
        if name in selected:
            continue
        package = types.ModuleType(name)
        package.__path__ = [str(REPOSITORY / Path(*name.split('.')))]
        package.__package__ = name
        package.__spec__ = importlib.machinery.ModuleSpec(name, loader=None, is_package=True)
        sys.modules[name] = package
        if '.' in name:
            parent, leaf = name.rsplit('.', 1)
            setattr(sys.modules[parent], leaf, package)
    finder = CapturedFinder(selected)
    sys.meta_path.insert(0, finder)
    return finder


def capture_plan(path, expected_sha):
    selected = binding(path)
    require(selected['sha256'] == expected_sha, 'externally selected plan SHA differs')
    plan = strict_json(checked(selected))
    closed(plan, ('schema', 'helper_binding', 'bootstrap_binding', 'source_inputs_binding',
                  'cohort_metadata_binding', 'producer_source_bindings', 'asset_manifest_binding',
                  'expected_profiles', 'authorization_scope', 'resource_limits', 'content_sha256'), 'encoding plan')
    require(plan['schema'] == 'expanded-source-native-encoding-plan/v1'
            and plan['authorization_scope'] == 'source_only_native_encoding_no_semantic_admission'
            and raw(plan['resource_limits']) == raw(RESOURCE_LIMITS), 'encoding plan scope/resources differ')
    check_seal(plan)
    require(Path(plan['helper_binding']['path']) == Path(__file__).absolute(), 'encoding helper differs')
    checked(plan['helper_binding'])
    require(plan['bootstrap_binding'] == {'path': str(BOOTSTRAP), 'bytes': 6247, 'sha256': BOOTSTRAP_SHA},
            'bootstrap pin differs')
    bootstrap_data = checked(plan['bootstrap_binding'])
    require(plan['asset_manifest_binding'] == {'path': str(ASSET_MANIFEST), 'bytes': 1470,
                                              'sha256': ASSET_MANIFEST_SHA}, 'asset manifest differs')
    checked(plan['asset_manifest_binding'])
    sources = plan['producer_source_bindings']
    require(type(sources) is list and len(sources) == len(MODULES), 'selected source coverage differs')
    captured = {}
    for name, item in zip(MODULES, sources, strict=True):
        closed(item, ('module', 'binding'), 'selected module')
        require(item['module'] == name and Path(item['binding']['path']) == module_path(name),
                'canonical source order/path differs')
        captured[name] = item['binding'], checked(item['binding'])
    require(type(plan['expected_profiles']) is dict and set(plan['expected_profiles']) == set(LANES),
            'three selected native profiles required')
    inputs = strict_json(checked(plan['source_inputs_binding']))
    cohort = strict_json(checked(plan['cohort_metadata_binding']))
    counts = validate_sources(inputs, cohort)
    return plan, selected, captured, bootstrap_data, inputs, counts


def admit_native(bootstrap_data):
    require(sys.flags.isolated and sys.dont_write_bytecode, 'native worker requires -I -B')
    require(not any(name in sys.modules for name in (*PROVIDERS, 'torch', 'safetensors')),
            'native providers imported before admission')
    bootstrap = types.ModuleType('_expanded_verified_native_bootstrap')
    bootstrap.__file__ = str(BOOTSTRAP)
    exec(compile(bootstrap_data, str(BOOTSTRAP), 'exec'), bootstrap.__dict__)
    providers = bootstrap.select_native_site()
    for name, (distribution, version, size, sha) in PROVIDERS.items():
        selected = {'path': str(NATIVE_SITE / name / '__init__.py'), 'bytes': size, 'sha256': sha}
        checked(selected)
        spec = importlib.util.find_spec(name)
        require(spec is not None and spec.origin == selected['path'], 'selected provider origin differs')
        found = importlib.metadata.distribution(distribution)
        require(found.version == version and Path(found.locate_file('')) == NATIVE_SITE,
                'selected provider distribution differs')
        providers[name] = {**selected, 'distribution': distribution, 'version': version}
    return providers


def apply_resources():
    for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
        os.environ[key] = '1'
    os.environ.update({'CUDA_VISIBLE_DEVICES': '', 'TOKENIZERS_PARALLELISM': 'false',
                       'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1', 'HF_DATASETS_OFFLINE': '1',
                       'HF_HUB_DISABLE_TELEMETRY': '1', 'PYTHONDONTWRITEBYTECODE': '1'})
    resource.setrlimit(resource.RLIMIT_AS, (RESOURCE_LIMITS['address_space_bytes'],) * 2)
    resource.setrlimit(resource.RLIMIT_CPU, (RESOURCE_LIMITS['cpu_soft_seconds'], RESOURCE_LIMITS['cpu_hard_seconds']))
    resource.setrlimit(resource.RLIMIT_FSIZE, (RESOURCE_LIMITS['file_size_bytes'],) * 2)
    return {'before_model_library_imports': True, 'configured': RESOURCE_LIMITS,
            'actual_address_space': list(resource.getrlimit(resource.RLIMIT_AS)),
            'actual_cpu_seconds': list(resource.getrlimit(resource.RLIMIT_CPU)),
            'actual_file_size': list(resource.getrlimit(resource.RLIMIT_FSIZE)),
            'cuda_visible_devices': os.environ['CUDA_VISIBLE_DEVICES']}


def raw_profile(owner, lane):
    backend, lane_id = lane['backend_evidence'], lane['lane_id']
    if lane_id == 'legacy8':
        metadata = backend['production_evidence']['model_identity']
        model_id, revision = metadata['model_name'], metadata['model_version']
        stage, precision, pooling, endpoint = ('historical_linguistic_features', 'decimal6', 'none',
                                               'spacy_modal_codec.decode_embedding(dimensions=8)')
    else:
        stage, precision = 'raw_embedding', 'float32'
        if lane_id == 'native384':
            metadata = backend['production_evidence']['model']
            model_id, revision = metadata['model_id'], metadata['revision']
            pooling, endpoint = 'mean', 'sentence_transformers.mean_pooling'
        else:
            model_id, revision = 'Alibaba-NLP/gte-multilingual-base', backend['production_evidence']['assets']['model_revision']
            pooling, endpoint = 'cls', 'complete_model.encoder.last_hidden_state[:,0]'
    return seal({'schema': owner.PROFILE_SCHEMA, 'lane_id': lane_id, 'stage': stage,
                 'dimension': lane['dimension'], 'producer': {'profile_id': backend['profile_id'],
                 'model_id': model_id, 'model_revision': revision, 'code_sha256': digest(backend['implementation']),
                 'model_assets_sha256': digest(backend['asset_evidence']), 'checkpoint_sha256': None},
                 'pooling': {'method': pooling, 'endpoint': endpoint},
                 'normalization': {'kind': 'l2', 'unit_tolerance': 1e-5}, 'precision': precision,
                 'fit_input_recipe': 'exact_source_only/v1', 'inference_input_recipe': 'exact_source_only/v1'})


def build_bundle(owner, inputs, profile, lane, artifact):
    require(len(inputs['rows']) == len(lane['receipts']) == 64, 'production coverage differs')
    rows, declarations = [], []
    for source, observed in zip(inputs['rows'], lane['receipts'], strict=True):
        require(source['id'] == observed['id'] and source['input_sha256'] == observed['input_sha256']
                and source['source_sha256'] == observed['source_sha256'], 'source producer join differs')
        vector = observed['embedding']
        available = observed['status'] == 'embedded'
        declaration = {'id': source['id'], 'input_sha256': source['input_sha256'],
                       'encoder_text_sha256': source['source_sha256'],
                       'status': 'available' if available else 'unavailable',
                       'reason': None if available else observed['status'],
                       'vector_sha256': digest(vector) if available else None,
                       'upstream_vector_sha256': None, 'token_receipt_sha256': observed['token_input_sha256']}
        declarations.append(declaration)
        rows.append({**declaration, 'input': deepcopy(source['input']),
                     'encoder_text': source['input']['source_text'], 'vector': deepcopy(vector),
                     'producer_row_sha256': digest(declaration)})
    producer = seal({'schema': owner.PRODUCER_SCHEMA, 'profile_sha256': digest(profile),
                     'artifact_binding': artifact, 'rows': declarations})
    bundle = seal({'schema': owner.SCHEMA, 'profile': profile, 'producer_receipt': producer, 'rows': rows})
    expected = {'profile_sha256': digest(profile), 'producer_receipt_sha256': digest(producer),
                'inputs': [{'id': r['id'], 'input_sha256': r['input_sha256']} for r in rows]}
    owner.validate_lane_bundle(bundle, expected_bindings=expected)
    return bundle, expected


def split_bundle(owner, bundle, identities):
    require(type(identities) is list and identities == sorted(set(identities)) and len(identities) == 32,
            'sorted unique split32 identities required')
    selected = set(identities)
    rows = [deepcopy(r) for r in bundle['rows'] if r['id'] in selected]
    require([r['id'] for r in rows] == identities, 'split identities unavailable')
    producer = deepcopy(bundle['producer_receipt'])
    producer['rows'] = [deepcopy(r) for r in producer['rows'] if r['id'] in selected]
    seal(producer)
    result = seal({'schema': bundle['schema'], 'profile': deepcopy(bundle['profile']),
                   'producer_receipt': producer, 'rows': rows})
    expected = {'profile_sha256': digest(result['profile']), 'producer_receipt_sha256': digest(producer),
                'inputs': [{'id': r['id'], 'input_sha256': r['input_sha256']} for r in rows]}
    owner.validate_lane_bundle(result, expected_bindings=expected)
    return result, expected


def save(path, value):
    data = raw(value) + b'\n'
    require(len(data) <= MAX_BYTES, 'result exceeds file bound')
    with Path(path).open('xb') as stream:
        stream.write(data)
    return {'path': str(Path(path).absolute()), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def run(plan_path, plan_sha, output):
    started = time.monotonic()
    output = Path(output)
    require(output.is_absolute() and not output.exists()
            and not any(p.is_symlink() for p in output.parents), 'fresh absolute output directory required')
    plan, plan_binding, captured, bootstrap_data, inputs, counts = capture_plan(plan_path, plan_sha)
    output.mkdir(parents=True)
    resources = apply_resources()
    save(output / 'resource-admission.json', seal({'schema': 'expanded-source-native-resource-admission/v1',
                                                'observations': resources, 'model_libraries_imported': False}))
    providers = admit_native(bootstrap_data)
    install_canonical_sources(captured)
    owner = importlib.import_module(AUTOENCODER + 'alignment_lane_bundle')
    wrapper = importlib.import_module(AUTOENCODER + 'alignment_richer_embeddings')
    selected_inputs = producer_inputs(inputs)
    wrapper.validate_richer_embedding_inputs(selected_inputs)
    selected_binding = save(output / 'producer-source-inputs.json', selected_inputs)
    guard = importlib.import_module(OPTIMIZER + 'autoencoder_embedding_runtime')
    # Asset admission precedes every neural forward; producers repeat their own
    # full asset checks before loading and after inference.
    _, gte384_assets = guard._snapshot_assets(GTE384_SNAPSHOT)
    profile = importlib.import_module(AUTOENCODER + 'gte_multilingual_profile')
    gte768_assets = profile.inspect_local_assets(ASSET_MANIFEST, expected_sha256=ASSET_MANIFEST_SHA,
                                               model_directory=ASSET_BASE / 'model', code_directory=ASSET_BASE / 'code')
    require(gte768_assets['status'] == 'available', 'native768 assets unavailable')
    artifacts, summaries, total_forwards = {}, {}, 0
    for lane_id in LANES:
        lane_started = time.monotonic()
        with guard._offline_guard():
            if lane_id == 'legacy8':
                lane = wrapper.run_spacy8(selected_inputs, backend='local_en_core_web_sm')
            elif lane_id == 'native384':
                lane = wrapper.run_gte384(selected_inputs, snapshot_path=GTE384_SNAPSHOT, batch_size=16)
            else:
                lane = wrapper.run_gte768(selected_inputs, manifest_path=ASSET_MANIFEST,
                                          expected_manifest_sha256=ASSET_MANIFEST_SHA,
                                          model_directory=ASSET_BASE / 'model', code_directory=ASSET_BASE / 'code',
                                          batch_size=1)
        wrapper.validate_embedding_lane(lane, selected_inputs)
        require(lane['status'] == 'produced' and len(lane['receipts']) == 64, 'complete native64 production required')
        current_profile = raw_profile(owner, lane)
        require(current_profile == plan['expected_profiles'][lane_id], 'native producer profile changed')
        lane_binding = save(output / (lane_id + '-production.json'), lane)
        bundle, expected = build_bundle(owner, inputs, current_profile, lane, lane_binding)
        lane_artifacts = {'production': lane_binding,
                          'full_bundle': save(output / (lane_id + '_raw_bundle.json'), bundle),
                          'full_expected': save(output / (lane_id + '_raw_expected_bindings.json'), expected)}
        for split, filename in (('train', 'train'), ('development', 'query')):
            identities = [r['id'] for r in inputs['rows'] if r['split'] == split]
            subset, pins = split_bundle(owner, bundle, identities)
            lane_artifacts[filename + '_bundle'] = save(output / (lane_id + '_raw_' + filename + '_bundle.json'), subset)
            lane_artifacts[filename + '_expected'] = save(output / (lane_id + '_raw_' + filename + '_expected_bindings.json'), pins)
        tokens = [r['token_count'] for r in lane['receipts']]
        summary = {'rows': 64, 'train_rows': 32, 'development_rows': 32, 'dimension': lane['dimension'],
                   'source_profile_sha256': digest(current_profile), 'profile_id': lane['backend_evidence']['profile_id'],
                   'token_count_min': min(tokens), 'token_count_max': max(tokens), 'token_count_total': sum(tokens),
                   'elapsed_seconds': time.monotonic() - lane_started,
                   'model_inference_executed': lane['model_inference_executed'],
                   'encoder_execution_executed': lane['encoder_execution_executed'],
                   'context_semantics_applied': False, 'training_executed': False, 'download_executed': False}
        if lane_id == 'native768':
            summary['extra_dense_path_probe_forwards'] = 2
            total_forwards += 2
        total_forwards += 64
        artifacts[lane_id], summaries[lane_id] = lane_artifacts, summary
        save(output / (lane_id + '-summary.json'), seal(summary))
        del lane, bundle, expected, subset, pins
        gc.collect()
    for selected, data in captured.values():
        require(checked(selected) == data, 'canonical source changed during encoding')
    for item in providers.values():
        checked({k: item[k] for k in ('path', 'bytes', 'sha256')})
    checked(plan['helper_binding'])
    checked(plan['bootstrap_binding'])
    checked(plan['source_inputs_binding'])
    checked(plan['cohort_metadata_binding'])
    checked(plan['asset_manifest_binding'])
    require(guard._snapshot_assets(GTE384_SNAPSHOT)[1] == gte384_assets, 'native384 assets changed')
    require(profile.inspect_local_assets(ASSET_MANIFEST, expected_sha256=ASSET_MANIFEST_SHA,
                                         model_directory=ASSET_BASE / 'model', code_directory=ASSET_BASE / 'code')
            == gte768_assets, 'native768 assets changed')
    report = seal({'schema': 'expanded-source-native-encoding-report/v1', 'status': 'completed',
                   'plan_binding': plan_binding, 'source_inputs_binding': plan['source_inputs_binding'],
                   'cohort_metadata_binding': plan['cohort_metadata_binding'], 'producer_inputs_binding': selected_binding,
                   'source_policy': source_policy(), 'counts': counts, 'resources': resources,
                   'selected_provider_entrypoints': providers,
                   'canonical_source_bindings': plan['producer_source_bindings'], 'artifacts': artifacts,
                   'lanes': summaries, 'native_source_row_encodings': 192,
                   'extra_native768_dense_path_probe_forwards': 2,
                   'row_encoder_invocations_including_probe': total_forwards,
                   'dependency_scope': 'selected_entrypoints_and_captured_canonical_modules_not_complete_binary_closure',
                   'site_pth_processing': False, 'canonical_package_initializers_executed': [LINGUISTIC],
                   'os_sandbox': False, 'model_inference_executed': True,
                   'optimizer_updates': 0, 'training_executed': False, 'download_executed': False,
                   'formal_targets_read': False, 'semantic_label_admission': False,
                   'masks': dict.fromkeys(MASKS, 0), 'source_fidelity_established': False,
                   'proof_authority': False, 'qualified': False, 'prover_executed': False,
                   'elapsed_seconds': time.monotonic() - started})
    report_binding = save(output / 'encoding-report.json', report)
    return {'status': 'completed', 'report_binding': report_binding, 'source_rows': 64,
            'native_vectors': 192, 'optimizer_updates': 0, 'qualified': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', required=True)
    parser.add_argument('--plan-sha256', required=True)
    parser.add_argument('--output-directory', required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.plan, args.plan_sha256, args.output_directory), sort_keys=True))


if __name__ == '__main__':
    main()
