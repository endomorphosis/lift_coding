"""Genuine source-owner refusal and complete-intent artifact corruption controls."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
from constraint_io import ROOT,FALSE,inputs,read,write,wire,sha
from constraint_run import source_records,check_lease,TASK

def main(run,label):
    from constraint_verify import validate_result,artifact_check
    output=ROOT/run;result_raw=read(output/'result.json',1024**2);result=json.loads(result_raw)
    validate_result(result);acquired=artifact_check(output,result)
    corpus,bodies,instructions,lineage=inputs()
    structural=json.loads(acquired['structural-report.json']);contract=json.loads(acquired['scheduler-contract.json'])
    projections=json.loads(acquired['constraint-projections.json']);cases=json.loads(acquired['authored-cases.json']);controls=[]
    from scheduler_constraints import validate_scheduler_contract,validate_case_evaluation
    from constraint_projections import validate_constraint_projections
    def refuse(case,callback):
        try:callback()
        except (ValueError,TypeError,KeyError) as error:
            controls.append({'case':case,'rejected':True,'exception_class':type(error).__name__,'message':str(error)})
        else:raise ValueError('authored constraint corruption was accepted: '+case)
    refuse('changed_instruction',lambda:validate_scheduler_contract(contract,instruction=instructions[TASK]+b'\nDo not omit this requirement.\n',
        head=structural['head'],source_records=source_records(bodies)))
    changed=deepcopy(contract)
    next(row for row in changed['clauses'] if row['requirement_id']=='scheduler.global_shape_cap')['parameters']['max_shapes']=9
    refuse('changed_contract_bound',lambda:validate_scheduler_contract(changed,instruction=instructions[TASK],
        head=structural['head'],source_records=source_records(bodies)))
    negative=next(row for row in cases if not row['expected_pass'])
    from scheduler_constraints import evaluate_case
    forged=evaluate_case(contract,negative['case']);forged['evaluation_passed']=True;forged['violations']=[]
    refuse('forged_case_evaluation',lambda:validate_case_evaluation(forged,contract=contract,case=negative['case']))
    promoted=deepcopy(projections);promoted['proof_authority']=True
    refuse('projection_authority_promoted',lambda:validate_constraint_projections(promoted,contract=contract))
    from native_structural_ir import _owner,_scheduler,verify_structural_ir
    from ipfs_datasets_py.duckdb_control.codebase_catalog import CodebaseHead
    from ipfs_datasets_py.optimizers.logic_theorem_optimizer.resource_scheduler import ResourceLane
    from ipfs_accelerate_py.agent_supervisor.planning.structural_codebase_context import run_with_structural_codebase_context
    from constraint_source_mutation import owned_source_mutation,SOURCE_PATH
    head=CodebaseHead.from_dict(structural['head']);repository=output/'source-repository'
    verify_structural_ir(repository=repository,output=output/'structural',expected=structural)
    with _scheduler().acquire(ResourceLane.VALIDATION,cpu_slots=1,memory_mb=1024,child_process_slots=1,
            timeout=30,request_id='terminal-typed-constraints:native-faults') as lease:
        with _owner(output/'structural',existing=True) as (index,_):
            with owned_source_mutation(repository/SOURCE_PATH,bodies[SOURCE_PATH]) as mutation:
                reached=[]
                def build(context):
                    reached.append(context.head.to_dict());mutation.apply()
                    return {'candidate':'must not escape current owner exit fence'}
                try:run_with_structural_codebase_context(index,repository,build,repository_id=head.repository_id,
                    expected_head=head,parent_lease=lease,admission_timeout_seconds=20,timeout_seconds=120,memory_mb=256)
                except Exception as error:
                    if type(error).__name__!='StaleCodebaseError' or reached!=[head.to_dict()]:raise
                    controls.append({'case':'source_changed_at_exit','rejected':True,'exception_class':type(error).__name__,'message':str(error)})
                else:raise ValueError('source-bound intent escaped stale native owner')
            index.observe_current(repository,expected_head=head,parent_lease=lease,
                admission_timeout_seconds=20,timeout_seconds=120,memory_mb=256)
    verify_structural_ir(repository=repository,output=output/'structural',expected=structural)
    if inputs()[3]!=lineage or read(output/'result.json',1024**2)!=result_raw or artifact_check(output,result)!=acquired:
        raise ValueError('selected complete instruction/source/artifact scope changed across faults')
    report={'schema':'terminal-typed-constraint-faults@1','qualified':True,'selected_run':run,
        'selected_result_sha256':sha(result_raw),'native_head':structural['head'],'controls':controls,
        'source_restored':True,'source_body_execution':False,'external_provider_calls':0,'new_optimizer_updates':0,**FALSE}
    write(ROOT/(label+'-fault-report.json'),report);print(json.dumps({'qualified':True,'native_controls':len(controls)}))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--run',required=True);parser.add_argument('--label',required=True);args=parser.parse_args()
    for name in (args.run,args.label):
        if Path(name).name!=name or name in {'.','..'}:raise ValueError('fresh owned local names required')
    main(args.run,args.label)
