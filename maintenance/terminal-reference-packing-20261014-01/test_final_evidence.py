"""Authored data-only fixtures exercise the final evidence joins and drift guards."""
from copy import deepcopy
import json
import pytest
from finalize_stage import validate_report_bindings,verify_selected_report_bytes
from packing_verify import artifact_check, FILES, fault_precondition
from packing_io import wire,sha

def reports():
    result={'native_head':{'generation':1},'artifact_pins':[]}
    raw=wire(result);pins=[{'path':'/authored-fixture/producer.py','bytes':12,'sha256':'1'*64}]
    fault_name='authored-fault-fixture.json'
    faults={'qualified':True,'selected_run':'authored-run','selected_result_sha256':sha(raw)}
    fault_raw=wire(faults)
    cold={'qualified':True,'selected_run':'authored-run','selected_result_sha256':sha(raw),
        'selected_native_head':result['native_head'],'selected_artifact_pins_sha256':sha(wire(result['artifact_pins'])),
        'qualified_faults_verified_before_positive_replay':True,
        'preceding_fault_report':{'relative_path':fault_name,'bytes':len(fault_raw),'sha256':sha(fault_raw)}}
    processes={name:{'qualified':True,'kind':kind,'selected_run':'authored-run','before':deepcopy(pins),'after':deepcopy(pins)}
        for name,kind in [('process','run'),('tests','test'),('cold_process','cold'),('fault_process','fault')]}
    processes['tests']['tests']={'tests':1,'failures':0,'errors':0,'skipped':0}
    return dict(run='authored-run',result=result,result_raw=raw,cold=cold,faults=faults,
        fault_name=fault_name,fault_raw=fault_raw,**processes)

def test_same_result_scope_and_producer_fixtures_join():
    validate_report_bindings(**reports())

@pytest.mark.parametrize('report',['process','cold','cold_process','faults','fault_process'])
def test_reports_from_another_run_refused(report):
    data=reports();data[report]['selected_run']='different-run'
    with pytest.raises(ValueError,match='selected run'):validate_report_bindings(**data)

@pytest.mark.parametrize('report',['cold','faults'])
def test_result_replaced_even_with_rebuilt_artifact_pins_refused(report):
    data=reports();data[report]['selected_result_sha256']='0'*64
    with pytest.raises(ValueError,match='exact selected result'):validate_report_bindings(**data)

@pytest.mark.parametrize('field',['selected_native_head','selected_artifact_pins_sha256'])
def test_cold_owner_or_artifact_scope_substitution_refused(field):
    data=reports();data['cold'][field]='changed'
    with pytest.raises(ValueError,match='complete artifact scope'):validate_report_bindings(**data)

def test_positive_cold_without_preceding_fault_dependency_refused():
    data=reports();del data['cold']['preceding_fault_report']
    with pytest.raises(ValueError,match='preceding faults'):validate_report_bindings(**data)

def test_fault_report_changed_after_cold_refused():
    data=reports();data['fault_raw']+=b' '
    with pytest.raises(ValueError,match='preceding faults'):validate_report_bindings(**data)

@pytest.mark.parametrize('report',['process','tests','cold_process','fault_process'])
def test_wrong_process_kind_refused(report):
    data=reports();data[report]['kind']='authored-wrong-kind'
    with pytest.raises(ValueError,match='process kind'):validate_report_bindings(**data)

@pytest.mark.parametrize('report',['process','tests','fault_process'])
def test_regression_or_run_from_old_producer_version_refused(report):
    data=reports();data[report]['before'][0]['sha256']='0'*64;data[report]['after'][0]['sha256']='0'*64
    with pytest.raises(ValueError,match='producer pins'):validate_report_bindings(**data)

def test_producer_mutated_during_a_selected_process_refused():
    data=reports();data['cold_process']['before'][0]['sha256']='0'*64
    with pytest.raises(ValueError,match='producer pins'):validate_report_bindings(**data)

def test_selected_artifact_drift_refused_even_after_an_earlier_positive_check(tmp_path):
    rows=[]
    for name in sorted(FILES):
        raw=wire({'authored_fixture':name});(tmp_path/name).write_bytes(raw)
        rows.append({'relative_path':name,'bytes':len(raw),'sha256':sha(raw)})
    result={'artifact_pins':rows};artifact_check(tmp_path,result)
    (tmp_path/'contexts.json').write_bytes(b'{}')
    with pytest.raises(ValueError,match='selected artifact changed'):artifact_check(tmp_path,result)

def test_fault_precondition_from_wrong_result_refused(tmp_path,monkeypatch):
    import packing_verify as verify
    monkeypatch.setattr(verify,'ROOT',tmp_path)
    raw=wire({'schema':'terminal-reference-packing-fault-controls@1','qualified':True,
        'selected_run':'authored-run','selected_result_sha256':'0'*64,'native_head':{'generation':1}})
    (tmp_path/'authored-fault.json').write_bytes(raw)
    with pytest.raises(ValueError,match='exact result'):
        fault_precondition('authored-fault.json',{'selected_run':'authored-run','native_head':{'generation':1}},b'authored result')

def test_exact_selected_reports_remain_stable(tmp_path):
    raw=b'{"authored_fixture":true}';(tmp_path/'report.json').write_bytes(raw)
    verify_selected_report_bytes(tmp_path,{'report.json':raw})

def test_selected_cold_or_fault_report_changed_during_finalization_refused(tmp_path):
    raw=b'{"authored_fixture":true}';(tmp_path/'report.json').write_bytes(b'{}')
    with pytest.raises(ValueError,match='report changed'):
        verify_selected_report_bytes(tmp_path,{'report.json':raw})
