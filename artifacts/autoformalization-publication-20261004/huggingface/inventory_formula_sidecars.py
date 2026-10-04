"""Static inventory of two distinct historical formula-sidecar comparisons.

Only saved JSON and explicitly named source files are read. No provider import,
tensor deserialization, model execution, fit, reference scoring or upload occurs.
Training reports are inspected for selected counters only and never copied.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import stat
from pathlib import Path

ROOT = Path('/home/barberb/lift_coding/external/ipfs_datasets')
LOGS = ROOT / 'workspace/test-logs'
COMPARISONS = {
    'decoder-four-width-20261004': ('54a74986f0121f018af05fb96237a4094f0415c79d0025b6450be799919e8f98', 340),
    'decoder-continuation-20261004': ('8c246877a04e159f64f6bd6e752432a548e8ed1a1cb560ba62aaa70898e1af9b', 170),
}
SOURCE_ROOTS = [ROOT, *[LOGS / run / 'experiment-source' for run in (
    'decoder-four-width-20261004', 'decoder-continuation-20261004',
    'decoder-content-matched-r3-20261004', 'decoder-modality-gap-r2-20261004',
    'decoder-source-margin-20261004')]]
AUTHORITY = ('qualified', 'admitted', 'proof_authority', 'source_semantics_verified',
             'checkpoint_promoted', 'formalized', 'roundtrip_ok', 'fresh_holdout')
MAX_FILE = 64 * 1024 ** 2


def require(value, message):
    if not value:
        raise ValueError(message)


def raw(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def read(path, expected=None):
    path = Path(path).absolute()
    require(not any(p.is_symlink() for p in (path, *path.parents)), 'nonsymlink ordinary input required')
    with path.open('rb') as stream:
        before = os.fstat(stream.fileno())
        require(stat.S_ISREG(before.st_mode) and 0 < before.st_size <= MAX_FILE, 'bounded ordinary file required')
        data = stream.read(MAX_FILE + 1)
        after = os.fstat(stream.fileno())
    require((before.st_ino, before.st_size, before.st_mtime_ns) ==
            (after.st_ino, after.st_size, after.st_mtime_ns), 'input changed during read')
    sha = hashlib.sha256(data).hexdigest()
    require(expected is None or sha == expected, 'selected input hash differs: ' + str(path))
    return data, {'path': str(path), 'bytes': len(data), 'sha256': sha}


def ordinary_json(path, expected=None):
    data, binding = read(path, expected)

    def pairs(items):
        value = {}
        for key, item in items:
            require(key not in value, 'duplicate JSON key')
            value[key] = item
        return value

    result = json.loads(data.decode('utf-8'), object_pairs_hook=pairs,
                        parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite JSON')))
    require(type(result) is dict, 'ordinary JSON object required')
    return result, binding


def numeric_count(value, depth=0):
    require(depth <= 16, 'saved numerical state depth exceeded')
    if type(value) is list:
        return sum(numeric_count(item, depth + 1) for item in value)
    require(type(value) in (int, float) and math.isfinite(value), 'finite saved numerical leaf required')
    return 1


def prepare_inventory():
    groups = []
    all_bindings = {}

    def bind(binding):
        old = all_bindings.setdefault(binding['path'], binding)
        require(old == binding, 'same-path file binding collision')
        return binding

    for comparison, (expected_summary, steps) in COMPARISONS.items():
        directory = LOGS / comparison / 'training-r1/results'
        aggregate, summary_binding = ordinary_json(directory / 'summary.json', expected_summary)
        bind(summary_binding)
        require(aggregate['complete'] is True and len(aggregate['runs']) == 6, 'six complete arms required')
        require(all(aggregate.get(key) is False for key in AUTHORITY), 'aggregate authority differs')
        arms = []
        for selected in aggregate['runs']:
            arm, arm_binding = ordinary_json(selected['summary_path'], selected['summary_sha256'])
            bind(arm_binding)
            require(arm['arm'] == selected['arm'] and arm['seed'] == 1729 and arm['dimension'] in (8, 384, 768)
                    and arm['budget_completed'] is True, 'arm identity/budget differs')
            require(all(arm.get(key) is False for key in AUTHORITY), 'arm authority differs')
            report, report_binding = ordinary_json(arm['training_ref']['path'], arm['training_ref']['sha256'])
            bind(report_binding)
            require(report['optimizer_steps'] == steps and report['stopped_reason'] == 'epochs_completed'
                    and report['optimizer_resumable'] is False, 'completed weights-only training count differs')
            states = []
            for role in ('initial', 'selected', 'last-attempt'):
                reference = arm['states'][role]
                state, state_binding = ordinary_json(reference['path'], reference['sha256'])
                bind(state_binding)
                require(state_binding['bytes'] == reference['bytes'] and state['tensor_sha256'] == reference['tensor_sha256'],
                        'saved state bytes/declared runtime tensor identity differs')
                require(state['schema'] == 'private-native-dimension-source-state/v1' and state['dimension'] == arm['dimension']
                        and state['role'] == role and state['optimizer_resumable'] is False, 'state lineage/role differs')
                require(all(state.get(key) is False for key in AUTHORITY), 'state authority differs')
                require(hashlib.sha256(raw(state['model_state'])).hexdigest() == state['weights_sha256'], 'saved JSON weight digest differs')
                leaf_count = sum(numeric_count(value) for value in state['model_state'].values())
                architecture = state['architecture']
                initializer = state['initializer_receipt']
                require(initializer['learned_projection_reconstruction'] is False
                        and initializer['reconstruction_mse_scope'] == 'identity_by_construction_not_learned_reconstruction'
                        and architecture['production_runtime_compatible'] is False, 'experimental sidecar/reconstruction scope differs')
                states.append({'role': role, 'file_binding': state_binding, 'weights_sha256': state['weights_sha256'],
                    'producer_declared_runtime_tensor_sha256': state['tensor_sha256'],
                    'runtime_tensor_digest_independently_recomputed': False, 'finite_saved_numerical_leaf_count': leaf_count,
                    'selected': state['selected'], 'architecture_schema': architecture['schema'],
                    'native_input_dimension': initializer['input_dimension'], 'residual_projection_width': initializer['projection_width'],
                    'projected_output_dimension': initializer['projected_output_dimension'],
                    'hidden_width': architecture['hidden_width'], 'vocabulary_size': architecture['vocabulary_size'],
                    'source_context_required': architecture['source_context_required'],
                    'architecture_sha256': hashlib.sha256(raw(architecture)).hexdigest(),
                    'codec_sha256': hashlib.sha256(raw(state['codec'])).hexdigest(),
                    'input_transform_sha256': hashlib.sha256(raw(state['input_transform'])).hexdigest(),
                    'production_runtime_compatible': False, 'learned_vector_reconstruction': False,
                    'optimizer_resumable': False, **dict.fromkeys(AUTHORITY, False)})
            arms.append({'arm': arm['arm'], 'dimension': arm['dimension'], 'seed': 1729, 'summary_binding': arm_binding,
                'recipe': arm['recipe'], 'completed_optimizer_steps': steps, 'selected_epoch': report['selected_epoch'],
                'training_report_binding_private_not_for_upload': report_binding,
                'parent_endpoint': arm.get('parent_endpoint'), 'parent_state': arm.get('parent_state'),
                'exact_optimizer_resume': False, 'states': states})
        sources = []
        for key, expected in aggregate['source_dependencies'].items():
            require(re.fullmatch(r'[0-9a-f]{64}', expected), 'ordinary declared source SHA required')
            _, relative = key.split(':', 1)
            require(not Path(relative).is_absolute() and '..' not in Path(relative).parts, 'safe explicit source path required')
            matches = []
            for source_root in SOURCE_ROOTS:
                candidate = source_root / relative
                if candidate.is_file():
                    data, binding = read(candidate)
                    if hashlib.sha256(data).hexdigest() == expected:
                        matches.append(bind(binding))
            sources.append({'producer_source_key': key, 'producer_sha256': expected, 'matching_explicit_source_files': matches})
        groups.append({'comparison': comparison, 'summary_binding': summary_binding, 'producer_elapsed_seconds': aggregate['elapsed_seconds'],
            'arm_count': 6, 'state_count': 18, 'completed_optimizer_updates': 6 * steps,
            'state_bytes': sum(s['file_binding']['bytes'] for arm in arms for s in arm['states']),
            'arms': arms, 'producer_source_pins': sources,
            'source_pin_keys_matched_from_bounded_candidates': sum(bool(row['matching_explicit_source_files']) for row in sources),
            'source_pin_key_count': len(sources), 'complete_dependency_closure_claimed': False})
    producer = Path(__file__).resolve()
    bind(read(producer)[1])
    return {'schema': 'historical-formula-sidecar-static-inventory/v1', 'comparisons': groups,
        'comparison_count': 2, 'fit_count': 12, 'state_count': 36,
        'total_completed_optimizer_updates_in_historical_reports': sum(g['completed_optimizer_updates'] for g in groups),
        'state_bytes': sum(g['state_bytes'] for g in groups), 'selected_input_bindings': list(all_bindings.values()),
        'saved_finite_JSON_weight_digest_checked': True, 'runtime_model_restore_smoke_executed': False,
        'training_reports_read_for_counters_only': True, 'training_reports_or_reference_payloads_copied_for_upload': False,
        'scope': 'original_340_step_comparison_and_distinct_170_step_continuation_only_not_all_later_doc_lineages',
        'runtime_calls': 0, 'model_calls': 0, 'optimizer_updates_by_inventory': 0, 'uploads': 0,
        'complete_runtime_loader_packaging_claimed': False, **dict.fromkeys(AUTHORITY, False)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = prepare_inventory()
    result['content_sha256'] = hashlib.sha256(raw(result)).hexdigest()
    data = raw(result) + b'\n'
    descriptor = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, 'wb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps({'inventory': {'path': str(args.output), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()},
                      'fit_count': result['fit_count'], 'state_count': result['state_count'], 'state_bytes': result['state_bytes']}))


if __name__ == '__main__':
    main()
