"""Separately admitted32-cell held-out A/B cold transport. Draft source."""
import hashlib,itertools,json,os,re,stat
from pathlib import Path
ARMS=('A','B');CACHES=('local_cold',);REPETITIONS=(104729,130363)
HISTORICAL_ARMS=('A','B','C','D','C-no-route','C-no-reuse');HISTORICAL_CACHES=('local_cold','local_warm')
UNITS=('ns-hist-09-tomlkit','ns-hist-10-installer','ns-hist-11-tornado','ns-hist-12-more-itertools','ns-hist-13-charset_normalizer','ns-hist-14-iniconfig','ns-hist-15-wheel','ns-hist-16-jinja')
FAMILIES=('upstream:sdispater/tomlkit','upstream:pypa/installer','upstream:tornadoweb/tornado','upstream:more-itertools/more-itertools','upstream:jawah/charset_normalizer','upstream:pytest-dev/iniconfig','upstream:pypa/wheel','upstream:pallets/jinja')
ORIGINAL_PLAN_SHA='6ed6e590479d7d71bdcc9cc67fc7cccf51b05230c0f6761fcd7c520bece2ac80'
def canon(x):return json.dumps(x,sort_keys=True,separators=(',',':')).encode()
def digest(x):return hashlib.sha256(canon(x)).hexdigest()
def require(ok,msg):
 if not ok:raise ValueError(msg)
def sha_ok(v):return type(v)is str and re.fullmatch('[0-9a-f]{64}',v)is not None
def cell_id(unit,arm,cache,repetition=104729):return digest({'unit':unit,'arm':arm,'cache':cache,'repetition':repetition,'record_kind':'final'})
def read_bound(path,expected):
 p=Path(path);require(p.is_absolute()and p.resolve()==p and sha_ok(expected),'canonical bound batch required')
 fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW)
 try:
  info=os.fstat(fd);require(stat.S_ISREG(info.st_mode)and info.st_mode&0o077==0 and info.st_size<=1048576 and p.parent.stat().st_mode&0o077==0,'private bounded batch required')
  with os.fdopen(fd,'rb',closefd=False)as f:raw=f.read(1048577)
 finally:os.close(fd)
 require(hashlib.sha256(raw).hexdigest()==expected,'batch bytes changed');return json.loads(raw)
def validate(batch):
 require(batch.get('schema')=='ns-historical-final-AB-cold-batch/v1'and batch.get('scope')=='heldout_AB_cold_final_only'and batch.get('final_admitted')is False and batch.get('requires_separate_operator_admission')is True,'separate final batch plan required')
 require(batch.get('enabled_arms')==list(ARMS)and batch.get('enabled_cache')=='local_cold'and batch.get('repetitions')==list(REPETITIONS)and all(type(v)is int for v in batch['repetitions']),'exact A/B cold original repetition identities required')
 require(all(type(batch.get(k))is int and batch[k]==32 for k in ('max_provider_calls','max_scorer_calls')),'exact32-cell ceiling required')
 require(batch.get('candidate_review_required')is True and type(batch.get('retries'))is int and batch['retries']==0 and batch.get('fallback_allowed')is False,'review/no-retry policy changed')
 require(set(batch['units'])==set(UNITS),'all eight frozen final units required')
 planned=batch['planned_cells'];expected={cell_id(*cell) for cell in itertools.product(UNITS,ARMS,CACHES,REPETITIONS)}
 require(len(planned)==32 and set(planned)==expected,'complete fixed final32 plan required')
 require(batch['enabled_cells']==planned,'enabled order must equal the frozen current plan')
 require(batch.get('original_plan_binding',{}).get('sha256')==ORIGINAL_PLAN_SHA,'original192-cell plan provenance missing')
 require(batch.get('removed_old_units')==160 and batch.get('unrecruited_original_final_families')==8,'removed factors and unrecruited families must remain explicit')
 require(batch.get('retained_claims')==['A_vs_B_native_semantic_context']and batch.get('reuse_admitted')is False and batch.get('publication_comparison_admitted')is False,'unsupported mechanism claims')
 for unit,meta in batch['units'].items():
  require(meta.get('split')=='final'and meta.get('family_id')==dict(zip(UNITS,FAMILIES))[unit]and sha_ok(meta.get('manifest_sha256'))and set(meta.get('arms',{}))==set(ARMS),'final unit/source identity differs')
  for arm,fields in meta['arms'].items():
   require(all(sha_ok(fields.get(k))for k in ('request_binding_sha256','context_binding_sha256','profile_sha256')),'per-arm source context/profile not frozen')
 for rel in ('private_root','queue_root'):
  p=Path(batch[rel]);require(p.is_absolute()and p.resolve()==p,'canonical batch root required')
 p,q=Path(batch['private_root']),Path(batch['queue_root']);require(not p.is_relative_to(q)and not q.is_relative_to(p),'private and public roots overlap')
 require(all(sha_ok(batch.get(k))for k in ('registry_sha256','package_sha256','amendment_source_sha256','native_harness_source_sha256')),'final source/profile authority missing')
 require(isinstance(batch.get('native_pin_files'),dict)and 0<len(batch['native_pin_files'])<=128,'current native/source file map required')
 for label,value in batch['native_pin_files'].items():
  p=Path(value);require(type(label)is str and label and p.is_absolute()and p.resolve()==p,'canonical native/source pin file required')
 require(set(batch.get('native_runtime_profile_binding',{}))=={'path','sha256'}and batch['native_runtime_profile_binding']['sha256']=='1bc2c65388bc5a79ae61e762653d336ae5401e7b0d592d265884d2ab166a8f84','approved native runtime profile required')
 require(type(batch.get('native_head'))is str and re.fullmatch('[0-9a-f]{40}',batch['native_head'])is not None,'exact final native commit missing')
 return batch
