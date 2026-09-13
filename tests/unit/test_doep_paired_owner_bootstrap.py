"""Native configured scopes and bootstrap publication fail closed before dispatch."""
import copy
from dataclasses import replace
import importlib.util
import json
import os
from pathlib import Path
from types import SimpleNamespace
import threading

import pytest

ROOT = Path(__file__).resolve().parents[2]


def module():
    spec = importlib.util.spec_from_file_location('doep_paired_test', ROOT /
        'scripts/ops/agent_supervisor/direct_objective_event_driven_planning_handoff.py')
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


@pytest.mark.parametrize('drift', [None, 'repository_id', 'target_branch', 'store_id',
    'board_namespace', 'config_cid', 'plan_cid', 'lane_id', 'attempt_root', 'missing_lane'])
def test_queue_owner_requires_exact_current_configured_scopes(tmp_path, monkeypatch, drift):
    m = module()
    from scripts.ops.agent_supervisor import spar_merge_owner as native
    from ipfs_accelerate_py.agent_supervisor.merge.owner_recovery_runtime import _cid
    from ipfs_accelerate_py.agent_supervisor.merge.checkout_lock import checkout_repository_id
    board = SimpleNamespace(board_namespace='configured-other-board', task_prefix='ASEH-',
        max_lanes=2, payload={'merge_target_branch': 'main', 'board_namespace': 'configured-other-board'})
    paths = {'state': tmp_path / 'native-state'}
    scopes = [{
        'board_namespace': board.board_namespace, 'config_cid': _cid(board.payload),
        'plan_cid': 'plan:current', 'lane_id': str(lane),
        'attempt_root': str(paths['state'] / f'lane-{lane}' / f'aseh_lane_{lane}_database_portal_attempts'),
    } for lane in range(board.max_lanes)]
    manifest = {'repository_id': checkout_repository_id(m.ROOT), 'target_branch': 'main',
        'store_id': 'separate-queue-store', 'scope_bindings': copy.deepcopy(scopes)}
    if drift in ('repository_id', 'target_branch'):
        manifest[drift] = 'foreign'
    elif drift == 'store_id':
        manifest[drift] = 'task-store'
    elif drift == 'missing_lane':
        manifest['scope_bindings'].pop()
    elif drift:
        manifest['scope_bindings'][0][drift] = 'foreign'
    prepared = native.PreparedQueueStore(tmp_path / 'queue.duckdb', manifest, 'uuid', {}, (), ())
    started = []
    owner = object()
    monkeypatch.setattr(m, '_store_id', lambda board: 'task-store')
    def start(value, **kwargs):
        started.append((value, kwargs))
        return owner
    monkeypatch.setattr(native, 'start_queue_owner', start)
    kwargs = dict(board=board, paths=paths, policy=SimpleNamespace(plan_root_cid='plan:current'), prepared=prepared)
    if drift:
        with pytest.raises(m.HandoffError, match='current configured native scopes'):
            m._start_admitted_merge_owner(**kwargs)
        assert not started
    else:
        selected, bindings, config = m._start_admitted_merge_owner(**kwargs)
        assert selected is owner
        assert bindings == scopes and config == _cid(board.payload)
        assert started == [(prepared, {'state_dir': tmp_path / 'native-queue-owner'})]
        with pytest.raises(m.HandoffError, match='prepared queue object'):
            m._start_admitted_merge_owner(**{**kwargs, 'prepared': dict(manifest)})
        assert len(started) == 1


@pytest.mark.parametrize('drift', [None, '--state-dir', '--state-prefix', '--board-namespace', '--state-owner-bootstrap-fd', '--state-owner-bootstrap-store-id',
    '--owner-merge-config-cid', '--owner-merge-plan-cid', 'client'])
def test_merge_peer_binds_numeric_shard_and_exact_daemon_state(tmp_path, monkeypatch, drift):
    m = module()
    broker = object.__new__(m._BootstrapBroker)
    from ipfs_accelerate_py.agent_supervisor.merge.owner_recovery_runtime import _cid
    broker.board = SimpleNamespace(task_prefix='DOEP-', board_namespace='board:doep', payload={'current': True})
    broker.policy = SimpleNamespace(plan_root_cid='plan:current')
    broker.listener = SimpleNamespace(fileno=lambda: 99)
    monkeypatch.setattr(m, '_store_id', lambda board: 'task-store')
    broker.paths = {'state': tmp_path / 'state'}
    broker._validate_parent = lambda **_: 2
    session = m.OWNER_SESSION + ':shard:2-of-4'
    argv = ['python', '-m', 'ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon', '--owner-session-id', session,
        '--state-dir', str(tmp_path / 'state/lane-2'), '--state-prefix', 'doep_lane_2',
        '--board-namespace', 'board:doep', '--state-owner-bootstrap-fd', '99',
        '--state-owner-bootstrap-store-id', 'task-store',
        '--owner-merge-config-cid', _cid(broker.board.payload), '--owner-merge-plan-cid', 'plan:current']
    client = 'database-implementation-daemon:' + session
    if drift == 'client':
        client += '-foreign'
    elif drift:
        argv[argv.index(drift) + 1] = 'foreign'
    monkeypatch.setattr(m, '_process_argv', lambda pid: tuple(argv))
    if drift:
        with pytest.raises(m.HandoffError, match='state namespace'):
            broker._validate_merge_peer(peer_pid=123, client_id=client)
    else:
        assert broker._validate_merge_peer(peer_pid=123, client_id=client) == '2'


