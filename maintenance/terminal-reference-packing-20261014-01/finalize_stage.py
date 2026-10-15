"""Record complete cost controls, next gates and a bounded public-artifact seal."""
import argparse
import json
import os
from pathlib import Path
from packing_io import ROOT,FALSE,read,write,inputs,pin,sha,wire

def verify_selected_report_bytes(root, reports):
    for name,raw in reports.items():
        if read(root/name) != raw:
            raise ValueError('selected report changed during finalization')

def validate_report_bindings(*,run,result,result_raw,process,tests,cold,cold_process,faults,fault_process,fault_name,fault_raw):
    if not all(v['qualified'] is True for v in [process,tests,cold,cold_process,faults,fault_process]):
        raise ValueError('complete qualified local evidence required')
    if any(v.get('selected_run') != run for v in [process,cold,cold_process,faults,fault_process]):
        raise ValueError('cold/fault/process reports must bind the selected run')
    if any(v.get('selected_result_sha256') != sha(result_raw) for v in [cold,faults]):
        raise ValueError('cold/fault reports must bind the exact selected result')
    if cold.get('selected_native_head') != result['native_head'] or cold.get('selected_artifact_pins_sha256') != sha(wire(result['artifact_pins'])):
        raise ValueError('cold owner and complete artifact scope must match the selected result')
    if cold.get('qualified_faults_verified_before_positive_replay') is not True or cold.get('preceding_fault_report') != {
            'relative_path':fault_name,'bytes':len(fault_raw),'sha256':sha(fault_raw)}:
        raise ValueError('positive cold replay must depend on these exact qualified preceding faults')
    if any(tests['tests'][k] for k in ['failures','errors','skipped']): raise ValueError('complete selected regressions required')
    for report,kind in [(process,'run'),(tests,'test'),(cold_process,'cold'),(fault_process,'fault')]:
        if report.get('kind') != kind: raise ValueError('selected process kind differs')
        if not report.get('after') or report.get('before') != report['after'] or report['after'] != cold_process['after']:
            raise ValueError('all selected processes must use the same unchanged producer pins')

