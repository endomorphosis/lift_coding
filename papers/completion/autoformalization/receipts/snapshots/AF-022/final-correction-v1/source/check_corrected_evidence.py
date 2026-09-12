#!/usr/bin/env python3
"""Check actual corrected scalar/source joins; no experiment or checkpoint load."""
import sys
sys.dont_write_bytecode=True
from pathlib import Path
import hashlib,json,math,collections,ast,importlib.util
P=Path(__file__).resolve().parents[2]
def read(rel):return json.loads((P/rel).read_bytes())
def digest(rel):return hashlib.sha256((P/rel).read_bytes()).hexdigest()
def require(value,label):
 if not value:raise ValueError(label)
checks=[]
def check(value,label):require(value,label);checks.append(label)
a=read('evidence/final_correction/actual_execution.json');s=read('results/summary.json');m=read('runs/native_training/manifest.json');sc=read('evidence/native_training/adoption_scalar_summary.json')
check(all(digest(p)==h for p,h in a['original_input_sha256'].items()),'all_actual_projection_original_input_hashes_match')
check(a['saved_training_completed'] is True and a['original_container_success'] is False and a['separate_retained_byte_checker_succeeded'] is True,'saved_training_success_does_not_rewrite_original_checker_OOM')
check([r['seed'] for r in a['t2']]==[104729,130363,155921] and all(r['accepted_epochs']==1 and r['applied_packed_updates']==5 and r['changed_numeric_parameters']==182500992 for r in a['t2']),'actual_three_T2_seeds_full_updates')
check([r['seed'] for r in a['t3']]==[104729,130363,155921] and all(r['applied_updates']==256 and r['eligible_labels']==2606 and r['protected_parameters_unchanged'] and r['scope']=='native_compiler_structural_contracts_only' for r in a['t3']),'actual_three_T3_seeds_structural_scope_isolation')
check(a['resources']==m['environment']['resource_limits'] and a['resources']['memory_gib']==64 and a['resources']['cpu_limit']==2 and a['resources']['complete_T2_wall_seconds']==10800 and a['resources']['whole_wall_seconds']==36000,'actual_amended_resource_profile_preserved')
check(s['corrected_actual_execution']==a and s['af029']['saved_training_completed'],'summary_uses_actual_adopted_execution')
rows=[json.loads(x) for x in (P/'runs/costs/results.jsonl').read_text().splitlines()]
def total(kind):return math.fsum(r['elapsed_seconds']['value'] for r in rows if r.get('record_kind')==kind and r.get('elapsed_seconds',{}).get('kind')=='measured')
check(math.isclose(total('source_usage'),481.585523993,abs_tol=1e-8) and math.isclose(total('phase_total'),total('source_usage'),abs_tol=1e-8) and math.isclose(s['cost_accounting']['measured_elapsed_seconds'],total('source_usage'),abs_tol=1e-8),'source_usage_equals_phase_projection_but_counted_only_once')
check(a['AF013']['diagnostics_total']==114 and a['AF013']['fixed_canaries_per_seed']==38 and all(v=='no_candidate' for v in a['AF013']['promotion_outcomes']) and a['AF013']['applied_learned_features'] is False and a['AF013']['E_locked'],'actual_114_native_canaries_no_candidate_unactivated')
check(a['AF013']['default_reset_is_applied_learning_rollback'] is False and a['AF013']['family_metrics_empty'],'no_empty_metric_or_reset_efficacy_inference')
check(s['original_placeholder_cells']==44 and s['remaining_placeholder_cells']==0 and len(s['table6']['cells'])==20 and len(s['table11']['cells'])==24,'all_44_primary_cells_preserved')
check(all(c['status'] in {'unrun','unavailable','unmeasured','measured_inventory'} for table in ['table6','table11'] for c in s[table]['cells']),'primary_final_cells_have_no_invented_measurements')
check(a['human_fidelity'] is None and a['human_agreement'] is None and not a['outside_human_review_required'],'human_fidelity_unknown_without_reviewer_gate')
tex=(P/'manuscript/main.tex').read_text();check('target-assisted' in tex and 'original container remains failed' in tex and 'T3 applied 256' in tex,'manuscript_actual_success_and_limitations_join')
check(not any(t in tex for t in ['T3 has no eligible native labels','T2 accepted $0$','963.171','unsupported sealed-\\texttt{PATH} T2 shared-learner update']),'stale_failure_and_duplicate_cost_claims_removed')
code=ast.parse((P/'evaluation/pipeline_arms.py').read_bytes());func=next(n for n in code.body if isinstance(n,ast.FunctionDef) and n.name=='execute_arm');locked=False
for n in func.body:
 if isinstance(n,ast.If):
  test=n.test.values[0] if isinstance(n.test,ast.BoolOp) else n.test
  if ast.dump(test)==ast.dump(ast.parse("arm_id == 'E'",mode='eval').body):locked=any(isinstance(x,ast.Return) and isinstance(x.value,ast.Call) and isinstance(x.value.func,ast.Name) and x.value.func.id=='unavailable_result' for x in n.body)
check(locked,'actual_E_executor_unconditional_refusal_preserved')
# Constructed negative uses the actual reducer API and only metadata copies.
sys.path.insert(0,str(P/'evaluation'));spec=importlib.util.spec_from_file_location('corrected_native_summary',P/'evaluation/analyze_results.py');mod=importlib.util.module_from_spec(spec);sys.modules[spec.name]=mod;spec.loader.exec_module(mod)
from copy import deepcopy
bad=deepcopy(m);bad['arms']['T2']['packed_cpu'][0]['accepted_epochs']=0
try:mod.native_training_notes(bad,sc)
except ValueError:checks.append('constructed_zero_epoch_cannot_be_promoted_to_actual_completion')
else:raise AssertionError('Zero epoch accepted')
# Source-only constructor/export checks: no native imports or checkpoint allocation.
native=P.parents[2]/'external/ipfs_datasets/ipfs_datasets_py/optimizers/logic_theorem_optimizer/modal_autoencoder.py'
nt=ast.parse(native.read_bytes());classes={n.name:n for n in nt.body if isinstance(n,ast.ClassDef)}
model=classes['AdaptiveModalAutoencoder'];init=next(n for n in model.body if isinstance(n,ast.FunctionDef) and n.name=='__init__')
kw={a.arg for a in init.args.kwonlyargs}
check('state' in kw and 'training_state' not in kw and 'AdaptiveModalAutoencoder(state=state)' in (P/'artifact/README.md').read_text(),'source_guide_uses_actual_native_keyword_only_state_constructor')
check(any(isinstance(n,ast.FunctionDef) and n.name=='from_dict' for n in classes['ModalAutoencoderTrainingState'].body) and any(isinstance(n,ast.FunctionDef) and n.name=='export_deterministic_ir_guidance_features' for n in model.body),'source_guide_state_loader_and_structural_export_exist')
feedback=read('evidence/final_correction/feedback_status.json')
check(len(feedback['rows'])==69 and dict(collections.Counter(r['status'] for r in feedback['rows']))==feedback['counts']=={'checked':61,'timeout':6,'unsupported_fragment':2} and feedback['coverage']['admitted_records']==2606 and '61 checked' in tex and '6 timed-out' in tex,'all_69_final_feedback_statuses_bound_to_final_inventory_not_prior_OOM')
print(json.dumps({'schema':'af-final-correction-evidence-check/v1','ok':True,'checks':checks,'checks_passed':len(checks),'no_new_experiment':True},sort_keys=True,indent=2))
