#!/usr/bin/env python3
"""Release compact numeric outputs with explicit prediction and model custody."""
from pathlib import Path
import argparse,hashlib,json,shutil
HERE=Path(__file__).resolve().parent
SEEDS=(104729,130363,155921)
NAMES=['T0']+[f'{arm}-{seed}' for arm in ('T1','T2','T3') for seed in SEEDS]+['training_mean']
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def copy(source,target):target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
def redact_documentary_paths(out):
 index_path=out/'provenance/documentary_redactions.json'
 records_by_path={r['path']:r for r in json.load(open(index_path))['records']} if index_path.exists() else {}
 for path in sorted((out/'provenance').rglob('*')):
  if not path.is_file():continue
  text=path.read_text();published=text.replace('/home/barberb','<USER_HOME>')
  if text!=published:
   original_sha=sha(path);path.write_text(published);records_by_path[str(path.relative_to(out))]={'path':str(path.relative_to(out)),'original_documentary_sha256':original_sha,'published_sha256':sha(path),'change':'Replace personal home path prefix with anonymous USER_HOME placeholder; documentary copy only, not executed code or model values.'}
 (out/'provenance/documentary_redactions.json').write_text(json.dumps({'schema':'autoformalization-anonymous-documentary-copies/v1','records':[records_by_path[k] for k in sorted(records_by_path)],'original_executed_code_and_model_hashes_remain_in_frozen_profile':True,'numeric_scorer_profile_inputs_and_predictions_unmodified':True},indent=2)+'\n')

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);p.add_argument('--provenance-only',action='store_true');a=p.parse_args();out=a.output;out.mkdir(parents=True,exist_ok=True)
 for name in ('scientific_profile.json','cache_execution_amendment.json','mean_metadata_amendment.json','training_mean_baseline.freeze.json','METHODS_AND_SCOPE.md','score_embeddings.py','summarize_final.py','training_mean_baseline.py','complete_mean_prediction_metadata.py','source_only_eval.py','encode_sources.py','cached_execution_parallel.py','collect_cached_workers.py','derive_t1.py','derive_t3.py','cached_execution_parallel_engineering_review.json','mean_metadata_adapter_engineering_review.json'):
  copy(HERE/name,out/'provenance'/name)
 for seed in SEEDS:
  copy(HERE/f'vectors/T2-{seed}/manifest.json',out/f'provenance/vector_manifests/T2-{seed}.json')
  for arm in ('T1','T2','T3'):
   path=HERE/f'compact/{arm}-{seed}.json';x=json.load(open(path));excerpt={k:v for k,v in x.items() if k!='state'}
   excerpt.update({'schema':'autoformalization-model-provenance-excerpt/v1','full_compact_sha256':sha(path),'state_field_cardinalities':{k:len(v) if hasattr(v,'__len__') else None for k,v in x['state'].items()},'proof_auxiliary_head_logits':x['state'].get('proof_auxiliary_head_logits',{}),'scope':'Metadata, parameter-table cardinalities, and isolated proof-head values only; not a loadable full decoder. Learned vector arrays and large membership tables are omitted.'});target=out/f'provenance/checkpoints/{arm}-{seed}.json';target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(excerpt,sort_keys=True,indent=2)+'\n');del x
   receipt=Path(str(path)+'.receipt.json')
   if receipt.exists():copy(receipt,out/f'provenance/checkpoints/{arm}-{seed}.extraction_receipt.json')
 copy(HERE/'selection/cache_execution_parallel/qualification.json',out/'provenance/source_cache_qualification.json')
 copy(HERE/'train/source_embeddings.jsonl',out/'training.source_embeddings.jsonl');copy(HERE/'train/memory_control_summary.json',out/'provenance/training_memory_control.json')
 copy(HERE/'final/source_embeddings.jsonl',out/'source_embeddings.jsonl');copy(HERE/'final/source_embeddings.jsonl.receipt.json',out/'provenance/source_embeddings.receipt.json')
 sourcepath=HERE.parent/'pipeline/final.sources.jsonl';sources=list(map(json.loads,open(sourcepath)))
 with (out/'source_metadata.jsonl').open('w') as f:
  for r in sources:f.write(json.dumps({'record_id':r['record_id'],'family':r['family'],'component_id':r['component_id'],'text_sha256':hashlib.sha256(r['text'].encode()).hexdigest()},sort_keys=True,separators=(',',':'))+'\n')
 if a.provenance_only:
  redact_documentary_paths(out);return
 manifest={'schema':'autoformalization-compact-evaluation-release/v1','original_final_sources_sha256':sha(sourcepath),'source_metadata_sha256':sha(out/'source_metadata.jsonl'),'source_embeddings_sha256':sha(out/'source_embeddings.jsonl'),'training_embeddings_sha256':sha(out/'training.source_embeddings.jsonl'),'cohort_records':1913,'arms':{},'scope':'Reproduction of numeric metrics/statistics from released model outputs; original full learned parameters are not bundled, so this alone does not reproduce model inference.'}
 for name in NAMES:
  src=HERE/f'final/{name}.predictions.jsonl';receipt=json.load(open(Path(str(src)+'.receipt.json')))
  if receipt['count']!=1913 or receipt['predictions_sha256']!=sha(src):raise ValueError('Final prediction custody incomplete')
  target=out/f'predictions/{name}.jsonl';target.parent.mkdir(exist_ok=True);count=0;overrides=0;expanded_hash=hashlib.sha256()
  base_name='T0' if name.startswith('T1-') else name.replace('T3-','T2-') if name.startswith('T3-') else None
  base_rows={r['record_id']:r for r in map(json.loads,open(out/f'predictions/{base_name}.jsonl'))} if base_name else None
  with src.open() as source,target.open('x') as f:
   for line in source:
    r=json.loads(line);keep={k:r[k] for k in ('record_id','text_sha256','family','arm_id','seed','wall_seconds','decoded_source_embedding')};expanded=(json.dumps(keep,sort_keys=True,separators=(',',':'))+'\n').encode();expanded_hash.update(expanded)
    if base_name:
     base=base_rows[r['record_id']]
     if keep['text_sha256']!=base['text_sha256']:raise ValueError('Alias source binding differs')
     stored={k:v for k,v in keep.items() if k!='decoded_source_embedding'}
     if name.startswith('T1-'):
      stored['native_memory_hit']=r['sample_memory_hit']
      if r['sample_memory_hit']:stored['vector_override']=keep['decoded_source_embedding'];overrides+=1
     if 'vector_override' not in stored and json.dumps(keep['decoded_source_embedding'],separators=(',',':'))!=json.dumps(base['decoded_source_embedding'],separators=(',',':')):raise ValueError('Alias vector is not exactly equal to its base')
    else:stored=keep
    f.write(json.dumps(stored,sort_keys=True,separators=(',',':'))+'\n');count+=1
  if count!=1913 or (name.startswith('T1-') and overrides!=receipt['sample_memory_hits']):raise ValueError('Projection population or native-hit count mismatch')
  copy(HERE/f'final/{name}.scores.json',out/f'scores/{name}.json');copy(Path(str(src)+'.receipt.json'),out/f'provenance/prediction_receipts/{name}.json')
  manifest['arms'][name]={'count':count,'stored_prediction_sha256':sha(target),'compact_projection_sha256':expanded_hash.hexdigest(),'representation':'exact_alias_with_metadata' if base_name else 'full_numeric_projection','base_prediction_name':base_name,'native_hit_vector_overrides':overrides,'original_prediction_sha256':receipt['predictions_sha256'],'scores_sha256':sha(out/f'scores/{name}.json'),'original_receipt_sha256':sha(Path(str(src)+'.receipt.json')),'retained_fields':list(keep),'projection_values_copied_without_arithmetic':True,'all_alias_vectors_checked_against_original_outputs':bool(base_name)}
 for name in ('summary.json','RESULTS.md','execution_receipt.json','input_binding.json','orchestration_handoff.json','affinity_amendment_worker0.json','affinity_amendment_worker0.applied.json','affinity_amendment_worker0_fast.json','affinity_amendment_worker0_fast.json.applied.json'):
  copy(HERE/'final'/name,out/name)
 for worker in range(2):
  copy(HERE/f'final/worker{worker}/execution_receipt.json',out/f'provenance/worker{worker}.execution_receipt.json')
 copy(HERE/'final/source_activation_receipts.jsonl',out/'provenance/source_activation_receipts.jsonl')
 for name in ('supplement_engineering_review_guidance.json','supplement_alias_engineering_review_guidance.json'):
  copy(HERE/name,out/'provenance'/name)
 redact_documentary_paths(out)
 manifest['reported_summary_sha256']=sha(out/'summary.json');manifest['profile_sha256']=sha(out/'provenance/scientific_profile.json');manifest['source_cache_amendment_sha256']=sha(out/'provenance/cache_execution_amendment.json')
 (out/'manifest.json').write_text(json.dumps(manifest,sort_keys=True,indent=2)+'\n');print(json.dumps({'output':str(out),'manifest_sha256':sha(out/'manifest.json'),'arms':len(NAMES)}))
if __name__=='__main__':main()