def main(args):
    for name in [args.run,args.regression,args.cold,args.fault]:
        if not name or Path(name).name != name or name in {'.','..'}: raise ValueError('local selected names required')
    result_raw=read(ROOT/args.run/'result.json');result=json.loads(result_raw)
    from packing_verify import result_check,artifact_check
    result_check(result);artifact_check(ROOT/args.run,result)
    costs=json.loads(read(ROOT/args.run/'costs.json'))
    selected_report_bytes={}
    def selected_report(name):
        raw=read(ROOT/name);selected_report_bytes[name]=raw;return json.loads(raw)
    process=selected_report(args.run+'-process-report.json')
    tests=selected_report(args.regression+'-process-report.json')
    cold=selected_report(args.cold+'-cold-report.json')
    cold_process=selected_report(args.cold+'-process-report.json')
    faults=selected_report(args.fault+'-fault-report.json')
    fault_process=selected_report(args.fault+'-process-report.json')
    fault_name=args.fault+'-fault-report.json'
    fault_raw=selected_report_bytes[fault_name]
    validate_report_bindings(run=args.run,result=result,result_raw=result_raw,process=process,tests=tests,
        cold=cold,cold_process=cold_process,faults=faults,fault_process=fault_process,fault_name=fault_name,fault_raw=fault_raw)
    for entry in cold_process['after']:
        if pin(Path(entry['path'])) != entry: raise ValueError('final producer drift')
    totals={}; per_task=[]
    for row in costs['pairs']:
        for mode,measurement in row['measurement']['comparisons'].items():
            baseline=measurement['baseline']['totals']['total_tokens']
            candidate=measurement['compact']['totals']['total_tokens']
            key=(row['variant'],row['scenario'],mode)
            aggregate=totals.setdefault(key,{'baseline_tokens':0,'candidate_tokens':0,'signed_difference':0})
            aggregate['baseline_tokens']+=baseline; aggregate['candidate_tokens']+=candidate
            aggregate['signed_difference']+=baseline-candidate
            per_task.append({'task_id':row['task_id'],'variant':row['variant'],'scenario':row['scenario'],'delivery':mode,
                'baseline_local_tokens':baseline,'candidate_local_tokens':candidate,'signed_difference':baseline-candidate,
                'provider_usage':None,'source':'declared full-message counterfactual script'})
    aggregate=[{'variant':variant,'scenario':scenario,'delivery':mode,**v,
        'signed_local_reduction':v['signed_difference']/v['baseline_tokens'],'observed_provider_savings':None}
        for (variant,scenario,mode),v in sorted(totals.items())]
    controls=[v for v in aggregate if v['delivery']=='decode_before_model']
    if not controls or any(v['signed_difference'] != 0 for v in controls):
        raise ValueError('decode-before-model must preserve complete input cost')
    selected=totals[('reference_lifted','one_turn','direct_encoded_delivery')]
    decision=('Retain token-aware reference packing as an experimental representation. '
        'Its hypothetical direct-model cost and exact data restoration are measured locally; '
        'decode-before-model preserves the full original input cost. Actual worker delivery and task behavior remain unmeasured.')
    status={'schema':'terminal-reference-packing-improvement-status@1','completed_milestone':True,'selected_run':args.run,
        'native_head':result['native_head'],'native_capsule_inventory':result['native_capsule_inventory'],
        'metadata_original_record_counts':result['metadata_original_record_counts'],
        'native_shared_admission':True,'fresh_own_source_only_git_repository':True,
        'native_structural_context_and_plan_materials_exercised':True,'native_context_compiler_exercised':True,
        'all_12_context_variant_roundtrips_byte_exact':True,'all_36_local_cost_scripts_cold_reproduced':True,
        'all_instruction_bytes_and_original_raw_sources_preserved':True,'all_instruction_requirements_unresolved':True,
        'residual_span_unit':'utf8_bytes','source_omission_enabled':False,
        'raw_source_required_before_edit_or_proving':True,'all_inline_decoder_guidance_and_dictionaries_charged':True,
        'optimizer_diagnostics_are_detached_from_model_wire':True,'global_dictionary_optimum_claimed':False,
        'local_one_turn_lifted_reference_direct_model':selected,
        'local_one_turn_lifted_reference_reduction_fraction':selected['signed_difference']/selected['baseline_tokens'],
        'aggregate_counterfactual_costs':aggregate,'per_task_counterfactual_costs':per_task,
        'decode_before_model_input_saving_tokens':0,'actual_worker_delivery_observed':False,
        'provider_usage':None,'actual_provider_invocations':0,'actual_terminal_bench_outcomes':None,'cache_reuse_credit':0,
        'compression_promoted_to_supervisor_default':False,'promotion_decision':decision,
        'unique_selected_tests':tests['tests']['tests'],'genuine_negative_controls':faults,
        'positive_cold_after_faults_qualified':True,'new_optimizer_updates':0,'new_prover_invocations':0,
        'source_body_execution':False,**FALSE}
    write(ROOT/'improvement-status-01.json',status)
    plan={'schema':'terminal-codebase-intent-ir-improvement-plan@6','measured_decision':decision,
        'next_work':[
          {'priority':1,'id':'generic-admitted-worker-context-delivery',
           'implementation':['Add a distinctly versioned generic complete-context worker interface; existing Bottle-specific adapters do not accept this profile.',
             'Use a per-task expanded-context fallback when the complete packed-message cost rises; charge any routing labels or selection guidance.',
             'Capture bytes actually passed to the model after router/worker materialization using the original native admission and resource leases.',
             'Check the budget against the complete delivered packet and message framing; original-context reservations do not qualify a changed model payload.',
             'Evaluate direct symbolic-reference interpretation against expanded context; exact Python decoding does not establish model interpretation equivalence.',
             'Require exact head, codec/profile/tokenizer pins and required-source/instruction checks before and after use.'],
           'acceptance':['Decoding before model input saves zero input tokens in this controlled experiment.',
             'Do not label hypothetical packed-wire BPE reductions as observed provider savings.',
             'No real worker/provider receipts are fabricated from pure codecs or scripted ledgers.']},
          {'priority':2,'id':'paired-terminal-bench-outcomes-and-total-cost',
           'implementation':['Run frozen paired task/model/config populations through the official verifier.',
             'Capture actual provider input/output usage, indexing/training/setup work, full histories, retries and tool expansion reads.',
             'Preserve failed attempt work and resource admission across restart; zero failed usage is never inferred.'],
           'acceptance':['Maintain task behavior and charge all cumulative work before enabling compression by default.',
             'Report per-task regressions and uncertainty; current headless direct-model case may cost more despite aggregate reduction.']},
          {'priority':3,'id':'intent-coverage-and-current-codebase-matching',
           'implementation':['Decode complete instruction goals, guards, prohibitions, effects and numeric limits with source-span-accounted residuals.',
             'Join intent atoms to current AST, interfaces, effects, graph, vectors and contracts in DuckDB/DuckLake.',
             'Exercise the actual planner coverage API with negative omission controls before any relevance-based source reduction.',
             'Keep unsupported requirements and raw source obligations mandatory; learned scores cannot discharge them.'],
           'acceptance':['All present task instructions remain unresolved; exact packing confers no task-completion authority.']},
          {'priority':4,'id':'source-to-model-and-proof-index',
           'implementation':['Retain richer learned CodebaseIR features as advisory; previous training-only SVD beat neural reconstruction.',
             'Add constrained discrete decoding with exact bindings, literals, types, effects and control flow; unsupported atoms remain explicit.',
             'Compile supported projections through genuine logic-family/checker routes and Lean.',
             'Bind conditional proof-cache entries and reverse dependencies to exact source/head/target/checker artifacts.'],
           'acceptance':['Byte-exact reconstruction is data integrity, not CPython runtime equivalence.',
             'Finite training improvement, fragment theorems, whole-task satisfaction and optimizer convergence remain distinct.']}
        ],'counterfactual_costs':aggregate,**FALSE}
    write(ROOT/'follow-up-plan-01.json',plan); inputs()
    if read(ROOT/args.run/'result.json') != result_raw: raise ValueError('selected result changed during finalization')
    artifact_check(ROOT/args.run,result)
    verify_selected_report_bytes(ROOT,selected_report_bytes)
    files=[]
    for base,dirs,names in os.walk(ROOT,followlinks=False):
        dirs[:]=[n for n in dirs if n not in {'.git','__pycache__','.pytest_cache'}]
        for name in names:
            path=Path(base)/name
            if path.is_symlink(): raise ValueError('unexpected owned symlink')
            files.append(path.relative_to(ROOT).as_posix())
    config={'schema':'terminal-codebase-ir-evidence-selection@1','root':str(ROOT),
        'files':sorted(files+['seal-config-01.json']),'selection_scope':'owned_public_reference_packing_artifacts',
        'excluded_git_metadata':True,'symlink_targets_opened':False,'proof_authority':False}
    write(ROOT/'seal-config-01.json',config)
    from seal_training_evidence import seal
    sealed=seal(config,ROOT/'evidence-manifest.json');seal(config,ROOT/'evidence-manifest.json',verify=True)
    print(json.dumps({'sealed':True,'files':sealed['file_count'],'bytes':sealed['total_bytes'],
        'file_set_sha256':sealed['file_set_sha256'],'tests':tests['tests']['tests'],
        'direct_one_turn_local_difference':selected['signed_difference'],'provider_usage':None}))

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    for name in ['run','regression','cold','fault']: parser.add_argument('--'+name,required=True)
    main(parser.parse_args())
