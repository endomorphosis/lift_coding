#!/usr/bin/env python3
"""Protected foundation gate: independent DB, bytes and kernel process evidence.

--sdk-self-test executes only tiny fixed offline children in a fresh owned RAM DB.
--verify requires the separately pinned ownership helper and real MCP fixture API.
No simulated SDK/WorkflowCoordinator, injected Popen, provider or browser calls.
"""
from __future__ import annotations
import argparse,ast,datetime,hashlib,importlib.util,inspect,json,marshal,os,re,stat,subprocess,sys,threading,time,urllib.request,uuid
from pathlib import Path
SDK_ROOT=Path(os.environ.get('SVF_FOUNDATION_REPOSITORY_ROOT',str(Path(__file__).resolve().parents[2]))).resolve()
HERE=Path(__file__).resolve().parent
MODE='svf-goal-worker-v1'
ALIAS='WorkflowCoordinator.submit_task'
SDK_PATHS={
'intent':'external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/task_sources/intent_repository.py',
'database':'external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/task_sources/database_task_source.py',
'runner':'external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/verification/process_runner.py'}
IMPLEMENTATION_PATHS=['scripts/svf_backends/native_supervisor_backend.py','scripts/svf_backends/native_accelerate_service.py','swissknife/scripts/ipfs-accelerate-native-forwarder.cjs','swissknife/scripts/start-ipfs-accelerate-mcp-compat.cjs']

CPU_CORE_AST_SHA256={'inference_arguments': 'ee6f77e9c56911fb3ba37febdb83c0906670775f2d8f2a287a6817f29dd12ba1', 'safe_runtime': '91d67857c21e8455bd52f0e42467ddf5f3758248e6c7b997b70072c3c6d46040', 'WarmInferenceWorker': '77e0ec35602ce9b18c378ac39d2c06dbda2edfb30f49cc4d31b547a53e7899d7'}
CPU_CALL_SUFFIX_AST_SHA256=['9b8898817c073df1296ed0c368ffc58634db8a9ec92d93cdf95df99d3ae9c175', '753b139ba81fa4f280be5eb2d57c9eb77a51fa3f3d8eead6d574c5193504d87c', '9f4a9f93c7a338b298c3faf6e893e3e9567fe88815d7ee3f4de7416c73fbe21e', '37b172082c93bba369f3b70b62bccea7ad62a096b10a83c6231b852108e651af', '19f4988f0bdba34471d819827552e27e78e6049d6b8dde0cc121935bed69faed', 'e4d6aaec303f648723e3cf3b15d9184dbbee0c327e5f03d6e11ab41bece386ad', '70cc2ca88411e11d03731938125cc3ceb5853fe821f5830819fb0763f7b5d988', 'fef3282676c07a32f83417d35a61adb9a972d4b57d4546a0b9d3aba3885cc2a1', '90b8d93d89cb89a28e3be88d23cca92bdd07415e07af56102b45bb90aabf194c', '0b0504e9e8c49c0dc4045de124b0bb31f7f96d67d92f7a3392095f0a336a2a53', '96b1dc140fcc71d727e4e2f14769521fd8939bcf59850304b6e54789225af25f', '0117a8e6078e7ea9a46c62338f56de97159d94a6750fc1c0682b1cecb3b49f89', 'b980832f4a637b9e8e2415e96b1ffdee7de14f98405898642c8f12f2d3be01a4', '83d38efccaea24eb03492381ae781956da196e58b85b1729d596a3d9fe6b3953', 'e1a47195ac9273405d7c33dfd577e5e66a910837774e0b2fd22093eac8331c4a', 'a7c6c73784a7e328983d8fcc44046e02b108734a5bf79f67b7f055655daa1866', '923cf8e687a819b5c80c08b8e5e3f84a40d2ad3bc8dc93fea611feeda68dd4fb', '7b1d642d8354b03513d85ddd38bf4e4911c5b147b5b68f50fd12c2072903af3e']

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def need(condition,message):
    if not condition:raise ValueError(message)
def save(path,value):
    path=Path(path);need(not path.exists() and not path.is_symlink(),'immutable proof collision');path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'w') as out:json.dump(value,out,sort_keys=True,indent=2);out.flush();os.fsync(out.fileno())
def load_module(path,name):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module);return module

def sdk(root=SDK_ROOT):
    sys.path.insert(0,str(root/'external/ipfs_accelerate'))
    from ipfs_accelerate_py.agent_supervisor.task_sources.intent_repository import IntentRepository
    from ipfs_accelerate_py.agent_supervisor.task_sources.database_task_source import DatabaseTaskSource
    from ipfs_accelerate_py.agent_supervisor.verification.process_runner import VerificationCommand,VerificationProcessRunner,VerificationCancellation,build_closed_sandbox,build_hermetic_environment
    import ipfs_accelerate_py.agent_supervisor.task_sources.intent_repository as intent
    import ipfs_accelerate_py.agent_supervisor.task_sources.database_task_source as database
    import ipfs_accelerate_py.agent_supervisor.verification.process_runner as runner
    for key,module in [('intent',intent),('database',database),('runner',runner)]:need(Path(module.__file__).resolve()==root/SDK_PATHS[key],'foreign SDK import')
    return IntentRepository,DatabaseTaskSource,VerificationCommand,VerificationProcessRunner,VerificationCancellation,build_closed_sandbox,build_hermetic_environment


def process(pid):
    proc=Path('/proc')/str(pid);fields=(proc/'stat').read_text().rsplit(')',1)[1].split()
    need(fields[0]!='Z','dead process')
    return {'pid':pid,'start_ticks':fields[19],'parent_pid':int(fields[1]),'uid':proc.stat().st_uid,'process_group_id':os.getpgid(pid),'argv':(proc/'cmdline').read_bytes().rstrip(b'\0').decode().split('\0'),'cgroups':(proc/'cgroup').read_text().splitlines()}


class KernelWitness:
    """Read-only observer; implementation JSON cannot create this evidence."""
    def __init__(self,parent_pid,worker_paths,run_id):
        self.parent=parent_pid;self.parent_birth=process(parent_pid)['start_ticks'];self.paths={str(p.resolve()):sha(p) for p in worker_paths};self.run_id=run_id;self.records={};self.done=threading.Event();self.thread=None
    def scan(self,pid,depth=0):
        if depth>4:return
        children=set()
        try:threads=list((Path('/proc')/str(pid)/'task').iterdir())
        except OSError:return
        if len(threads)>4096:return  # Refuse proof instead of unbounded process observation.
        for thread in threads:
            try:children.update((thread/'children').read_text().split())
            except OSError:continue
        if len(children)>4096:return
        for raw in children:
            try:
                value=process(int(raw));argv=value['argv']
                matching=[path for path in self.paths if path in argv]
                if matching and '--run-id' in argv and argv[argv.index('--run-id')+1]==self.run_id:
                    path=matching[0]
                    if sha(path)==self.paths[path] and value['uid']==os.getuid():self.records[(value['pid'],value['start_ticks'])]={**value,'protected_source':path,'source_sha256':self.paths[path]}
                self.scan(int(raw),depth+1)
            except (OSError,ValueError,IndexError):pass
    def __enter__(self):
        def monitor():
            while not self.done.is_set():
                try:
                    if process(self.parent)['start_ticks']!=self.parent_birth:return
                    self.scan(self.parent)
                except (OSError,ValueError):return
                self.done.wait(.01)
        self.thread=threading.Thread(target=monitor,daemon=True);self.thread.start();return self
    def __exit__(self,*_):self.scan(self.parent);self.done.set();self.thread.join(timeout=1)
    def rows(self):return list(self.records.values())


def fixed_argv(runtime,run_id,stage,challenge,*,validator=False,mode='normal'):
    name='fixed_supervisor_output_validator.py' if validator else 'fixed_supervisor_worker.py'
    argv=[str(SDK_ROOT/'external/ipfs_datasets/.venv/bin/python'),'-I','-B',str(HERE/name),'--runtime-root',str(runtime),'--run-id',run_id,'--stage',stage,'--challenge',challenge]
    if not validator:argv+=['--mode',mode]
    return argv



