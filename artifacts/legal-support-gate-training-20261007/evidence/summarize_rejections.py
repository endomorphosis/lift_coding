"""Postfit pure analysis of saved TRAIN/selection panels; no forwards or updates."""
from pathlib import Path
import hashlib,importlib.util,json,os,sys
F=Path(__file__).resolve().parent;R=Path('/home/barberb/lift_coding/external/ipfs_datasets/workspace/test-logs/legal-trigger-readout-pilot-20261007-01/support-gate-20261007-01/results')
os.environ['CUDA_VISIBLE_DEVICES']='';os.environ['OMP_NUM_THREADS']='2';os.environ['MKL_NUM_THREADS']='2';sys.path.insert(0,str(F/'datasets'))
spec=importlib.util.spec_from_file_location('_frozen_support_gate_analysis',F/'run_support_gate_experiment.py');owner=importlib.util.module_from_spec(spec);spec.loader.exec_module(owner)
spec=importlib.util.spec_from_file_location('_frozen_score_owner',owner.SCORER);scorer=importlib.util.module_from_spec(spec);spec.loader.exec_module(scorer)
inputs=json.loads((F/'selection-inputs.json').read_text());refs=json.loads((F/'selection-references.json').read_text());parent=json.loads((R/'parent-selection-predictions.json').read_text())['rows'];baseline=owner.score_components(scorer.score,parent,refs,inputs)
rows={}
for kind in ('global','predicted_trigger'):
 rows[kind]=[]
 for step in (0,120,240):
  panel=json.loads((R/kind/f'selection-predictions-{step}.json').read_text())['rows'];s=owner.score_components(scorer.score,panel,refs,inputs)
  rules=dict(negative_emitted_no_increase=s['negative_emitted_proposal_count']<=baseline['negative_emitted_proposal_count'],positive_whole_no_loss=s['positive_exact_count']>=baseline['positive_exact_count'],positive_emission_no_loss=s['positive_emitted_proposal_count']>=baseline['positive_emitted_proposal_count'],positive_learned_refusal_no_increase=s['positive_learned_refusal_count']<=baseline['positive_learned_refusal_count'])
  rows[kind].append(dict(step=step,all_floors_satisfied=all(rules.values()),floors=rules,paired=owner.transitions(parent,panel,refs),score=s))
ti=json.loads((F/'train-inputs.json').read_text());tr=json.loads((F/'train-references.json').read_text());tp=json.loads((R/'parent-TRAIN-predictions.json').read_text())['rows'];train={'parent':owner.score_components(scorer.score,tp,tr,ti)}
train_pairs={}
for kind in ('global','predicted_trigger'):
 panel=json.loads((R/kind/'last-TRAIN-predictions.json').read_text())['rows'];train[kind]=owner.score_components(scorer.score,panel,tr,ti);train_pairs[kind]=owner.transitions(tp,panel,tr)
value=dict(schema='support-gate-postfit-selection-TRAIN-diagnostic/v1',label_informed_postfit=True,analysis_model_calls=0,analysis_optimizer_steps=0,selection_or_checkpoint_changes=0,fresh_final_or_retention_references_opened=False,selection=rows,baseline_selection=baseline,last_TRAIN=train,last_TRAIN_pairs=train_pairs,script=owner.pin(Path(__file__)),runner=owner.pin(F/'run_support_gate_experiment.py'),scorer=owner.pin(owner.SCORER),panels={str(p):owner.pin(p) for p in [R/'parent-selection-predictions.json',R/'parent-TRAIN-predictions.json',*[R/k/f'selection-predictions-{s}.json' for k in rows for s in (0,120,240)],*[R/k/'last-TRAIN-predictions.json' for k in rows]]})
p=F/'rejection-diagnostics.json';assert not p.exists();p.write_text(json.dumps(value,indent=2)+'\n');print(json.dumps(dict(last_TRAIN={k:dict(whole=v['positive_exact_count'],negative_emitted=v['negative_emitted_proposal_count'],BCE=v['support_probability_BCE'],modal_misspelling=v['negative_categories']['modal_misspelling']) for k,v in train.items()},selection_pairs={k:{r['step']:r['paired']['counts'] for r in rows[k]} for k in rows})))
