#!/usr/bin/env python3
"""Report preregistered source-component and conditional-unit uncertainty."""
import argparse,collections,hashlib,json,math
from pathlib import Path
import numpy as np
SEEDS=(104729,130363,155921)

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--root',required=True,type=Path);p.add_argument('--sources',required=True,type=Path);a=p.parse_args();final=a.root/'final'
 sources={r['record_id']:r for r in map(json.loads,open(a.sources))};ids=sorted(sources)
 if len(ids)!=1913:raise ValueError('Final source population incomplete')
 metric_names=('cosine','mse');loaded={};table=[]
 names=['T0']+[f'{arm}-{seed}' for arm in ('T1','T2','T3') for seed in SEEDS]
 for name in names:
  data=json.load(open(final/f'{name}.scores.json'));rows={r['record_id']:r for r in data['rows']}
  if set(rows)!=set(ids):raise ValueError(f'{name} score population incomplete')
  loaded[name]=np.array([[rows[rid][m] for m in metric_names] for rid in ids],dtype=float)
  receipt=json.load(open(final/f'{name}.predictions.jsonl.receipt.json'))
  if sha(final/f'{name}.predictions.jsonl')!=receipt['predictions_sha256']:raise ValueError('Prediction custody mismatch')
  table.append({'arm':name,'records':len(ids),'mean_cosine':float(loaded[name][:,0].mean()),'mean_mse':float(loaded[name][:,1].mean()),'sample_memory_hits':receipt.get('sample_memory_hits'),'actual_decoder_calls':receipt.get('new_decoder_calls',receipt.get('new_shared_decoder_calls',len(ids))),'wall_seconds':receipt['wall_seconds'],'cpu_seconds':receipt['cpu_seconds'],'max_rss_bytes':receipt['max_rss_bytes']})
 seed_mean=np.mean([loaded[f'T2-{seed}'] for seed in SEEDS],axis=0);delta=seed_mean-loaded['T0']
 groups=sorted({r['component_id'] for r in sources.values()});members={g:[i for i,rid in enumerate(ids) if sources[rid]['component_id']==g] for g in groups}
 if len(groups)!=20:raise ValueError('Frozen AF004 component count changed')
 size=np.array([len(members[g]) for g in groups]);sums=np.array([delta[members[g]].sum(axis=0) for g in groups]);rng=np.random.default_rng(104729);draws=rng.integers(0,len(groups),size=(10000,len(groups)))
 boot=sums[draws].sum(axis=1)/size[draws].sum(axis=1)[:,None]
 primary={m:{'point':float(delta[:,j].mean()),'ci95':np.quantile(boot[:,j],[.025,.975]).tolist()} for j,m in enumerate(metric_names)}
 rng=np.random.default_rng(104729);unit_boot=np.zeros((2000,2))
 domains=sorted({r['family'] for r in sources.values()})
 for domain in domains:
  ix=np.array([i for i,rid in enumerate(ids) if sources[rid]['family']==domain]);draw=rng.integers(0,len(ix),size=(2000,len(ix)));unit_boot+=delta[ix][draw].sum(axis=1)
 unit_boot/=len(ids);secondary={m:{'point':float(delta[:,j].mean()),'ci95':np.quantile(unit_boot[:,j],[.025,.975]).tolist()} for j,m in enumerate(metric_names)}
 per_domain={domain:{'count':sum(sources[rid]['family']==domain for rid in ids),'T0_mean_cosine':float(loaded['T0'][[sources[rid]['family']==domain for rid in ids],0].mean()),'T2_seed_mean_cosine':float(seed_mean[[sources[rid]['family']==domain for rid in ids],0].mean()),'T0_mean_mse':float(loaded['T0'][[sources[rid]['family']==domain for rid in ids],1].mean()),'T2_seed_mean_mse':float(seed_mean[[sources[rid]['family']==domain for rid in ids],1].mean())} for domain in domains}
 for seed in SEEDS:
  if not np.array_equal(loaded[f'T2-{seed}'],loaded[f'T3-{seed}']):raise ValueError('Tied T3 decoder scores differ')
 report={'schema':'autoformalization-final-AE-summary/v1','sources_sha256':sha(a.sources),'profile_sha256':sha(a.root/'scientific_profile.json'),'scorer_sha256':sha(__file__),'table':table,'domain':per_domain,'cohort_records':len(ids),'unique_original_components':len(groups),'component_sizes':sorted(size.tolist(),reverse=True),'largest_component_fraction':float(size.max()/len(ids)),'T2_minus_T0_primary_component_bootstrap':{'draws':10000,'seed':104729,'sampling':'resample original components; include all their member units; average the three training seeds within unit before resampling','metrics':primary,'draws_omitting_dominant_component':int(np.sum(~np.any(draws==int(np.argmax(size)),axis=1)))},'T2_minus_T0_secondary_unit_bootstrap':{'draws':2000,'seed':104729,'sampling':'domain-stratified units, conditional finite-cohort display only; not independent-unit generalization uncertainty','metrics':secondary},'independent_T3_decoder_replications':0,'native_T3_head_calls':sum(json.load(open(final/f'T3-{s}.predictions.jsonl.receipt.json'))['actual_native_proof_head_calls'] for s in SEEDS),'actual_T1_memory_lookups':sum(json.load(open(final/f'T1-{s}.predictions.jsonl.receipt.json'))['native_lookup_calls'] for s in SEEDS),'limitations':['Source-conditioned vector reconstruction, not independent legal or semantic fidelity','Linear path from the input embedding remains; identity copy would trivially yield cosine1/MSE0','One component contains most records; only four corpus editions underlie the cohort','T0/T2/T3 view and modal logit heads are empty, so no learned classifier gain is established','T3 embedding values reuse the tied T2 decoder and are not independent repetitions']}
 if (final/'training_mean.scores.json').exists():
  mean_data=json.load(open(final/'training_mean.scores.json'));mean_rows={r['record_id']:r for r in mean_data['rows']}
  if set(mean_rows)!=set(ids):raise ValueError('Training-mean prediction population incomplete')
  mean_values=np.array([[mean_rows[rid][m] for m in metric_names] for rid in ids]);mean_receipt=json.load(open(final/'training_mean.predictions.jsonl.receipt.json'))
  if sha(final/'training_mean.predictions.jsonl')!=mean_receipt['predictions_sha256'] or mean_receipt['frozen_baseline_sha256']!=sha(a.root/'training_mean_baseline.freeze.json'):raise ValueError('Training-mean custody mismatch')
  table.append({'arm':'TRAIN mean supplement','records':len(ids),'mean_cosine':float(mean_values[:,0].mean()),'mean_mse':float(mean_values[:,1].mean()),'sample_memory_hits':None,'actual_decoder_calls':0,'wall_seconds':mean_receipt['wall_seconds'],'cpu_seconds':None,'max_rss_bytes':None})
  report['supplemental_training_mean']={'frozen_baseline_sha256':sha(a.root/'training_mean_baseline.freeze.json'),'point_T2_minus_mean_cosine':float((seed_mean[:,0]-mean_values[:,0]).mean()),'point_T2_minus_mean_mse':float((seed_mean[:,1]-mean_values[:,1]).mean()),'interpretation':'Descriptive constant-training-mean comparison added before final AE predictions; original primary T2-vs-T0 analysis unchanged','domain':{domain:{'mean_cosine':float(mean_values[[sources[rid]['family']==domain for rid in ids],0].mean()),'mean_mse':float(mean_values[[sources[rid]['family']==domain for rid in ids],1].mean())} for domain in domains}}
 if (final/'execution_receipt.json').exists():
  execution=json.load(open(final/'execution_receipt.json'));report['joint_source_preparation_and_T0_T2_execution']={k:v for k,v in execution.items() if k!='comparisons'}
 (final/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
 lines=['# Held-out autoencoder results','','All rows use the frozen 1,913-source cohort. Source embedding reconstruction is a diagnostic, not semantic fidelity.','','| Arm | Sources | Mean cosine | Mean MSE | Memory hits | Decoder calls |','|---|---:|---:|---:|---:|---:|']
 for row in table:lines.append(f"| {row['arm']} | {row['records']} | {row['mean_cosine']:.6f} | {row['mean_mse']:.8f} | {row['sample_memory_hits'] if row['sample_memory_hits'] is not None else '—'} | {row['actual_decoder_calls']} |")
 lines+=['',f"The primary paired component bootstrap uses 10,000 draws over {len(groups)} original source components. The largest contains {size.max()} / {len(ids)} units. Training seeds are averaged within source units."]
 for m,x in primary.items():lines.append(f"T2−T0 {m}: {x['point']:+.8f}; component-bootstrap 95% interval [{x['ci95'][0]:+.8f}, {x['ci95'][1]:+.8f}].")
 lines+=['','T3 decoder entries are reused by exact parameter isolation; the native isolated proof heads are evaluated separately. T1 counts actual memory lookups and verifies every cold fallback against the T0 projection.']
 (final/'RESULTS.md').write_text('\n'.join(lines)+'\n');print(json.dumps({'cohort':len(ids),'table':table,'primary':primary}))
if __name__=='__main__':main()
