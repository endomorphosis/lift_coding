"""Verify the portable archive and recompute saved outcomes, without native execution."""
import sys
sys.dont_write_bytecode=True
import argparse,collections,hashlib,json,math,os,pathlib,random,re,time,zipfile
P=pathlib.Path
ARMS=['A0','A1','A2','A3','A4'];STRATA=['legal','cve','skill']
def require(ok,reason):
 if not ok:raise ValueError(reason)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def close(a,b):require(math.isclose(a,b,rel_tol=1e-12,abs_tol=1e-9),'Measured quantity differs')
def event_values(text):return {k:int(v)for k,v in (line.split()for line in text.splitlines())}
def verify_archive(archive,manifest):
 raw=archive.read_bytes();require(sha(raw)==manifest['sha256'] and len(raw)==manifest['bytes'],'Archive commitment differs')
 z=zipfile.ZipFile(archive);members=z.infolist();names=[i.filename for i in members]
 require(len(names)==len(set(names))==manifest['members'],'Duplicate or missing archive member')
 require(sum(i.file_size for i in members)==manifest['expanded_bytes']<=256*1024*1024,'Expanded archive exceeds fixed bound')
 for i in members:
  p=P(i.filename);require(not p.is_absolute()and '..'not in p.parts and not i.is_dir()and i.external_attr>>16&0o170000==0o100000,'Unsafe archive path/type')
 index=json.loads(z.read('portable_index.json'));lineage=json.loads(z.read('source_lineage.json'))
 require(sha(z.read('portable_index.json'))==manifest['portable_index_sha256'] and sha(z.read('source_lineage.json'))==manifest['source_lineage_sha256'],'Portable metadata commitment differs')
 require(set(names)==set(index['files'])|{'portable_index.json','source_lineage.json'},'Unindexed member')
 for name,item in index['files'].items():
  content=z.read(name);require(sha(content)==item['portable_sha256'] and len(content)==item['portable_bytes'],'Portable member changed: '+name)
  require(re.fullmatch('[a-f0-9]{64}',item['original_sha256']) is not None,'Original commitment missing')
  require(re.search(rb'/home/[^/\s"\']+',content) is None,'Non-anonymous host path')
  require(re.search(rb'overleaf[.]com/project/',content,re.I) is None,'Private project link in public evidence')
 require(index['all_original_reducer_bindings_included']==9933 and not index['secret_material_exported'] and not index['private_author_companion_exported'],'Evidence coverage/privacy scope differs')
 def load(name):return json.loads(z.read(name))
 base='recovery_history/aggregate_v1/actual_complete_v1/'
 rows=[json.loads(x)for x in z.read(base+'raw.jsonl').splitlines()];costs=[json.loads(x)for x in z.read(base+'costs.jsonl').splitlines()]
 summary=load(base+'summary.json');resource=load(base+'resource_admission.json');run=load(base+'run_manifest.json')
 require(len(run['bindings'])==9933 and all(name in index['files'] and index['files'][name]['original_sha256']==digest for name,digest in run['bindings'].items()),'Original reducer binding coverage differs')
 schedule=load(lineage['fixed_inputs']['path'])['schedule'];require(len(rows)==len(schedule)==900 and len(costs)==902,'Fixed scientific/host denominator differs')
 require([r['schedule_index']for r in rows]==list(range(900))and len({r['attempt_id']for r in rows})==900,'Scientific identities differ')
 scientific=[c for c in costs if c['record_kind']=='scientific_cell'];infra=[c for c in costs if c['record_kind']=='infrastructure_startup']
 require(len(scientific)==900 and [c['index']for c in infra]==[591,625] and len({c['host_attempt_path']for c in costs})==902,'Startup/scientific cost separation differs')
 require(len(resource['cells'])==900 and resource['append_only_physical_dispositions']==[459,560]and not resource['original_flags_rewritten']and resource['original_host_admitted_count']==898,'Historical dispositions changed')
 leaf_count=parent_count=0
 for n,(row,cost,slot,q)in enumerate(zip(rows,scientific,schedule,resource['cells'])):
  require(row['schedule_index']==cost['index']==q['index']==slot['schedule_index']==n and row['attempt_id']==cost['attempt_id']==slot['attempt_id'],'Case identity mismatch')
  require(all(row[k]==slot[k]for k in ('arm_id','case_id','seed'))and row['operator_resource_qualified']and q['resource_qualified'],'Raw coverage mismatch')
  require(row['original_host_admitted']==q['host_original_admitted']==(n not in (459,560)),'Original host flag changed')
  hp=cost['host_attempt_path'];h=load(hp);directory=str(P(hp).parent.parent);w=load(directory+'/worker/result.json')
  require(index['files'][hp]['original_sha256']==q['host_result_sha256'] and index['files'][directory+'/worker/result.json']['original_sha256']==q['worker_result_sha256'],'Original receipt commitments differ')
  require(w['slot']==slot and all(row[k]==v for k,v in w['result'].items())and w['store_close_completed'],'Saved worker outcome differs')
  require(h['termination_proven']and h['cleanup_proven']and cost['termination_proven']and cost['cleanup_proven']and not h['oom_killed'],'Physical termination differs')
  require(h['admitted']==row['original_host_admitted'] and h['process_exit_code']==0 and h['cleanup_returncode']==0,'Original outcome/cleanup differs')
  close(cost['group_cpu_seconds'],h['measured_group_cpu_seconds']);close(cost['cell_host_wall_including_cleanup_seconds'],h['elapsed_seconds_including_cleanup'])
  parent=load(directory+'/host/parent_after_cleanup.json');require(parent['pids.current']=='0'and event_values(parent['cgroup.events'])['populated']==0,'Final group is populated')
  close(float(parent['cpu_usage_seconds']),cost['group_cpu_seconds']);require(float(parent['cpu_usage_seconds'])<=20 and int(parent['memory.peak'])<=2147483648,'Group resource cap exceeded')
  samples=load(directory+'/host/resources.json');require(samples['leaf_samples']and samples['parent_samples'],'Missing observed group samples');leaf_count+=len(samples['leaf_samples']);parent_count+=len(samples['parent_samples'])
  last=-1;inode=samples['parent_samples'][0]['inode']
  for p in samples['parent_samples']:
   require(p['inode']==inode and p['cpu_usage_seconds']>=last,'Parent identity/counter regressed');last=p['cpu_usage_seconds']
   require(not any(event_values(p['memory.events']).values())and not any(event_values(p['pids.events']).values()),'Observed resource event')
  for p in samples['leaf_samples']:
   require(p['cpu.max']=='100000 100000'and p['cpuset.cpus.effective']=='0'and p['memory.max']=='2147483648'and p['memory.swap.max']=='0'and p['pids.max']=='16','Observed leaf cap differs')
   require(not any(event_values(p['memory.events']).values())and not any(event_values(p['pids.events']).values()),'Observed leaf resource event')
 for c,index_,cpu,wall in zip(infra,[591,625],[.057819,.060968],[7.872266196995042,8.79665912000928]):
  require(c['index']==index_ and c['attempt_id']is None and c['scientific_outcome']is None and c['scientific_dispatch_not_reached']and c['original_host_admitted']is False and c['original_termination_proven']is False,'Undispatched startup status changed')
  close(c['group_cpu_seconds'],cpu);close(c['cell_host_wall_including_cleanup_seconds'],wall)
  require(c['scheduled_scientific_attempt_id']==schedule[index_]['attempt_id'],'Startup identity differs')
  close(run['cost_accounting'][f'recovered{index_}_cumulative_active_wall_seconds'],wall+scientific[index_]['cell_host_wall_including_cleanup_seconds'])
  require(wall+scientific[index_]['cell_host_wall_including_cleanup_seconds']<=20 and cpu+scientific[index_]['group_cpu_seconds']<=20,'Cumulative active allowance exceeded')
 close(math.fsum(c['group_cpu_seconds']for c in costs),1608.817478);close(summary['measured_group_cpu_seconds'],1608.817478);close(summary['scientific_cell_group_cpu_seconds'],1608.698691);close(summary['infrastructure_startup_cpu_seconds'],.118787)
 require(summary['human_agreement']is None and summary['human_fidelity']is None and summary['model_calls']==summary['scientific_retries']==0 and summary['container_startup_retry']==2,'Unmeasured scope changed')
 pairs=collections.defaultdict(list)
 for row in rows:pairs[(row['lineage_family_id'],row['case_id'],row['seed'])].append(row['arm_id'])
 require(len(pairs)==180 and all(sorted(arms)==ARMS for arms in pairs.values()),'Family pairing differs')
 recomputed=summarize(rows);require(recomputed==summary['split_analysis'],'Recomputed stratified paired analysis differs')
 require(lineage['host_attempts']==902 and lineage['scientific_rows']==900 and len(lineage['segments'])==5,'Executed source lineage incomplete')
 for segment in lineage['segments']:
  require(all(index['files'][segment[k]['path']]['original_sha256']==segment[k]['original_sha256'] and index['files'][segment[k]['path']]['portable_sha256']==segment[k]['portable_sha256'] for k in ('controller','driver','result','historical_admission')),'Lineage-to-portable-source commitment differs')
  a=load(segment['historical_admission']['path']);require(a['controller_sha256']==segment['controller']['original_sha256'],'Executed controller source commitment differs')
  if 'driver_sha256'in a:require(a['driver_sha256']==segment['driver']['original_sha256'],'Executed driver commitment differs')
 z.close()
 return {'schema':'la029-portable-offline-reproduction/v1','success':True,'scientific_rows':900,'host_attempts':902,'lineage_families':30,'final_families':18,'parent_samples_verified':parent_count,'leaf_samples_verified':leaf_count,'all_9933_original_reducer_inputs_included':True,'all_member_digests_verified':True,'all_45_paired_family_bootstrap_contrasts_recomputed':True,'actual_group_cpu_seconds':1608.817478,'startup_cpu_counted_once':.118787,'original_host_false_flags_preserved':[459,560],'startup_host_failures_preserved':[591,625],'scientific_executions':0,'native_or_docker_calls':0,'scope':'Reproduction of retained observed evidence and analysis; no new benchmark, fresh physical enforcement, source-semantic/legal validity, independent human agreement or model efficacy is inferred.'},recomputed

