"""Authored cold-data fixtures; no child, router, DB or native owner execution.

These synthetic captures test consistency and custody checks only. They are not
actual worker evidence and are never published as observed process receipts.
"""
from copy import deepcopy
import json
from pathlib import Path

import pytest

import worker_verify as subject
import worker_capture
import context_worker
from worker_io import FALSE, sha, wire
from test_worker_capture import authored_request, fixture_observation


def declared_result(head):
    return {'schema':'terminal-generic-context-worker-experiment@1','completed':True,
        'policy':deepcopy(subject.POLICY),'native_head':deepcopy(head),'source_count':5,'task_count':4,
        'sessions':12,'worker_child_invocations':48,'local_consumer_calls':48,
        'actual_external_provider_invocations':0,'new_optimizer_updates':0,'new_prover_invocations':0,
        'source_body_execution':False,'metadata_original_record_counts':{'source_files':5},
        'native_capsule_inventory':{'source_entries':5,'symbols':57,'edges':382},
        'artifact_pins':[],'seconds':0.0,'peak_rss_kib':1,**FALSE}


@pytest.fixture
def inventory(tmp_path,authored_request):
    result=declared_result(authored_request['expected_head']);rows=[]
    files={name:('authored core artifact '+name).encode() for name in subject.FILES}
    for task in subject.TASKS:
        for mode in subject.MODES:
            for step in range(4):
                for leaf in subject.MANDATORY_LEAVES:
                    name=f'workers/{task}/{mode}/turn-{step}/{leaf}'
                    files[name]=b'' if leaf=='stderr.log' else ('authored leaf '+name).encode()
    for name,raw in files.items():
        path=tmp_path/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
        rows.append({'relative_path':name,'bytes':len(raw),'sha256':sha(raw)})
    result['artifact_pins']=sorted(rows,key=lambda row:row['relative_path'])
    return tmp_path,result,files


def test_closed_result_and_complete_inventory_acquisition(inventory):
    output,result,files=inventory
    assert subject.validate_result(result) is None
    assert subject.artifact_check(output,result)==files


@pytest.mark.parametrize('damage',['extra','missing_flag','worker_count_bool','worker_count_47','session_count',
    'external_provider','external_bool','optimizer','prover','source_body','authority_zero','policy_flag_zero',
    'bad_head','seconds_nan','rss_float','empty_metadata'])
def test_closed_worker_result_counters_and_authority_refuse(inventory,damage):
    _,result,_=inventory
    if damage=='extra':result['invented_provider_receipt']=True
    elif damage=='missing_flag':result.pop('proof_authority')
    elif damage=='worker_count_bool':result['worker_child_invocations']=True
    elif damage=='worker_count_47':result['worker_child_invocations']=47
    elif damage=='session_count':result['sessions']=11
    elif damage=='external_provider':result['actual_external_provider_invocations']=1
    elif damage=='external_bool':result['actual_external_provider_invocations']=False
    elif damage=='optimizer':result['new_optimizer_updates']=1
    elif damage=='prover':result['new_prover_invocations']=1
    elif damage=='source_body':result['source_body_execution']=True
    elif damage=='authority_zero':result['proof_authority']=0
    elif damage=='policy_flag_zero':result['policy']['proof_authority']=0
    elif damage=='bad_head':result['native_head']['generation']=True
    elif damage=='seconds_nan':result['seconds']=float('nan')
    elif damage=='rss_float':result['peak_rss_kib']=1.0
    elif damage=='empty_metadata':result['metadata_original_record_counts']={}
    with pytest.raises(ValueError):subject.validate_result(result)


@pytest.mark.parametrize('damage',['duplicate','missing','unknown_path','traversal','backslash','unknown_task',
    'unknown_mode','unknown_turn','unknown_leaf','bool_bytes','negative_bytes','wrong_digest','unsorted',
    'actual_extra_leaf','actual_symlink','modified','unlinked_leaf'])
