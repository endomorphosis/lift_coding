"""Fault evidence joins over authored data, not genuine child fault receipts.

Four fresh native signing/task fixtures are real. All worker, birth and DB-leaf
bytes are explicitly synthetic validator data; no child or provider is invoked.
"""
from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile

import pytest

import admission_verify as subject
import planning_job
import planning_permit
import router_consumer
import worker_capture
from admission_io import FALSE,wire,sha
from test_worker_capture import authored_request as request_fixture,fixture_observation

CASES=('request_changed','output_exists','claim_released','source_changed_after_spawn')


@pytest.fixture(scope='module')
def fault_fixture():
    with tempfile.TemporaryDirectory(prefix='.authored-fault-evidence-',dir=subject.ROOT) as directory:
        root=Path(directory);output=root/'selected';output.mkdir()
        label='authored';prefix=root/(label+'-artifacts');prefix.mkdir()
        request=deepcopy(request_fixture.__wrapped__())
        request.update(request_id='headless-terminal:adaptive:0',session_id='headless-terminal:adaptive',delivery_mode='adaptive')
        body=b"raise RuntimeError('repository source must never execute')\ndef add(a: int, b: int) -> int:\n    return a + b\n"
        instruction="  Preserve every source and unresolved instruction. π\n\n".encode()
        path='authored-task/environment/unit.py'
        corpus={'tasks':[{'task_id':'headless-terminal'}]};bodies={path:body};instructions={'headless-terminal':instruction}
        expected=subject.input_binding(request=request,structural={'head':request['expected_head']},
            corpus=corpus,bodies=bodies,instructions=instructions)
        reports={}
        for case in CASES:
            parent=prefix/case;parent.mkdir()
            private=Path(tempfile.mkdtemp(prefix='authored-fault-signing-'))
            with planning_job.create_owned_planning_job(job_repository=parent/'repository',private_root=private,
                    public_output=parent/'admission',input_binding=expected,task_key='fault-'+case.replace('_','-')) as job:
                reports[case]=job.report
        parent=prefix/'source_changed_after_spawn';capture_dir=parent/'capture';capture_dir.mkdir()
        observation=fixture_observation(request,capture_dir)
        observation['consumer']['schema']=router_consumer.SCHEMA
        proof={'schema':planning_permit.SCHEMA,'scope':'planning-observation-only','worker_mode':'localcapture',
            'native_coordinator_claim_fenced_before_after':True,'single_use_owner_permit_consumed':True,
            'worker_birth_acknowledged_before_stdin':True,'native_job_binding':reports['source_changed_after_spawn']['job_binding'],
            'request_binding':planning_permit.planning_request_binding(request),'claim_binding_sha256':'a'*64,
            'launch_binding_sha256':sha(wire(worker_capture.capture_launch_binding(capture_dir))),
            'actual_worker_birth':{'pid':123,'start_time_ticks':456,'uid':os.geteuid(),'parent_pid':12,'boot_id':'authored-synthetic-birth'},
            'provider_usage':None,'actual_external_provider_invocations':0,**planning_permit.CLAIMS}
        leaves={'request.json':worker_capture._request(request),'stdout.json':wire(observation),'stderr.log':b'',
            'router-allocation.duckdb':b'authored placeholder, never opened as a database'}
        for name,raw in leaves.items():(capture_dir/name).write_bytes(raw)
        capture={'schema':worker_capture.SCHEMA,'request_sha256':sha(leaves['request.json']),'request_bytes':len(leaves['request.json']),
            'native_dispatch':{'module':'ipfs_accelerate_py.agent_supervisor.todo_daemon.supervisor_runtime',
                'method':'run_process_group_stream','path':str(worker_capture.RUNTIME_SOURCE),
                'sha256':sha(worker_capture._read(worker_capture.RUNTIME_SOURCE,256000)),
                'actual_child_birth':{'pid':123,'start_time_ticks':456},'actual_process_invoked':True,
                'native_shared_parent_lease_used':True,'native_child_lease':{'cpu_slots':1,'memory_mb':256,'child_process_slots':1},
                'inherited_environment':False,'shell':False},'observation':observation,
            'output_artifacts':[{'relative_path':name,'bytes':len(leaves[name]),'sha256':sha(leaves[name])}
                for name in ('request.json','stdout.json','stderr.log')],
            'current_head_observation_owned_by_caller':True,'provider_usage':None,
            'actual_external_provider_invocations':0,'planning_admission':proof,**worker_capture.FALSE}
        (parent/'refused-candidate-capture.json').write_bytes(wire(capture))
        main={'schema':'terminal-planning-admitted-deliveries@1','deliveries':[
            {'task_id':'headless-terminal','delivery_mode':'adaptive','request':request}]}
        main_raw=wire(main);(output/'deliveries.json').write_bytes(main_raw)
        result={'native_head':request['expected_head'],'artifact_pins':[{'relative_path':'deliveries.json',
            'bytes':len(main_raw),'sha256':sha(main_raw)}]};result_raw=wire(result)
        controls=[{'case':case+suffix,'rejected':True,
            'exception_class':'StaleCodebaseError' if case=='source_changed_after_spawn' and not suffix else 'AuthoredRefusal',
            'message':'Authored synthetic refusal data, not a real fault run.',
            'actual_child_spawned':case=='source_changed_after_spawn' and not suffix,'original_source_restored':True}
            for case in CASES for suffix in ('','-replay')]
        fault={'schema':'terminal-planning-admission-faults@1','qualified':True,'selected_run':output.name,
            'selected_result_sha256':sha(result_raw),'native_head':request['expected_head'],'controls':controls,
            'artifact_pins':[],'actual_extra_worker_children':1,'actual_external_provider_invocations':0,
            'provider_usage':None,'source_body_execution':False,'private_authority_destroyed':True,
            'original_source_restored':True,**FALSE}
        files={path.relative_to(root).as_posix():path.read_bytes() for path in root.rglob('*')
            if path.is_file() and '.git' not in path.relative_to(root).parts}
        yield {'root':root,'output':output,'prefix':prefix,'name':label+'-fault-report.json',
            'fault':fault,'result':result,'result_raw':result_raw,'inputs':(corpus,bodies,instructions,[]),'files':files}


