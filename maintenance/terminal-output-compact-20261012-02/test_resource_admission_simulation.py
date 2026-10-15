"""Deterministic admission/active-pressure checks against the frozen launcher.

All provider/process launches and resource samples are substituted. State is
written only under pytest temporary directories, never the live launcher-state.
"""
from __future__ import annotations

import importlib.util
import io
import json
from pathlib import Path
import subprocess
from unittest.mock import Mock

import pytest

PATH = Path(__file__).with_name('run-prepared-trials.py')
spec = importlib.util.spec_from_file_location('authored_resource_launcher', PATH)
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)

PRESSURES = (
    ('memory', 'mem_available_bytes', 24 * launcher.GIB - 1, 'available_memory_below_24_GiB'),
    ('disk', 'disk_free_bytes', 20 * launcher.GIB - 1, 'free_disk_below_20_GiB'),
    ('load', 'load_1m', 17.01, 'load_above_85_percent_of_affinity_CPUs'),
)


def healthy():
    return dict(at='authored-fixed-time', mem_available_bytes=24 * launcher.GIB,
                disk_free_bytes=20 * launcher.GIB, load_1m=17.0, affinity_cpus=20,
                load_limit=17.0)


def pressured(case):
    _, field, value, _ = case
    return {**healthy(), field: value}


class SimulatedClock:
    def __init__(self):
        self.elapsed = 0.0
        self.sleeps = []

    def monotonic(self):
        return self.elapsed

    def sleep(self, duration):
        self.sleeps.append(duration)
        self.elapsed += duration


def admissions(stream):
    return [row for row in map(json.loads, stream.getvalue().splitlines())
            if row['event'] == 'resource_admission']


def test_exact_admission_thresholds_accept():
    assert launcher.pressure_reasons(healthy()) == []


@pytest.mark.parametrize('case', PRESSURES, ids=lambda case: case[0])
def test_each_independent_pressure_reason_rejects(case):
    assert launcher.pressure_reasons(pressured(case)) == [case[3]]


def test_all_pressure_reasons_are_reported_together():
    sample = healthy()
    for case in PRESSURES:
        sample[case[1]] = case[2]
    assert set(launcher.pressure_reasons(sample)) == {case[3] for case in PRESSURES}


def test_load_threshold_uses_current_cpu_affinity():
    sample = {**healthy(), 'affinity_cpus': 10, 'load_1m': 8.51, 'load_limit': 17.0}
    assert launcher.pressure_reasons(sample) == [PRESSURES[2][3]]
    assert launcher.pressure_reasons({**sample, 'load_1m': 8.5}) == []


@pytest.mark.parametrize('case', PRESSURES, ids=lambda case: case[0])
def test_independent_pressure_backs_off_5_10_20_30_capped_then_recovers(case):
    clock, stream = SimulatedClock(), io.StringIO()
    samples = iter([pressured(case)] * 5 + [healthy()])
    result = launcher.await_resources(stream, 300, sample_fn=lambda: next(samples),
        sleeper=clock.sleep, monotonic=clock.monotonic)
    assert result == healthy()
    assert clock.sleeps == [5.0, 10.0, 20.0, 30.0, 30.0]
    assert clock.elapsed == 95.0
    decisions = admissions(stream)
    assert [row['admitted'] for row in decisions] == [False] * 5 + [True]
    assert all(row['pressure_reasons'] == [case[3]] for row in decisions[:-1])
    assert decisions[-1]['pressure_reasons'] == []


@pytest.mark.parametrize('case', PRESSURES, ids=lambda case: case[0])
def test_remaining_wait_bounds_last_sleep_and_stops_at_deadline(case):
    clock, stream = SimulatedClock(), io.StringIO()
    with pytest.raises(TimeoutError, match='no trial launched'):
        launcher.await_resources(stream, 13, sample_fn=lambda: pressured(case),
            sleeper=clock.sleep, monotonic=clock.monotonic)
    assert clock.sleeps == [5.0, 8.0]
    assert clock.elapsed == 13
    assert [row['admitted'] for row in admissions(stream)] == [False, False, False]


@pytest.mark.parametrize('case', PRESSURES, ids=lambda case: case[0])
def test_zero_wait_pressure_fails_without_sleep(case):
    sleep = Mock(side_effect=AssertionError('no sleep authorized'))
    with pytest.raises(TimeoutError):
        launcher.await_resources(io.StringIO(), 0, sample_fn=lambda: pressured(case),
            sleeper=sleep, monotonic=lambda: 0)
    sleep.assert_not_called()


def test_zero_wait_healthy_sample_is_admitted_without_sleep():
    sleep = Mock(side_effect=AssertionError('no sleep authorized'))
    assert launcher.await_resources(io.StringIO(), 0, sample_fn=healthy,
        sleeper=sleep, monotonic=lambda: 0) == healthy()
    sleep.assert_not_called()


