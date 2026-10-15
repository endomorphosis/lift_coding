"""Collect bounded public Stage Y results, without native jobs or storage reads."""
import hashlib,json,os
from pathlib import Path
Y=Path(__file__).resolve().parent
os.umask(0o077)
def read(name):return json.loads((Y/name).read_bytes())
def pin(p):
 r=p.read_bytes();return {'path':str(p),'bytes':len(r),'sha256':hashlib.sha256(r).hexdigest()}
def save(name,value):
 with (Y/name).open('x') as f:json.dump(value,f,sort_keys=True,indent=2,allow_nan=False);f.write('\n')
tests=read('test-final-run.json');a=read('preview-run-02/summary.json');p=read('package-report.json')
assert tests['tests']==tests['unique_identities']==162 and tests['exit_code']==tests['failures']==tests['errors']==tests['skipped']==0
assert tests['all_sources_unchanged'] and a['qualified'] and len(a['controls'])==13 and all(x['rejected'] for x in a['controls'])
assert a['traces']['expanded']['initial_tokens']==70977 and a['traces']['view']['initial_tokens']==47215
assert a['traces']['view']['totals']['rendered_input_tokens']==95678
assert a['actual_current_expansion_calls']==['native_block']
assert a['resources_after']['active_lease_count']==a['resources_after']['waiting_request_count']==0
assert p['source_count']==4 and p['patch_check_passed'] and p['patch_exact_apply_passed']
for f in tests['sources_after']:assert f==pin(Path(f['path']))
q=read('actual-public-budget-01/qualification-summary.json')
assert q['model_status']=='model_proved' and q['rows']==49 and len(q['families'])==20
scope={'native_planning_renderer_used':True,'native_worker_observer_used':False,
 'full_supervisor_entrypoint_used':False,'provider_calls':0,'provider_output_tokens':None,
 'provider_usage_measured':False,'provider_savings_measured':False,'worker_launched':False,
 'global_task_budget_enforced':False,'durable_budget_resume_supported':False,
 'training_steps':0,'source_body_executed':False,'runtime_behavior_verified':False,
 'source_origin_verified':False,'source_to_model_equivalence_proved':False,
 'convergence_proved':False,'full_task_satisfaction':False,'production_admitted':False,
 'project_commits':0,'project_pushes':0,'loaded_module_code_attested':False,
 'transitive_dependency_closure_attested':False}
report={'schema':'terminal-semantic-context-budget-qualification@1','qualified':True,
 'stage':'Y','selected_run':'preview-run-02','unique_tests':162,'live_negative_controls':13,
 'actual_fixture':'fresh authored three-module public repository, not a Terminal-Bench task or hidden oracle',
 'metadata_rows':49,'metadata_families':20,'fresh_lean_process_invocations':3,
 'proof_scope':'conditional unbounded-integer closed caller model; unsupported dynamic source stays residual',
 'budget_policy':a['budget_policy'],'main_trace_binding':a['selected_budget_binding'],
 'initial_native_rendered_input_tokens':{'expanded':70977,'view':47215},
 'initial_new_content_tokens':{'expanded':57379,'view':43189},
 'view_plus_one_actual_registered_block':a['traces']['view']['totals'],
 'remaining_rendered_input_tokens_after_block':100000-95678,
 'whole_rendered_history_counted_each_turn':True,'aborted_attempts_remain_charged_and_visible':True,
 'all_expansion_request_response_instruction_counted_once_as_new_content':True,
 'initial_comparison_shares_complete_head_view_reference_capacity_and_native_basis':True,
 'cumulative_task_token_savings_measured':False,
 'trace_comparison_limit':'Initial input comparison only. Expanded and view traces have different admitted turn counts; no equivalent completed-task or provider saving is asserted.',
 'preflight_boundary':'Trusted pure native planning preparation occurs before reservation to measure exact bytes. Hard cumulative preflight precedes actual current expansion and local observer callbacks.',
 'native_single_input_byte_limit':256000,'fixed_cumulative_rendered_input_token_limit':100000,
 'native_conditional_review_tasks_unchanged':a['selected_task_ids'],'admitted_execution_width':0,
 'normal_local_observer_probes':len(a['local_observer_calls']),
 'fault_injected_local_observer_attempts':2,'all_local_observer_attempts':7,
 'actual_current_expansions':a['actual_current_expansion_calls'],
 'all_expected_pins_unchanged':read('preservation-before-package.json')['all_expected_pins_unchanged'],
 'public_artifact_count':113,'preserved_pin_occurrences':296,'patch_bytes':p['patch']['bytes'],
 'capacity_scope':'Independent main/failure/custody/late original held native controls; maximum120seconds each; no serialized renewal or same-budget restart authority.',
 **scope}
