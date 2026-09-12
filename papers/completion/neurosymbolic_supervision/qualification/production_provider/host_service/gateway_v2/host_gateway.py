"""One-use operator development handoff; not a campaign claim/reservation.

Only the host operator runs prepare/execute. Worker requests carry IDs, never
argv, paths, prompts, credentials or scorer material. No paid call in self-test.
"""
from pathlib import Path
import argparse, base64, datetime as dt, fcntl, hashlib, json, os, secrets
import shutil, stat, subprocess, sys, tempfile, time

IMAGE='sha256:74c4a6ff67f397f8a10b058851d218896b2f1ee0f2cddf47741219b734de93a6'
SOCKET='unix:///var/run/docker.sock'
ROOT=Path(__file__).resolve().parents[5]
SCHEMA='operator-scientific-development-grant/v1'
UNIT='public-slug-development-canary-v1'
ARM='single-fixed-grok-development'
SOURCE=b'def slug(text):\n    return text.strip().lower().replace(" ", "-")\n'
CORRECTED=b'def slug(text):\n    return "-".join(text.lower().split())\n'
PROMPT='Development-only qualification. In slug.py implement slug(text): lowercase and trim text, split on all whitespace, and join nonempty tokens with a single hyphen. Empty or whitespace-only input returns an empty string. Edit only slug.py. Do not add dependencies or read other repositories. There are no tests in this proposal workspace. A separate cold evaluator will execute the exported function. This is not a paper benchmark or final population.\n'
CASES=['  Alpha   Beta  ','\tOne\nTWO  ', '', '   ', 'MiXeD-Text', 'a\tb\tc']
EXPECTED=['alpha-beta','one-two','','','mixed-text','a-b-c']
RUNNER=b'import importlib.util,json,sys\np=json.load(sys.stdin)\ns=importlib.util.spec_from_file_location("candidate","/candidate/slug.py")\nm=importlib.util.module_from_spec(s)\ns.loader.exec_module(m)\nprint(json.dumps({"outputs":[m.slug(x) for x in p["inputs"]]},sort_keys=True))\n'

def require(ok,msg):
    if not ok:raise RuntimeError(msg)
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':')).encode()
def sha(data):return hashlib.sha256(data).hexdigest()
def now():return dt.datetime.now(dt.timezone.utc)
def read(path,limit=8*1024*1024):
    p=Path(path)
    require(p.is_absolute() and p.resolve()==p,'noncanonical or symlink path')
    fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW)
    try:
        s=os.fstat(fd);require(stat.S_ISREG(s.st_mode) and s.st_size<=limit,'nonregular or oversized file')
        with os.fdopen(fd,'rb',closefd=False) as f:data=f.read(limit+1)
        require(len(data)<=limit,'oversized file');return data
    finally:os.close(fd)
def write(path,data,mode=0o600):
    p=Path(path);require(p.parent.resolve()==p.parent,'symlink write parent')
    fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,mode)
    try:
        with os.fdopen(fd,'wb',closefd=False)as f:f.write(data);f.flush();os.fsync(fd)
    finally:os.close(fd)
    fd=os.open(p.parent,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)
def file_sha(path):
    p=Path(path);require(p.is_absolute()and p.resolve()==p,'noncanonical executable')
    fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW)
    try:
        require(stat.S_ISREG(os.fstat(fd).st_mode),'nonregular executable')
        with os.fdopen(fd,'rb',closefd=False)as f:return hashlib.file_digest(f,'sha256').hexdigest()
    finally:os.close(fd)
def load(path):return json.loads(read(path))
def command(argv,**kwargs):
    return subprocess.run(argv,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,**kwargs)
def git(repo,*argv):return command(['git','--no-optional-locks','-C',str(repo),*argv]).stdout.decode().strip()
def native_environment(repo):
    sys.path.insert(0,str(ROOT/'scripts'));import paper_supervisor_campaign as C
    require(Path(C.ROOT)==ROOT,'wrong campaign environment module')
    env=C.environment(repo.parent.parent)
    for name in ('IPFS_ACCELERATE_GROK_TERMINAL_RECEIPT_FD','IPFS_ACCELERATE_AGENT_TRUSTED_FAILURE_RECEIPT_FD'):
        env.pop(name,None)
    env['IPFS_ACCEL_SKIP_CORE']='1'
    return C,env
