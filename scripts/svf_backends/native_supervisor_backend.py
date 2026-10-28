#!/usr/bin/env python3
"""SVF-044 fixture: real supervisor SDK only. No datasets WorkflowCoordinator and no simulated completion."""
from __future__ import annotations
import hashlib,json,os,sys,threading,uuid
from pathlib import Path
MODE='svf-goal-worker-v1'
FIXTURE_SCOPE='svf-agent-supervisor-552'
SUBMIT='WorkflowCoordinator.submit_task'
ROOT=Path(__file__).resolve().parents[2]
RUNTIME=ROOT/'data/agent_supervisor/swissknife_visual_functional/backends/supervisor-fixtures'
RELATIVE_RUNTIME='data/agent_supervisor/swissknife_visual_functional/backends/supervisor-fixtures'
PYTHON=ROOT/'external/ipfs_datasets/.venv/bin/python'
WORKER=ROOT/'scripts/svf_backends/fixed_supervisor_worker.py'
VALIDATOR=ROOT/'scripts/svf_backends/fixed_supervisor_output_validator.py'
SOURCE_PATHS=[
 'scripts/svf_backends/native_supervisor_backend.py','scripts/svf_backends/native_accelerate_service.py',
 'swissknife/scripts/ipfs-accelerate-native-forwarder.cjs','swissknife/scripts/start-ipfs-accelerate-mcp-compat.cjs',
 'external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/task_sources/intent_repository.py',
 'external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/task_sources/database_task_source.py',
 'external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/verification/process_runner.py',
 'external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/runtime/resource_scheduler.py',
 'scripts/svf_backends/fixed_supervisor_worker.py','scripts/svf_backends/fixed_supervisor_output_validator.py']
SDK_CLASSES=['ipfs_accelerate_py.agent_supervisor.task_sources.intent_repository.IntentRepository','ipfs_accelerate_py.agent_supervisor.task_sources.database_task_source.DatabaseTaskSource','ipfs_accelerate_py.agent_supervisor.verification.process_runner.VerificationProcessRunner']
CREATE_KEYS={'fixture_mode','fixture_scope','action','fixture','dry_run','correlation_id'}
MUTATE_KEYS={'fixture_mode','fixture_scope','action','run_id','task_key','dry_run','correlation_id'}
READ_KEYS={'fixture_mode','fixture_scope','run_id','task_key','correlation_id'}
FIXTURES={'dependency-output-v1','timeout-recovery-v1','cancel-recovery-v1'}
LOCK=threading.RLock()
RUNS={}

def sha_bytes(data):return hashlib.sha256(data).hexdigest()
def sha_file(path):return sha_bytes(Path(path).read_bytes())
def reject(message):
    raise ValueError(message)
def load_sdk():
    root=str(ROOT/'external/ipfs_accelerate')
    if root not in sys.path:sys.path.insert(0,root)
    from ipfs_accelerate_py.agent_supervisor.task_sources.intent_repository import IntentRepository
    from ipfs_accelerate_py.agent_supervisor.task_sources.database_task_source import DatabaseTaskSource
    from ipfs_accelerate_py.agent_supervisor.verification.process_runner import VerificationCommand,VerificationProcessRunner,VerificationCancellation,build_closed_sandbox,build_hermetic_environment
    return IntentRepository,DatabaseTaskSource,VerificationCommand,VerificationProcessRunner,VerificationCancellation,build_closed_sandbox,build_hermetic_environment
def provenance(service):
    pins={}
    for relative in SOURCE_PATHS:
        path=service.root/relative
        if not path.is_file() or path.is_symlink():reject('supervisor source pin missing')
        pins[relative]=sha_file(path)
    return {'schema':'swissknife.native-supervisor-execution.v1','owner':'ipfs_accelerate_py','simulated':False,'cache_fallback':False,'source_sha256':pins,'sdk_classes':list(SDK_CLASSES)}
def envelope(service,tool,payload):
    proof=provenance(service)
    body={**payload,'success':True,'fixture_mode':MODE,'native_provenance':proof}
    return {'isError':False,'content':[{'type':'json','json':body}],'receipt':{'owner':'ipfs_accelerate_py','tool':tool,'status':'ok','native_provenance':proof}}
def failure(service,payload):
    proof=provenance(service)
    body={**payload,'fixture_mode':MODE,'native_provenance':proof}
    return {'isError':True,'content':[{'type':'json','json':body}]}
