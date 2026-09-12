"""One-shot private source binding; stdout contains aggregate counts/commitments only."""
import collections,copy,datetime,fcntl,hashlib,hmac,json,os,re,stat,unicodedata
from pathlib import Path
B=Path(__file__).resolve().parent
LANE=Path('/home/barberb/lift_coding/.worktrees/vericodegen-autoformalization-2026')
ROOT=Path('/home/barberb/.local/state/ipfs_accelerate_py/vericodegen-2026/research-inputs/autoformalization')
OLD=ROOT/'af004-v1';OUT=ROOT/'af005-independent-annotation-v1'
PLAN_SHA='41bfb6978de5560fcc7404c04e34fe8b42297c3c875c7ec3353c9fc55348e87a'
os.umask(0o077)
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def check_private(p,directory=False):
 s=p.lstat();assert p.resolve()==p and s.st_uid==os.getuid()
 assert (stat.S_ISDIR(s.st_mode) if directory else stat.S_ISREG(s.st_mode))
 assert stat.S_IMODE(s.st_mode)==(0o700 if directory else 0o600)
def read_private(p):
 check_private(p)
 fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW)
 with os.fdopen(fd,'rb') as f:return f.read()
def durable(p,data):
 fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 with os.fdopen(fd,'wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
def fsyncdir(p):
 fd=os.open(p,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
 try:os.fsync(fd)
 finally:os.close(fd)
def main():
 assert digest(B/'sampling_plan.json')==PLAN_SHA
 plan=json.loads((B/'sampling_plan.json').read_text());bindings=plan['source_bindings']
 check_private(OLD,True)
 lock=os.open(ROOT/'af005-annotation-binding.lock',os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
 try:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  assert not OUT.exists(), 'private binding already exists; no replacement/reselection allowed'
  tracked=[OLD/n for n in ['partitions.private.json','final_test.private.jsonl','partition_salt.private.bin','holdout_deny_index.private.json','full_graph.private.json']]
  original={str(p):digest(p) for p in tracked}
  assert original[str(OLD/'partitions.private.json')]==bindings['private_partition_commitment_sha256']
  assert original[str(OLD/'final_test.private.jsonl')]==bindings['private_final_source_file_sha256']
  public={LANE/'papers/completion/autoformalization'/name:key for name,key in [
   ('data/annotation_guidelines.md','guidelines_sha256'),('data/annotation_packets.jsonl','public_packets_sha256'),
   ('data/gold_facets.jsonl','public_gold_templates_sha256'),('data/splits.json','splits_sha256'),('config/experiment_plan.json','experiment_plan_sha256')]}
  assert all(digest(p)==bindings[key] for p,key in public.items())
  metadata=json.loads(read_private(OLD/'partitions.private.json'))['membership']['final_test']
  salt=read_private(OLD/'partition_salt.private.bin');assert len(salt)>=32
  def rank(domain,value):return hmac.new(salt,canonical({'domain':plan['selection_domain']+'/'+domain,'seed':104729,'plan_sha256':PLAN_SHA,'value':value}),hashlib.sha256).hexdigest()
  groups=collections.defaultdict(lambda:collections.defaultdict(list));unit_group={}
  for row in metadata:
   group=row['component'];unit=row['normalized_source_unit_sha256']
   assert unit not in unit_group or unit_group[unit]==group
   unit_group[unit]=group;groups[group][unit].append(row['record_id'])
  ordered=sorted(groups,key=lambda g:(rank('group',g),str(g)))
  sizes=[len(groups[g]) for g in ordered];assert len(metadata)==1921 and len(unit_group)==1913 and len(ordered)==20
  capacity=[n-1 for n in sizes];den=sum(capacity);remaining=100-len(ordered)
  allocation=[1+remaining*n//den for n in capacity]
  spare=100-sum(allocation)
  priority=sorted(range(len(ordered)),key=lambda i:(-(remaining*capacity[i]%den),rank('group',ordered[i])))
  for i in priority[:spare]:allocation[i]+=1
  assert sum(allocation)==100 and all(1<=n<=size for n,size in zip(allocation,sizes))
  chosen=[];private_groups=[]
  for index,(group,N,n) in enumerate(zip(ordered,sizes,allocation),1):
   units=sorted(groups[group],key=lambda u:(rank('unit',u),u))[:n]
   private_groups.append({'component':group,'private_group_slot':index,'N_h':N,'n_h':n,'unit_digests':units})
   for unit in units:
    aliases=sorted(groups[group][unit]);chosen.append({'unit_digest':unit,'record_id':aliases[0],'alias_record_ids':aliases,'component':group,'group_slot':index,'N_h':N,'n_h':n})
  assert len({r['unit_digest'] for r in chosen})==100
  selected_ids={r['record_id'] for r in chosen};documents={}
  # Full sources are read only inside this private host process, never printed.
  for line in read_private(OLD/'final_test.private.jsonl').splitlines():
   row=json.loads(line)
   if row['record_id'] in selected_ids:documents[row['record_id']]=row
  assert set(documents)==selected_ids
  pubpack=[json.loads(s) for s in (LANE/'papers/completion/autoformalization/data/annotation_packets.jsonl').read_text().splitlines()]
  slots=sorted((p for p in pubpack if p['packet_role']=='planned_final_annotation_slot'),key=lambda p:p['packet_id']);assert len(slots)==100
  gold=[json.loads(s) for s in (LANE/'papers/completion/autoformalization/data/gold_facets.jsonl').read_text().splitlines()]
  gold_by_id={g['packet_id']:g for g in gold}
  packets=[];pending=[]
  for number,(selected,slot) in enumerate(zip(chosen,slots),1):
   source=documents[selected['record_id']]
   normal=' '.join(re.findall(r'[^\W_]+',unicodedata.normalize('NFKC',source['text']).casefold()))
   assert hashlib.sha256(normal.encode()).hexdigest()==selected['unit_digest']
   packet=copy.deepcopy(slot);pid=f'AF005-BOUND-{number:03d}'
   packet.update(packet_id=pid,packet_role='bound_final_annotation_unit',evaluation_sample=True,evaluation_eligible=False,
    binding_status='source_bound_pending_independent_annotation',original_provisional_template_id=slot['packet_id'],
    original_provisional_group_assignment_superseded=True,actual_independent_review=False)
   packet['source']={k:source[k] for k in ['record_id','text','title','citation','current_through','effective_start','effective_end','authority_kind','authority_claim','source_lineage','rights_review'] if k in source}
   packet['source'].update(split='final_test',disclosure='private_authorized_annotation_only',body_in_packet=True,identities_published=False,
    normalized_source_unit_sha256=selected['unit_digest'],alias_record_ids=selected['alias_record_ids'],component=selected['component'],private_group_slot=selected['group_slot'])
   packet['sampling']={'plan_sha256':PLAN_SHA,'N_h':selected['N_h'],'n_h':selected['n_h'],
    'inclusion_probability':{'numerator':selected['n_h'],'denominator':selected['N_h']},
    'inverse_probability_weight':{'numerator':selected['N_h'],'denominator':selected['n_h']},
    'population_unique_units':1913,'primary_estimand':'finite_population_unit_mean'}
   pending_gold=copy.deepcopy(gold_by_id[slot['packet_id']])
   assert pending_gold['label_origin'] is None and not pending_gold['annotators'] and pending_gold['semantic_claim_status']=='unmeasured'
   pending_gold.update(packet_id=pid,packet_role='bound_final_annotation_unit',evaluation_sample=True,evaluation_eligible=False)
   packets.append(packet);pending.append(pending_gold)
  assert all(not p['model_outputs_present'] and not p['teacher_ir_present'] and not p['gold_values_present'] for p in packets)
  build=ROOT/'.af005-independent-annotation-v1.build';assert not build.exists(), 'prior partial build requires inspection; no blind retry'
  build.mkdir(mode=0o700);fsyncdir(ROOT)
  durable(build/'sampling_plan.json',(B/'sampling_plan.json').read_bytes())
  durable(build/'annotation_packets.private.jsonl',b''.join(canonical(p)+b'\n' for p in packets))
  durable(build/'gold_facets.pending.private.jsonl',b''.join(canonical(p)+b'\n' for p in pending))
  private_manifest={'schema':'af005-private-source-binding/v1','created_at':now(),'sampling_plan_sha256':PLAN_SHA,
   'private_partition_commitment_sha256':bindings['private_partition_commitment_sha256'],'groups':private_groups,'selected_units':chosen,
   'packets_sha256':digest(build/'annotation_packets.private.jsonl'),'pending_gold_sha256':digest(build/'gold_facets.pending.private.jsonl'),
   'actual_human_annotations':0,'actual_adjudicated_units':0,'evaluation_eligible_units':0}
  durable(build/'binding_manifest.private.json',canonical(private_manifest)+b'\n');fsyncdir(build)
  assert all(digest(Path(p))==h for p,h in original.items())
  assert all(digest(p)==bindings[key] for p,key in public.items())
  os.rename(build,OUT);fsyncdir(ROOT);check_private(OUT,True)
  for p in OUT.iterdir():check_private(p)
  # Public record deliberately excludes all actual IDs, unit digests and body text.
  report={'schema':'af005-private-annotation-binding-report/v1','completed':True,'completed_at':now(),
   'helper_sha256':digest(Path(__file__)),'sampling_plan_sha256':PLAN_SHA,'private_directory':str(OUT),
   'population_records':1921,'population_unique_units':1913,'operational_groups':20,'bound_unique_units':100,
   'bound_group_count':len(private_groups),'alias_duplicates_selected_as_extra_units':0,
   'anonymous_group_allocation_histogram':dict(collections.Counter(f'{N}:{n}' for N,n in zip(sizes,allocation))),
   'human_annotations':0,'adjudicated_units':0,'evaluation_eligible_units':0,'unit_inclusion_probability':'n_h/N_h','unit_inverse_probability_weight':'N_h/n_h',
   'primary_estimand':'finite-population unit mean over1913 unique final units; group dependence retained',
   'private_commitments':{p.name:digest(p) for p in OUT.iterdir()},'private_modes':'directory0700/files0600',
   'original_private_inputs_and_public_preparation_unchanged':True,'new_source_oracle_or_label_data_exported_to_provider':False,
   'limits':['100 privately bound sources are prepared, not independently annotated.','20 operational components are correlated; four broad official editions are not20 publishers.','One giant1730-unit component dominates unit weighting; report weighted intervals and macro-edition sensitivity, not equal-group point weighting.','No benchmark, model selection, formal validity, human agreement or semantic fidelity result.','Provider filesystem exclusion is an external runtime contract; this binding helper does not claim network/pretraining denial.']}
  # Fail before public output if any private identifier/body escaped report construction.
  encoded=canonical(report)
  assert not any(x.encode() in encoded for x in selected_ids|{r['unit_digest'] for r in chosen})
  durable(B/'binding_report.json',json.dumps(report,indent=2).encode()+b'\n')
  print(json.dumps({'completed':True,'report_sha256':digest(B/'binding_report.json'),'bound_units':100,'groups':20,'human_annotations':0,'evaluation_eligible':0}))
 finally:os.close(lock)
if __name__=='__main__':main()
