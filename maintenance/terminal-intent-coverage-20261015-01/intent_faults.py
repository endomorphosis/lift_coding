"""Genuine source-owner refusal and complete-intent artifact corruption controls."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
from intent_io import ROOT,FALSE,inputs,read,write,wire,sha
from intent_run import source_records,check_lease

def main(run,label):
    from intent_verify import validate_result,artifact_check
    output=ROOT/run;result_raw=read(output/'result.json',1024**2);result=json.loads(result_raw)
    validate_result(result);acquired=artifact_check(output,result)
    corpus,bodies,instructions,lineage=inputs();inventories=json.loads(acquired['intent-inventories.json'])
    structural=json.loads(acquired['structural-report.json']);grounding=json.loads(acquired['grounding.json'])
    projections=json.loads(acquired['logic-projections.json']);controls=[]
    from clause_inventory import validate_instruction_inventory
    from requirement_grounding import validate_requirement_grounding
    from logic_projections import validate_logic_projections
    def refuse(case,callback):
        try:callback()
        except (ValueError,TypeError,KeyError) as error:
            controls.append({'case':case,'rejected':True,'exception_class':type(error).__name__,'message':str(error)})
        else:raise ValueError('authored intent corruption was accepted: '+case)
    chosen=inventories[0];task=chosen['task_id']
    refuse('changed_instruction',lambda:validate_instruction_inventory(chosen,task_id=task,instruction=instructions[task]+b'\nDo not drop this mandatory requirement.\n'))
    omitted=deepcopy(chosen);omitted['units'].pop()
    refuse('omitted_instruction_unit',lambda:validate_instruction_inventory(omitted,task_id=task,instruction=instructions[task]))
    forged=deepcopy(grounding);forged['head']['generation']+=1
    refuse('forged_grounding',lambda:validate_requirement_grounding(forged,inventories=inventories,
        source_records=source_records(bodies),structural_manifest=structural['manifest'],head=structural['head'],corpus=corpus))
    promoted=deepcopy(projections);promoted['proof_authority']=True
    refuse('projection_authority_promoted',lambda:validate_logic_projections(promoted,inventories=inventories))
    from native_structural_ir import _owner,_scheduler,verify_structural_ir
    from ipfs_datasets_py.duckdb_control.codebase_catalog import CodebaseHead
    from ipfs_datasets_py.optimizers.logic_theorem_optimizer.resource_scheduler import ResourceLane
    from ipfs_accelerate_py.agent_supervisor.planning.structural_codebase_context import run_with_structural_codebase_context
    from intent_source_mutation import owned_source_mutation,SOURCE_PATH
    head=CodebaseHead.from_dict(structural['head']);repository=output/'source-repository'
    verify_structural_ir(repository=repository,output=output/'structural',expected=structural)
    with _scheduler().acquire(ResourceLane.VALIDATION,cpu_slots=1,memory_mb=1024,child_process_slots=1,
            timeout=30,request_id='terminal-intent-coverage:native-faults') as lease:
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
    report={'schema':'terminal-intent-coverage-faults@1','qualified':True,'selected_run':run,
        'selected_result_sha256':sha(result_raw),'native_head':structural['head'],'controls':controls,
        'source_restored':True,'source_body_execution':False,'external_provider_calls':0,'new_optimizer_updates':0,**FALSE}
    write(ROOT/(label+'-fault-report.json'),report);print(json.dumps({'qualified':True,'native_controls':len(controls)}))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--run',required=True);parser.add_argument('--label',required=True);args=parser.parse_args()
    for name in (args.run,args.label):
        if Path(name).name!=name or name in {'.','..'}:raise ValueError('fresh owned local names required')
    main(args.run,args.label)
