"""Host-only one-use historical DEVELOPMENT transport; no campaign authority.

The fixed public gateway remains unchanged. Host registry + amendment choose the
unit/source/prompt/checker. Worker messages contain the offered IDs only.
"""
from pathlib import Path
import argparse,datetime as dt,fcntl,importlib.util,json,os,secrets,shutil,subprocess,sys,time
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'gateway_v2'));import host_gateway as P
sys.path.insert(0,str(HERE.parent/'historical_adapter'));import adapter as A
import http_proposer as F
# The separate wrapper consumes these utilities without changing the public module.
require=P.require;read=P.read;write=P.write;load=P.load;canonical=P.canonical;sha=P.sha;file_sha=P.file_sha;now=P.now;git=P.git
ROOT=P.ROOT;IMAGE=P.IMAGE;SOCKET=P.SOCKET
SCHEMA='operator-historical-development-grant/v1'

def source_binding():
    paths=[Path(__file__).resolve(),Path(P.__file__).resolve(),Path(A.__file__).resolve(),Path(A.__file__).with_name('cold_scorer.py'),Path(F.__file__).resolve()]
    return {str(p):file_sha(p)for p in paths}
def native_environment(repo):
    C,env=P.native_environment(repo)
    for key in ('IPFS_ACCELERATE_AGENT_GROK_TEX_TOOLCHAIN_JSON','IPFS_ACCELERATE_AGENT_RESEARCH_TOOLCHAIN_JSON'):
        env.pop(key,None)
    return C,env
def configuration_binding(repo):
    C,env=native_environment(repo)
    selected={k:v for k,v in env.items()if(k.startswith(('IPFS_ACCELERATE','IPFS_DATASETS','IPFS_KIT'))or k in ('PATH','PYTHONPATH','HOME'))and not any(x in k for x in ('KEY','TOKEN','SECRET','PASSWORD'))}
    return {'driver_path':str(Path(C.__file__).resolve()),'driver_sha256':file_sha(Path(C.__file__).resolve()),'effective_minimal_profile_environment_sha256':sha(canonical(selected)),'optional_research_tex_profiles':False}
def manifest_for(grant):
    m=A.lookup_unit(grant['registry_path'],grant['registry_sha256'],grant['unit'])
    require(A.digest(m)==grant['manifest_sha256'],'admitted historical unit changed')
    return m
def stable(grant):
    require(source_binding()==grant['source_bindings'],'historical service dependency drift')
    repo=Path(grant['native_repo']);require(configuration_binding(repo)==grant['configuration_binding'],'historical proposal profile drift')
    require(git(repo,'rev-parse','HEAD')==grant['native_head']and not git(repo,'status','--porcelain=v1','--untracked-files=all'),'native source changed')
    require(file_sha(repo/'ipfs_accelerate_py/agent_supervisor/runtime/grok_cli_runner.py')==grant['runner_sha256'],'native runner changed')
    require(now()<dt.datetime.fromisoformat(grant['expires_at']),'expired historical development grant')
    return manifest_for(grant)
def profile_for(m):
    return {'provider':'grok','model':'grok-4.6','expected_served_aliases':['grok-4.6'],'underlying_served_revision_known':False,'transport':F.PROFILE['transport'],'fallback_allowed':False,'http':F.PROFILE,'scorer':m['scorer_profile'],'phases_sequential':True,'max_provider_calls':1,'max_patch_bytes':16384,'scoring_admission':'explicit_ai_operator_candidate_review','automatic_adversarial_scorer_integrity_qualified':False,'production_final_admitted':False}

def preflight(private,registry,registry_sha,unit):
    require(not private.exists(),'fresh preflight export required')
    m=A.lookup_unit(registry,registry_sha,unit);prepared=A.prepare_admitted_unit(private,m)
    _,request_binding=F.build_request(private,m)
    return {'schema':'historical-host-preflight/v1','unit_id':unit,'manifest_sha256':A.digest(m),'source_preimage_sha256':prepared['source_preimage_sha256'],'prompt_sha256':prepared['prompt_sha256'],'request_binding':request_binding,'profile':profile_for(m),'source_bindings':source_binding(),'provider_invoked':False,'oracle_executed':False}

