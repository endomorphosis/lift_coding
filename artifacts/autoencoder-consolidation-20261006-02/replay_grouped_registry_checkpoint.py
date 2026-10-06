"""Repeat two retained selection witnesses through the opt-in registry adapter."""
from pathlib import Path
import hashlib
import json

import torch

from ipfs_datasets_py.logic.formalization.autoencoder import legal_grouped_span_decoder_v2 as head
from ipfs_datasets_py.optimizers.logic_theorem_optimizer import autoencoder_runtime_registry as registry

A = Path(__file__).resolve().parent
V2 = Path('/home/barberb/lift_coding/artifacts/legal-grouped-head-v2-20261006')


def ref(path):
    return {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'bytes': path.stat().st_size}


def load(path):
    return json.loads(path.read_text())


def checked(binding):
    path = Path(binding['path'])
    assert ref(path) == binding
    return load(path)


assert Path(registry.__file__).resolve().is_relative_to(A / 'datasets-integration')
assert Path(head.__file__).resolve().is_relative_to(A / 'datasets-integration')
torch.set_num_threads(2)
before = ref(Path(registry.__file__))
selected = load(V2 / 'run-02/selected.json')
checkpoint = selected['selected']['checkpoint']
assert checkpoint['sha256'] == 'efd7f7e71159592672769c7f580112917381e9a854f021a72f8de1613d299b95'
assert ref(Path(checkpoint['path'])) == checkpoint
audit = load(V2 / 'native-audit-01/results.json')
predictions = checked(audit['predictions'])
decoded = checked(audit['decoded_records'])
selected_witnesses = [predictions[0], predictions[2]]
assert selected_witnesses[0]['actual_prediction']['raw_prediction']['count'] == 8
assert selected_witnesses[1]['actual_prediction']['blockers'] == ['learned_source_unsupported']
runtime = registry.open_runtime('legal_ir', 'source_conditioned_grouped_v2',
    checkpoint_path=checkpoint['path'], checkpoint_sha256=checkpoint['sha256'])
assert runtime.describe()['optimizer_steps'] == 480
original_predictor = head.predict_grouped_span_decoder
calls = []


def observed_predictor(model, source_text, modal_scope):
    assert model is runtime._model
    assert type(source_text) is str and modal_scope in head.SCOPES
    calls.append({'source_text': source_text, 'modal_scope': modal_scope})
    return original_predictor(model, source_text, modal_scope)


head.predict_grouped_span_decoder = observed_predictor
rows = []
try:
    for index, witness in enumerate(selected_witnesses):
        inputs = witness['input']
        assert type(inputs) is dict and set(inputs) == {'source_text', 'modal_scope'}
        output = runtime.decode_formal_logic(inputs['source_text'], modal_scope=inputs['modal_scope'])
        prior = witness['actual_prediction']
        expected_blockers = prior['blockers'] + ([] if index else decoded[0]['blockers'])
        assert output['blockers'] == expected_blockers
        assert all(output[key] == value for key, value in prior.items() if key != 'blockers')
        assert output['formal_output'] == (decoded[0] if index == 0 else None)
        for key in ('qualified', 'admitted', 'formalized', 'accepted', 'source_semantics_verified',
                    'proof_ready', 'kernel_checked', 'lake_executed', 'promotion_performed'):
            assert output[key] is False
        rows.append({'case_id': witness['case_id'], 'input': inputs, 'output': output,
                     'retained_neural_prediction_exactly_reproduced': True,
                     'retained_native_rendering_exactly_reproduced': True if index == 0 else None})
finally:
    head.predict_grouped_span_decoder = original_predictor
assert calls == [witness['input'] for witness in selected_witnesses]
assert ref(Path(registry.__file__)) == before
assert ref(Path(checkpoint['path'])) == checkpoint
result = {
    'schema': 'grouped-legal-runtime-selected-checkpoint-replay/v1', 'status': 'passed',
    'runner': ref(Path(__file__)), 'registry_source': before, 'checkpoint': checkpoint,
    'selected_receipt': ref(V2 / 'run-02/selected.json'),
    'prior_native_audit': ref(V2 / 'native-audit-01/results.json'),
    'prior_predictions': audit['predictions'], 'prior_native_records': audit['decoded_records'],
    'descriptor': runtime.describe(), 'rows': rows, 'predictor_inputs_observed': calls,
    'actual_source_only_predictions': len(calls), 'eight_member_native_formula_count': 1,
    'learned_refusal_count': 1, 'checkpoint_steps': 480,
    'target_fields_supplied_to_predictor': False, 'checkpoint_or_production_modified': False,
    'training_calls': 0, 'new_lake_builds': 0, 'semantic_accuracy_claimed': False,
    'fresh_final_scored': False, 'source_semantics_verified': False, 'qualified': False,
    'scope': 'Two previously selected engineering witnesses replayed through the new registry; not an accuracy estimate or new native build.',
}
path = A / 'registry-selected-checkpoint-replay.json'
assert not path.exists()
path.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
print(json.dumps({'status': 'passed', 'receipt': ref(path), 'actual_source_only_predictions': len(calls)}))
