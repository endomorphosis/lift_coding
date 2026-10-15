"""Record measured tradeoffs, successor gates and a public-artifact integrity seal."""
import json
import os
from pathlib import Path
from capsule_io import ROOT,FALSE,inputs,read,write,wire,pin,sha

def main():
 result=json.loads(read(ROOT/'experiment-04/result.json'))
 contexts=json.loads(read(ROOT/'experiment-04/context-costs.json'))
 tests=json.loads(read(ROOT/'regression-04-process-report.json'))
 process=json.loads(read(ROOT/'experiment-04-process-report.json'))
 cold=json.loads(read(ROOT/'experiment-04-cold-03-cold-report.json'))
 cold_process=json.loads(read(ROOT/'experiment-04-cold-03-process-report.json'))
 faults=json.loads(read(ROOT/'native-faults-01.json'))
 if not all(p['qualified'] is True for p in [tests,process,cold,cold_process,faults]):raise ValueError('qualified local evidence required')
 if tests['tests']!={'tests':145,'failures':0,'errors':0,'skipped':0}:raise ValueError('complete selected regression required')
 for entry in cold_process['after']:
  if pin(Path(entry['path']))!=entry:raise ValueError('final cold producer drift')
 summaries=[];totals={}
 for task in contexts['tasks']:
  rows=[]
  for scenario in task['scenarios']:
   measurement=scenario['measurement'];baseline=measurement['baseline']['totals']['total_tokens']
   compact=measurement['compact']['totals']['total_tokens'];key=(scenario['arm'],scenario['scenario'])
   total=totals.setdefault(key,{'baseline_tokens':0,'candidate_tokens':0,'signed_difference':0})
   total['baseline_tokens']+=baseline;total['candidate_tokens']+=compact;total['signed_difference']+=baseline-compact
   rows.append({'arm':scenario['arm'],'scenario':scenario['scenario'],'baseline_local_tokens':baseline,
    'candidate_local_tokens':compact,'signed_difference':baseline-compact,
    'provider_usage':None,'source':'declared counterfactual full-message script'})
  summaries.append({'task_id':task['task_id'],'scenarios':rows,
   'native_reserved_input_tokens':{k:p['native_reserved_input_tokens'] for k,p in task['projections'].items()},
   'expanded_context_local_bpe_tokens':{k:p['rendered_local_bpe_tokens'] for k,p in task['projections'].items()}})
 aggregate=[{'arm':arm,'scenario':scenario,**v,'signed_local_reduction':v['signed_difference']/v['baseline_tokens'],
  'observed_provider_savings':None} for (arm,scenario),v in sorted(totals.items())]
 minified=totals[('minified','one_turn')];aliased=totals[('aliased','one_turn')]
 decision='Keep compression experimental. Full-source minification saves less than one percent here; NAME alias dictionaries cost more, and raw-source expansion erases the gains.'
 status={'schema':'terminal-source-capsule-improvement-status@1','completed_milestone':True,'selected_run':'experiment-04',
  'native_head':result['native_head'],'genuine_generic_native_capsules':result['native_capsule_inventory'],
  'original_256_edge_adapter_refusal_preserved':result['old_adapter_refusal'],
  'metadata_original_record_counts':result['metadata_original_record_counts'],'native_shared_admission':True,
  'native_structural_context_and_plan_materials_exercised':True,'native_context_compiler_exercised':True,
  'all_10_original_source_roundtrips_byte_exact':True,'all_12_contexts_preserve_required_sources_and_full_instructions':True,
  'all_32_counterfactual_pairs_cold_reproduced':True,'all_instruction_requirements_unresolved':True,
  'residual_span_unit':'utf8_bytes','no_source_omission_enabled':True,'raw_source_required_before_edit_or_proving':True,
  'local_one_turn_minification':minified,'local_one_turn_aliases':aliased,
  'local_minification_reduction_fraction':minified['signed_difference']/minified['baseline_tokens'],
  'aggregate_counterfactual_costs':aggregate,'per_task_costs':summaries,'provider_usage':None,
  'actual_provider_invocations':0,'actual_terminal_bench_outcomes':None,'cache_reuse_credit':0,
  'compression_promoted_to_supervisor_default':False,'promotion_decision':decision,
  'unique_selected_tests':145,'genuine_live_negative_controls':faults['controls'],
  'mid_callback_source_change_refused_before_candidate_return':True,'all_fault_bodies_restored':True,
  'positive_cold_after_faults_qualified':True,'new_optimizer_updates':0,'new_lean_or_backend_invocations':0,
  'unexecuted_archived_policy_proposal':'archived_policy.py; original matching-live-source loader remained in use',
  'source_body_execution':False,**FALSE}
 write(ROOT/'improvement-status-01.json',status)
 plan={'schema':'terminal-codebase-intent-ir-improvement-plan@5','measured_decision':decision,
  'next_work':[
   {'priority':1,'id':'token-aware-lossless-semantic-reference-packing',
    'reason':'Simple code minification contributes only192localtokens of24125; repetitive source/head/capsule identifiers and framing dominate overhead.',
    'implementation':['Measure invariant core, complete source views, capsule metadata, opaque identities and message framing separately without changing the required evidence set.',
     'Evaluate native lossless dictionary transport against complete canonical contexts, charging inline dictionary and decoder instructions.',
     'If native byte-oriented selection increases BPE tokens, build a distinctly versioned token-aware candidate; leave pinned native limits and validators unchanged.',
     'Intern repeated path/CID/metadata references rather than rewriting Python names; exact expansion must restore all original values, types, ordering and requiredness.',
     'Bind codec, complete native head, metadata/capsule root and source footprints; reject unknown or changed references before downstream planning.'],
    'acceptance':['Whole serialized local BPE cost must fall under source-complete paired scenarios; report cases with higher cost.',
     'Count setup and every subsequent expansion/history/retry; byte reduction alone is insufficient.',
     'Transport reduction does not qualify provider token savings if the worker expands the full payload before model delivery.']},
   {'priority':2,'id':'complete-intent-coverage-before-relevance-based-source-selection',
    'implementation':['Decode complete public instructions into native IntentIR goals, guards, prohibitions, effects, numeric bounds and source-span-accounted residuals.',
     'Match requirements to current code interfaces/effects/AST/graph/contracts using DuckDB/DuckLake and exact head observations.',
     'Keep unresolved requirements and unsupported regions mandatory; learned scores may nominate candidates but cannot discharge coverage or source obligations.',
     'Preserve byte/character span units explicitly for Unicode instructions.'],
    'acceptance':['Current one-turn scripts retain full source syntax; they do not establish that a smaller selected-source context satisfies a task.',
     'Any requirement or source-selection change must be checked through the actual planner coverage API with negative omission controls.']},
   {'priority':3,'id':'genuine-worker-delivery-and-terminal-bench-pairing',
    'implementation':['Adapt the actual admitted worker/router context seam for the new public-source profile; do not relabel the existing Bottle-only entrypoint.',
     'Observe the bytes actually delivered after worker/router materialization, retain genuine native admission and original leases.',
     'Use paired frozen task/model/config populations and the official verifier; capture task outcomes, retries, expansions, input and output usage.'],
    'acceptance':['No fabricated worker/provider usage, zero-call savings or scripted outcomes qualify live efficiency.',
     'Require actual provider usage and maintained task behavior before making a savings claim or enabling compression by default.']},
   {'priority':4,'id':'typed-model-and-logic-proof-frontiers',
    'implementation':['Keep richer learned features advisory: training-only SVD beat neural reconstruction in the previous sealed milestone.',
     'Add constrained discrete CodebaseIR decoding with exact variable binding, literals, types, effects and control flow; retain unsupported atoms.',
     'Project supported candidates through genuine logic-family/checker routes and Lean; bind conditional proofs and reverse dependencies to exact source/head/target/checker artifacts.'],
    'acceptance':['Byte-exact context/source restoration proves data integrity, not CPython or source-model runtime equivalence.',
     'Finite training improvement, modeled fragment theorems, task completion and optimizer convergence remain separate claims.']},
   {'priority':5,'id':'durable-work-budget-and-failure-accounting',
    'implementation':['Join context setup/indexing/compilation, token retrieval/expansion and model/trainer worker work to persistent per-task counters and original native leases.',
     'Preserve failed attempts and completed optimizer/worker work across restart; do not reconstruct zero spent budget from a failed candidate.'],
    'acceptance':['The existing live shared-pool resource guards remain intact; this milestone does not implement a durable whole-task budget.']}
  ],'counterfactual_costs':aggregate,**FALSE}
 write(ROOT/'follow-up-plan-01.json',plan);inputs()
 files=[]
 for base,dirs,names in os.walk(ROOT,followlinks=False):
  dirs[:]=[name for name in dirs if name not in {'.git','__pycache__','.pytest_cache'}]
  for name in names:
   path=Path(base)/name
   if path.is_symlink():raise ValueError('unexpected owned successor symlink')
   files.append(path.relative_to(ROOT).as_posix())
 config={'schema':'terminal-codebase-ir-evidence-selection@1','root':str(ROOT),
  'files':sorted(files+['seal-config-01.json']),'selection_scope':'owned_public_source_capsule_artifacts',
  'excluded_git_metadata':True,'symlink_targets_opened':False,'proof_authority':False}
 write(ROOT/'seal-config-01.json',config)
 from seal_training_evidence import seal
 sealed=seal(config,ROOT/'evidence-manifest.json');seal(config,ROOT/'evidence-manifest.json',verify=True)
 print(json.dumps({'sealed':True,'files':sealed['file_count'],'bytes':sealed['total_bytes'],
  'file_set_sha256':sealed['file_set_sha256'],'tests':145,'counterfactual_pairs':32,
  'one_turn_minified_local_difference':minified['signed_difference'],'provider_usage':None}))

if __name__=='__main__':main()
