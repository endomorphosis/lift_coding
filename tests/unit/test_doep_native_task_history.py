"""Native owner history reads preserve uncertainty without dispatch authority."""
import copy
import importlib.util
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / 'scripts/ops/agent_supervisor/direct_objective_event_driven_planning_handoff.py'
LAUNCH = 'sha256:' + 'a' * 64


def module():
    spec = importlib.util.spec_from_file_location('doep_native_history_test', SCRIPT)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def population(m):
    return {'tasks': [
        {'task_alias': alias, 'task_cid': 'sha256:' + f'{number:064x}'}
        for number, alias in enumerate(m.HISTORY_TASK_ALIASES, 1)
    ]}


def fixture(monkeypatch, *, generations=None, drift=None):
    m = module()
    from ipfs_accelerate_py.agent_supervisor.task_sources import typed_database_task_source as typed
    from ipfs_accelerate_py.agent_supervisor.task_sources.control_plane_contracts import content_identity
    from ipfs_accelerate_py.agent_supervisor.task_sources.intent_repository import TASK_REVISION_HISTORY_PROJECTION_SCHEMA
    calls = []
    closed = []
    revoked = []
    value = population(m)
    owner = {'server_id': 'owner:test', 'process_birth_id': 'birth:test'}
    server = SimpleNamespace(identity=SimpleNamespace(to_dict=lambda: owner.copy()),
                             ready=lambda: True, revoke_typed_client_grant=revoked.append)
    revisions = [
        {'revision': 1, 'status': 'quarantined', 'body': {
            'completion_receipt': {'attempt_id': 'attempt:original', 'reason': 'callback_unknown'}}},
        {'revision': 2, 'status': 'retrying', 'body': {
            'completion_receipt': {'reason': 'unknown_callback_no_merge_source_requeued'}}},
    ]
    sequence = iter(generations or ['stable', 'stable'])
    client = SimpleNamespace(load_generation=lambda: SimpleNamespace(
        content_id=next(sequence), to_record=lambda: {'generation': 4, 'revision': 12}))
    grant = SimpleNamespace(grant_id='owned-grant')

    def make_client(_server, _board, *, client_id):
        calls.append(('grant', client_id))
        return client, grant, 'private-test-token'

    class Source:
        def __init__(self, received, *, owns_client):
            assert received is client and owns_client
        def __enter__(self):
            return self
        def __exit__(self, *_args):
            closed.append(True)
        def task_revision_history_projection(self, cid):
            calls.append(('read', cid))
            history = {'schema': TASK_REVISION_HISTORY_PROJECTION_SCHEMA,
                       'task_cid': cid, 'revisions': copy.deepcopy(revisions)}
            history['projection_cid'] = content_identity(history)
            if drift == 'task':
                history['task_cid'] = 'wrong'
            elif drift == 'digest':
                history['revisions'][1]['status'] = 'completed'
            elif drift == 'owner':
                owner['server_id'] = 'changed'
            elif drift == 'read_error':
                raise OSError('private diagnostic must not become acceptance')
            return history

    monkeypatch.setattr(typed, 'TypedDatabaseTaskSource', Source)
    monkeypatch.setattr(m, '_make_client', make_client)
    source_calls = []
    def source_observation():
        source_calls.append(True)
        return {'.': {'head': 'changed' if drift == 'source' and len(source_calls) > 1 else 'head', 'tree': 'tree'}}
    monkeypatch.setattr(m, '_history_source_observation', source_observation)
    return m, value, server, calls, closed, revoked, revisions


def test_history_observation_preserves_unknown_callback_and_alias(monkeypatch):
    m, value, server, calls, closed, revoked, revisions = fixture(monkeypatch)
    result = m._observe_task_histories(server, object(), value, launch_id=LAUNCH)
    assert calls[0] == ('grant', m.HISTORY_OBSERVER_CLIENT_ID)
    assert [item[1] for item in calls[1:]] == [task['task_cid'] for task in value['tasks']]
    assert set(result['task_histories']) == set(m.HISTORY_TASK_ALIASES)
    assert all(history['revisions'] == revisions for history in result['task_histories'].values())
    assert all(result[key] is False for key in (
        'completion_authoritative', 'source_adoption_authoritative', 'recovery_authoritative'))
    assert 'private-test-token' not in json.dumps(result)
    assert result['owner_identity']['server_id'] == 'owner:test'
    assert result['store_generation'] == {'generation': 4, 'revision': 12}
    assert closed == [True] and revoked == ['owned-grant']