def prepare(private,queue,repo,registry,registry_sha,unit,amendment,amendment_sha):
    private=private.resolve();queue=queue.resolve();repo=repo.resolve();registry=registry.resolve()
    require(not private.exists()and not queue.exists(),'fresh private grant and handoff queue required')
    require(not private.is_relative_to(queue)and not queue.is_relative_to(private),'private grant overlaps worker handoff')
    policy=load(amendment);require(sha(read(amendment))==amendment_sha,'amendment changed')
    require(policy.get('schema')=='ns-historical-development-provider-amendment/v1'and policy.get('scope')=='development_only'and policy.get('unit_id')==unit and policy.get('provider')=='grok'and policy.get('model')=='grok-4.6'and policy.get('expected_served_aliases')==['grok-4.6']and policy.get('fallback_allowed')is False and policy.get('max_provider_calls')==1,'explicit historical development-only amendment required')
    require(type(policy.get('arm'))is str and 0<len(policy['arm'])<=128 and policy.get('transport')==F.PROFILE['transport'],'missing frozen scientific arm/transport')
    m=A.lookup_unit(registry,registry_sha,unit)
    require(m['scorer_profile']['wall_seconds_max']==120 and m['scorer_profile']['pids']==32,'historical scorer budget differs')
    require(policy.get('manifest_sha256')==A.digest(m)and policy.get('prompt_sha256')==sha(m['prompt'].encode()),'amendment not bound to exact source/prompt')
    require(A.digest(m['installed_target_masks'])==m['installed_target_masks_sha256'],'installed target mask inventory changed')
    profile=profile_for(m)
    require(policy.get('profile')==profile,'amendment does not freeze exact proposal/scorer resource and tool profile')
    require(not git(repo,'status','--porcelain=v1','--untracked-files=all'),'native source dirty')
    preflight={'transport':F.PROFILE['transport'],'provider_cli_required':False,'http_source_sha256':file_sha(Path(F.__file__).resolve())}
    private.mkdir(mode=0o700);fd=os.open(private.parent,os.O_RDONLY|os.O_DIRECTORY);os.fsync(fd);os.close(fd)
    prepared=A.prepare_admitted_unit(private,m)
    # HTTP receives only the frozen public request; no agent filesystem/tools.
    _,request_binding=F.build_request(private,m)
    require(policy.get('request_binding')==request_binding,'amendment does not bind full untruncated public request')
    grant={'schema':SCHEMA,'grant_id':secrets.token_hex(16),'unit':unit,'arm':policy['arm'],'created_at':now().isoformat(),'expires_at':(now()+dt.timedelta(hours=2)).isoformat(),'queue':str(queue),'registry_path':str(registry),'registry_sha256':registry_sha,'manifest_sha256':A.digest(m),'source_sha256':prepared['source_preimage_sha256'],'prompt_sha256':prepared['prompt_sha256'],'amendment_sha256':amendment_sha,'profile':profile,'native_repo':str(repo),'native_head':git(repo,'rev-parse','HEAD'),'runner_sha256':file_sha(repo/'ipfs_accelerate_py/agent_supervisor/runtime/grok_cli_runner.py'),'native_preflight':preflight,'configuration_binding':configuration_binding(repo),'source_bindings':source_binding(),'gateway_sha256':file_sha(Path(__file__).resolve()),'request_binding':request_binding,'max_provider_calls':1,'authority':'explicit_operator_development_grant_not_campaign_claim','historical_population_admitted':False,'historical_development_unit_admitted':True,'final_scientific_results_permitted':False}
    write(private/'amendment.json',read(amendment));write(private/'grant.json',canonical(grant))
    P.command(['openssl','genpkey','-algorithm','ED25519','-out',str(private/'signing.pem')]);(private/'signing.pem').chmod(0o600)
    fd=os.open(private/'signing.pem',os.O_RDONLY);os.fsync(fd);os.close(fd)
    pub=P.command(['openssl','pkey','-in',str(private/'signing.pem'),'-pubout','-outform','DER']).stdout;write(private/'public.der',pub)
    request={'schema':'operator-development-request/v1','grant_sha256':sha(canonical(grant)),'grant_id':grant['grant_id'],'request_id':secrets.token_hex(16),'unit':unit,'arm':grant['arm'],'amendment_sha256':amendment_sha};write(private/'expected_request.json',canonical(request))
    queue.mkdir(parents=True)
    offer={'request':request,'profile':profile,'source_sha256':grant['source_sha256'],'public_key_sha256':sha(pub),'public_verifier':{'algorithm':'Ed25519','encoding':'spki_der_base64','data':__import__('base64').b64encode(pub).decode()},'authority':grant['authority'],'mode':'operator_proposal_review_score_historical_development_handoff','status':'waiting_for_exact_worker_request_and_operator_execute'}
    write(queue/'offer.json',canonical(offer),0o644)
    return {'grant_sha256':request['grant_sha256'],'offer_sha256':sha(canonical(offer)),'provider_invoked':False,'historical_evaluation_executed':False}