def check_common(args,allowed):
    if type(args) is not dict:reject('Tool arguments must be an object')
    if set(args)-allowed:reject('Unsupported supervisor fixture arguments')
    if args.get('fixture_mode')!=MODE:reject('Unsupported supervisor fixture mode')
    if 'fixture_scope' in args and (type(args['fixture_scope']) is not str or args['fixture_scope']!=FIXTURE_SCOPE):reject('Unsupported supervisor fixture scope')
    if 'dry_run' in args and args['dry_run'] is not False:reject('Preview is not a supervisor fixture execution')
    if 'correlation_id' in args and (type(args['correlation_id']) is not str or not 0<len(args['correlation_id'])<=256):reject('Invalid correlation ID')
def canonical_uuid(value,label):
    if type(value) is not str or str(uuid.UUID(value))!=value:reject('Invalid '+label)
    return value
def private_dir(path,*,exist_ok=True):
    path=Path(path)
    if not path.is_absolute() or not path.is_relative_to(RUNTIME) or path.is_symlink() or path.resolve()!=path:
        reject('symlink or foreign supervisor path refused')
    path.mkdir(mode=0o700,exist_ok=exist_ok)
    if path.is_symlink() or not path.is_dir() or path.resolve()!=path:reject('symlink supervisor path refused')
    os.chmod(path,0o700)
    return path
def database_argument(run_id):
    relative=RELATIVE_RUNTIME+'/'+run_id+'/control.duckdb'
    if Path.cwd().resolve()==ROOT.resolve():return relative
    return str((ROOT/relative).resolve())
def absolute_database(run_id):return str((RUNTIME.resolve()/run_id/'control.duckdb'))
def fixed_argv(run_id,stage,challenge,*,validator=False,mode='normal'):
    name=VALIDATOR if validator else WORKER
    argv=[str(PYTHON),'-I','-B',str(name),'--runtime-root',str(RUNTIME),'--run-id',run_id,'--stage',stage,'--challenge',challenge]
    if not validator:argv+=['--mode',mode]
    return argv
def open_sdk(run_id):
    Intent,Database,Command,Runner,Cancellation,box,environment=load_sdk()
    repo=Intent(database_argument(run_id),owner_id='svf-goal-worker',session_id=run_id,install_schema=True)
    source=Database(database_argument(run_id),intent=repo,owner_id='svf-goal-worker')
    return repo,source,Command,Runner,Cancellation,box,environment
def task_cids(page):
    found=[]
    for item in getattr(page,'tasks',()) or ():
        cid=getattr(item,'task_cid',None)
        if cid is None and isinstance(item,dict):cid=item.get('task_cid')
        if cid:found.append(cid)
    return found
def persist(state):
    path=Path(state['run_dir'])/'fixture-state.json'
    blob={key:value for key,value in state.items() if key!='live_cancel'}
    temporary=path.with_suffix('.tmp')
    temporary.write_text(json.dumps(blob,sort_keys=True)+'\n')
    os.chmod(temporary,0o600);os.replace(temporary,path)
def remember(state):
    RUNS[state['run_id']]=state;persist(state);return state
def load_run(run_id):
    if run_id in RUNS:return RUNS[run_id]
    path=RUNTIME/run_id/'fixture-state.json'
    if not path.is_file() or path.is_symlink():reject('Unknown supervisor run')
    state=json.loads(path.read_text());RUNS[run_id]=state;return state
def write_artifact(run_dir,result):
    run=Path(run_dir)
    if run.parent!=RUNTIME or not run.is_dir() or run.is_symlink() or run.resolve()!=run:
        reject('foreign or missing supervisor run refused')
    canonical_uuid(run.name,'run')
    private_dir(RUNTIME);private_dir(run)
    attempts=private_dir(run/'attempts')
    folder=private_dir(attempts/str(uuid.uuid4()),exist_ok=False)
    path=folder/'result.json'
    raw=json.dumps(result.to_dict(),sort_keys=True).encode()
    fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'wb') as out:out.write(raw);out.flush();os.fsync(out.fileno())
    return {'path':str(path.resolve()),'sha256':sha_bytes(raw)}
def run_command(runner,command_type,box,environment,argv,timeout,cancellation,run_id):
    command=command_type(argv=argv,cwd=str(ROOT),environment=environment,timeout_seconds=timeout,sandbox=box,max_stdout_bytes=4096,max_stderr_bytes=4096,lane_id='svf-fixture-'+run_id,resource_class='cpu-validation',stage='validation',metadata={'run_id':run_id},stdin=None)
    return runner.run(command,cancellation=cancellation)