@pytest.mark.parametrize('drift', ['task', 'digest', 'owner', 'source', 'read_error'])
def test_history_rejects_identity_drift_and_revokes_own_grant(monkeypatch, drift):
    m, value, server, _calls, closed, revoked, _revisions = fixture(monkeypatch, drift=drift)
    with pytest.raises((m.HandoffError, OSError)):
        m._observe_task_histories(server, object(), value, launch_id=LAUNCH)
    assert closed == [True] and revoked == ['owned-grant']


@pytest.mark.parametrize('stabilizes', [False, True])
def test_history_generation_churn_retries_the_entire_four_task_observation(monkeypatch, stabilizes):
    generations = ['before', 'after', 'stable', 'stable'] if stabilizes else [str(i) for i in range(8)]
    m, value, server, calls, closed, revoked, _revisions = fixture(monkeypatch, generations=generations)
    if stabilizes:
        result = m._observe_task_histories(server, object(), value, launch_id=LAUNCH)
        assert len(result['task_histories']) == 4
    else:
        with pytest.raises(m.HandoffError, match='bounded observation'):
            m._observe_task_histories(server, object(), value, launch_id=LAUNCH)
    assert len([item for item in calls if item[0] == 'read']) == (8 if stabilizes else 16)
    assert closed == [True] and revoked == ['owned-grant']


@pytest.mark.parametrize('defect', ['missing', 'duplicate', 'duplicate_cid', 'invalid_cid', 'launch'])
def test_invalid_history_scope_never_acquires_grant(monkeypatch, defect):
    m, value, server, calls, closed, revoked, _revisions = fixture(monkeypatch)
    if defect == 'missing':
        value['tasks'].pop()
    elif defect == 'duplicate':
        value['tasks'].append(value['tasks'][0])
    elif defect == 'duplicate_cid':
        value['tasks'][1]['task_cid'] = value['tasks'][0]['task_cid']
    elif defect == 'invalid_cid':
        value['tasks'][0]['task_cid'] = 'invalid'
    with pytest.raises(m.HandoffError):
        m._observe_task_histories(server, object(), value, launch_id='invalid' if defect == 'launch' else LAUNCH)
    assert calls == [] and closed == [] and revoked == []


def test_history_observation_byte_bound_revokes_grant(monkeypatch):
    m, value, server, _calls, closed, revoked, _revisions = fixture(monkeypatch)
    monkeypatch.setattr(m, 'HISTORY_OBSERVATION_MAX_BYTES', 100)
    with pytest.raises(m.HandoffError, match='byte bound'):
        m._observe_task_histories(server, object(), value, launch_id=LAUNCH)
    assert closed == [True] and revoked == ['owned-grant']


def test_history_publication_is_bounded_and_never_replaces_evidence(tmp_path, monkeypatch):
    import stat
    m = module()
    target = tmp_path / 'history.json'
    value = {'history': 'original unknown callback'}
    synced = []
    original_fsync = os.fsync
    def fsync(descriptor):
        synced.append(stat.S_ISDIR(os.fstat(descriptor).st_mode))
        return original_fsync(descriptor)
    monkeypatch.setattr(m.os, 'fsync', fsync)
    m._publish_history_observation(target, value)
    assert synced == [False, True], 'file then directory durability must precede success'
    original = target.read_bytes()
    identity = target.stat()
    with pytest.raises(m.HandoffError, match='already exists'):
        m._publish_history_observation(target, {'history': 'invented closure'})
    assert target.read_bytes() == original
    assert (target.stat().st_ino, target.stat().st_mtime_ns) == (identity.st_ino, identity.st_mtime_ns)
    assert not list(tmp_path.glob('.*.tmp.*'))
    monkeypatch.setattr(m, 'HISTORY_OBSERVATION_MAX_BYTES', 5)
    with pytest.raises(m.HandoffError, match='byte bound'):
        m._publish_history_observation(tmp_path / 'oversize.json', value)
    assert not (tmp_path / 'oversize.json').exists()


