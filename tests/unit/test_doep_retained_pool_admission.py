"""Actual owner reads plus exact native projection validation, without release."""
from copy import deepcopy
from dataclasses import replace
import hashlib
import importlib.util
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('doep_retained_admission_test', ROOT / 'scripts/ops/agent_supervisor/retained_pool_admission.py')
admission = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(admission)
TASK = 'sha256:' + '1' * 64
UNKNOWN = 'sha256:' + '3' * 64
ATTEMPT = 'attempt:' + 'a' * 32
TOKEN = '123456789abc-abcdef123456'


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True))


@pytest.fixture
def native(tmp_path, monkeypatch):
    from test.api.causal_federation.test_typed_state_owner import _gateway, _install
    from ipfs_accelerate_py.agent_supervisor.merge.worktree_lifecycle import (
        WorktreeLifecycleStore, WorkspaceLifecycleRecord, WorkspaceLifecycleState, current_process_birth,
    )
    from ipfs_accelerate_py.agent_supervisor.task_sources.typed_state_owner import (
        TYPED_STATE_OWNER_SOCKET_FILENAME, TYPED_STATE_OWNER_TOKEN_FILENAME, compact_default_owner_socket_path,
    )
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.database_portal_bridge import _projection_immutable_digest
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import parse_task_text, portal_task_identity
    from test.api.test_implementation_supervisor_control_plane_pool_lease import _seed_active_database_pool_lease
    # Build a genuine bridge fixture, then recreate its path-bound projection
    # at the native DOEP namespace. No projection/custody checker is mocked.
    (tmp_path / 'seed').mkdir()
    seeded = _seed_active_database_pool_lease(tmp_path / 'seed', task_alias='DOEP-032',
        database_task_cid=TASK, attempt_id=ATTEMPT, database_attempt_number=1)
    repo = seeded['repo']
    runtime = repo / 'native-runtime'
    state_dir = runtime / 'state/lane-2/doep_lane_2_database_portal_attempts' / hashlib.sha256(ATTEMPT.encode()).hexdigest()[:24]
    state_dir.mkdir(parents=True)
    projection_path = state_dir / 'task-projection.md'
    projection = seeded['projection_path'].read_text()
    projection_path.write_text(projection)
    binding = deepcopy(seeded['binding'])
    binding['projection_seed_digest'] = 'sha256:' + hashlib.sha256(projection.encode()).hexdigest()
    binding['projection_immutable_digest'] = _projection_immutable_digest(projection)
    binding.pop('binding_id')
    binding['binding_id'] = 'sha256:' + hashlib.sha256(json.dumps(binding, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()
    write(state_dir / 'database-attempt-binding.json', binding)
    task = parse_task_text(projection, path=projection_path, task_header_prefix='## DOEP-032')[0]
    identity = portal_task_identity(task, todo_path=projection_path)
    workspace = runtime / 'worktrees' / ('workspace_' + TOKEN.replace('-', '_'))
    workspace.mkdir(parents=True)
    birth = current_process_birth()
    record = WorkspaceLifecycleRecord(task_id='DOEP-032', canonical_task_cid=identity.canonical_task_cid,
        attempt=2, lane_id='lane2', state=WorkspaceLifecycleState.TERMINAL, owner=birth,
        lease_id='preserved-native-lease', fence=4, workspace_path=str(workspace), branch=binding['task_alias'],
        merge_target='main', created_at=1, updated_at=2, expires_at=999, repo_root=str(repo),
        state_dir=str(state_dir), terminal_reason='verification_deferred_checkout_lease_unavailable')
    lifecycle_path = WorktreeLifecycleStore(repo).workspace_path_for(workspace)
    write(lifecycle_path, record.to_dict())
    pool_path = runtime / 'worktrees/.pool-state' / (TOKEN + '.json')
    write(pool_path, {'schema':'agent-supervisor-worktree-pool-v1', 'state':'leased', 'lease_token':TOKEN,
        'repo_root':str(repo), 'path':str(workspace), 'branch':record.branch, 'lease_pid':os.getpid()})
    write(pool_path.with_suffix('.lock'), {'pid':os.getpid()})
    write(state_dir / 'portal-task-state.json', {'implementation_in_progress':False, 'active_task_id':'',
                                              'release_authorized':True, 'completion_authority':True})
    write(state_dir / 'portal-events.jsonl', {'type':'implementation_finished', 'release_authorized':True})
    spec = importlib.util.spec_from_file_location('doep_admission_native_test', ROOT / 'scripts/ops/agent_supervisor/direct_objective_event_driven_planning_handoff.py')
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    database = tmp_path / 'control.duckdb'; _install(database)
    owner_dir = tmp_path / 'owner'; owner_dir.mkdir()
    gateway, connection = _gateway(database, compact_default_owner_socket_path(owner_dir / TYPED_STATE_OWNER_SOCKET_FILENAME, identity=database))
    (owner_dir / TYPED_STATE_OWNER_TOKEN_FILENAME).write_text(gateway.configure_status_bootstrap())
    result = connection.execute('SELECT * FROM tasks')
    from ipfs_accelerate_py.agent_supervisor.task_sources.typed_state_owner import _result_columns
    columns = _result_columns(result)
    raw = result.fetchone()
    row = dict(raw)
    body = {'board_namespace':m.PROGRAM_ID, 'completion_receipt':{'attempt_id':ATTEMPT, 'operation':'database_portal_terminal_failure'}}
    row.update(task_cid=TASK, task_alias='DOEP-032', plan_cid='plan:sealed', status='blocked',
               body_json=json.dumps(body), identity_json=json.dumps({'repository_tree_id':'tree:sealed'}), revision=1)
    connection.execute('DELETE FROM tasks')
    connection.execute('INSERT INTO tasks VALUES (' + ','.join('?' for _ in columns) + ')', [row[c] for c in columns])
    unknown_body = {'board_namespace':m.PROGRAM_ID, 'completion_receipt':{'attempt_id':'attempt:b553-original', 'failure_kind':'provider_callback_outcome_unknown'}}
    unknown = {**row, 'task_cid':UNKNOWN, 'task_alias':'DOEP-031', 'status':'quarantined', 'body_json':json.dumps(unknown_body)}
    connection.execute('INSERT INTO tasks VALUES (' + ','.join('?' for _ in columns) + ')', [unknown[c] for c in columns])
    for cid, status, value in [(TASK,'blocked',body),(UNKNOWN,'quarantined',unknown_body)]:
        connection.execute('INSERT INTO task_revisions VALUES (?,1,?,?,?)', [cid,status,json.dumps(value),'historical-time'])
    population = {'tasks':[{'task_alias':'DOEP-032','task_cid':TASK},{'task_alias':'DOEP-031','task_cid':UNKNOWN}],
                  'goals':[{}], 'plan_root_cid':'plan:sealed', 'repository_tree_id':'tree:sealed'}
    board = SimpleNamespace(resolved_database_program=lambda:SimpleNamespace(store_generation='control.duckdb', quack_endpoint='quack:127.0.0.1:27942'))
    status_path = owner_dir / 'quack-state-server.status.json'
    write(status_path, {'lifecycle':'ready', 'identity':{**gateway.identity,'process_birth':birth.to_dict()}})
    monkeypatch.setattr(m, '_load', lambda:(board,population,{'owner':owner_dir,'owner_status':status_path,'database':database,'root':runtime}))
    m._bind_native_status(gateway, population)
    observed = m.authoritative_status(history_tasks=['DOEP-032'])
    request = {'schema':admission.REQUEST_SCHEMA, 'task_alias':'DOEP-032','task_cid':TASK,'task_revision':1,
        'attempt_id':ATTEMPT,'binding_id':binding['binding_id'],'pool_lease_token':TOKEN,'pool_owner':birth.to_dict(),
        'lifecycle_lease_id':record.lease_id,'lifecycle_fence':record.fence,
        'owner_identity':{k:observed['owner_identity'][k] for k in admission.OWNER_KEYS},
        'store_generation':observed['store_generation']}
    def call(value=None, observer=None, source=None):
        return admission.release_admission(request if value is None else value, repo_root=repo, runtime_root=runtime,
            observe_status=observer or m.authoritative_status, observe_source=source or (lambda:{'source_admitted':True,'qualified_test_source':'unchanged'}))
    yield SimpleNamespace(call=call, request=request, connection=connection, gateway=gateway, module=m,
        runtime=runtime, lifecycle=lifecycle_path, pool=pool_path, state_dir=state_dir, body=body,
        status=m.authoritative_status)
    gateway.stop(); connection.close()


def test_actual_canonical_history_and_local_terminal_evidence_never_release(native):
    before = native.connection.execute('SELECT * FROM tasks ORDER BY task_cid').fetchall()
    history_before = native.connection.execute('SELECT * FROM task_revisions ORDER BY task_cid, revision').fetchall()
    files = {p:p.read_bytes() for p in native.runtime.rglob('*') if p.is_file()}
    result = native.call()
    assert result['disposition'] == 'deferred', result
    assert result['release_authorized'] is False and result['mutations_performed'] is False
    assert result['canonical_task_observation']['task_status'] == 'blocked'
    assert result['canonical_task_observation']['canonical_terminal_receipt_present'] is True
    assert result['local_terminal_lifecycle_verified'] is True
    assert {v['kind'] for v in result['missing_evidence']} >= {'canonical_callback_effect_settlement','historical_retained_candidate_receipt','exact_retained_pool_release_grant'}
    assert native.connection.execute('SELECT * FROM tasks ORDER BY task_cid').fetchall() == before
    assert native.connection.execute('SELECT * FROM task_revisions ORDER BY task_cid, revision').fetchall() == history_before
    assert all(p.read_bytes() == raw for p,raw in files.items())


@pytest.mark.parametrize('change,reason', [
    ('owner','native_owner_identity_mismatch'),('generation','native_store_generation_mismatch'),
    ('lease','lifecycle_lease_or_fence_mismatch'),('fence','lifecycle_lease_or_fence_mismatch'),
    ('pool-owner','lifecycle_owner_mismatch'),('binding','database_attempt_binding_mismatch'),
    ('task-revision','native_task_scope_mismatch'),('unknown031','task_outside_retained_release_scope'),
    ('injected-authority','request_schema_invalid'),
])
def test_wrong_exact_scope_rejected_without_mutation(native, change, reason):
    request = deepcopy(native.request)
    if change=='owner':request['owner_identity']['server_id']='server:foreign'
    elif change=='generation':
        from ipfs_accelerate_py.agent_supervisor.task_sources.control_plane_contracts import StoreGeneration
        value = StoreGeneration.from_dict(request['store_generation']);request['store_generation']=replace(value,revision=value.revision+1).to_record()
    elif change=='lease':request['lifecycle_lease_id']='foreign-lease'
    elif change=='fence':request['lifecycle_fence']+=1
    elif change=='pool-owner':request['pool_owner']['start_time_ticks']+=1
    elif change=='binding':request['binding_id']='sha256:'+'f'*64
    elif change=='task-revision':request['task_revision']+=1
    elif change=='unknown031':request['task_alias']='DOEP-031';request['task_cid']=UNKNOWN
    else:request['independent_callback_settlement']={'release_authorized':True}
    before=native.pool.read_bytes(); result=native.call(request)
    assert result['disposition']=='rejected', result
    assert result['reason_codes']==[reason]
    assert native.pool.read_bytes()==before
    assert result['release_authorized'] is False


def test_actual_canonical_unknown_and_missing_receipt_give_task_specific_blockers(native):
    body={**native.body,'completion_receipt':{'attempt_id':ATTEMPT,'failure_kind':'provider_callback_outcome_unknown','release_authorized':True}}
    for value,reason in [(body,'bound_terminal_receipt_reports_unknown'),({'board_namespace':native.module.PROGRAM_ID},'absent_from_bound_task_history_head')]:
        native.connection.execute('UPDATE tasks SET body_json=? WHERE task_cid=?',[json.dumps(value),TASK])
        native.connection.execute('UPDATE task_revisions SET body_json=? WHERE task_cid=?',[json.dumps(value),TASK])
        result=native.call()
        assert result['disposition']=='deferred',result
        assert reason in {item['reason'] for item in result['missing_evidence']}
        assert result['release_authorized'] is False


@pytest.mark.parametrize('drift', ['owner','source','pool'])
def test_final_native_or_local_drift_refuses_observation(native, drift):
    calls=[]
    def observe(**kwargs):
        value=native.status(**kwargs);calls.append(1)
        if len(calls)==2:
            if drift=='owner':value={**value,'owner_identity':{**value['owner_identity'],'server_id':'server:replacement'}}
            if drift=='pool':native.pool.write_text(native.pool.read_text()+' ')
        return value
    source_calls=[]
    def source():
        source_calls.append(1);return {'source_admitted':True,'source':len(source_calls) if drift=='source' else 1}
    result=native.call(observer=observe,source=source)
    assert result['disposition']=='rejected',result
    assert result['reason_codes'][0] in {'native_owner_identity_mismatch','source_changed','retained_custody_changed'}
    assert result['release_authorized'] is False


def test_unavailable_native_history_has_no_ambient_or_local_fallback(native):
    def unavailable(**kwargs):
        raise OSError('private transport path or token must not be printed')
    result=native.call(observer=unavailable)
    assert result['disposition']=='unavailable'
    assert result['reason_codes']==['canonical_history_unavailable']
    assert 'private transport' not in json.dumps(result)
    assert result['release_authorized'] is False


@pytest.mark.parametrize('source', [{}, {'source_admitted':False}, {'source_admitted':'true'}])
def test_unadmitted_source_stops_before_any_reader_grant(native, source):
    reads=[]
    result=native.call(source=lambda:source, observer=lambda **kwargs:reads.append(kwargs))
    assert result['disposition']=='rejected'
    assert result['reason_codes']==['source_not_admitted']
    assert reads==[]


def test_actual_open_effect_is_reported_for_the_bound_task(native):
    native.connection.execute('INSERT INTO effect_claims VALUES (?,?,?,?,?,?,?,?)',
        ['effect:retained',TASK,ATTEMPT,'provider','retained-path','historical-time','open','{}'])
    native.connection.execute('INSERT INTO effect_claims VALUES (?,?,?,?,?,?,?,?)',
        ['effect:other',UNKNOWN,'attempt:b553-original','provider','other-path','historical-time','open','{}'])
    result=native.call()
    assert result['disposition']=='deferred',result
    assert result['canonical_task_observation']['effect_claims_open_count']==1
    assert {'kind':'effect_claims','reason':'bound_task_has_open_canonical_rows','count':1} in result['missing_evidence']
    assert result['release_authorized'] is False


@pytest.mark.parametrize('kind',['fifo','symlink','hardlink','oversize'])
def test_request_reader_rejects_unsafe_files_without_consuming_them(tmp_path,kind):
    path=tmp_path/'request'
    if kind=='fifo':os.mkfifo(path)
    elif kind in {'symlink','hardlink'}:
        original=tmp_path/'original';original.write_bytes(b'{}')
        if kind=='symlink':path.symlink_to(original)
        else:os.link(original,path)
    else:path.write_bytes(b' '*(16*1024+1))
    with pytest.raises((admission.AdmissionRejected,OSError)):
        admission.read_request(path)
    assert path.lstat()


@pytest.mark.parametrize('moment',['before-open','during-read'])
def test_pinned_reader_rejects_ancestor_symlink_swap(tmp_path,monkeypatch,moment):
    original=tmp_path/'original';original.mkdir();path=original/'request';path.write_bytes(b'original')
    other=tmp_path/'other';other.mkdir();(other/'request').write_bytes(b'foreign')
    moved=tmp_path/'retained';swapped=[]
    def swap():
        if not swapped:
            original.rename(moved);original.symlink_to(other,target_is_directory=True);swapped.append(True)
    raw_open=admission.os.open;raw_read=admission.os.read
    def opened(name,flags,*args,**kwargs):
        if moment=='before-open' and name=='original' and kwargs.get('dir_fd') is not None:swap()
        return raw_open(name,flags,*args,**kwargs)
    def read(fd,count):
        if moment=='during-read':swap()
        return raw_read(fd,count)
    monkeypatch.setattr(admission.os,'open',opened);monkeypatch.setattr(admission.os,'read',read)
    with pytest.raises((admission.AdmissionRejected,OSError)):
        admission._read_regular(path)
    assert swapped
    assert (moved/'request').read_bytes()==b'original'
    assert (other/'request').read_bytes()==b'foreign'


@pytest.mark.parametrize('preflight_valid,drift',[(False,False),(True,True),(True,False)])
def test_native_source_adapter_requires_preflight_and_unchanged_source(native,monkeypatch,preflight_valid,drift):
    from ipfs_accelerate_py.agent_supervisor.runtime import configured_board_scheduler as scheduler
    source_calls=[]
    def source():
        source_calls.append(1);return {'source_head':len(source_calls) if drift else 1}
    monkeypatch.setattr(native.module,'_history_source_observation',source)
    monkeypatch.setattr(scheduler,'preflight_configured_board',lambda board:{'valid':preflight_valid})
    if not preflight_valid or drift:
        with pytest.raises(native.module.HandoffError,match='not currently admitted'):
            native.module._retained_pool_source_admission()
    else:
        assert native.module._retained_pool_source_admission()=={'source_admitted':True,'source_observation':{'source_head':1}}


def test_native_cli_emits_typed_read_only_deferral_and_redacted_file_error(native,tmp_path,monkeypatch,capsys):
    request_path=tmp_path/'request.json';write(request_path,native.request)
    monkeypatch.setattr(native.module,'ROOT',native.runtime.parent)
    monkeypatch.setattr(native.module,'_retained_pool_source_admission',lambda:{'source_admitted':True,'source':'test-qualified'})
    assert native.module.main(['retained-pool-release-admission','--request-json',str(request_path)])==0
    result=json.loads(capsys.readouterr().out)
    assert result['disposition']=='deferred' and result['release_authorized'] is False
    request_path.write_text('not JSON private material')
    assert native.module.main(['retained-pool-release-admission','--request-json',str(request_path)])==2
    output=capsys.readouterr().out
    assert 'private material' not in output
    assert json.loads(output)['reason_codes']==['request_unavailable']
