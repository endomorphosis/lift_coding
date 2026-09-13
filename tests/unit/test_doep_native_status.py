"""Native DOEP readers receive their own sealed read-only owner session."""
import importlib.util
import json
import os
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]


def module():
    spec = importlib.util.spec_from_file_location(
        'doep_native_status_test', ROOT / 'scripts/ops/agent_supervisor/direct_objective_event_driven_planning_handoff.py')
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


@pytest.fixture
def native(tmp_path, monkeypatch):
    m = module()
    from test.api.causal_federation.test_typed_state_owner import _gateway, _install
    from ipfs_accelerate_py.agent_supervisor.merge.worktree_lifecycle import read_process_birth
    from ipfs_accelerate_py.agent_supervisor.task_sources.typed_state_owner import (
        TYPED_STATE_OWNER_SOCKET_FILENAME, TYPED_STATE_OWNER_TOKEN_FILENAME,
        compact_default_owner_socket_path,
    )
    db = tmp_path / 'control.duckdb'
    _install(db)
    owner = tmp_path / 'owner'
    owner.mkdir()
    gateway, connection = _gateway(db, compact_default_owner_socket_path(
        owner / TYPED_STATE_OWNER_SOCKET_FILENAME, identity=db))
    token = gateway.configure_status_bootstrap()
    (owner / TYPED_STATE_OWNER_TOKEN_FILENAME).write_text(token)
    body = json.dumps({'board_namespace': m.PROGRAM_ID, 'original_evidence': 'retained'})
    connection.execute('UPDATE tasks SET task_alias=?, plan_cid=?, identity_json=?, body_json=?, revision=1',
                       ['DOEP-031', 'plan:sealed', json.dumps({'repository_tree_id': 'tree:sealed'}), body])
    connection.execute('INSERT INTO task_revisions VALUES (?,1,?,?,?)',
                       ['task:typed-owner', 'ready', body, 'original-time'])
    population = {'tasks': [{'task_alias': 'DOEP-031', 'task_cid': 'task:typed-owner'}],
                  'goals': [{}], 'plan_root_cid': 'plan:sealed', 'repository_tree_id': 'tree:sealed'}
    board = SimpleNamespace(resolved_database_program=lambda: SimpleNamespace(
        store_generation='control.duckdb', quack_endpoint='quack:127.0.0.1:27942'))
    status = owner / 'quack-state-server.status.json'
    status.write_text(json.dumps({'lifecycle': 'ready', 'identity': {
        **gateway.identity, 'process_birth': read_process_birth(os.getpid()).to_dict()}}))
    paths = {'owner': owner, 'owner_status': status, 'database': db}
    monkeypatch.setattr(m, '_load', lambda: (board, population, paths))
    yield m, gateway, connection, population, paths
    gateway.stop()
    connection.close()


def test_native_reader_requires_explicit_launcher_scope(native):
    m, gateway, _, population, _ = native
    from ipfs_accelerate_py.agent_supervisor.task_sources.typed_state_owner import TypedStateOwnerError
    with pytest.raises(TypedStateOwnerError) as denied:
        m.authoritative_status()
    assert denied.value.error_code == 'status_scope_not_admitted'
    m._bind_native_status(gateway, population)
    result = m.authoritative_status(history_tasks=['DOEP-031'])
    assert result['authoritative_task_observation'] is True
    assert result['completion_authority'] is False
    assert result['control']['task_count'] == 1
    assert result['task_histories']['DOEP-031']['revisions'][0]['body']['original_evidence'] == 'retained'
    assert result['closeout_snapshot']['closeout_facts']['goal_contracts_evaluated'] is False
    assert result['tasks'][0]['revision'] == 1
    # The session is retired when this invocation closes; no lane grant used.
    deadline = time.monotonic() + 2
    while gateway.capability()["active_grants"] and time.monotonic() < deadline:
        time.sleep(0.01)
    assert gateway.capability()["active_grants"] == 0


@pytest.mark.parametrize('failure', ['foreign-history', 'owner', 'population', 'history-gap'])
def test_native_reader_rejects_unqualified_observations(native, failure):
    m, gateway, connection, population, paths = native
    m._bind_native_status(gateway, population)
    tasks = ['DOEP-031']
    if failure == 'foreign-history':
        tasks = ['DOEP-foreign']
    elif failure == 'owner':
        value = json.loads(paths['owner_status'].read_text())
        value['identity']['server_id'] = 'server:foreign'
        paths['owner_status'].write_text(json.dumps(value))
    elif failure == 'population':
        connection.execute("UPDATE tasks SET plan_cid='plan:changed'")
    elif failure == 'history-gap':
        connection.execute('DELETE FROM task_revisions')
    with pytest.raises(Exception) as error:
        m.authoritative_status(history_tasks=tasks)
    assert any(word in str(error.value) for word in ('sealed', 'owner', 'history', 'head', 'binding'))


def test_native_reader_without_history_does_not_require_historical_reconstruction(native):
    m, gateway, connection, population, _ = native
    m._bind_native_status(gateway, population)
    connection.execute('DELETE FROM task_revisions')
    result = m.authoritative_status()
    assert result['task_histories'] == {}
    assert result['completion_authority'] is False


