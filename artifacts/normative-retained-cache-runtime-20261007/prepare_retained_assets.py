"""Metadata-only preparation of four original states and retained exposed-v3 caches."""
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = Path('/home/barberb/lift_coding')
DATASETS = ROOT / '.worktrees/normative-cache-input-datasets-20261007'
sys.path.insert(0, str(DATASETS))


def pin(path):
    p = Path(path).resolve(strict=True)
    data = p.read_bytes()
    return {'path': str(p), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')
    return pin(path)


def main():
    from ipfs_datasets_py.logic.formalization.autoencoder import normative_cached_legal_ir_runtime as runtime
    assert 'torch' not in sys.modules and 'transformers' not in sys.modules
    destination = HERE / 'preflight'
    destination.mkdir(exist_ok=True)
    auth_path = ROOT / 'artifacts/normative-checkpoint-availability-20261006/authentication/authenticated-states.json'
    auth = json.loads(auth_path.read_text())
    cohort = ROOT / 'external/ipfs_datasets/workspace/test-logs/decoder-fresh-normative-style-r2-20261004/preparation-r1/results'
    donor = ROOT / 'artifacts/source-reconstruction-v2-20261001/run-01/legal_ir/raw_ce-1729-checkpoint.json'
    owner_pins = {name: pin(path) for name, path in runtime.source_owner_paths().items()}
    records = []
    for state in auth['states']:
        if state['role'] != 'selected':
            continue
        dimension = state['dimension']
        source_cache = pin(cohort / f'dimension-inputs-{dimension}.json')
        rows = json.loads(Path(source_cache['path']).read_text())['rows']
        checkpoint = {k: state['original_checkpoint_pin'][k] for k in ('path', 'bytes', 'sha256')}
        preprocessing = {k: state['preprocessing_pin'][k] for k in ('path', 'bytes', 'sha256')}
        assert pin(checkpoint['path']) == checkpoint and pin(preprocessing['path']) == preprocessing
        options = dict(request=dict(ir_family_id='legal_ir', dimension=dimension,
            dimension_role='input_embedding', task_id='semantic_IR_reconstruction',
            checkpoint_sha256=checkpoint['sha256'], decoder_contract_id=runtime.DECODER_CONTRACT_ID,
            training_recipe_name=state['recipe']['name']), checkpoint_pin=checkpoint,
            preprocessing_pin=preprocessing, donor_checkpoint_pin=pin(donor),
            source_cache_pin=source_cache, source_plan_pin=pin(cohort / 'source-plan.json'),
            production_pin=pin(cohort / f'production-{dimension}.json'), source_owner_pins=owner_pins,
            row_ids=[r['id'] for r in rows], deadline_seconds=120)
        plan = runtime.prepare_normative_cached_legal_ir_runtime(**options)
        assert not any(plan['authority'].values()) and plan['source_cache_binding']['encoder_execution_attested'] is False
        assert 'torch' not in sys.modules and 'transformers' not in sys.modules
        key = f"{dimension}-{state['arm']}"
        metadata_pin = save(destination / (key + '-metadata-plan.json'), {k:v for k,v in plan.items() if k != 'source_inputs'})
        options_pin = save(destination / (key + '-options.json'), options)
        records.append(dict(dimension=dimension, arm=state['arm'], row_count=len(plan['row_ids']),
            model_tensor_sha256=plan['model_tensor_sha256'], original_checkpoint_pin=checkpoint,
            model_manager_selector=plan['model_manager_selector'], plan_pin=metadata_pin, options_pin=options_pin))
    assert len(records) == 4 and all(pin(p['path']) == p for p in owner_pins.values())
    result = dict(schema='normative-retained-source-cache-preflight/v1', completed=True, script_pin=pin(__file__),
        state_authentication_pin=pin(auth_path), selected_states=records, torch_imported=False, transformers_imported=False,
        model_or_manager_loaded=False, original_targets_accessed=False, source_only=True,
        cached_cohort='exposed_v3_fresh_modality', reused_original_embeddings=True,
        registered_selector_resolution_performed=False, runtime_admitted=False, teacher_qualified=False,
        proof_authority=False, fresh_semantic_holdout=False)
    receipt = save(destination / 'retained-assets-preflight.json', result)
    print(json.dumps({'completed': True, 'states':len(records), 'receipt':receipt}))


if __name__ == '__main__':
    main()
