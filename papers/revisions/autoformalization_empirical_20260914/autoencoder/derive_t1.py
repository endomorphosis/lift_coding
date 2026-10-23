#!/usr/bin/env python3
"""Execute retained T1 sample-memory lookup; verify exact cold fallback on misses."""
import argparse,json,time,resource,os
from pathlib import Path
from source_only_eval import load_model,source_sample,sha,HERE,native

def main():
 p=argparse.ArgumentParser();p.add_argument('--t0-predictions',required=True,type=Path);p.add_argument('--sources',required=True,type=Path);p.add_argument('--embeddings',required=True,type=Path);p.add_argument('--compact',required=True,type=Path);p.add_argument('--freeze',required=True,type=Path);p.add_argument('--output',required=True,type=Path);p.add_argument('--split',choices=('selection','final'),default='final');a=p.parse_args();expected_count=1913 if a.split=='final' else 15
 start=time.monotonic();resource.setrlimit(resource.RLIMIT_AS,(4<<30,4<<30));os.sched_setaffinity(0,sorted(os.sched_getaffinity(0))[-2:])
 frozen=json.load(open(a.freeze))
 if frozen['derive_t1_sha256']!=sha(__file__) or frozen['source_only_eval_sha256']!=sha(HERE/'source_only_eval.py') or frozen['native_implementation_sha256']!=sha(native.__file__):raise ValueError('Frozen code changed')
 x=json.load(open(a.compact));seed=x['source_metadata']['seed']
 if x['source_metadata']['arm_id']!='T1':raise ValueError('T1 required')
 if not any(b['arm_id']=='T1' and b['seed']==seed and b['compact_sha256']==sha(a.compact) and b['checkpoint_sha256']==x['source_sha256'] for b in frozen['model_bindings']):raise ValueError('Unbound T1 state')
 if sha(a.sources)!=frozen['final_sources_sha256'] or sha(a.embeddings)!=frozen['source_embeddings_sha256']:raise ValueError('Derived inputs changed')
 receipt=json.load(open(Path(str(a.t0_predictions)+'.receipt.json')))
 if receipt['predictions_sha256']!=sha(a.t0_predictions) or receipt['sources_sha256']!=frozen['final_sources_sha256'] or receipt['count']!=expected_count or receipt['consumer_sha256']!=frozen['source_only_eval_sha256'] or receipt['provenance']['arm_id']!='T0':raise ValueError('T0 cold baseline custody mismatch')
 model,provenance=load_model(a.compact)
 if len(x['disabled_embedding_scales'])!=13 or any(getattr(model,k)!=0.0 for k in x['disabled_embedding_scales']):raise ValueError('Retained T1 shared decoder scale is enabled')
 if model.feature_codec is not None or model.legacy_embedding_adapters is not None:raise ValueError('Unexpected decoder adapter')
 embedding={r['record_id']:r for r in map(json.loads,open(a.embeddings))};sources={r['record_id']:r for r in map(json.loads,open(a.sources))};seen=set();hits=0;count=0
 with a.output.open('x') as out,a.t0_predictions.open() as inp:
  for line in inp:
   begin=time.monotonic();row=json.loads(line);rid=row['record_id']
   if rid in seen or row['arm_id']!='T0':raise ValueError('Invalid T0 row')
   seen.add(rid);source=sources[rid];er=embedding[rid]
   if er['text_sha256']!=row['text_sha256']:raise ValueError('Source input identity mismatch')
   sample=source_sample(source,er['embedding_vector']);stored=model.state.decoded_embeddings.get(sample.sample_id)
   hit=stored is not None and len(stored)==len(sample.embedding_vector)
   if hit:decoded=list(stored);hits+=1
   else:
    decoded=model._base_decoded_for(sample)
    if decoded!=row['decoded_source_embedding']:raise ValueError('Native cold projection differs from T0')
   row.update(provenance);row['decoded_source_embedding']=decoded;row['sample_memory_used']=True;row['sample_memory_hit']=hit;row['decoder_execution']='native_retained_sample_memory_lookup' if hit else 'native_cold_projection_verified_equal_T0';row['new_shared_decoder_calls']=0;row['new_native_memory_lookup_calls']=1;row['source_t0_predictions_sha256']=receipt['predictions_sha256'];row['wall_seconds']=time.monotonic()-begin
   # This focused control evaluates the actual memorized vector head. It does
   # not recycle T0 labels as a claimed fresh T1 classifier measurement.
   row['modal_distribution']=None;row['view_distribution']=None;row['proof_heads_by_family']=None;row['active_learned_features']=[];row['classifier_measurement']='not_measured_in_memory_lookup_control'
   out.write(json.dumps(row,sort_keys=True,separators=(',',':'))+'\n');count+=1;model._sample_feature_cache.clear()
 if count!=expected_count or seen!=set(sources) or seen!=set(embedding):raise ValueError('Final population incomplete')
 result={'schema':'autoformalization-native-T1-memory-control/v1','count':count,'seed':seed,'split':a.split,'predictions_sha256':sha(a.output),'t0_predictions_sha256':receipt['predictions_sha256'],'consumer_sha256':sha(__file__),'sources_sha256':frozen['final_sources_sha256'],'sample_memory_entries':len(model.state.decoded_embeddings),'sample_memory_hits':hits,'native_lookup_calls':count,'native_cold_fallbacks_verified':count-hits,'new_shared_decoder_calls':0,'wall_seconds':time.monotonic()-start,'cpu_seconds':time.process_time(),'max_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,'provenance':provenance}
 Path(str(a.output)+'.receipt.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
