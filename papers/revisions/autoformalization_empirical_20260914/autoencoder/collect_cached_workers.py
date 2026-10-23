#!/usr/bin/env python3
"""Collect fixed disjoint source partitions; never select outputs by scores."""
import argparse,hashlib,json,time
from pathlib import Path
NAMES=('T0','T2-104729','T2-130363','T2-155921')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--root',required=True,type=Path);p.add_argument('--sources',required=True,type=Path);p.add_argument('--split',choices=('selection','final'),required=True);p.add_argument('--freeze',required=True,type=Path);p.add_argument('--amendment',type=Path);a=p.parse_args();start=time.monotonic();here=Path(__file__).resolve().parent;frozen=json.load(open(a.freeze))
 if a.split=='final':
  amendment=json.load(open(a.amendment)) if a.amendment else {}
  if amendment.get('collector_sha256')!=sha(__file__) or amendment.get('runner_sha256')!=sha(here/'cached_execution_parallel.py'):raise ValueError('Collector/runner amendment identity mismatch')
 rows=list(map(json.loads,open(a.sources)));expected=1913 if a.split=='final' else 15
 if len(rows)!=expected or len({r['record_id'] for r in rows})!=expected:raise ValueError('Full population mismatch')
 ids=[r['record_id'] for r in rows];sourcehash=sha(a.sources);workers=[]
 if a.split=='final' and sourcehash!=frozen['final_sources_sha256']:raise ValueError('Final sources differ from freeze')
 for worker in range(2):
  folder=a.root/f'worker{worker}';receipt=json.load(open(folder/('qualification.json' if a.split=='selection' else 'execution_receipt.json')))
  if receipt['worker_index']!=worker or receipt['workers']!=2 or receipt['count']!=len(ids[worker::2]) or receipt['sources_sha256']!=sourcehash or receipt['runner_sha256']!=sha(here/'cached_execution_parallel.py') or receipt['source_only_eval_sha256']!=frozen['source_only_eval_sha256'] or receipt['native_implementation_sha256']!=frozen['native_implementation_sha256']:raise ValueError('Worker provenance mismatch')
  if a.split=='selection' and (not receipt['all_selection_predictions_bitexact'] or len(receipt['comparisons'])!=4*len(ids[worker::2])):raise ValueError('Worker qualification incomplete')
  if a.split=='final' and receipt['embeddings_sha256']!=frozen['source_embeddings_sha256']:raise ValueError('Worker embeddings differ from freeze')
  workers.append(receipt)
 activations={}
 for worker in range(2):
  path=a.root/f'worker{worker}'/'source_activation_receipts.jsonl'
  data=list(map(json.loads,open(path)))
  if [r['record_id'] for r in data]!=ids[worker::2]:raise ValueError('Source activation partition mismatch')
  for row in data:activations[row['record_id']]=row
 with (a.root/'source_activation_receipts.jsonl').open('x') as out:
  for rid in ids:out.write(json.dumps(activations[rid],sort_keys=True)+'\n')
 for name in NAMES:
  combined={};receipts=[]
  for worker in range(2):
   path=a.root/f'worker{worker}'/f'{name}.predictions.jsonl';r=json.load(open(Path(str(path)+'.receipt.json')));data=list(map(json.loads,open(path)))
   if r['predictions_sha256']!=sha(path) or r['count']!=len(data) or r['sources_sha256']!=sourcehash or r['consumer_sha256']!=frozen['source_only_eval_sha256'] or r['execution_runner_sha256']!=sha(here/'cached_execution_parallel.py'):raise ValueError('Worker prediction custody mismatch')
   if r['source_activation_receipts_sha256']!=sha(a.root/f'worker{worker}'/'source_activation_receipts.jsonl'):raise ValueError('Worker source activation custody mismatch')
   if [x['record_id'] for x in data]!=ids[worker::2]:raise ValueError('Worker partition membership/order mismatch')
   for item in data:
    if item['record_id'] in combined:raise ValueError('Duplicated source prediction')
    combined[item['record_id']]=item
   receipts.append(r)
  if set(combined)!=set(ids) or receipts[0]['provenance']!=receipts[1]['provenance']:raise ValueError('Arm merge mismatch')
  out=a.root/f'{name}.predictions.jsonl'
  with out.open('x') as f:
   for rid in ids:f.write(json.dumps(combined[rid],sort_keys=True,separators=(',',':'))+'\n')
  receipt=dict(receipts[0]);receipt.update({'count':len(ids),'predictions_sha256':sha(out),'wall_seconds':sum(r['wall_seconds'] for r in receipts),'max_rss_bytes':max(r['max_rss_bytes'] for r in receipts),'actual_decoder_calls':len(ids),'source_cache_population':len(ids),'worker_index':None,'cpu_affinity':None,'source_activation_receipts_sha256':sha(a.root/'source_activation_receipts.jsonl'),'worker_receipts':receipts,'collector_sha256':sha(__file__),'timing_scope':'Sum of actual per-record frozen predict_row wall times across two workers; includes logits/heads, excludes shared preparation/copying. Aggregate CPU belongs to joint execution receipt.'});Path(str(out)+'.receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
 comparisons=[r for w in workers for r in w['comparisons']]
 result={'schema':'autoformalization-parallel-cache-execution/v1','split':a.split,'count':len(ids),'arms':4,'workers':2,'runner_sha256':sha(here/'cached_execution_parallel.py'),'collector_sha256':sha(__file__),'source_only_eval_sha256':frozen['source_only_eval_sha256'],'native_implementation_sha256':frozen['native_implementation_sha256'],'sources_sha256':sourcehash,'embeddings_sha256':workers[0]['embeddings_sha256'],'all_selection_predictions_bitexact':a.split=='selection' and all(w['all_selection_predictions_bitexact'] for w in workers),'selection_comparison_pairs':len(comparisons),'comparisons':comparisons,'actual_decoder_calls':sum(w['actual_decoder_calls'] for w in workers),'cpu_seconds':sum(w['cpu_seconds'] for w in workers),'worker_wall_seconds':[w['wall_seconds'] for w in workers],'worker_peak_rss_bytes':[w['max_rss_bytes'] for w in workers],'collector_wall_seconds':time.monotonic()-start,'source_activation_wall_seconds':sum(r['source_activation_wall_seconds'] for r in activations.values()),'source_activation_receipts_sha256':sha(a.root/'source_activation_receipts.jsonl'),'per_arm_predict_row_seconds':{name:sum(w['per_arm_predict_row_seconds'][name] for w in workers) for name in NAMES},'timing_scope':'Joint worker CPU includes all four arms and shared preparation; simultaneous worker wall times are separate, not additive elapsed runtime','partition':'original full-source-file row index modulo2; immutable scientific cohort unchanged','source_activations_depend_on_learned_parameters':False}
 target=a.root/('qualification.json' if a.split=='selection' else 'execution_receipt.json');target.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='comparisons'}))
if __name__=='__main__':main()
