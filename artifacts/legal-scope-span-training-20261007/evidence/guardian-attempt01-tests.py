"""Pure refusal and process-ownership checks; never acquire a real lease."""
from importlib.util import module_from_spec, spec_from_file_location
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

SPEC = spec_from_file_location('scope_guardian_under_test', Path(__file__).with_name('run_scope_guardian.py'))
guardian = module_from_spec(SPEC)
SPEC.loader.exec_module(guardian)


def reviewed(tmp_path):
    candidate = tmp_path / 'candidate'
    (candidate / 'ipfs_datasets_py').mkdir(parents=True)
    plan, runner = tmp_path / 'plan.json', tmp_path / 'runner.py'
    plan.write_text('{}')
    runner.write_text('raise RuntimeError("must never execute during these tests")\n')
    paths = [plan, runner, Path(guardian.__file__).resolve()]
    review = dict(passed=True, findings=[], phase='training', package_root=str(candidate),
                  run_root=str(guardian.RUN_ROOT), plan_sha256=guardian.pin(plan)['sha256'],
                  runner_sha256=guardian.pin(runner)['sha256'],
                  guardian_sha256=guardian.pin(paths[-1])['sha256'],
                  artifacts={str(p): guardian.pin(p) for p in paths})
    path = tmp_path / 'review.json'
    path.write_text(json.dumps(review))
    return SimpleNamespace(plan=plan, runner=runner, package_root=candidate, review=path), review


def test_review_accepts_exact_complete_bindings_without_launch(tmp_path):
    args, _ = reviewed(tmp_path)
    result = guardian.validate_review(args)
    assert result[:3] == (args.plan, args.runner, args.package_root)


@pytest.mark.parametrize('mutation', ['runner', 'plan', 'failed', 'findings', 'package_root', 'run_root', 'guardian', 'missing_artifact'])
def test_review_refuses_changes_before_admission(tmp_path, mutation):
    args, review = reviewed(tmp_path)
    if mutation in ('runner', 'plan'):
        getattr(args, mutation).write_text('changed')
    elif mutation == 'failed':
        review['passed'] = False
    elif mutation == 'findings':
        review['findings'] = ['incomplete labels']
    elif mutation in ('package_root', 'run_root'):
        review[mutation] += '-different'
    elif mutation == 'guardian':
        review['guardian_sha256'] = '0' * 64
    elif mutation == 'missing_artifact':
        del review['artifacts'][str(args.runner)]
    args.review.write_text(json.dumps(review))
    with pytest.raises(ValueError):
        guardian.validate_review(args)


@pytest.mark.parametrize('data', ['{"a":1,"a":2}', '{"value":NaN}', '{"value":Infinity}'])
def test_finite_unique_json_required(tmp_path, data):
    path = tmp_path / 'input.json'
    path.write_text(data)
    with pytest.raises(ValueError):
        guardian.read_json(path)


def test_cleanup_never_inspects_or_signals_mismatched_child():
    class Resources:
        def _group_usage(self, _):
            raise AssertionError('foreign identity must not be inspected')
    with pytest.raises(ValueError, match='captured isolated'):
        guardian.cleanup(SimpleNamespace(pid=1234), {'pid': 1235, 'birth': 'x'}, Resources())


def test_dead_owned_child_is_reaped_without_signal(monkeypatch):
    class Child:
        pid = 1234
        def wait(self, timeout):
            assert timeout == 5
            return 7
    class Resources:
        def _group_usage(self, identity):
            assert identity == {'pid': 1234, 'birth': 'original'}
            return {'live_processes': 0}
    monkeypatch.setattr(guardian.os, 'killpg', lambda *_: pytest.fail('dead group must not be signaled'))
    result = guardian.cleanup(Child(), {'pid': 1234, 'birth': 'original'}, Resources())
    assert result['leader_returncode'] == 7 and result['leader_reaped']
    assert result['signals'] == []


def test_symlink_artifact_refused(tmp_path):
    target = tmp_path / 'target'
    target.write_text('data')
    link = tmp_path / 'link'
    link.symlink_to(target)
    with pytest.raises(ValueError, match='regular artifact'):
        guardian.pin(link)


