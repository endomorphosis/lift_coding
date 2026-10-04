"""The repair service must delegate the whole sealed operator before mutation."""
import sys

import pytest

from ipfs_accelerate_py.agent_supervisor.runtime import durable_launch
import importlib.util
from pathlib import Path

FACADE = Path(__file__).resolve().parents[3] / "scripts/ops/agent_supervisor/parallel_content_sealing_proof_carrying_tdd.py"

def _load(name):
    spec = importlib.util.spec_from_file_location(name, FACADE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize('command', [['resume', '--monitor-seconds', '17'], ['launch', '--real']])
@pytest.mark.parametrize('exit_code', [0, 78])
def test_native_entry_delegates_before_owner_and_source_checks(monkeypatch, command, exit_code):
    facade = _load('pctdd_durable_entry')
    calls = []
    def delegate(argv):
        calls.append(argv)
        return exit_code
    monkeypatch.setattr(durable_launch, 'delegate_repair_service_launch', delegate)
    monkeypatch.setattr(facade, '_load_board', lambda *_a: pytest.fail('outer operator loaded authority'))
    monkeypatch.setattr(facade, 'resume', lambda *_a, **_k: pytest.fail('outer operator resumed'))
    monkeypatch.setattr(facade, 'launch', lambda *_a, **_k: pytest.fail('outer operator launched'))
    argv = ['--config', '/repo with spaces/config.json', *command]
    assert facade.main(argv) == exit_code
    assert calls == [[sys.executable, str(FACADE.resolve()), *argv]]


def test_inner_native_entry_keeps_original_admission(monkeypatch):
    facade = _load('pctdd_inner_entry')
    monkeypatch.setattr(durable_launch, 'delegate_repair_service_launch', lambda argv: None)
    calls = []
    def resume(config, **kwargs):
        calls.append((config, kwargs))
        raise facade.OperatorError('source not qualified')
    monkeypatch.setattr(facade, 'resume', resume)
    assert facade.main(['resume', '--monitor-seconds', '17']) == 2
    assert calls == [(facade.DEFAULT_CONFIG, {'monitor_seconds': 17.0})]


def test_launch_lifetime_observation_failure_refuses_native_action(monkeypatch):
    facade = _load('pctdd_lifetime_unknown')
    def unavailable(argv):
        raise RuntimeError('cgroup unavailable')
    monkeypatch.setattr(durable_launch, 'delegate_repair_service_launch', unavailable)
    monkeypatch.setattr(facade, 'resume', lambda *_a, **_k: pytest.fail('unqualified lifetime launched'))
    assert facade.main(['resume']) == 2


def test_dry_run_does_not_delegate(monkeypatch):
    facade = _load('pctdd_dry_run')
    monkeypatch.setattr(durable_launch, 'delegate_repair_service_launch', lambda argv: pytest.fail('dry run delegated'))
    monkeypatch.setattr(facade, 'launch', lambda *_a, **_k: {'dry_run': True})
    assert facade.main(['launch', '--dry-run']) == 0
