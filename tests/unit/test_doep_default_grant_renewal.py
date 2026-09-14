"""Default native grants stay live without changing or resurrecting authority."""
from dataclasses import replace
import importlib.util
import json
import os
from pathlib import Path
import socket
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _module():
    spec = importlib.util.spec_from_file_location('doep_default_renewal_test', ROOT /
        'scripts/ops/agent_supervisor/direct_objective_event_driven_planning_handoff.py')
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


@pytest.fixture
def admitted(tmp_path, monkeypatch):
    m = _module()
    from ipfs_accelerate_py.agent_supervisor.merge import worktree_lifecycle as lifecycle
    from ipfs_accelerate_py.agent_supervisor.merge.database_worktree_registry import process_birth_id
    from ipfs_accelerate_py.agent_supervisor.task_sources import typed_state_owner as typed
    from ipfs_accelerate_py.agent_supervisor.task_sources.state_owner_bootstrap import STATE_OWNER_BOOTSTRAP_REQUEST_SCHEMA

    clock = SimpleNamespace(wall=2_000_000_000.0, mono=10.0)
    monkeypatch.setattr(m, 'time', SimpleNamespace(
        monotonic=lambda: clock.mono, time_ns=lambda: int(clock.wall * 1_000_000_000)))
    monkeypatch.setattr(typed, 'time', SimpleNamespace(time=lambda: clock.wall))
    birth = lifecycle.current_process_birth()
    owner = {'server_id': 'owner:original', 'process_birth_id': process_birth_id(birth), 'generation': 104}
    identity = SimpleNamespace(server_id=owner['server_id'], process_birth_id=owner['process_birth_id'],
        to_dict=lambda: dict(owner))
    gateway = typed.TypedStateOwnerGateway(connection=None, socket_path=tmp_path / 'gateway.sock',
        store_id='doep:test', identity=owner)
    renewals = []
    def renew(*args, **kwargs):
        value = gateway.renew_grant(*args, **kwargs)
        renewals.append(value)
        return value
    server = SimpleNamespace(identity=identity, _command_gateway=gateway,
        issue_typed_client_grant_record=gateway.issue_grant,
        renew_typed_client_grant=renew, revoke_typed_client_grant=gateway.revoke_grant,
        typed_command_socket_path=lambda: gateway.socket_path)
    program = SimpleNamespace(store_generation='doep:test', quack_endpoint='quack:127.0.0.1:41327')
    board = SimpleNamespace(board_namespace='board:doep', max_lanes=4,
        resolved_database_program=lambda: program)
    policy = SimpleNamespace(policy_id='policy:original', public_summary=lambda: {}, to_dict=lambda: {})
    listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    broker = m._BootstrapBroker(listener=listener, server=server, board=board,
        paths={'broker_evidence': tmp_path / 'broker.json'}, policy=policy, launch_id='launch:original')
    ancestry_checks = []
    broker._validate_parent = lambda **kwargs: ancestry_checks.append(kwargs)
    def admit(role='supervisor'):
        client = f'database-implementation-{role}:{m.OWNER_SESSION}:shard:0-of-4'
        request = {'schema': STATE_OWNER_BOOTSTRAP_REQUEST_SCHEMA, 'pid': birth.pid,
            'process_birth': birth.to_dict(), 'process_birth_id': process_birth_id(birth),
            'client_id': client, 'store_id': 'doep:test'}
        response = broker._admit(request, peer_pid=birth.pid, peer_uid=os.geteuid())
        return client, response, broker._grant_bindings[client][0]
    yield SimpleNamespace(m=m, broker=broker, birth=birth, owner=owner, gateway=gateway,
        typed=typed, lifecycle=lifecycle, clock=clock, renewals=renewals,
        ancestry_checks=ancestry_checks, admit=admit)
    listener.close()


@pytest.mark.parametrize('role', ['supervisor', 'daemon'])
def test_default_grant_stays_authorized_past_original_expiry(admitted, role):
    x = admitted
    client, response, original = x.admit(role)
    assert x.renewals == []
    x.clock.wall += x.m.GRANT_TTL_SECONDS - 60
    x.broker._maintain_grants()
    renewed = x.renewals[-1]
    assert replace(renewed, issued_at=original.issued_at, expires_at=original.expires_at) == original
    assert x.gateway._grants[response['token']] == renewed
    assert len(x.gateway._grants) == 1 and not x.gateway._revoked_grants
    assert x.broker._grant_bindings[client][0] == renewed
    # A cached client still presenting its original grant resolves the current
    # server record after the original 24-hour lifetime, with no new bootstrap.
    x.clock.wall += 120
    assert x.clock.wall * 1000 > original.expires_at
    peer = (x.birth.pid, os.geteuid(), x.birth.start_time_ticks)
    assert x.gateway._require_active_grant(original, peer_identity=peer) == renewed
    x.broker._maintain_grants()
    assert len(x.renewals) == 1
    x.clock.mono += x.m.GRANT_RENEW_INTERVAL_SECONDS
    x.broker._maintain_grants()
    assert len(x.renewals) == 2 and len(x.ancestry_checks) == 3
    x.clock.wall += x.m.GRANT_TTL_SECONDS - 60
    x.clock.mono += x.m.GRANT_TTL_SECONDS - 60
    x.broker._maintain_grants()
    assert len(x.renewals) == 3
    assert x.broker._grant_bindings[client][0] == x.renewals[-1]
    assert x.gateway._grants[response['token']] == x.renewals[-1]
    x.clock.wall += 61
    assert x.clock.wall * 1000 > original.expires_at + int(x.m.GRANT_TTL_SECONDS * 1000)
    assert x.gateway._require_active_grant(original, peer_identity=peer) == x.renewals[-1]
    public = json.loads(x.broker.paths['broker_evidence'].read_text())
    assert 'token' not in public['current'][0] and 'grant_id' not in public['current'][0]
    assert 'grant_bindings' not in public


