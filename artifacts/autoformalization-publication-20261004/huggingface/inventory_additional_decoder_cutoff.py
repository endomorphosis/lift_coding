"""Bounded static weight inventory of six explicitly selected later lineages."""

import hashlib
import json
import os
from pathlib import Path

WORK = Path(__file__).resolve().parent
ROOT = Path('/home/barberb/lift_coding/external/ipfs_datasets')
CUTOFF = {
    'native4096-layer-reclaim-pilot-r3-20261004': 'cd204bb3b7fa11b8c0c4e7626f46139df79aa4fb5a9a79b90718c32d49276a44',
    'native4096-conditioning-20261004': '4140f47f4cbc96855206d9922591dd99e12456157bc3cb21c9f024fa5b65b649',
    'native4096-balanced-cohort-20261004': 'f99c1b09cede1789d7168d64ad1e2fd8de0c25382e36e8ce2a935a1355417ef4',
    'decoder-eight-head-rate-20261004': '830d50d3971e9ace166e58d4dfb69293275bf24ea0455d1fced80bdbf26d625f',
    'decoder-eight-source-preconditioning-20261004': 'dfc43564b297a900ea45437aadfca74ec2bf23a00cab3c30f720cdc325a6fb8d',
    'decoder-selected-continuation-20261004': 'bb1efa109608ab0092ad0b6845f7a2f172f6ebe896cc1705e73fabe91c1a10fa',
}


