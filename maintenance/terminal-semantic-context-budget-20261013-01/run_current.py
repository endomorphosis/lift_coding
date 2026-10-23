"""Fresh current-owner review forecasts, exact native replay and offline packets."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import sys

V = Path(__file__).resolve().parent
A = V/'actual-public-budget-01'
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

    # Fixed before any trace measurement/admission. Separate owners below are
    # explicit counterfactual traces, not resumable or global-task budgets.
    budget_policy=budgets.ContextBudgetPolicy(max_rendered_input_tokens=100000,
        max_new_content_tokens=60000,max_rendered_input_bytes=1000000,
        max_new_content_bytes=400000,max_model_calls=4,max_expansion_calls=3,
        max_retry_calls=2,max_events=6,max_payload_bytes=256000)
    save('budget-policy.json',budget_policy.to_dict())
    results={};packets={};traces={};calls=[];expansion_calls=[]
    original_resolver=review.resolve_current_semantic_audit_reference
    def count_expansion(**kwargs):
        expansion_calls.append(kwargs['request']['kind'])
        return original_resolver(**kwargs)
    def local_observer(text,prepared):
        assert text==prepared['event']['rendered_input']['text']
        assert prepared['materialization']['native_planning_renderer_used']
        transcript=json.loads(text)
        assert transcript['schema']==delivery.TRANSCRIPT_SCHEMA
        calls.append({'event_id':prepared['event']['event_id'],'bytes':len(text.encode()),
            'sha256':hashlib.sha256(text.encode()).hexdigest()})
    def owner():
        return budgets.create_semantic_context_budget(binding=budget_binding,policy=budget_policy)
    def attempt(budget_owner,kind,event_id,packet='view',**kwargs):
        return delivery.observe_current_budgeted_semantic_input(budget_owner=budget_owner,
            event_id=event_id,kind=kind,context_packet=packets[packet],
            local_observer=local_observer,**common,**basis,**kwargs)
    def refresh(control,label):
        global packets,audit_view,budget_binding
        common['capacity_control']=control
        registered=dict(capacity_control=control,native_capsules=native_set,code_views=views,
            manifest=manifest,expected_head=head,sources=sources,**basis)
        packets={kind:review.build_semantic_audit_context_packet(representation=kind,**registered) for kind in ('expanded','view')}
        audit_view=json.loads(packets['view'])['payload']['model_view']
        budget_binding=budgets.build_context_budget_binding(head=head,view_id=audit_view['view_id'],
            reference_basis_cid=audit_view['expansion_directory']['reference_basis_cid'],
            native_root_cid=audit_view['native_root_cid'],capsule_set_id=audit_view['capsule_set_id'],state_cid=audit_view['state_cid'])
        save(label+'-capacity.json',control.public_dict());save(label+'-budget-binding.json',budget_binding)
        save(label+'-audit-view.json',audit_view)
        (RUN/(label+'-view-packet.json')).write_bytes(packets['view'].encode())
    with capacity.reserve_call_review_capacity(scheduler=scheduler,binding=binding,timeout_seconds=120) as control:
        common['capacity_control']=control
        save('capacity.json',control.public_dict())
        registered=dict(capacity_control=control,native_capsules=native_set,code_views=views,
            manifest=manifest,expected_head=head,sources=sources,**basis)
        for kind in ('expanded','view'):
            packets[kind]=review.build_semantic_audit_context_packet(representation=kind,**registered)
            (RUN/(kind+'-packet.json')).write_bytes(packets[kind].encode())
            results[kind]=review.preview_current_semantic_audit_review(context_packet=packets[kind],**common,**basis)
            save(kind+'-preview.json',results[kind])
        assert results['expanded']['pure_material_basis_cid']==results['view']['pure_material_basis_cid']
        assert results['expanded']['selected_task_ids']==results['view']['selected_task_ids']
        assert len(results['view']['selected_task_ids'])==3
        native_a=results['expanded']['native_review'];native_b=results['view']['native_review']
        for key in ('input_snapshot_cid','obligation_graph_cid','candidate_portfolio_cid','critique_cid'):
            assert native_a['native_preview']['preview'][key]==native_b['native_preview']['preview'][key]
        assert native_a['review_projection']==native_b['review_projection']
        assert normalized_forecast(native_a['native_parallel_plan'])==normalized_forecast(native_b['native_parallel_plan'])
        audit_view=json.loads(packets['view'])['payload']['model_view'];save('audit-view.json',audit_view)
        budget_binding=budgets.build_context_budget_binding(head=head,view_id=audit_view['view_id'],
            reference_basis_cid=audit_view['expansion_directory']['reference_basis_cid'],
            native_root_cid=audit_view['native_root_cid'],capsule_set_id=audit_view['capsule_set_id'],
            state_cid=audit_view['state_cid'])
        save('budget-binding.json',budget_binding)
        review.resolve_current_semantic_audit_reference=count_expansion
        for representation in ('expanded','view'):
            live=owner()
            result=attempt(live,'initial',representation+'.initial',packet=representation)
            save(representation+'-initial-delivery.json',result)
            traces[representation]={'initial_tokens':result['event']['rendered_input']['tokens'],
                'initial_new_tokens':result['event']['new_content']['tokens']}
            if representation=='expanded':
                n=len(calls);e=len(expansion_calls);before=live.snapshot()
                refuse('expanded-retry-over-cumulative-budget-before-observer',lambda:attempt(live,
                    'retry','expanded.retry',packet='expanded',retry_of='expanded.initial',retry_instruction='Continue the same conditional review.'))
                assert len(calls)==n and len(expansion_calls)==e and live.snapshot()==before
            else:
                handle=next(x for x in audit_view['expansion_directory']['references'] if x['kind']=='native_block')
                expanded=attempt(live,'expansion','view.block',expansion_reference=handle)
                save('view-block-delivery.json',expanded)
                n=len(calls);e=len(expansion_calls);before=live.snapshot()
                refuse('view-retry-over-cumulative-budget-before-observer',lambda:attempt(live,
                    'retry','view.retry',retry_of='view.block',retry_instruction='Continue the same conditional review.'))
                assert len(calls)==n and len(expansion_calls)==e and live.snapshot()==before
                refuse('view-state-over-cumulative-budget-before-current-expansion',lambda:attempt(live,
                    'expansion','view.state',expansion_reference=next(x for x in audit_view['expansion_directory']['references'] if x['kind']=='repository_state')))
                assert len(calls)==n and len(expansion_calls)==e and live.snapshot()==before
                refuse('full-audit-expansion-rejected-before-current-expansion',lambda:attempt(live,
                    'expansion','view.full',expansion_reference=audit_view['expansion_directory']['complete_audit_reference']))
                assert len(calls)==n and len(expansion_calls)==e and live.snapshot()==before
            live.close();snapshot=live.snapshot();save(representation+'-trace.json',snapshot)
            budgets.validate_context_budget_snapshot(snapshot,binding=budget_binding,policy=budget_policy)
            traces[representation]['totals']=snapshot['totals']
            traces[representation]['snapshot_cid']=snapshot['snapshot_cid']
    with capacity.reserve_call_review_capacity(scheduler=scheduler,binding=binding,timeout_seconds=120) as control:
        refresh(control,'failure')
        # A failed local callback retains its conservative materialization cost.
        failed_owner=owner();failed_calls=[]
        def failing(text,prepared):
            failed_calls.append(prepared['event']['event_id'])
            raise RuntimeError('authored local observer failed after reservation')
        refuse('failed-observer-cost-retained',lambda:delivery.observe_current_budgeted_semantic_input(
            budget_owner=failed_owner,event_id='failed.initial',kind='initial',context_packet=packets['view'],
            local_observer=failing,**common,**basis))
        failed_snapshot=failed_owner.snapshot()
        assert len(failed_calls)==1 and failed_snapshot['records'][0]['status']=='aborted'
        assert failed_snapshot['totals']['rendered_input_tokens']>0
        retried=attempt(failed_owner,'retry','failed.retry',retry_of='failed.initial',retry_instruction='Retry the same review after the local failure.')
        save('failed-retry-delivery.json',retried)
        assert json.loads(retried['event']['rendered_input']['text'])['events'][0]['status']=='aborted'
        failed_owner.close();save('failure-trace.json',failed_owner.snapshot())
        # Public representations confer no original process-local control.
        refuse('serialized-budget-owner-refused',lambda:attempt(failed_snapshot,'initial','serialized.initial'))
        refuse('closed-budget-owner-refused',lambda:attempt(failed_owner,'retry','closed.retry',retry_of='failed.initial'))
        changed=head.to_dict();changed['generation']+=1
        refuse('wrong-complete-head-refused',lambda:delivery.observe_current_budgeted_semantic_input(
            budget_owner=owner(),event_id='wrong.initial',kind='initial',context_packet=packets['view'],
            **dict(common,expected_head=CodebaseHead.from_dict(changed)),**basis))
    with capacity.reserve_call_review_capacity(scheduler=scheduler,binding=binding,timeout_seconds=120) as control:
        refresh(control,'custody')
        # Retained original custody predates the first native renderer callback.
        original_renderer=delivery.native_runner.render_model_prompt
        source=repository/'caller.py';raw=source.read_bytes();held=RUN/'held-source.py';swaps=[]
        def swapped_renderer(**kwargs):
            if not swaps:
                source.rename(held);source.write_bytes(raw);source.chmod(0o644);swaps.append(True)
            return original_renderer(**kwargs)
        live=owner();n=len(calls)
        try:
            delivery.native_runner.render_model_prompt=swapped_renderer
            refuse('same-byte-source-replaced-on-native-renderer',lambda:attempt(live,'initial','source.initial'))
            assert swaps and not live.snapshot()['records'] and len(calls)==n
        finally:
            delivery.native_runner.render_model_prompt=original_renderer
            if held.exists():source.unlink();held.rename(source)
            live.close()
        obj=Path(model['caller_object']['path']);raw=obj.read_bytes();held=RUN/'held-proof.olean';swaps=[]
        def swapped_observer(text,prepared):
            obj.rename(held);obj.write_bytes(raw);obj.chmod(0o600);swaps.append(True)
        live=owner()
        try:
            refuse('same-byte-proof-replaced-on-local-observer',lambda:delivery.observe_current_budgeted_semantic_input(
                budget_owner=live,event_id='proof.initial',kind='initial',context_packet=packets['view'],
                local_observer=swapped_observer,**common,**basis))
            assert swaps and live.snapshot()['records'][0]['status']=='aborted'
        finally:
            if held.exists():obj.unlink();held.rename(obj)
            live.close()
        save('proof-mutation-failure-trace.json',live.snapshot())
        # First capacity callback also occurs only after original source capture.
        probe=capacity.host_probes.collect_proof_host_resources
        source=repository/'caller.py';raw=source.read_bytes();held=RUN/'held-capacity-source.py';swaps=[]
        def swap_capacity_source():
            if not swaps:
                source.rename(held);source.write_bytes(raw);source.chmod(0o644);swaps.append(True)
            return probe()
        live=owner()
        try:
            capacity.host_probes.collect_proof_host_resources=swap_capacity_source
            refuse('same-byte-source-replaced-on-first-capacity-callback',lambda:attempt(live,'initial','capacity.initial'))
            assert swaps and not live.snapshot()['records']
        finally:
            capacity.host_probes.collect_proof_host_resources=probe
            if held.exists():source.unlink();held.rename(source)
            live.close()
    with capacity.reserve_call_review_capacity(scheduler=scheduler,binding=binding,timeout_seconds=120) as control:
        refresh(control,'late')
        # Mutation by the final capacity callback must not escape publication.
        original_public=capacity.CallReviewCapacity.public_dict
        generation=model['head']['generation'];mutated=[];checked=[]
        def mutate_input_late(owner_value):
            public=original_public(owner_value)
            frame=sys._getframe(1)
            if frame.f_globals.get('__name__')==delivery.__name__ and frame.f_code.co_name=='check':
                checked.append(True)
                if len(checked)==7:
                    model['head']['generation']+=1;mutated.append(True)
            return public
        live=owner()
        try:
            capacity.CallReviewCapacity.public_dict=mutate_input_late
            refuse('input-mutation-after-final-scope-capacity-callback-refused',lambda:attempt(live,'initial','late.initial'))
            assert mutated,controls[-1]
        finally:
            capacity.CallReviewCapacity.public_dict=original_public
            model['head']['generation']=generation
            live.close()
        assert live.snapshot()['records'][0]['status']=='committed'
        save('late-input-failure-trace.json',live.snapshot())
        review.resolve_current_semantic_audit_reference=original_resolver
    refused_owner=owner()
    refuse('released-capacity-refused',lambda:attempt(refused_owner,'initial','released.initial'))
    assert not refused_owner.snapshot()['records'];refused_owner.close()
    prepared_guard();model_guard();callee_guard();policy_guard();profile_guard()
    resources=scheduler.snapshot()
    assert resources['active_lease_count']==0 and resources['waiting_request_count']==0
    summary={'schema':'terminal-semantic-context-budget-live-experiment@1','qualified':True,
        'head':head.to_dict(),'selected_budget_binding':json.loads((RUN/'budget-binding.json').read_bytes()),'budget_policy':budget_policy.to_dict(),
        'traces':traces,'local_observer_calls':calls,'actual_current_expansion_calls':expansion_calls,
        'controls':controls,'policy_observation_count':len(observations),'resources_after':resources,
        'native_basis_equal':True,'native_projection_equal':True,'parallel_forecast_equal_except_explicit_time_identity':True,
        'selected_task_ids':results['view']['selected_task_ids'],'admitted_execution_width':0,
        'native_planning_renderer_used':True,'native_worker_observer_used':False,'full_supervisor_entrypoint_used':False,
        'global_task_budget_enforced':False,'durable_budget_resume_supported':False,
        'independent_counterfactual_traces':True,'capacity_scopes':['main','failure','custody','late'],
        'provider_calls':0,'provider_output_tokens':None,'provider_usage_measured':False,'provider_savings_measured':False,
        'training_steps':0,'source_body_executed':False,'runtime_behavior_verified':False,
        'source_origin_verified':False,'convergence_proved':False,'full_task_satisfaction':False,
        'project_commits':0,'project_pushes':0}
    save('summary.json',summary)
    print(json.dumps({'qualified':True,'traces':traces,'controls':len(controls),
        'current_expansion_calls':expansion_calls,'local_observer_calls':len(calls)}),flush=True)
finally:
    review.resolve_current_semantic_audit_reference=locals().get('original_resolver',review.resolve_current_semantic_audit_reference)
    connection.close()
