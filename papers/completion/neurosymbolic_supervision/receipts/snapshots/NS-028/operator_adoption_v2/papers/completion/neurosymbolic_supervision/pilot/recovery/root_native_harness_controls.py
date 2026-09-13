"""Actual native control calls; constructed variants never execute science."""
import sys
sys.dont_write_bytecode = True
import hashlib, json, os, pathlib, resource, time

P = pathlib.Path
CONFIG = json.loads(P('/qualification/invocation.json').read_text())
SOURCE_REL = 'external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/semantic_state/harness.py'
EVIDENCE_REL = 'papers/completion/neurosymbolic_supervision/pilot/recovery/root_native_harness_execution.json'
LOG_REL = 'papers/completion/neurosymbolic_supervision/pilot/recovery/root_native_harness_execution.log'
started = time.monotonic()
cpu = time.process_time()

def sha(path):
    return hashlib.sha256(P(path).read_bytes()).hexdigest()

def audit(event, args):
    if event == 'subprocess.Popen' or event in ('socket.connect', 'socket.connect_ex', 'socket.bind'):
        raise RuntimeError('native control qualification cannot create processes or network endpoints')

def main():
    os.umask(0o077)
    os.environ.update(IPFS_ACCEL_SKIP_CORE='1', IPFS_AUTO_INSTALL='false', IPFS_DATASETS_AUTO_INSTALL='false', IPFS_KIT_AUTO_INSTALL='false', PYTHONDONTWRITEBYTECODE='1')
    roots = [CONFIG['accelerate_source'], CONFIG['datasets_source'], CONFIG['kit_source'], CONFIG['runtime_python']]
    for path in roots:
        assert P(path).is_absolute() and P(path).is_dir()
    sys.path[:0] = roots
    sys.addaudithook(audit)
    from ipfs_accelerate_py.agent_supervisor.semantic_state import harness as H
    source = P(CONFIG['accelerate_source'])/'ipfs_accelerate_py/agent_supervisor/semantic_state/harness.py'
    assert P(H.__file__).resolve() == source and sha(source) == CONFIG['source_sha256']
    assert all(callable(getattr(H, name)) for name in ('admit_final_attempt','source_bound_current_profile_check','refuse_automatic_pilot_replay'))
    current = {SOURCE_REL: sha(source)}
    freeze = {'schema': H.FINAL_EXPERIMENT_FREEZE_SCHEMA, 'final_dispatch_authorized': False, 'first_final_attempt_started': False, 'immutable_pins': current, 'retained_executable_arms': ['A','B'], 'arm_useful_paths': {}, 'developmental_task_ids': ['ns-hist-07-idna'], 'developmental_family_ids': ['upstream:kjd/idna'], 'final_task_ids': [], 'final_family_ids': [], 'removed_arms': {}}
    freeze['freeze_sha256'] = H._sha256_canonical(freeze)
    actual = H.source_bound_current_profile_check(freeze, current)
    assert actual['current'] is True and actual['reasons'] == []
    missing = H.source_bound_current_profile_check(None, current)
    assert missing['current'] is False and missing['missing_freeze'] is True
    stale = H.source_bound_current_profile_check(freeze, {SOURCE_REL: '0'*64})
    assert stale['current'] is False and stale['stale'] is True and stale['mismatched'] == [SOURCE_REL]
    missing_current = H.source_bound_current_profile_check(freeze, {})
    assert missing_current['current'] is False and missing_current['missing_current'] == [SOURCE_REL]
    damaged_freeze = dict(freeze, freeze_sha256='0'*64)
    damaged = H.source_bound_current_profile_check(damaged_freeze, current)
    assert damaged['current'] is False and 'freeze_sha256_mismatch' in damaged['reasons']
    request = {'record_kind':'final','split':'final','task_id':'normal-control-only-final-id','family_id':'normal-control-only-final-family','arm':'A','final_freeze_sha256':freeze['freeze_sha256']}
    final = H.admit_final_attempt(freeze, request)
    assert final['admitted'] is False and 'final_dispatch_not_authorized' in final['reasons'] and final['first_final_attempt_started'] is False
    no_freeze = H.admit_final_attempt(None, request)
    assert no_freeze['admitted'] is False and 'missing_final_experiment_freeze' in no_freeze['reasons']
    stale_admission = H.admit_final_attempt(damaged_freeze, request)
    assert stale_admission['admitted'] is False and 'freeze_sha256_mismatch' in stale_admission['reasons']
    pilot = H.admit_final_attempt(freeze, dict(request, split='pilot', task_id='ns-hist-07-idna', family_id='upstream:kjd/idna'))
    assert pilot['admitted'] is False and 'developmental_task_in_final' in pilot['reasons']
    consumed = H.refuse_automatic_pilot_replay({'terminal':True,'provider_invoked':True,'reservation_consumed':True}, {'record_kind':'pilot','retry':True})
    assert consumed['replay_allowed'] is False and consumed['action'] == 'retain_terminal' and 'consumed_reservation_no_replay' in consumed['reasons']
    unknown = H.refuse_automatic_pilot_replay({'terminal':False,'unknown_effect':True,'reservation_consumed':True}, {'record_kind':'pilot','automatic_replay':True})
    assert unknown['replay_allowed'] is False and unknown['terminal'] is False and 'unknown_effect_must_remain' in unknown['reasons']
    pending = H.refuse_automatic_pilot_replay({'terminal':False,'status':'pending_operator_inputs'}, {'record_kind':'pilot'})
    assert pending['replay_allowed'] is False and pending['terminal'] is False and pending['action'] == 'repoll_same_cell'
    assert sha(source) == current[SOURCE_REL]
    checks = {k:True for k in ('native_import','admit_final_attempt','missing_freeze_refused','stale_freeze_refused','current_source_profile','consumed_replay_refused')}
    result = {'schema':'ns028-root-native-harness-execution/v1','executed':True,'fixture':False,'execution_kind':'actual_native_python_import_and_call','source_path':SOURCE_REL,'source_sha256':sha(source),'actual_import_path':str(source),'checks':checks,'command':{'argv':CONFIG['actual_python_argv'],'exit_code':0,'log':LOG_REL},'normal_control_inputs_constructed':True,'control_scope':'Actual native Python methods and real caller-computed source bytes. Missing/stale/consumed mapping variants are normal negative controls, not historical/scientific outcomes. This receipt is not a scientific freeze or execution grant.','caller_current_file_hashes':current,'qualification_only_freeze_sha256':freeze['freeze_sha256'],'results':{'current':actual,'missing':missing,'stale':stale,'missing_current':missing_current,'damaged':damaged,'final_refusal':final,'missing_admission':no_freeze,'stale_admission':stale_admission,'pilot_refusal':pilot,'consumed':consumed,'unknown':unknown,'pending':pending},'native_state_or_coordinator_queries':0,'native_state_mutations':0,'provider_calls':0,'scorer_calls':0,'scientific_or_final_executions':0,'scientific_or_final_admission':False,'authoring_claim_execution':False,'scope_limit':'These APIs are metadata predicates. Actual signed host/client one-use custody remains separately enforced by the reviewed service; this run does not prove native coordinator reservation exclusion or scientific completion.','cpu_seconds':time.process_time()-cpu,'wall_seconds':time.monotonic()-started,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
    out=P('/qualification-output')
    raw=(json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
    fd=os.open(out/'root_native_harness_execution.json',os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'wb')as f:f.write(raw);f.flush();os.fsync(f.fileno())
    print(json.dumps({'schema':'ns028-native-control-log/v1','native_source_sha256':sha(source),'checks':checks,'actual_control_calls':12,'scientific_executions':0,'receipt_sha256':hashlib.sha256(raw).hexdigest()},sort_keys=True),flush=True)

if __name__ == '__main__':
    main()