save('qualification-report.json',report)
save('development-history.json',{'schema':'terminal-semantic-context-budget-development-history@1',
 'selected_final_sources':tests['sources_after'],'selected_final_run':'preview-run-02',
 'excluded_attempts':[
  {'name':'budget-focused-01','reason':'public snapshot binding alias found and fixed'},
  {'name':'budget-focused-02','reason':'copy-owner gap found and fixed before final qualification'},
  {'name':'budget-focused-03','reason':'atomic admission missing; superseded by57-test concurrency followup'},
  {'name':'agent-semantic-budget-delivery-00','reason':'producer path setup error before pytest/native imports'},
  {'name':'preview-run-01','reason':'late control did not execute before original120second capacity deadline; assertions failed. Superseded by separate authentic original capacity scopes in run02; root source/cold-custody/closing guards also finalized.'}],
 'original_sealed_stages_mutated':False,'errors_are_evidence_not_success':True})
save('improvement-status.json',{'schema':'terminal-semantic-context-budget-improvement-status@1',
 'completed':['Atomic process-local exact cumulative budgeting across all charged attempts',
 'Exact native planning rendering of complete ordered audit/expansion/retry histories',
 'Current source, conditional proof, fixed DuckDB metadata and policy custody before and after delivery',
 'Budget preflight before actual expansion and local observation; no refund after failed local delivery',
 'Independent initial representation comparison with unchanged native three-task review projection'],
 'next_gaps':[
 {'priority':1,'gap':'Supported supervisor-to-worker transport for the checked audit context and budget',
  'work':'Add an explicit admitted API in a new isolated dependency revision. Bind task CID, signed instruction, allocated worktree, verified container boundary, complete current head/reference basis and budget policy before runner use.',
  'acceptance':'Genuine supervisor prepare/resume route and native observe_model_input_only branch; independently captured final renderer bytes match native receipt hash/size; no forged boundary, monkeypatch or custom unadmitted CLI wrapper.'},
 {'priority':2,'gap':'Equivalent multi-turn task and provider usage evaluation',
  'work':'Run paired allowed public Terminal-Bench tasks with identical intent, current-source/proof coverage, tools, stop criteria and outcome checks. Capture whole model inputs, outputs, expansion counts, retries and authoritative provider usage including any allocation/CLI-added messages.',
  'acceptance':'Report total equivalent completed-task input/output/usage costs, not initial prompt size or local call-budget counters alone.'},
 {'priority':3,'gap':'Durable task-wide accounting across workers and restarts',
  'work':'Use one authenticated owner/admission ledger with atomic transactional reservations, replay/incomplete-history rejection, cancellation semantics and recovery custody. Snapshots in this stage remain offline data only.',
  'acceptance':'No reset via a new owner/process or serialized prefix; concurrent workers cannot exceed aggregate limits before external calls.'},
 {'priority':4,'gap':'Semantic sufficiency and source-to-model equivalence',
  'work':'Evaluate all required facts, dependency closures, unsupported constructs and logical projection preservation on real repositories; expand exact registered source when needed. Keep model assumptions and unproved runtime behaviors explicit.',
  'acceptance':'Separately checked equivalence claims with assumptions and coverage, without promoting embeddings, AST labels, compression or metadata retrieval into behavior proofs.'},
 {'priority':5,'gap':'On-the-fly CodebaseIR training and convergence',
  'work':'Introduce a genuine trainable repository encoder with versioned data/model provenance, held-out task/semantic reconstruction evaluation and explicit convergence criteria; join learned candidates to checked logic projections/proof index.',
  'acceptance':'Actual training traces and declared mathematical or empirical convergence evidence, separate from Lean compilation of a fixed conditional model.'}],
 'route_review':pin(Y/'entrypoint-model-input-review.json'),**scope})
print(json.dumps({'qualified':True,'tests':162,'controls':13,'whole_view_trace_tokens':95678,'provider_calls':0}))
