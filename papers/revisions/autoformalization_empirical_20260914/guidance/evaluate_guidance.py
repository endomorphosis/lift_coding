#!/usr/bin/env python3
"""Frozen complete-population paired learned scheduling and rollback experiment.

Joins source-only T3 outputs to native C candidate packets by exact source IDs
and parser-prefix hashes. Every record is retained, including missing candidates
and failed checks. These are three-seed scheduler runs, not semantic annotations.
"""
from __future__ import annotations
import argparse,collections,hashlib,json,os,resource,statistics,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
sys.path.insert(0,str(ROOT/'external/ipfs_datasets'))
os.environ.update(IPFS_DATASETS_PY_MINIMAL_IMPORTS='1',IPFS_DATASETS_AUTO_INSTALL='false',IPFS_KIT_AUTO_INSTALL_DEPS='0',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',CUDA_VISIBLE_DEVICES='')
from learned_route import digest,execute_checks,file_digest,implementation_identity
from structural_checks import CHECKS,checker_contract

STATS_CONFIG={
 'schema':'autoformalization-guidance-paired-stats/v1','seeds':[104729,130363,155921],
 'population':1913,'comparison':'off/on/rollback on identical source-prefix candidate',
 'executed_order':['off','on','rollback'],'early_stopping':False,
 'eligibility':'C compile_status measured and nonempty formulas and both structural checks pass',
 'cost_scope':'actual serial rerun wall time; fixed order, so no speedup inference',
 'inferential_semantic_claims':False,'independent_replications':'three retained training seeds; same source population',
}


def profile():
 return {'runner_sha256':file_digest(Path(__file__)),'scheduler':implementation_identity(),'checker_contract':checker_contract(),'qualification_sha256':file_digest(HERE/'qualification.json'),'statistics':STATS_CONFIG}


def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for chunk in iter(lambda:f.read(8<<20),b''):h.update(chunk)
 return h.hexdigest()


def load_rows(path):
 result={}
 with Path(path).open() as f:
  for line in f:
   row=json.loads(line);rid=row['record_id']
   if rid in result:raise ValueError('Duplicate record ID in '+str(path))
   result[rid]=row
 return result


def outcomes(receipt):return {r['check']:r['result'] for r in receipt['checks_executed']}


def summarize(rows):
 counts=collections.Counter();timing={key:[] for key in ('off','on','rollback')};paired=[]
 for row in rows:
  counts['records']+=1
  if row['C_compile_status']=='measured':counts['C_compiled']+=1
  if row['formula_count']>0:counts['nonempty_candidates']+=1
  if row['on']['learned_parameters_consumed']:counts['learned_consumptions']+=1
  if row['on']['order_changed']:counts['order_changes']+=1
  if row['outcomes_unchanged']:counts['outcomes_unchanged']+=1
  if row['rollback_passed']:counts['rollback_passed']+=1
  if row['on']['all_passed']:counts['all_structural_checks_pass']+=1
  if row['eligible']:counts['eligible_nonempty_checked_candidates']+=1
  before,after=row['off']['first_failure_index'],row['on']['first_failure_index']
  if before is not None and after is not None:
   counts['records_with_failure']+=1
   if after<before:counts['first_failure_earlier']+=1
   elif after>before:counts['first_failure_later']+=1
   else:counts['first_failure_same_position']+=1
  for condition in timing:timing[condition].append(row[condition]['wall_seconds'])
  paired.append(row['on']['wall_seconds']-row['off']['wall_seconds'])
  for c in ('off','on','rollback'):
   counts['actual_check_calls']+=len(row[c]['checks_executed'])
   counts['check_execution_errors']+=sum(r['status']=='error' for r in row[c]['checks_executed'])
 return {'counts':dict(counts),'wall_seconds':{k:{'sum':sum(v),'mean':statistics.mean(v),'median':statistics.median(v)} for k,v in timing.items()},'mean_paired_on_minus_off_seconds':statistics.mean(paired),'interpretation':'Order is the treatment. Identical outcomes do not show semantic improvement; all checks run, fixed condition order prevents a speedup claim.'}


def main():
 p=argparse.ArgumentParser();p.add_argument('--sources',required=True,type=Path);p.add_argument('--c-results',required=True,type=Path);p.add_argument('--predictions',required=True,nargs='+',type=Path);p.add_argument('--output',required=True,type=Path);p.add_argument('--freeze',required=True,type=Path);p.add_argument('--split',choices=('selection','final'),default='final');a=p.parse_args()
 hard=resource.getrlimit(resource.RLIMIT_AS)[1];cap=min(4<<30,hard) if hard!=resource.RLIM_INFINITY else 4<<30;resource.setrlimit(resource.RLIMIT_AS,(cap,cap));os.sched_setaffinity(0,sorted(os.sched_getaffinity(0))[-2:])
 frozen=json.loads(a.freeze.read_text());expected_count=1913 if a.split=='final' else 15
 if frozen.get('guidance_profile')!=profile():raise ValueError('Guidance runner, statistics, native contracts, or qualification differs from freeze')
 if frozen.get('final_sources_sha256')!=sha(a.sources):raise ValueError('Source population differs from freeze')
 qualification=json.loads((HERE/'qualification.json').read_text())
 # Bind deterministic derived artifacts before reading any results. No settings
 # are selected from those artifacts or changed by the join.
 inputs={'sources_sha256':sha(a.sources),'c_results_sha256':sha(a.c_results),'predictions_sha256':{str(path.name):sha(path) for path in a.predictions},'frozen_profile_sha256':sha(a.freeze)}
 a.output.mkdir(parents=True,exist_ok=False);(a.output/'derived_inputs.json').write_text(json.dumps(inputs,indent=2)+'\n')
 started=time.monotonic();sources=load_rows(a.sources);compiled=load_rows(a.c_results)
 if len(sources)!=expected_count or set(sources)!=set(compiled):raise ValueError('C/source population incomplete or changed')
 seed_reports={};all_rows=[]
 for path in a.predictions:
  receipt_path=Path(str(path)+'.receipt.json');pred_receipt=json.loads(receipt_path.read_text())
  if pred_receipt.get('predictions_sha256')!=sha(path) or pred_receipt.get('count')!=expected_count or pred_receipt.get('sources_sha256')!=sha(a.sources) or pred_receipt.get('split')!=a.split:raise ValueError('Prediction execution receipt/source identity mismatch')
  producer=pred_receipt.get('consumer_sha256')
  accepted={frozen.get('source_only_eval_sha256'),frozen.get('derive_t3_sha256')}-{None}
  if producer not in accepted:raise ValueError('Unfrozen prediction producer')
  predictions=load_rows(path)
  if set(predictions)!=set(sources):raise ValueError('T3/source population incomplete or changed')
  seeds={r.get('seed') for r in predictions.values()}
  if len(seeds)!=1 or seeds.pop() not in STATS_CONFIG['seeds']:raise ValueError('Unexpected prediction seed')
  seed=next(iter(predictions.values()))['seed']
  if seed in seed_reports:raise ValueError('Duplicate seed')
  rows=[]
  with (a.output/f'paired_seed{seed}.jsonl').open('x') as out:
   for rid,source in sources.items():
    original=source['text'];prefix=original[:4096];c=compiled[rid];prediction=predictions[rid]
    if prediction.get('arm_id')!='T3' or prediction.get('text_sha256')!=hashlib.sha256(original.encode()).hexdigest():raise ValueError('T3 full source identity mismatch')
    if c.get('text_sha256')!=hashlib.sha256(prefix.encode()).hexdigest() or c.get('full_text_sha256')!=prediction['text_sha256']:raise ValueError('C full/prefix source identity mismatch')
    packet={'record_id':rid,'text_sha256':c['text_sha256'],'source_text':prefix,'canonical_ir':c.get('canonical_ir'),'checker_contract':checker_contract()}
    common={'qualification':qualification,'qualification_required':True,'expected_prediction_sha256':digest(prediction)}
    off=execute_checks(prediction,packet,CHECKS,enabled=False,**common)
    on=execute_checks(prediction,packet,CHECKS,enabled=True,**common)
    rollback=execute_checks(prediction,packet,CHECKS,enabled=False,**common)
    same=outcomes(off)==outcomes(on)==outcomes(rollback)
    restored=rollback['check_order']==off['check_order'] and outcomes(rollback)==outcomes(off)
    row={'record_id':rid,'seed':seed,'family':source.get('family'),'C_compile_status':c.get('compile_status'),'formula_count':c.get('formula_count',0),'off':off,'on':on,'rollback':rollback,'outcomes_unchanged':same,'rollback_passed':restored,'eligible':c.get('compile_status')=='measured' and c.get('formula_count',0)>0 and on['all_passed']}
    if not same or not restored:raise ValueError('Scheduler changed check semantics or failed rollback')
    if c.get('compile_status')=='measured' and c.get('checks')!=outcomes(off):raise ValueError('Native C stored checks do not match unchanged replay')
    out.write(json.dumps(row,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)+'\n');out.flush();rows.append(row)
  seed_reports[str(seed)]=summarize(rows);all_rows.extend(rows)
 if a.split=='final' and set(seed_reports)!=set(map(str,STATS_CONFIG['seeds'])):raise ValueError('Missing final seed')
 summary={'schema':'autoformalization-complete-guidance-comparison/v1','split':a.split,'profile':profile(),'input_bindings':inputs,'seed_reports':seed_reports,'pooled_descriptive':summarize(all_rows),'wall_seconds':time.monotonic()-started,'cpu_seconds':time.process_time(),'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,'model_decodes_performed':0,'new_native_model_head_calls':0,'model_heads_consumed':'actual previously emitted native T3 outputs; no duplicate inference claim','semantic_fidelity_measured':False,'kernel_proof_success_measured':False,'historical_canonical_mutation_adapter_implemented':False}
 (a.output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps({'output':str(a.output),'seeds':list(seed_reports),'counts':summary['pooled_descriptive']['counts']}))
if __name__=='__main__':main()