@pytest.mark.parametrize('failure', ['expired', 'revoked', 'missing', 'duplicate',
    'grant_id', 'client_id', 'process_birth_id', 'scope', 'owner', 'gateway_owner',
    'ancestry', 'missing_binding', 'peer_uid'])
def test_default_renewal_never_resurrects_or_promotes_authority(admitted, failure):
    x = admitted
    client, response, original = x.admit()
    if failure == 'expired':
        x.clock.wall += x.m.GRANT_TTL_SECONDS
    elif failure == 'revoked':
        x.gateway.revoke_grant(original.grant_id)
    elif failure == 'missing':
        x.gateway._grants.clear()
    elif failure == 'duplicate':
        x.gateway._grants['foreign-token'] = original
    elif failure in ('grant_id', 'client_id', 'process_birth_id'):
        x.gateway._grants[response['token']] = replace(original, **{failure: 'foreign'})
    elif failure == 'scope':
        x.gateway._grants[response['token']] = replace(original, allowed_operations=frozenset())
    elif failure == 'owner':
        x.owner['server_id'] = 'owner:replacement'
    elif failure == 'gateway_owner':
        x.gateway.identity = {**x.owner, 'generation': 105}
    elif failure == 'ancestry':
        def deny(**kwargs):
            raise x.m.HandoffError('admitted ancestry changed')
        x.broker._validate_parent = deny
    elif failure == 'missing_binding':
        x.broker._grant_bindings.clear()
    elif failure == 'peer_uid':
        x.gateway._grants[response['token']] = replace(original, peer_uid=os.geteuid() + 1)
    before = dict(x.gateway._grants)
    with pytest.raises((x.m.HandoffError, x.typed.TypedStateOwnerAuthorizationError)):
        x.broker._maintain_grants()
    assert x.renewals == []
    if failure == 'expired':
        assert x.gateway._grants == {} and original.grant_id in x.gateway._revoked_grants
    else:
        assert x.gateway._grants == before


@pytest.mark.parametrize('failure', ['dead', 'pid_reuse', 'boot_changed', 'parent_changed'])
def test_default_renewal_retires_only_old_process_birth(admitted, monkeypatch, failure):
    x = admitted
    client, response, original = x.admit()
    birth = None if failure == 'dead' else replace(x.birth, **{
        'pid_reuse': {'start_time_ticks': x.birth.start_time_ticks + 1},
        'boot_changed': {'boot_id': 'different-boot'},
        'parent_changed': {'parent_pid': x.birth.parent_pid + 1},
    }[failure])
    monkeypatch.setattr(x.lifecycle, 'read_process_birth', lambda pid: birth)
    x.broker._maintain_grants()
    assert x.renewals == [] and x.gateway._grants == {}
    assert original.grant_id in x.gateway._revoked_grants
    assert client not in x.broker._grants and client not in x.broker._grant_bindings


def test_default_renewal_runs_on_idle_listener(admitted):
    x = admitted
    x.admit()
    calls = []
    class IdleListener:
        def settimeout(self, timeout):
            assert timeout == 1.0
        def accept(self):
            calls.append('accept')
            x.broker.stopping.set()
            raise TimeoutError
    x.broker.listener = IdleListener()
    x.broker._run()
    assert calls == ['accept'] and len(x.renewals) == 1


def test_default_renewal_stopping_never_changes_grants(admitted):
    x = admitted
    x.admit()
    before = dict(x.gateway._grants)
    x.broker.stopping.set()
    x.broker._maintain_grants()
    assert x.renewals == [] and x.gateway._grants == before


@pytest.mark.parametrize('drift', [None, 'ancestry', '--board-namespace',
    '--state-owner-bootstrap-fd', '--task-shard-count', '--task-shard-index', 'entry'])
def test_renewal_rechecks_actual_sealed_supervisor_ancestry(admitted, monkeypatch, drift):
    x = admitted
    x.admit()
    argv = ['python', '-m', 'ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_supervisor',
        '--board-namespace', x.broker.board.board_namespace,
        '--state-owner-bootstrap-fd', str(x.broker.listener.fileno()),
        '--task-shard-count', '4', '--task-shard-index', '0',
        '--database-owner-session-id', x.m.OWNER_SESSION + ':shard:0-of-4']
    if drift == 'entry':
        argv[2] = 'foreign.module'
    elif drift and drift != 'ancestry':
        argv[argv.index(drift) + 1] = 'foreign'
    monkeypatch.setattr(x.m, '_process_argv', lambda pid: tuple(argv))
    monkeypatch.setattr(x.m, 'os', SimpleNamespace(stat=os.stat,
        getpid=lambda: x.birth.parent_pid + (drift == 'ancestry')))
    x.broker._validate_parent = lambda **kwargs: x.m._BootstrapBroker._validate_parent(x.broker, **kwargs)
    if drift:
        with pytest.raises(x.m.HandoffError):
            x.broker._maintain_grants()
        assert x.renewals == []
    else:
        x.broker._maintain_grants()
        assert len(x.renewals) == 1