def seal(private,manifest):
    workspace=private/'proposal';target=private/'sealed';require(not target.exists(),'preserve prior sealed proposal')
    target.mkdir(mode=0o700)
    # Copy all current non-Git content; strict candidate binding rejects additions,
    # removed files, type/mode changes, escaping links and non-admitted edits.
    for p in workspace.iterdir():
        if p.name=='.git':continue
        q=target/p.name
        if p.is_symlink():q.symlink_to(os.readlink(p))
        elif p.is_dir():shutil.copytree(p,q,symlinks=True)
        else:shutil.copy2(p,q,follow_symlinks=False)
    binding=A.candidate_binding(target,manifest)
    return target,binding

def http_reconciliation(private):
    target=private/'http_proposer';cleanup=target/'cleanup.json'
    record={'termination_proven':False,'immediate_operator_action_required':True,'no_automatic_retry':True}
    if cleanup.exists():
        observed=load(cleanup);record.update(termination_proven=observed.get('returncode')==0,immediate_operator_action_required=observed.get('returncode')!=0,container_id=observed.get('container'),cleanup_sha256=A.sha(cleanup))
    command_path=target/'command.private.json'
    if command_path.exists():
        argv=load(command_path);record['command_sha256']=A.sha(command_path)
        if argv.count('--name')==1:record['container_name']=argv[argv.index('--name')+1]
        if argv.count('--cidfile')==1:
            cid=Path(argv[argv.index('--cidfile')+1])
            if cid.exists():
                value=read(cid,100).decode().strip();require(len(value)==64 and all(c in '0123456789abcdef'for c in value),'invalid retained HTTP CID');record['container_id']=value
    if not record['termination_proven']:record['operator_action']='Inspect only the retained exact owned container name/CID and reconcile termination; do not repeat this consumed grant or score an unproven candidate.'
    write(private/'http_reconciliation.json',canonical(record));return record

def sign_phase(private,receipt,phase):
    require(phase in ('proposal','final'),'unknown receipt phase')
    raw=private/(phase+'.unsigned.json');write(raw,canonical(receipt))
    signature=P.command(['openssl','pkeyutl','-sign','-rawin','-inkey',str(private/'signing.pem'),'-in',str(raw)]).stdout
    return {'receipt':receipt,'signature':__import__('base64').b64encode(signature).decode(),'public_key_sha256':sha(read(private/'public.der'))}