def test_admission_failure_retains_outer_receipts_without_child_or_lease(tmp_path, monkeypatch):
    monkeypatch.setattr(guardian, 'RUN_ROOT', tmp_path / 'physical-run')
    args, _ = reviewed(tmp_path)
    args.attempt = 'admission-refused'

    class Owner:
        _record = None
        _lease = None
        def __init__(self, *_, **__):
            pass
        def __enter__(self):
            raise RuntimeError('test admission refusal')
        def __exit__(self, *_):
            pytest.fail('failed admission must not enter owner context')

    resources = SimpleNamespace(DaemonResourceReservation=Owner)
    lazy = SimpleNamespace(install=lambda *_, **__: lambda: pytest.fail('adoption must not complete'))
    watch = SimpleNamespace(safe_exception=lambda error: {'error_type': type(error).__name__},
                            safe_owner_snapshot=lambda _: {'status': 'not_admitted'})
    monkeypatch.setattr(guardian, 'closure_and_configuration',
                        lambda: (resources, None, SimpleNamespace(adopt_for_owner=None), lazy, watch, {'passed': True}))
    monkeypatch.setattr(guardian.subprocess, 'Popen', lambda *_, **__: pytest.fail('no child after failed admission'))
    assert guardian.execute(args) == 1
    output = guardian.RUN_ROOT / args.attempt
    receipt = json.loads((output / 'guardian-exit.json').read_text())
    assert receipt['returncode'] == 1 and receipt['child_returncode'] is None
    assert receipt['resource_reservation_released'] is False
    assert (output / 'resources-final-failure.json').is_file()
    assert json.loads((output / 'child-exit.json').read_text())['child_created'] is False


def test_watchdog_setup_and_cleanup_failure_keep_live_child_lease(tmp_path, monkeypatch):
    monkeypatch.setattr(guardian, 'RUN_ROOT', tmp_path / 'physical-run')
    args, _ = reviewed(tmp_path)
    args.attempt = 'watchdog-refused'
    events = []
    child = SimpleNamespace(pid=999991, poll=lambda: None)

    class Lease:
        _released = False
        def release(self):
            events.append('lease_released')
            self._released = True

    class Owner:
        def __init__(self, *_, **__):
            self._record = {'status': 'active'}
            self._lease = Lease()
            self._child = None
            self._owner_pid = guardian.os.getpid()
            self._entered = True
        def __enter__(self):
            return self
        def _update(self, **fields):
            assert self._child == {'pid': child.pid, 'birth': 'owned-birth'}
            self._record.update(fields)
            events.append('durable_child_binding')
        def check_usage(self, *unused):
            assert self._child is not None
            events.append('usage_registered')
            return {'rss_bytes': 1}
        def __exit__(self, *_):
            self._record['status'] = 'retained'
            events.append('owner_exit_child_bound' if self._child else 'owner_exit_child_absent')
            if self._child is None:
                self._lease.release()

    class Watchdog:
        def __init__(self, *_, **__):
            pass
        def observe(self, _):
            pass
        def bind_child(self, _):
            events.append('watchdog_refused')
            raise RuntimeError('test watchdog setup failure')
        def stop(self):
            pass
        def close(self):
            pass

    resources = SimpleNamespace(DaemonResourceReservation=Owner,
        _process=lambda pid: {'pid': pid, 'birth': 'owned-birth', 'group_pid': pid,
                              'parent_pid': guardian.os.getpid()})
    lazy = SimpleNamespace(install=lambda *_, **__: lambda: {})
    watch = SimpleNamespace(OwnedLeaseWatchdog=Watchdog,
        capture_lease_binding=lambda *args: SimpleNamespace(public=lambda: {}),
        safe_exception=lambda error: {'error_type': type(error).__name__},
        safe_owner_snapshot=lambda owner: {'status': owner._record['status'],
                                          'lease_released': owner._lease._released})
    monkeypatch.setattr(guardian, 'closure_and_configuration',
                        lambda: (resources, None, SimpleNamespace(adopt_for_owner=None), lazy, watch, {}))
    monkeypatch.setattr(guardian.subprocess, 'Popen', lambda *_, **__: child)
    def failed_cleanup(*_):
        events.append('cleanup_failed')
        raise RuntimeError('test surviving owned child')
    monkeypatch.setattr(guardian, 'cleanup', failed_cleanup)
    assert guardian.execute(args) == 1
    assert events.index('durable_child_binding') < events.index('watchdog_refused')
    assert events.index('cleanup_failed') < events.index('owner_exit_child_bound')
    assert 'owner_exit_child_absent' not in events and 'lease_released' not in events
    receipt = json.loads((guardian.RUN_ROOT / args.attempt / 'guardian-exit.json').read_text())
    assert receipt['resources']['lease_released'] is False
    assert receipt['retained_reservation_requires_explicit_reconciliation'] is True