def executed_argv(argv,*,root=SDK_ROOT):
    """The SDK resolves only the registered Python executable for execve.

    Database definitions and SDK run-entry policy keep the literal venv alias.
    Result/kernel evidence must instead match its independently pinned binary.
    No script, flag, fixture path, stage, challenge or other argument is changed.
    """
    root=Path(root)
    need(root.is_absolute() and root.resolve()==root,'nonphysical executable registration root')
    alias=root/'external/ipfs_datasets/.venv/bin/python'
    need(type(argv) is list and argv and all(type(item) is str for item in argv)
         and argv[0]==str(alias),'fixed command does not name registered Python alias')
    registration=root/'config/swissknife_visual_functional_foundation_owners.json'
    info=registration.lstat()
    need(stat.S_ISREG(info.st_mode) and info.st_uid==os.getuid() and not info.st_mode&0o022
         and info.st_size<=524288 and registration.resolve()==registration,'unsafe executable registration')
    cfg=json.loads(registration.read_text())
    need(cfg.get('schema')=='swissknife.foundation-service-registration.v1'
         and cfg.get('status')=='REGISTERED' and cfg.get('root')==str(root),'foreign executable registration')
    entry=cfg.get('units',{}).get('swissknife-visual-functional-native-accelerate.service',{})
    pin=entry.get('binary_sha256','');registered=entry.get('argv')
    need(type(registered) is list and registered and registered[0]==str(alias) and type(pin) is str
         and re.fullmatch('[0-9a-f]{64}',pin) is not None,'registered Python alias/binary pin differs')
    executable=alias.resolve(strict=True);binary=executable.lstat()
    need(stat.S_ISREG(binary.st_mode) and not binary.st_mode&0o022 and binary.st_mode&0o111
         and 0<binary.st_size<=33554432,'unsafe registered executable binary')
    need(sha(executable)==pin and alias.resolve(strict=True)==executable,'registered executable binary changed')
    return [str(executable),*argv[1:]]


def sdk_self_test(output_root,*,root=SDK_ROOT):
    output_root=Path(output_root).resolve();need(str(output_root).startswith('/dev/shm/'),'SDK self-test must remain in RAM');output_root.mkdir(parents=True,exist_ok=True,mode=0o700);output_root.chmod(0o700)
    Intent,Database,Command,Runner,Cancellation,box,environment=sdk(root)
    run_id=str(uuid.uuid4());challenge=uuid.uuid4().hex;runtime=output_root/'runtime';runtime.mkdir(mode=0o700);run=runtime/run_id;run.mkdir(mode=0o700)
    db=run/'control.duckdb';repo=Intent(db,owner_id='svf-protected-gate',session_id=run_id);source=Database(intent=repo,owner_id='svf-protected-gate')
    ids={name:f'svf:{run_id}:{name}' for name in ('objective','root','child','plan','a','b')}
    repo.upsert_objective(objective_id=ids['objective'],objective_alias='SVF-044-'+run_id,title='Controlled actual SDK worker qualification')
    repo.upsert_goal(goal_cid=ids['root'],goal_alias='root-'+run_id,title='Validated fixed worker output',objective_id=ids['objective'])
    repo.upsert_goal(goal_cid=ids['child'],goal_alias='child-'+run_id,title='Dependent actual worker output',objective_id=ids['objective'],parent_goal_cid=ids['root'])
    repo.link_goal_edge(parent_goal_cid=ids['root'],child_goal_cid=ids['child'],edge_kind='subgoal')
    repo.upsert_plan(plan_cid=ids['plan'],goal_cid=ids['root'],plan_alias='plan-'+run_id,status='active')
    for stage in ('a','b'):
        repo.upsert_task(task_cid=ids[stage],task_alias=stage+'-'+run_id,goal_cid=ids['root'] if stage=='a' else ids['child'],plan_cid=ids['plan'],objective_id=ids['objective'],status='ready',dependencies=[] if stage=='a' else [ids['a']],outputs=[{'path':stage+'.json','effect':'create'}],acceptance=[{'criterion':'Exact original output passed independent fixed validator','evidence_kind':'validation'}],validations=[fixed_argv(runtime,run_id,stage,challenge,validator=True)])
    checks={};checks['actual_dependency_blocks_b']=[x['task_cid'] for x in repo.select_ready_tasks()]==[ids['a']]
    checks['database_source_same_ready']=[x.task_cid for x in source.ready_tasks().tasks]==[ids['a']]
    try:repo.cas_task_status(task_cid=ids['a'],expected_revision=repo.get_task(ids['a'])['revision'],new_status='completed',receipt={},evidence_digests=[])
    except Exception:checks['completion_without_validation_refused']=True
    else:checks['completion_without_validation_refused']=False
    runner=Runner(require_resource_lease=True);sandbox=box(source_root=HERE.parent.parent,artifact_root=runtime);env=environment(path='/usr/bin:/bin');results=[];witnesses=[]
    def execute(argv,timeout=3,cancel=None):
        command=Command(argv=argv,cwd=str(HERE.parent.parent),environment=env,timeout_seconds=timeout,sandbox=sandbox,max_stdout_bytes=4096,max_stderr_bytes=4096,lane_id='svf-protected-'+run_id,resource_class='cpu-validation',stage='validation',stdin=None)
        with KernelWitness(os.getpid(),[HERE/'fixed_supervisor_worker.py',HERE/'fixed_supervisor_output_validator.py'],run_id) as witness:result=runner.run(command,cancellation=cancel)
        rows=witness.rows()
        results.append(result.to_dict());return result,rows
    for stage in ('a','b'):
        repo.record_attempt(task_cid=ids[stage],status='started',owner_session_id=run_id)
        original,observed=execute(fixed_argv(runtime,run_id,stage,challenge));need(original.ok,'actual fixed producer did not pass: '+original.reason)
        need(any(row['pid']==original.pid for row in observed),'no independent kernel witness for actual producer');witnesses.extend(observed)
        validator,rows=execute(fixed_argv(runtime,run_id,stage,challenge,validator=True));need(validator.ok,'independent fixed validator failed');need(any(row['pid']==validator.pid for row in rows),'no independent validator kernel witness');witnesses.extend(rows)
        path=run/(stage+'.json');digest='sha256:'+sha(path);value=load_module(HERE/'fixed_supervisor_output_validator.py','independent_validator_'+stage).check(runtime,run_id,stage,challenge);need(digest=='sha256:'+value['output_sha256'],'independent read hash mismatch')
        repo.record_validation_result(task_cid=ids[stage],outcome='passed',evidence_digest=digest,argv=fixed_argv(runtime,run_id,stage,challenge,validator=True),attempt_id=str(uuid.uuid4()),body={'actual_producer_pid':original.pid,'actual_validator_pid':validator.pid,'output_sha256':sha(path)})
        snapshot=repo.get_task(ids[stage]);source.compare_and_set_status(ids[stage],int(snapshot['revision']),'completed',receipt={'validation':'actual fixed validator passed'},evidence_digests=[digest])
        checks['actual_'+stage+'_validated_completed']=repo.get_task(ids[stage])['status']=='completed'
        if stage=='a':checks['a_validation_unlocks_b']=[x['task_cid'] for x in repo.select_ready_tasks()]==[ids['b']]
    # Bounded timeout/cancel execute the same protected code, no output publication.
    for mode in ('timeout','cancel'):
        special=str(uuid.uuid4());(runtime/special).mkdir(mode=0o700);cancel=Cancellation() if mode=='cancel' else None;timer=threading.Timer(.15,cancel.cancel) if cancel is not None else None
        if timer:timer.start()
        command=Command(argv=fixed_argv(runtime,special,'a',challenge,mode=mode),cwd=str(HERE.parent.parent),environment=env,timeout_seconds=.1 if mode=='timeout' else 3,sandbox=sandbox,max_stdout_bytes=4096,max_stderr_bytes=4096,lane_id='svf-negative-'+special,resource_class='cpu-validation',stage='validation',stdin=None)
        result=runner.run(command,cancellation=cancel)
        if timer:timer.join(timeout=1)
        checks['actual_'+mode+'_not_publication']=not result.ok and not result.publication_allowed and not (runtime/special/'a.json').exists() and (result.timed_out if mode=='timeout' else result.cancelled);results.append(result.to_dict())
    reopened=Intent(db,owner_id='svf-independent-readback',install_schema=False)
    checks['actual_db_reopen_preserves_completed']=all(reopened.get_task(ids[k])['status']=='completed' for k in ('a','b'))
    checks['all_real_resource_leases']=all(r['lease_id'] and r['process_started'] for r in results)
    checks['all_sdk_processes_reaped']=all(not Path('/proc',str(r['pid'])).exists() for r in results if r['pid'])
    report={'schema':'swissknife.protected-supervisor-sdk-qualification.v1','run_id':run_id,'challenge':challenge,'database_path':str(db),'checks':checks,'qualified':all(checks.values()),'actual_sdk':True,'injected_sdk_or_process':False,'production_mcp_ready':False,'network_policy':'declared deny_all; not a kernel namespace','sdk_sources':{path:sha(root/path) for path in SDK_PATHS.values()},'protected_sources':{str(p):sha(p) for p in [HERE/'fixed_supervisor_worker.py',HERE/'fixed_supervisor_output_validator.py',Path(__file__)]},'process_results':results,'kernel_witnesses':witnesses,'work_complete':False,'completion_authority':False}
    save(output_root/'sdk-qualification.json',report);need(report['qualified'],'one or more actual SDK qualifications failed');return report