def configuration_binding(repo):
    C,env=native_environment(repo)
    selected={k:v for k,v in env.items()if (k.startswith(('IPFS_ACCELERATE','IPFS_DATASETS','IPFS_KIT'))or k in ('PATH','PYTHONPATH','HOME'))and not any(word in k for word in ('KEY','TOKEN','SECRET','PASSWORD'))}
    return {'driver_path':str(Path(C.__file__).resolve()),'driver_sha256':file_sha(Path(C.__file__).resolve()),'effective_profile_environment_sha256':sha(canonical(selected))}
def native_preflight(repo):
    C,env=native_environment(repo)
    probe='import sys;sys.path.insert(0,sys.argv[1]);from ipfs_accelerate_py.agent_supervisor.runtime.grok_cli_runner import _select_grok_isolation_backend;print("BOUNDARY="+_select_grok_isolation_backend(require_container_boundary=False))'
    result=command([str(C.PYTHON),'-B','-c',probe,str(repo)],env=env,timeout=30)
    require(b'BOUNDARY=docker\n' in result.stdout,'direct native runner does not select Docker; no operator grant issued')
    cli=shutil.which('grok',path=env.get('PATH'))
    require(cli is not None,'Grok executable unavailable')
    cli=Path(cli).resolve();return {'selected_backend':'docker','grok_bin':str(cli),'grok_bin_sha256':file_sha(cli),'probe_stdout_sha256':sha(result.stdout),'probe_stderr_sha256':sha(result.stderr)}
def provider_metadata(path):
    events=[]
    for line in read(path).splitlines():
        try:event=json.loads(line)
        except (ValueError,UnicodeError):continue
        if isinstance(event,dict)and event.get('type')=='end':
            events.append({k:event[k] for k in ('type','stopReason','sessionId','requestId','usage','num_turns','total_cost_usd','modelUsage')if k in event})
    models=sorted({m for event in events for m in event.get('modelUsage',{})})
    return {'terminal_events':events,'served_models':models,'served_identity_observed':bool(models)}
def receipt_sign(private,receipt):
    data=canonical(receipt);raw=private/'receipt.unsigned.json';write(raw,data)
    sig=command(['openssl','pkeyutl','-sign','-rawin','-inkey',str(private/'signing.pem'),'-in',str(raw)]).stdout
    return {'receipt':receipt,'signature':base64.b64encode(sig).decode(),'public_key_sha256':sha(read(private/'public.der'))}
def verify_signature(response,public):
    require(response['public_key_sha256']==sha(read(public)),'untrusted result public key')
    with tempfile.TemporaryDirectory(prefix='development-result-verify-')as t:
        p=Path(t);write(p/'body',canonical(response['receipt']));write(p/'signature',base64.b64decode(response['signature'],validate=True))
        command(['openssl','pkeyutl','-verify','-pubin','-keyform','DER','-rawin','-inkey',str(public),'-in',str(p/'body'),'-sigfile',str(p/'signature')])