def create(service,args):
    check_common(args,CREATE_KEYS)
    if args.get('action')!='create':reject('Unsupported supervisor action')
    fixture=args.get('fixture')
    if fixture not in FIXTURES:reject('Unsupported supervisor fixture')
    private_dir(RUNTIME)
    for ancestor in [RUNTIME,*RUNTIME.parents]:
        if ancestor==ROOT:break
        if ancestor.is_symlink():reject('symlink supervisor runtime refused')
    run_id=str(uuid.uuid4());challenge=uuid.uuid4().hex
    run=RUNTIME/run_id
    if run.exists() or run.is_symlink():reject('supervisor run collision')
    private_dir(run)
    repo,source,*_=open_sdk(run_id)
    ids={name:str(uuid.uuid4()) for name in ('objective','root','child','plan','a','b')}
    repo.upsert_objective(objective_id=ids['objective'],objective_alias='SVF-044-'+run_id,title='Controlled actual SDK worker qualification',body={'fixture':fixture})
    repo.upsert_goal(goal_cid=ids['root'],goal_alias='root-'+run_id,title='Validated fixed worker output',objective_id=ids['objective'])
    repo.upsert_goal(goal_cid=ids['child'],goal_alias='child-'+run_id,title='Dependent actual worker output',objective_id=ids['objective'],parent_goal_cid=ids['root'])
    repo.link_goal_edge(parent_goal_cid=ids['root'],child_goal_cid=ids['child'],edge_kind='subgoal')
    repo.upsert_plan(plan_cid=ids['plan'],goal_cid=ids['root'],plan_alias='plan-'+run_id,status='active')
    for stage in ('a','b'):
        repo.upsert_task(task_cid=ids[stage],task_alias=stage+'-'+run_id,goal_cid=ids['root'] if stage=='a' else ids['child'],plan_cid=ids['plan'],objective_id=ids['objective'],ordinal=0 if stage=='a' else 1,status='ready',dependencies=[] if stage=='a' else [ids['a']],outputs=[{'path':stage+'.json','effect':'create'}],acceptance=[{'criterion':'Exact original output passed independent fixed validator','evidence_kind':'validation','evidence_policy':{'evidence_kind':'validation'}}],validations=[fixed_argv(run_id,stage,challenge,validator=True)])
    ready=task_cids(source.ready_tasks())
    if ids['a'] not in ready or ids['b'] in ready:reject('initial dependency readiness differs')
    state=remember({'run_id':run_id,'challenge':challenge,'fixture':fixture,'run_dir':str(run.resolve()),'database_path':absolute_database(run_id),'objective_id':ids['objective'],'root_goal_cid':ids['root'],'child_goal_cid':ids['child'],'task_ids':{'a':ids['a'],'b':ids['b']},'attempts':{'a':0,'b':0},'failure_consumed':False,'execution':{}})
    return envelope(service,SUBMIT,{'run_id':run_id,'challenge':challenge,'database_path':state['database_path'],'objective_id':ids['objective'],'root_goal_cid':ids['root'],'child_goal_cid':ids['child'],'task_ids':{'a':ids['a'],'b':ids['b']}})
def cached_success(service,state,stage):
    saved=state.get('execution',{}).get(stage)
    if not saved:reject('completed task has no immutable execution record')
    repo,source,*_=open_sdk(state['run_id'])
    task_cids(source.ready_tasks())
    current=repo.get_task(state['task_ids'][stage])
    output=Path(state['run_dir'])/(stage+'.json')
    return envelope(service,SUBMIT,{'run_id':state['run_id'],'challenge':state['challenge'],'task_key':stage,'task_id':state['task_ids'][stage],'status':current['status'],'output_sha256':sha_file(output),'execution':saved})