def assert_cpu_preserved(root):
    tree=ast.parse((root/'scripts/svf_backends/native_accelerate_service.py').read_text())
    def fingerprint(node):return hashlib.sha256(ast.dump(node,include_attributes=False).encode()).hexdigest()
    for name,wanted in CPU_CORE_AST_SHA256.items():
        need(any(isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name==name and fingerprint(n)==wanted for n in tree.body),'existing CPU core changed: '+name)
    parent=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='NativeAccelerate')
    call=next(n for n in parent.body if isinstance(n,ast.FunctionDef) and n.name=='call')
    need([fingerprint(n) for n in call.body[-len(CPU_CALL_SUFFIX_AST_SHA256):]]==CPU_CALL_SUFFIX_AST_SHA256,'existing CPU call body changed; add only an explicit fixture prefix')
    prefix=call.body[:-len(CPU_CALL_SUFFIX_AST_SHA256)]
    if prefix:
        expected_guard=ast.parse("tool == 'WorkflowCoordinator.submit_task' or (type(args) is dict and 'fixture_mode' in args)",mode='eval').body
        need(len(prefix)==1 and isinstance(prefix[0],ast.If) and ast.dump(prefix[0].test,include_attributes=False)==ast.dump(expected_guard,include_attributes=False) and not prefix[0].orelse,'fixture prefix can intercept ordinary CPU calls; use the exact explicit-mode guard')
    alias=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='ALIASES' for t in n.targets))
    need(ast.literal_eval(alias.value)=={'submit_task':'run_inference_job','get_task':'job_status','detect_hardware':'hardware_profile'},'existing ordinary CPU aliases changed')


def wait_catalog(url,seconds=15):
    deadline=time.monotonic()+seconds;last='not-ready'
    while time.monotonic()<deadline:
        request={'jsonrpc':'2.0','id':'svf-ready-'+uuid.uuid4().hex,'method':'tools/list','params':{}}
        try:
            req=urllib.request.Request(url,data=json.dumps(request).encode(),headers={'Content-Type':'application/json'},method='POST')
            with urllib.request.urlopen(req,timeout=max(.01,min(2,deadline-time.monotonic()))) as response:data=response.read(131073)
            need(len(data)<=131072,'catalog too large');value=json.loads(data)
            need(value.get('id')==request['id'],'readiness RPC identity differs')
            names={item['name'] for item in value.get('result',{}).get('tools',[])}
            if {ALIAS,'get_task','submit_task','run_inference_job','list_models'}<=names:return
            last='required-real-tools-not-advertised'
        except (OSError,ValueError,KeyError) as error:last=type(error).__name__
        remaining=deadline-time.monotonic()
        if remaining>0:time.sleep(min(1,remaining))
    raise RuntimeError('registered service not ready within15s: '+last)


def rpc_failure_context(name,args,value,payload):
    """Bounded observations of a failed owned RPC, never qualification evidence."""
    def text(item,limit):
        if type(item) is not str:return None
        item=re.sub(r'(?i)([a-z][a-z0-9+.-]*://)[^\s/@:]+:[^\s/@]+@',r'\1<redacted>@',item)
        item=re.sub(r'(?i)(\b(?:api[_-]?key|access[_-]?token|refresh[_-]?token|password|secret)\b\s*[=:]\s*)[^\s,;&]+',r'\1<redacted>',item)
        item=re.sub(r'(?i)(\bauthorization\s*[:=]\s*)(?:bearer\s+)?[^\s,;]+',r'\1<redacted>',item)
        return item.encode('utf8',errors='replace')[:limit].decode('utf8',errors='ignore')
    def error_fields(item,limit):
        result={'type':type(item).__name__}
        if type(item) is dict:
            code=item.get('code')
            if type(code) in {str,int}:result['code_text']=text(str(code),128)
            message=text(item.get('message'),limit)
            if message is not None:result['message']=message
        elif type(item) is str:result['message']=text(item,limit)
        return result
    result=value.get('result',{});content=result.get('content',[])
    first=content[0] if type(content) is list and content and type(content[0]) is dict else {}
    native=first.get('json',{});native=native if type(native) is dict else {}
    request_context={key:text(args[key],128) for key in ('fixture_mode','action','run_id','task_key','fixture') if type(args) is dict and type(args.get(key)) is str}
    limit=1024
    while True:
        summary={'schema':'swissknife.protected-supervisor-rpc-failure.v1',
                 'tool':text(name,128),'request_context':request_context,
                 'response_sha256':hashlib.sha256(payload).hexdigest(),'response_bytes':len(payload),
                 'jsonrpc_error':error_fields(value.get('error'),limit),
                 'mcp_is_error':bool(result.get('isError')),
                 'native_error':error_fields(native.get('error'),limit),
                 'work_complete':False,'completion_authority':False,
                 'scope':'Actual failed RPC summary only; messages may be truncated/redacted; no response salvage or acceptance'}
        if type(first.get('text')) is str:summary['mcp_text']=text(first['text'],limit)
        encoded=json.dumps(summary,sort_keys=True,separators=(',',':'),ensure_ascii=False)
        if len(encoded.encode())<=3500:return encoded
        if limit<=64:
            return json.dumps({'schema':summary['schema'],'response_sha256':summary['response_sha256'],
                               'response_bytes':len(payload),'diagnostic_fields_omitted':True,
                               'work_complete':False,'completion_authority':False},sort_keys=True,separators=(',',':'))
        limit//=2


def rpc(url,name,args,*,allow_error=False):
    request={'jsonrpc':'2.0','id':'svf-protected-'+uuid.uuid4().hex,'method':'tools/call','params':{'name':name,'arguments':args}}
    raw=json.dumps(request).encode();need(len(raw)<=8192,'bounded request required')
    req=urllib.request.Request(url,data=raw,headers={'Content-Type':'application/json'},method='POST')
    with urllib.request.urlopen(req,timeout=30) as response:payload=response.read(262145)
    need(len(payload)<=262144,'oversized MCP response');value=json.loads(payload);need(value.get('id')==request['id'] and value.get('jsonrpc')=='2.0','RPC identity mismatch')
    result=value.get('result',{});failed=bool(value.get('error') or result.get('isError'))
    if failed:
        message='real supervisor MCP operation failed'
        if not allow_error:message+=': '+rpc_failure_context(name,args,value,payload)
        need(allow_error,message);return None,{'request':request,'response':value}
    need(not allow_error,'expected refusal was accepted');content=result.get('content');need(type(content) is list and len(content)==1 and content[0].get('type')=='json','ambiguous MCP payload')
    return content[0]['json'],{'request':request,'response':value}