def checked(binding):
 require(set(binding)=={'path','sha256','cell_id','operator_admission_path','operator_admission_sha256'},'exact batch binding required')
 b=validate(read_bound(binding['path'],binding['sha256']));require(binding['cell_id']in b['enabled_cells'],'arm/cache/cell not implemented')
 old=read_bound(b['original_plan_binding']['path'],ORIGINAL_PLAN_SHA)
 selected=[u for u in old['units']if u['arm']in ARMS and u['cache']=='local_cold']
 require(len(old['units'])==192 and len(selected)==32 and b['planned_cells']==[cell_id(u['task_id'],u['arm'],u['cache'],u['repetition'])for u in selected],'original frozen order or denominator changed')
 freeze=read_bound(b['freeze_binding']['path'],b['freeze_binding']['sha256'])
 read_bound(freeze['resource_reservation_evidence']['path'],freeze['resource_reservation_evidence']['sha256'])
 policy=read_bound(b['analysis_policy_binding']['path'],b['analysis_policy_binding']['sha256'])
 require(freeze.get('schema')=='paper-ns-final-experiment-freeze/v1'and freeze.get('frozen')is True and freeze.get('first_final_attempt_started')is False,'actual pre-outcome final freeze required')
 for k in ('package_sha256','registry_sha256','planned_cells','native_head','native_harness_source_sha256','native_runtime_profile_binding'):
  require(freeze.get(k)==b[k],'final freeze differs: '+k)
 require(freeze.get('analysis_policy_sha256')==b['analysis_policy_binding']['sha256']and freeze.get('pilot_complete')is True and freeze.get('pilot_analysis_sha256')==b['pilot_analysis_binding']['sha256'],'complete pilot/analysis authority missing')
 require(freeze.get('freeze_sha256')==digest({k:v for k,v in freeze.items()if k!='freeze_sha256'}),'native canonical freeze self-hash differs')
 require(set(freeze.get('immutable_pins',{}))==set(b['native_pin_files'])and all(sha_ok(v)for v in freeze['immutable_pins'].values()),'native file pins differ')
 require(freeze.get('retained_executable_arms')==list(ARMS),'retained final native arms differ')
 analysis=read_bound(b['pilot_analysis_binding']['path'],b['pilot_analysis_binding']['sha256'])
 require(analysis.get('complete')is True and analysis.get('terminal_cells')==24 and analysis.get('planned_cells')==24,'complete retained developmental pilot required')
 require(policy.get('schema')=='ns028-final-AB-analysis-policy/v1'and policy.get('frozen_before_final_outcomes')is True and policy.get('independent_family_count')==8 and policy.get('nested_repetitions')==list(REPETITIONS)and policy.get('missing_cost_is_zero')is False,'explicit eight-family analysis policy required')
 h=read_bound(freeze['native_harness_execution']['path'],freeze['native_harness_execution']['sha256'])
 require(h.get('schema')=='ns028-root-native-harness-execution/v1'and h.get('executed')is True and h.get('fixture')is False and h.get('source_sha256')==b['native_harness_source_sha256'],'actual qualified native harness evidence required')
 require(all(h.get('checks',{}).get(k)is True for k in ('native_import','admit_final_attempt','missing_freeze_refused','stale_freeze_refused','current_source_profile','consumed_replay_refused')),'native harness checks incomplete')
 a=read_bound(binding['operator_admission_path'],binding['operator_admission_sha256'])
 require(a.get('schema')=='ns-final-AB-operator-admission/v1'and a.get('approved')is True and a.get('scope')=='heldout_AB_cold_final_only'and a.get('batch_sha256')==binding['sha256']and a.get('package_sha256')==b['package_sha256'],'separate reviewed final authority required')
 require(all(type(a.get(k))is int and a[k]==32 for k in ('paid_calls_authorized','scorer_calls_authorized'))and a.get('candidate_review_required')is True and a.get('final_admitted')is True,'final operator scope differs')
 require(a.get('freeze_sha256')==b['freeze_binding']['sha256']and a.get('analysis_policy_sha256')==b['analysis_policy_binding']['sha256'],'operator final freeze differs')
 require(sha_ok(a.get('independent_source_review_sha256'))and sha_ok(a.get('qualification_sha256')),'actual review and qualification bindings required')
 return b
