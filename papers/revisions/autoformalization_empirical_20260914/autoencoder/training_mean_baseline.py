#!/usr/bin/env python3
"""Prespecified supplemental constant training-mean source-vector diagnostic."""
import argparse,hashlib,json,math,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
SOURCE_SHA='c335ed0289debc45462e1f9399e1e9c1c4e40b62f2128473304c5959682adca0'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def objsha(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--construct',action='store_true');p.add_argument('--sources',type=Path);p.add_argument('--output',required=True,type=Path);p.add_argument('--freeze',type=Path);a=p.parse_args()
 if a.construct:
  src=HERE/'train/source_embeddings.jsonl';rows=list(map(json.loads,open(src)))
  if len(rows)!=69 or len({r['record_id'] for r in rows})!=69:raise ValueError('Training population changed')
  rows.sort(key=lambda r:r['record_id']);vectors=[r['embedding_vector'] for r in rows]
  if any(len(v)!=384 or any(not math.isfinite(x) for x in v) for v in vectors):raise ValueError('Training vectors invalid')
  if any(r['embedding_vector_sha256']!=objsha(r['embedding_vector']) for r in rows):raise ValueError('Training vector custody mismatch')
  mean=[sum(v[j] for v in vectors)/69 for j in range(384)];norm=math.sqrt(sum(x*x for x in mean));vector=[x/norm for x in mean]
  result={'schema':'autoformalization-frozen-training-mean-baseline/v1','constructor_sha256':sha(__file__),'training_embeddings_sha256':sha(src),'training_records':69,'training_record_ids_sha256':objsha([r['record_id'] for r in rows]),'construction':'record_id sorted float64 Python arithmetic mean of all69 retained training source embeddings; one L2 normalization; no weighting/selection/tuning','vector':vector,'vector_sha256':objsha(vector),'dimensions':384,'final_sources_sha256':SOURCE_SHA,'final_inputs_read':False,'designation':'supplemental constant domain-mean baseline; no new T-arm','timing':'Added by parent before any final AE predictions or AE outcome scoring; frozen separately as an amendment'}
  with a.output.open('x') as out:json.dump(result,out,sort_keys=True,indent=2);out.write('\n')
  print(json.dumps({'baseline_sha256':sha(a.output),'vector_sha256':result['vector_sha256']}));return
 if not a.freeze or not a.sources:raise ValueError('Prediction requires frozen baseline and final sources')
 frozen=json.load(open(a.freeze))
 if frozen['constructor_sha256']!=sha(__file__) or frozen['final_sources_sha256']!=sha(a.sources) or frozen['vector_sha256']!=objsha(frozen['vector']):raise ValueError('Frozen baseline/source identity changed')
 rows=list(map(json.loads,open(a.sources)))
 if len(rows)!=1913:raise ValueError('Final population changed')
 start=time.monotonic()
 with a.output.open('x') as out:
  for row in rows:out.write(json.dumps({'record_id':row['record_id'],'family':row['family'],'text_sha256':hashlib.sha256(row['text'].encode()).hexdigest(),'decoded_source_embedding':frozen['vector'],'arm_id':'training_mean_supplement','fixed_training_mean_sha256':sha(a.freeze),'reference_targets_used':False,'sample_memory_used':False},sort_keys=True,separators=(',',':'))+'\n')
 receipt={'count':len(rows),'split':'final','predictions_sha256':sha(a.output),'consumer_sha256':sha(__file__),'sources_sha256':sha(a.sources),'frozen_baseline_sha256':sha(a.freeze),'new_decoder_calls':0,'constant_vector_predictions':len(rows),'wall_seconds':time.monotonic()-start,'source_embedding_targets_read':False};Path(str(a.output)+'.receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
if __name__=='__main__':main()
