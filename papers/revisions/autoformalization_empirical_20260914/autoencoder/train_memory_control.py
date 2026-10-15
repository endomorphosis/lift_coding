#!/usr/bin/env python3
"""Retained T1 training-memory diagnostic; no new training and no final inputs."""
import json,sys,time,resource
from pathlib import Path
from source_only_eval import HERE,load_model,source_sample,sha
from score_embeddings import score
BASE=HERE.parents[3]/'papers/completion/runtime_bootstrap/unblock_20260912/af029_recovery/memory_lifetime_recovery/resource_amendment_v1/execution_source/papers/completion/autoformalization'
SOURCES=BASE/'receipts/snapshots/AF-004/train.sources.jsonl'

def main():
 source_rows=[json.loads(l) for l in SOURCES.open()]
 assert len(source_rows)==69
 reports=[]
 for seed in (104729,130363,155921):
  start=time.monotonic();model,provenance=load_model(HERE/f'compact/T1-{seed}.json');p=HERE/f'train/T1-{seed}.memory_predictions.jsonl';hits=0
  with p.open('x') as out:
   for row in source_rows:
    # Source text/metadata determine the key. No reference embedding is read.
    sample=source_sample(row);vector=model.state.decoded_embeddings.get(sample.sample_id)
    if vector is None:raise ValueError('Retained training memory missing')
    hits+=1;out.write(json.dumps({'record_id':row['record_id'],'family':row['family'],'text_sha256':__import__('hashlib').sha256(row['text'].encode()).hexdigest(),'decoded_source_embedding':list(vector),'wall_seconds':None,'sample_memory_hit':True,'memory_lookup_only':True,**provenance},sort_keys=True,separators=(',',':'))+'\n')
  prediction_sha=sha(p)
  # Scorer opens the source-embedding targets only after emitted predictions.
  rows,summary=score(p,HERE/'train/source_embeddings.jsonl')
  reports.append({'seed':seed,'training_rows':69,'native_source_key_memory_hits':hits,'source_sha256':sha(SOURCES),'predictions_sha256':prediction_sha,'summary':summary,'wall_seconds':time.monotonic()-start})
 (HERE/'train/memory_control_summary.json').write_text(json.dumps({'schema':'autoformalization-retained-T1-training-memory-control/v1','new_training_updates':0,'final_inputs_read':False,'reports':reports},indent=2)+'\n');print(json.dumps(reports))
if __name__=='__main__':main()