def test_paired_parent_denies_legacy_daemon_but_preserves_supervisor_reader():
    m = module()
    broker = object.__new__(m._BootstrapBroker)
    broker._paired = object()
    calls = []
    broker._admit_task = lambda request, **kwargs: calls.append(request) or {'legacy': True}
    daemon = {'client_id': 'database-implementation-daemon:' + m.OWNER_SESSION}
    with pytest.raises(m.HandoffError, match='complete paired owner bundle'):
        broker._admit(daemon, peer_pid=123, peer_uid=os.geteuid())
    supervisor = {'client_id': 'database-implementation-supervisor:' + m.OWNER_SESSION}
    assert broker._admit(supervisor, peer_pid=123, peer_uid=os.geteuid()) == {'legacy': True}
    assert calls == [supervisor]


def test_paired_retirement_revokes_even_if_publication_fails(monkeypatch):
    m = module()
    broker = object.__new__(m._BootstrapBroker)
    broker._lock = threading.Lock()
    broker._grants = {'client': {'grant_id': 'grant'}}
    revoked = []
    broker.server = SimpleNamespace(revoke_typed_client_grant=revoked.append)
    def fail():
        raise OSError('publication failed')
    broker._publish_grants_locked = fail
    with pytest.raises(OSError):
        broker._revoke_paired_task('client', 'grant')
    assert broker._grants == {}
    assert revoked == ['grant']


def test_paired_peer_refuses_unqualified_wrapper_before_scope_checks(tmp_path, monkeypatch):
    m = module()
    broker = object.__new__(m._BootstrapBroker)
    broker._validate_parent = lambda **kwargs: 0
    monkeypatch.setattr(m, '_process_argv', lambda pid: ('python', '-c', 'unqualified wrapper'))
    with pytest.raises(m.HandoffError, match='native module route'):
        broker._validate_merge_peer(peer_pid=123,
            client_id='database-implementation-daemon:' + m.OWNER_SESSION)


@pytest.mark.parametrize('failure', [None, 'dead', 'pid_reuse', 'expired', 'revoked', 'ancestry'])
def test_paired_readers_renew_only_exact_live_authority(monkeypatch, failure):
    m = module()
    from ipfs_accelerate_py.agent_supervisor.merge import worktree_lifecycle as lifecycle
    birth = lifecycle.current_process_birth()
    broker = object.__new__(m._BootstrapBroker)
    broker._lock = threading.Lock()
    broker._reader_renew_at = 0
    broker._grants = {'reader': {'client_role': 'supervisor_read',
        'process_birth': birth.to_dict(), 'grant_id': 'read-grant'}}
    calls = []
    def validate(**kwargs):
        calls.append(('validate', kwargs))
        if failure == 'ancestry':
            raise m.HandoffError('ancestry changed')
    def active(server, grant_id, current):
        calls.append(('active', grant_id, current))
        if failure in ('expired', 'revoked'):
            raise RuntimeError(failure)
    broker._validate_parent = validate
    broker._paired = SimpleNamespace(maintain=lambda: calls.append('paired'), _live_grant=active)
    broker.server = SimpleNamespace(renew_typed_client_grant=lambda *args, **kwargs: calls.append(('renew', args, kwargs)))
    broker._revoke_paired_task = lambda *args: calls.append(('retire', args))
    broker._publish_grants_locked = lambda: calls.append('publish')
    if failure == 'dead':
        monkeypatch.setattr(lifecycle, 'read_process_birth', lambda pid: None)
    elif failure == 'pid_reuse':
        monkeypatch.setattr(lifecycle, 'read_process_birth', lambda pid: replace(birth, start_time_ticks=birth.start_time_ticks + 1))
    if failure in ('expired', 'revoked', 'ancestry'):
        with pytest.raises(RuntimeError):
            broker._maintain_paired_grants()
    else:
        broker._maintain_paired_grants()
    renewed = [item for item in calls if isinstance(item, tuple) and item[0] == 'renew']
    assert bool(renewed) is (failure is None)
    if failure is None:
        assert renewed == [('renew', ('read-grant',), {'ttl_seconds': m.GRANT_TTL_SECONDS})]
        assert broker._grants['reader']['grant_id'] == 'read-grant'
        previous = list(calls)
        broker._maintain_paired_grants()
        assert calls == previous + ['paired']
    elif failure in ('dead', 'pid_reuse'):
        assert ('retire', ('reader', 'read-grant')) in calls
