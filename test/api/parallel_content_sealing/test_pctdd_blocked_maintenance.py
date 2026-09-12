"""Native maintenance observations: no readiness or callback settlement claim."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time
from types import SimpleNamespace

import pytest

SOURCE = Path(__file__).resolve().parents[3] / 'scripts/ops/agent_supervisor/parallel_content_sealing_proof_carrying_tdd.py'
RUNTIME = Path(os.environ['PYTHONPATH'].split(os.pathsep)[0])


def load():
    spec = importlib.util.spec_from_file_location('pctdd_native_blocked_fixture', SOURCE)
    native = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(native)
    return native


def authority(native):
    rows = [[f'task:{i}', f'PCTDD-{i:03d}', i + 1,
             'accepted' if i == 0 else 'blocked' if i in (6, 35) else 'in_progress' if i == 5 else 'todo',
             1, 'plan', '{}', '{}'] for i in range(54)]
    blocks = [[f'block-{i}', f'task:{i}', 'external', 'original', 'original unresolved', 'then', None, 'active']
              for i in (6, 35)]
    class Connection:
        def execute(self, sql):
            self.rows = [row[:4] for row in rows] if 'FROM tasks ' in sql else (
                [[row[1]] for row in blocks] if 'FROM task_blocks' in sql else [])
            return self
        def fetchall(self): return self.rows
    return {'authenticated_query': True, **native._task_projection(Connection()),
            'identity': {'store_id': 'control.duckdb', 'database_uuid': 'original-uuid', 'listen_uri': 'quack:127.0.0.1:1234',
                         'schema_revision': 1, 'extension_fingerprint': 'fp', 'generation': 108},
            'maintenance_task_rows': rows, 'maintenance_block_rows': blocks}


def test_exact_blocker_subset_allows_only_resolved_originals():
    native = load(); old = authority(native); current = copy.deepcopy(old)
    assert native._maintenance_block_subset(old, current) == ['PCTDD-006', 'PCTDD-035']
    current['maintenance_block_rows'][0][7] = 'cleared'
    current['maintenance_block_rows'][0][6] = 'now'
    current['maintenance_task_rows'][6][3:5] = ['accepted', 2]
    current['task_statuses'][6] = 'accepted'
    current['blocked_task_ids'] = ['PCTDD-035']; current['blocked_count'] = 1
    assert native._maintenance_block_subset(old, current) == ['PCTDD-035']
    assert old['maintenance_task_rows'][5] == current['maintenance_task_rows'][5]


@pytest.mark.parametrize('mutation', ['block_id', 'reason', 'blocker', 'created', 'revision', 'body', 'identity', 'duplicate', 'missing', 'alias'])
def test_replacement_forgery_and_population_drift_refuse(mutation):
    native=load(); old=authority(native); current=copy.deepcopy(old)
    if mutation in ('block_id','reason','blocker','created'):
        current['maintenance_block_rows'][0][{'block_id':0,'reason':4,'blocker':3,'created':5}[mutation]]='replacement'
    elif mutation in ('revision','body','identity'):
        current['maintenance_task_rows'][6][{'revision':4,'body':6,'identity':7}[mutation]] = 2 if mutation=='revision' else 'changed'
    elif mutation=='duplicate': current['maintenance_task_rows'].append(current['maintenance_task_rows'][6])
    elif mutation=='missing': current['maintenance_block_rows'].clear()
    else: current['blocked_task_ids']=['PCTDD-005','PCTDD-006']; current['blocked_count']=2
    with pytest.raises(native.OperatorError): native._maintenance_block_subset(old,current)


def test_read_only_process_identity_retains_pidfd_and_detects_exit(tmp_path, monkeypatch):
    native=load(); monkeypatch.setattr(native,'ROOT',tmp_path)
    child=subprocess.Popen([sys.executable,'-c','import sys; sys.stdin.read()'],cwd=tmp_path,stdin=subprocess.PIPE)
    monitor=object.__new__(native._BlockedMaintenanceMonitor);monitor.fds={}
    try:
        observed=monitor.actor(child.pid)
        assert observed['birth']['pid']==child.pid and observed['birth']['parent_pid']==os.getpid()
        assert monitor.actor(child.pid)==observed
        child.stdin.close(); child.wait(timeout=5)
        with pytest.raises(native.OperatorError): monitor.actor(child.pid)
    finally:
        if child.poll() is None: child.terminate();child.wait(timeout=5)
        monitor.close()
    assert not monitor.fds


def test_permission_denied_is_not_actor_death(tmp_path,monkeypatch):
    native=load(); monkeypatch.setattr(native,'ROOT',tmp_path)
    original=os.readlink
    monkeypatch.setattr(os,'readlink',lambda path: (_ for _ in ()).throw(PermissionError('private')) if str(path).endswith('/cwd') else original(path))
    with pytest.raises(PermissionError):native._maintenance_process(os.getpid())


@pytest.mark.parametrize('drift', [None, 'loaded', 'missing', 'unavailable', 'bytes', 'revision', 'root'])
def test_qualified_private_runtime_requires_complete_current_source_equivalence(tmp_path, monkeypatch, drift):
    native = load()
    from ipfs_accelerate_py.agent_supervisor.todo_daemon import implementation_supervisor as runtime
    root = tmp_path / 'parent'
    root.mkdir()
    adopted = root / 'external/ipfs_accelerate'
    adopted.mkdir(parents=True)
    (root / 'external/ipfs_datasets').mkdir()
    (root / 'external/ipfs_kit').mkdir()
    operator = root / 'operator.py'
    operator.write_bytes(b'bound operator source')
    config = root / 'config.json'
    config.write_bytes(b'bound configuration')
    sources = []
    for name, content in (('a.py', b'a source'), ('b.py', b'b source')):
        (adopted / name).write_bytes(content)
        sources.append({'path': name, 'available': True, 'size_bytes': len(content),
                        'sha256': hashlib.sha256(content).hexdigest()})
    snapshot = {'repository_root': str(tmp_path / 'different-qualified-import-root'),
                'repository_revision': 'b' * 40, 'source_id': 'source:exact',
                'control_plane_tree_id': 'tree:exact', 'sources': sources}
    imported = copy.deepcopy(snapshot)
    monkeypatch.setattr(native, 'ROOT', root)
    monkeypatch.setattr(native, 'ACCEL_ROOT', adopted)
    monkeypatch.setattr(native, '__file__', str(operator))
    monkeypatch.setattr(runtime, 'IMPORTED_CONTROL_PLANE_SOURCE', imported)
    monkeypatch.setattr(runtime, 'CONTROL_PLANE_SOURCE_PATHS', ('a.py', 'b.py'))
    monkeypatch.setattr(runtime, '_read_control_plane_source_snapshot', lambda: snapshot)
    def git(argv, **_):
        path = argv[argv.index('-C') + 1]
        revision = 'b' * 40 if path == str(adopted) else 'a' * 40
        observed_root = str(tmp_path) if drift == 'root' else path
        return SimpleNamespace(returncode=0, stdout=observed_root + '\n' + revision + '\n')
    monkeypatch.setattr(native.subprocess, 'run', git)
    if drift == 'loaded': imported['source_id'] = 'source:old-loaded'
    elif drift == 'missing': sources.pop()
    elif drift == 'unavailable': sources[1]['available'] = False
    elif drift == 'bytes': (adopted / 'b.py').write_bytes(b'changed bytes')
    elif drift == 'revision': snapshot['repository_revision'] = 'c' * 40
    if drift is not None:
        with pytest.raises(native.OperatorError): native._maintenance_source(config)
    else:
        result = native._maintenance_source(config)
        assert result['runtime']['sources'] == sources
        assert result['runtime']['repository_revision'] == 'b' * 40
        assert 'repository_root' not in result['runtime']
        assert result['repositories'][1] == [str(adopted), 'b' * 40]


def configure(native, root):
    native.ROOT=root;native.ACCEL_ROOT=RUNTIME
    payload=json.loads((root/'fixture.json').read_text())
    program=SimpleNamespace(store_id='control.duckdb', endpoint_secret_handle='env://PCTDD_TEST_OWNER',
                            quack_endpoint=f"quack:127.0.0.1:{payload['port']}")
    board=SimpleNamespace(config_path=root/'fixture.json',resolved_database_program=lambda:program)
    paths={name:root/part for name,part in {'runtime':'runtime','state':'state','logs':'logs','owner':'owner',
         'database':'control.duckdb','owner_status':'owner/quack-state-server.status.json','owner_pid':'state/owner.pid',
         'owner_log':'logs/owner.log'}.items()}
    native._load_board=lambda _:(board,payload);native._runtime_paths=lambda _:paths
    return board,paths


def test_actual_native_owner_transaction_observes_full_records(tmp_path, monkeypatch):
    native=load()
    from ipfs_accelerate_py.agent_supervisor.task_sources.database_task_source import DatabaseTaskSource
    from ipfs_accelerate_py.agent_supervisor.task_sources.duckdb_state import open_duckdb_connection
    source=DatabaseTaskSource(tmp_path/'control.duckdb')
    source.materialize({'repository_tree_id':'tree:maintenance','plan_root_cid':'plan:maintenance',
        'goals':[{'goal_cid':'goal:maintenance','goal_alias':'PCTDD-G','title':'Maintenance'}],
        'tasks':[{'task_cid':f'task:{i}','task_id':f'PCTDD-{i:03d}','goal_cid':'goal:maintenance',
                  'status':'completed' if i==0 else 'blocked' if i in (6,35) else 'in_progress' if i==5 else 'todo'} for i in range(54)]})
    source.close()
    with open_duckdb_connection(tmp_path/'control.duckdb') as connection:
        for i in (6,35):
            connection.execute("INSERT INTO task_blocks VALUES (?, ?, 'external', 'original', 'unresolved', 'then', NULL, 'active')",
                               [f'block-{i}',f'task:{i}'])
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    (tmp_path/'fixture.json').write_text(json.dumps({'port':port}))
    board,paths=configure(native,tmp_path)
    log=(tmp_path/'owner-output.log').open('wb')
    child=subprocess.Popen([sys.executable,'-B',str(Path(__file__)),'owner',str(tmp_path)],
                           cwd=tmp_path,stdout=log,stderr=subprocess.STDOUT,env=os.environ.copy())
    try:
        deadline=time.monotonic()+30
        while time.monotonic()<deadline:
            if child.poll() is not None:pytest.fail((tmp_path/'owner-output.log').read_text())
            if native._owner_projection(paths).get('lifecycle')=='ready':break
            time.sleep(.05)
        value=native._authenticated_projection(board,paths,maintenance=True)
        assert value['authenticated_query'] is True and value['direct_database_file_open'] is False
        assert len(value['maintenance_task_rows'])==54 and len(value['maintenance_block_rows'])==2
        native._require_runtime_resume_authority(value,expected_task_identities=tuple((f'task:{i}',f'PCTDD-{i:03d}',i+1) for i in range(54)))
        assert native._maintenance_block_subset(value,value)==['PCTDD-006','PCTDD-035']
        assert value['maintenance_task_rows'][5][3]=='in_progress'
        again=native._authenticated_projection(board,paths,maintenance=True)
        assert value==again
        original_token_reader=native._read_owner_token
        monkeypatch.setattr(native,'_read_owner_token',lambda _: 'wrong-native-owner-token')
        with pytest.raises(Exception): native._authenticated_projection(board,paths,maintenance=True)
        monkeypatch.setattr(native,'_read_owner_token',original_token_reader)
        original_owner=native._owner_projection
        def foreign_generation(paths):
            observed=original_owner(paths)
            observed['identity']['generation']+=1
            return observed
        monkeypatch.setattr(native,'_owner_projection',foreign_generation)
        with pytest.raises(native.OperatorError,match='identity mismatch'):
            native._authenticated_projection(board,paths,maintenance=True)
        monkeypatch.setattr(native,'_owner_projection',original_owner)
        assert native._authenticated_projection(board,paths,maintenance=True)==value
        # The live writer stays native; our observer only attached over Quack.
        with pytest.raises(Exception):
            with open_duckdb_connection(tmp_path/'control.duckdb', timeout_seconds=.1): pass
    finally:
        if child.poll() is None:child.terminate()
        child.wait(timeout=30);log.close()
    assert native._owner_projection(paths)['lifecycle']=='stopped'


if __name__=='__main__':
    assert sys.argv[1]=='owner'
    root=Path(sys.argv[2]).resolve()
    assert root.name.startswith('test_') and str(root).startswith('/tmp/')
    native=load();configure(native,root)
    native._serve_state_owner(root/'fixture.json')


def monitor_fixture(tmp_path, monkeypatch):
    """Transport/kernel seams are explicit here; actual implementations tested separately."""
    native=load();old=authority(native);current=copy.deepcopy(old)
    current['identity'].update(generation=109,server_id='new',process_birth_id='newbirth',started_at='now',status='ready',revision=2)
    source={'runtime':{'source_id':'source:current','control_plane_tree_id':'tree:current'}}
    board=SimpleNamespace(max_lanes=4,task_prefix='PCTDD-',payload={'watchdog_startup_grace_seconds':600},
                          resolved_database_program=lambda:SimpleNamespace(endpoint_secret_handle='env://TEST'))
    paths={'runtime':tmp_path/'runtime','state':tmp_path/'state','owner':tmp_path/'owner'}
    actors={}
    def actor(pid,parent,argv):
        value={'birth':{'pid':pid,'parent_pid':parent,'start_time_ticks':pid+1000,'boot_id':'boot'},'argv':argv}
        actors[pid]=value;return value
    master=actor(100,1,['python','-m','ipfs_accelerate_py.agent_supervisor.runtime.multi_supervisor_runner',
                            '--repo-root',str(tmp_path),'--master-dir',str(paths['runtime'])])
    owner=actor(101,1,['python','native-owner'])
    lanes=[];projections={}
    for i in range(4):
        directory=paths['state']/f'lane-{i}';prefix=f'pctdd_lane_{i}'
        wrapper=actor(200+i,100,['python',str(tmp_path/'scripts/ops/agent_supervisor/implementation_supervisor_entry.py'),
                 '--state-dir',str(directory),'--state-prefix',prefix,'--task-shard-index',str(i)])
        daemon=actor(300+i,200+i,['python','-P','-m','ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon',
                 '--state-dir',str(directory),'--state-prefix',prefix])
        lanes.append({'index':i,'healthy':True,'supervisor_pid':200+i,'daemon_pid':300+i})
        projections[str(directory/(prefix+'_supervisor_status.json'))]={
           'supervisor_pid':200+i,'control_plane_source_id':'source:current','control_plane_current_source_id':'source:current',
           'control_plane_source_tree_id':'tree:current','control_plane_update_pending':False}
    supervisor={'master_pid':100,'ready':True,'master_alive':True,'expected_lane_count':4,'lanes':lanes}
    published={**current['identity'],'revision':1,'process_birth':owner['birth']}
    monkeypatch.setattr(native,'ROOT',tmp_path)
    monkeypatch.setattr(native,'_configured_task_identities',lambda _:tuple(tuple(row[:3]) for row in old['maintenance_task_rows']))
    monkeypatch.setattr(native,'_maintenance_source',lambda _:copy.deepcopy(source))
    monkeypatch.setattr(native,'_authenticated_projection',lambda *a,**k:copy.deepcopy(current))
    monkeypatch.setattr(native,'_supervisor_projection',lambda *a:copy.deepcopy(supervisor))
    monkeypatch.setattr(native,'_owner_projection',lambda *_:copy.deepcopy(published))
    monkeypatch.setattr(native,'_exact_live_owner_identity',lambda *a:(copy.deepcopy(published),None))
    monkeypatch.setattr(native,'_json_object',lambda p:copy.deepcopy(projections[str(p)]))
    monkeypatch.setattr(native,'_maintenance_daemon_command',lambda *a:None)
    monkeypatch.setattr(native._BlockedMaintenanceMonitor,'actor',lambda self,pid:copy.deepcopy(actors[pid]))
    baseline={'schema':native.MAINTENANCE_OBSERVATION_SCHEMA,'authority':old,'source':{'old':'source'},'callback_settlement_claimed':False}
    return native,board,paths,baseline,current,source,supervisor,actors,published,projections


@pytest.mark.parametrize('grace,deadline',[(20,45),(600,45)])
def test_both_native_monitor_blocked_exits_issue_only_typed_diagnosis(tmp_path,monkeypatch,grace,deadline):
    native,board,paths,baseline,current,*rest=monitor_fixture(tmp_path,monkeypatch)
    supervisor=rest[1];board.payload['watchdog_startup_grace_seconds']=grace
    clock={'now':0.0};launches=[]
    monkeypatch.setattr(native.time,'monotonic',lambda:clock['now'])
    monkeypatch.setattr(native.time,'sleep',lambda seconds:clock.update(now=clock['now']+seconds))
    monkeypatch.setattr(native,'_read_owner_token',lambda _: 'private-test-token')
    monkeypatch.setattr(native,'_python_environment',lambda **kw:{})
    monkeypatch.setattr(native,'_scheduler_command',lambda *a,**k:['native-fixture'])
    def launch(*a,**k):
        launches.append(True);return {'returncode':0,'json':None,'stdout':'master_pid=100\nmaster_pid_file=fixture','stderr':''}
    monkeypatch.setattr(native,'_run',launch)
    monkeypatch.setattr(native,'status',lambda _:{'operational_ready':False,'program_state':'blocked',
                                                  'task_authority':copy.deepcopy(current),'supervisor':copy.deepcopy(supervisor)})
    with pytest.raises(native.DiagnosedBlockedMaintenance) as caught:
        native._launch_scheduler_and_monitor(tmp_path/'config',board=board,paths=paths,owner={},initial_authority=current,
            monitor_seconds=deadline,command='resume',mode='runtime_resume',maintenance_baseline=baseline)
    assert len(launches)==1 and caught.value.observation['stable_health_seconds']>=15
    assert caught.value.observation['operational_ready'] is False
    assert caught.value.observation['callback_settlement_claimed'] is False
    assert isinstance(caught.value,native.OperatorError)
    assert clock['now']==min(grace,deadline)


@pytest.mark.parametrize('drift',['generation','published_birth','published_identity','source','wrapper_birth','daemon_birth','parent','projection_source','new_block','same_alias_block','unhealthy'])
def test_final_observation_refuses_custody_and_record_drift(tmp_path,monkeypatch,drift):
    native,board,paths,baseline,current,source,supervisor,actors,published,projections=monitor_fixture(tmp_path,monkeypatch)
    check=native._BlockedMaintenanceMonitor(tmp_path/'config',board,paths,baseline,current['identity'])
    check.bind_launch({'json':{'master_pid':100}});check.observe({},0);check.observe({},15)
    if drift=='generation':current['identity']['generation']=110
    elif drift=='published_birth':published['process_birth']['start_time_ticks']+=1
    elif drift=='published_identity':published['database_uuid']='foreign'
    elif drift=='source':source['runtime']['source_id']='different'
    elif drift=='wrapper_birth':actors[200]['birth']['start_time_ticks']+=1
    elif drift=='daemon_birth':actors[300]['birth']['start_time_ticks']+=1
    elif drift=='parent':actors[300]['birth']['parent_pid']=999
    elif drift=='projection_source':next(iter(projections.values()))['control_plane_source_id']='old'
    elif drift=='new_block':current['maintenance_block_rows'].append(['new','task:5','external','new','reason','now',None,'active'])
    elif drift=='same_alias_block':current['maintenance_block_rows'][0][0]='new'
    else:supervisor['lanes'][0]['healthy']=False
    monkeypatch.setattr(native.time,'monotonic',lambda:16)
    with pytest.raises(native.OperatorError) as caught:check.raise_diagnosed({})
    assert not isinstance(caught.value,native.DiagnosedBlockedMaintenance)
    check.close()


def test_native_daemon_renderer_refuses_wrong_entry_and_flags(tmp_path,monkeypatch):
    native=load();monkeypatch.setattr(native,'ROOT',tmp_path)
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_supervisor import (
        PortalImplementationSupervisor,parse_args,supervisor_config_from_args)
    argv=['--todo-path',str(tmp_path/'todo.duckdb'),'--state-dir',str(tmp_path/'lane-0'),
          '--state-prefix','pctdd_lane_0','--task-prefix','PCTDD-', '--board-namespace','pctdd',
          '--task-shard-count','4','--task-shard-index','0','--task-source-kind','duckdb',
          '--database-authority-mode','quack','--database-quack-endpoint','quack:127.0.0.1:12345',
          '--database-endpoint-secret-handle','env://TEST','--database-store-id','control.duckdb']
    # Use the native parser's exact supported names (defined by database_program).
    from ipfs_accelerate_py.agent_supervisor.runtime.multi_supervisor_runner import DatabaseProgramConfig
    program=DatabaseProgramConfig.from_mapping({'task_source_kind':'duckdb','authority_mode':'quack',
             'quack_endpoint':'quack:127.0.0.1:12345','endpoint_secret_handle':'env://TEST',
             'store_id':'control.duckdb','store_generation':'g1','schema_revision':'1','failover_policy':'fail_closed'})
    argv=argv[:14]+program.cli_args()
    config=supervisor_config_from_args(parse_args(argv),repo_root=tmp_path)
    renderer=object.__new__(PortalImplementationSupervisor);renderer.config=config;renderer.board_namespace='pctdd'
    command=renderer._build_daemon_command()
    board=SimpleNamespace(max_lanes=4,task_prefix='PCTDD-',board_namespace='pctdd',resolved_database_program=lambda:program)
    wrapper={'argv':[sys.executable,str(tmp_path/'scripts/ops/agent_supervisor/implementation_supervisor_entry.py'),*argv]}
    native._maintenance_daemon_command(board,wrapper,{'argv':command})
    for changed in ([sys.executable,'-c','pass',*command[4:]],command+['--implement'],command[:-2]+['--task-shard-index','1']):
        with pytest.raises(native.OperatorError):native._maintenance_daemon_command(board,wrapper,{'argv':changed})


def test_final_verifier_preserves_qualified_diagnosis_across_owner_reparent(tmp_path,monkeypatch):
    native,board,paths,baseline,current,source,supervisor,actors,published,projections=monitor_fixture(tmp_path,monkeypatch)
    check=native._BlockedMaintenanceMonitor(tmp_path/'config',board,paths,baseline,current['identity'])
    check.bind_launch({'json':{'master_pid':100}});check.observe({},0);check.observe({},15)
    original=json.loads(json.dumps(check.last))
    # Published native birth keeps its original launch parent; current kernel
    # parent changes only after that caller exits. No PID/birth/source changes.
    published['process_birth']=copy.deepcopy(published['process_birth'])
    actors[101]['birth']['parent_pid']=999
    monkeypatch.setattr(native,'_load_board',lambda _:(board,{}))
    monkeypatch.setattr(native,'_runtime_paths',lambda _:paths)
    verified=native.verify_diagnosed_blocked_maintenance(tmp_path/'config',original)
    assert verified['original_diagnosis']==original
    assert original['stable_health_seconds']==15
    assert verified['current_verification']['stable_health_seconds']==0
    assert verified['current_verification']['cohort']['owner']['birth']['parent_pid']==999
    assert original['cohort']['owner']['birth']['parent_pid']==1


def test_final_verifier_all_resolved_requires_ordinary_native_readiness(tmp_path,monkeypatch):
    native,board,paths,baseline,current,source,supervisor,actors,published,projections=monitor_fixture(tmp_path,monkeypatch)
    check=native._BlockedMaintenanceMonitor(tmp_path/'config',board,paths,baseline,current['identity'])
    check.bind_launch({'json':{'master_pid':100}});check.observe({},0);check.observe({},15)
    original=json.loads(json.dumps(check.last))
    for i in (6,35):
        current['maintenance_task_rows'][i][3:5]=['completed',2];current['task_statuses'][i]='completed'
    current['status_counts'].pop('blocked');current['status_counts']['completed']=2
    current['completed_count']=3;current['terminal_count']=3
    for row in current['maintenance_block_rows']:row[7]='cleared';row[6]='now'
    current['blocked_count']=0;current['blocked_task_ids']=[]
    monkeypatch.setattr(native,'_load_board',lambda _:(board,{}))
    monkeypatch.setattr(native,'_runtime_paths',lambda _:paths)
    monkeypatch.setattr(native,'status',lambda _:{'operational_ready':False,'task_authority':current})
    with pytest.raises(native.OperatorError,match='ordinary native readiness'):
        native.verify_diagnosed_blocked_maintenance(tmp_path/'config',original)
    monkeypatch.setattr(native,'status',lambda _:{'operational_ready':True,'task_authority':current})
    verified=native.verify_diagnosed_blocked_maintenance(tmp_path/'config',original)
    assert verified['original_diagnosis']==original
    assert verified['current_verification']['outcome']=='infrastructure_recovered_work_unblocked'
    assert verified['current_verification']['callback_settlement_claimed'] is False


@pytest.mark.parametrize('grace,deadline', [(20,45),(600,45)])
@pytest.mark.parametrize('drift', [None,'late_resolution','readiness','new_block','owner','source','cohort','unhealthy','progress'])
def test_resolution_at_native_diagnosis_boundary_requires_fresh_ordinary_readiness(
        tmp_path, monkeypatch, grace, deadline, drift):
    # Independent review exposed both native exits. Transport/kernel seams are
    # explicit mocks here; the production monitor, canonical vector checks and
    # readiness result construction are the actual source implementation.
    native,board,paths,baseline,current,source,supervisor,actors,*_=monitor_fixture(tmp_path,monkeypatch)
    board.payload['watchdog_startup_grace_seconds']=grace
    clock={'now':0.0};launches=[];resolved=False;changed=False
    monkeypatch.setattr(native.time,'monotonic',lambda:clock['now'])
    monkeypatch.setattr(native.time,'sleep',lambda seconds:clock.update(now=clock['now']+seconds))
    monkeypatch.setattr(native,'_read_owner_token',lambda _:'private-test-token')
    monkeypatch.setattr(native,'_python_environment',lambda **_:{})
    monkeypatch.setattr(native,'_scheduler_command',lambda *_a,**_k:['native-fixture'])
    def launch(*_a,**_k):
        launches.append(True)
        return {'returncode':0,'json':None,'stdout':'master_pid=100\n','stderr':''}
    monkeypatch.setattr(native,'_run',launch)
    if drift=='progress':
        current['maintenance_task_rows'][5][3]='todo';current['task_statuses'][5]='todo'
        current['status_counts'].pop('in_progress');current['status_counts']['todo']+=1
        current['in_progress_count']=0
    initial=copy.deepcopy(current)
    threshold=min(grace,deadline)-(1 if drift=='late_resolution' else 0)
    def resolve():
        nonlocal resolved
        resolved=True
        for i in (6,35):
            current['maintenance_task_rows'][i][3:5]=['todo' if drift=='progress' else 'completed',2]
            current['task_statuses'][i]=current['maintenance_task_rows'][i][3]
        current['status_counts'].pop('blocked')
        if drift=='progress':current['status_counts']['todo']+=2
        else:
            current['status_counts']['completed']=2
            current['completed_count']=3;current['terminal_count']=3
        for block in current['maintenance_block_rows']:block[7]='cleared';block[6]='now'
        current['blocked_count']=0;current['blocked_task_ids']=[]
    def auth(*_a,**_k):
        if not resolved and clock['now']>=threshold:resolve()
        return copy.deepcopy(current)
    monkeypatch.setattr(native,'_authenticated_projection',auth)
    def ordinary_status(_):
        nonlocal changed
        result={'operational_ready':resolved and drift!='readiness',
                'program_state':'running' if resolved else 'blocked',
                'task_authority':copy.deepcopy(current),'supervisor':copy.deepcopy(supervisor)}
        if resolved and not changed:
            changed=True
            if drift=='new_block':
                current['maintenance_block_rows'][0]=['replacement','task:6','external','new','new failure','now',None,'active']
                current['maintenance_task_rows'][6][3:5]=['blocked',3];current['task_statuses'][6]='blocked'
                current['blocked_count']=1;current['blocked_task_ids']=['PCTDD-006']
            elif drift=='owner':current['identity']['generation']+=1
            elif drift=='source':source['runtime']['source_id']='changed source'
            elif drift=='cohort':actors[200]['birth']['start_time_ticks']+=1
            elif drift=='unhealthy':supervisor['lanes'][0]['healthy']=False
        return result
    monkeypatch.setattr(native,'status',ordinary_status)
    kwargs=dict(board=board,paths=paths,owner={},initial_authority=initial,
                monitor_seconds=deadline,command='resume',mode='runtime_resume',maintenance_baseline=baseline)
    if drift in (None,'late_resolution'):
        result=native._launch_scheduler_and_monitor(tmp_path/'config',**kwargs)
        assert result['status']['operational_ready'] is True
        assert result['stable_health_seconds']>=15
        assert result['authoritative_progress_observed'] is True
    else:
        with pytest.raises(native.OperatorError) as error:
            native._launch_scheduler_and_monitor(tmp_path/'config',**kwargs)
        assert not isinstance(error.value,native.DiagnosedBlockedMaintenance)
    assert resolved and len(launches)==1


@pytest.mark.parametrize('drift', ['new_block', 'source', 'cohort', 'unhealthy'])
def test_final_resolved_verifier_rechecks_custody_after_ordinary_status(tmp_path,monkeypatch,drift):
    native,board,paths,baseline,current,source,supervisor,actors,*_=monitor_fixture(tmp_path,monkeypatch)
    check=native._BlockedMaintenanceMonitor(tmp_path/'config',board,paths,baseline,current['identity'])
    check.bind_launch({'json':{'master_pid':100}});check.observe({},0);check.observe({},15)
    original=json.loads(json.dumps(check.last))
    for i in (6,35):
        current['maintenance_task_rows'][i][3:5]=['completed',2];current['task_statuses'][i]='completed'
    current['status_counts'].pop('blocked');current['status_counts']['completed']=2
    current['completed_count']=3;current['terminal_count']=3
    for block in current['maintenance_block_rows']:block[7]='cleared';block[6]='now'
    current['blocked_count']=0;current['blocked_task_ids']=[]
    monkeypatch.setattr(native,'_load_board',lambda _:(board,{}))
    monkeypatch.setattr(native,'_runtime_paths',lambda _:paths)
    def ordinary_status(_):
        ready={'operational_ready':True,'task_authority':copy.deepcopy(current)}
        if drift=='new_block':
            current['maintenance_block_rows'][0]=['replacement','task:6','external','new','new failure','now',None,'active']
            current['maintenance_task_rows'][6][3:5]=['blocked',3];current['task_statuses'][6]='blocked'
            current['blocked_count']=1;current['blocked_task_ids']=['PCTDD-006']
        elif drift=='source':source['runtime']['source_id']='different source'
        elif drift=='cohort':actors[200]['birth']['start_time_ticks']+=1
        elif drift=='unhealthy':supervisor['lanes'][0]['healthy']=False
        return ready
    monkeypatch.setattr(native,'status',ordinary_status)
    with pytest.raises(native.OperatorError):
        native.verify_diagnosed_blocked_maintenance(tmp_path/'config',original)
    assert original['stable_health_seconds']==15