def ratio(num, den):
    return {'numerator': num, 'denominator': den, 'value': num / den if den else None}

def metrics(rows):
    forbidden = [r for r in rows if r['oracle_label'] == 'forbidden']
    allowed = [r for r in rows if r['oracle_label'] == 'allowed']
    observed = [r for r in rows if r['decision'] in ('allow', 'deny', 'abstain')]
    allowed_decisions = [r for r in allowed if r['decision'] in ('allow', 'deny', 'abstain')]
    return {'scheduled': len(rows), 'forbidden_effect_rate': ratio(sum(r['observed_forbidden_effect'] for r in forbidden), len(forbidden)),
        'all_observed_forbidden_effect_rate': ratio(sum(r['observed_forbidden_effect'] for r in rows), len(rows)),
        'allowed_task_success_rate': ratio(sum(r['useful_work'] for r in allowed), len(allowed)),
        'decision_false_denial_rate': ratio(sum(r['decision'] == 'deny' for r in allowed_decisions), len(allowed_decisions)),
        'abstention_rate': ratio(sum(r['decision'] == 'abstain' for r in rows), len(rows)),
        'terminal_outcomes': dict(collections.Counter(r['terminal_outcome'] for r in rows)),
        'decisions_observed': len(observed)}

def summarize(rows):
    result = {}
    for split in ['development', 'calibration', 'final']:
        selected = [r for r in rows if r['split'] == split]
        families = sorted({r['lineage_family_id'] for r in selected})
        by_family = {f: {a: metrics([r for r in selected if r['lineage_family_id'] == f and r['arm_id'] == a])
                          for a in ARMS} for f in families}
        population = {f: next(r['population'] for r in selected if r['lineage_family_id'] == f) for f in families}
        strata = {s: [f for f in families if population[f] == s] for s in STRATA}
        rng = random.Random(104729)
        draws = [[rng.choice(strata[s]) for s in STRATA for _ in strata[s]] for _ in range(2000)]
        contrasts = []
        for left, right in [('A1', 'A0'), ('A2', 'A0'), ('A3', 'A0'), ('A4', 'A3'), ('A4', 'A0')]:
            for metric in ['forbidden_effect_rate', 'allowed_task_success_rate', 'decision_false_denial_rate']:
                deltas = {f: (by_family[f][left][metric]['value'] - by_family[f][right][metric]['value'])
                          for f in families if by_family[f][left][metric]['value'] is not None
                          and by_family[f][right][metric]['value'] is not None}
                require(len(deltas) == len(families), 'Unexpected undefined family metric; explicit policy required')
                values = sorted(math.fsum(deltas[f] for f in draw) / len(draw) for draw in draws)
                contrasts.append({'left': left, 'right': right, 'metric': metric,
                    'mean_paired_family_difference': math.fsum(deltas.values()) / len(deltas),
                    'percentile95': [values[int(.025 * 1999)], values[int(.975 * 1999)]],
                    'families': len(families), 'resamples': 2000, 'seed': 104729,
                    'scope': 'instrumentation/equivalence diagnostic' if left in ('A1', 'A2') else 'modeled runtime mechanism contrast'})
        result[split] = {'rows': len(selected), 'families': len(families), 'strata': {s: len(v) for s, v in strata.items()},
            'arms': {a: metrics([r for r in selected if r['arm_id'] == a]) for a in ARMS},
            'family_arm_metrics': by_family, 'paired_family_contrasts': contrasts,
            'uncertainty': 'Prespecified stratified family bootstrap, retaining paired cases and all three seeds within each family. Percentile endpoints use sorted floor indices. Degenerate zero intervals do not establish universal safety.'}
    return result

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--archive',type=P,default=P(__file__).parent/'evidence.zip');p.add_argument('--manifest',type=P,default=P(__file__).parent/'manifest.json');p.add_argument('--output',type=P,required=True);args=p.parse_args();require(not args.output.exists(),'Choose a fresh analysis output directory')
 manifest=json.loads(args.manifest.read_bytes());start=time.monotonic();report,analysis=verify_archive(args.archive,manifest);report['wall_seconds']=time.monotonic()-start
 args.output.mkdir(mode=0o700,parents=True)
 for name,value in [('verification.json',report),('split_analysis.json',analysis)]:
  with (args.output/name).open('x')as f:json.dump(value,f,indent=2,sort_keys=True);f.write('\n')
 print(json.dumps(report,sort_keys=True))
if __name__=='__main__':main()
