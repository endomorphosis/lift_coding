"""Bounded source-only comparison of frozen native768 decoder conditioning.

Reuses saved source vectors, PCA inverses and AE reconstructions. The unchanged
source-span decoder emits unaccepted single-rule proposals; no reference,
semantic accuracy, new encoder execution, model fit or prover is available.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.abc
import importlib.machinery
import importlib.util
import json
import math
import os
import resource
import stat
import sys
import time
import types
from collections import Counter
from pathlib import Path

REPOSITORY = Path('/home/barberb/lift_coding/external/ipfs_datasets')
MAX_BYTES = 32 * 1024**2
BOOTSTRAP_SHA = '910ff61a235d6e988e78b34a3b27d7ae7520f2bb10722881ab532c934be1199e'
PROFILE_SHA = '151bd007468651bb720cfa60976c491e3e7cde55a06ef2336d786f9b80fe5f5e'
OPTIMIZER = 'ipfs_datasets_py.optimizers.logic_theorem_optimizer.'
LEGAL = 'ipfs_datasets_py.logic.legal_ir.'
MODULES = ('ipfs_datasets_py.utils.cid_utils', LEGAL + 'canonical_contracts',
           OPTIMIZER + 'snapshot_evaluator', OPTIMIZER + 'legal_ir_family_evaluator',
           OPTIMIZER + 'legal_ir_grammar_decoder', OPTIMIZER + 'legal_formula_codec',
           OPTIMIZER + 'legal_span_formula', OPTIMIZER + 'legal_span_dimensions',
           LEGAL + 'canonical_source_guards', LEGAL + 'canonical_decoder_preflight',
           LEGAL + 'canonical_span_decoder')
SEEDS = (1729, 1730, 1731)
CONTROLS = ('raw_source', 'pca_reconstructed', 'new_ae_reconstructed',
            'zero_raw', 'disabled_raw', 'rotated_raw')
VIEWS = ('raw_source', 'new_latent', 'new_reconstructed', 'old_latent',
         'old_reconstructed', 'mean_reconstructed', 'pca_latent', 'pca_reconstructed')
MASKS = ('weak_decoder_fit', 'strong_semantic_fit', 'contrastive_supervision',
         'proof_supervision', 'fidelity_evaluation')
AUTHORIZATION = {
    'scope': 'exposed_authored_source_only_frozen_decoder_conditioning_perturbation/v1',
    'request_selection': 'all64_authored_requests_no_semantic_filter',
    'semantic_masks': dict.fromkeys(MASKS, 0), 'formal_targets_read': False,
    'semantic_label_admission': False, 'independent_semantic_accuracy_measured': False,
    'source_fidelity_established': False, 'natural_sources': False,
    'pristine_holdout': False, 'training_executed': False, 'qualified': False,
    'proof_authority': False, 'accepted': False}
SOURCE_POLICY = {
    'scope': 'exposed_authored_composition_source_reconstruction_only',
    'source_reconstruction_fit_authorized': True, 'semantic_masks': dict.fromkeys(MASKS, 0),
    'semantic_label_admission': False, 'independent_semantic_review_completed': False,
    'source_fidelity_established': False, 'natural_sources': False, 'pristine_holdout': False,
    'reused_exposed_components': True, 'formal_targets_read': False,
    'proof_authority': False, 'qualified': False}
LIMITS = {'address_space_bytes': 8 * 1024**3, 'cpu_seconds_soft': 120,
          'cpu_seconds_hard': 130, 'cooperative_rss_kib': 2 * 1024**2,
          'cooperative_seconds': 90, 'cpu_threads': 1, 'dtype': 'float32',
          'device': 'cpu', 'parent_wall_seconds': 180}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def raw(value, *, ascii=False):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=ascii, allow_nan=False).encode('utf-8')


def digest(value, *, ascii=False):
    return hashlib.sha256(raw(value, ascii=ascii)).hexdigest()


def closed(value, keys, label):
    require(type(value) is dict and set(value) == set(keys), 'closed ' + label + ' required')


def sha(value):
    require(type(value) is str and len(value) == 64 and
            all(c in '0123456789abcdef' for c in value), 'lowercase SHA256 required')


def strict_json(data):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'duplicate JSON key')
            result[key] = value
        return result
    return json.loads(data.decode('utf-8'), object_pairs_hook=pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite JSON')))


def seal_check(value):
    require(type(value) is dict and value.get('content_sha256') ==
            digest({k: v for k, v in value.items() if k != 'content_sha256'}), 'JSON seal differs')


def file_bytes(path):
    path = Path(path)
    require(path.is_absolute() and not any(p.is_symlink() for p in (path, *path.parents)),
            'absolute nonsymlink selected file required')
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(descriptor)
        require(stat.S_ISREG(before.st_mode) and 0 < before.st_size <= MAX_BYTES,
                'bounded nonempty regular file required')
        with os.fdopen(descriptor, 'rb', closefd=False) as stream:
            data = stream.read(MAX_BYTES + 1)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) ==
            (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns) and
            len(data) == before.st_size, 'selected file changed during capture')
    return data


def binding(path):
    data = file_bytes(path)
    return {'path': str(path), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


class Capture:
    def __init__(self):
        self.files = {}

    def get(self, reference):
        closed(reference, ('path', 'bytes', 'sha256'), 'file binding')
        sha(reference['sha256'])
        require(type(reference['bytes']) is int and 0 < reference['bytes'] <= MAX_BYTES,
                'bounded binding bytes required')
        key = reference['path']
        if key not in self.files:
            data = file_bytes(key)
            require(len(data) == reference['bytes'] and
                    hashlib.sha256(data).hexdigest() == reference['sha256'], 'external file pin differs')
            self.files[key] = (copy.deepcopy(reference), data)
        require(self.files[key][0] == reference, 'conflicting selected file bindings')
        return self.files[key][1]

    def json(self, reference):
        return strict_json(self.get(reference))

    def recheck(self):
        for reference, data in self.files.values():
            require(file_bytes(reference['path']) == data, 'selected input changed during execution')

    def references(self):
        return [r for r, _ in self.files.values()]


def write(path, value):
    if 'content_sha256' in value:
        seal_check(value)
    body = {k: v for k, v in value.items() if k != 'content_sha256'}
    data = json.dumps({**body, 'content_sha256': digest(body)}, sort_keys=True, indent=2,
                      ensure_ascii=False, allow_nan=False).encode('utf-8') + b'\n'
    require(len(data) <= MAX_BYTES, 'bounded output required')
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, 'wb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    return binding(path)


def validate_sources(inputs, cohort):
    closed(inputs, ('schema', 'rows', 'row_count', 'input_recipe', 'policy',
                    'contains_formal_targets', 'content_sha256'), 'source inputs')
    closed(cohort, ('schema', 'rows', 'contains_formal_targets', 'policy', 'content_sha256'), 'cohort')
    for value in (inputs, cohort):
        seal_check(value)
        require(value['contains_formal_targets'] is False and raw(value['policy']) == raw(SOURCE_POLICY),
                'source-only policy differs')
    require(inputs['schema'] == 'source-only-authored-expansion-inputs/v1' and
            cohort['schema'] == 'source-only-authored-expansion-cohort/v1' and
            inputs['input_recipe'] == 'exact_source_only/v1' and inputs['row_count'] == 64 and
            len(inputs['rows']) == len(cohort['rows']) == 64, 'complete source-only64 required')
    requests, metadata, seen = [], [], set()
    for source, meta in zip(inputs['rows'], cohort['rows'], strict=True):
        closed(source, ('id', 'input', 'input_sha256', 'source_sha256', 'group_id', 'split',
                        'review_item_id'), 'source row')
        closed(meta, ('id', 'split', 'group_id', 'source_sha256', 'input_sha256', 'context_role'), 'cohort row')
        closed(source['input'], ('source_text', 'context'), 'source input')
        context = source['input']['context']
        closed(context, ('role', 'text', 'bindings', 'sha256'), 'source context')
        text = source['input']['source_text']
        require(type(text) is str and 0 < len(text) <= 16384 and
                context == {'role': 'none_required', 'text': '', 'bindings': {},
                            'sha256': hashlib.sha256(b'').hexdigest()}, 'exact source-only context required')
        require(source['input_sha256'] == digest(source['input']) and
                source['source_sha256'] == hashlib.sha256(text.encode('utf-8')).hexdigest() and
                source['id'] == 'sha256:' + source['input_sha256'] and source['id'] not in seen,
                'source row identity/hash differs')
        require(source['split'] in ('train', 'development') and type(source['group_id']) is str and
                source['group_id'] and all(source[k] == meta[k] for k in
                    ('id', 'split', 'group_id', 'source_sha256', 'input_sha256')) and
                meta['context_role'] == 'none_required', 'ordered source cohort joins differ')
        seen.add(source['id'])
        requests.append({'id': source['id'], 'source_text': text, 'context_text': '',
                         'requires_context_resolution': False})
        metadata.append(copy.deepcopy(meta))
    split_rows = {s: [r for r in metadata if r['split'] == s] for s in ('train', 'development')}
    require(all(len(rows) == 32 and len(Counter(r['group_id'] for r in rows)) == 8 and
                set(Counter(r['group_id'] for r in rows).values()) == {4}
                for rows in split_rows.values()), 'eight four-variant groups per32 split required')
    for field in ('id', 'source_sha256', 'input_sha256', 'group_id'):
        require(not ({r[field] for r in split_rows['train']} &
                     {r[field] for r in split_rows['development']}), 'source split overlap')
    return requests, metadata


def vector(value, dimension):
    require(type(value) is list and len(value) == dimension and
            all(type(v) in (int, float) and math.isfinite(v) and abs(v) <= 3.4028234e38 for v in value),
            'finite exact-width float32-range vector required')
    return value


def validate_native(bundle, inputs, encoding):
    closed(bundle, ('schema', 'profile', 'rows', 'producer_receipt', 'content_sha256'), 'native lane bundle')
    seal_check(bundle)
    profile = bundle['profile']
    seal_check(profile)
    require(bundle['schema'] == 'alignment-lane-bundle/v1' and digest(profile) == PROFILE_SHA and
            profile['lane_id'] == 'native768' and profile['dimension'] == 768 and
            profile['stage'] == 'raw_embedding' and
            profile['fit_input_recipe'] == profile['inference_input_recipe'] == 'exact_source_only/v1' and
            profile['producer']['model_id'] == 'Alibaba-NLP/gte-multilingual-base' and
            len(bundle['rows']) == 64, 'original native768 profile/recipe differs')
    require(encoding['lanes']['native768']['source_profile_sha256'] == PROFILE_SHA and
            encoding['lanes']['native768']['profile_id'] == profile['producer']['profile_id'] and
            encoding['source_inputs_binding']['sha256'] and encoding['formal_targets_read'] is False,
            'native encoding receipt differs')
    producer = bundle['producer_receipt']
    seal_check(producer)
    require(producer['profile_sha256'] == PROFILE_SHA and len(producer['rows']) == 64,
            'native producer row bindings differ')
    vectors = []
    for row, source, receipt in zip(bundle['rows'], inputs['rows'], producer['rows'], strict=True):
        require(row['id'] == source['id'] == receipt['id'] and row['status'] == receipt['status'] == 'available' and
                raw(row['input']) == raw(source['input']) and
                row['input_sha256'] == receipt['input_sha256'] == source['input_sha256'] and
                row['encoder_text'] == source['input']['source_text'] and
                row['encoder_text_sha256'] == receipt['encoder_text_sha256'] == source['source_sha256'],
                'exact producer source/context join differs')
        values = vector(row['vector'], 768)
        require(row['vector_sha256'] == receipt['vector_sha256'] == digest(values) and
                row['producer_row_sha256'] == digest(receipt) and row['reason'] is None and
                receipt['reason'] is None, 'native vector producer hash differs')
        vectors.append(values)
    return vectors, profile


def validate_endpoints(endpoints, numeric, arm, metadata, native_vectors):
    closed(endpoints, ('schema', 'lane_id', 'seed', 'architecture', 'source_profile_sha256',
        'native_train_bundle_binding', 'native_development_bundle_binding', 'new_checkpoint_binding',
        'new_training_report_binding', 'old_checkpoint_binding', 'pca_control', 'rows',
        'model_inference_executed', 'optimizer_updates', 'semantic_relevance_measured', 'content_sha256'), 'endpoints')
    for value in (endpoints, numeric):
        seal_check(value)
    require(endpoints['schema'] == 'source-only-expanded-reconstruction-endpoints/v1' and
            numeric['schema'] == 'source-only-expanded-reconstruction-numeric-report/v1' and
            endpoints['lane_id'] == numeric['lane_id'] == 'native768' and
            endpoints['seed'] == numeric['seed'] == arm['seed'] and
            endpoints['architecture'] == numeric['architecture'] == [768, 128, 64] and
            endpoints['source_profile_sha256'] == PROFILE_SHA and
            numeric['endpoint_binding'] == arm['endpoints_binding'] and
            endpoints['new_checkpoint_binding'] == numeric['new_checkpoint_binding'] and
            endpoints['new_training_report_binding'] == numeric['new_training_report_binding'] and
            endpoints['old_checkpoint_binding'] == numeric['old_checkpoint_binding'] and
            raw(endpoints['pca_control']) == raw(numeric['pca_control']) and
            endpoints['pca_control']['fit_rows'] == 32 and
            endpoints['pca_control']['development_rows_read_before_fit'] == 0 and
            endpoints['pca_control']['retained_axes'] == 31 and len(endpoints['rows']) == 64,
            'frozen same-seed numeric endpoint joins differ')
    require(endpoints['model_inference_executed'] is True and type(endpoints['optimizer_updates']) is int and
            endpoints['optimizer_updates'] == 0 and endpoints['semantic_relevance_measured'] is False and
            type(numeric['optimizer_updates']) is int and numeric['optimizer_updates'] == 0 and
            raw(numeric['masks']) == raw(dict.fromkeys(MASKS, 0)) and
            numeric['independent_semantic_accuracy_measured'] is False and
            numeric['qualified'] is False and numeric['proof_authority'] is False,
            'frozen numeric evidence scope differs')
    endpoint_by_id = {}
    for row in endpoints['rows']:
        require(type(row) is dict and type(row.get('id')) is str and row['id'] not in endpoint_by_id,
                'unique endpoint identities required')
        endpoint_by_id[row['id']] = row
    require(set(endpoint_by_id) == {m['id'] for m in metadata}, 'complete endpoint identity set differs')
    aligned_rows = [endpoint_by_id[m['id']] for m in metadata]
    for row, meta, native in zip(aligned_rows, metadata, native_vectors, strict=True):
        closed(row, ('id', 'split', 'group_id', 'source_sha256', 'context_role', 'panel_input_sha256',
                     'lane_input_sha256', 'endpoints'), 'endpoint row')
        require(all(row[k] == meta[k] for k in ('id', 'split', 'group_id', 'source_sha256', 'context_role')) and
                row['panel_input_sha256'] == row['lane_input_sha256'] == meta['input_sha256'] and
                set(row['endpoints']) == set(VIEWS), 'complete ordered endpoint row joins differ')
        for view, values in row['endpoints'].items():
            vector(values, 64 if view in ('new_latent', 'old_latent') else 31 if view == 'pca_latent' else 768)
        require(raw(row['endpoints']['raw_source']) == raw(native), 'raw conditioner differs from actual producer vector')
    # The evaluator serializes TRAIN followed by DEV. Preserve original source
    # order for split-local transformations through explicit identity joins.
    return aligned_rows


def validate_checkpoint_source(checkpoint, seed, sources, profile):
    """Check implementation and original producer identity before importing Torch."""
    require(checkpoint['schema'] == 'native-dimensional-source-span-checkpoint/v1' and
            checkpoint['lineage_id'] == 'native_dimensional_source_span_v1' and
            checkpoint['config']['latent_dimension'] == 768 and checkpoint['config']['latent_enabled'] is True and
            checkpoint['config']['seed'] == seed and checkpoint['progress']['optimizer_steps'] == 400,
            'retained selected400 native768 checkpoint required')
    expected_base = {field: sources[MODULES[index]][0]['sha256'] for field, index in
                     (('span', 6), ('codec', 5), ('canonical', 1), ('grammar', 4))}
    require(checkpoint['implementation'] == {'dimensions_sha256': sources[MODULES[7]][0]['sha256'],
                                           'base_span': expected_base} and
            checkpoint['source_parent_checkpoint']['implementation'] == expected_base,
            'retained checkpoint implementation source pins differ')
    contract = checkpoint['context_contract']
    closed(contract, ('dimension', 'representation_id', 'producer_sha256', 'training_index_sha256'), 'context contract')
    require(contract['dimension'] == 768 and contract['representation_id'] == profile['producer']['profile_id'] and
            checkpoint['context_contract_sha256'] == digest(contract, ascii=True) and
            checkpoint['source_parent_checkpoint_sha256'] == digest(checkpoint['source_parent_checkpoint'], ascii=True),
            'unchanged original context/source-parent identity differs')
    sha(contract['producer_sha256'])
    sha(contract['training_index_sha256'])
    return contract


class CapturedLoader(importlib.abc.Loader):
    def __init__(self, selected, data):
        self.selected, self.data = selected, data

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        module.__file__ = self.selected['path']
        exec(compile(self.data, self.selected['path'], 'exec'), module.__dict__)


class CapturedFinder(importlib.abc.MetaPathFinder):
    def __init__(self, sources):
        self.sources = sources

    def find_spec(self, fullname, path=None, target=None):
        if fullname in self.sources:
            reference, data = self.sources[fullname]
            return importlib.util.spec_from_loader(fullname, CapturedLoader(reference, data))
        if fullname == 'ipfs_datasets_py' or fullname.startswith('ipfs_datasets_py.'):
            raise ImportError('unselected canonical import: ' + fullname)
        return None


def install_sources(sources):
    require(not any(n == 'ipfs_datasets_py' or n.startswith('ipfs_datasets_py.') for n in sys.modules),
            'canonical modules imported before capture')
    parents = set()
    for name in sources:
        parts = name.split('.')
        parents.update('.'.join(parts[:n]) for n in range(1, len(parts)))
    for name in sorted(parents, key=lambda n: (n.count('.'), n)):
        package = types.ModuleType(name)
        package.__path__ = [str(REPOSITORY / Path(*name.split('.')))]
        package.__package__ = name
        package.__spec__ = importlib.machinery.ModuleSpec(name, loader=None, is_package=True)
        sys.modules[name] = package
        if '.' in name:
            parent, leaf = name.rsplit('.', 1)
            setattr(sys.modules[parent], leaf, package)
    finder = CapturedFinder(sources)
    sys.meta_path.insert(0, finder)
    return finder


def prepare_arm(rows, metadata, requests, arm, split):
    require(arm in CONTROLS and split in ('train', 'development'), 'prespecified control/split required')
    positions = [n for n, row in enumerate(metadata) if row['split'] == split]
    require(len(positions) == 32, 'full within-split32 control panel required')
    key = 'pca_reconstructed' if arm == 'pca_reconstructed' else 'new_reconstructed' if arm == 'new_ae_reconstructed' else 'raw_source'
    vectors = [copy.deepcopy(rows[n]['endpoints'][key]) for n in positions]
    panel = [copy.deepcopy(requests[n]) for n in positions]
    control = {'zero_raw': 'zero', 'disabled_raw': 'disabled', 'rotated_raw': 'rotate'}.get(arm, 'none')
    return panel, vectors, control


def receipt_summary(record):
    rows = record['rows']
    backend_rows = [r['decoder_row'] for r in rows if r['decoder_row'] is not None]
    return {'requested_rows': len(rows), 'preflight_outcomes': dict(Counter(r['preflight']['outcome'] for r in rows)),
            'source_outcomes': dict(Counter(r['outcome'] for r in rows)),
            'eligible_rows': record['eligible_count'], 'decoder_calls': record['decoder_call_count'],
            'decoder_completions': record['decoder_completion_count'],
            'backend_exception_type': record['backend_exception_type'],
            'decoder_status_counts': dict(Counter(r['status'] for r in backend_rows)),
            'decoder_reason_counts': dict(Counter(r['reason'] for r in backend_rows if r['reason'] is not None)),
            'syntax_valid_unaccepted_proposals': sum(r['family_syntax_checked'] is True for r in backend_rows),
            'semantic_support_established': False, 'semantic_accuracy_measured': False,
            'accepted_artifacts': 0, 'proof_calls': 0}


def compare_receipts(baseline, candidate):
    require([r['id'] for r in baseline['rows']] == [r['id'] for r in candidate['rows']],
            'matched all-request comparison identities required')
    changes = Counter()
    compared = 0
    maximum = 0.
    sum_difference = 0.
    for left, right in zip(baseline['rows'], candidate['rows'], strict=True):
        changes['source_outcome'] += left['outcome'] != right['outcome']
        changes['preflight'] += raw(left['preflight']) != raw(right['preflight'])
        a, b = left['decoder_row'], right['decoder_row']
        changes['decoder_presence'] += (a is None) != (b is None)
        if a is None or b is None:
            continue
        for field in ('status', 'reason', 'canonical_ir'):
            changes[field] += raw(a[field]) != raw(b[field])
        changes['status_reason_ir'] += any(raw(a[k]) != raw(b[k]) for k in ('status', 'reason', 'canonical_ir'))
        x = a.get('span_diagnostics', {}).get('modality_logits')
        y = b.get('span_diagnostics', {}).get('modality_logits')
        if x is not None and y is not None:
            require(len(x) == len(y) == 3 and all(math.isfinite(v) for v in x + y), 'finite three-logit comparison required')
            deltas = [abs(u - v) for u, v in zip(x, y, strict=True)]
            maximum = max(maximum, *deltas)
            sum_difference += math.fsum(deltas)
            compared += 1
    return {'requested_rows': len(baseline['rows']), 'changed_counts': dict(changes),
            'modality_logit_comparison_rows': compared, 'max_abs_modality_logit_difference': maximum if compared else None,
            'mean_abs_modality_logit_difference': sum_difference / (3 * compared) if compared else None,
            'semantic_improvement_measured': False}


def validate_plan(plan, self_binding):
    closed(plan, ('schema', 'helper_binding', 'bootstrap_binding', 'canonical_module_bindings',
        'cohort_binding', 'source_inputs_binding', 'encoding_report_binding', 'arms', 'controls',
        'authorization_scope', 'resource_limits', 'content_sha256'), 'downstream plan')
    seal_check(plan)
    require(plan['schema'] == 'source-only-frozen-downstream-span-plan/v1' and
            plan['helper_binding'] == self_binding and plan['bootstrap_binding']['sha256'] == BOOTSTRAP_SHA and
            raw(plan['controls']) == raw(list(CONTROLS)) and raw(plan['authorization_scope']) == raw(AUTHORIZATION) and
            raw(plan['resource_limits']) == raw(LIMITS), 'bounded source-only frozen plan differs')
    require(type(plan['arms']) is list and len(plan['arms']) == 3 and
            [a.get('seed') for a in plan['arms']] == list(SEEDS), 'all three fixed seeds required')
    for arm in plan['arms']:
        closed(arm, ('seed', 'checkpoint_binding', 'endpoints_binding', 'numeric_report_binding'), 'selected seed')
    require(type(plan['canonical_module_bindings']) is list and len(plan['canonical_module_bindings']) == len(MODULES),
            'complete canonical source closure required')
    for name, item in zip(MODULES, plan['canonical_module_bindings'], strict=True):
        closed(item, ('module', 'binding'), 'selected canonical module')
        require(item['module'] == name and Path(item['binding']['path']) ==
                REPOSITORY / Path(*name.split('.')).with_suffix('.py'), 'ordered canonical module path differs')


def run(plan_path, plan_sha, seed, output):
    started = time.monotonic()
    usage_before = resource.getrusage(resource.RUSAGE_SELF)
    cpu_before = usage_before.ru_utime + usage_before.ru_stime
    require(sys.flags.isolated and sys.dont_write_bytecode, 'selected interpreter -I -B required')
    require(seed in SEEDS, 'fixed decoder seed required')
    for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
        require(os.environ.get(name) == '1', 'one-thread numerical environment required')
    require(os.environ.get('CUDA_VISIBLE_DEVICES') == '' and
            os.environ.get('HF_HUB_OFFLINE') == os.environ.get('TRANSFORMERS_OFFLINE') == '1', 'offline CPU environment required')
    resource.setrlimit(resource.RLIMIT_AS, (LIMITS['address_space_bytes'], LIMITS['address_space_bytes']))
    resource.setrlimit(resource.RLIMIT_CPU, (LIMITS['cpu_seconds_soft'], LIMITS['cpu_seconds_hard']))
    resource.setrlimit(resource.RLIMIT_FSIZE, (MAX_BYTES, MAX_BYTES))
    capture = Capture()
    plan_binding = binding(plan_path)
    require(plan_binding['sha256'] == plan_sha, 'externally selected plan SHA differs')
    plan = capture.json(plan_binding)
    self_binding = binding(Path(__file__))
    capture.get(self_binding)
    validate_plan(plan, self_binding)
    require(not any(name in sys.modules for name in ('torch', 'safetensors')), 'providers imported before source capture')
    bootstrap_data = capture.get(plan['bootstrap_binding'])
    sources = {item['module']: (item['binding'], capture.get(item['binding']))
               for item in plan['canonical_module_bindings']}
    inputs = capture.json(plan['source_inputs_binding'])
    cohort = capture.json(plan['cohort_binding'])
    requests, metadata = validate_sources(inputs, cohort)
    encoding = capture.json(plan['encoding_report_binding'])
    seal_check(encoding)
    require(encoding['schema'] == 'expanded-source-native-encoding-report/v1' and
            encoding['source_inputs_binding'] == plan['source_inputs_binding'] and
            encoding['cohort_metadata_binding'] == plan['cohort_binding'] and
            raw(encoding['masks']) == raw(dict.fromkeys(MASKS, 0)), 'bound native source encoding joins differ')
    native_binding = encoding['artifacts']['native768']['full_bundle']
    native_vectors, profile = validate_native(capture.json(native_binding), inputs, encoding)
    # Capture every selected checkpoint/conditioner pin before any provider runs.
    for arm in plan['arms']:
        for key in ('checkpoint_binding', 'endpoints_binding', 'numeric_report_binding'):
            capture.get(arm[key])
    arm = next(a for a in plan['arms'] if a['seed'] == seed)
    endpoints = capture.json(arm['endpoints_binding'])
    numeric = capture.json(arm['numeric_report_binding'])
    rows = validate_endpoints(endpoints, numeric, arm, metadata, native_vectors)
    for key in ('native_train_bundle_binding', 'native_development_bundle_binding'):
        capture.get(endpoints[key])
    checkpoint = capture.json(arm['checkpoint_binding'])
    context_contract = validate_checkpoint_source(checkpoint, seed, sources, profile)
    checkpoint_before = digest(checkpoint, ascii=True)
    saved_optimizer_before = digest(checkpoint['optimizer_state'], ascii=True)
    output = Path(output)
    require(output.is_absolute() and not output.exists() and
            output.parent.is_dir() and not any(p.is_symlink() for p in output.parents), 'fresh nonsymlink output required')
    output.mkdir(mode=0o700)
    bootstrap = {'__name__': 'selected_native_bootstrap', '__file__': plan['bootstrap_binding']['path']}
    exec(compile(bootstrap_data, plan['bootstrap_binding']['path'], 'exec'), bootstrap)
    selected_providers = bootstrap['select_native_site']()
    install_sources(sources)
    owner = importlib.import_module(OPTIMIZER + 'legal_span_dimensions')
    wrapper = importlib.import_module(LEGAL + 'canonical_span_decoder')
    import torch
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    torch.set_default_dtype(torch.float32)
    torch.set_default_device('cpu')
    rng_before = torch.get_rng_state().clone()
    calls = Counter(optimizer_step_attempts=0, optimizer_updates=0, dimensional_restores=0,
                    embedded_parent_restores=0, model_constructors=0, wrapper_calls=0,
                    owner_decoder_calls=0, source_row_decode_calls=0, actual_model_forward_calls=0)

    def admission():
        require(time.monotonic() - started < LIMITS['cooperative_seconds'], 'soft wall budget exceeded')
        require(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss < LIMITS['cooperative_rss_kib'], 'cooperative RSS budget exceeded')

    def forbid_step(*args, **kwargs):
        calls['optimizer_step_attempts'] += 1
        raise RuntimeError('optimizer updates forbidden in frozen downstream evaluation')

    def counted(original, name):
        def invoke(*args, **kwargs):
            admission()
            calls[name] += 1
            return original(*args, **kwargs)
        return invoke

    torch.optim.Adam.step = forbid_step
    # Counters wrap unchanged routines and retain the restored Adam for checking.
    restored_optimizers = []
    parent_restore = owner.span._restore
    dimensional_restore = owner._restore

    def restore_parent(*args, **kwargs):
        calls['embedded_parent_restores'] += 1
        value = parent_restore(*args, **kwargs)
        restored_optimizers.append(('embedded_source_parent', value[1], value[2]))
        return value

    def restore_dimensional(*args, **kwargs):
        calls['dimensional_restores'] += 1
        value = dimensional_restore(*args, **kwargs)
        restored_optimizers.append(('retained_dimensional_decoder', value[1], value[2]))
        return value

    owner.span._restore = restore_parent
    owner._restore = restore_dimensional
    owner.span._model = counted(owner.span._model, 'model_constructors')
    admission()
    decoder = owner.DimensionalSpanDecoder(checkpoint)
    require(calls['dimensional_restores'] == calls['embedded_parent_restores'] == 1 and
            calls['model_constructors'] == 3, 'unexpected native restoration counts')
    require(all(p.device.type == 'cpu' and p.dtype == torch.float32 for p in decoder.model.parameters()), 'CPU float32 model required')
    decoder.decode_formal_logic = counted(decoder.decode_formal_logic, 'owner_decoder_calls')
    decoder._decode = counted(decoder._decode, 'source_row_decode_calls')
    decoder.model.forward = counted(decoder.model.forward, 'actual_model_forward_calls')
    model_before = digest({k: v.detach().tolist() for k, v in decoder.model.state_dict().items()}, ascii=True)
    require(model_before == digest(checkpoint['model_state'], ascii=True), 'restored model differs from checkpoint')

    def optimizer_digest(model, optimizer):
        return digest(owner.span._pack(model, optimizer)[1], ascii=True)

    optimizer_before = [(role, optimizer_digest(model, optimizer)) for role, model, optimizer in restored_optimizers]
    require(len(optimizer_before) == 2 and optimizer_before[-1][1] == saved_optimizer_before,
            'saved Adam state restoration differs')
    records, summaries, comparisons = {}, {}, {}
    for control in CONTROLS:
        records[control], summaries[control], comparisons[control] = {}, {}, {}
        for split in ('train', 'development'):
            admission()
            panel, vectors, owner_control = prepare_arm(rows, metadata, requests, control, split)
            before_forward = calls['actual_model_forward_calls']
            before_calls = calls['owner_decoder_calls']
            calls['wrapper_calls'] += 1
            with torch.inference_mode():
                record = wrapper.decode_with_preflight(decoder, panel, vectors, latent_ablation=owner_control)
            wrapper.validate_preflight_decoding(record, panel, vectors)
            summary = receipt_summary(record)
            summary['actual_model_forward_calls'] = calls['actual_model_forward_calls'] - before_forward
            summary['observed_owner_decoder_calls'] = calls['owner_decoder_calls'] - before_calls
            require(summary['observed_owner_decoder_calls'] == record['decoder_call_count'], 'wrapper owner call counts differ')
            require(summary['actual_model_forward_calls'] <= record['eligible_count'], 'forward counts exceed eligibility')
            summary['generation_executed'] = summary['actual_model_forward_calls'] > 0
            records[control][split] = record
            summaries[control][split] = {'receipt_binding': write(output / (control + '-' + split + '.json'), record), **summary}
            comparisons[control][split] = compare_receipts(records['raw_source'][split], record)
    admission()
    capture.recheck()
    model_after = digest({k: v.detach().tolist() for k, v in decoder.model.state_dict().items()}, ascii=True)
    require(model_after == model_before and digest(checkpoint, ascii=True) == checkpoint_before and
            digest(decoder.checkpoint, ascii=True) == checkpoint_before, 'model/checkpoint changed during inference')
    require(optimizer_before == [(role, optimizer_digest(model, optimizer)) for role, model, optimizer in restored_optimizers],
            'restored Adam state changed during inference')
    require(torch.equal(rng_before, torch.get_rng_state()) and calls['optimizer_step_attempts'] == 0 and
            all(p.grad is None for p in decoder.model.parameters()), 'global RNG/optimizer/gradient preservation differs')
    for reference in selected_providers.values():
        bootstrap['checked_bytes'](reference['path'], reference['sha256'], reference['bytes'])
    profiles = {
        'raw_source': {'kind': 'original_pinned_native_source', 'source_profile_sha256': PROFILE_SHA},
        'pca_reconstructed': {'kind': 'out_of_distribution_frozen_pca_inverse_perturbation',
                              'original_producer_receipt_claimed': False, 'pca_control': endpoints['pca_control']},
        'new_ae_reconstructed': {'kind': 'out_of_distribution_frozen_ae_reconstruction_perturbation',
                                 'original_producer_receipt_claimed': False, 'checkpoint_binding': endpoints['new_checkpoint_binding']},
        'zero_raw': {'kind': 'zero_vector_ablation', 'original_producer_receipt_claimed': False},
        'disabled_raw': {'kind': 'original_raw_vector_gate_disabled', 'latent_input_enabled': False},
        'rotated_raw': {'kind': 'within_split32_one_position_rotation_before_preflight',
                        'original_matched_source_producer_receipt_claimed': False}}
    report = {
        'schema': 'source-only-frozen-downstream-span-report/v1', 'status': 'completed',
        'seed': seed, 'plan_binding': plan_binding, 'helper_binding': self_binding,
        'checkpoint_binding': arm['checkpoint_binding'], 'endpoints_binding': arm['endpoints_binding'],
        'numeric_report_binding': arm['numeric_report_binding'], 'source_inputs_binding': plan['source_inputs_binding'],
        'cohort_binding': plan['cohort_binding'], 'native_bundle_binding': native_binding,
        'preserved_input_bindings': capture.references(), 'selected_provider_entrypoints': selected_providers,
        'original_context_contract': context_contract, 'context_contract_unchanged': True,
        'conditioner_profiles': profiles, 'arms': summaries, 'comparisons_against_raw': comparisons,
        'conditioner_width': 768, 'compression_storage_or_latency_benefit_measured': False,
        'cost_scope': 'frozen_decoder_execution_excludes_upstream_encoding_pca_and_ae_production',
        'counts': dict(calls), 'saved_optimizer_state_sha256': saved_optimizer_before,
        'restored_optimizer_state_checksums': [{'role': role, 'sha256': checksum} for role, checksum in optimizer_before],
        'model_state_sha256': model_before, 'model_state_unchanged': True,
        'checkpoint_unchanged': True, 'restored_adam_unchanged': True, 'global_cpu_rng_unchanged': True,
        'parameter_gradients_created': False, 'all64_requests_retained_per_control': True,
        'control_transformation_scope': 'complete_within_split32_before_preflight',
        'native768_only': True, 'matched_8d_384d_decoder_experiments_executed': False,
        'frozen_pca_ae_conditioners_reused': True, 'new_pca_fits': 0, 'new_ae_fits': 0,
        'new_encoder_calls': 0, 'teacher_forcing': False, 'target_access': False,
        'semantic_accuracy_measured': False, 'semantic_relevance_measured': False,
        'source_fidelity_established': False, 'training_executed': False, 'qualified': False,
        'proof_authority': False, 'accepted': False, 'proof_calls': 0,
        'masks': dict.fromkeys(MASKS, 0), 'source_vector_tables_included': False,
        'output_scope': 'unaccepted_single_rule_literal_source_span_proposals',
        'preflight_scope': 'unassessed_means_eligible_not_semantically_supported',
        'site_pth_processing': False, 'canonical_package_initializers_executed': False,
        'dependency_scope': 'selected_entrypoints_and_captured_canonical_modules_not_complete_binary_closure',
        'os_sandbox': False, 'resources': {'limits': LIMITS, 'peak_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            'elapsed_seconds': time.monotonic() - started,
            'cpu_seconds': resource.getrusage(resource.RUSAGE_SELF).ru_utime +
                resource.getrusage(resource.RUSAGE_SELF).ru_stime - cpu_before,
            'observation_scope': 'worker_before_final_report_serialization'}}
    report_binding = write(output / 'downstream-report.json', report)
    print(json.dumps({'status': 'completed', 'seed': seed, 'report_binding': report_binding,
                      'counts': dict(calls), 'qualified': False}, sort_keys=True))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--plan-sha256', required=True)
    parser.add_argument('--seed', type=int, choices=SEEDS, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    return run(args.plan, args.plan_sha256, args.seed, args.output)


if __name__ == '__main__':
    raise SystemExit(main())
