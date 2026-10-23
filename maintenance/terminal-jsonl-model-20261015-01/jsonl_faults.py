"""Actual file replacement/edit and current-codebase exit refusal controls."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
from jsonl_io import ROOT,FALSE,inputs,read,write,wire,sha,pin

def main(run,label):
    from jsonl_verify import validate_result,artifact_check
    output=ROOT/run;raw=read(output/'result.json',1024**2);result=json.loads(raw);validate_result(result)
    artifacts=artifact_check(output,result);base=json.loads(artifacts['base-materials.json']);contract=base['contract']
    structural=json.loads(artifacts['structural-report.json']);corpus,bodies,instructions,lineage=inputs()
    from jsonl_cases import specs,create_bundle,mutate_between_observations
    from observed_files import observe_bundle,reobserve_bundle,ObservationError
    from file_model_bridge import build_file_model,validate_file_model
    destination=ROOT/(label+'-artifacts');destination.mkdir(mode=0o700)
    chosen=next(row for row in specs() if row['case_id']=='valid-minimal');controls=[]
    cases=('file_changed_after_model','same_bytes_replacement','forged_derived_model','plan_changed_after_model')
    for case in cases:
        parent=destination/case;parent.mkdir();bundle=parent/'bundle'
        spec=deepcopy(chosen);spec['case_id']='fault-'+case
        create_bundle(destination=bundle,spec=spec)
        before=observe_bundle(root=bundle);after=observe_bundle(root=bundle)
        candidate=build_file_model(contract=contract,before=before,after=after,metrics=spec['metrics'],case_id=spec['case_id'])
        validate_file_model(candidate,contract=contract,before=before,after=after,metrics=spec['metrics'],case_id=spec['case_id'])
        if case=='forged_derived_model':
            candidate['case']['buckets'][0]['requests'][0]['prompt_len']+=64
            def reject():return validate_file_model(candidate,contract=contract,before=before,after=after,
                metrics=spec['metrics'],case_id=spec['case_id'])
        else:
            spec['fault']={'file_changed_after_model':'changed_input_bytes','same_bytes_replacement':'same_bytes_replacement',
                'plan_changed_after_model':'changed_plan_bytes'}[case]
            mutate_between_observations(destination=bundle,spec=spec)
            def reject():return reobserve_bundle(after,root=bundle)
        try:reject()
        except ValueError as error:
            if case!='forged_derived_model' and not isinstance(error,ObservationError):raise
            controls.append({'case':case,'rejected':True,'exception_class':type(error).__name__,'message':str(error)})
        else:raise ValueError('changed file/model escaped its actual verification fence')
        current=observe_bundle(root=bundle);reobserve_bundle(current,root=bundle)
        for name,value in [('before.json',before),('after.json',after),('candidate.json',candidate),('current.json',current)]:write(parent/name,value)
    from native_structural_ir import _owner,_scheduler,verify_structural_ir
    from ipfs_datasets_py.duckdb_control.codebase_catalog import CodebaseHead
    from ipfs_datasets_py.optimizers.logic_theorem_optimizer.resource_scheduler import ResourceLane
    from ipfs_accelerate_py.agent_supervisor.planning.structural_codebase_context import run_with_structural_codebase_context
    from jsonl_source_mutation import owned_source_mutation,SOURCE_PATH
    repository=output/'source-repository';head=CodebaseHead.from_dict(structural['head'])
    verify_structural_ir(repository=repository,output=output/'structural',expected=structural)
    with _scheduler().acquire(ResourceLane.VALIDATION,cpu_slots=1,memory_mb=2048,child_process_slots=1,
            timeout=30,request_id='terminal-jsonl-model:native-faults') as lease:
        with _owner(output/'structural',existing=True) as (index,_):
            with owned_source_mutation(repository/SOURCE_PATH,bodies[SOURCE_PATH]) as mutation:
                reached=[]
                def build(context):
                    reached.append(context.head.to_dict());mutation.apply()
                    return {'candidate':'must remain behind native owner exit fence'}
                try:run_with_structural_codebase_context(index,repository,build,repository_id=head.repository_id,expected_head=head,
                    parent_lease=lease,admission_timeout_seconds=20,timeout_seconds=120,memory_mb=256)
                except Exception as error:
                    if type(error).__name__!='StaleCodebaseError' or reached!=[head.to_dict()]:raise
                    controls.append({'case':'source_changed_at_exit','rejected':True,'exception_class':type(error).__name__,'message':str(error)})
                else:raise ValueError('stale source-bound model escaped native current owner')
            index.observe_current(repository,expected_head=head,parent_lease=lease,admission_timeout_seconds=20,timeout_seconds=120,memory_mb=256)
    verify_structural_ir(repository=repository,output=output/'structural',expected=structural)
    if artifact_check(output,result)!=artifacts or read(output/'result.json',1024**2)!=raw or inputs()[3]!=lineage:
        raise ValueError('selected source or artifact scope changed during actual faults')
    pins=[{'relative_path':path.relative_to(destination).as_posix(),**{k:v for k,v in pin(path).items() if k!='path'}}
        for path in sorted(destination.rglob('*')) if path.is_file()]
    report={'schema':'terminal-jsonl-model-faults@1','qualified':True,'selected_run':run,'selected_result_sha256':sha(raw),
        'native_head':structural['head'],'controls':controls,'artifact_pins':pins,'source_restored':True,
        'source_body_execution':False,'external_provider_calls':0,'new_optimizer_updates':0,**FALSE}
    write(ROOT/(label+'-fault-report.json'),report);print(json.dumps({'qualified':True,'actual_fault_controls':len(controls)}))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--run',required=True);parser.add_argument('--label',required=True);args=parser.parse_args()
    for name in (args.run,args.label):
        if Path(name).name!=name or name in {'.','..'}:raise ValueError('fresh owned local names required')
    main(args.run,args.label)