@pytest.mark.parametrize('kind', ['fifo', 'symlink'])
def test_history_publication_never_reads_special_incumbent(tmp_path, kind):
    import multiprocessing
    m = module()
    target = tmp_path / 'history.json'
    if kind == 'fifo':
        os.mkfifo(target)
    else:
        target.symlink_to(tmp_path / 'unknown-target')
    context = multiprocessing.get_context('fork')
    result = context.Queue()
    def publish():
        try:
            m._publish_history_observation(target, {'observation': 'new'})
        except m.HandoffError as error:
            result.put(str(error))
    process = context.Process(target=publish)
    process.start()
    process.join(1)
    blocked = process.is_alive()
    if blocked:
        process.kill()
        process.join(1)
    assert not blocked
    assert process.exitcode == 0
    assert result.get(timeout=1) == 'history observation already exists'
    assert target.is_symlink() if kind == 'symlink' else __import__('stat').S_ISFIFO(target.stat().st_mode)


def test_real_native_owned_history_grant_is_read_only_and_preserves_store(tmp_path, monkeypatch):
    m = module()
    from ipfs_accelerate_py.agent_supervisor.merge.worktree_lifecycle import OwnerLiveness
    from ipfs_accelerate_py.agent_supervisor.runtime.quack_state_server import FakeQuackTransport, build_server
    from ipfs_accelerate_py.agent_supervisor.task_sources.database_task_source import DatabaseTaskSource
    from ipfs_accelerate_py.agent_supervisor.task_sources.duckdb_state import open_duckdb_connection
    from test.api.causal_federation.test_bootstrap_runtime import _capability, _migrate

    database = tmp_path / 'history.duckdb'
    value = population(m)
    with DatabaseTaskSource(database) as source:
        source.materialize({
            'repository_tree_id': 'tree:test', 'plan_root_cid': 'plan:test',
            'goals': [{'goal_cid': 'goal:test', 'goal_alias': 'goal', 'title': 'History'}],
            'tasks': [{**task, 'task_id': task['task_alias'], 'goal_cid': 'goal:test',
                       'status': 'quarantined', 'body': {'unknown_callback': True},
                       'outputs': [], 'validations': []} for task in value['tasks']],
        })
    server = build_server(database_path=database, state_dir=tmp_path / 'owner',
        repository_id='repository:test', store_id='doep-history-test',
        transport=FakeQuackTransport(), capability_probe=_capability, migrate=_migrate,
        connection_factory=open_duckdb_connection, owner_liveness_probe=lambda _birth: OwnerLiveness.DEAD)
    identity = server.start()
    program = SimpleNamespace(quack_endpoint=identity.listen_uri)
    board = SimpleNamespace(resolved_database_program=lambda: program)
    monkeypatch.setattr(m, '_store_id', lambda _board: identity.store_id)
    monkeypatch.setattr(m, '_history_source_observation', lambda: {'.': {'head': 'head', 'tree': 'tree'}})
    grants = []
    original_issue = server.issue_typed_client_grant_record
    def issue(**kwargs):
        grants.append(kwargs)
        return original_issue(**kwargs)
    monkeypatch.setattr(server, 'issue_typed_client_grant_record', issue)
    try:
        first = m._observe_task_histories(server, board, value, launch_id=LAUNCH)
        second = m._observe_task_histories(server, board, value, launch_id=LAUNCH)
        assert first['task_histories'] == second['task_histories']
        assert first['store_generation'] == second['store_generation']
        assert all(item['revisions'][0]['status'] == 'quarantined'
                   for item in first['task_histories'].values())
        assert len(grants) == 2
        for grant in grants:
            assert grant['peer_pid'] == os.getpid()
            assert grant['process_birth_id'] == identity.process_birth_id
            assert set(grant['allowed_operations']) == {
                'whoami_metadata', 'load_store_generation',
                'executor_task_projection_by_identity', 'executor_task_revision_history_page'}
            assert not grant.get('allowed_command_operations')
    finally:
        server.stop()
