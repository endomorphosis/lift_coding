#!/usr/bin/env python3
"""Execution-only per-source activation memoization; frozen predict_row unchanged.

All shared activations are produced by the native source feature methods while
ANY access to learned state raises. Learned predictions are separately evaluated
for every T0/T2 arm using the unchanged frozen function and original parameters.
"""
from __future__ import annotations
import argparse,copy,hashlib,json,os,resource,time
from pathlib import Path
from source_only_eval import HERE,CONFIG,SourceOnlyModel,load_model,source_sample,predict_row,native,sha,objsha
SEEDS=(104729,130363,155921)
PRODUCERS=('_legal_ir_view_feature_keys_for','_base_decoded_for','_base_logits_for','_logic_signature_distribution_for','_round_trip_signal_distribution_for','_decompiler_plan_distribution_for','_predicate_argument_distribution_for','_semantic_slot_distribution_for')
class DeniedState:
 def __getattribute__(self,name):raise RuntimeError('Source activation producer attempted learned-state access: '+name)
def normalize(x):
 if isinstance(x,dict):return {repr(k):normalize(v) for k,v in sorted(x.items(),key=lambda z:repr(z[0]))}
 if isinstance(x,(set,frozenset)):return sorted(normalize(v) for v in x)
 if isinstance(x,(list,tuple)):return [normalize(v) for v in x]
 return x

def source_activations(extractor,row,embedding):
 assert isinstance(extractor.state,DeniedState) and extractor.feature_codec is None
 assert not extractor._legal_ir_view_target_cache and not extractor._legal_ir_loss_target_cache
 extractor._sample_feature_cache.clear();sample=source_sample(row,embedding);start=time.monotonic()
 for method in PRODUCERS:getattr(extractor,method)(sample)
 cache=extractor._sample_feature_cache
 return copy.deepcopy(cache),{'source_activation_sha256':objsha(normalize(cache)),'source_activation_wall_seconds':time.monotonic()-start,'raw_source_sha256':hashlib.sha256(row['text'].encode()).hexdigest(),'parser_text_sha256':hashlib.sha256(sample.text.encode()).hexdigest(),'input_embedding_sha256':objsha(embedding),'native_feature_implementation_sha256':sha(native.__file__),'learned_state_reads_allowed':False,'reference_targets_read':False,'cache_entries':sum(len(v) for v in cache.values()),'producer_methods':PRODUCERS}

def prepare_models(frozen):
 models=[]
 for arm,seed in [('T0',None)]+[('T2',seed) for seed in SEEDS]:
  compact=HERE/'compact'/f'{arm}-{seed}.json' if seed else None
  vectors=HERE/'vectors'/f'{arm}-{seed}' if seed else None
  m,prov=load_model(compact,vectors)
  if seed and prov not in frozen['model_bindings']:raise ValueError('Model identity absent from freeze')
  assert m.feature_codec is None and not m._legal_ir_view_target_cache and not m._legal_ir_loss_target_cache
  models.append((arm if seed is None else f'{arm}-{seed}',m,prov))
 # Only the learned state differs. Verify every native initialization attribute
 # used by feature extraction; all non-state instance settings must match.
 reference=models[0][1]
 for _,m,_ in models[1:]:
  left={k:v for k,v in reference.__dict__.items() if k not in {'state','_sample_feature_cache'}}
  right={k:v for k,v in m.__dict__.items() if k not in {'state','_sample_feature_cache'}}
  if left!=right:raise ValueError('Source-feature model settings differ: '+repr([k for k in set(left)|set(right) if left.get(k)!=right.get(k)]))
 extractor=SourceOnlyModel(compute_device='cpu');extractor.state=DeniedState()
 return models,extractor

