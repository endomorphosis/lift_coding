"""Fresh current-owner review forecasts, exact native replay and offline packets."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace
import sys
import subprocess,shlex,tarfile,io,textwrap

V = Path(__file__).resolve().parent
A = V/'actual-public-checked-01'
RUN = V/sys.argv[1]
os.umask(0o077)
assert not RUN.exists()
RUN.mkdir(mode=0o700)
os.environ['IPFS_ACCELERATE_META_INDEX_DUCKDB']=str(RUN/'meta-index.duckdb')
os.environ['IPFS_ACCELERATE_PYTEST_SEAL_DUCKDB']=str(RUN/'pytest-seal.duckdb')
os.environ['IPFS_ACCELERATE_AGENT_ORCHESTRATION_DIR']=str(RUN/'orchestration')
os.environ['TIKTOKEN_CACHE_DIR']='/tmp/data-gym-cache'

from benchmarks.agent_supervisor.container_coding.terminal_codebase_finite_service_experiment import _open,_scheduler
from benchmarks.agent_supervisor.container_coding import terminal_call_review_planning as planning
from benchmarks.agent_supervisor.container_coding import terminal_semantic_call_review as semantic
from benchmarks.agent_supervisor.container_coding import terminal_semantic_audit_review as review
from benchmarks.agent_supervisor.container_coding import terminal_semantic_audit_view as audit_views
from benchmarks.agent_supervisor.container_coding import terminal_native_semantic_capsule as native
from benchmarks.agent_supervisor.container_coding import terminal_semantic_context_transport as transport
from benchmarks.agent_supervisor.container_coding import terminal_call_review_capacity as capacity
from benchmarks.agent_supervisor.container_coding import terminal_call_intent_profile as profiles
from benchmarks.agent_supervisor.container_coding import terminal_call_proof_capsule as capsules
from benchmarks.agent_supervisor.container_coding import terminal_revision_proof_cache as revisions
from benchmarks.agent_supervisor.container_coding import terminal_input_token_comparison as tokenizer
from benchmarks.agent_supervisor.container_coding import terminal_semantic_context_budget as budgets
from benchmarks.agent_supervisor.container_coding import terminal_semantic_budget_delivery as delivery
from benchmarks.agent_supervisor.container_coding import terminal_semantic_budget_delivery as delivery
from benchmarks.agent_supervisor.container_coding import terminal_checked_worker_budget as worker_budget
from ipfs_accelerate_py.agent_supervisor.planning.plan_revision_contracts import PlanAuthorityRoots
from ipfs_datasets_py.duckdb_control.codebase_catalog import CodebaseHead
from ipfs_datasets_py.logic.software_contracts.content import cid_for_structured

def wire(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode()
def save(name,value):
    path=RUN/name
    with path.open('xb') as stream:stream.write(wire(value))
def retained(path):
    _,raw,guard=revisions._file(path)
    return json.loads(raw),guard

prepared,prepared_guard=retained(A/'prepared.json')
model,model_guard=retained(A/'model/result.json')
callee,callee_guard=retained(Path(model['callee']['native_proof']['path']))
head=CodebaseHead.from_dict(prepared['head'])
repository=A/'repository'
prompt='Under closed-caller-model@1, caller.py::twice(n) must return n + 2.'
profile=profiles.build_call_intent_profile(prompt=prompt)
save('intent-profile.json',profile)
policy={name:{'schema':'authored-call-review-policy@1','role':name,'production_activated':False,
    'worker_allowed':False,'model_calls':0,'training_allowed':False,'mutation_authority':False}
    for name in ('policy','legal','security','provider','usage')}
policy['configuration']=capacity.capacity_configuration_profile()
policy['catalog']={'schema':'authored-call-review-catalog@1','operations':[list(x) for x in planning.previous.OPERATIONS],
    'scope':'conditional evidence review only','completion_authority':False,'mutation_authority':False}
save('policy.json',policy)
_,policy_guard=retained(RUN/'policy.json')
_,profile_guard=retained(RUN/'intent-profile.json')
scheduler=_scheduler(A/'resources.json')
connection,index=_open(A)
observations=[]

def observe_policy(_request):
    policy_guard();profile_guard()
    actual_policy=json.loads((RUN/'policy.json').read_bytes())
    actual_profile=json.loads((RUN/'intent-profile.json').read_bytes())
    assert actual_policy==policy and actual_profile==profile
    profiles.validate_call_intent_profile(actual_profile,prompt=prompt)
    current=index.observe_current(repository,expected_head=head,scheduler=scheduler)
    catalog=cid_for_structured(actual_policy['catalog'])
    ir=planning.previous.intent_root(actual_profile)
    role=lambda name:cid_for_structured(actual_policy[name])
    roots=PlanAuthorityRoots(repository_id=head.repository_id,repository_root_cid=head.snapshot_cid,
        dirty_worktree_root=head.snapshot_cid,task_source_id=cid_for_structured({'intent':ir,'catalog':catalog}),
        task_source_revision=catalog,policy_root=role('policy'),intent_ir_root=ir,legal_ir_root=role('legal'),
        security_ir_root=role('security'),program_root=current.manifest.semantic_state.state_cid,
        capability_catalog_root=catalog,provider_catalog_root=role('provider'),usage_policy_root=role('usage'),
        configuration_root=role('configuration'))
    observations.append(roots.to_dict())
    return roots

controls=[]
def refuse(name,callback):
    try:callback()
    except (ValueError,RuntimeError,TypeError,KeyError) as exc:
        controls.append({'name':name,'rejected':True,'error_type':type(exc).__name__,'reason':str(exc)[:600]})
        save('control-%02d.json'%len(controls),controls[-1])
    else:raise AssertionError('negative control accepted: '+name)

def normalized_forecast(value):
    # Enumerate exactly temporal input identity paths, preserving every other
    # source, proof, capacity, resource, deadline and structural task field.
    value=deepcopy(value)
    for key in ('input_digest','plan_id'):value.pop(key)
    for key in ('input_digest','plan_id'):value['deterministic_replay'].pop(key)
    value['replay_request'].pop('current_time_ms')
    return value

try:
    query=capsules.query_call_capsule_rows(output=A/'model/metadata',expected_metadata=model['metadata'],expected_head=head.to_dict())
    basis=dict(prompt=prompt,intent_profile=profile,model_record=model,query=query,callee_proof=callee)
    save('query.json',query)
    capsule=capsules.build_call_proof_capsule(**basis);save('checked-call-capsule.json',capsule)
    roots=observe_policy(None)
    observed=index.observe_current(repository,expected_head=head,scheduler=scheduler)
    manifest=observed.manifest;save('observed-manifest.json',manifest.to_dict())
    native_set=native.build_native_semantic_capsule_set(manifest=manifest,expected_head=head)
    save('native-semantic-capsules.json',native_set)
    sources={path:(repository/path).read_bytes() for path in model['paths']}
    views=transport.build_bound_code_views(sources=sources,head=head.to_dict());save('code-views.json',views)
    request,materials,binding=semantic.build_semantic_call_review_basis(manifest=manifest,
        expected_head=head,native_capsules=native_set,code_views=views,sources=sources,
        repository=repository,policy_roots=roots,**basis)
    save('pre-capacity-binding.json',binding)
    common=dict(index=index,repository=repository,expected_head=head,tool_policy=prepared['tool_policy'],
        policy_roots=roots,policy_observer=observe_policy,scheduler=scheduler,native_capsules=native_set,code_views=views)

    container='ipfs-checked-worker-context-z01'
    native_owner=json.loads((V/'native-fixture-03/public/owner-receipt.json').read_bytes())
    native_prompt=(V/'native-fixture-03/public/native-prompt.txt').read_text()
    install=json.loads((V/'docker-boundary-01/installation/installation.json').read_bytes())
    raw_boundary=install['boundary']
    boundary={key:raw_boundary[key] for key in ('schema','container_id','image_id','namespaces','owner_uid','worker_uid')}
    boundary.update(purpose='coding',manifest_sha256=install['boundary_sha256'],completion_authority=False)
    policy_budget=budgets.ContextBudgetPolicy(max_rendered_input_tokens=100000,max_new_content_tokens=100000,
        max_rendered_input_bytes=1000000,max_new_content_bytes=1000000,max_model_calls=2,
        max_expansion_calls=0,max_retry_calls=1,max_events=2,max_payload_bytes=256000)
    counter=[0]; worker_calls=[]; actual_snapshots=[]
    def docker_owner(program,payload=None,label='owner'):
        counter[0]+=1;name='%02d-%s'%(counter[0],label)
        cmd=['docker','exec','-i','--user','supervisor','--workdir','/app',container,
            '/opt/ipfs-supervisor/venv/bin/python','-B','-P','-c',program]
        envprogram='import sys;sys.path[:0]=["/opt/ipfs-supervisor/source","/opt/ipfs-supervisor/datasets","/opt/ipfs-supervisor/kit"];'+textwrap.dedent(program)
        cmd[-1]=envprogram
        call=subprocess.run(cmd,input=b'' if payload is None else wire(payload),capture_output=True,timeout=45)
        (RUN/(name+'.stdout')).write_bytes(call.stdout);(RUN/(name+'.stderr')).write_bytes(call.stderr)
        save(name+'-command.json',{'argv':cmd,'returncode':call.returncode})
        if call.returncode:raise RuntimeError(name+' failed; see retained stderr')
        return json.loads(call.stdout)
    snapshot_program='''import json,sys
from pathlib import Path
from ipfs_datasets_py.logic.software_contracts.semantic_index.snapshot import snapshot_repository
p=json.load(sys.stdin)
s=snapshot_repository('/app',repository_id=p['repository_id'],max_file_bytes=p['max_file_bytes'],max_entries=p['max_entries'])
print(json.dumps(s.to_dict(),sort_keys=True,separators=(',',':')))
'''
    snapshot_request={'repository_id':head.repository_id,'max_file_bytes':manifest.snapshot.max_file_bytes,'max_entries':manifest.snapshot.max_entries}
    def current_container():
        actual=docker_owner(snapshot_program,snapshot_request,'snapshot')
        assert actual['snapshot_cid']==head.snapshot_cid
        assert len(actual['entries'])==3
        actual_snapshots.append({'snapshot_cid':actual['snapshot_cid'],'git_commit':actual['git_commit'],'git_tree':actual['git_tree']})
    # The actual native worker receives only an immutable public extension; the
    # original current proof/index and live budget stay in this host owner.
    _, original_host_sources = revisions._capture(repository, model['paths'], head.repository_id)
    original_host_artifacts = planning.previous._retain_model_artifacts(model,callee)
    def final_host_custody():
        original_host_sources.verify_originals()
        for witness in original_host_artifacts:witness()
        prepared_guard();model_guard();callee_guard();policy_guard();profile_guard()
        assert index.current(head.repository_id)==head
    producer_paths=[str(V/'checkout'/item['relative_path']) for item in json.loads((V/'final-runtime-update-02.json').read_bytes())['files']]
    producer_paths.append(str(Path(__file__).resolve()))
    with planning.metadata._producer([SimpleNamespace(__file__=path) for path in producer_paths]) as (transport_producer,transport_guard):
        save('transport-producer.json',transport_producer)
        with capacity.reserve_call_review_capacity(scheduler=scheduler,binding=binding,timeout_seconds=120) as control:
            registered=dict(capacity_control=control,native_capsules=native_set,code_views=views,
                manifest=manifest,expected_head=head,sources=sources,**basis)
            packet=review.build_semantic_audit_context_packet(representation='view',**registered)
            expanded_packet=review.build_semantic_audit_context_packet(representation='expanded',**registered)
            (RUN/'view-packet.json').write_bytes(packet.encode());(RUN/'expanded-packet.json').write_bytes(expanded_packet.encode())
            view=json.loads(packet)['payload']['model_view'];save('audit-view.json',view)
            budget_binding=budgets.build_context_budget_binding(head=head,view_id=view['view_id'],
                reference_basis_cid=view['expansion_directory']['reference_basis_cid'],native_root_cid=view['native_root_cid'],
                capsule_set_id=view['capsule_set_id'],state_cid=view['state_cid'])
            save('budget-binding.json',budget_binding);save('budget-policy.json',policy_budget.to_dict())
            live=budgets.create_semantic_context_budget(binding=budget_binding,policy=policy_budget)
            scope_args=dict(budget_owner=live,context_packet=packet,**common,capacity_control=control)
            # Original host source/proof/producer custody is retained before any
            # container setup or native renderer callback in the guarded operation.
            with delivery._current_delivery_scope(**scope_args,expansion_reference=None,retry_instruction='',basis=basis) as current:
                current_container()
                setup=r'''
    import json,sys,hashlib,subprocess
    from pathlib import Path
    from ipfs_accelerate_py.agent_supervisor.runtime.checked_audit_context import prepare_checked_context_extension,load_checked_context_extension
    from ipfs_accelerate_py.agent_supervisor.runtime.router_public_instruction import load_public_instruction
    from ipfs_accelerate_py.agent_supervisor.runtime.semantic_router_translation import encode_semantic_router_prompt
    p=json.load(sys.stdin);root=Path('/app');public=Path('/opt/ipfs-supervisor/public-fixture');owner=json.loads((public/'owner-receipt.json').read_bytes());native=(public/'native-prompt.txt').read_text()
    workspace=Path('/opt/ipfs-supervisor/worktrees')/p['workspace_name']
    subprocess.run(['git','-C',str(root),'worktree','add','--detach',str(workspace),'HEAD'],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    admission=json.loads((public/'admission.json').read_bytes())
    d=prepare_checked_context_extension(repository=root,admission=admission,task_cid=owner['task_cid'],native_prompt=native,
     public_instruction=owner['public_instruction'],context_packet=p['packet'],checked_binding=p['binding'],budget_policy=p['policy'])
    i=owner['public_instruction'];block,inclusion=load_public_instruction(artifact=Path(i['artifact']),expected_sha256=i['sha256'],task_cid=owner['task_cid'],prompt=native,repository=root,workspace=workspace)
    verified=encode_semantic_router_prompt(prompt=native,repository=root).receipt
    verification={'schema':'semantic-router-source-verification@1',**{key:verified[key] for key in ('task_id','scope_cid','semantic_root_cid','semantic_sha256','native_prompt_sha256','native_prompt_bytes','freshness_checked')}}
    suffix,checked,guard=load_checked_context_extension(artifact=Path(d['artifact']),expected_sha256=d['sha256'],task_cid=owner['task_cid'],native_prompt=native,
     instruction_receipt=inclusion,semantic_verification=verification,workspace=workspace,boundary=p['boundary'],repository=root)
    try:
     guard();result={'descriptor':d,'router_prompt':native+block,'checked_suffix':suffix,'instruction_receipt':inclusion,'checked_inclusion':checked,'semantic_verification':verification,'workspace':str(workspace)}
     print(json.dumps(result,sort_keys=True,separators=(',',':'),ensure_ascii=True))
    finally:guard.close()
    '''
                preflight=docker_owner(setup,{'packet':packet,'binding':budget_binding,'policy':policy_budget.to_dict(),
                    'boundary':boundary,'workspace_name':RUN.name},'prepare')
                save('native-preflight.json',preflight)
                current['check']();current_container()
                prepare_kwargs=dict(native_prompt=native_prompt,worker_workspace=Path(preflight['workspace']),
                    router_prompt=preflight['router_prompt'],checked_suffix=preflight['checked_suffix'],
                    task_cid=native_owner['task_cid'],instruction_receipt=preflight['instruction_receipt'],
                    boundary=boundary,boundary_sha256=install['boundary_sha256'])
                prepared_event=worker_budget.prepare_checked_worker_budget_event(budget_owner=live,event_id='native.view.initial',**prepare_kwargs)
                save('native-budget-preparation.json',prepared_event)
                # Expanded packet is measured as an explicit counterfactual whole
                # native coding input; it is never silently truncated or dispatched.
                expanded_suffix=preflight['checked_suffix'].replace(packet,expanded_packet)
                assert expanded_suffix!=preflight['checked_suffix']
                refuse('expanded-complete-native-input-exceeds-byte-bound-before-launch',lambda:worker_budget.prepare_checked_worker_budget_event(
                    budget_owner=live,event_id='native.expanded.initial',**dict(prepare_kwargs,checked_suffix=expanded_suffix)))
                def guard():
                    transport_guard();current['check']();current_container();transport_guard()
                def launch():
                    d=preflight['descriptor'];i=native_owner['public_instruction']
                    cmd=['docker','exec','-i','--user','supervisor','--workdir',preflight['workspace'],container,
                        '/opt/ipfs-supervisor/bin/router-worker','--model','authored-offline-observer','--reasoning-effort','high',
                        '--timeout','30','--max-output-tokens','128','--purpose','coding','--semantic-repository','/app',
                        '--semantic-transport','native','--public-instruction-artifact',i['artifact'],'--public-instruction-sha256',i['sha256'],
                        '--public-instruction-task-cid',i['task_cid'],'--checked-context-artifact',d['artifact'],
                        '--checked-context-sha256',d['sha256'],'--checked-context-task-cid',d['task_cid'],'--observe-model-input-only']
                    worker_calls.append(cmd)
                    call=subprocess.run(cmd,input=native_prompt.encode(),capture_output=True,timeout=50)
                    n=len(worker_calls);(RUN/f'worker-{n:02d}.stdout').write_bytes(call.stdout);(RUN/f'worker-{n:02d}.stderr').write_bytes(call.stderr)
                    result={'returncode':call.returncode,'stdout':call.stdout.decode(),'stderr':call.stderr.decode()}
                    save(f'worker-{n:02d}-launch.json',{'argv':cmd,'returncode':call.returncode,'stdin_sha256':hashlib.sha256(native_prompt.encode()).hexdigest(),'stdin_bytes':len(native_prompt.encode())})
                    return result
                result=worker_budget.transact_checked_worker_observation(budget_owner=live,preparation=prepared_event,
                    launch_observer=launch,current_guard=guard)
                save('budgeted-native-observation.json',result)
                receipt=json.loads(result['observation']['canonical_json']);save('native-observation.json',receipt)
                assert receipt['checked_context']==preflight['checked_inclusion']
                assert receipt['requested_model']=='authored-offline-observer' and receipt['timeout_seconds']==30 and receipt['requested_output_tokens']==128
                assert receipt['semantic_context_verification']==preflight['semantic_verification']
                assert receipt['external_container_boundary']==boundary
                assert receipt['model_prompt_sha256']==prepared_event['event']['rendered_input']['sha256']
                replay=worker_budget.prepare_checked_worker_budget_event(budget_owner=live,event_id='native.view.retry',
                    kind='retry',retry_of='native.view.initial',**prepare_kwargs)
                before=live.snapshot();n=len(worker_calls)
                refuse('retry-over-cumulative-token-budget-before-actual-worker',lambda:worker_budget.transact_checked_worker_observation(
                    budget_owner=live,preparation=replay,launch_observer=launch,current_guard=guard))
                assert len(worker_calls)==n==1 and live.snapshot()==before
                current['check']();current_container()
            live.close();snapshot=live.snapshot();save('native-budget-trace.json',snapshot)
            budgets.validate_context_budget_snapshot(snapshot,binding=budget_binding,policy=policy_budget)
        cleanup=r'''
    import json,subprocess,sys
    from pathlib import Path
    p=json.load(sys.stdin);cmd=['/usr/bin/sudo','-n','-u','benchmarkworker','--','/opt/ipfs-supervisor/bin/worker-entry','--cleanup'];r=subprocess.run(cmd,cwd='/',capture_output=True,timeout=15)
    if r.returncode:raise RuntimeError('worker cleanup failed')
    subprocess.run(['git','-C','/app','worktree','remove','--force',p['workspace']],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    remaining=[]
    for q in Path('/proc').iterdir():
     if not q.name.isdigit():continue
     try:
      lines=(q/'status').read_text().splitlines();uid=next(x for x in lines if x.startswith('Uid:')).split()[1];state=next(x for x in lines if x.startswith('State:'))
      if uid=='1001' and 'Z' not in state:remaining.append(int(q.name))
     except (FileNotFoundError,PermissionError,ProcessLookupError,StopIteration):pass
    print(json.dumps({'cleanup_returncode':r.returncode,'remaining_worker_pids':remaining,'worktree_removed':not Path(p['workspace']).exists()}))
    '''
        cleanup_result=docker_owner(cleanup,{'workspace':preflight['workspace']},'cleanup');save('cleanup.json',cleanup_result)
        assert cleanup_result['cleanup_returncode']==0 and not cleanup_result['remaining_worker_pids'] and cleanup_result['worktree_removed']
        # Exact native full-input replay after allocated candidate removal. The
        # current canonical original sources must remain unchanged for this profile.
        audit_program=r'''
    import json,sys
    from pathlib import Path
    from benchmarks.agent_supervisor.container_coding import terminal_model_input_observation_audit as observations,terminal_context_audit as audit
    p=json.load(sys.stdin);facts=observations._observation_bindings(p['receipt'],Path('/opt/ipfs-supervisor/worktrees'))
    model,advisory,checks=audit._model_projection(rendered=p['native_prompt'],receipt=facts,repository=Path('/app'))
    import hashlib
    assert all(checks.values())
    print(json.dumps({'passed':True,'checks':checks,'model_sha256':hashlib.sha256(model.encode()).hexdigest(),'model_bytes':len(model.encode()),'workspace_advisory_bytes':len(advisory.encode()),'allocated_worktree_absent':not Path(p['receipt']['workspace']).exists(),'provider_calls':0}))
    '''
        historical=docker_owner(audit_program,{'receipt':receipt,'native_prompt':native_prompt},'historical');save('historical-replay.json',historical)
        assert historical['model_sha256']==receipt['model_prompt_sha256'] and historical['model_bytes']==receipt['model_prompt_bytes']
        prepared_guard();model_guard();callee_guard();policy_guard();profile_guard()
        resources=scheduler.snapshot();assert resources['active_lease_count']==resources['waiting_request_count']==0
        summary={'schema':'terminal-checked-native-worker-experiment@1','qualified':True,
            'head':head.to_dict(),'native_task_cid':native_owner['task_cid'],'snapshot_joins':actual_snapshots,
            'whole_coding_input':{k:prepared_event['event']['rendered_input'][k] for k in ('sha256','bytes','tokens')},
            'new_content':{k:prepared_event['event']['new_content'][k] for k in ('sha256','bytes','tokens')},
            'totals':snapshot['totals'],'budget_policy':policy_budget.to_dict(),'controls':controls,
            'actual_native_worker_observer_invocations':len(worker_calls),'actual_router_calls':receipt['router_calls'],
            'worker_uid':boundary['worker_uid'],'owner_uid':boundary['owner_uid'],'kernel_namespace_boundary_verified_by_native_worker':True,
            'native_checked_context_observation_qualified':True,'native_admitted_benchmark_runtime_START_used':False,
            'full_supervisor_entrypoint_used':False,'Terminal_Bench_harness_used':False,'actual_provider_usage_measured':False,
            'provider_calls':0,'provider_output_tokens':None,'global_task_budget_enforced':False,'durable_budget_resume_supported':False,
            'source_body_executed':False,'training_steps':0,'source_to_model_equivalence_proved':False,'convergence_proved':False,
            'full_task_satisfaction':False,'native_task_status':'ready','pending_checks_executed':False,
            'native_origin_scope':'Controlled Docker owner exec of root-protected router-worker; actual worker kernel UID/namespace verification. No native supervisor marked birth/START claim.',
            'cleanup':cleanup_result,'historical_replay':historical,'resources_after':resources,'project_pushes':0}
        final_host_custody();transport_guard()
        save('summary.json',summary)
        print(json.dumps({'qualified':True,'whole_input':summary['whole_coding_input'],'worker_observer_calls':1,'controls':len(controls),'provider_calls':0}),flush=True)
finally:
    try:
        if 'live' in locals():
            snap=live.snapshot()
            if not snap['closed']:live.close()
            path=RUN/'final-budget-state.json'
            if not path.exists():save('final-budget-state.json',live.snapshot())
        if 'preflight' in locals():
            work=preflight['workspace']
            cmd=['docker','exec','--user','supervisor',container,'/opt/ipfs-supervisor/venv/bin/python','-B','-I','-c',
                "import subprocess,pathlib,json;w="+repr(work)+";r=subprocess.run(['/usr/bin/sudo','-n','-u','benchmarkworker','--','/opt/ipfs-supervisor/bin/worker-entry','--cleanup'],cwd='/',capture_output=True,timeout=15);assert r.returncode==0;exists=pathlib.Path(w).exists();x=subprocess.run(['git','-C','/app','worktree','remove','--force',w],capture_output=True,timeout=15) if exists else None;print(json.dumps({'cleanup_returncode':r.returncode,'owned_worktree_existed':exists,'worktree_removed':not pathlib.Path(w).exists()}))"]
            clean=subprocess.run(cmd,capture_output=True,timeout=30)
            (RUN/'final-cleanup.stdout').write_bytes(clean.stdout);(RUN/'final-cleanup.stderr').write_bytes(clean.stderr)
            save('final-cleanup.json',{'returncode':clean.returncode})
            assert clean.returncode==0
    finally:
        connection.close()
