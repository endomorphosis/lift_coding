#!/usr/bin/env python3
"""Reuse exactly tied T2 decoder output; execute actual isolated native T3 heads.

No additional decoder run or independent scientific replication is claimed.
The original training checkpoint protected fingerprints, extracted parameter
fields and native decoding function establish equivalence before final access.
"""
import argparse,json,time,resource
from pathlib import Path
from source_only_eval import load_model,native,sha,HERE

def main():
 p=argparse.ArgumentParser();p.add_argument('--t2-predictions',required=True,type=Path);p.add_argument('--t2-compact',required=True,type=Path);p.add_argument('--t3-compact',required=True,type=Path);p.add_argument('--freeze',required=True,type=Path);p.add_argument('--output',required=True,type=Path);p.add_argument('--split',choices=('selection','final'),default='final');a=p.parse_args();expected_count=1913 if a.split=='final' else 15
 start=time.monotonic();frozen=json.load(open(a.freeze))
 if frozen['derive_t3_sha256']!=sha(__file__) or frozen['source_only_eval_sha256']!=sha(HERE/'source_only_eval.py') or frozen['native_implementation_sha256']!=sha(native.__file__):raise ValueError('Frozen code changed')
 x=json.load(open(a.t2_compact));y=json.load(open(a.t3_compact));seed=x['source_metadata']['seed']
 if x['source_metadata']['arm_id']!='T2' or y['source_metadata']['arm_id']!='T3' or y['source_metadata']['seed']!=seed:raise ValueError('Wrong paired arms/seeds')
 if x['source_metadata']['protected_fingerprint']!=y['source_metadata']['protected_fingerprint']:raise ValueError('Protected checkpoint identities differ')
 excluded={'applied_proof_feedback_ids','proof_auxiliary_head_logits','proof_auxiliary_head_schema_version','proof_feedback_version_fingerprint'}
 if {k:v for k,v in x['state'].items() if k not in excluded}!={k:v for k,v in y['state'].items() if k not in excluded}:raise ValueError('Protected compact values differ')
 matched=[b for b in frozen['model_bindings'] if b['arm_id'] in ('T2','T3') and b['seed']==seed]
 if len(matched)!=2 or len({b['vectors_manifest_sha256'] for b in matched})!=1:raise ValueError('Tied vectors not frozen')
 for compact,record in [(a.t2_compact,x),(a.t3_compact,y)]:
  if not any(b['compact_sha256']==sha(compact) and b['checkpoint_sha256']==record['source_sha256'] for b in matched):raise ValueError('Checkpoint custody changed')
 t2receipt=json.load(open(Path(str(a.t2_predictions)+'.receipt.json')))
 if t2receipt['predictions_sha256']!=sha(a.t2_predictions) or t2receipt['sources_sha256']!=frozen['final_sources_sha256'] or t2receipt['count']!=expected_count or t2receipt['consumer_sha256']!=frozen['source_only_eval_sha256']:raise ValueError('T2 output custody mismatch')
 model,provenance=load_model(a.t3_compact)
 heads={family:model.predict_proof_auxiliary_heads(family) for family in native.LEGAL_IR_VIEW_FAMILIES}
 provenance['vectors_manifest_sha256']=matched[0]['vectors_manifest_sha256'];seen=set();count=0
 with a.output.open('x') as out,a.t2_predictions.open() as source:
  for line in source:
   row=json.loads(line)
   if row['arm_id']!='T2' or row['seed']!=seed or row['checkpoint_sha256']!=x['source_sha256'] or row['record_id'] in seen:raise ValueError('Invalid T2 prediction row')
   seen.add(row['record_id']);row.update(provenance);row['proof_heads_by_family']=heads;row['decoder_execution']='reused_exact_protected_T2_decoder';row['new_decoder_calls']=0;row['source_decoder_wall_seconds']=row.pop('wall_seconds');row['wall_seconds']=None;row['wall_seconds_status']='batch proof-head lookup cost reported separately; no per-record decoder execution';row['proof_head_execution']='native_fixed_family_lookup_once_per_checkpoint';row['t2_predictions_sha256']=t2receipt['predictions_sha256']
   out.write(json.dumps(row,sort_keys=True,separators=(',',':'))+'\n');count+=1
 if count!=expected_count:raise ValueError('Final population incomplete')
 receipt={'schema':'autoformalization-tied-T3-decoder-evaluation/v1','count':count,'split':a.split,'seed':seed,'consumer_sha256':sha(__file__),'source_only_eval_sha256':sha(HERE/'source_only_eval.py'),'sources_sha256':frozen['final_sources_sha256'],'predictions_sha256':sha(a.output),'t2_predictions_sha256':t2receipt['predictions_sha256'],'protected_fingerprint':x['source_metadata']['protected_fingerprint'],'new_decoder_calls':0,'actual_native_proof_head_calls':len(heads),'decoder_values_reused':count,'independent_replication_claimed':False,'wall_seconds':time.monotonic()-start,'cpu_seconds':time.process_time(),'max_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,'provenance':provenance}
 Path(str(a.output)+'.receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
if __name__=='__main__':main()