def main():
 p=argparse.ArgumentParser();p.add_argument('--sources',type=Path,required=True);p.add_argument('--embeddings',type=Path,required=True);p.add_argument('--freeze',type=Path,required=True);p.add_argument('--output-dir',type=Path,required=True);p.add_argument('--split',choices=('selection','final'),required=True);p.add_argument('--amendment',type=Path);a=p.parse_args()
 resource.setrlimit(resource.RLIMIT_AS,(8<<30,8<<30));os.sched_setaffinity(0,sorted(os.sched_getaffinity(0))[-2:]);start=time.monotonic();startcpu=time.process_time()
 frozen=json.load(open(a.freeze))
 if frozen['source_only_eval_sha256']!=sha(HERE/'source_only_eval.py') or frozen['native_implementation_sha256']!=sha(native.__file__) or frozen['configuration_sha256']!=objsha(CONFIG):raise ValueError('Frozen function/config/native identity mismatch')
 if a.split=='final':
  amendment=json.load(open(a.amendment)) if a.amendment else {}
  if amendment.get('runner_sha256')!=sha(__file__) or amendment.get('qualification_sha256')!=sha(HERE/'selection/cache_execution/qualification.json') or amendment.get('source_only_eval_sha256')!=frozen['source_only_eval_sha256']:raise ValueError('Execution amendment not qualified')
  if frozen['final_sources_sha256']!=sha(a.sources) or frozen['source_embeddings_sha256']!=sha(a.embeddings):raise ValueError('Final source/embedding binding mismatch')
 rows=list(map(json.loads,open(a.sources)));ers={r['record_id']:r for r in map(json.loads,open(a.embeddings))};expected=1913 if a.split=='final' else 15
 if len(rows)!=expected or len({r['record_id'] for r in rows})!=expected or set(ers)!={r['record_id'] for r in rows}:raise ValueError('Population mismatch')
 models,extractor=prepare_models(frozen);a.output_dir.mkdir(exist_ok=True,parents=True);handles={name:(a.output_dir/f'{name}.predictions.jsonl').open('x') for name,_,_ in models};activation_handle=(a.output_dir/'source_activation_receipts.jsonl').open('x');qualification=[];per_arm_wall={name:0. for name,_,_ in models}
 for index,row in enumerate(rows):
  er=ers[row['record_id']];embedding=er['embedding_vector']
  if er['text_sha256']!=hashlib.sha256(row['text'].encode()).hexdigest() or er['embedding_vector_sha256']!=objsha(embedding):raise ValueError('Embedding per-row binding mismatch')
  cache,receipt=source_activations(extractor,row,embedding);receipt['record_id']=row['record_id'];activation_handle.write(json.dumps(receipt,sort_keys=True)+'\n');activation_handle.flush()
  for name,model,prov in models:
   if a.split=='selection':
    model._sample_feature_cache.clear();baseline=predict_row(model,row,prov,embedding)
   model._sample_feature_cache=copy.deepcopy(cache);prediction=predict_row(model,row,prov,embedding)
   if a.split=='selection':
    expected_prediction={k:v for k,v in baseline.items() if k!='wall_seconds'};actual_prediction={k:v for k,v in prediction.items() if k!='wall_seconds'}
    if expected_prediction!=actual_prediction:raise ValueError('Cached execution differs: '+name+' '+row['record_id'])
    qualification.append({'record_id':row['record_id'],'arm':name,'prediction_sha256':objsha(actual_prediction),'all_nontiming_fields_bitexact':True,'uncached_seconds':baseline['wall_seconds'],'cached_seconds':prediction['wall_seconds']})
   per_arm_wall[name]+=prediction['wall_seconds'];prediction['execution_cache']={'source_activation_sha256':receipt['source_activation_sha256'],'source_activation_cache_hit':True,'execution_runner_sha256':sha(__file__),'learned_state_reads_during_activation_preparation':False,'shared_source_preparation_cost_reported_separately':True}
   handles[name].write(json.dumps(prediction,sort_keys=True,separators=(',',':'))+'\n');handles[name].flush()
  extractor._sample_feature_cache.clear()
  print(json.dumps({'rows':index+1,'arms':4,'wall_seconds':time.monotonic()-start}),flush=True)
 for handle in handles.values():handle.close()
 activation_handle.close();totalwall=time.monotonic()-start;totalcpu=time.process_time()-startcpu;peak=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
 for name,_,prov in models:
  path=a.output_dir/f'{name}.predictions.jsonl';receipt={'schema':'autoformalization-source-only-inference-receipt/v1','configuration':CONFIG,'configuration_sha256':objsha(CONFIG),'consumer_sha256':sha(HERE/'source_only_eval.py'),'native_implementation_sha256':sha(native.__file__),'sources_sha256':sha(a.sources),'predictions_sha256':sha(path),'count':len(rows),'split':a.split,'provenance':prov,'sample_memory_enabled':False,'wall_seconds':per_arm_wall[name],'cpu_seconds':None,'cpu_seconds_status':'Joint four-arm CPU and shared source preparation cost in execution receipt; no per-arm attribution claimed','max_rss_bytes':peak,'targets_read':False,'execution_runner_sha256':sha(__file__),'source_activation_receipts_sha256':sha(a.output_dir/'source_activation_receipts.jsonl'),'actual_decoder_calls':len(rows),'source_cache_population':len(rows),'shared_timing_accounting':True}
  Path(str(path)+'.receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
 result={'schema':'autoformalization-source-activation-cache-execution/v1','split':a.split,'count':len(rows),'arms':4,'actual_decoder_calls':4*len(rows),'runner_sha256':sha(__file__),'source_only_eval_sha256':sha(HERE/'source_only_eval.py'),'native_implementation_sha256':sha(native.__file__),'source_activation_producer_methods':PRODUCERS,'learned_state_access_denied_during_all_shared_activation_preparation':True,'source_feature_configuration_equal_all_models':True,'per_unit_cache_discarded':True,'sources_sha256':sha(a.sources),'embeddings_sha256':sha(a.embeddings),'wall_seconds':totalwall,'cpu_seconds':totalcpu,'max_rss_bytes':peak,'per_arm_decoder_seconds':per_arm_wall,'all_selection_predictions_bitexact':a.split=='selection','comparisons':qualification}
 target=a.output_dir/('qualification.json' if a.split=='selection' else 'execution_receipt.json');target.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='comparisons'}),flush=True)
if __name__=='__main__':main()
