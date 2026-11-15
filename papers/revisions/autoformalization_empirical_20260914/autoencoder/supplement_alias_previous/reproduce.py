#!/usr/bin/env python3
"""Recompute released numeric metrics and predeclared uncertainty from outputs.

Needs Python3 + NumPy (original execution used NumPy1.26.4). No model download,
service, GPU, native compiler, or private checkout is required.
"""
import argparse,hashlib,importlib.util,json,math
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent
SEEDS=(104729,130363,155921)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def close(a,b):
 if not np.allclose(a,b,rtol=0,atol=1e-12):raise ValueError('Published numeric result did not reproduce')
def main():
 p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True);manifest=json.load(open(HERE/'manifest.json'));published=json.load(open(HERE/'summary.json'))
 for file,key in [('source_metadata.jsonl','source_metadata_sha256'),('source_embeddings.jsonl','source_embeddings_sha256'),('training.source_embeddings.jsonl','training_embeddings_sha256')]:
  if sha(HERE/file)!=manifest[key]:raise ValueError('Release input identity mismatch: '+file)
 profile=json.load(open(HERE/'provenance/scientific_profile.json'))
 if sha(HERE/'provenance/scientific_profile.json')!=manifest['profile_sha256'] or sha(HERE/'summary.json')!=manifest['reported_summary_sha256'] or sha(HERE/'provenance/score_embeddings.py')!=profile['scorer_sha256']:raise ValueError('Frozen metric/profile identity mismatch')
 spec=importlib.util.spec_from_file_location('frozen_numeric_scorer',HERE/'provenance/score_embeddings.py');scorer=importlib.util.module_from_spec(spec);spec.loader.exec_module(scorer)
 sources={r['record_id']:r for r in map(json.loads,open(HERE/'source_metadata.jsonl'))};ids=sorted(sources)
 if len(ids)!=1913:raise ValueError('Cohort incomplete')
 loaded={};verified=[];vector_digests={}
 tables={r['arm']:r for r in published['table']}
 if len(tables)!=len(published['table']):raise ValueError('Duplicate published table arm')
 for name,binding in manifest['arms'].items():
  pred=HERE/f'predictions/{name}.jsonl';expected=HERE/f'scores/{name}.json'
  if sha(pred)!=binding['compact_projection_sha256'] or sha(expected)!=binding['scores_sha256']:raise ValueError('Prediction/score artifact identity mismatch')
  receipt_path=HERE/f'provenance/prediction_receipts/{name}.json'
  if sha(receipt_path)!=binding['original_receipt_sha256']:raise ValueError('Original receipt identity mismatch')
  receipt=json.load(open(receipt_path))
  vector_digests[name]={r['record_id']:hashlib.sha256(json.dumps(r['decoded_source_embedding'],separators=(',',':')).encode()).hexdigest() for r in map(json.loads,open(pred))}
  rows,summary=scorer.score(pred,HERE/'source_embeddings.jsonl');byid={r['record_id']:r for r in rows};reference={r['record_id']:r for r in json.load(open(expected))['rows']}
  if set(byid)!=set(ids) or set(reference)!=set(ids):raise ValueError('Prediction/score cohort mismatch')
  for rid in ids:
   for key in ('family','arm_id','seed'):
    if byid[rid][key]!=reference[rid][key]:raise ValueError('Scored row metadata mismatch')
   close([byid[rid][k] for k in ('cosine','mse','squared_l2')],[reference[rid][k] for k in ('cosine','mse','squared_l2')])
  loaded[name]=np.array([[byid[rid][k] for k in ('cosine','mse')] for rid in ids]);verified.append({'arm':name,'records':len(rows),'all_rows_match_atol':1e-12,'mean_cosine':float(loaded[name][:,0].mean()),'mean_mse':float(loaded[name][:,1].mean())});(a.output/f'{name}.scores.json').write_text(json.dumps({'rows':rows,'summary':summary},indent=2)+'\n')
  table=tables['TRAIN mean supplement' if name=='training_mean' else name]
  if table['records']!=len(rows):raise ValueError('Published table denominator mismatch')
  close([table['mean_cosine'],table['mean_mse']],loaded[name].mean(axis=0))
  if table['actual_decoder_calls']!=receipt.get('new_decoder_calls',receipt.get('new_shared_decoder_calls',len(ids))) or table['sample_memory_hits']!=receipt.get('sample_memory_hits'):raise ValueError('Published decoder/memory counters differ from receipts')
  for key in ('wall_seconds','cpu_seconds','max_rss_bytes'):
   expected_cost=None if name=='training_mean' and key!='wall_seconds' else receipt.get(key)
   if table[key]!=expected_cost:raise ValueError('Published cost metadata differs from receipt')
 meanfreeze=json.load(open(HERE/'provenance/training_mean_baseline.freeze.json'));train=sorted(map(json.loads,open(HERE/'training.source_embeddings.jsonl')),key=lambda r:r['record_id'])
 if len(train)!=69 or sha(HERE/'training.source_embeddings.jsonl')!=meanfreeze['training_embeddings_sha256']:raise ValueError('Training mean input mismatch')
 mean=[sum(r['embedding_vector'][j] for r in train)/69 for j in range(384)];norm=math.sqrt(sum(x*x for x in mean));mean=[x/norm for x in mean]
 if mean!=meanfreeze['vector']:raise ValueError('Frozen training mean did not reproduce exactly')
 for row in map(json.loads,open(HERE/'predictions/training_mean.jsonl')):
  if row['decoded_source_embedding']!=mean:raise ValueError('Constant mean prediction changed')
 seed_mean=np.mean([loaded[f'T2-{seed}'] for seed in SEEDS],axis=0);delta=seed_mean-loaded['T0'];groups=sorted({r['component_id'] for r in sources.values()});members={g:[i for i,rid in enumerate(ids) if sources[rid]['component_id']==g] for g in groups};size=np.array([len(members[g]) for g in groups]);sums=np.array([delta[members[g]].sum(axis=0) for g in groups])
 if len(groups)!=20:raise ValueError('Component membership changed')
 rng=np.random.default_rng(104729);draws=rng.integers(0,len(groups),size=(10000,len(groups)));boot=sums[draws].sum(axis=1)/size[draws].sum(axis=1)[:,None];names=('cosine','mse');primary={m:{'point':float(delta[:,j].mean()),'ci95':np.quantile(boot[:,j],[.025,.975]).tolist()} for j,m in enumerate(names)}
 rng=np.random.default_rng(104729);uboot=np.zeros((2000,2));domains=sorted({r['family'] for r in sources.values()})
 for domain in domains:
  ix=np.array([i for i,rid in enumerate(ids) if sources[rid]['family']==domain]);draw=rng.integers(0,len(ix),size=(2000,len(ix)));uboot+=delta[ix][draw].sum(axis=1)
 uboot/=len(ids);secondary={m:{'point':float(delta[:,j].mean()),'ci95':np.quantile(uboot[:,j],[.025,.975]).tolist()} for j,m in enumerate(names)}
 for label,value in [('T2_minus_T0_primary_component_bootstrap',primary),('T2_minus_T0_secondary_unit_bootstrap',secondary)]:
  for metric in names:
   reference=published[label]['metrics'][metric];close(value[metric]['point'],reference['point']);close(value[metric]['ci95'],reference['ci95'])
 if sorted(size.tolist(),reverse=True)!=published['component_sizes']:raise ValueError('Published component sizes differ')
 for domain in domains:
  mask=[sources[rid]['family']==domain for rid in ids];expected=published['domain'][domain]
  if expected['count']!=sum(mask):raise ValueError('Published domain count differs')
  close([expected['T0_mean_cosine'],expected['T0_mean_mse']],loaded['T0'][mask].mean(axis=0));close([expected['T2_seed_mean_cosine'],expected['T2_seed_mean_mse']],seed_mean[mask].mean(axis=0))
  mean_expected=published['supplemental_training_mean']['domain'][domain];close([mean_expected['mean_cosine'],mean_expected['mean_mse']],loaded['training_mean'][mask].mean(axis=0))
 for seed in SEEDS:
  if not np.array_equal(loaded[f'T2-{seed}'],loaded[f'T3-{seed}']) or vector_digests[f'T2-{seed}']!=vector_digests[f'T3-{seed}']:raise ValueError('T3 tied decoder vector/metric equality mismatch')
 supplemental={'point_T2_minus_mean_cosine':float((seed_mean[:,0]-loaded['training_mean'][:,0]).mean()),'point_T2_minus_mean_mse':float((seed_mean[:,1]-loaded['training_mean'][:,1]).mean())}
 for key,value in supplemental.items():close(value,published['supplemental_training_mean'][key])
 result={'schema':'autoformalization-portable-metric-reproduction/v1','cohort':len(ids),'verified_arms':verified,'original_components':len(groups),'component_sizes':sorted(size.tolist(),reverse=True),'primary':primary,'secondary_conditional_unit_display':secondary,'supplemental_training_mean':supplemental,'training_mean_vector_bitexact':True,'independent_T3_decoder_replications':0,'published_reconstruction_means_and_bootstrap_intervals_verified_atol':1e-12,'published_table_costs_and_counters_match_original_receipts':True,'timing_remeasured':False,'T2_T3_decoded_vectors_bitexact':True,'numpy_version':np.__version__,'inference_rerun':False,'scope':'Reproduction from released numeric predictions, not re-execution of omitted checkpoint arrays or a test of legal-semantic truth'}
 (a.output/'reproduced_summary.json').write_text(json.dumps(result,indent=2)+'\n');(a.output/'metric_verification.json').write_text(json.dumps({'status':'PASS','sources':len(ids),'arms':len(verified),'scored_rows':len(ids)*len(verified),'bootstrap_draws':10000,'secondary_draws':2000,'training_mean_exact':True,'source_manifest_sha256':sha(HERE/'manifest.json')},indent=2)+'\n');print(json.dumps({'status':'PASS','sources':len(ids),'arms':len(verified),'output':str(a.output)}))
if __name__=='__main__':main()
