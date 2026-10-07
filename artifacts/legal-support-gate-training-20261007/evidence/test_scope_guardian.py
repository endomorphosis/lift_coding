"""Pure refusal and process-ownership checks; never acquire a real lease."""
from importlib.util import module_from_spec, spec_from_file_location
import json
from pathlib import Path
from types import SimpleNamespace
import threading
import time

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


@pytest.mark.parametrize('usage_fails', [False, True])
def test_slow_initial_usage_is_monitored_while_model_stays_gated(tmp_path, monkeypatch, usage_fails):
    monkeypatch.setattr(guardian, 'RUN_ROOT', tmp_path / 'physical-run')
    args, _ = reviewed(tmp_path)
    args.attempt = 'slow-initial-usage'
    events = []
    clock = {'now': 0.0}
    monkeypatch.setattr(guardian.time, 'monotonic', lambda: clock['now'])
    child = SimpleNamespace(pid=999992, poll=lambda: 0, wait=lambda timeout=None: 0)
    active = {'watchdog': False, 'gate': False}

    class Lease:
        _released = False
        def release(self):
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
            events.append('durable_child_custody')
        def check_usage(self, *unused):
            assert active['watchdog'] and not active['gate']
            events.append('usage_started')
            # A mocked 14.43-second census, longer than the unchanged five-second
            # gap budget, with independent sampled monitoring already active.
            for _ in range(14):
                clock['now'] += 1.0
                assert active['watchdog'] and not active['gate']
                events.append('monitor_during_census')
            clock['now'] += .43
            if usage_fails:
                raise RuntimeError('test resource census refusal')
            events.append('usage_passed')
            return {'rss_bytes': 1}
        def finalize(self, *_, **__):
            self._record['status'] = 'released'
            self._lease.release()
            return {'status': 'released'}
        def __exit__(self, *_):
            if self._record['status'] != 'released':
                self._record['status'] = 'retained'
                self._lease.release()

    class Watchdog:
        def __init__(self, *_, **kwargs):
            self.events_path = kwargs['events_path']
            self.events_path.write_text('{}\n')
        def observe(self, *_, **__):
            return {'healthy': True}
        def bind_child(self, _):
            events.append('watchdog_bound')
        def start(self):
            active['watchdog'] = True
            events.append('watchdog_started')
        def assert_healthy(self):
            assert active['watchdog'] or 'usage_passed' in events
        def stop(self):
            active['watchdog'] = False
        def close(self):
            self.stop()

    class RSSSampler:
        def __init__(self, *_, **kwargs):
            self.events_path = kwargs['events_path']
            self.events_path.write_text('{}\n')
            self._closed = False
        def start(self):
            events.append('rss_started')
        def assert_healthy(self):
            pass
        def mark_model_started(self):
            assert 'usage_passed' in events and 'model_permitted' in events
            events.append('model_rss_started')
        def mark_model_stopped(self):
            pass
        def sample(self, _):
            pass
        def stop(self):
            pass
        def close(self):
            self._closed = True
        def snapshot(self):
            return dict(sampled_model_phase_peak_rss_bytes=42, model_phase_sample_count=1)

    resources = SimpleNamespace(DaemonResourceReservation=Owner,
        _process=lambda pid: {'pid': pid, 'birth': 'owned-birth', 'group_pid': pid,
                              'parent_pid': guardian.os.getpid()})
    lazy = SimpleNamespace(install=lambda *_, **__: lambda: {})
    watch = SimpleNamespace(OwnedLeaseWatchdog=Watchdog,
        capture_lease_binding=lambda *args: SimpleNamespace(public=lambda: {}),
        safe_exception=lambda error: {'error_type': type(error).__name__},
        safe_owner_snapshot=lambda owner: {'status': owner._record['status']})
    monkeypatch.setattr(guardian, 'closure_and_configuration',
                        lambda: (resources, None, SimpleNamespace(adopt_for_owner=None), lazy, watch, {}))
    monkeypatch.setattr(guardian.subprocess, 'Popen', lambda *_, **__: child)
    monkeypatch.setattr(guardian, 'OwnedGroupRSSSampler', RSSSampler)
    monkeypatch.setattr(guardian, 'cleanup', lambda *_: {'live_group_processes': 0, 'leader_reaped': True})
    def permit(_fd, data):
        assert data == b'1' and active['watchdog'] and 'usage_passed' in events
        assert clock['now'] == pytest.approx(14.43)
        active['gate'] = True
        events.append('model_permitted')
        output = guardian.RUN_ROOT / args.attempt / 'results'
        output.mkdir()
        (output / 'summary.json').write_text('{}')
        return 1
    monkeypatch.setattr(guardian.os, 'write', permit)
    result = guardian.execute(args)
    assert result == (1 if usage_fails else 0)
    assert events.index('durable_child_custody') < events.index('watchdog_started') < events.index('usage_started')
    assert events.index('watchdog_started') < events.index('rss_started') < events.index('usage_started')
    assert events.count('monitor_during_census') == 14
    if usage_fails:
        assert 'model_permitted' not in events
        assert not (guardian.RUN_ROOT / args.attempt / 'results').exists()
    else:
        assert events.index('usage_passed') < events.index('model_permitted')