def check_native_payload(payload,receipt,tool,expected):
    need(type(payload) is dict and payload.get('success') is True and payload.get('fixture_mode')==MODE,'not a native supervisor fixture payload')
    proof=payload.get('native_provenance',{})
    need(proof.get('schema')=='swissknife.native-supervisor-execution.v1' and proof.get('owner')=='ipfs_accelerate_py' and proof.get('simulated') is False and proof.get('cache_fallback') is False,'native supervisor provenance missing')
    need(proof.get('sdk_classes')==['ipfs_accelerate_py.agent_supervisor.task_sources.intent_repository.IntentRepository','ipfs_accelerate_py.agent_supervisor.task_sources.database_task_source.DatabaseTaskSource','ipfs_accelerate_py.agent_supervisor.verification.process_runner.VerificationProcessRunner'],'wrong actual SDK classes')
    need(proof.get('source_sha256')==expected,'native source pins differ')
    need(receipt.get('owner')=='ipfs_accelerate_py' and receipt.get('tool')==tool and receipt.get('status')=='ok' and receipt.get('native_provenance')==proof,'native receipt/provenance join differs')


def sdk_artifact(item,run):
    need(type(item) is dict and set(item)=={'path','sha256'},'exact raw SDK artifact reference required')
    path=Path(item['path']);need(path.is_absolute() and path.resolve()==path and path.is_relative_to(run/'attempts'),'raw SDK artifact outside own immutable attempt')
    info=path.lstat();need(stat.S_ISREG(info.st_mode) and info.st_uid==os.getuid() and not info.st_mode&0o077 and 0<info.st_size<=65536,'unsafe raw SDK result')
    need(sha(path)==item['sha256'],'raw SDK result hash mismatch');return json.loads(path.read_text())


def check_execution(payload,run,runtime,run_id,stage,challenge,observed,*,outcome='completed',mode='normal'):
    execution=payload.get('execution',{});need(set(execution)=={'producer','validator'} if outcome=='completed' else set(execution)=={'producer'},'exact execution artifact set required')
    raw=sdk_artifact(execution['producer'],run);need(raw.get('schema')=='ipfs_accelerate_py/agent-supervisor/verification-process-runner@1' and raw.get('process_started') is True and type(raw.get('lease_id')) is str and raw['lease_id'].startswith('resource-lease:'),'actual leased SDK process result missing')
    need(raw.get('command_argv')==executed_argv(fixed_argv(runtime,run_id,stage,challenge,mode=mode)),'producer command differs from protected fixed argv')
    witnesses=[row for row in observed if row['pid']==raw.get('pid') and row['argv']==raw['command_argv'] and row['process_group_id']==raw.get('process_group_id')];need(witnesses,'producer SDK result lacks independent kernel PID/birth/argv witness')
    try:
        still=process(raw['pid']);need(not any(still['start_ticks']==row['start_ticks'] for row in witnesses),'owned SDK worker was not reaped')
    except (FileNotFoundError,ProcessLookupError):pass
    if outcome!='completed':
        need(raw.get('publication_allowed') is False and raw.get('ok') is False and raw.get('disposition')==outcome and raw.get('timed_out' if outcome=='timeout' else 'cancelled') is True,'timeout/cancel outcome was not fenced')
        need(not (run/(stage+'.json')).exists(),'failed attempt published output');return raw
    need(raw.get('ok') is True and raw.get('exit_code')==0 and raw.get('publication_allowed') is True and not raw.get('timed_out') and not raw.get('cancelled'),'producer did not finish normally')
    stdout=raw.get('stdout',{});text=stdout.get('preview','');data=text.encode();need(stdout.get('truncated') is False and stdout.get('byte_count')==len(data)==stdout.get('captured_byte_count') and stdout.get('digest')=='sha256:'+hashlib.sha256(data).hexdigest(),'producer raw stdout binding differs')
    emitted=json.loads(text);need(emitted.get('pid')==witnesses[0]['pid'] and emitted.get('start_ticks')==witnesses[0]['start_ticks'] and emitted.get('parent_pid')==witnesses[0]['parent_pid'] and emitted.get('producer_sha256')==witnesses[0]['source_sha256'],'producer stdout kernel/source identity differs')
    value=load_module(HERE/'fixed_supervisor_output_validator.py','independent_final_'+stage).check(runtime,run_id,stage,challenge)
    need(emitted.get('output_sha256')==value['output_sha256'] and emitted.get('output_path')==str(run/(stage+'.json')),'actual worker output differs')
    validated=sdk_artifact(execution['validator'],run);need(validated.get('command_argv')==executed_argv(fixed_argv(runtime,run_id,stage,challenge,validator=True)) and validated.get('ok') is True and validated.get('publication_allowed') is True and validated.get('exit_code')==0 and validated.get('lease_id'),'actual protected validator SDK result missing')
    need(any(row['pid']==validated.get('pid') and row['argv']==validated['command_argv'] for row in observed),'no independent kernel witness of validator')
    return raw


def protected_module(root,relative):
    registration=root/'config/swissknife_visual_functional_foundation_owners.json'
    need(registration.is_file() and registration.resolve()==registration,'protected registration missing; foundation is not admitted')
    info=registration.lstat();need(stat.S_ISREG(info.st_mode) and info.st_uid==os.getuid() and not info.st_mode&0o022 and info.st_size<=524288,'unsafe protected registration')
    cfg=json.loads(registration.read_text());need(cfg.get('schema')=='swissknife.foundation-service-registration.v1' and cfg.get('status')=='REGISTERED' and cfg.get('root')==str(root),'protected registration is not admitted')
    allowed={'scripts/svf_backends/foundation_service_ownership.py','scripts/svf_backends/foundation_native_entrypoint.py'}
    need(relative in allowed,'unknown protected module')
    for name in [*allowed,'scripts/svf_backends/validate_supervisor_foundation.py']:
        path=root/name;need(path.is_file() and path.resolve()==path,'protected source missing or symlink')
        st=path.lstat();need(st.st_uid==os.getuid() and not st.st_mode&0o022 and cfg.get('protected_sha256',{}).get(name)==sha(path),'protected module lacks independently registered hash')
    return load_module(root/relative,'protected_'+Path(relative).stem)


def sdk_observer_code_hashes(root,classes,paths,methods,expected):
    """Reproduce the pinned observer's import-time code hashes from source.

    marshal's reference records depend on whether the module compiler's code
    tree is still alive. The observer records hashes inside exec_module, while
    an ordinary import has already released that tree. Keep it alive here,
    and independently require the imported method's complete v0 serialization
    to equal the source-compiled method (v0 has no reference-sharing records).
    No SDK method is called and the process module registry is unchanged.
    """
    hashes={}
    for kind,cls in classes.items():
        path=root/paths[kind];raw=path.read_bytes()
        need(path.resolve()==path and hashlib.sha256(raw).hexdigest()==expected[paths[kind]],'SDK compiler source differs')
        namespace={'__name__':cls.__module__,'__package__':cls.__module__.rpartition('.')[0],'__file__':str(path)}
        compiled=compile(raw,str(path),'exec',dont_inherit=True)
        exec(compiled,namespace)
        fresh=namespace.get(kind)
        need(inspect.isclass(fresh) and fresh.__module__==cls.__module__,'SDK compiler class differs')
        for method in methods[kind]:
            original=inspect.unwrap(getattr(cls,method,None));candidate=inspect.unwrap(getattr(fresh,method,None))
            need(inspect.isfunction(original) and inspect.isfunction(candidate) and original.__module__==candidate.__module__==cls.__module__ and original.__code__.co_filename==candidate.__code__.co_filename==str(path),'SDK compiler method origin differs')
            need(marshal.dumps(original.__code__,0)==marshal.dumps(candidate.__code__,0),'SDK imported method differs from pinned source code')
            hashes[kind,method]=hashlib.sha256(marshal.dumps(candidate.__code__)).hexdigest()
        need(hashlib.sha256(path.read_bytes()).hexdigest()==expected[paths[kind]],'SDK compiler source changed')
    return hashes


