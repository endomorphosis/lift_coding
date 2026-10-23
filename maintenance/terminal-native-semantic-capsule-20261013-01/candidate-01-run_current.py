"""Fresh current-owner review forecasts, exact native replay and offline packets."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import sys

V = Path(__file__).resolve().parent
A = V/'actual-public-semantic-01'
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
from benchmarks.agent_supervisor.container_coding import terminal_native_semantic_capsule as native
from benchmarks.agent_supervisor.container_coding import terminal_semantic_context_transport as transport
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
    capsule=capsules.build_call_proof_capsule(**basis);save('checked-call-capsule.json',capsule)
    roots=observe_policy(None)
    observed=index.observe_current(repository,expected_head=head,scheduler=scheduler)
    save('observed-manifest.json',observed.manifest.to_dict())
    native_set=native.build_native_semantic_capsule_set(manifest=observed.manifest,expected_head=head)
    save('native-semantic-capsules.json',native_set)
    sources={path:(repository/path).read_bytes() for path in model['paths']}
    views=transport.build_bound_code_views(sources=sources,head=head.to_dict())
    save('code-views.json',views)
    view_source_bytes=sum(len(raw) for raw in sources.values())
    request,materials,binding=semantic.build_semantic_call_review_basis(manifest=observed.manifest,
        expected_head=head,native_capsules=native_set,code_views=views,sources=sources,
        repository=repository,policy_roots=roots,**basis)
    save('pre-capacity-binding.json',binding)
    original_binding=planning.build_call_review_plan_basis(repository=repository,policy_roots=roots,**basis)[2]
    assert binding['material_basis_cid']!=original_binding['material_basis_cid']
    assert materials.current_facts==() and semantic.MATERIAL_KEY in materials.extra
    common=dict(index=index,repository=repository,expected_head=head,tool_policy=prepared['tool_policy'],
        policy_roots=roots,policy_observer=observe_policy,scheduler=scheduler,native_capsules=native_set,code_views=views)
    encoding=tokenizer._load_tokenizer()
    # Full W packets can exceed the older V 256KiB measurement profile; still bound to W's 1MiB.
    def measure(text):
        raw=text.encode();assert len(raw)<=transport.MAX_DECODED_BYTES
        tokens=encoding.encode(text,allowed_special=set(),disallowed_special=())
        assert encoding.decode(tokens)==text
        return {'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'tokens':len(tokens)}
    measures={};packet_pins={};results={}
    with capacity.reserve_call_review_capacity(scheduler=scheduler,binding=binding,timeout_seconds=120) as control:
        public_capacity=control.public_dict();save('capacity.json',public_capacity)
        common['capacity_control']=control
        v_packet=planning.build_call_review_context_packet(representation='capsule',capacity_control=control,**basis)
        (RUN/'original-call-context.json').write_bytes(v_packet.encode())
        measures['call_capsule_without_native']=measure(v_packet)
        full=semantic.build_semantic_context_packet(representation='capsule',capacity_control=control,
            native_capsules=native_set,code_views=views,**basis)
        encoded=transport.encode_context_packet(json.loads(full))
        for kind,text,is_encoded in [('full',full,False),('dictionary',encoded,True)]:
            normalized=semantic.normalize_semantic_context_packet(text,encoded=is_encoded,capacity_control=control,
                native_capsules=native_set,code_views=views,**basis)
            assert normalized['native_capsule_set_id']==native_set['capsule_set_id']
            decoded=transport.decode_context_packet(text) if is_encoded else json.loads(text)
            assert transport.canonical_context_packet(decoded)==full
            path=RUN/(kind+'-packet.json');path.write_bytes(text.encode())
            measures[kind]=measure(text);packet_pins[kind]={'path':str(path),**measures[kind]}
            result=semantic.preview_current_semantic_call_review(**common,**basis)
            save(kind+'-preview.json',result);results[kind]=result
            replay_material=deepcopy(result['native_parallel_request'])
            assert replay_material.pop('schema')==planning.parallel.PARALLEL_PLAN_REQUEST_SCHEMA
            replayed=planning.parallel.ParallelPlanCompiler().compile(planning.parallel.ParallelPlanCompilationRequest(**replay_material))
            assert replayed.to_dict(include_replay_request=True)==result['native_parallel_plan']
        a,b=results['full'],results['dictionary']
        stable=['input_snapshot_cid','obligation_graph_cid','candidate_portfolio_cid','critique_cid']
        assert all(a['native_preview']['preview'][key]==b['native_preview']['preview'][key] for key in stable)
        assert a['review_projection']==b['review_projection']
        assert normalized_forecast(a['native_parallel_plan'])==normalized_forecast(b['native_parallel_plan'])
        assert a['selected_task_ids']==b['selected_task_ids'] and len(a['selected_task_ids'])==3
        refuse('serialized-capacity-cannot-reconstruct-live-owner',lambda:semantic.preview_current_semantic_call_review(
            **dict(common,capacity_control=public_capacity),**basis))
        for field in ['native_semantic_capsules','code_views','assumptions','residuals','execution_width']:
            bad=json.loads(full)
            if field=='native_semantic_capsules':bad[field]['capsules'][0]['capsule']['source_cid']=head.snapshot_cid
            elif field=='code_views':bad[field]['views'][0]['display_text']='forged view'
            elif field in ['assumptions','residuals']:bad['checked_call_context']['capsule'][field]=[]
            else:bad['checked_call_context']['review_forecast_context'][field]=1
            forged=transport.encode_context_packet(bad)
            refuse('rebound-dictionary-cannot-alter-'+field,lambda forged=forged:semantic.normalize_semantic_context_packet(
                forged,encoded=True,capacity_control=control,native_capsules=native_set,code_views=views,**basis))
        wrong_head=deepcopy(head.to_dict());wrong_head['generation']+=1
        refuse('same-snapshot-wrong-head-generation',lambda:semantic.preview_current_semantic_call_review(
            **dict(common,expected_head=CodebaseHead.from_dict(wrong_head)),**basis))
        changed=deepcopy(native_set);changed['blocks'].pop()
        changed['capsule_set_id']=cid_for_structured({k:v for k,v in changed.items() if k!='capsule_set_id'})
        refuse('rebound-native-set-cannot-omit-block',lambda:semantic.preview_current_semantic_call_review(
            **dict(common,native_capsules=changed),**basis))
        source=repository/'caller.py';raw=source.read_bytes();held=RUN/'held-original-caller.py';swapped=[]
        probe=capacity.host_probes.collect_proof_host_resources
        def swap_source():
            if not swapped:
                source.rename(held);source.write_bytes(raw);source.chmod(0o644);swapped.append(True)
            return probe()
        try:
            capacity.host_probes.collect_proof_host_resources=swap_source
            refuse('same-byte-source-replaced-on-first-capacity-callback',lambda:semantic.preview_current_semantic_call_review(**common,**basis))
            assert swapped
        finally:
            capacity.host_probes.collect_proof_host_resources=probe
            if held.exists():source.unlink();held.rename(source)
        obj=Path(model['caller_object']['path']);raw=obj.read_bytes();held=RUN/'held-original-caller.olean';swapped=[]
        def swap_proof(value):
            roots_now=observe_policy(value)
            if not swapped:
                obj.rename(held);obj.write_bytes(raw);obj.chmod(0o600);swapped.append(True)
            return roots_now
        try:
            refuse('same-byte-proof-replacement-during-policy-observation',lambda:semantic.preview_current_semantic_call_review(
                **dict(common,policy_observer=swap_proof),**basis))
            assert swapped
        finally:
            if held.exists():obj.unlink();held.rename(obj)
        final=semantic.preview_current_semantic_call_review(**common,**basis);save('final-current-preview.json',final)
        assert control.public_dict()==public_capacity
        held_state=scheduler.snapshot();assert held_state['active_lease_count']==1 and held_state['waiting_request_count']==0
    refuse('released-capacity-cannot-replay-context',lambda:semantic.normalize_semantic_context_packet(
        encoded,encoded=True,capacity_control=control,native_capsules=native_set,code_views=views,**basis))
    state=scheduler.snapshot();assert state['active_lease_count']==state['waiting_request_count']==0
    prepared_guard();model_guard();callee_guard();policy_guard();profile_guard()
    summary={'schema':'terminal-native-semantic-live-experiment@1','qualified':True,'head':head.to_dict(),
        'native_capsule_set_id':native_set['capsule_set_id'],'native_root_cid':native_set['native_root']['root_cid'],
        'native_symbol_count':len(native_set['capsules']),'native_block_count':len(native_set['blocks']),
        'native_cold_incremental':native_set['cold_incremental'],'source_scope':native_set['source_scope'],
        'code_view_selections':[{'path':v['path'],'selected':v['selected'],'fallback_reason':v['fallback_reason']} for v in views['views']],
        'display_original_bytes':view_source_bytes,'display_selected_bytes':sum(v['display_bytes'] for v in views['views']),
        'capacity_binding_cid':public_capacity['binding_cid'],'selected_task_ids':final['selected_task_ids'],
        'native_stages':final['native_preview']['preview']['stage_results'],'native_parallel_outcome':'review_only',
        'admitted_execution_width':0,'remaining_admission_blockers':['ir_admission_materials_absent'],
        'stable_native_identity_fields':stable,'stable_review_projection_equal':True,'normalized_forecasts_equal':True,
        'exact_each_native_parallel_replay':True,'complete_parallel_plan_ids_equal':a['native_parallel_plan']['plan_id']==b['native_parallel_plan']['plan_id'],
        'normalization_exclusions':['input_digest','plan_id','deterministic_replay.input_digest','deterministic_replay.plan_id','replay_request.current_time_ms'],
        'packets':packet_pins,'measures':measures,
        'native_capsule_and_display_overhead_tokens':measures['full']['tokens']-measures['call_capsule_without_native']['tokens'],
        'lossless_encoded_packet_token_delta':measures['full']['tokens']-measures['dictionary']['tokens'],
        'lossless_encoded_packet_reduction_basis_points':10000*(measures['full']['tokens']-measures['dictionary']['tokens'])//measures['full']['tokens'],
        'selected_transport':'dictionary' if measures['dictionary']['tokens']<measures['full']['tokens'] else 'full',
        'decoded_model_visible_token_delta':0,'provider_token_savings_measured':False,
        'tokenizer':{'library':'tiktoken','version':tokenizer.TOKENIZER_VERSION,'encoding':tokenizer.ENCODING,
            'vocabulary_sha256':tokenizer.TOKENIZER_SHA256,'bpe_sha256':tokenizer.BPE_SHA256,'offline':True,'approximation_used':False},
        'controls':controls,'policy_observation_count':len(observations),'held_resources_before_release':held_state,
        'resources_after':state,'fresh_qualification_lean_processes':3,'checker_invocations_during_planning':0,
        'provider_calls':0,'training_steps':0,'source_body_executed':False,'production_admitted':False,
        'worker_launched':False,'runtime_behavior_verified':False,'source_origin_verified':False,
        'full_task_satisfaction':False,'convergence_proved':False,'quack_transport_used':False,
        'network_isolation_enforced':False,'project_commits':0,'project_pushes':0,'fixture_commits':1}
    save('summary.json',summary)
    print(json.dumps({'qualified':True,'tokens':measures,'controls':len(controls),'symbols':len(native_set['capsules']),
        'selected_transport':summary['selected_transport'],'execution_width':0}),flush=True)
except Exception as exc:
    save('failure.json',{'qualified':False,'error_type':type(exc).__name__,'reason':str(exc),
        'provider_calls':0,'training_steps':0,'source_body_executed':False})
    raise
finally:connection.close()