def test_complete_worker_pin_scope_rejects_aliasing_omission_and_changed_files(inventory,damage):
    output,result,_=inventory
    rows=result['artifact_pins'];worker=next(row for row in rows if row['relative_path'].startswith('workers/'))
    path=output/worker['relative_path']
    if damage=='duplicate':rows.append(deepcopy(rows[-1]));rows.sort(key=lambda row:row['relative_path'])
    elif damage=='missing':rows.remove(worker)
    elif damage=='unknown_path':worker['relative_path']='private-other/file.json'
    elif damage=='traversal':worker['relative_path']='workers/../private/file.json'
    elif damage=='backslash':worker['relative_path']=worker['relative_path'].replace('/','\\')
    elif damage=='unknown_task':worker['relative_path']='workers/private-task/adaptive/turn-0/request.json'
    elif damage=='unknown_mode':worker['relative_path']='workers/headless-terminal/provider/turn-0/request.json'
    elif damage=='unknown_turn':worker['relative_path']='workers/headless-terminal/adaptive/turn-4/request.json'
    elif damage=='unknown_leaf':worker['relative_path']=worker['relative_path'].rsplit('/',1)[0]+'/unknown.json'
    elif damage=='bool_bytes':worker['bytes']=False
    elif damage=='negative_bytes':worker['bytes']=-1
    elif damage=='wrong_digest':worker['sha256']='0'*64
    elif damage=='unsorted':rows.reverse()
    elif damage=='actual_extra_leaf':(path.parent/'unexpected.json').write_bytes(b'authored extra')
    elif damage=='actual_symlink':
        raw=path.read_bytes();path.unlink();target=output/'authored-target';target.write_bytes(raw);path.symlink_to(target)
    elif damage=='modified':path.write_bytes(b'modified authored artifact')
    elif damage=='unlinked_leaf':path.unlink()
    with pytest.raises(ValueError):subject.artifact_check(output,result)


@pytest.fixture
def retained_capture(authored_request,tmp_path):
    request=deepcopy(authored_request)
    directory=tmp_path/'authored-retained-capture'
    observation=fixture_observation(request,directory)
    artifacts={'request.json':worker_capture._request(request),'stdout.json':worker_capture._wire(observation),
        'stderr.log':b'','router-allocation.duckdb':b'authored binary fixture never opened as a DB'}
    capture={'schema':worker_capture.SCHEMA,'request_sha256':sha(artifacts['request.json']),
        'request_bytes':len(artifacts['request.json']),
        'native_dispatch':{'module':'ipfs_accelerate_py.agent_supervisor.todo_daemon.supervisor_runtime',
            'method':'run_process_group_stream','path':str(worker_capture.RUNTIME_SOURCE),
            'sha256':sha(worker_capture._read(worker_capture.RUNTIME_SOURCE,256_000)),
            'actual_child_birth':{'pid':123,'start_time_ticks':456},'actual_process_invoked':True,
            'native_shared_parent_lease_used':True,'native_child_lease':{'cpu_slots':1,'memory_mb':256,'child_process_slots':1},
            'inherited_environment':False,'shell':False},'observation':observation,
        'output_artifacts':[{'relative_path':name,'bytes':len(artifacts[name]),'sha256':sha(artifacts[name])}
                            for name in ['request.json','stdout.json','stderr.log']],
        'current_head_observation_owned_by_caller':True,'provider_usage':None,
        'actual_external_provider_invocations':0,**worker_capture.FALSE}
    return dict(output_dir=directory,request=request,capture=capture,artifacts=artifacts)


def test_retained_observation_replay_never_spawns_or_reinvokes_consumer(retained_capture,monkeypatch):
    import router_consumer
    def forbidden(*_args,**_kwargs):pytest.fail('cold replay must not launch a child or invoke a consumer')
    monkeypatch.setattr(worker_capture,'launch_capture',forbidden)
    monkeypatch.setattr(context_worker,'execute_request',forbidden)
    monkeypatch.setattr(router_consumer,'capture_with_native_router',forbidden)
    observation,birth=subject.validate_capture(**retained_capture)
    assert observation==retained_capture['capture']['observation'] and birth==(123,456)


