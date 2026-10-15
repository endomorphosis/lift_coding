#!/usr/bin/env python3
"""Run actual native compiler/check/learned-head pairs on non-final controls."""
from __future__ import annotations
import argparse,copy,hashlib,json,os,resource,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
for k,v in {'IPFS_DATASETS_PY_MINIMAL_IMPORTS':'1','IPFS_DATASETS_AUTO_INSTALL':'false','IPFS_KIT_AUTO_INSTALL_DEPS':'0','HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1','CUDA_VISIBLE_DEVICES':'','OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1'}.items():os.environ[k]=v
sys.path.insert(0,str(ROOT/'external/ipfs_datasets'));sys.path.insert(1,str(HERE.parent/'autoencoder'));sys.path.insert(2,str(HERE.parent/'pipeline'))
from learned_route import *
from structural_checks import CHECKS,checker_contract
from source_only_eval import load_model,predict_row,sha
from native_c import setup

SOURCES=(
 ('obligation','Company A shall submit backup report.'),
 ('permission','Company A may submit backup report.'),
 ('prohibition','Company A must not submit backup report.'),
 ('exception','Company A shall submit backup report within 10 days unless emergency.'),
 ('empty','Administrative heading.'),
)


def outcomes(receipt):return {r['check']:r['result'] for r in receipt['checks_executed']}


def main():
 p=argparse.ArgumentParser();p.add_argument('--compact',required=True,type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
 hard=resource.getrlimit(resource.RLIMIT_AS)[1];cap=min(4<<30,hard) if hard!=resource.RLIM_INFINITY else 4<<30;resource.setrlimit(resource.RLIMIT_AS,(cap,cap));os.sched_setaffinity(0,set(sorted(os.sched_getaffinity(0))[-2:]))
 started=time.monotonic();a.output.mkdir(parents=True,exist_ok=False)
 model,provenance=load_model(a.compact)
 compile_text=setup(False)[0]
 rows=[];predictions=[];originals=[]
 for case_id,source in SOURCES:
  row={'record_id':'constructed-guidance:'+case_id,'text':source,'family':'constructed','title':'constructed','section_id':case_id,'citation':'constructed'}
  prediction=predict_row(model,row,provenance);predictions.append(prediction)
  ir=compile_text(source,row['record_id']).to_dict()
  candidate={'record_id':row['record_id'],'text_sha256':hashlib.sha256(source.encode()).hexdigest(),'canonical_ir':ir,'source_text':source,'checker_contract':checker_contract()}
  originals.append(candidate)
  variants=[('pristine',candidate)]
  if case_id=='obligation':
   bad=copy.deepcopy(candidate);bad['canonical_ir']['formulas'][0]['operator']['symbol']='invented';variants.append(('bad_operator',bad))
   bad=copy.deepcopy(candidate);bad['canonical_ir']['formulas'][0]['provenance']['end_char']=len(source)+100;variants.append(('bad_span',bad))
   bad=copy.deepcopy(candidate);bad['canonical_ir']['normalized_text']='Other text';variants.append(('bad_normalized_source',bad))
   bad=copy.deepcopy(candidate);bad['canonical_ir']['formulas'][0]['provenance']['source_id']='foreign';variants.append(('bad_source_id',bad))
   bad=copy.deepcopy(candidate);bad['canonical_ir']['formulas'][0]['operator']['symbol']='invented';bad['canonical_ir']['formulas'][0]['provenance']['end_char']=len(source)+100;variants.append(('both_fail',bad))
  for variant,record in variants:
   disabled=execute_checks(prediction,record,CHECKS,enabled=False)
   enabled=execute_checks(prediction,record,CHECKS,enabled=True,expected_prediction_sha256=digest(prediction))
   rollback=execute_checks(prediction,record,CHECKS,enabled=False)
   expected={'modal_well_formedness':variant not in {'bad_operator','both_fail'},'provenance_preservation':variant not in {'bad_span','bad_normalized_source','bad_source_id','both_fail'}}
   observed={name:out['passed'] for name,out in outcomes(enabled).items()}
   if observed!=expected:raise AssertionError((case_id,variant,expected,observed,outcomes(enabled)))
   assert outcomes(disabled)==outcomes(enabled)==outcomes(rollback)
   assert disabled['check_order']==rollback['check_order']==list(REQUIRED_CHECKS)
   assert all(r['all_required_checks_executed'] for r in (disabled,enabled,rollback))
   rows.append({'case_id':case_id,'variant':variant,'constructed_expected':expected,'disabled':disabled,'enabled':enabled,'rollback':rollback,'outcomes_unchanged':True,'rollback_passed':True})
 # Malformed/frozen-output contract probes are qualification only.
 p0=predictions[0];c0=originals[0];rejections=[]
 mutations={
  'wrong_source_hash':lambda p:p.update(parser_text_sha256='0'*64),
  'sample_memory':lambda p:p.update(sample_memory_used=True),
  'reference_targets':lambda p:p.update(reference_targets_used=True),
  'nonfinite_probability':lambda p:p['proof_heads_by_family']['frame_logic']['heads']['obligation_family']['probabilities'].update(provenance_preservation=float('nan')),
  'wrong_vocabulary':lambda p:p['proof_heads_by_family']['frame_logic']['heads']['obligation_family']['probabilities'].update(invented=0.0),
 }
 for name,mutate in mutations.items():
  corrupt=copy.deepcopy(p0);mutate(corrupt)
  try:choose_check_order(corrupt,c0)
  except (GuidanceBoundaryError,ValueError):rejections.append(name)
  else:raise AssertionError('Malformed prediction accepted: '+name)
 try:choose_check_order(p0,c0,expected_prediction_sha256='0'*64)
 except GuidanceBoundaryError:rejections.append('frozen_prediction_digest_mismatch')
 else:raise AssertionError('Frozen hash mismatch accepted')
 try:choose_check_order(p0,c0,qualification_required=True)
 except GuidanceBoundaryError:rejections.append('unqualified_final_execution')
 else:raise AssertionError('Unqualified final execution accepted')
 summary={'schema':'autoformalization-guidance-execution-qualification/v1','scope':'constructed_canaries_only_no_final_examples','created_unix_seconds':time.time(),'implementation':implementation_identity(),'checker_contract':checker_contract(),'model_binding':{k:provenance[k] for k in ('arm_id','seed','checkpoint_sha256','compact_sha256')},'real_checkpoint_predictions_consumed':all(r['enabled']['learned_parameters_consumed'] for r in rows),'paired_on_off_effect_observed':any(r['enabled']['order_changed'] for r in rows),'checker_preserved':all(r['outcomes_unchanged'] for r in rows),'rollback_passed':all(r['rollback_passed'] for r in rows),'final_examples_opened_is_false':True,'case_count':len(rows),'native_compiler_calls':len(SOURCES),'actual_check_calls':len(rows)*3*2,'model_inference_calls':len(SOURCES),'observed_order_changes':sum(r['enabled']['order_changed'] for r in rows),'negative_control_rejections':rejections,'native_proof_truth_measured':False,'historical_canonical_mutation_adapter_qualified':False,'wall_seconds':time.monotonic()-started,'cpu_seconds':time.process_time(),'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,'qualification_runner_sha256':file_digest(Path(__file__))}
 for name,value in [('cases.json',rows),('predictions.json',predictions),('candidates.json',originals)]:
  (a.output/name).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n');summary[name+'_sha256']=file_digest(a.output/name)
 (a.output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary),flush=True)
if __name__=='__main__':main()