def pending_binding(private,grant_sha):
    grant=load(private/'grant.json');require(sha(read(private/'grant.json'))==grant_sha and grant['schema']==SCHEMA,'wrong historical grant')
    m=stable(grant);request=load(private/'expected_request.json')
    require(load(Path(grant['queue'])/'request.json')==request,'review request drift')
    require(sha(read(private/'amendment.json'))==grant['amendment_sha256'],'review amendment drift')
    reservation=load(private/'reservation.json')
    require(reservation['grant_sha256']==grant_sha and reservation['request_sha256']==sha(canonical(request)),'model reservation binding differs')
    pending=load(private/'proposal_result.json');P.verify_signature(pending,private/'public.der');body=pending['receipt']
    require(body['status']=='awaiting_operator_candidate_review' and body['error'] is None and body['scorer']['executed'] is False,'proposal not pending review')
    require(body['provider_termination']['termination_proven'] is True,'provider termination not established')
    require(body['grant_sha256']==grant_sha and body['request_sha256']==reservation['request_sha256'],'pending receipt scope differs')
    require(body['proposal_result_sha256']==file_sha(private/'http_proposer/result.json'),'proposal result changed')
    candidate=A.candidate_binding(private/'sealed',m)
    require(candidate==load(private/'candidate_binding.json') and candidate['sha256']==body['candidate_sha256'],'sealed candidate changed')
    binding={'grant_sha256':grant_sha,'request_sha256':reservation['request_sha256'],'proposal_receipt_sha256':file_sha(private/'proposal_result.json'),'provider_result_sha256':body['proposal_result_sha256'],'reservation_sha256':file_sha(private/'reservation.json'),'amendment_sha256':grant['amendment_sha256'],'source_sha256':grant['source_sha256'],'manifest_sha256':grant['manifest_sha256'],'profile_sha256':sha(canonical(grant['profile'])),'candidate_binding_sha256':sha(canonical(candidate)),'candidate_sha256':candidate['sha256'],'patch_sha256':candidate['patch_sha256'],'scorer_source_sha256':file_sha(Path(A.__file__).with_name('cold_scorer.py')),'adapter_source_sha256':file_sha(Path(A.__file__)),'scorer_profile_sha256':sha(canonical(m['scorer_profile']))}
    return grant,m,body,binding

def review_template(private,grant_sha):
    _,_,_,binding=pending_binding(private.resolve(),grant_sha)
    return {'schema':'operator-historical-candidate-review/v1','approved':False,'reviewer_kind':'ai_operator','reviewed_at':None,'binding':binding,'review_statement':'REPLACE after reading this exact candidate diff: record the bounded source review and specific trust assumptions. This is not human annotation or adversarial scorer qualification.','trust_scope':'specific_reviewed_development_candidate_only','automatic_adversarial_scorer_integrity_qualified':False,'human_annotation':False,'final_admission':False}