def test_rss_sampler_separates_gated_model_and_post_model_samples(tmp_path):
    current = {'rss': 10, 'live': 1}
    polled = threading.Event()
    class Resources:
        def _group_usage(self, identity):
            assert identity == {'pid': 23456, 'birth': 'owned'}
            polled.set()
            return dict(available=True, rss_bytes=current['rss'], live_processes=current['live'])
    path = tmp_path / 'rss.jsonl'
    sampler = guardian.OwnedGroupRSSSampler(Resources(), {'pid': 23456, 'birth': 'owned'},
        events_path=path, memory_limit_bytes=1000, safe_exception=lambda error: {'type': type(error).__name__},
        poll_seconds=.01, signal_group=lambda *_: pytest.fail('healthy samples must not signal'))
    sampler.start()
    current['rss'] = 100
    sampler.mark_model_started()
    current['rss'] = 250
    polled.clear()
    assert polled.wait(.5)
    # Event is set at collection, so wait for its bounded log update before stop.
    deadline = time.monotonic() + .5
    while sampler.snapshot()['sampled_model_phase_peak_rss_bytes'] != 250 and time.monotonic() < deadline:
        time.sleep(.001)
    current.update(rss=0, live=0)
    sampler.mark_model_stopped()
    sampler.close()
    summary = sampler.snapshot()
    assert summary['sampled_model_phase_peak_rss_bytes'] == 250
    assert summary['sampled_peaks_by_phase']['gated'] == 10
    assert summary['model_phase_sample_count'] >= 2
    assert summary['sample_counts_by_phase']['post_model'] >= 1
    assert summary['model_phase_wall_seconds'] > 0
    assert summary['absolute_peak_measured'] is summary['kernel_hard_cap'] is summary['continuous_coverage_claimed'] is False
    events = [json.loads(line) for line in path.read_text().splitlines()]
    assert {'gated', 'model', 'post_model'} <= {e['phase'] for e in events}
    assert all(e['sampled_only'] and not e['scheduler_or_claim_mutation'] for e in events)


def test_rss_sampler_observes_during_independent_slow_operation(tmp_path):
    collected = []
    class Resources:
        def _group_usage(self, _):
            collected.append(time.monotonic())
            return dict(available=True, rss_bytes=10, live_processes=1)
    sampler = guardian.OwnedGroupRSSSampler(Resources(), {'pid': 23456, 'birth': 'owned'},
        events_path=tmp_path / 'rss.jsonl', memory_limit_bytes=1000,
        safe_exception=lambda error: {'type': type(error).__name__}, poll_seconds=.01)
    sampler.start()
    # Represents a blocked main-thread disk census; there is no lease/census here.
    threading.Event().wait(.055)
    sampler.close()
    assert len(collected) >= 3
    assert sampler.snapshot()['model_phase_sample_count'] == 0
    assert sampler.snapshot()['sampled_model_phase_peak_rss_bytes'] is None


def test_rss_over_envelope_interrupts_only_verified_owned_group(tmp_path):
    identity = {'pid': 23456, 'birth': 'owned'}
    calls = []
    class Resources:
        def _group_usage(self, actual):
            assert actual == identity
            return dict(available=True, rss_bytes=1001, live_processes=1)
    sampler = guardian.OwnedGroupRSSSampler(Resources(), identity,
        events_path=tmp_path / 'rss.jsonl', memory_limit_bytes=1000,
        safe_exception=lambda error: {'type': type(error).__name__},
        signal_group=lambda pid, sig: calls.append((pid, sig)))
    with pytest.raises(guardian.GroupRSSSamplerError):
        sampler.start()
    sampler.close()
    assert calls == [(identity['pid'], guardian.signal.SIGINT)]
    assert sampler.snapshot()['failure']['owned_group_interrupt'] == 'SIGINT_sent'
    assert sampler.snapshot()['sample_counts_by_phase']['gated'] == 1


def test_rss_unknown_or_reused_group_refuses_signal(tmp_path):
    class Resources:
        def _group_usage(self, _):
            raise RuntimeError('birth mismatch')
    sampler = guardian.OwnedGroupRSSSampler(Resources(), {'pid': 23456, 'birth': 'owned'},
        events_path=tmp_path / 'rss.jsonl', memory_limit_bytes=1000,
        safe_exception=lambda error: {'type': type(error).__name__},
        signal_group=lambda *_: pytest.fail('unverified group must not receive signal'))
    with pytest.raises(guardian.GroupRSSSamplerError):
        sampler.start()
    sampler.close()
    assert sampler.snapshot()['failure']['owned_group_interrupt'] == 'refused_or_failed'
