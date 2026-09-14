"""Actual pure producer CLI projection; no owner, worker or database is started."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'external/ipfs_accelerate'))

# Capsule generation is an optional import side effect, outside this pure
# parser/renderer contract. Keep this suite independent of frozen build caches.
_mkdtemp = tempfile.mkdtemp
def _parser_import_directory(*args, **kwargs):
    if kwargs.get('prefix') == 'asref-imported-control-plane-':
        raise PermissionError('pure command tests do not materialize capsules')
    return _mkdtemp(*args, **kwargs)

with patch.object(tempfile, 'mkdtemp', _parser_import_directory):
    from ipfs_accelerate_py.agent_supervisor.todo_daemon import implementation_supervisor as IS
from ipfs_accelerate_py.agent_supervisor.runtime.multi_supervisor_runner import DatabaseProgramConfig


def load():
    source = ROOT / 'scripts/ops/agent_supervisor/parallel_content_sealing_proof_carrying_tdd.py'
    spec = importlib.util.spec_from_file_location('pctdd_worker_projection_fixture', source)
    native = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(native)
    return native


@pytest.fixture
def fixture(tmp_path, monkeypatch):
    native = load()
    monkeypatch.setattr(native, 'ROOT', tmp_path)
    (tmp_path / 'workspaces').mkdir()
    program = DatabaseProgramConfig.from_mapping({
        'task_source_kind': 'duckdb', 'authority_mode': 'quack',
        'quack_endpoint': 'quack:127.0.0.1:12345', 'endpoint_secret_handle': 'env://TEST',
        'store_id': 'control.duckdb', 'store_generation': 'g1', 'schema_revision': '1',
        'failover_policy': 'fail_closed', 'worktree_root': 'workspaces',
        'owner_management': {'mode': 'managed_local', 'owner_state_dir': str(tmp_path / 'owner'),
            'initial_backoff_seconds': 1.0, 'max_backoff_seconds': 10.0,
            'health_check_interval_seconds': 5.0, 'max_restart_attempts': 8,
            'startup_timeout_seconds': 120.0, 'termination_grace_seconds': 40.0}})
    board = SimpleNamespace(max_lanes=4, task_prefix='PCTDD-', task_header_prefix='## PCTDD-',
                            board_namespace='pctdd', resolved_database_program=lambda: program)
    lanes = []
    for index in range(4):
        args = ['--todo-path', str(tmp_path / 'todo.md'), '--state-dir', str(tmp_path / f'lane-{index}'),
                '--state-prefix', f'pctdd_lane_{index}', '--task-prefix', board.task_header_prefix,
                '--board-namespace', board.board_namespace, '--task-shard-count', '4',
                '--task-shard-index', str(index), *program.cli_args()]
        config = IS.supervisor_config_from_args(IS.parse_args(args), repo_root=tmp_path)
        renderer = object.__new__(IS.PortalImplementationSupervisor)
        renderer.config = config
        renderer.board_namespace = board.board_namespace
        lanes.append(({'argv': [sys.executable,
            str(tmp_path / 'scripts/ops/agent_supervisor/implementation_supervisor_entry.py'), *args]},
            {'argv': renderer._build_daemon_command()}, config))
    master = {'argv': [sys.executable, '-m',
        'ipfs_accelerate_py.agent_supervisor.runtime.multi_supervisor_runner',
        '--repo-root', str(tmp_path), '--master-dir', str(tmp_path / 'runtime'),
        '--database-program-json', json.dumps(program.to_dict())]}
    return native, board, lanes, master


def test_actual_cli_projection_and_complete_master_program(fixture, monkeypatch):
    native, board, lanes, master = fixture
    def forbidden(*args, **kwargs):
        raise AssertionError('supervisor constructor must not run')
    monkeypatch.setattr(IS.PortalImplementationSupervisor, '__init__', forbidden)
    native._maintenance_master_program(board, master)
    for wrapper, daemon, config in lanes:
        assert config.database_program.worktree_root == ''
        assert config.database_program.owner_management is None
        assert board.resolved_database_program().owner_management is not None
        assert config.task_prefix == board.task_header_prefix != board.task_prefix
        native._maintenance_daemon_command(board, wrapper, daemon)


@pytest.mark.parametrize('flag,value', [
    ('--state-store-id', 'foreign.duckdb'), ('--state-store-generation', 'foreign'),
    ('--quack-endpoint', 'quack:127.0.0.1:22222'), ('--endpoint-secret-handle', 'env://OTHER'),
    ('--task-prefix', 'PCTDD-'), ('--board-namespace', 'foreign'),
    ('--task-shard-count', '3'), ('--worktree-root', 'foreign-workspaces')])
def test_worker_authority_header_and_worktree_drift_refuse(fixture, flag, value):
    native, board, lanes, _ = fixture
    wrapper, daemon, _ = lanes[0]
    argv = wrapper['argv']; argv[argv.index(flag) + 1] = value
    with pytest.raises((native.OperatorError, ValueError)):
        native._maintenance_daemon_command(board, wrapper, daemon)


@pytest.mark.parametrize('field', ['owner_management', 'worktree_root', 'store_id', 'unknown', 'numeric_bool'])
def test_master_program_must_remain_complete_and_typed(fixture, field):
    native, board, _, master = fixture
    argv = master['argv']; index = argv.index('--database-program-json') + 1
    program = json.loads(argv[index])
    if field == 'owner_management':
        program.pop(field)
    elif field == 'unknown':
        program['unqualified_policy'] = True
    elif field == 'numeric_bool':
        program['owner_management']['initial_backoff_seconds'] = True
    else:
        program[field] = 'foreign'
    argv[index] = json.dumps(program)
    with pytest.raises(native.OperatorError, match='master configured program differs'):
        native._maintenance_master_program(board, master)


def test_native_launch_monitor_uses_complete_master_validation(fixture):
    native, board, _, master = fixture
    monitor = object.__new__(native._BlockedMaintenanceMonitor)
    monitor.board = board
    monitor.paths = {'runtime': native.ROOT / 'runtime'}
    monitor.actor = lambda pid: copy.deepcopy(master)
    monitor.bind_launch({'json': {'master_pid': 123}})
    argv = master['argv']; argv[argv.index('--database-program-json') + 1] = '{}'
    with pytest.raises(native.OperatorError, match='master configured program differs'):
        monitor.bind_launch({'json': {'master_pid': 123}})


def test_complete_rendered_daemon_argv_is_required(fixture):
    native, board, lanes, _ = fixture
    wrapper, daemon, _ = lanes[0]
    daemon['argv'].append('--unexpected-option')
    with pytest.raises(native.OperatorError, match='native daemon command differs'):
        native._maintenance_daemon_command(board, wrapper, daemon)
