"""Audit saved trial artifacts without importing Torch or executing a model."""
from pathlib import Path
from hashlib import sha256
import argparse, importlib.util, json, math, sys

F = Path(__file__).resolve().parent
def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode()
def pin(path):
    path = Path(path).resolve(); raw = path.read_bytes()
    return dict(path=str(path), bytes=len(raw), sha256=sha256(raw).hexdigest())
def load(path):
    return json.loads(Path(path).read_text())
def bound(reference):
    assert pin(reference['path']) == reference
    return load(reference['path'])

p = argparse.ArgumentParser(); p.add_argument('--results', type=Path, required=True)
args = p.parse_args(); root = args.results.resolve()
plan = load(F/'experiment-plan.json'); result = load(root/'training-results.json')
assert result['status'] == 'completed' and result['plan'] == pin(F/'experiment-plan.json')
assert result['runner'] == pin(F/'run_retention_experiment.py')
assert result['actual_optimizer_updates'] == result['support_head_updates'] == 480
assert result['action_head_updates'] == result['additional_parent_forwards'] == 0
assert result['training_input_records'] == result['online_teacher_decoded_rows'] == 7680
assert result['frozen_parent_tensor_paths'] == 480
assert result['frozen_all_structural_postfit_rows'] == 1280
assert result['parent_full_model_and_Adam_unchanged'] is True
assert result['source_only'] is True and result['latent_conditioned'] is False
assert all(result[key] is False for key in ('legal_gold','semantic_admission','Lake_executed',
    'existing_weights_changed','final_references_used_for_training_or_selection',
    'retention_references_used_for_training_or_selection'))
barrier = bound(result['selection_barrier'])
assert barrier['references_parsed'] is False and barrier['actual_optimizer_calls'] == 480
outputs = bound(result['predictions_barrier'])
assert outputs['evaluation_references_parsed'] is False and len(outputs['panels']) == 15
source = F/'datasets/ipfs_datasets_py/logic/formalization/autoencoder/legal_scope_retention_selection.py'
spec = importlib.util.spec_from_file_location('_pure_trial_selector', source)
policy = importlib.util.module_from_spec(spec); sys.modules[spec.name] = policy
spec.loader.exec_module(policy)
assert 'torch' not in sys.modules
config = policy.SelectionConfig(source_profile=plan['source_profile'])
baseline = load(root/'selection-baseline-floors.json')['panel']
parent_raw = Path(plan['parent_checkpoint']['path']).read_bytes()
arms = {}
for arm in plan['arms']:
    data = result['arms'][arm]; losses = load(root/arm/'losses.json')
    assert len(losses) == data['completed_support_updates'] == 240
    assert [r['update'] for r in losses] == list(range(1,241))
    for row in losses:
        assert row['objective'] == arm and row['retention_lambda'] == (0.0 if arm == 'bce' else 1.0)
        assert row['optimizer_step_executed'] and row['encoded_examples'] == 16
        assert row['supported_examples'] == row['unsupported_examples'] == 8
        assert row['shared_tensor_forward_calls'] == row['frozen_parent_tensor_paths'] == 1
        assert row['additional_parent_forwards'] == 0 and row['teacher_source_rows_checked'] == 16
        assert row['retention_eligible_examples'] == sum(row['anchor_mask'])
        assert len(row['anchor_mask']) == len(row['parent_emitted_proposal_mask']) == 16
        assert math.isclose(row['loss'], row['support_loss'] + row['weighted_retention_loss'], abs_tol=2e-6)
        assert row['weighted_retention_loss'] == (0.0 if arm == 'bce' else row['retention_loss'])
    candidates = []
    for candidate in data['selection_candidates']:
        step = candidate['completed_updates']; checkpoint = bound(candidate['checkpoint'])
        assert checkpoint['steps'] == step and checkpoint['config']['objective'] == arm
        assert checkpoint['parent']['json_utf8'].encode() == parent_raw
        assert checkpoint['parent']['sha256'] == plan['parent_checkpoint']['sha256']
        assert sha256(canonical({k:v for k,v in checkpoint.items() if k != 'checkpoint_sha256'})).hexdigest() == checkpoint['checkpoint_sha256']
        state = checkpoint['optimizer']['state']
        if step == 0:
            assert state == {} and candidate['panel'] == baseline
        else:
            assert len(state) == 4
            assert all(s['step']['values'] == [float(step)] for s in state.values())
            assert any(any(x != 0 for x in s['exp_avg']['values']) for s in state.values())
        assert policy.eligible(candidate['panel'], baseline, config=config) == candidate['eligible']
        assert policy.retention_report(candidate['panel'], baseline, config=config) == candidate['retention_report']
        candidates.append(dict(completed_updates=step,panel=candidate['panel'],
                               checkpoint_sha256=candidate['checkpoint']['sha256']))
    chosen, decision = policy.select(candidates, baseline, config=config)
    assert chosen['completed_updates'] == data['selected']['completed_updates']
    assert decision == data['selection_decision'] == load(root/arm/'selection-decision.json')
    assert data['selected'] == load(root/arm/'selected.json')
    assert data['teacher_source_rows_checked'] == 3840 and data['additional_parent_forwards'] == 0
    assert data['frozen_parent_tensor_paths'] == 240
    arms[arm] = dict(selected_updates=chosen['completed_updates'],
        selected_fitted_gain=decision['selected_fitted_gain'],
        candidate_retention=[dict(step=c['completed_updates'],eligible=c['eligible'],
                                 report=c['retention_report']) for c in data['selection_candidates']],
        nonzero_hinge_updates=sum(r['retention_loss']>0 for r in losses),
        first_BCE=losses[0]['support_loss'],last_BCE=losses[-1]['support_loss'])
for name, reference in outputs['panels'].items():
    panel = bound(reference); assert len(panel['rows']) == 128
    assert panel['references_accessed_by_inference'] is False
    for row in panel['rows']:
        prediction = row['prediction']
        assert prediction['formal_output'] is None
        assert not any(prediction[k] for k in ('source_semantics_verified','accepted','qualified',
            'formalized','proof_ready','proof_authority','target_access','targets_used_at_inference'))
        if prediction['proposal']: assert not any(prediction['proposal']['masks'].values())
for name, cohort in plan['retention'].items():
    prior = bound(cohort['archived_parent_predictions'])['rows']
    actual = bound(outputs['panels']['parent/'+name])['rows']
    assert len(prior) == len(actual) == 128
    assert all(a['id']==b['id'] and a['prediction']==b['prediction'] for a,b in zip(prior,actual,strict=True))
assert 'torch' not in sys.modules
receipt = dict(schema='support-retention-saved-artifact-audit/v1',passed=True,findings=[],
    model_forwards=0,optimizer_updates=0,Torch_imported=False,
    actual_trial_optimizer_calls=480,actual_trial_encoded_presentations=7680,
    historical_parent_full_output_dictionaries_exact=512,
    arms=arms,scores=result['scores'],paired_transitions=result['paired_transitions'],
    raw_source_inputs_only=True,native_latent_or_legal_promotion=False,
    result=pin(root/'training-results.json'),source=pin(__file__))
with (F/'trial-artifact-audit.json').open('x') as out:
    json.dump(receipt,out,indent=2);out.write('\n')
print(json.dumps(dict(passed=True,arms=arms)))