def prepare_inventory():
    helper = WORK / 'inventory_formula_sidecars.py'
    data = helper.read_bytes()
    if hashlib.sha256(data).hexdigest() != '551aea7aba055a75a46dbd939a98087a272155dd91200f3efd3a9842d30e3b12':
        raise ValueError('selected static JSON helpers differ')
    namespace = {'__name__': '_bounded_inventory_helpers', '__file__': str(helper)}
    exec(compile(data, str(helper), 'exec'), namespace)
    read, raw, ordinary_json, numeric_count = (namespace[key] for key in ('read', 'raw', 'ordinary_json', 'numeric_count'))
    inputs = [read(helper)[1], read(Path(__file__).resolve())[1]]
    weights = []
    lineages = []
    for lineage, expected in CUTOFF.items():
        directory = ROOT / 'workspace/test-logs' / lineage / 'training-r1/results'
        summary, summary_binding = ordinary_json(directory / 'summary.json', expected)
        inputs.append(summary_binding)
        if summary.get('complete') is not True or summary.get('qualified') is not False or summary.get('admitted') is not False:
            raise ValueError('selected complete unqualified lineage differs')
        before = len(weights)
        updates = 0
        if lineage.startswith('native4096-'):
            report, binding = ordinary_json(directory / 'training.json', summary['training_sha256'])
            inputs.append(binding)
            if report['dimension'] != 4096 or report['learned_embedding_reconstruction'] is not False or report['optimizer_resumable'] is not False:
                raise ValueError('native4096 experimental formula-head scope differs')
            models = [(report, '/model_state')] if 'model_state' in report else [(arm, f'/arms/{i}/model_state') for i, arm in enumerate(report['arms'])]
            for model, pointer in models:
                state = model['model_state']
                steps = model.get('optimizer_steps', report.get('fit', {}).get('optimizer_steps'))
                if type(steps) is not int or steps <= 0:
                    raise ValueError('actual saved fit update count unavailable')
                updates += steps
                weights.append({'lineage': lineage, 'arm': model.get('arm', 'two-source-pilot'), 'dimension': 4096,
                    'role': 'final_attempt', 'source_file_binding': binding, 'model_state_JSON_pointer': pointer,
                    'weights_sha256': hashlib.sha256(raw(state)).hexdigest(),
                    'finite_saved_numerical_leaf_count': sum(numeric_count(value) for value in state.values()),
                    'completed_optimizer_steps': steps, 'model_state_parameter_key_count': len(state),
                    'model_state_serialized_bytes': len(raw(state)), 'native_profile_producer_declaration': summary['native_profile'],
                    'raw_training_report_body_must_not_be_uploaded': True,
                    'checkpoint_extraction_needed': True, 'runtime_restore_smoke_executed': False,
                    'source_fidelity_established': False, 'qualified': False, 'proof_authority': False})
            if updates != summary['optimizer_steps']:
                raise ValueError('native4096 per-arm update counts differ from summary')
        else:
            for item in summary['runs']:
                arm, binding = ordinary_json(item['summary_path'], item['summary_sha256'])
                inputs.append(binding)
                report, report_binding = ordinary_json(arm['training_ref']['path'], arm['training_ref']['sha256'])
                inputs.append(report_binding)
                steps = report['optimizer_steps']
                if type(steps) is not int or steps <= 0:
                    raise ValueError('actual completed fit count unavailable')
                updates += steps
                for role in ('initial', 'selected', 'last-attempt'):
                    reference = arm['states'][role]
                    state, state_binding = ordinary_json(reference['path'], reference['sha256'])
                    inputs.append(state_binding)
                    if state['role'] != role or state['dimension'] != arm['dimension'] or state['qualified'] is not False:
                        raise ValueError('later state lineage/authority differs')
                    if hashlib.sha256(raw(state['model_state'])).hexdigest() != state['weights_sha256']:
                        raise ValueError('later saved JSON weights digest differs')
                    weights.append({'lineage': lineage, 'arm': arm['arm'], 'dimension': arm['dimension'], 'role': role,
                        'source_file_binding': state_binding, 'model_state_JSON_pointer': '/model_state',
                        'weights_sha256': state['weights_sha256'],
                        'finite_saved_numerical_leaf_count': sum(numeric_count(value) for value in state['model_state'].values()),
                        'completed_fit_optimizer_steps': steps, 'selected_epoch': report['selected_epoch'],
                        'checkpoint_extraction_needed': False, 'runtime_restore_smoke_executed': False,
                        'source_fidelity_established': False, 'qualified': False, 'proof_authority': False})
        lineages.append({'lineage': lineage, 'summary_binding': summary_binding, 'schema': summary['schema'],
                         'retained_weight_endpoints': len(weights) - before, 'completed_optimizer_updates': updates})
    return {'schema': 'fixed-cutoff-additional-formula-decoder-weight-inventory/v1', 'selected_lineages': lineages,
        'weights': weights, 'weight_endpoint_count': len(weights),
        'raw_state_file_count': sum(not row['checkpoint_extraction_needed'] for row in weights),
        'embedded_native4096_weight_count': sum(row['checkpoint_extraction_needed'] for row in weights),
        'historical_completed_optimizer_updates': sum(row['completed_optimizer_updates'] for row in lineages),
        'source_bindings': list({row['path']: row for row in inputs}.values()),
        'cutoff_scope': 'exact_six_named_lineages_and_pinned_summaries_no_chasing_later_runs',
        'new_model_calls': 0, 'new_optimizer_updates': 0, 'native_worker_calls': 0,
        'training_report_bodies_or_reference_banks_copied': False, 'uploads': 0,
        'complete_runtime_or_producer_dependency_closure_claimed': False,
        'runtime_tensor_digest_recomputed': False, 'qualified': False,
        'source_fidelity_established': False, 'proof_authority': False}


if __name__ == '__main__':
    result = prepare_inventory()

    def raw(value):
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()

    result['content_sha256'] = hashlib.sha256(raw(result)).hexdigest()
    data = raw(result) + b'\n'
    target = WORK / 'additional_decoder_cutoff_inventory.json'
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, 'wb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps({'inventory': {'path': str(target), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()},
                      'weight_endpoints': result['weight_endpoint_count'], 'historical_updates': result['historical_completed_optimizer_updates']}))
