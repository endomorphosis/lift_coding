"""A normal launch cannot rewrite historical materialization evidence."""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / 'scripts/ops/agent_supervisor/direct_objective_event_driven_planning_handoff.py'


def module():
    spec = importlib.util.spec_from_file_location('doep_resume_test', SCRIPT)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def population():
    return {
        'tasks': [{'task_alias': f'DOEP-{n:03}'} for n in range(85)],
        'goals': list(range(50)), 'plan_root_cid': 'plan:test',
        'repository_tree_id': 'tree:test', 'plan_revision': 5,
        'objective': {'objective_id': 'objective:test', 'objective_cid': 'cid:test'},
    }


def policy():
    return SimpleNamespace(
        entries=[SimpleNamespace(task_alias=t['task_alias']) for t in population()['tasks']],
        public_summary=lambda: {'policy_id': 'policy:test'},
        plan_root_cid='plan:test', repository_tree_id='tree:test',
    )


@pytest.mark.parametrize('drift', [None, 'plan_root_cid', 'repository_tree_id', 'goal_count', 'task_count', 'dependency_count'])
def test_route_observation_uses_only_the_paired_projection(monkeypatch, drift):
    m = module()
    from ipfs_accelerate_py.agent_supervisor.task_sources import typed_database_task_source as typed
    snapshot = SimpleNamespace(
        plan_root_cid='plan:test', repository_tree_id='tree:test', goal_count=50,
        task_count=85, dependency_count=233, revision=24, event_cursor=236,
        objective_count=1, plan_count=1, projection_cid='projection:test',
    )
    if drift:
        setattr(snapshot, drift, -1)
    calls = []
    class Source:
        def __init__(self, client, *, owns_client):
            assert owns_client
        def __enter__(self):
            return self
        def __exit__(self, *_args):
            pass
        def seal_execution_route_snapshot(self, modes):
            calls.append(modes)
            return snapshot, policy()
    monkeypatch.setattr(typed, 'TypedDatabaseTaskSource', Source)
    monkeypatch.setattr(m, '_make_client', lambda *args, **kwargs: (object(), SimpleNamespace(grant_id='grant'), 'private'))
    revoked = []
    server = SimpleNamespace(revoke_typed_client_grant=revoked.append)
    if drift:
        with pytest.raises(m.HandoffError, match='sealed DOEP identities'):
            m._seal_route_policy(server, object(), population(), {'revision': 1})
    else:
        _policy, observation = m._seal_route_policy(server, object(), population(), {'revision': 1})
        assert observation['schema'].endswith('/doep-launch-observation@1')
        assert observation['completion_authoritative'] is False
        assert observation['source_adoption_authoritative'] is False
        assert observation['store_revision'] == 24
        assert observation['event_cursor'] == 236
        assert observation['execution_route_policy'] == {'policy_id': 'policy:test'}
        assert 'initial_ready_task_ids' not in observation
    assert len(calls) == 1
    assert revoked == ['grant']


@pytest.mark.parametrize('runner_result', [0, 17])
def test_full_launch_preserves_bootstrap_and_propagates_runner_result(tmp_path, monkeypatch, runner_result):
    m = module()
    from ipfs_accelerate_py.agent_supervisor.runtime import configured_board_scheduler as scheduler
    from ipfs_accelerate_py.agent_supervisor.runtime import multi_supervisor_runner as runner
    paths = {name: tmp_path / name for name in ('state', 'logs', 'evidence', 'owner', 'operator_pid', 'bootstrap_receipt', 'handoff_receipt', 'launch_observation')}
    historical = b'{"historical":"materialization","verified_at":"original"}\n'
    paths['bootstrap_receipt'].write_bytes(historical)
    before = paths['bootstrap_receipt'].stat()
    board = SimpleNamespace()
    identity = SimpleNamespace(process_birth_id='birth:test', to_dict=lambda: {'server_id': 'owner:test', 'process_birth_id': 'birth:test'})
    stopped = []
    server = SimpleNamespace(start=lambda: identity, ready=lambda: True, stop=lambda: stopped.append('owner'))
    class Child:
        failure = ''
        def __init__(self, **kwargs):
            pass
        def start(self):
            pass
        def stop(self):
            stopped.append('child')
    monkeypatch.setattr(m, '_load', lambda: (board, population(), paths))
    monkeypatch.setattr(scheduler, 'main', lambda args: 0)
    monkeypatch.setattr(scheduler, 'configured_board_launch_plan', lambda *args, **kwargs: {'argv': [], 'environment': {}, 'lanes': 4})
    monkeypatch.setattr(runner, 'main', lambda args: runner_result)
    monkeypatch.setattr(m, '_objective_observation', lambda *args: {'revision': 1})
    monkeypatch.setattr(m, '_build_server', lambda *args: server)
    monkeypatch.setattr(m, '_seal_route_policy', lambda *args: (policy(), {'schema': 'ipfs_accelerate_py/agent-supervisor/doep-launch-observation@1', 'completion_authoritative': False, 'source_adoption_authoritative': False}))
    monkeypatch.setattr(m, '_listener', lambda: SimpleNamespace(fileno=lambda: 99))
    monkeypatch.setattr(m, '_BootstrapBroker', Child)
    monkeypatch.setattr(m, '_LiveMonitor', Child)
    monkeypatch.setattr(m, '_store_id', lambda board: 'store:test')
    bindings = []
    monkeypatch.setattr(m, '_bind_native_status', lambda server, population: bindings.append(population))
    assert m.launch() == runner_result
    assert bindings == [population()]
    assert paths['bootstrap_receipt'].read_bytes() == historical
    after = paths['bootstrap_receipt'].stat()
    assert (after.st_ino, after.st_mtime_ns) == (before.st_ino, before.st_mtime_ns)
    observation = json.loads(paths['launch_observation'].read_text())
    handoff = json.loads(paths['handoff_receipt'].read_text())
    assert observation['launch_id'] == handoff['launch_id']
    assert observation['owner_identity'] == handoff['owner_identity']
    assert observation['source_adoption_authoritative'] is False
    assert stopped == ['child', 'child', 'owner']
    assert not paths['operator_pid'].exists()