def call_snapshot(root,native,expected,ownership):
    observer=protected_module(root,'scripts/svf_backends/foundation_native_entrypoint.py')
    descriptor=ownership.get('sdk_call_witness',{})
    need(descriptor.get('schema')=='swissknife.foundation-sdk-call-capture-ref.v1' and descriptor.get('family')=='accelerate-supervisor' and descriptor.get('invocation_id')==native['invocation_id'],'protected SDK capture descriptor missing or foreign')
    reference=descriptor.get('capture',{});capture_path=root/reference.get('path','')
    required_path=root/'data/agent_supervisor/swissknife_visual_functional/backends/foundation-call-witness/accelerate-supervisor'/native['invocation_id']/'capture.json'
    need(capture_path==required_path and capture_path.resolve()==capture_path and capture_path.is_file() and not capture_path.is_symlink(),'capture path escapes registered native invocation')
    info=capture_path.lstat();need(info.st_uid==os.getuid() and stat.S_ISREG(info.st_mode) and not info.st_mode&0o077 and info.st_size<=16384,'unsafe SDK capture record')
    capture_raw=capture_path.read_bytes();need(len(capture_raw)==reference.get('bytes') and hashlib.sha256(capture_raw).hexdigest()==reference.get('sha256'),'SDK capture reference hash differs')
    capture=json.loads(capture_raw);capture_id=capture.get('capture_id');need(type(capture_id) is str and str(uuid.UUID(capture_id))==capture_id and descriptor.get('capture_id')==capture_id and reference.get('capture_id')==capture_id,'capture identity differs')
    need(capture.get('schema')=='swissknife.foundation-sdk-call-capture.v1' and capture.get('family')=='accelerate-supervisor' and capture.get('invocation_id')==native['invocation_id'] and capture.get('task_id')=='SVF-044' and capture.get('native_process',{}).get('pid')==native['pid'] and capture.get('native_process',{}).get('start_ticks')==native['start_ticks'] and capture.get('expected_sources')==expected and capture.get('observational_only') is True and capture.get('completion_authority') is False,'capture native/task/source binding differs')
    issued=capture.get('issued_at');expires=capture.get('expires_at');need(type(issued) in (int,float) and type(expires) in (int,float) and issued<expires<=issued+300 and issued-5<=time.time()<expires and reference.get('expires_at')==expires,'SDK capture is expired or unbounded')
    source=descriptor.get('observer_source',{});need(source.get('path')=='scripts/svf_backends/foundation_native_entrypoint.py' and source.get('sha256')==sha(root/source['path']),'capture observer source differs')
    owner_path=Path(ownership['witness_path']);need(owner_path.resolve()==owner_path and owner_path.is_file() and sha(owner_path)==ownership['witness_sha256'],'owned service source witness differs');owner_record=json.loads(owner_path.read_text())
    need(capture.get('lease_id')==owner_record.get('lease_id') and capture.get('foreground_birth')==owner_record.get('foreground_birth'),'capture original leased foreground differs')
    snapshot=observer.read_snapshot(root,family='accelerate-supervisor',invocation_id=native['invocation_id'])
    need(snapshot.get('schema')=='swissknife.foundation-sdk-call-snapshot.v1' and snapshot.get('family')=='accelerate-supervisor' and snapshot.get('invocation_id')==native['invocation_id'] and snapshot.get('identity')=={'pid':native['pid'],'start_ticks':native['start_ticks']},'SDK snapshot belongs to another native process generation')
    captured=snapshot.get('capture',{});need(captured.get('value')==capture and all(captured.get('reference',{}).get(k)==reference.get(k) for k in ('path','sha256','bytes')) and snapshot.get('capture_faults')==[],'snapshot capture reference/faults differ')
    manifest=snapshot.get('observer',{});need(manifest.get('observer_sha256')==sha(root/'scripts/svf_backends/foundation_native_entrypoint.py') and manifest.get('authenticated_origin') is False and manifest.get('observational_only') is True,'protected observer source/observational scope differs')
    need(manifest.get('source_sha256')==expected,'observer did not load this actual service source generation')
    events=snapshot.get('events');need(type(events) is list and len(events)<=8192,'bounded actual SDK events missing')
    records={};sequence=[];classes=dict(zip(['IntentRepository','DatabaseTaskSource','VerificationProcessRunner'],[sdk(root)[0],sdk(root)[1],sdk(root)[3]]));paths={'IntentRepository':SDK_PATHS['intent'],'DatabaseTaskSource':SDK_PATHS['database'],'VerificationProcessRunner':SDK_PATHS['runner']}
    methods={kind:observer.TARGETS[cls.__module__][2][kind] for kind,cls in classes.items()}
    code_hashes=sdk_observer_code_hashes(root,classes,paths,methods,expected)
    for item in events:
        ref=item.get('reference',{});event=item.get('event',{});path=root/ref.get('path','')
        base=root/'data/agent_supervisor/swissknife_visual_functional/backends/foundation-call-witness/accelerate-supervisor'/native['invocation_id']/'events'
        need(path.resolve()==path and path.is_relative_to(base) and path.is_file() and not path.is_symlink(),'SDK event reference escapes native invocation')
        st=path.lstat();need(stat.S_ISREG(st.st_mode) and st.st_uid==os.getuid() and not st.st_mode&0o077 and st.st_size<=16384,'unsafe SDK event artifact')
        raw=path.read_bytes();need(len(raw)==ref.get('bytes') and hashlib.sha256(raw).hexdigest()==ref.get('sha256') and json.loads(raw)==event,'SDK event artifact hash/content differs')
        need(event.get('schema')=='swissknife.foundation-sdk-call-event.v1' and event.get('family')=='accelerate-supervisor' and event.get('invocation_id')==native['invocation_id'] and event.get('pid')==native['pid'] and event.get('start_ticks')==native['start_ticks'] and event.get('observational_only') is True and event.get('completion_authority') is False and event.get('capture_id')==capture_id and event.get('capture_sha256')==reference['sha256'],'SDK event native/capture identity differs')
        need(type(event.get('sequence')) is int and event['sequence']>0 and type(event.get('thread_id')) is int and event['thread_id']>0,'SDK event sequence/thread missing');sequence.append(event['sequence'])
        desc=event.get('sdk',{});kind=desc.get('class');method=desc.get('method');need(kind in classes and type(method) is str and desc.get('module')==classes[kind].__module__ and desc.get('source_path')==paths[kind] and desc.get('source_sha256')==expected[paths[kind]],'SDK event source/class differs')
        need((kind,method) in code_hashes and desc.get('code_sha256')==code_hashes[kind,method],'SDK event did not call pinned original method code')
        key=event.get('call_id');need(type(key) is str and str(uuid.UUID(key))==key and event.get('phase') in {'enter','return','error'},'SDK call phase/identity invalid')
        pair=records.setdefault(key,{});need(event['phase'] not in pair,'duplicate SDK call phase');pair[event['phase']]=event
    need(sequence==list(range(1,len(sequence)+1)),'SDK trace has missing/reordered events')
    for pair in records.values():
        need('enter' in pair and not ('return' in pair and 'error' in pair),'SDK trace lacks original enter or has conflicting terminal phases')
        terminal=pair.get('return') or pair.get('error')
        if terminal:need(terminal['thread_id']==pair['enter']['thread_id'] and terminal['sdk']==pair['enter']['sdk'] and terminal.get('parent_call_id')==pair['enter'].get('parent_call_id'),'SDK call thread/source parent join differs')
    return snapshot,records


