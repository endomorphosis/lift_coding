"""Summarize final named evidence and retain explicit limits and next gates."""
import hashlib,json,os
from pathlib import Path
Z=Path(__file__).resolve().parent;os.umask(0o077)
def load(name):return json.loads((Z/name).read_bytes())
def pin(name):
 p=Z/name;b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def save(name,value):
 with (Z/name).open('x') as f:json.dump(value,f,sort_keys=True,indent=2);f.write('\n')
test=load('final-combined-02-report.json');package=load('review-package-02.json')
assert test['qualified_combined_test_run'] is True and test['exit_code']==0
assert test['test_counts']['tests']==test['test_counts']['unique_tests']
assert all(test['test_counts'][k]==0 for k in ('failures','errors','skips'))
assert test['producer_bytes_unchanged'] and test['changed_path_population_unchanged'] and test['suite_bytes_unchanged']
assert package['counts']['source_files']==14 and package['independent_apply']['exact_all_source_bytes'] is True
assert package['independent_apply']['exact_all_git_executable_modes'] is True
assert package['independent_apply']['git_apply_check']['returncode']==package['independent_apply']['git_apply']['returncode']==0
assert package['original_preservation']['index_unchanged'] and package['original_preservation']['source_pins_unchanged']
for required in ['checked-worker-run-04/summary.json','actual-public-checked-01/qualification-summary.json','coding-input-comparison-02.json','deployed-runtime-source-pins-02.json','native-worker-public-readback-02.json','native-task-final-readback-02.json','container-disposal-02.json','actual-public-inventory.json','preservation-final.json','offline-duckdb-prerequisite.json']:
 pin(required)
ceilings={'provider_calls':0,'provider_usage_measured':False,'provider_savings_measured':False,
 'task_total_savings_measured':False,'source_body_executed':False,'training_steps':0,
 'source_to_model_equivalence_proved':False,'convergence_proved':False,
 'full_task_satisfaction':False,'full_supervisor_entrypoint_used':False,
 'Terminal_Bench_harness_used':False,'global_task_budget_enforced':False,
 'durable_budget_resume_supported':False,'completion_authority':False,
 'proof_authority':False,'omission_authority':False,'production_admitted':False,
 'loaded_module_code_attested':False,'transitive_dependency_closure_attested':False,
 'database_bodies_included':False,'private_cas_bodies_included':False,
 'ducklake_parquet_bodies_included':False,'project_pushes':0}
