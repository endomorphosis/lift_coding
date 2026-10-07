"""Prepare four normative states against existing original source-only caches."""
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = Path('/home/barberb/lift_coding')
DATASETS = ROOT / '.worktrees/normative-decoder-runtime-datasets-20261007'
sys.path.insert(0, str(DATASETS))


def pin(path):
    p = Path(path).resolve(strict=True)
    data = p.read_bytes()
    return {'path': str(p), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')
    return pin(path)


def main():
    from ipfs_datasets_py.logic.formalization.autoencoder import normative_legal_ir_runtime as runtime
    assert 'torch' not in sys.modules
    destination = HERE / 'preflight-final'
    destination.mkdir(exist_ok=True)
    survey_path = ROOT / 'artifacts/contextual-legal-runtime-20261006/source-survey/source-survey.json'
    auth_path = ROOT / 'artifacts/normative-checkpoint-availability-20261006/authentication/authenticated-states.json'
    survey, auth = json.loads(survey_path.read_text()), json.loads(auth_path.read_text())
    folder = Path(runtime.__file__).parent
    owner_pins = {name: pin(folder / (name + '.py')) for name in runtime.SOURCE_OWNER_NAMES}
    records = []
    for state in auth['states']:
        if state['role'] != 'selected':
            continue
        lane = next(p for p in survey['lanes'] if p['dimension'] == state['dimension'])
        cached = lane['cached_file_pins']
        rows = json.loads(Path(cached['source_only_inputs']['path']).read_text())
        checkpoint = {k: state['original_checkpoint_pin'][k] for k in ('path', 'bytes', 'sha256')}
        preprocessing = {k: state['preprocessing_pin'][k] for k in ('path', 'bytes', 'sha256')}
        assert pin(checkpoint['path']) == checkpoint and pin(preprocessing['path']) == preprocessing
        options = dict(request=dict(ir_family_id='legal_ir', dimension=state['dimension'],
            dimension_role='input_embedding', task_id='semantic_IR_reconstruction',
            checkpoint_sha256=checkpoint['sha256'], decoder_contract_id=runtime.DECODER_CONTRACT_ID,
            training_recipe_name=state['recipe']['name']), checkpoint_pin=checkpoint,
            preprocessing_pin=preprocessing, donor_checkpoint_pin=survey['original_raw_donor_pin'],
            source_inputs_pin=cached['source_only_inputs'], source_contexts_pin=cached['source_only_contexts'],
            source_owner_pins=owner_pins, row_ids=[r['id'] for r in rows], deadline_seconds=120)
        plan = runtime.prepare_normative_legal_ir_runtime(**options)
        assert 'torch' not in sys.modules and not any(plan['authority'].values())
        key = f"{state['dimension']}-{state['arm']}"
        plan_pin = save(destination / (key + '-metadata-plan.json'),
                        {k: v for k, v in plan.items() if k != 'source_inputs'})
        options_pin = save(destination / (key + '-options.json'), options)
        records.append(dict(dimension=state['dimension'], arm=state['arm'],
            row_count=len(plan['row_ids']), model_tensor_sha256=plan['model_tensor_sha256'],
            original_checkpoint_pin=checkpoint, model_manager_selector=plan['model_manager_selector'],
            plan_pin=plan_pin, options_pin=options_pin))
    assert len(records) == 4
    assert owner_pins == {name: pin(folder / (name + '.py')) for name in runtime.SOURCE_OWNER_NAMES}
    result = dict(schema='normative-original-assets-runtime-preflight/v1', completed=True,
        script_pin=pin(__file__), source_survey_pin=pin(survey_path), state_authentication_pin=pin(auth_path),
        selected_states=records, torch_imported=False, model_or_manager_loaded=False,
        original_targets_accessed=False, source_inputs_scope='original caller-bound cached validation split',
        registered_selector_resolution_performed=False, runtime_admitted=False,
        teacher_qualified=False, proof_authority=False)
    receipt = save(destination / 'original-assets-preflight.json', result)
    print(json.dumps({'completed': True, 'states': len(records), 'receipt': receipt}))


if __name__ == '__main__':
    main()