def assert_sdk_chain(records,*,root,runtime,run_id,ids,challenge,observed,objective_id,root_goal,child_goal,completed_stages=('a','b'),failure=None):
    database=(runtime/run_id/'control.duckdb').relative_to(root).as_posix();calls=[]
    for pair in records.values():
        event=pair['enter'];args=event.get('arguments',{})
        if args.get('database_path')==database or args.get('run_id')==run_id:
            need('return' in pair or 'error' in pair,'required SDK call never terminated')
            need(any(frame.get('path')=='scripts/svf_backends/native_supervisor_backend.py' and frame.get('sha256')==sha(root/'scripts/svf_backends/native_supervisor_backend.py') for frame in event.get('caller',[])),'SDK call was not made by this actual native supervisor implementation')
            calls.append(pair)
    need(calls,'no actual native SDK calls for fresh fixture DB/run')
    def returned(kind,method,predicate=lambda a,r:True):
        return [pair for pair in calls if pair['enter']['sdk']['class']==kind and pair['enter']['sdk']['method']==method and 'return' in pair and predicate(pair['enter'].get('arguments',{}),pair['return'].get('result',{}))]
    need(returned('IntentRepository','upsert_objective',lambda a,r:a.get('objective_id')==objective_id),'objective was not created through actual SDK')
    need(returned('IntentRepository','upsert_goal',lambda a,r:a.get('goal_cid')==root_goal and a.get('objective_id')==objective_id) and returned('IntentRepository','upsert_goal',lambda a,r:a.get('goal_cid')==child_goal and a.get('parent_goal_cid')==root_goal and a.get('objective_id')==objective_id) and returned('IntentRepository','link_goal_edge',lambda a,r:a.get('parent_goal_cid')==root_goal and a.get('child_goal_cid')==child_goal and a.get('edge_kind')=='subgoal'),'actual SDK goal/subgoal creation missing')
    need(all(returned('IntentRepository','upsert_task',lambda a,r:a.get('task_cid')==ids[k]) for k in ('a','b')),'actual SDK task creation missing')
    need(returned('DatabaseTaskSource','ready_tasks',lambda a,r:ids['a'] in r.get('task_cids',[])),'native scheduler bypassed actual A readiness API')
    if 'b' in completed_stages:need(returned('DatabaseTaskSource','ready_tasks',lambda a,r:ids['b'] in r.get('task_cids',[])),'native scheduler bypassed actual dependency-unlocked B readiness API')
    runs=returned('VerificationProcessRunner','run')
    policy_keys=('require_resource_lease','host_snapshot_is_none','popen_is_subprocess_popen','clock_is_time_monotonic','sleep_is_time_sleep','scheduler_is_sdk_type','host_sampler_is_sdk_function')
    scheduler_path='external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/runtime/resource_scheduler.py'
    registration=json.loads((root/'config/swissknife_visual_functional_foundation_owners.json').read_text())
    for pair in runs:
        policy=pair['enter'].get('arguments',{}).get('runner_policy',{})
        need(all(policy.get(key) is True for key in policy_keys),'SDK runner used injected process/clock/host/resource policy or lacks actual observation')
        need(policy.get('resource_scheduler_source_path')==scheduler_path and policy.get('resource_scheduler_source_sha256')==sha(root/scheduler_path)==registration.get('protected_sha256',{}).get(scheduler_path),'actual live resource scheduler source is not protected')
    for stage in completed_stages:
        attempts=returned('IntentRepository','record_attempt',lambda a,r:a.get('task_cid')==ids[stage])
        need(attempts,'actual durable SDK attempt admission is missing')
        producer_calls=[pair for pair in runs if pair['enter'].get('arguments',{}).get('command_argv')==fixed_argv(runtime,run_id,stage,challenge)]
        need(any(attempt['return']['sequence']<run['enter']['sequence'] for attempt in attempts for run in producer_calls),'SDK attempt was not recorded before real producer dispatch')
        for validator in (False,True):
            argv=fixed_argv(runtime,run_id,stage,challenge,validator=validator)
            matching=[pair for pair in runs if pair['enter'].get('arguments',{}).get('command_argv')==argv]
            executed=executed_argv(argv,root=root)
            need(any(pair['return'].get('result',{}).get('pid')==row['pid'] and pair['return']['result'].get('process_group_id')==row['process_group_id'] and pair['return']['result'].get('command_argv')==executed and pair['return']['result'].get('publication_allowed') is True and pair['return']['result'].get('lease_id') for pair in matching for row in observed if row['argv']==executed),'actual SDK process call missing independent producer/validator kernel join')
        digest='sha256:'+sha(runtime/run_id/(stage+'.json'));validator_argv=fixed_argv(runtime,run_id,stage,challenge,validator=True)
        need(returned('IntentRepository','record_validation_result',lambda a,r:a.get('task_cid')==ids[stage] and a.get('outcome')=='passed' and a.get('evidence_digest')==digest and a.get('argv')==validator_argv),'actual SDK output validation record missing')
        outer=returned('DatabaseTaskSource','compare_and_set_status',lambda a,r:a.get('task_cid_or_alias')==ids[stage] and a.get('status')=='completed' and digest in a.get('evidence_digests',[]))
        inner=returned('IntentRepository','cas_task_status',lambda a,r:a.get('task_cid')==ids[stage] and a.get('new_status')=='completed' and a.get('allow_completion_without_evidence',False) is False and digest in a.get('evidence_digests',[]))
        need(outer,'actual DatabaseTaskSource completion CAS missing');need(inner,'actual evidence-fenced IntentRepository CAS missing')
        need(any(i['enter'].get('parent_call_id')==o['enter']['call_id'] and i['enter']['thread_id']==o['enter']['thread_id'] and o['enter']['sequence']<i['enter']['sequence']<i['return']['sequence']<o['return']['sequence'] for o in outer for i in inner),'actual database-to-intent CAS nesting/thread chain differs')
    if failure:
        attempt_calls=returned('IntentRepository','record_attempt',lambda a,r:a.get('task_cid')==ids['a'])
        failed_calls=[pair for pair in runs if pair['return'].get('result',{}).get('disposition')==('timeout' if failure=='timeout' else 'cancelled')]
        retry_calls=[pair for pair in runs if pair['enter'].get('arguments',{}).get('command_argv')==fixed_argv(runtime,run_id,'a',challenge)]
        need(any(a['return']['sequence']<f['enter']['sequence'] for a in attempt_calls for f in failed_calls) and any(f['return']['sequence']<a['enter']['sequence']<a['return']['sequence']<r['enter']['sequence'] for f in failed_calls for a in attempt_calls for r in retry_calls),'failed and retried real attempts lack separate durable SDK admission history')
        need(any(pair['return'].get('result',{}).get('disposition')==('timeout' if failure=='timeout' else 'cancelled') and pair['return']['result'].get('publication_allowed') is False and any(pair['return']['result'].get('pid')==row['pid'] for row in observed) for pair in runs),'actual SDK timeout/cancellation call absent')
    return {'run_id':run_id,'database_path':database,'sdk_calls':len(calls),'completed_stages':list(completed_stages),'failure':failure,'observational_only':True,'authenticated_origin':False}


