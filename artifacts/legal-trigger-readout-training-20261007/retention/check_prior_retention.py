"""Postfit retention only; no selection or optimizer updates."""
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import torch
from ipfs_datasets_py.logic.formalization.autoencoder import legal_scope_span_decoder as donor
from ipfs_datasets_py.logic.formalization.autoencoder import legal_scope_trigger_readout as head

F=Path(__file__).resolve().parent
OLD=Path('/home/barberb/lift_coding/artifacts/legal-next-training-20261007-01')
R=Path('/home/barberb/lift_coding/external/ipfs_datasets/workspace/test-logs/legal-trigger-readout-pilot-20261007-01/attempt-01/results')
spec=importlib.util.spec_from_file_location('frozen_trigger_runner',F/'run_trigger_experiment.py')
runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
assert runner.pin(F/'run_trigger_experiment.py')['sha256']=='8db24c4c0e39ebb106a72031fa53aa9f153fed94f1ddaf1b58ba7ef9ad093f00'
torch.set_num_threads(2);torch.use_deterministic_algorithms(True);assert not torch.cuda.is_initialized()
out=F/'prior-retention';assert not out.exists();runner.mkdir_durable(out)
inputs=json.loads((OLD/'final-inputs.json').read_text());models={};saved={};panels={};refs={}
for mode in ('global','predicted_trigger'):
    selected=json.loads((R/mode/'selected.json').read_text());checkpoint=runner.load(selected['checkpoint'])
    model,optimizer,steps=head.restore_trigger_readout_checkpoint(checkpoint)
    saved[mode]=(checkpoint,model,optimizer,steps)
    panels[mode],refs[mode]=runner.collect(model,inputs,out/(mode+'-predictions.json'))
    assert head.save_trigger_readout_checkpoint(model,optimizer,steps=steps)==checkpoint
donor_json=saved['global'][1].donor_checkpoint
model,optimizer,steps=donor.restore_scope_span_checkpoint(donor_json)
panels['donor'],refs['donor']=runner.collect(model,inputs,out/'donor-predictions.json',donor=True)
assert donor.save_scope_span_checkpoint(model,optimizer,steps=steps)==donor_json
for mode in ('global','predicted_trigger'):runner.assert_frozen_panels(panels[mode],panels['donor'])
runner.write(out/'all-predictions-before-reference-join.json',dict(panels=refs,references_parsed_by_evaluator=False))
references=json.loads((OLD/'final-references.json').read_text())
results={mode:runner.score(panel,references,inputs) for mode,panel in panels.items()}
original=json.loads((OLD/'completion.json').read_text())
assert results['donor']['positive_exact_count']==12 and results['donor']['positive_raw_modality_exact']==25
receipt=dict(schema='trigger-readout-prior-exposed-cohort-retention/v1',status='completed',role='postfit_retention_only',
    selected_adapter_steps={mode:saved[mode][3] for mode in saved},additional_optimizer_updates=0,
    selected_weights_changed=False,fresh_selection_changed=False,training_lease_claimed=False,
    old_exposed_inputs=runner.pin(OLD/'final-inputs.json'),old_exposed_references=runner.pin(OLD/'final-references.json'),
    panels=refs,metrics=results,source=runner.pin(Path(__file__)),runner=runner.pin(F/'run_trigger_experiment.py'),
    producer_pins=head.producer_pins(),legal_gold=False,Lake_executed=False)
runner.write(out/'retention-results.json',receipt)
print(json.dumps(dict(retention={k:dict(class_exact=v['positive_raw_modality_exact'],whole_exact=v['positive_exact_count'],condition_exact=v['nonempty_condition_exact_count']) for k,v in results.items()},additional_optimizer_updates=0)))
