"""Actual fixture-authority, native claim and source freshness refusal controls."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import tempfile
from admission_io import ROOT,FALSE,inputs,read,write,wire,sha,pin
from admission_run import input_binding,check_lease

def main(run,label):
    from admission_verify import validate_result,artifact_check
    output=ROOT/run;raw=read(output/'result.json',1024**2);result=json.loads(raw);validate_result(result)
    artifacts=artifact_check(output,result);structural=json.loads(artifacts['structural-report.json'])
    corpus,bodies,instructions,lineage=inputs()
    request=next(item['request'] for item in json.loads(artifacts['deliveries.json'])['deliveries']
        if item['task_id']=='headless-terminal' and item['delivery_mode']=='adaptive')
    from native_structural_ir import verify_structural_ir,_owner,_scheduler
    from ipfs_datasets_py.duckdb_control.codebase_catalog import CodebaseHead
    from ipfs_datasets_py.optimizers.logic_theorem_optimizer.resource_scheduler import ResourceLane
    from ipfs_accelerate_py.agent_supervisor.merge.database_coordination import DatabaseCoordinator
    from ipfs_accelerate_py.agent_supervisor.todo_daemon import supervisor_runtime as runtime
    from planning_job import create_owned_planning_job
    from planning_permit import issue_planning_permit
    from worker_capture import launch_admitted_capture,capture_launch_binding
    from admission_source_mutation import owned_source_mutation,SOURCE_PATH
    destination=ROOT/(label+'-artifacts');destination.mkdir(mode=0o700)
    repository=output/'source-repository';head=CodebaseHead.from_dict(structural['head']);controls=[];extra=0
    verify_structural_ir(repository=repository,output=output/'structural',expected=structural)
    with _scheduler().acquire(ResourceLane.VALIDATION,cpu_slots=1,memory_mb=1024,child_process_slots=1,
            timeout=30,request_id='terminal-planning-admission:native-faults') as lease:
        with _owner(output/'structural',existing=True) as (index,_):
            for case in ('request_changed','output_exists','claim_released','source_changed_after_spawn'):
                parent=destination/case;parent.mkdir();target=parent/'capture'
                private=Path(tempfile.mkdtemp(prefix='terminal-planning-fault-job-'))
                with create_owned_planning_job(job_repository=parent/'repository',private_root=private,
                        public_output=parent/'admission',input_binding=input_binding(request=request,structural=structural,
                            corpus=corpus,bodies=bodies,instructions=instructions),task_key='fault-'+case.replace('_','-')) as job:
                    with tempfile.TemporaryDirectory(prefix='terminal-planning-fault-coordinator-') as private_coordinator:
                        with DatabaseCoordinator(Path(private_coordinator)/'claims.duckdb') as coordinator:
                            coordinator.register_task(task_cid=job.task_cid,task_id=job.task_id,
                                worktree_id=str(repository),body=job.job_binding)
                            claim=coordinator.claim_task(task_cid=job.task_cid,owner_session_id=job.job_binding['intent_session_id'],
                                worktree_id=str(repository),lease_ms=120000,body=job.job_binding)
                            permit=issue_planning_permit(job=job,job_binding=job.job_binding,coordinator=coordinator,claim=claim,
                                parent_lease=lease,request=request,repository=repository,**capture_launch_binding(target))
                            changed=deepcopy(request)
                            if case=='request_changed':changed['max_input_tokens']+=1
                            if case=='output_exists':target.mkdir()
                            if case=='claim_released':coordinator.release(coordinator.protect_task_claim(claim),reason='authored-negative-control')
                            index.observe_current(repository,expected_head=head,parent_lease=lease,
                                admission_timeout_seconds=20,timeout_seconds=120,memory_mb=256)
                            failure=None;candidate=None
                            if case=='source_changed_after_spawn':
                                original_run=runtime.run_process_group_stream
                                with owned_source_mutation(repository/SOURCE_PATH,bodies[SOURCE_PATH]) as mutation:
                                    def injected(*args,**kwargs):
                                        original_started=kwargs['on_started']
                                        def started(process):
                                            original_started(process);mutation.apply()
                                        kwargs['on_started']=started
                                        return original_run(*args,**kwargs)
                                    runtime.run_process_group_stream=injected
                                    try:
                                        candidate=launch_admitted_capture(request=changed,repository=repository,lease=lease,
                                            output_dir=target,permit=permit)
                                        extra+=1
                                        index.observe_current(repository,expected_head=head,parent_lease=lease,
                                            admission_timeout_seconds=20,timeout_seconds=120,memory_mb=256)
                                    except Exception as error:failure=error
                                    finally:runtime.run_process_group_stream=original_run
                                if candidate is None or type(failure).__name__!='StaleCodebaseError':
                                    raise ValueError('actual child/source mutation did not reach native owner exit refusal')
                                write(parent/'refused-candidate-capture.json',candidate)
                            else:
                                try:launch_admitted_capture(request=changed,repository=repository,lease=lease,output_dir=target,permit=permit)
                                except Exception as error:failure=error
                                if failure is None or (target/'request.json').exists():raise ValueError('fault reached child or was accepted')
                            index.observe_current(repository,expected_head=head,parent_lease=lease,
                                admission_timeout_seconds=20,timeout_seconds=120,memory_mb=256)
                            controls.append({'case':case,'rejected':True,'exception_class':type(failure).__name__,
                                'message':str(failure),'actual_child_spawned':candidate is not None,'original_source_restored':True})
                            try:launch_admitted_capture(request=request,repository=repository,lease=lease,output_dir=target,permit=permit)
                            except Exception as error:
                                if 'consumed or burned' not in str(error):raise
                                controls.append({'case':case+'-replay','rejected':True,'exception_class':type(error).__name__,
                                    'message':str(error),'actual_child_spawned':False,'original_source_restored':True})
                            else:raise ValueError('failed/completed planning permit was reusable')
                if private.exists():raise ValueError('private fixture state escaped cleanup')
    verify_structural_ir(repository=repository,output=output/'structural',expected=structural)
    if inputs()[3]!=lineage or read(output/'result.json',1024**2)!=raw or artifact_check(output,result)!=artifacts:
        raise ValueError('selected source/result/artifacts changed across native faults')
    pins=[pin(path) for path in sorted(destination.rglob('*')) if path.is_file() and '.git' not in path.relative_to(destination).parts]
    report={'schema':'terminal-planning-admission-faults@1','qualified':True,'selected_run':run,
        'selected_result_sha256':sha(raw),'native_head':head.to_dict(),'controls':controls,'artifact_pins':pins,
        'actual_extra_worker_children':extra,'actual_external_provider_invocations':0,'provider_usage':None,
        'source_body_execution':False,'private_authority_destroyed':True,'original_source_restored':True,**FALSE}
    write(ROOT/(label+'-fault-report.json'),report)
    print(json.dumps({'qualified':True,'controls':len(controls),'actual_extra_worker_children':extra}))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--run',required=True);parser.add_argument('--label',required=True);args=parser.parse_args()
    for name in (args.run,args.label):
        if Path(name).name!=name or name in {'.','..'}:raise ValueError('fresh owned local names required')
    main(args.run,args.label)