def verify_live(profile_path,output_root,*,root=SDK_ROOT):
    """Strict future implementation gate; unavailable ownership/route refuses."""
    selected_profile=Path(profile_path)
    if not selected_profile.is_absolute():selected_profile=root/selected_profile
    need(selected_profile.resolve()==root/'config/swissknife_visual_functional_supervisor.json','unregistered profile')
    output_base=Path(output_root)
    need('..' not in output_base.parts,'unregistered qualification output namespace')
    if not output_base.is_absolute():output_base=root/output_base
    need(output_base.is_absolute() and output_base.resolve()==output_base and output_base.is_relative_to(root/'data/agent_supervisor/swissknife_visual_functional/tasks/SVF-044/qualification'),'unregistered qualification output namespace')
    output=output_base/('attempt-'+uuid.uuid4().hex);output.mkdir(parents=True,mode=0o700)
    sys.path.insert(0,str(root/'scripts/svf_backends'))
    ensure_owned_services=protected_module(root,'scripts/svf_backends/foundation_service_ownership.py').ensure_owned_services
    required=[*IMPLEMENTATION_PATHS,*SDK_PATHS.values(),'external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/runtime/resource_scheduler.py','scripts/svf_backends/fixed_supervisor_worker.py','scripts/svf_backends/fixed_supervisor_output_validator.py']
    expected={path:sha(root/path) for path in required};assert_cpu_preserved(root);witness=ensure_owned_services(root,family='accelerate-supervisor',expected_sources=expected,output_dir=output)
    need(witness['mcp_url']=='http://127.0.0.1:18315/mcp' and witness['expected_sources']==expected,'wrong registered native service witness')
    native=witness['native_process'];actual=process(native['pid']);need(native['unit']=='swissknife-visual-functional-native-accelerate.service' and actual['uid']==os.getuid() and actual['start_ticks']==native['start_ticks'] and any(row.split(':',2)[-1]==native['control_group'] for row in actual['cgroups']),'native kernel identity mismatch')
    runtime=Path(witness['runtime_root']);need(runtime==root/'data/agent_supervisor/swissknife_visual_functional/backends/supervisor-fixtures' and runtime.resolve()==runtime,'wrong registered fixture namespace')
    call_snapshot(root,native,expected,witness);wait_catalog(witness['mcp_url']);Intent,Database,*_=sdk(root);correlation='svf-044-'+uuid.uuid4().hex
    created,raw=rpc(witness['mcp_url'],ALIAS,{'fixture_mode':MODE,'action':'create','fixture':'dependency-output-v1','dry_run':False,'correlation_id':correlation});save(output/'create.json',raw)
    need(created.get('fixture_mode')==MODE,'fixture mode absent');run_id=created.get('run_id');need(type(run_id) is str and str(uuid.UUID(run_id))==run_id,'bad run identity');challenge=created.get('challenge');need(type(challenge) is str and re.fullmatch('[0-9a-f]{32}',challenge),'bad fixed challenge')
    db=runtime/run_id/'control.duckdb';need(created.get('database_path')==str(db) and db.resolve()==db and db.is_file() and not db.is_symlink(),'wrong actual DB path')
    ids=created.get('task_ids');need(type(ids) is dict and set(ids)=={'a','b'} and ids['a']!=ids['b'],'actual task identities missing');repo=Intent(db,owner_id='svf-protected-live-read',install_schema=False);source=Database(intent=repo,owner_id='svf-protected-live-read')
    check_native_payload(created,raw['response']['result'].get('receipt',{}),ALIAS,expected)
    objective=repo.get_objective(created.get('objective_id','missing'));rootgoal=repo.get_goal(created.get('root_goal_cid','missing'));childgoal=repo.get_goal(created.get('child_goal_cid','missing'))
    need(objective and rootgoal and childgoal and childgoal['parent_goal_cid']==rootgoal['goal_cid'] and rootgoal['objective_id']==objective['objective_id'],'actual objective/goal hierarchy missing')
    need(any(e['parent_goal_cid']==rootgoal['goal_cid'] and e['child_goal_cid']==childgoal['goal_cid'] and e['edge_kind']=='subgoal' for e in repo.list_goal_edges()),'actual subgoal containment missing')
    checks={'a_ready_b_blocked':{x['task_cid'] for x in repo.select_ready_tasks()}=={ids['a']}}
    before={key:repo.get_task(value) for key,value in ids.items()};need(list(before['b']['dependencies'])==[ids['a']],'actual dependency absent')
    need(rootgoal['status']!='completed' and childgoal['status']!='completed','unexecuted goal claims completion')
    for stage in ('a','b'):
        task=before[stage]
        need(any(a.get('evidence_policy',{}).get('evidence_kind')=='validation' for a in task['acceptance']),'original required validation acceptance absent')
        need(len(task['validations'])==1 and task['validations'][0]['argv']==fixed_argv(runtime,run_id,stage,challenge,validator=True),'original protected validator changed')
    with KernelWitness(native['pid'],[root/'scripts/svf_backends/fixed_supervisor_worker.py'],run_id) as blocked:
        _,raw=rpc(witness['mcp_url'],ALIAS,{'fixture_mode':MODE,'action':'dispatch','run_id':run_id,'task_key':'b','dry_run':False},allow_error=True)
    save(output/'dependency-refusal.json',raw)
    checks['blocked_dispatch_did_not_complete']=repo.get_task(ids['b'])['status']!='completed'
    checks['blocked_task_not_dispatched']=not blocked.rows() and repo.get_task(ids['b'])['revision']==before['b']['revision']
    observed=[]
    for stage in ('a','b'):
        with KernelWitness(native['pid'],[root/'scripts/svf_backends/fixed_supervisor_worker.py',root/'scripts/svf_backends/fixed_supervisor_output_validator.py'],run_id) as kernel:
            result,raw=rpc(witness['mcp_url'],ALIAS,{'fixture_mode':MODE,'action':'dispatch','run_id':run_id,'task_key':stage,'dry_run':False,'correlation_id':correlation+'-'+stage})
        save(output/('dispatch-'+stage+'.json'),raw);rows=kernel.rows();observed+=rows;checks['actual_'+stage+'_child_observed']=bool(rows)
        check_native_payload(result,raw['response']['result'].get('receipt',{}),ALIAS,expected)
        check_execution(result,runtime/run_id,runtime,run_id,stage,challenge,rows)
        value=load_module(root/'scripts/svf_backends/fixed_supervisor_output_validator.py','live_output_'+stage).check(runtime,run_id,stage,challenge)
        task=repo.get_task(ids[stage]);checks['actual_'+stage+'_completed_after_validation']=task['status']=='completed' and repo.required_evidence_satisfied(ids[stage])[0]
        if stage=='a':
            checks['a_unlocks_b']={x['task_cid'] for x in repo.select_ready_tasks()}=={ids['b']}
            checks['unfinished_subgoal_not_settled']=repo.get_goal(childgoal['goal_cid'])['status']!='completed'
        payload,raw=rpc(witness['mcp_url'],'get_task',{'fixture_mode':MODE,'run_id':run_id,'task_key':stage});save(output/('readback-'+stage+'.json'),raw)
        check_native_payload(payload,raw['response']['result'].get('receipt',{}),'get_task',expected)
        checks['readback_'+stage+'_identity']=payload.get('task_id')==ids[stage] and payload.get('status')=='completed' and payload.get('output_sha256')==value['output_sha256']
    snapshot,pairs=call_snapshot(root,native,expected,witness);chain=assert_sdk_chain(pairs,root=root,runtime=runtime,run_id=run_id,ids=ids,challenge=challenge,observed=observed,objective_id=created['objective_id'],root_goal=created['root_goal_cid'],child_goal=created['child_goal_cid']);save(output/'positive-sdk-call-snapshot.json',snapshot);save(output/'positive-sdk-call-chain.json',chain)
    # Explicit disallowed browser execution fields must be refused pre-dispatch.
    for key,value in [('argv',['sh','-c','true']),('code','print(1)'),('database_path','/tmp/foreign'),('validator','foreign'),('evidence_digest','sha256:'+'0'*64)]:
        _,raw=rpc(witness['mcp_url'],ALIAS,{'fixture_mode':MODE,'action':'dispatch','run_id':run_id,'task_key':'a',key:value,'dry_run':False},allow_error=True);save(output/('refused-'+key+'.json'),raw)
    for label,args in [('foreign-run',{'fixture_mode':MODE,'action':'dispatch','run_id':str(uuid.uuid4()),'task_key':'a','dry_run':False}),('unknown-mode',{'fixture_mode':'not-registered','action':'create','fixture':'dependency-output-v1','dry_run':False}),('path-traversal',{'fixture_mode':MODE,'action':'dispatch','run_id':'../../foreign','task_key':'a','dry_run':False}),('unknown-fixture',{'fixture_mode':MODE,'action':'create','fixture':'arbitrary-command','dry_run':False})]:
        _,raw=rpc(witness['mcp_url'],ALIAS,args,allow_error=True);save(output/('refused-'+label+'.json'),raw)
    # A repeated successful dispatch is a readback, not a second worker.
    previous=repo.get_task(ids['a']);previous_digest=sha(runtime/run_id/'a.json')
    with KernelWitness(native['pid'],[root/'scripts/svf_backends/fixed_supervisor_worker.py'],run_id) as duplicate:
        repeated,raw=rpc(witness['mcp_url'],ALIAS,{'fixture_mode':MODE,'action':'dispatch','run_id':run_id,'task_key':'a','dry_run':False})
    save(output/'duplicate-dispatch.json',raw);checks['successful_dispatch_not_duplicated']=not duplicate.rows() and repo.get_task(ids['a'])['revision']==previous['revision'] and sha(runtime/run_id/'a.json')==previous_digest
    reopen=Intent(db,owner_id='svf-protected-reopen',install_schema=False);checks['db_reopen_persists_actual_output']=all(reopen.get_task(ids[k])['status']=='completed' for k in ('a','b'))
    # Real timeout/cancel followed by one actual bounded retry, never counter surgery.
    for failure in ('timeout','cancel'):
        negative,raw=rpc(witness['mcp_url'],ALIAS,{'fixture_mode':MODE,'action':'create','fixture':failure+'-recovery-v1','dry_run':False});save(output/(failure+'-create.json'),raw)
        check_native_payload(negative,raw['response']['result'].get('receipt',{}),ALIAS,expected)
        nr=negative['run_id'];need(str(uuid.UUID(nr))==nr,'invalid negative fixture UUID');nc=negative['challenge'];need(re.fullmatch('[0-9a-f]{32}',nc),'invalid negative challenge');nrun=runtime/nr;need(negative['database_path']==str(nrun/'control.duckdb'),'negative DB namespace mismatch');nrepo=Intent(nrun/'control.duckdb',owner_id='svf-negative-read',install_schema=False);nid=negative['task_ids']['a']
        response=[];errors=[]
        def dispatch_negative():
            try:response.append(rpc(witness['mcp_url'],ALIAS,{'fixture_mode':MODE,'action':'dispatch','run_id':nr,'task_key':'a','dry_run':False},allow_error=True))
            except Exception as error:errors.append(error)
        with KernelWitness(native['pid'],[root/'scripts/svf_backends/fixed_supervisor_worker.py'],nr) as kernel:
            thread=threading.Thread(target=dispatch_negative,daemon=True);thread.start()
            until=time.monotonic()+10
            while not kernel.rows() and thread.is_alive() and time.monotonic()<until:time.sleep(.01)
            if failure=='cancel':
                need(kernel.rows(),'no real worker before cancellation')
                cancellation,raw=rpc(witness['mcp_url'],ALIAS,{'fixture_mode':MODE,'action':'cancel','run_id':nr,'task_key':'a','dry_run':False});save(output/'cancel-request.json',raw)
            thread.join(timeout=35);need(not thread.is_alive() and not errors and len(response)==1,'negative dispatch did not finish boundedly')
        _,raw=response[0];save(output/(failure+'-dispatch.json'),raw)
        # Typed failure JSON retains the exact raw SDK execution reference.
        error_payload=raw['response'].get('result',{}).get('content',[{}])[0].get('json',{})
        need(error_payload.get('error',{}).get('code') in {'supervisor_timeout','supervisor_cancelled'},'typed real failure absent')
        check_execution(error_payload,nrun,runtime,nr,'a',nc,kernel.rows(),outcome='timeout' if failure=='timeout' else 'cancelled',mode=failure)
        checks[failure+'_never_completed_or_published']=nrepo.get_task(nid)['status']!='completed' and not (nrun/'a.json').exists()
        with KernelWitness(native['pid'],[root/'scripts/svf_backends/fixed_supervisor_worker.py',root/'scripts/svf_backends/fixed_supervisor_output_validator.py'],nr) as retry:
            retried,raw=rpc(witness['mcp_url'],ALIAS,{'fixture_mode':MODE,'action':'retry','run_id':nr,'task_key':'a','dry_run':False})
        save(output/(failure+'-retry.json'),raw);check_native_payload(retried,raw['response']['result'].get('receipt',{}),ALIAS,expected);check_execution(retried,nrun,runtime,nr,'a',nc,retry.rows())
        checks[failure+'_actual_retry_validated']=nrepo.get_task(nid)['status']=='completed' and nrepo.required_evidence_satisfied(nid)[0]
        snapshot,pairs=call_snapshot(root,native,expected,witness);chain=assert_sdk_chain(pairs,root=root,runtime=runtime,run_id=nr,ids=negative['task_ids'],challenge=nc,observed=[*kernel.rows(),*retry.rows()],objective_id=negative['objective_id'],root_goal=negative['root_goal_cid'],child_goal=negative['child_goal_cid'],completed_stages=('a',),failure=failure);save(output/(failure+'-sdk-call-snapshot.json'),snapshot);save(output/(failure+'-sdk-call-chain.json'),chain)
    assert_cpu_preserved(root)
    models,raw=rpc(witness['mcp_url'],'list_models',{});save(output/'preserved-cpu-model-catalog.json',raw)
    checks['existing_cpu_model_catalog_preserved']=any(model.get('model_id')=='gpt2' and model.get('task')=='text-generation' and model.get('device')=='cpu' for model in models.get('models',[]))
    checks['protected_and_sdk_sources_unchanged']=all(sha(root/path)==digest for path,digest in expected.items());checks['same_native_birth']=process(native['pid'])['start_ticks']==native['start_ticks']
    save(output/'database-readback.json',{'objective':dict(objective),'root_goal':dict(rootgoal),'child_goal':dict(childgoal),'goal_edges':[dict(e) for e in repo.list_goal_edges()],'tasks':[dict(repo.get_task(ids[k])) for k in ('a','b')],'events':[dict(e) for e in repo.list_events(limit=1000)]})
    report={'schema':'swissknife.protected-supervisor-live-foundation.v1','run_id':run_id,'ownership_witness':witness,'checks':checks,'qualified':all(checks.values()),'kernel_witnesses':observed,'database_path':str(db),'production_mcp_ready':all(checks.values()),'actual_native_sdk_call_chain_verified':True,'sdk_trace_observational_not_same_uid_authenticated':True,'network_policy':'declared deny_all; no kernel network sandbox claim','work_complete':False,'completion_authority':False}
    save(output/'qualification.json',report);need(report['qualified'],'protected actual live qualification failed')
    print(json.dumps({'qualification':str(output/'qualification.json'),'sha256':sha(output/'qualification.json'),'checks':len(checks),'passed':sum(checks.values()),'work_complete':False,'completion_authority':False}));return report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--profile');p.add_argument('--verify',action='store_true');p.add_argument('--ensure-owned-services',action='store_true');p.add_argument('--sdk-self-test',action='store_true');p.add_argument('--output-root',required=True);a=p.parse_args()
    need(a.sdk_self_test != a.verify,'select exactly one qualification mode')
    if a.sdk_self_test:
        report=sdk_self_test(a.output_root);print(json.dumps({'sdk_qualification':True,'production_mcp_ready':False,'checks':len(report['checks']),'passed':sum(report['checks'].values()),'report':str(Path(a.output_root)/'sdk-qualification.json')}));return 0
    need(a.profile and a.ensure_owned_services,'live qualification requires explicit profile and owned-service authorization');verify_live(a.profile,a.output_root);return 0
if __name__=='__main__':raise SystemExit(main())