status={'schema':'terminal-checked-worker-context-improvement-status@1',**ceilings,
 'qualified_this_stage':[
  'Closed version2 checked-context observation on one real isolated native coding worker, preserving legacy version1.',
  'Exact signed native three-source inventory joins to the current datasets CodebaseIR snapshot; literal task instruction separately signed and retained.',
  'Owner retains current source, proof, producer and metadata guards; worker receives an immutable public artifact carrying explicit assumptions and unsupported residuals.',
  'Original process-local owner reserves the complete coding-input charge before actual launch; an over-budget retry is refused before worker invocation.',
  'Root-protected observer deployment uses no provider assets and a real distinct kernel worker UID/namespace boundary.',
  'Genuine coding-input replay after allocated worktree removal requires the unchanged canonical source and instruction.',
  'Fresh authored conditional caller model has49 public metadata rows across20 families and3 successful Lean processes.'
 ],
 'next_ordered_gaps':[
  {'priority':1,'gap':'Authenticated owner authorization after native runtime allocates the worktree',
   'implementation':'Add a narrow prelaunch hook to the admitted runtime between allocation and native spawn. The original owner verifies allocated canonical path, signed task/attempt identity, current snapshot and original proof custody, renders exact full coding input, and reserves budget before authorizing the protected worker command.',
   'authorization_binding':['launch_nonce','task_cid','admission_cid','allocated_worktree','kernel_boundary','current_codebase_head','checked_extension_sha256','full_input_sha256','event_cid','budget_owner_instance'],
   'acceptance':'One actual AdmittedBenchmarkRuntime START with matching protected launch identity and exactly one bounded observation; stale head, swapped worktree, replayed nonce, changed artifact and exceeded budget all refuse before spawn.',
   'current_limit':'This stage uses controlled Docker owner exec and a manually owner-allocated worktree. Generic callback and receipt data cannot confer native child origin.'},
  {'priority':2,'gap':'Durable task budget and full supervisor integration',
   'implementation':'Place authoritative task budgets in the supervisor owner transaction path with single-writer compare-and-swap semantics, crash reconciliation of uncertain launches, monotone charges, idempotent event IDs and authenticated resume. Include all planning/coding/retry/expansion/history inputs and subsequent provider usage.',
   'acceptance':'Concurrent owners cannot both spend the same remaining allowance; crash-after-spawn and cancellation preserve charge; restart does not revive serialized controls; Harbor/Terminal-Bench dispatch matches the same signed task and observed input.',
   'current_limit':'Local RLock/HMAC owner is process-local. Z counts complete single coding inputs without claiming chat-history delivery or actual billing.'},
  {'priority':3,'gap':'Repository-scale incremental CodebaseIR and proof-cache hydration',
   'implementation':'Scan the actual repository under test into source spans, AST, symbols, imports, calls, KG, vectors, contracts, unsupported features and provenance. Store authoritative revision identities in DuckDB/DuckLake; use quack as a bounded retrieval interface. Cache explicit checked facts separately from learned suggestions.',
   'cache_key':['repository_snapshot_cid','source_digest_and_span','parser_and_extractor_versions','codebase_ir_schema','projection_version','toolchain_and_options','assumption_set','dependency_proof_digests'],
   'acceptance':'Cold and warm queries return the same typed results; dependency changes invalidate affected proof closures; stale heads and incomplete metadata cannot authorize omission; raw source remains available for unsupported/dynamic code.',
   'current_limit':'The passing fixture has three authored Python modules and a separate public instruction. Public hashes do not prove private-store contents or whole-repository scan completeness.'},
  {'priority':4,'gap':'IntentIR grounding and symbolic planning',
   'implementation':'Compile user intent into typed objectives, preconditions, effects, constraints and acceptance obligations. Resolve references against the current CodebaseIR and retrieve bounded relevant capsules. The symbolic planner must preserve explicit unresolved predicates and produce dependency-linked actions with per-action proof and validation requirements.',
   'acceptance':'Ambiguous or unsupported intent remains unresolved; a stale codebase reference cannot satisfy an intent predicate; planning decisions have replayable snapshot/query/assumption evidence and respect cumulative token policy.'},
  {'priority':5,'gap':'Real on-the-fly codebase representation training',
   'implementation':'Add a versioned autoencoder training adapter over public benchmark source/AST/graph samples. Split by task/repository to avoid leakage; pin model initialization, tokenizer, seeds, optimizer and data order. Log reconstruction, retrieval and contract prediction losses, checkpoints and held-out behavior. Learned output remains a proposal until checked.',
   'acceptance':'A genuine run takes nonzero optimizer steps, can resume reproducibly, improves held-out retrieval or reconstruction over a specified baseline, and never promotes a predicted contract to a proved fact.',
   'current_limit':'No autoencoder has been trained in this stage. Metadata vectors are not evidence of learned convergence.'},
  {'priority':6,'gap':'Source-to-model semantics and logic-family compiler coverage',
   'implementation':'Define a precise supported language fragment and executable semantics, connect AST extraction to typed CodebaseIR, and validate each logic-family projection with a checker appropriate to its semantics. Prove translation correctness under explicit integer, import and call assumptions before using resulting theorems to authorize changes.',
   'acceptance':'The admitted supported fragment has a checked source/model relation; integer/domain mismatches and eval/dynamic imports yield explicit residual obligations; Lean compilation is attributed only to the exact generated theorem and toolchain.',
   'current_limit':'Three successful Lean processes prove the closed mathematical caller model; they do not establish Python execution equivalence or compilation of every metadata family.'},
  {'priority':7,'gap':'Convergence and full task satisfaction',
   'implementation':'Distinguish measured optimization stabilization from a theorem of convergence. For theorem claims specify objective, update rule and all analytic assumptions. Complete real benchmark edits and required validations, then measure task success, total input/output tokens, retries and wall time against matched baselines.',
   'acceptance':'All declared task acceptance checks pass on the current source revision with provenance, and any convergence theorem names its algorithm and assumptions. Full-task token savings require complete comparable runs.',
   'current_limit':'The native task remains ready with pending checks, unchanged revision and watermark. It has not been completed.'}
 ],
 'publication_status':'Isolated source/test review package only; no project GitHub or Hugging Face publication.'}