def fixture_trial(tmp_path, monkeypatch):
    state = tmp_path / 'isolated-launcher-state'
    state.mkdir()
    output = tmp_path / 'authored-output'
    output.mkdir()
    trial = dict(name='authored-only', output=output, job=output/'jobs/authored', config_sha256='a'*64)
    monkeypatch.setattr(launcher, 'STATE', state)
    monkeypatch.setattr(launcher, 'validate_trial', Mock(return_value=trial))
    monkeypatch.setattr(launcher, 'unresolved_campaign_invocations', Mock(return_value=[]))
    monkeypatch.setattr(launcher, 'process_sample', Mock(return_value={'pid': 12345, 'returncode': None}))
    monkeypatch.setattr(launcher, 'collect_outcome', Mock(return_value={'classification': 'authored_complete', 'continue_batch': True}))
    monkeypatch.setattr(launcher.subprocess, 'check_output', Mock(side_effect=AssertionError('external inspection forbidden')))
    monkeypatch.setattr(launcher.subprocess, 'run', Mock(side_effect=AssertionError('external execution forbidden')))
    return trial, state / trial['name']


def install_admission_simulation(monkeypatch, samples, clock):
    original = launcher.await_resources
    sample_fn = Mock(side_effect=samples)
    def simulated(stream, max_wait):
        return original(stream, max_wait, sample_fn=sample_fn,
                        sleeper=clock.sleep, monotonic=clock.monotonic)
    monkeypatch.setattr(launcher, 'await_resources', simulated)
    return sample_fn


@pytest.mark.parametrize('case', PRESSURES, ids=lambda case: case[0])
def test_run_trial_wait_exhaustion_creates_no_claim_or_process(tmp_path, monkeypatch, case):
    trial, state = fixture_trial(tmp_path, monkeypatch)
    clock = SimulatedClock()
    install_admission_simulation(monkeypatch, [pressured(case)] * 3, clock)
    popen = Mock(side_effect=AssertionError('process launch forbidden before admission'))
    monkeypatch.setattr(launcher.subprocess, 'Popen', popen)
    result = launcher.run_trial(trial, env={}, overrides={}, max_wait=13, interval=15)
    assert result == dict(trial='authored-only', classification='resource_wait_exhausted',
                          continue_batch=False, process_started=False)
    assert clock.sleeps == [5.0, 8.0]
    popen.assert_not_called()
    launcher.validate_trial.assert_not_called()
    launcher.collect_outcome.assert_not_called()
    assert not (state/'claim.json').exists()
    assert not (state/'process.json').exists()
    assert not (state/'execute.stdout').exists()
    assert json.loads((state/'outcome.json').read_text()) == result


@pytest.mark.parametrize('case', PRESSURES, ids=lambda case: case[0])
def test_recovered_resources_precede_revalidation_claim_and_launch(tmp_path, monkeypatch, case):
    trial, state = fixture_trial(tmp_path, monkeypatch)
    clock = SimulatedClock()
    install_admission_simulation(monkeypatch, [pressured(case), pressured(case), healthy()], clock)
    process = Mock(pid=12345)
    process.wait.return_value = 0
    def admitted_popen(*args, **kwargs):
        assert clock.elapsed == 15.0
        launcher.validate_trial.assert_called_once_with('authored-only')
        launcher.unresolved_campaign_invocations.assert_called_once()
        assert (state/'claim.json').is_file()
        records = [json.loads(line) for line in (state/'events.jsonl').read_text().splitlines()]
        assert records[-1]['event'] == 'resource_admission' and records[-1]['admitted'] is True
        return process
    popen = Mock(side_effect=admitted_popen)
    monkeypatch.setattr(launcher.subprocess, 'Popen', popen)
    monkeypatch.setattr(launcher, 'resource_sample', Mock(return_value=healthy()))
    result = launcher.run_trial(trial, env={'AUTHORED': '1'}, overrides={}, max_wait=100, interval=15)
    assert result['classification'] == 'authored_complete'
    popen.assert_called_once()
    process.wait.assert_called_once_with(timeout=15)
    assert clock.sleeps == [5.0, 10.0]
    assert json.loads((state/'claim.json').read_text())['automatic_retry'] is False
    launcher.collect_outcome.assert_called_once_with(trial, 0)


@pytest.mark.parametrize('case', PRESSURES, ids=lambda case: case[0])
def test_pressure_after_launch_is_observed_without_backoff_or_termination(tmp_path, monkeypatch, case):
    trial, state = fixture_trial(tmp_path, monkeypatch)
    clock = SimulatedClock()
    admission_samples = install_admission_simulation(monkeypatch, [healthy()], clock)
    process = Mock(pid=12345)
    process.wait.side_effect = [subprocess.TimeoutExpired('authored-no-process', 15), 0]
    popen = Mock(return_value=process)
    monkeypatch.setattr(launcher.subprocess, 'Popen', popen)
    active_samples = Mock(side_effect=[pressured(case), pressured(case)])
    monkeypatch.setattr(launcher, 'resource_sample', active_samples)
    result = launcher.run_trial(trial, env={}, overrides={}, max_wait=100, interval=15)
    assert result['classification'] == 'authored_complete'
    assert clock.sleeps == []
    admission_samples.assert_called_once()
    assert active_samples.call_count == 2
    popen.assert_called_once()
    process.terminate.assert_not_called()
    process.kill.assert_not_called()
    process.send_signal.assert_not_called()
    records = [json.loads(line) for line in (state/'events.jsonl').read_text().splitlines()]
    active = [row for row in records if row['event'] == 'active_trial_sample']
    assert len(active) == 2
    assert all(row['pressure_reasons'] == [case[3]] for row in active)
    assert all(row['pressure_action'] == 'observe_only_no_termination' for row in active)
    assert not any(row['event'] == 'resource_backoff' for row in records)