def prepare(private,queue,native_repo,amendment,amendment_sha):
    private=private.resolve();queue=queue.resolve();native_repo=native_repo.resolve()
    require(not private.exists(),'preserve prior grant/state; choose new private directory')
    require(not private.is_relative_to(queue) and not queue.is_relative_to(private),'private state overlaps worker queue')
    require(sha(read(amendment))==amendment_sha,'development amendment changed')
    policy=load(amendment)
    require(policy.get('schema')=='ns-development-provider-amendment/v1' and policy.get('scope')=='development_only' and policy.get('provider')=='grok' and policy.get('model')=='grok-4.6' and policy.get('transport')=='operator_host_native_builder_with_explicit_resources' and policy.get('fallback_allowed') is False and policy.get('max_provider_calls')==1 and policy.get('expected_served_aliases')==['grok-4.6-build'],'explicit one-call development amendment required')
    private.mkdir(mode=0o700)
    parent_fd=os.open(private.parent,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(parent_fd)
    finally:os.close(parent_fd)
    queue.mkdir(parents=True,exist_ok=True)
    require(queue.resolve()==queue,'queue is symlinked')
    runner=native_repo/'ipfs_accelerate_py/agent_supervisor/runtime/grok_cli_runner.py'
    require(not git(native_repo,'status','--porcelain=v1','--untracked-files=all'),'native source is dirty')
    preflight=native_preflight(native_repo)
    grant={'schema':SCHEMA,'grant_id':secrets.token_hex(16),'unit':UNIT,'arm':ARM,
           'created_at':now().isoformat(),'expires_at':(now()+dt.timedelta(hours=2)).isoformat(),
           'queue':str(queue),'amendment_sha256':amendment_sha,'native_repo':str(native_repo),
           'native_head':git(native_repo,'rev-parse','HEAD'),'runner_sha256':sha(read(runner)),
           'native_preflight':preflight,'configuration_binding':configuration_binding(native_repo),
           'gateway_sha256':sha(read(Path(__file__).resolve())),'wrapper_sha256':sha(read(Path(__file__).with_name('invoke_native_bounded.py').resolve())),'source_sha256':sha(SOURCE),
           'prompt_sha256':sha(PROMPT.encode()),'scorer_sha256':sha(RUNNER),
           'profile':{'provider':'grok','model':'grok-4.6','expected_served_aliases':['grok-4.6-build'],'underlying_served_revision_known':False,'fallback_allowed':False,'image':IMAGE,'max_turns':6,'wall_seconds':180,'cpu_cores':1,'memory_bytes':2147483648,'pids':32,'transport':'operator_host_native_builder_with_explicit_resources','scorer_memory_bytes':536870912,'scorer_pids':32,'scorer_wall_seconds':20,'phases_sequential':True},
           'max_provider_calls':1,'authority':'explicit_operator_development_grant_not_campaign_claim',
           'historical_population_admitted':False,'final_scientific_results_permitted':False}
    write(private/'amendment.json',read(amendment));write(private/'grant.json',canonical(grant))
    command(['openssl','genpkey','-algorithm','ED25519','-out',str(private/'signing.pem')]);(private/'signing.pem').chmod(0o600)
    pub=command(['openssl','pkey','-in',str(private/'signing.pem'),'-pubout','-outform','DER']).stdout;write(private/'public.der',pub)
    request={'schema':'operator-development-request/v1','grant_sha256':sha(canonical(grant)),
             'grant_id':grant['grant_id'],'request_id':secrets.token_hex(16),'unit':UNIT,'arm':ARM,
             'amendment_sha256':amendment_sha}
    write(private/'expected_request.json',canonical(request))
    public={'request':request,'profile':grant['profile'],'source_sha256':grant['source_sha256'],
            'public_key_sha256':sha(pub),'public_verifier':{'algorithm':'Ed25519','encoding':'spki_der_base64','data':base64.b64encode(pub).decode()},'authority':grant['authority'],
            'mode':'two_phase_operator_handoff','status':'waiting_for_worker_request_then_operator_execute'}
    write(queue/'offer.json',canonical(public),0o644)
    return {'grant':str(private/'grant.json'),'grant_sha256':sha(canonical(grant)),'offer':str(queue/'offer.json'),'provider_invoked':False}

def score(private,sealed):
    grader=private/'scorer';grader.mkdir(mode=0o700);write(grader/'probe.py',RUNNER,0o444)
    require(sha(read(grader/'probe.py'))==sha(RUNNER),'scorer changed')
    name='ns-development-score-'+secrets.token_hex(12);cid=private/'scorer.cid'
    create=['docker','--host',SOCKET,'create','--cidfile',str(cid),'--name',name,'--network','none','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--user',f'{os.getuid()}:{os.getgid()}','--cpus','1','--memory','512m','--memory-swap','512m','--pids-limit','32','--tmpfs','/tmp:rw,nosuid,nodev,size=16777216',
            '--entrypoint=python3','--mount',f'type=bind,src={sealed},dst=/candidate,readonly','--mount',f'type=bind,src={grader},dst=/runner,readonly','-i',IMAGE,'-I','-B','/runner/probe.py']
    write(private/'scorer.command.json',canonical(create));command(create)
    exact=read(cid,100).decode().strip();require(len(exact)==64 and all(c in '0123456789abcdef'for c in exact),'invalid owned scorer identity')
    try:
        inspect=json.loads(command(['docker','--host',SOCKET,'inspect',exact]).stdout)[0]
        mounts={m['Source']:m for m in inspect['Mounts'] if m['Type']=='bind'}
        require(sorted((m['Source'],m['Destination'],m['RW'])for m in mounts.values())==sorted([(str(sealed),'/candidate',False),(str(grader),'/runner',False)]),'scorer mount boundary mismatch')
        h=inspect['HostConfig']
        require(h['NetworkMode']=='none' and h['NanoCpus']==1000000000 and h['Memory']==536870912 and h['PidsLimit']==32 and h['MemorySwap']==536870912 and h['ReadonlyRootfs'] and not h.get('Privileged') and inspect['Image']==IMAGE and inspect['Config']['User']==f'{os.getuid()}:{os.getgid()}' and h.get('CapDrop')==['ALL'] and any(x.startswith('no-new-privileges')for x in h.get('SecurityOpt',[])) and not h.get('PidMode') and inspect['State']['Running']is False,'scorer actual resource/security profile differs')
        write(private/'scorer.boundary.json',canonical({'image':inspect['Image'],'resources':{k:h[k]for k in ('NetworkMode','NanoCpus','Memory','MemorySwap','PidsLimit','ReadonlyRootfs','CapDrop','SecurityOpt')},'mounts':[{k:m[k]for k in ('Source','Destination','RW')}for m in mounts.values()],'checked_before_start':inspect['State']['Running']is False}))
        run=subprocess.run(['docker','--host',SOCKET,'start','-a','-i',exact],input=canonical({'inputs':CASES}),stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=20)
        write(private/'scorer.stdout',run.stdout);write(private/'scorer.stderr',run.stderr)
        outcome=json.loads(run.stdout)if run.returncode==0 else {}
        require(set(outcome)<= {'outputs'},'unexpected scorer output fields')
        outputs=outcome.get('outputs');passed=isinstance(outputs,list) and outputs==EXPECTED
        return {'executed':True,'exit_code':run.returncode,'passed':passed,'case_count':len(CASES),'passed_count':sum(a==b for a,b in zip(outputs,EXPECTED))if isinstance(outputs,list) and len(outputs)==len(EXPECTED) else 0,'network':'none','oracle_files_mounted':False,'source':'separate_host_expected_outcomes','stdout_sha256':sha(run.stdout),'stderr_sha256':sha(run.stderr)}
    finally:
        cleanup=subprocess.run(['docker','--host',SOCKET,'rm','-f',exact],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        write(private/'scorer.cleanup.json',canonical({'container_id':exact,'returncode':cleanup.returncode}));require(cleanup.returncode==0,'owned scorer cleanup failed')

def terminate_owned_provider(private):
    """Retain and stop only the exact CID durably produced by this invocation."""
    evidence={'checked_at':now().isoformat(),'container_id':None,'termination_proven':False}
    created=private/'provider.created.json';argvpath=private/'provider.create-argv.json'
    if created.exists():cid=load(created)['container_id']
    elif argvpath.exists():
        argv=load(argvpath);require(argv.count('--cidfile')==1,'ambiguous owned cidfile')
        cidpath=Path(argv[argv.index('--cidfile')+1])
        if not cidpath.exists():
            evidence['reason']='create was prepared without a retained CID; manual inventory required'
            write(private/'provider.termination.json',canonical(evidence));return evidence
        cid=read(cidpath,100).decode().strip()
    else:
        evidence.update(termination_proven=True,provider_started=False,reason='native create was never prepared')
        write(private/'provider.termination.json',canonical(evidence));return evidence
    require(len(cid)==64 and all(c in '0123456789abcdef'for c in cid),'invalid exact owned provider CID')
    evidence['container_id']=cid
    observed=subprocess.run(['docker','--host',SOCKET,'inspect',cid],capture_output=True,timeout=15)
    if observed.returncode:
        require(b'no such object' in observed.stderr.lower() or b'no such container' in observed.stderr.lower(),'provider exit inventory failed')
        evidence.update(termination_proven=True,provider_started=None,reason='exact owned container absent after native return')
    else:
        data=json.loads(observed.stdout)[0];state=data['State'];evidence['state_before_cleanup']={k:state.get(k)for k in ('Status','Running','StartedAt','FinishedAt','ExitCode')}
        evidence['provider_started']=state.get('StartedAt','').startswith('0001-')is False
        removed=subprocess.run(['docker','--host',SOCKET,'rm','-f',cid],capture_output=True,timeout=20)
        evidence['cleanup_returncode']=removed.returncode
        require(removed.returncode==0,'owned provider cleanup failed; immediate operator action required')
        check=subprocess.run(['docker','--host',SOCKET,'inspect',cid],capture_output=True,timeout=10)
        require(check.returncode!=0 and (b'no such object'in check.stderr.lower() or b'no such container'in check.stderr.lower()),'owned provider still present after cleanup')
        evidence['termination_proven']=True
        evidence['forced_running_cleanup']=state['Running']
    write(private/'provider.termination.json',canonical(evidence));return evidence

def execute(private,grant_sha,*,inert=False):
    private=private.resolve();grant=load(private/'grant.json')
    require(sha(read(private/'grant.json'))==grant_sha and grant['schema']==SCHEMA,'wrong grant')
    require(sha(read(Path(__file__).resolve()))==grant['gateway_sha256'] and sha(read(Path(__file__).with_name('invoke_native_bounded.py').resolve()))==grant['wrapper_sha256'],'gateway source drift')
    require(now()<dt.datetime.fromisoformat(grant['expires_at']),'expired grant')
    require(configuration_binding(Path(grant['native_repo']))==grant['configuration_binding'],'host execution profile changed')
    queue=Path(grant['queue']);request=load(queue/'request.json')
    require(request==load(private/'expected_request.json'),'request scope mismatch')
    require(sha(read(private/'amendment.json'))==grant['amendment_sha256'],'amendment drift')
    require(grant['unit']==UNIT and grant['source_sha256']==sha(SOURCE) and grant['prompt_sha256']==sha(PROMPT.encode()) and grant['scorer_sha256']==sha(RUNNER),'fixed development source/scorer differs')
    lock=private/'execution.lock';fd=os.open(lock,os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
    try:
        fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if (private/'result.json').exists():return load(private/'result.json')
        require(not (private/'reservation.json').exists(),'grant already consumed or uncertain; operator reconciliation required, never automatic reinvoke')
        repo=Path(grant['native_repo']);runner=repo/'ipfs_accelerate_py/agent_supervisor/runtime/grok_cli_runner.py'
        require(git(repo,'rev-parse','HEAD')==grant['native_head'] and not git(repo,'status','--porcelain=v1','--untracked-files=all') and sha(read(runner))==grant['runner_sha256'],'native route changed')
        preflight=native_preflight(repo)
        require(all(preflight[k]==grant['native_preflight'][k] for k in ('selected_backend','grok_bin','grok_bin_sha256')),'native direct-run boundary/CLI changed')
        workspace=private/'proposal';workspace.mkdir(mode=0o700);write(workspace/'slug.py',SOURCE,0o644)
        command(['git','init','-q',str(workspace)]);command(['git','-C',str(workspace),'add','slug.py']);command(['git','-C',str(workspace),'-c','user.name=Development Gateway','-c','user.email=development.invalid','commit','-q','-m','Pinned public development source'])
        write(private/'reservation.json',canonical({'grant_sha256':grant_sha,'request_sha256':sha(canonical(request)),'reserved_at':now().isoformat(),'provider_call_budget_consumed':not inert,'possible_external_charge':not inert,'mode':'inert_qualification'if inert else'operator_development','campaign_claim_or_budget_modified':False}))
        started=now().isoformat();t0=time.monotonic();returncode=0;failure=None;termination=None
        try:
            if inert:(workspace/'slug.py').write_bytes(CORRECTED)
            else:
                # The operator transport is explicit; no borrowed campaign claim,
                # fabricated quota receipt or Codex fallback is supplied.
                C,env=native_environment(repo)
                argv=[str(C.PYTHON),'-B',str(Path(__file__).with_name('invoke_native_bounded.py')),'--private',str(private),'--grant-sha256',grant_sha]
                write(private/'provider.command.json',canonical(argv))
                with (private/'provider.stdout').open('xb')as out,(private/'provider.stderr').open('xb')as err:
                    os.fchmod(out.fileno(),0o600);os.fchmod(err.fileno(),0o600)
                    try:run=subprocess.run(argv,input=PROMPT.encode(),cwd=workspace,env=env,stdout=out,stderr=err,timeout=grant['profile']['wall_seconds'])
                    finally:
                        out.flush();err.flush();os.fsync(out.fileno());os.fsync(err.fileno())
                returncode=run.returncode
                termination=terminate_owned_provider(private)
                require(termination['termination_proven'] and not termination.get('forced_running_cleanup'),'provider termination not clean; no scoring')
                require((private/'provider.boundary.json').exists(),'provider was not admitted at the actual pre-start boundary')
            files=[p for p in workspace.rglob('*')if p.is_file()and'.git'not in p.relative_to(workspace).parts]
            require([p.relative_to(workspace).as_posix()for p in files]==['slug.py'],'proposal exceeded fixed output scope')
            payload=read(workspace/'slug.py',65536);payload.decode('utf-8');require(b'\x00'not in payload,'binary proposal rejected')
            sealed=private/'sealed';sealed.mkdir(mode=0o700);write(sealed/'slug.py',payload,0o444)
            scored=score(private,sealed)if returncode==0 else {'executed':False,'passed':False,'reason':'provider_nonzero'}
        except BaseException as exc:
            scored={'executed':False,'passed':False,'reason':'operator_reconciliation_required'};failure={'type':type(exc).__name__,'message':str(exc)}
            if not inert and termination is None:
                try:termination=terminate_owned_provider(private)
                except BaseException as cleanup_exc:
                    termination={'termination_proven':False,'immediate_operator_action_required':True,'error':str(cleanup_exc)}
                    if not(private/'provider.termination.json').exists():write(private/'provider.termination.json',canonical(termination))
        receipt={'schema':'operator-development-receipt/v1','grant_id':grant['grant_id'],'grant_sha256':grant_sha,'request_sha256':sha(canonical(request)),
                 'unit':UNIT,'arm':ARM,'amendment_sha256':grant['amendment_sha256'],'profile':grant['profile'],
                 'started_at':started,'completed_at':now().isoformat(),'elapsed_seconds':time.monotonic()-t0,'provider_invoked':False if inert else (termination or {}).get('provider_started'),'provider_dispatch_attempted':not inert,
                 'provider_dispatch_may_have_occurred':not inert,'provider_exit_code':returncode if failure is None else None,
                 'provider_token_usage':None,'provider_cost':None,'unknown_external_charge':not inert,
                 'native_campaign_claim_admitted':False,'inert_qualification':inert,'source_sha256':sha(SOURCE),
                 'candidate_sha256':sha(read(private/'sealed/slug.py'))if(private/'sealed/slug.py').exists()else None,
                 'scorer':scored,'error':failure,'final_scientific_run':False,'historical_population_admitted':False,
                 'provider_termination':termination,'native_production_admission_pending':True,'authority':'explicit_operator_development_grant_not_campaign_claim'}
        receipt['provider_stream_metadata']=provider_metadata(private/'provider.stdout')if(private/'provider.stdout').exists()else None
        metadata=receipt['provider_stream_metadata']
        receipt['served_profile_admitted']=False if inert else bool(metadata and metadata['served_models']==grant['profile']['expected_served_aliases'])
        signed=receipt_sign(private,receipt);write(private/'result.json',canonical(signed));write(queue/'response.json',canonical(signed),0o644)
        return signed
    finally:os.close(fd)

def main():
    p=argparse.ArgumentParser();s=p.add_subparsers(dest='command',required=True)
    a=s.add_parser('prepare');a.add_argument('--private',type=Path,required=True);a.add_argument('--queue',type=Path,required=True);a.add_argument('--native-repo',type=Path,required=True);a.add_argument('--amendment',type=Path,required=True);a.add_argument('--amendment-sha256',required=True)
    a=s.add_parser('execute');a.add_argument('--private',type=Path,required=True);a.add_argument('--grant-sha256',required=True)
    a=s.add_parser('qualify-inert');a.add_argument('--private',type=Path,required=True);a.add_argument('--grant-sha256',required=True)
    a=s.add_parser('verify');a.add_argument('--response',type=Path,required=True);a.add_argument('--public-key',type=Path,required=True)
    a=p.parse_args()
    if a.command=='prepare':r=prepare(a.private,a.queue,a.native_repo,a.amendment,a.amendment_sha256)
    elif a.command=='verify':verify_signature(load(a.response),a.public_key);r={'signature_valid':True,'provider_invoked':False}
    else:r=execute(a.private,a.grant_sha256,inert=a.command=='qualify-inert')
    print(json.dumps(r,sort_keys=True))
if __name__=='__main__':main()
