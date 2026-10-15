"""Fresh current-owner review forecasts, exact native replay and offline packets."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import sys

V = Path(__file__).resolve().parent
A = V/'actual-public-review-01'
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
from benchmarks.agent_supervisor.container_coding import terminal_call_review_capacity as capacity
from benchmarks.agent_supervisor.container_coding import terminal_call_intent_profile as profiles
from benchmarks.agent_supervisor.container_coding import terminal_call_proof_capsule as capsules
from benchmarks.agent_supervisor.container_coding import terminal_revision_proof_cache as revisions
from benchmarks.agent_supervisor.container_coding import terminal_input_token_comparison as tokenizer
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
    capsule=capsules.build_call_proof_capsule(**basis);save('capsule.json',capsule)
    roots=observe_policy(None)
    request,materials,binding=planning.build_call_review_plan_basis(repository=repository,policy_roots=roots,**basis)
    save('pre-capacity-binding.json',binding)
    common=dict(index=index,repository=repository,expected_head=head,tool_policy=prepared['tool_policy'],
        policy_roots=roots,policy_observer=observe_policy,scheduler=scheduler)
    encoding=tokenizer._load_tokenizer()
    results={};measures={};packet_pins={}
    with capacity.reserve_call_review_capacity(scheduler=scheduler,binding=binding,timeout_seconds=120) as control:
        public_capacity=control.public_dict();save('capacity.json',public_capacity)
        common['capacity_control']=control
        for kind in ('expanded','capsule'):
            packet=planning.build_call_review_context_packet(representation=kind,capacity_control=control,**basis)
            normalized=planning.normalize_call_review_context_packet(packet,capacity_control=control,**basis)
            assert normalized['capsule']==capsule and normalized['capacity']==public_capacity
            path=RUN/(kind+'-packet.json');path.write_bytes(packet.encode())
            measures[kind]=tokenizer._measure(packet,encoding)
            packet_pins[kind]={'path':str(path),**measures[kind]}
            result=planning.preview_current_call_review_plan(**common,**basis)
            save(kind+'-preview.json',result);results[kind]=result
            replay_request=planning.parallel.ParallelPlanCompilationRequest(**result['native_parallel_request'])
            replayed=planning.parallel.ParallelPlanCompiler().compile(replay_request)
            assert replayed.to_dict(include_replay_request=True)==result['native_parallel_plan']
        a,b=results['expanded'],results['capsule']
        stable=['input_snapshot_cid','obligation_graph_cid','candidate_portfolio_cid','critique_cid']
        assert all(a['native_preview']['preview'][key]==b['native_preview']['preview'][key] for key in stable)
        assert a['review_projection']==b['review_projection']
        assert normalized_forecast(a['native_parallel_plan'])==normalized_forecast(b['native_parallel_plan'])
        assert a['selected_task_ids']==b['selected_task_ids'] and len(a['selected_task_ids'])==3
        refuse('serialized-capacity-cannot-reconstruct-live-owner',lambda:planning.preview_current_call_review_plan(
            **dict(common,capacity_control=public_capacity),**basis))
        changed=prompt.replace('n + 2','n + 3')
        refuse('changed-requested-offset-cannot-reuse-proof-capacity',lambda:planning.preview_current_call_review_plan(
            **common,**dict(basis,prompt=changed,intent_profile=profiles.build_call_intent_profile(prompt=changed))))
        changed_head=deepcopy(head.to_dict());changed_head['generation']+=1
        refuse('same-snapshot-wrong-generation',lambda:planning.preview_current_call_review_plan(
            **dict(common,expected_head=CodebaseHead.from_dict(changed_head)),**basis))
        bad_packet=json.loads(planning.build_call_review_context_packet(representation='capsule',capacity_control=control,**basis))
        bad_packet['review_forecast_context']['execution_width']=1
        refuse('packet-cannot-invent-positive-execution-width',lambda:planning.normalize_call_review_context_packet(
            wire(bad_packet).decode(),capacity_control=control,**basis))

        source=repository/'caller.py';raw_source=source.read_bytes();held_source=RUN/'held-original-caller.py'
        host_probe=capacity.host_probes.collect_proof_host_resources;swapped=[]
        def replace_source_on_first_capacity_callback():
            if not swapped:
                source.rename(held_source);source.write_bytes(raw_source);source.chmod(0o644);swapped.append(True)
            return host_probe()
        try:
            capacity.host_probes.collect_proof_host_resources=replace_source_on_first_capacity_callback
            refuse('same-byte-source-replaced-on-first-capacity-callback',lambda:planning.preview_current_call_review_plan(**common,**basis))
            assert swapped
        finally:
            capacity.host_probes.collect_proof_host_resources=host_probe
            if held_source.exists():source.unlink();held_source.rename(source)

        object_path=Path(model['caller_object']['path']);object_bytes=object_path.read_bytes();held_object=RUN/'held-original-caller.olean';swapped=[]
        def replace_object_on_policy_callback(value):
            observed=observe_policy(value)
            if not swapped:
                object_path.rename(held_object);object_path.write_bytes(object_bytes);object_path.chmod(0o600);swapped.append(True)
            return observed
        try:
            refuse('same-byte-proof-object-replaced-during-preview',lambda:planning.preview_current_call_review_plan(
                **dict(common,policy_observer=replace_object_on_policy_callback),**basis))
            assert swapped
        finally:
            if held_object.exists():object_path.unlink();held_object.rename(object_path)

        real_builder=planning.projections.build_call_review_projection
        def inject_write(**values):
            projection=real_builder(**values);projection['tasks'][0]['outputs']=['callee.py']
            projection['plan_id']=cid_for_structured({k:v for k,v in projection.items() if k!='plan_id'})
            return projection
        try:
            planning.projections.build_call_review_projection=inject_write
            refuse('rebound-review-task-cannot-invent-source-output',lambda:planning.preview_current_call_review_plan(**common,**basis))
        finally:planning.projections.build_call_review_projection=real_builder

        original_public=control._public_wire;changed_capacity=[]
        def mutate_capacity_on_policy_callback(value):
            observed=observe_policy(value)
            if not changed_capacity:
                modified=json.loads(control._public_wire);modified['initial_observation']['process_slots']=0
                control._public_wire=wire(modified);changed_capacity.append(True)
            return observed
        try:
            refuse('capacity-mutation-during-preview',lambda:planning.preview_current_call_review_plan(
                **dict(common,policy_observer=mutate_capacity_on_policy_callback),**basis))
            assert changed_capacity
        finally:control._public_wire=original_public

        original_clock=capacity._wall_time
        try:
            capacity._wall_time=lambda:0
            refuse('zero-current-clock-cannot-use-native-fallback',lambda:planning.preview_current_call_review_plan(**common,**basis))
        finally:capacity._wall_time=original_clock
        final=planning.preview_current_call_review_plan(**common,**basis);save('final-current-preview.json',final)
        assert control.public_dict()==public_capacity
        held_state=scheduler.snapshot()
        assert held_state['active_lease_count']==1 and held_state['waiting_request_count']==0
    refuse('released-control-cannot-replay-live-plan',lambda:planning.preview_current_call_review_plan(**common,**basis))
    state=scheduler.snapshot();assert state['active_lease_count']==state['waiting_request_count']==0
    prepared_guard();model_guard();callee_guard();policy_guard();profile_guard()
    summary={'schema':'terminal-call-review-live-experiment@1','qualified':True,'head':head.to_dict(),
        'capsule_id':capsule['capsule_id'],'capacity_binding_cid':public_capacity['binding_cid'],
        'selected_task_ids':final['selected_task_ids'],'native_stages':final['native_preview']['preview']['stage_results'],
        'review_forecast_accepted':True,'native_parallel_outcome':'review_only','admitted_execution_width':0,
        'remaining_admission_blockers':['ir_admission_materials_absent'],'review_task_completion_proved':False,
        'stable_native_identity_fields':stable,'stable_review_projection_equal':True,'normalized_forecasts_equal':True,
        'exact_each_native_parallel_replay':True,'complete_parallel_plan_ids_equal':a['native_parallel_plan']['plan_id']==b['native_parallel_plan']['plan_id'],
        'normalization_exclusions':['input_digest','plan_id','deterministic_replay.input_digest','deterministic_replay.plan_id','replay_request.current_time_ms'],
        'normalization_scope':'only independent compile-time and its derived receipt identities; head/capacity/deadline/resources/tasks/leaves retained',
        'packets':packet_pins,'offline_input_token_reduction':measures['expanded']['tokens']-measures['capsule']['tokens'],
        'offline_reduction_basis_points':10000*(measures['expanded']['tokens']-measures['capsule']['tokens'])//measures['expanded']['tokens'],
        'tokenizer':{'library':'tiktoken','version':tokenizer.TOKENIZER_VERSION,'encoding':tokenizer.ENCODING,'vocabulary_sha256':tokenizer.TOKENIZER_SHA256,'bpe_sha256':tokenizer.BPE_SHA256,'offline':True,'approximation_used':False},
        'provider_token_savings_measured':False,'controls':controls,'policy_observation_count':len(observations),
        'held_resources_before_release':held_state,'resources_after':state,'fresh_qualification_lean_processes':3,
        'checker_invocations_during_planning':0,'provider_calls':0,'training_steps':0,'source_body_executed':False,
        'production_admitted':False,'worker_launched':False,'runtime_behavior_verified':False,
        'full_task_satisfaction':False,'convergence_proved':False,'quack_transport_used':False,'network_isolation_enforced':False}
    save('summary.json',summary)
    print(json.dumps({'qualified':True,'tokens':measures,'reduction_basis_points':summary['offline_reduction_basis_points'],
        'negative_controls':len(controls),'native_parallel_outcome':'review_only','execution_width':0,
        'admission_blockers':['ir_admission_materials_absent']}),flush=True)
except Exception as exc:
    save('failure.json',{'qualified':False,'error_type':type(exc).__name__,'reason':str(exc),
        'provider_calls':0,'training_steps':0,'source_body_executed':False})
    raise
finally:connection.close()