@pytest.mark.parametrize('damage',['request_file','request_hash','stderr','stdout','stdout_different_capture',
    'birth_bool','birth_missing','extra_dispatch','wrong_runtime_hash','wrong_runtime_path','wrong_method',
    'shell','inherited_env','missing_parent_lease','lease_float','lease_memory','consumer_flag_zero',
    'consumer_bytes_float','extra_store','extra_capture','authority_zero','extra_output','output_hash',
    'selection_flag_zero','selection_metadata','consumer_payload'])
def test_retained_capture_custody_birth_and_selected_payload_corruption_refuse(retained_capture,damage):
    data=retained_capture;capture=data['capture'];dispatch=capture['native_dispatch'];observation=capture['observation']
    if damage=='request_file':data['artifacts']['request.json']+=b' '
    elif damage=='request_hash':capture['request_sha256']='0'*64
    elif damage=='stderr':data['artifacts']['stderr.log']=b'authored unexpected stderr'
    elif damage=='stdout':data['artifacts']['stdout.json']+=b'\n'
    elif damage=='stdout_different_capture':observation['session_id']+='altered'
    elif damage=='birth_bool':dispatch['actual_child_birth']['pid']=True
    elif damage=='birth_missing':dispatch['actual_child_birth'].pop('start_time_ticks')
    elif damage=='extra_dispatch':dispatch['actual_provider_receipt']=True
    elif damage=='wrong_runtime_hash':dispatch['sha256']='0'*64
    elif damage=='wrong_runtime_path':dispatch['path']='/foreign/runtime.py'
    elif damage=='wrong_method':dispatch['method']='subprocess.run'
    elif damage=='shell':dispatch['shell']=True
    elif damage=='inherited_env':dispatch['inherited_environment']=True
    elif damage=='missing_parent_lease':dispatch['native_shared_parent_lease_used']=False
    elif damage=='lease_float':dispatch['native_child_lease']['cpu_slots']=1.0
    elif damage=='lease_memory':dispatch['native_child_lease']['memory_mb']=512
    elif damage=='extra_capture':capture['invented_execution_receipt']=True
    elif damage=='authority_zero':capture['proof_authority']=0
    elif damage=='extra_output':capture['output_artifacts'].append(deepcopy(capture['output_artifacts'][0]))
    elif damage=='output_hash':capture['output_artifacts'][0]['sha256']='0'*64
    else:
        if damage=='consumer_flag_zero':observation['consumer']['claims']['network_provider_invoked']=0
        elif damage=='consumer_bytes_float':observation['consumer']['input_bytes']=float(observation['consumer']['input_bytes'])
        elif damage=='extra_store':observation['consumer']['allocation_store']['invented_owner_receipt']=True
        elif damage=='selection_flag_zero':observation['selection']['proof_authority']=0
        elif damage=='selection_metadata':observation['selection']['reason']='invented routing proof'
        elif damage=='consumer_payload':observation['consumer']['input_sha256']='0'*64
        data['artifacts']['stdout.json']=worker_capture._wire(observation)
        capture['output_artifacts'][1]={'relative_path':'stdout.json','bytes':len(data['artifacts']['stdout.json']),
                                      'sha256':sha(data['artifacts']['stdout.json'])}
    with pytest.raises(ValueError):subject.validate_capture(**data)


@pytest.fixture
def declared_fault(retained_capture,tmp_path,monkeypatch):
    monkeypatch.setattr(subject,'ROOT',tmp_path)
    data=retained_capture
    parent=tmp_path/'authored-fault-artifacts'/'source_changed_after_spawn';parent.mkdir(parents=True)
    observation=deepcopy(data['capture']['observation'])
    observation['consumer']['allocation_store']['path']=str(parent/'router-allocation.duckdb')
    raw_stdout=worker_capture._wire(observation)
    files={**data['artifacts'],'stdout.json':raw_stdout}
    pins=[]
    for name,raw in sorted(files.items()):
        (parent/name).write_bytes(raw)
        pins.append({'relative_path':(parent/name).relative_to(tmp_path).as_posix(),'bytes':len(raw),'sha256':sha(raw)})
    output=tmp_path/'authored-run';output.mkdir()
    result={'native_head':deepcopy(data['request']['expected_head'])};result_raw=wire(result)
    fault={'schema':'terminal-context-worker-faults@1','qualified':True,'selected_run':output.name,
        'selected_result_sha256':sha(result_raw),'native_head':deepcopy(result['native_head']),
        'controls':[{'control':name,'refused':True,'error_class':'StaleCodebaseError' if calls else 'WorkerInputError',
            'message':'Authored consistency fixture; no actual fault observed.','consumer_calls':calls,**FALSE}
            for name,calls in [('overbudget_before_launch',0),('rewritten_history_before_launch',0),
                ('reordered_history_before_launch',0),('source_changed_after_spawn',1)]],
        'source_fault':{'mutation_after_actual_child_birth':True,'candidate_escaped':False,'source_restored':True,
                        'native_owner_reobserved':True,'actual_child_birth':{'pid':123,'start_time_ticks':456}},
        'artifact_pins':pins,'actual_extra_worker_children':1,'provider_usage':None,'source_body_execution':False,
        'actual_external_provider_invocations':0,**FALSE}
    return fault,output,result,result_raw,parent


