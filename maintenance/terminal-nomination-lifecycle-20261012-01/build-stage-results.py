"""Summarize only selected tests and explicit public lifecycle artifacts."""
import hashlib
import json
import math
from pathlib import Path

M=Path(__file__).resolve().parent
def read(name):return json.loads((M/name).read_bytes())
def pin(name):
    raw=(M/name).read_bytes()
    return {'path':name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
def write(name,value):
    assert not (M/name).exists()
    (M/name).write_text(json.dumps(value,sort_keys=True,indent=2)+'\n')

focused=read('final-focused-validation.json');preserved=read('preservation-check.json');sources=read('source-manifest.json')
assert focused['all_selected_cases_passed'] and focused['distinct_cases']==655 and preserved['all_checks_passed']
attempts=[]
for number in (1,2,3):
    prefix='actual-harbor-lifecycle-'+str(number).zfill(2)
    q=read(prefix+'/qualification.json');l=q.get('lifecycle',{});reports=q.get('named_report_export',{}).get('reports',{})
    summary={'attempt':number,'qualified':q['qualified'],'receipt':pin(prefix+'/qualification.json'),
      'final_runtime_generation':number!=1,'actual_harbor_sdk_environment':q['actual_harbor_sdk_environment'],
      'environment_call_counts':q['environment_call_counts'],'fresh_container_removed':q.get('fresh_container_removed'),
      'same_prepared_owner_reused':True if len(l.get('phases',[]))==2 else None,
      'lifecycle_failure':l.get('failure'),'setup_seconds':l.get('setup_seconds'),
      'total_controller_seconds':l.get('total_controller_seconds'),'phases':[]}
    for phase in ('prepare_only','resume'):
        r=reports.get(phase,{})
        row={'phase':phase,'active_budget':r.get('active_budget'),'named_report_sha256':r.get('sha256')}
        export_path=prefix+'/lifecycle/'+phase+'-public-report.json'
        if (M/export_path).exists():
            export=read(export_path)
            row.update(observation_count=export.get('observation_count'),provider_invocation_count=export.get('provider_invocation_count'),
              start_status=export.get('start_status'),stop_status=export.get('stop_status'),remaining_processes=export.get('remaining_processes'),
              worker_cleanup_returncode=export.get('worker_cleanup_returncode'),
              unreceipted_model_input_observation_present=export.get('unreceipted_model_input_observation_present'),
              task_completed=export.get('task_completed'),same_owner_resume=export.get('source_nomination_resume'))
        learner=r.get('codebase_autoencoder') or {};metrics=learner.get('metrics') or {}
        if learner:
            losses=metrics.get('native_objective_losses',[])
            row['training']={'source_count':learner['source_count'],'sample_count':learner['sample_count'],
              'epochs_completed':learner['epochs_completed'],'training_elapsed_seconds':learner['training_elapsed_seconds'],
              'before_reconstruction_loss':metrics['before_reconstruction_loss'],'after_reconstruction_loss':metrics['after_reconstruction_loss'],
              'native_kernel_calls':metrics['native_kernel_calls'],'holdout_evaluated':metrics['holdout_evaluated'],
              'finite_recorded_objective_losses':all(math.isfinite(x) for x in losses),
              'recorded_objective_nonincreasing':bool(losses) and all(a>=b for a,b in zip(losses,losses[1:])),
              'candidate_only':learner['authority']=='unverified_candidate_only','global_model_convergence_proved':False}
        for key in ('phases','native_diagnostics','task_state','implementation_route','unavailable_settlement','model_input_observation_audit'):
            if r.get(key) is not None:row[key]=r[key]
        summary['phases'].append(row)
    attempts.append(summary)

baseline=read('actual-harbor-lifecycle-02/lifecycle/baseline.json')
requirements=baseline['requirements']
assert len(requirements)==19 and all(r['residual'] is True for r in requirements)
result={'schema':'nomination-lifecycle-stage-result@1','source_package':pin('source-manifest.json'),
 'changes_patch':pin('changes.patch'),'focused_validation':pin('final-focused-validation.json'),
 'preservation':pin('preservation-check.json'),'source_files':14,'runtime_production_files':8,'host_test_files':6,
 'distinct_selected_test_cases':655,'duplicate_refresh_cases_not_recounted':55,'public_preservation_pin_checks':806,
 'changes':[
  'Preparation and resume debit one original active-processing cap; review waits do not reset it.',
  'One retained environment drives the actual prepare/review/resume CLIs with independently pinned public inputs.',
  'An explicit worker observation mode renders and guards inputs before provider discovery, with a distinct receipt and CLI exit75.',
  'Separate receipt validation and historical input replay verify rendering without manufacturing provider invocations or usage.',
  'Successful materialized observations require verified wire custody and cleanup; legacy provider audit behavior remains unchanged.'],
 'actual_harbor_attempts':attempts,'actual_retained_observer_lifecycle_qualified':any(a['qualified'] for a in attempts if a['final_runtime_generation']),
 'all_nineteen_public_requirements_residual':True,'mandatory_residual_requirements':17,'nonmandatory_residual_requirements':2,
 'local_original_recipe_arm64_image_used':True,'upstream_published_image_digest_equivalence_qualified':False,
 'task_resource_limits_scope':'Original task configuration values; measured kernel resource conformity is not retained.',
 'setup_target_imports_or_execution_instrumented':False,
 'actual_provider_invocation_or_billing_population_complete':False,'actual_provider_calls':None,
 'provider_total_session_token_savings_established':False,'task_verifier_or_solution_read_hashed_or_executed':False,
 'whole_entrypoint_or_official_wall_budget_qualified':False,'phase_report_publication_in_active_charge':False,
 'source_to_model_equivalence_proved':False,'full_task_satisfaction_established':False,'model_global_convergence_proved':False,
 'actual_prover_invocation_population_measured':False,'direct_owner_key_inspection_or_export':False,
 'existing_dirty_root_checkout_or_git_index_mutated':False,'remote_publication_performed':False}
write('result-summary.json',result)
write('next-work.json',{'schema':'nomination-lifecycle-next-work@1','priorities':[
 {'priority':1,'work':'Locate and qualify the native worker dispatch boundary using retained phase timing, final task state and bounded completed-pass diagnostics.',
  'acceptance':'One genuine observer packet, exact source/capsule/whole-input reconstruction, original cumulative cap, clean STOP and no provider or completion authority.'},
 {'priority':2,'work':'Derive repository IR facts from signed AST, symbols, calls, contracts and dependency closure; classify learned autoencoder output as candidates.',
  'acceptance':'Each fact identifies its source bytes, extraction version and explicit supported semantics; missing or unsupported facts remain residual.'},
 {'priority':3,'work':'Index verified proof results in DuckDB/DuckLake with dependencies on source, IR, projection, assumptions and proof-checker versions.',
  'acceptance':'Reuse only exact compatible checked proofs; changed dependencies invalidate affected facts and obligations before planning.'},
 {'priority':4,'work':'Project supported code and intent IR into existing logic families and Lean obligations, then check compiler output and source correspondence separately.',
  'acceptance':'A compiled theorem is counted only for its stated source mapping and assumptions; syntax compilation does not establish behavioral equivalence.'},
 {'priority':5,'work':'Evaluate finite training stability and held-out behavior separately from global convergence, with explicit objectives and stopping rules.',
  'acceptance':'Replayable finite loss and gradient traces, held-out evaluation, supported convergence assumptions, and no upgrade from decreasing training loss to global proof.'},
 {'priority':6,'work':'Measure capsules, code transport and reversible minification in matched full supervisor sessions.',
  'acceptance':'Retain every mandatory requirement and dependency, check exact decoding where promised, and compare total native provider usage, task success and runtime including tool overhead.'}],
 'current_gap':'Actual retained resume has not yet been demonstrated to yield a clean valid worker model-input observation; consult the final attempt receipt.',
 'provider_or_task_success_inferred_from_metadata_or_training_loss':False})
print(json.dumps({'tests':655,'preservation_checks':806,'final_lifecycle_qualified':result['actual_retained_observer_lifecycle_qualified']}))
