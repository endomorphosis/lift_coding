#!/usr/bin/env python3
"""Bind actual executed canaries and independent engineering review by CID."""
from pathlib import Path
import json,sys
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
sys.path.insert(0,str(ROOT/'external/ipfs_datasets'))
from learned_route import implementation_identity,file_digest,digest,validate_qualification,execute_checks,GuidanceBoundaryError
from structural_checks import checker_contract,CHECKS
from ipfs_datasets_py.utils.cid_utils import cid_for_dag_json

review=json.loads((HERE/'engineering_review_autoencoder.json').read_text())
assert review['approved'] and review['overlay_sha256']==implementation_identity()['overlay_sha256']
summaries=[]
for seed in (104729,130363,155921):
 path=HERE/f'qualification_v5_seed{seed}'/'summary.json'
 s=json.loads(path.read_text());assert s['implementation']==implementation_identity();assert s['checker_contract']==checker_contract()
 for member in ('cases.json','predictions.json','candidates.json'):
  assert file_digest(path.parent/member)==s[member+'_sha256']
 summaries.append(s)
required=('real_checkpoint_predictions_consumed','paired_on_off_effect_observed','checker_preserved','rollback_passed','final_examples_opened_is_false')
evidence={k:all(s[k] for s in summaries) for k in required}
evidence.update(schema='autoformalization-guidance-aggregate-qualification/v1',seed_summaries=summaries,case_count=sum(s['case_count'] for s in summaries),native_compiler_calls=sum(s['native_compiler_calls'] for s in summaries),actual_check_calls=sum(s['actual_check_calls'] for s in summaries),model_inference_calls=sum(s['model_inference_calls'] for s in summaries),observed_order_changes=sum(s['observed_order_changes'] for s in summaries),interpretation='Actual learned obligation-frequency scheduling only. Canonical content, checker outcomes, and proof boundaries unchanged; no semantic improvement claimed.')
q={'schema':'autoformalization-learned-route-qualification/v1','qualified':True,'implementation':implementation_identity(),'checker_contract':checker_contract(),'independent_engineering_review':review,'independent_review_cid':cid_for_dag_json(review),'qualification_evidence':evidence,'qualification_evidence_sha256':digest(evidence),'allowed_model_bindings':[s['model_binding'] for s in summaries],'historical_canonical_mutation_adapter_qualified':False,'semantic_fidelity_measured':False}
q['qualification_cid']=cid_for_dag_json(q)
# Replay with FINAL-strength runtime gates on constructed controls only.
replays=[]
for seed in (104729,130363,155921):
 base=HERE/f'qualification_v5_seed{seed}'
 predictions=json.loads((base/'predictions.json').read_text());candidates=json.loads((base/'candidates.json').read_text())
 for p,c in zip(predictions,candidates):
  validate_qualification(q,p)
  on=execute_checks(p,c,CHECKS,qualification=q,qualification_required=True,expected_prediction_sha256=digest(p))
  off=execute_checks(p,c,CHECKS,enabled=False,qualification=q,qualification_required=True,expected_prediction_sha256=digest(p))
  assert {x['check']:x['result'] for x in on['checks_executed']}=={x['check']:x['result'] for x in off['checks_executed']}
  replays.append({'seed':seed,'record_id':p['record_id'],'qualified_on':on,'qualified_off':off})
# In particular, a success-returning impostor callback cannot receive credit.
p,c=predictions[0],candidates[0]
try:execute_checks(p,c,dict(CHECKS,modal_well_formedness=lambda _: {'passed':True}),qualification=q,qualification_required=True,expected_prediction_sha256=digest(p))
except GuidanceBoundaryError:impostor_rejected=True
else:raise AssertionError('Impostor checker accepted')
# CID corruption cannot pass even if all descriptive success flags remain true.
bad=json.loads(json.dumps(q));bad['qualification_evidence']['case_count']+=1
try:validate_qualification(bad,p)
except GuidanceBoundaryError:cid_corruption_rejected=True
else:raise AssertionError('Corrupt qualification accepted')
(HERE/'qualification.json').write_text(json.dumps(q,indent=2)+'\n')
(HERE/'qualified_replays.json').write_text(json.dumps({'scope':'constructed_only_no_final_examples','qualification_cid':q['qualification_cid'],'replays':replays,'impostor_callback_rejected':impostor_rejected,'corrupt_qualification_rejected':cid_corruption_rejected},indent=2)+'\n')
print(json.dumps({'qualified':True,'qualification_cid':q['qualification_cid'],'cases':evidence['case_count'],'checks':evidence['actual_check_calls'],'strong_gate_replay_pairs':len(replays)}))