@pytest.fixture
def evidence(fault_fixture,monkeypatch):
    base=fault_fixture;root=base['root']
    for path in root.rglob('*'):
        if path.is_file() and '.git' not in path.relative_to(root).parts and path.relative_to(root).as_posix() not in base['files']:
            path.unlink()
    for name,raw in base['files'].items():(root/name).write_bytes(raw)
    monkeypatch.setattr(subject,'ROOT',root)
    monkeypatch.setattr(subject,'inputs',lambda:deepcopy(base['inputs']))
    return {**base,'fault':deepcopy(base['fault']),'result':deepcopy(base['result'])}


def publish(evidence):
    fault=evidence['fault'];prefix=evidence['prefix']
    fault['artifact_pins']=[{'path':str(path),'bytes':len(path.read_bytes()),'sha256':sha(path.read_bytes())}
        for path in sorted(prefix.rglob('*')) if path.is_file() and '.git' not in path.relative_to(prefix).parts]
    raw=wire(fault);(evidence['root']/evidence['name']).write_bytes(raw)
    return raw


def check(evidence):
    return subject.fault_precondition(evidence['name'],output=evidence['output'],
        result=evidence['result'],result_raw=evidence['result_raw'])


def test_historical_fault_joins_are_consistent_data_without_live_authority(evidence,monkeypatch):
    def forbidden(*args,**kwargs):pytest.fail('fault evidence replay must not recreate live authority or execute a worker')
    monkeypatch.setattr(planning_job,'verify_planning_job',forbidden)
    monkeypatch.setattr(planning_permit,'issue_planning_permit',forbidden)
    monkeypatch.setattr(worker_capture,'launch_admitted_capture',forbidden)
    raw=publish(evidence)
    assert check(evidence)==(raw,{'relative_path':evidence['name'],'bytes':len(raw),'sha256':sha(raw)})