def execute_stage(service,state,stage):
    with LOCK:
        repo,source,Command,Runner,Cancellation,box,environment=open_sdk(state['run_id'])
        cid=state['task_ids'][stage]
        current=repo.get_task(cid)
        if current is None:reject('Unknown supervisor task')
        if current['status']=='completed':return cached_success(service,state,stage)
        ready=set(task_cids(source.ready_tasks()))
        if cid not in ready and state['attempts'].get(stage,0)==0:
            reject('task is not ready')
        mode='normal'
        if not state.get('failure_consumed'):
            if state['fixture']=='timeout-recovery-v1':mode='timeout'
            elif state['fixture']=='cancel-recovery-v1':mode='cancel'
        if mode!='normal':state['failure_consumed']=True
        state['attempts'][stage]=state['attempts'].get(stage,0)+1
        remember(state)
        repo.record_attempt(task_cid=cid,status='started',owner_session_id=state['run_id'])
        runner=Runner(require_resource_lease=True)
        sandbox=box(source_root=str(ROOT),artifact_root=str(RUNTIME.resolve()))
        env=environment(path='/usr/bin:/bin')
        cancellation=Cancellation() if mode=='cancel' else None
        if cancellation is not None:state['live_cancel']=cancellation
        argv=fixed_argv(state['run_id'],stage,state['challenge'],mode=mode)
        timeout=0.1 if mode=='timeout' else 3
    try:
        produced=run_command(runner,Command,sandbox,env,argv,timeout,cancellation,state['run_id'])
    finally:
        with LOCK:state.pop('live_cancel',None)
    with LOCK:
        producer_ref=write_artifact(state['run_dir'],produced)
    if not produced.ok or not produced.publication_allowed:
        code='supervisor_timeout' if produced.timed_out else 'supervisor_cancelled' if produced.cancelled else 'supervisor_failed'
        remember(state)
        return failure(service,{'error':{'code':code},'run_id':state['run_id'],'task_key':stage,'task_id':cid,'execution':{'producer':producer_ref}})
    validated=run_command(runner,Command,sandbox,env,fixed_argv(state['run_id'],stage,state['challenge'],validator=True),3,None,state['run_id'])
    validator_ref=write_artifact(state['run_dir'],validated)
    if not validated.ok or not validated.publication_allowed:reject('protected output validator failed')
    output=Path(state['run_dir'])/(stage+'.json')
    if not output.is_file() or output.is_symlink():reject('fixed output missing')
    digest='sha256:'+sha_file(output)
    repo.record_validation_result(task_cid=cid,outcome='passed',evidence_digest=digest,argv=fixed_argv(state['run_id'],stage,state['challenge'],validator=True),attempt_id=str(uuid.uuid4()),body={'output_sha256':digest})
    fresh=repo.get_task(cid)
    source.compare_and_set_status(task_cid_or_alias=cid,expected_revision=int(fresh['revision']),status='completed',receipt={'validation':'actual fixed validator passed'},evidence_digests=[digest])
    task_cids(source.ready_tasks())
    state.setdefault('execution',{})[stage]={'producer':producer_ref,'validator':validator_ref}
    remember(state)
    done=repo.get_task(cid)
    return envelope(service,SUBMIT,{'run_id':state['run_id'],'challenge':state['challenge'],'task_key':stage,'task_id':cid,'status':done['status'],'output_sha256':digest.split(':',1)[1],'execution':state['execution'][stage]})
def mutate(service,args):
    check_common(args,MUTATE_KEYS)
    action=args.get('action');run_id=canonical_uuid(args.get('run_id'),'run');stage=args.get('task_key')
    if stage not in {'a','b'}:reject('Unsupported task key')
    state=load_run(run_id)
    if action=='cancel':
        live=state.get('live_cancel')
        if live is None:reject('No cancellable supervisor child')
        live.cancel(reason='cancelled')
        return envelope(service,SUBMIT,{'run_id':run_id,'task_key':stage,'task_id':state['task_ids'][stage],'status':'cancel_requested'})
    if action not in {'dispatch','retry'}:reject('Unsupported supervisor action')
    return execute_stage(service,state,stage)
def read_task(service,tool,args):
    check_common(args,READ_KEYS)
    run_id=canonical_uuid(args.get('run_id'),'run');stage=args.get('task_key')
    if stage not in {'a','b'}:reject('Unsupported task key')
    state=load_run(run_id)
    repo,source,*_=open_sdk(run_id)
    task_cids(source.ready_tasks())
    current=repo.get_task(state['task_ids'][stage])
    if current is None:reject('Unknown supervisor task')
    payload={'run_id':run_id,'task_key':stage,'task_id':state['task_ids'][stage],'status':current['status']}
    output=Path(state['run_dir'])/(stage+'.json')
    if current['status']=='completed' and output.is_file():payload['output_sha256']=sha_file(output)
    return envelope(service,tool,payload)
def supervise(service,tool,args):
    if tool=='get_task':
        with LOCK:return read_task(service,tool,args)
    if tool!=SUBMIT:reject('Fixture mode is only valid for the supervisor compatibility alias')
    if type(args) is dict and args.get('action')=='cancel':return mutate(service,args)
    if type(args) is dict and args.get('action')=='create':
        with LOCK:return create(service,args)
    return mutate(service,args)