@pytest.fixture
def queue_native(native):
    m, gateway, connection, population, paths = native
    from ipfs_accelerate_py.agent_supervisor.merge.checkout_lock import checkout_repository_id
    from ipfs_accelerate_py.agent_supervisor.merge.merge_queue import MergeQueue
    connection.execute("UPDATE tasks SET task_alias='DOEP-063'")
    population['tasks'][0]['task_alias'] = 'DOEP-063'
    queue = MergeQueue(paths['database'].parent / 'queue',
        target_repository_id=checkout_repository_id(m.ROOT), target_branch='main', require_target_binding=True)
    queue.enqueue(branch_name='candidate/retained', task_id='DOEP-063',
        canonical_task_id='task:typed-owner', canonical_task_key='task:typed-owner',
        commit_sha='a' * 40, metadata={'completion_task_cids': {'DOEP-063': 'task:typed-owner'}})
    m._bind_native_status(gateway, population)
    return m, gateway, connection, population, paths, queue


def test_queue_status_requires_opt_in_and_returns_same_guarded_closeout(queue_native):
    m, gateway, _, _, _, queue = queue_native
    from ipfs_accelerate_py.agent_supervisor.task_sources.typed_state_owner import TypedStateOwnerError
    with pytest.raises(TypedStateOwnerError): m.authoritative_status(queue_task='DOEP-063')
    gateway.bind_legacy_merge_queue_status_scope(queue_dir=queue.queue_dir,
        target_repository_id=queue.target_repository_id, target_branch='main')
    result = m.authoritative_status(queue_task='DOEP-063')
    queue_observation = result['legacy_queue_observation']
    assert queue_observation['task_alias'] == 'DOEP-063'
    assert queue_observation['population_complete'] and len(queue_observation['matching_rows']) == 1
    assert queue_observation['control_snapshot'] == result['closeout_snapshot']
    assert queue_observation['control_snapshot']['completion_snapshot'] == result['completion_snapshot']
    assert all(queue_observation[key] is False for key in
        ('guard_retained', 'claim_authority', 'retry_authorized', 'completion_authority'))


@pytest.mark.parametrize('failure', ['foreign-task', 'population', 'target', 'replacement'])
def test_queue_status_preserves_binding_and_population_refusals(queue_native, failure):
    m, gateway, connection, _, _, queue = queue_native
    gateway.bind_legacy_merge_queue_status_scope(queue_dir=queue.queue_dir,
        target_repository_id=queue.target_repository_id, target_branch='main')
    if failure == 'population': connection.execute("UPDATE tasks SET plan_cid='foreign-plan'")
    elif failure == 'target':
        from ipfs_accelerate_py.agent_supervisor.task_sources.duckdb_state import open_duckdb_connection
        with open_duckdb_connection(queue.queue_dir / 'merge_queue.duckdb') as store:
            store.execute("UPDATE merge_requests SET metadata_json=json_merge_patch(metadata_json, '{\"target_branch\":\"foreign\"}')")
    elif failure == 'replacement':
        import shutil
        path = queue.queue_dir / 'merge_queue.duckdb'
        path.rename(path.with_suffix('.original')); shutil.copyfile(path.with_suffix('.original'), path)
    with pytest.raises(Exception):
        m.authoritative_status(queue_task='DOEP-foreign' if failure == 'foreign-task' else 'DOEP-063')


def test_queue_cli_passes_only_the_sealed_alias_and_accepts_no_queue_path(monkeypatch, capsys):
    m = module(); calls = []
    monkeypatch.setattr(m, 'authoritative_status', lambda **kwargs: calls.append(kwargs) or {'read_only': True})
    assert m.main(['authoritative-status', '--queue-task', 'DOEP-063']) == 0
    assert calls == [{'history_tasks': [], 'queue_task': 'DOEP-063'}]
    assert json.loads(capsys.readouterr().out) == {'read_only': True}
    with pytest.raises(SystemExit):
        m.main(['authoritative-status', '--queue-task', 'DOEP-063', '--queue-dir', '/tmp/foreign'])
    assert len(calls) == 1


def test_launcher_derives_queue_scope_from_native_board_configuration(monkeypatch):
    m = module()
    from ipfs_accelerate_py.agent_supervisor.merge.checkout_lock import checkout_repository_id
    payload = json.loads((ROOT / 'config/agent_supervisor_direct_objective_event_driven_planning_scheduler.json').read_text())
    population = json.loads((ROOT / 'config/agent_supervisor_direct_objective_event_driven_planning_board.json').read_text())
    board = SimpleNamespace(payload=payload, path=lambda value: ROOT / value,
                            merge_target_branch=payload['merge_target_branch'])
    paths = {'root': board.path(payload['runtime_paths']['root'])}
    calls = []
    server = SimpleNamespace(configure_database_status_before_start=lambda **kwargs: calls.append(kwargs))
    m._configure_native_status_before_start(server, board, population, paths)
    assert calls == [dict(board_namespace=m.PROGRAM_ID, plan_root_cid=population['plan_root_cid'],
        repository_tree_id=population['repository_tree_id'], task_cids=[t['task_cid'] for t in population['tasks']],
        queue_dir=ROOT / payload['runtime_paths']['merge_queue'],
        target_repository_id=checkout_repository_id(ROOT), target_branch=payload['merge_target_branch'])]
    payload['runtime_paths']['merge_queue'] = 'data/foreign/merge-queue'
    with pytest.raises(m.HandoffError): m._configure_native_status_before_start(server, board, population, paths)
    assert len(calls) == 1
