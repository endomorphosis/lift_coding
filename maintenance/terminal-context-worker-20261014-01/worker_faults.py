"""Actual before-launch refusals and a source change after native child birth."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
from worker_io import ROOT,FALSE,read,write,wire,sha,inputs,pin

def run_faults(output,attempt):
    from worker_verify import validate_result,artifact_check
    from worker_run import dispatch_current,make_request
    from worker_capture import launch_capture
    from context_worker import prepare_request
    from worker_source_mutation import owned_source_mutation,SOURCE_PATH
    from native_structural_ir import _owner,_scheduler,verify_structural_ir
    from ipfs_datasets_py.duckdb_control.codebase_catalog import CodebaseHead
    from ipfs_datasets_py.logic.software_contracts.codebase_ir import StaleCodebaseError
    from ipfs_datasets_py.optimizers.logic_theorem_optimizer.resource_scheduler import ResourceLane
    from ipfs_accelerate_py.agent_supervisor.todo_daemon import supervisor_runtime as native
    if output.resolve()!=output or output.parent!=ROOT or attempt.resolve()!=attempt or attempt.parent!=ROOT or attempt.exists():
        raise ValueError('fresh owned fault namespace required')
    attempt.mkdir(mode=0o700)
    result_raw=read(output/'result.json');result=json.loads(result_raw);validate_result(result);artifact_check(output,result)
    structural=json.loads(read(output/'structural-report.json'));head=CodebaseHead.from_dict(structural['head'])
    contexts=json.loads(read(output/'contexts.json'));descriptor=json.loads(read(output/'tokenizer.json'))
    task=contexts['tasks'][0];repository=output/'source-repository';controls=[]
    _,bodies,_,lineage=inputs()
    baseline=make_request(task,'adaptive',0,descriptor,[])
    _,observed=prepare_request(baseline)
    cases=[]
    bad=deepcopy(baseline);bad['max_input_tokens']=1;cases.append(('overbudget_before_launch',bad))
    bad=make_request(task,'adaptive',1,descriptor,observed);bad['messages'][0]['content']+=' authored alteration'
    cases.append(('rewritten_history_before_launch',bad))
    bad=make_request(task,'adaptive',1,descriptor,observed);bad['messages'][:2]=reversed(bad['messages'][:2])
    cases.append(('reordered_history_before_launch',bad))
    with _scheduler().acquire(ResourceLane.VALIDATION,cpu_slots=1,memory_mb=1024,child_process_slots=1,
            timeout=30,request_id='terminal-context-worker:native-faults') as lease:
        for name,request in cases:
            destination=attempt/name
            try:launch_capture(request=request,repository=repository,lease=lease,output_dir=destination,timeout_seconds=30)
            except ValueError as error:
                if destination.exists():raise ValueError('invalid request reached worker filesystem creation') from error
                controls.append({'control':name,'refused':True,'error_class':type(error).__name__,
                    'message':str(error),'consumer_calls':0,**FALSE})
            else:raise ValueError('invalid complete-message request escaped before-launch guard')
        changed=False;escaped=False;birth={};original=native.run_process_group_stream
        with _owner(output/'structural',existing=True) as (index,_):
            with owned_source_mutation(repository/SOURCE_PATH,bodies[SOURCE_PATH]) as mutation:
                def run_after_birth(*args,**kwargs):
                    previous=kwargs.get('on_started')
                    def started(process):
                        nonlocal changed
                        if previous:previous(process)
                        identity=native.read_process_birth(process.pid)
                        birth.update(pid=process.pid,start_time_ticks=identity.start_time_ticks)
                        mutation.apply();changed=True
                    return original(*args,**dict(kwargs,on_started=started))
                native.run_process_group_stream=run_after_birth
                try:
                    dispatch_current(index=index,repository=repository,head=head,request=baseline,lease=lease,
                        output_dir=attempt/'source_changed_after_spawn')
                    escaped=True
                except StaleCodebaseError as error:
                    if not changed:raise ValueError('source fault did not follow actual native child birth') from error
                    controls.append({'control':'source_changed_after_spawn','refused':True,
                        'error_class':type(error).__name__,'message':str(error),'consumer_calls':1,**FALSE})
                finally:native.run_process_group_stream=original
            if escaped:raise ValueError('source-changed worker candidate escaped owner exit fence')
            index.observe_current(repository,expected_head=head,parent_lease=lease,
                admission_timeout_seconds=20,timeout_seconds=120,memory_mb=256)
    verify_structural_ir(repository=repository,output=output/'structural',expected=structural)
    if read(repository/SOURCE_PATH,8192)!=bodies[SOURCE_PATH] or inputs()[3]!=lineage:
        raise ValueError('source or selected lineage was not restored')
    if read(output/'result.json')!=result_raw:raise ValueError('selected result changed during faults')
    artifact_check(output,result)
    fault_artifacts=[{'relative_path':path.relative_to(ROOT).as_posix(),
        **{k:v for k,v in pin(path).items() if k!='path'}}
        for path in sorted((attempt/'source_changed_after_spawn').iterdir()) if path.is_file()]
    return {'schema':'terminal-context-worker-faults@1','qualified':True,'selected_run':output.name,
        'selected_result_sha256':sha(result_raw),'native_head':structural['head'],'controls':controls,
        'source_fault':{'mutation_after_actual_child_birth':changed,'candidate_escaped':escaped,
            'source_restored':True,'native_owner_reobserved':True,'actual_child_birth':birth},
        'artifact_pins':fault_artifacts,'actual_extra_worker_children':1,
        'provider_usage':None,'source_body_execution':False,'actual_external_provider_invocations':0,**FALSE}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--run',required=True);parser.add_argument('--label',required=True);args=parser.parse_args()
    for name in [args.run,args.label]:
        if not name or Path(name).name!=name or name in {'.','..'}:raise ValueError('local attempt names required')
    report=run_faults(ROOT/args.run,ROOT/(args.label+'-artifacts'))
    write(ROOT/(args.label+'-fault-report.json'),report)
    print(json.dumps({'qualified':True,'controls':len(report['controls']),'extra_local_capture_calls':1}))