save('improvement-status.json',status)
history={'schema':'terminal-checked-worker-context-development-history@1',**ceilings,
 'selected_actual_run':'checked-worker-run-04','development_failures_retained_and_excluded':True,
 'attempts':[
  {'attempt':'checked-worker-run-01','selected':False,'worker_invocations':1,'provider_calls':0,
   'outcome':'Native loader refused allocated directory mode3770 before observation. Actual worker access requires group traversal, while canonical protected files retain their separate checks.',
   'fix':'Allocated parent read mask005 changed to050 only for allocated inputs; exact3770/2770/660 regression added, final71 tests passed.',
   'cleanup':'Explicit failure cleanup and worktree removal passed.',
   'budget_state_limit':'Old experiment driver did not export the failed owner ledger before process exit. No retained charged-state verification is claimed for this attempt.'},
  {'attempt':'checked-worker-run-02','selected':False,'worker_invocations':0,'provider_calls':0,
   'outcome':'Owner setup snippet had an indentation error before worktree creation or worker launch. Zero-event final budget snapshot retained.',
   'fix':'Dedented the three standalone owner snippets; production code unchanged.'},
  {'attempt':'checked-worker-run-03','selected':False,'worker_invocations':1,'provider_calls':0,
   'outcome':'Native exit75 observed exact checked coding input; retry and byte-bound controls, replay and cleanup passed. Superseded by final-source run04 after malformed-schema compatibility fixes.'}
  ,{'attempt':'checked-worker-run-04','selected':True,'worker_invocations':1,'provider_calls':0,'outcome':'Final frozen production source, fresh native signed fixture05 and boundary02, actual checked observer exit75; both refusal controls, replay and cleanup passed.'}
 ],
 'final_regression_repair':{'failed_attempt':'final-combined-01','passed_attempt':'final-combined-02','reason':'Malformed schema list/dict values raised TypeError in the collector. Added exact string gates before supported-version membership in collector, validator and observer stop; added four fast invalid-schema tests. Final1046 tests all pass.'},
 'reproduction_prerequisite':{'failed_fixture':'native-fixture-04','selected_fixture':'native-fixture-05','reason':'Fresh owner HOME lacked DuckLake extension cache. Explicitly copied only public ducklake/httpfs/quack binaries from cached image and validated native offline LOAD ducklake. No production fallback or disabled check.', 'receipt':pin('offline-duckdb-prerequisite.json')},
 'other_development_attempts':'Focused extension/native integration/profile fixtures and first native source preparation failures are retained in their original named attempt files. Only final frozen-source qualification is counted.',
 'task_unchanged':pin('native-task-final-readback-02.json'),'container_disposal':pin('container-disposal-02.json')}
save('development-history.json',history)
actual=load('checked-worker-run-04/summary.json');model=load('actual-public-checked-01/qualification-summary.json');comparison=load('coding-input-comparison-02.json')
qualification={'schema':'terminal-checked-worker-context-qualification@1',**ceilings,
 'qualified':True,'selected_actual_run':'checked-worker-run-04',
 'actual_native_worker_observer_invocations':1,'native_worker_observer_used':True,
 'native_admitted_benchmark_runtime_START_used':False,'worker_uid':1001,'owner_uid':1000,
 'native_observation_schema':'supervisor-model-input-observation@2','native_observer_exit_code':75,
 'whole_coding_input':actual['whole_coding_input'],'new_content':actual['new_content'],
 'local_counterfactual_comparison':comparison,'budget_policy':actual['budget_policy'],
 'actual_budget_totals':actual['totals'],'live_controls':actual['controls'],
 'model_status':model['model_status'],'metadata_rows':model['rows'],'metadata_family_count':len(model['families']),
 'fresh_Lean_processes':3,'logic_proof_scope':'Authored closed conditional arithmetic caller model. No whole-program Python equivalence or all-family compiler coverage claim.',
 'unique_tests':test['test_counts']['unique_tests'],'test_failures':0,'test_errors':0,'test_skips':0,
 'packaged_source_test_files':14,'patch_exact_application_verified':True,
 'tests':pin('final-combined-02-report.json'),'package':pin('review-package-02.json'),
 'source_readback':pin('deployed-runtime-source-pins-02.json'),'public_artifact_readback':pin('native-worker-public-readback-02.json'),
 'native_task_final_readback':pin('native-task-final-readback-02.json'),'container_disposal':pin('container-disposal-02.json'),
 'public_inventory':pin('actual-public-inventory.json'),'preservation':pin('preservation-final.json'),
 'selected_actual_summary':pin('checked-worker-run-04/summary.json'),
 'scope':'One direct controlled Docker native observer with an original host owner budget. Not admitted supervisor START, full supervisor, Harbor or Terminal-Bench execution.',
 'replay_limit':'Historical full-input replay requires unchanged canonical source and literal instruction, even after the allocated worktree is removed.',
 'transport_limit':'Only the strict native/expanded/inline observer coding profile accepts checked context. Other transport combinations refuse.',
 'independent_audit':'Separate source-import-free audit and final evidence manifest follow this declaration of readiness.'}
save('qualification-report.json',qualification)
print(json.dumps({'qualified':True,'tokens':actual['whole_coding_input']['tokens'],'local_counterfactual_tokens':comparison['expanded_counterfactual']['tokens'],'metadata_rows':model['rows']}))