def precondition(data):
    fault,output,result,result_raw,parent=data
    name='authored-fault-report.json';raw=wire(fault);(output.parent/name).write_bytes(raw)
    return subject.fault_precondition(name,output=output,result=result,result_raw=result_raw)


def test_fault_precondition_binds_extra_worker_files_without_current_pid_authority(declared_fault,monkeypatch):
    monkeypatch.setattr(worker_capture,'launch_capture',lambda **_kwargs:pytest.fail('no extra worker during cold'))
    raw,pin=precondition(declared_fault)
    assert pin=={'relative_path':'authored-fault-report.json','bytes':len(raw),'sha256':sha(raw)}


@pytest.mark.parametrize('damage',['missing_control','duplicate_control','extra_control','wrong_run','wrong_result','wrong_head',
    'provider','extra_children_bool','source_candidate_escaped','source_not_restored','no_birth','source_wrong_error',
    'prelaunch_consumer','postspawn_no_consumer','artifact_hash','missing_artifact','foreign_artifact','changed_stdout',
    'prelaunch_output_dir','unrecorded_fault_leaf','authority_zero','source_body'])
def test_fault_precondition_rejects_partial_flags_and_unbound_actual_extra_capture(declared_fault,damage):
    fault,_,_,_,parent=declared_fault
    if damage=='missing_control':fault['controls'].pop()
    elif damage=='duplicate_control':fault['controls'][1]=deepcopy(fault['controls'][0])
    elif damage=='extra_control':fault['controls'].append(deepcopy(fault['controls'][0]))
    elif damage=='wrong_run':fault['selected_run']='other'
    elif damage=='wrong_result':fault['selected_result_sha256']='0'*64
    elif damage=='wrong_head':fault['native_head']['generation']+=1
    elif damage=='provider':fault['actual_external_provider_invocations']=1
    elif damage=='extra_children_bool':fault['actual_extra_worker_children']=True
    elif damage=='source_candidate_escaped':fault['source_fault']['candidate_escaped']=True
    elif damage=='source_not_restored':fault['source_fault']['source_restored']=False
    elif damage=='no_birth':fault['source_fault']['actual_child_birth'].pop('pid')
    elif damage=='source_wrong_error':fault['controls'][-1]['error_class']='LeaseTimeoutError'
    elif damage=='prelaunch_consumer':fault['controls'][0]['consumer_calls']=1
    elif damage=='postspawn_no_consumer':fault['controls'][-1]['consumer_calls']=0
    elif damage=='artifact_hash':fault['artifact_pins'][0]['sha256']='0'*64
    elif damage=='missing_artifact':fault['artifact_pins'].pop()
    elif damage=='foreign_artifact':fault['artifact_pins'][0]['relative_path']='../private/request.json'
    elif damage=='changed_stdout':(parent/'stdout.json').write_bytes(b'changed')
    elif damage=='prelaunch_output_dir':(parent.parent/'overbudget_before_launch').mkdir()
    elif damage=='unrecorded_fault_leaf':(parent/'unexpected.json').write_bytes(b'authored')
    elif damage=='authority_zero':fault['proof_authority']=0
    elif damage=='source_body':fault['source_body_execution']=True
    with pytest.raises(ValueError):precondition(declared_fault)