def prepare_cell(binding,private,queue,unit,profile_sha,registry_sha,arm='A',repetition=104729):
 b=checked(binding);require(unit in UNITS and arm in ARMS and type(repetition)is int and repetition in REPETITIONS,'arm/repetition not implemented')
 cid=cell_id(unit,arm,'local_cold',repetition);require(binding['cell_id']==cid,'cell/unit mismatch')
 require(Path(private)==Path(b['private_root'])/cid and Path(queue)==Path(b['queue_root'])/cid,'child paths must be derived from exact cell')
 require(profile_sha==b['units'][unit]['arms'][arm]['profile_sha256']and registry_sha==b['registry_sha256'],'batch profile/registry drift')
 base=Path(b['private_root']);require(base.is_dir()and base.resolve()==base and base.stat().st_mode&0o077==0,'private root must be prepared by operator')
 reservation=base/('prepared-'+cid+'.json')
 fd=os.open(reservation,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 try:
  with os.fdopen(fd,'wb',closefd=False)as f:f.write(canon({'batch':binding,'unit':unit,'arm':arm,'repetition':repetition,'cell_id':cid,'provider_executed':False,'preparation_consumed':True}));f.flush();os.fsync(f.fileno())
 finally:os.close(fd)
 fd=os.open(base,os.O_RDONLY|os.O_DIRECTORY)
 try:os.fsync(fd)
 finally:os.close(fd)
 return b

from contextlib import contextmanager
@contextmanager
def phase_lock(binding):
 """One proposal or cold-scoring phase at a time across all32 batch cells."""
 import fcntl
 b=checked(binding);root=Path(b['private_root']);require(root.is_dir()and root.resolve()==root and root.stat().st_mode&0o077==0,'private batch root changed')
 fd=os.open(root/'active_phase.lock',os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
 try:
  fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB);yield
 finally:os.close(fd)

def require_provider_order(binding):
 """Caller holds phase_lock. Uncertain previous cells block new effects."""
 b=checked(binding);cell=binding['cell_id'];index=b['enabled_cells'].index(cell)
 for previous in b['enabled_cells'][:index]:
  private=Path(b['private_root'])/previous
  if(private/'disposition.json').exists():
   # The disposition and original signatures are checked against this grant's offer.
   import pilot_client as PC
   grant=json.loads(PC.read(private/'grant.json'));request=json.loads(PC.read(private/'expected_request.json'))
   require(PC.sha(PC.read(private/'grant.json'))==request['grant_sha256']and grant['batch_binding']['sha256']==binding['sha256']and grant['batch_binding']['cell_id']==previous,'previous grant changed')
   queue=Path(b['queue_root'])/previous;require(Path(grant['queue'])==queue,'previous queue differs')
   offer=json.loads(PC.read(queue/'offer.json'));require(offer['request']==request,'previous offered request differs')
   require(PC.sha(PC.read(private/'public.der'))==offer['public_key_sha256'],'previous private/public verifier differs')
   signed=json.loads(PC.read(private/'disposition.json'));name=signed['receipt'].get('original_filename');require(name in('result.json','proposal_result.json'),'unknown original filename')
   expected={**request,'profile':grant['profile'],'source_sha256':grant['source_sha256'],'manifest_sha256':grant['manifest_sha256']}
   _,d=PC.verify_disposition(offer,signed,PC.read(private/name),expected)
   reservation=json.loads(PC.read(private/'disposition_reservation.json'));require(reservation.get('binding')==d['binding']and reservation.get('new_provider_calls')==0 and reservation.get('new_scorer_calls')==0,'previous disposition reservation differs')
   require(d['binding']['cell_id']==previous and d['binding']['batch_sha256']==binding['sha256'],'previous disposition cell differs')
   require(not(private/'score_reservation.json').exists()or d['classification']=='known_scorer_failure','unexpected score reservation after disposition')
   continue
  p=Path(b['private_root'])/previous/'result.json';require(p.is_file()and p.resolve()==p,'previous scheduled pilot cell not terminal')
  fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW)
  try:
   info=os.fstat(fd);require(stat.S_ISREG(info.st_mode)and info.st_size<=1048576,'previous result bound')
   with os.fdopen(fd,'rb',closefd=False)as f:body=json.loads(f.read(1048577))['receipt']
  finally:os.close(fd)
  require(body.get('cell_id')==previous and body.get('batch_sha256')==binding['sha256']and body.get('status')=='completed'and body.get('error')is None and body.get('provider_termination',{}).get('termination_proven')is True,'previous unknown/unfinished effect requires operator reconciliation before advancing')