@pytest.mark.parametrize('damage',['missing_job','missing_capture','missing_candidate','unsigned_job','wrong_job_case',
    'changed_source','changed_instruction','wrong_input_file','changed_validator','wrong_candidate_job','wrong_request',
    'wrong_birth','stderr','stdout','consumer_authority','capture_authority','unrelated_main_request','missing_main_pin',
    'main_hash','one_control','reordered_controls','wrong_extra_count','bool_extra_count','promoted_claim'])
def test_fault_scope_signatures_source_and_candidate_joins_reject(evidence,damage):
    prefix=evidence['prefix'];source=prefix/'source_changed_after_spawn';fault=evidence['fault']
    report_path=prefix/'request_changed/admission/planning-job.json'
    if damage=='missing_job':report_path.unlink()
    elif damage=='missing_capture':(source/'capture/router-allocation.duckdb').unlink()
    elif damage=='missing_candidate':(source/'refused-candidate-capture.json').unlink()
    elif damage in {'unsigned_job','wrong_job_case','changed_source','changed_instruction'}:
        report=json.loads(report_path.read_bytes())
        if damage=='unsigned_job':report['native_admission']['receipt']['binding']['signature']='not-a-signature'
        elif damage=='wrong_job_case':report=json.loads((prefix/'output_exists/admission/planning-job.json').read_bytes())
        elif damage=='changed_source':report['job_binding']['input_binding']['source_records'][0]['source_text']='changed'
        else:report['job_binding']['input_binding']['instructions'][0]['instruction_text']='changed'
        report_path.write_bytes(wire(report))
    elif damage=='wrong_input_file':(prefix/'claim_released/repository/input-binding.json').write_bytes(b'{}')
    elif damage=='changed_validator':(prefix/'claim_released/repository/validate-planning-observation.py').write_bytes(b'print("different")')
    elif damage in {'wrong_candidate_job','wrong_request','wrong_birth','consumer_authority','capture_authority'}:
        path=source/'refused-candidate-capture.json';capture=json.loads(path.read_bytes())
        if damage=='wrong_candidate_job':capture['planning_admission']['native_job_binding']=json.loads(report_path.read_bytes())['job_binding']
        elif damage=='wrong_request':capture['request_sha256']='0'*64
        elif damage=='wrong_birth':capture['planning_admission']['actual_worker_birth']['pid']+=1
        elif damage=='consumer_authority':capture['observation']['consumer']['claims']['network_provider_invoked']=True
        else:capture['planning_admission']['original_task_coverage']=True
        path.write_bytes(wire(capture))
    elif damage=='stderr':(source/'capture/stderr.log').write_bytes(b'authored unexpected error')
    elif damage=='stdout':(source/'capture/stdout.json').write_bytes(b'{}')
    elif damage=='unrelated_main_request':
        path=evidence['output']/'deliveries.json';main=json.loads(path.read_bytes())
        main['deliveries'][0]['request']['session_id']='unrelated-session';raw=wire(main);path.write_bytes(raw)
        evidence['result']['artifact_pins'][0].update(bytes=len(raw),sha256=sha(raw))
    elif damage=='missing_main_pin':evidence['result']['artifact_pins']=[]
    elif damage=='main_hash':evidence['result']['artifact_pins'][0]['sha256']='0'*64
    elif damage=='one_control':fault['controls']=fault['controls'][:1]
    elif damage=='reordered_controls':fault['controls'].reverse()
    elif damage=='wrong_extra_count':fault['actual_extra_worker_children']=0
    elif damage=='bool_extra_count':fault['actual_extra_worker_children']=True
    elif damage=='promoted_claim':fault['proof_authority']=True
    publish(evidence)
    with pytest.raises(ValueError):check(evidence)