def score_reviewed(private,grant_sha,review_sha):
    private=private.resolve();fd=os.open(private/'execution.lock',os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
    try:
        fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        grant,m,body,binding=pending_binding(private,grant_sha)
        review=load(private/'operator_review.json');require(file_sha(private/'operator_review.json')==review_sha,'operator review changed')
        require(review.get('schema')=='operator-historical-candidate-review/v1' and review.get('approved')is True and review.get('reviewer_kind')=='ai_operator' and review.get('binding')==binding,'explicit bound AI operator review required')
        require(review.get('trust_scope')=='specific_reviewed_development_candidate_only' and review.get('automatic_adversarial_scorer_integrity_qualified')is False and review.get('human_annotation')is False and review.get('final_admission')is False,'operator review overclaims authority')
        require(type(review.get('review_statement'))is str and 20<=len(review['review_statement'])<=8192 and not review['review_statement'].startswith('REPLACE'),'actual bounded review statement required')
        reviewed=dt.datetime.fromisoformat(review['reviewed_at']);require(dt.datetime.fromisoformat(body['completed_at'])<=reviewed<=now(),'review must follow this sealed proposal')
        if(private/'result.json').exists():
            existing=load(private/'result.json');require(existing['receipt'].get('operator_review_sha256')==review_sha,'different terminal review');return existing
        require(not(private/'score_reservation.json').exists(),'score consumed or uncertain; no automatic scoring retry')
        write(private/'score_reservation.json',canonical({'grant_sha256':grant_sha,'review_sha256':review_sha,'binding':binding,'reserved_at':now().isoformat(),'max_scorer_calls':1,'new_provider_calls':0}))
        # Recheck all immutable inputs immediately before the independent process.
        _,m,_,again=pending_binding(private,grant_sha);require(again==binding and file_sha(private/'operator_review.json')==review_sha,'review inputs changed at scoring boundary')
        started=now().isoformat();score_t0=time.monotonic();error=None
        try:
            scorer=A.score_sealed_candidate(private,private/'sealed',m)
            require(A.candidate_binding(private/'sealed',m)==load(private/'candidate_binding.json'),'sealed candidate changed during scoring')
            stable(grant)
        except BaseException as exc:
            error={'type':type(exc).__name__,'message':str(exc)};scorer={'success':False,'executed':False,'execution_may_have_occurred':True,'reason':'scorer_reconciliation_required_no_automatic_retry'}
        receipt=dict(body);receipt.update(status='completed'if error is None else'scorer_reconciliation_required',completed_at=now().isoformat(),score_started_at=started,score_elapsed_seconds=time.monotonic()-score_t0,score_elapsed_seconds_scope='host_scorer_invocation_and_postcheck_only_excludes_proposal_and_operator_review',scorer=scorer,error=error,operator_review_sha256=review_sha,operator_review_binding=binding,operator_review_kind='ai_operator',human_annotation=False,trust_scope='specific_reviewed_development_candidate_only',historical_development_unit_admitted=bool(error is None and not body['inert_qualification'] and body['served_profile_admitted']),new_provider_calls_during_score=0,automatic_adversarial_scorer_integrity_qualified=False,production_final_admitted=False,adversarial_demonstration_performed=False)
        signed=sign_phase(private,receipt,'final');write(private/'result.json',canonical(signed));write(Path(grant['queue'])/'response.json',canonical(signed),0o644);return signed
    finally:os.close(fd)

def execute(private,grant_sha,*,inert_fixture=None):
    inert=inert_fixture is not None
    private=private.resolve();grant=load(private/'grant.json');require(grant['schema']==SCHEMA and sha(read(private/'grant.json'))==grant_sha,'wrong historical grant')
    m=stable(grant);require(sha(read(private/'amendment.json'))==grant['amendment_sha256'],'amendment drift')
    queue=Path(grant['queue']);request=load(queue/'request.json');require(request==load(private/'expected_request.json'),'historical request scope mismatch')
    fd=os.open(private/'execution.lock',os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
    try:
        fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if(private/'result.json').exists():return load(private/'result.json')
        if(private/'proposal_result.json').exists():return load(private/'proposal_result.json')
        require(not(private/'reservation.json').exists(),'historical grant consumed or uncertain; no automatic retry')
        require(sha(read(private/'prompt.txt'))==grant['prompt_sha256'],'proposal prompt changed')
        _,request_binding=F.build_request(private,m);require(request_binding==grant['request_binding'],'frozen visible request changed before effect reservation')
        write(private/'reservation.json',canonical({'grant_sha256':grant_sha,'request_sha256':sha(canonical(request)),'reserved_at':now().isoformat(),'provider_call_budget_consumed':not inert,'possible_external_charge':not inert,'mode':'inert_qualification'if inert else'operator_development','campaign_claim_or_budget_modified':False}))
        started=now().isoformat();t0=time.monotonic();termination=None;failure=None;binding=None;rc=None
        try:
            if inert:require(m.get('qualification_fixture')is True,'inert service qualification cannot execute real historical oracle')
            proposal=F.propose_http(private,m,inert_fixture=inert_fixture)
            rc=proposal['container_exit_code'];termination=http_reconciliation(private);require(termination['termination_proven'],'HTTP proposer termination unproven; no scoring')
            stable(grant);target,binding=seal(private,m)
            require(proposal['success'],'provider candidate not admitted for operator review')
            write(private/'candidate_binding.json',canonical(binding))
            result={'success':False,'executed':False,'reason':'awaiting_operator_candidate_review'}
        except BaseException as exc:
            failure={'type':type(exc).__name__,'message':str(exc)};result={'success':False,'executed':False,'reason':'operator_reconciliation_required'}
            proposal=load(private/'http_proposer/result.json')if(private/'http_proposer/result.json').exists()else None
            if termination is None:termination=http_reconciliation(private)
        provider=(proposal or{}).get('provider')or{}
        meta={'served_models':[provider['served_model']]if provider.get('served_model')else [],'usage':provider.get('usage'),'api_system_fingerprint':provider.get('served_revision'),'underlying_served_revision_known':False,'response_sha256':provider.get('response_sha256'),'runtime_receipt_id':provider.get('runtime_receipt_id')}
        receipt={'schema':'operator-development-receipt/v1','grant_id':grant['grant_id'],'grant_sha256':grant_sha,'request_sha256':sha(canonical(request)),'unit':grant['unit'],'arm':grant['arm'],'amendment_sha256':grant['amendment_sha256'],'profile':grant['profile'],'source_sha256':grant['source_sha256'],'manifest_sha256':grant['manifest_sha256'],'candidate_sha256':binding['sha256']if binding else None,'patch_bytes':binding['patch_bytes']if binding else None,'started_at':started,'completed_at':now().isoformat(),'elapsed_seconds':time.monotonic()-t0,'elapsed_seconds_scope':'proposal_phase_only_excludes_operator_review_and_scoring','provider_invoked':False if inert else(proposal or{}).get('provider_invoked'),'provider_dispatch_attempted':not inert,'provider_dispatch_may_have_occurred':False if inert else(proposal or{}).get('provider_dispatch_may_have_occurred',True),'unknown_external_charge':not inert,'provider_exit_code':rc,'provider_stream_metadata':meta,'served_profile_admitted':False if inert else bool(meta and meta['served_models']==grant['profile']['expected_served_aliases']),'provider_termination':termination,'proposal_result_sha256':A.sha(private/'http_proposer/result.json')if(private/'http_proposer/result.json').exists()else None,'request_binding':grant['request_binding'],'native_campaign_claim_admitted':False,'authority':grant['authority'],'scorer':result,'error':failure,'inert_qualification':inert,'historical_population_admitted':False,'historical_development_unit_admitted':False,'final_scientific_run':False,'native_production_admission_pending':True}
        receipt.update(status='operator_reconciliation_required'if failure else'awaiting_operator_candidate_review',automatic_adversarial_scorer_integrity_qualified=False,production_final_admitted=False,adversarial_demonstration_performed=False)
        signed=sign_phase(private,receipt,'proposal')
        write(private/'proposal_result.json',canonical(signed));write(queue/'proposal.json',canonical(signed),0o644)
        if failure:
            write(private/'result.json',canonical(signed));write(queue/'response.json',canonical(signed),0o644)
        return signed
    finally:os.close(fd)
def main():
    p=argparse.ArgumentParser();s=p.add_subparsers(dest='command',required=True)
    a=s.add_parser('preflight')
    for n in ('private','registry'):a.add_argument('--'+n,type=Path,required=True)
    for n in ('registry-sha256','unit'):a.add_argument('--'+n,required=True)
    a=s.add_parser('prepare')
    for n in ('private','queue','repo','registry','amendment'):a.add_argument('--'+n,type=Path,required=True)
    for n in ('registry-sha256','unit','amendment-sha256'):a.add_argument('--'+n,required=True)
    for name in ('execute','review-template','score-reviewed'):
        a=s.add_parser(name);a.add_argument('--private',type=Path,required=True);a.add_argument('--grant-sha256',required=True)
        if name=='score-reviewed':a.add_argument('--review-sha256',required=True)
    a=p.parse_args()
    if a.command=='preflight':r=preflight(a.private,a.registry,a.registry_sha256,a.unit)
    elif a.command=='prepare':r=prepare(a.private,a.queue,a.repo,a.registry,a.registry_sha256,a.unit,a.amendment,a.amendment_sha256)
    elif a.command=='execute':r=execute(a.private,a.grant_sha256)
    elif a.command=='review-template':r=review_template(a.private,a.grant_sha256)
    else:r=score_reviewed(a.private,a.grant_sha256,a.review_sha256)
    print(json.dumps(r,sort_keys=True))
if __name__=='__main__':main()
