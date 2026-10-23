'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { assessObserverHealth, probeProcess } = require('./vdg-observer-health.cjs');
const ROOT = '/workspace/project';
const WATCHDOG = `${ROOT}/data/watchdog`;
const NOW = Date.parse('2026-10-21T07:00:00Z');
const LIFECYCLE = 'ipfs_accelerate_py/agent-supervisor/lifecycle-status@1';
const MOD = 'ipfs_accelerate_py.agent_supervisor.rescue.';
function fixture() {
  const guardian = { schema: 'ipfs_accelerate_py.agent_supervisor.watchdog-guardian@1', guardian_pid: 1,
    observed_at_ms: NOW - 10000, owner_pid: 3, owner_alive: true, owners: [{ pid: 3, start_ticks: '103' }], errors: [], hold_markers: [], report_health: 'fresh' };
  const dispatcher = { schema: 'ipfs_accelerate_py.agent_supervisor.repair-dispatcher@1', observed_at: (NOW - 10000) / 1000,
    action: 'healthy', held: false, incidents: [], owner: { pid: 3, start_ticks: 103 }, owner_discovery_errors: [], owner_discovery_uncertain: false };
  const watchdog = { timestamp: new Date(NOW - 100000).toISOString(), status: { schema: LIFECYCLE, pid: 3, state: 'healthy' } };
  const lane = { schema: LIFECYCLE, pid: 4, state: 'healthy', phase: 'deterministic_command', heartbeat_at_ms: NOW - 2000 };
  const modules = ['watchdog_guardian', 'repair_dispatcher', 'supervisor_watchdog', 'lane_resume'];
  const processes = Object.fromEntries(modules.map((module, index) => {
    const pid = index + 1;
    return [pid, { pid, alive: true, uid: 1003, start_ticks: String(100 + pid), argv: ['/usr/bin/python3', '-m', MOD + module,
      '--repo-root', ROOT, ...(module === 'lane_resume' ? ['--status-path', `${WATCHDOG}/lane.json`, '--bundle-key', 'vdg-planning']
        : ['--manifest-path', `${WATCHDOG}/bundle_lanes.json`])] }];
  }));
  return { nowMs: NOW, repoRoot: ROOT, manifestPath: `${WATCHDOG}/bundle_lanes.json`, laneStatusPath: `${WATCHDOG}/lane.json`, uid: 1003,
    pids: { dispatcher: 2, watchdog: 3, lane: 4 }, processes,
    snapshots: Object.fromEntries(Object.entries({ guardian, dispatcher, watchdog, lane }).map(([role, data]) => [role, { data, mtimeMs: NOW - 1000, error: '' }])) };
}
const has = (health, component, code) => health.warnings.some(item => item.component === component && item.code === code);

test('fresh exact live identities establish observation health at normal 120-second watchdog cadence', () => {
  const data = fixture();
  const result = assessObserverHealth(data);
  assert.equal(result.healthy, true);
  assert.equal(result.state, 'healthy');
  assert.deepEqual(result.warnings, []);
  assert.equal(result.reports.watchdog.age_seconds, 100);
  assert.equal(result.reports.watchdog.stale_after_seconds, 600);
  assert.equal(result.reports.lane.stale_after_seconds, 120);
  assert.equal(result.work_complete, false);
  assert.equal(result.completion_authority, false);
});

for (const role of ['guardian', 'dispatcher', 'watchdog', 'lane']) {
  test(`stored healthy cannot conceal stale ${role} output even when its file was touched now`, () => {
    const data = fixture(), report = data.snapshots[role].data;
    const old = NOW - 601000;
    if (role === 'guardian') report.observed_at_ms = old;
    if (role === 'dispatcher') report.observed_at = old / 1000;
    if (role === 'watchdog') report.timestamp = new Date(old).toISOString();
    if (role === 'lane') report.heartbeat_at_ms = old;
    data.snapshots[role].mtimeMs = NOW;
    const result = assessObserverHealth(data);
    assert.equal(result.healthy, false);
    assert.ok(has(result, role, 'stale_report'));
  });
  test(`missing and malformed ${role} reports fail closed`, () => {
    for (const error of ['missing_report', 'malformed_report']) {
      const data = fixture(); data.snapshots[role] = { data: null, error };
      const result = assessObserverHealth(data);
      assert.equal(result.healthy, false);
      assert.ok(has(result, role, error));
    }
  });
  test(`fresh saved healthy status cannot conceal a dead or mismatched ${role} process`, () => {
    for (const mismatch of ['dead', 'module', 'uid']) {
      const data = fixture(), pid = { guardian: 1, dispatcher: 2, watchdog: 3, lane: 4 }[role];
      if (mismatch === 'dead') data.processes[pid].alive = false;
      if (mismatch === 'module') data.processes[pid].argv[2] = MOD + 'unrelated';
      if (mismatch === 'uid') data.processes[pid].uid = 2000;
      const result = assessObserverHealth(data);
      assert.equal(result.healthy, false);
      assert.ok(has(result, role, mismatch === 'dead' ? 'process_dead_or_unknown' : 'process_identity_mismatch'));
    }
  });
}

test('current report PID disagreement and kernel start-time fences reject PID reuse', () => {
  const data = fixture(); data.snapshots.lane.data.pid = 44;
  data.snapshots.guardian.data.owners[0].start_ticks = 'old-start';
  const result = assessObserverHealth(data);
  assert.equal(result.healthy, false);
  assert.ok(has(result, 'lane', 'reported_pid_mismatch'));
  assert.ok(has(result, 'watchdog', 'start_ticks_mismatch'));
});

test('malformed nested owner and PID data produces explicit warnings instead of throwing or claiming health', () => {
  const data = fixture(); Object.assign(data.snapshots.guardian.data, { owners: { find: 1 }, guardian_pid: { valueOf: 1, toString: 1 } });
  const result = assessObserverHealth(data);
  assert.equal(result.healthy, false);
  assert.ok(has(result, 'guardian', 'process_dead_or_unknown'));
  assert.ok(has(result, 'guardian', 'reported_owner_health_not_clear'));
});

test('module or manifest names appearing only as application arguments cannot impersonate the watchdog', () => {
  const data = fixture();
  data.processes[3].argv = ['/usr/bin/python3', 'other.py', '--evidence-path', MOD + 'supervisor_watchdog',
    '--repo-root', ROOT, '--manifest-path', data.manifestPath];
  assert.ok(has(assessObserverHealth(data), 'watchdog', 'process_identity_mismatch'));
  data.processes[3].argv = ['/usr/bin/python3', '-m', MOD + 'supervisor_watchdog', '--repo-root', ROOT,
    '--manifest-path', data.manifestPath, '--manifest-path', '/different/manifest.json'];
  assert.ok(has(assessObserverHealth(data), 'watchdog', 'process_identity_mismatch'));
});

test('relative identity paths resolve only against the actual process cwd, with missing cwd failing closed', () => {
  for (const cwd of ['/unrelated/project', undefined]) {
    const data = fixture(); data.processes[3].cwd = cwd;
    data.processes[3].argv = ['/usr/bin/python3', '-m', MOD + 'supervisor_watchdog', '--repo-root', '.',
      '--manifest-path', 'data/watchdog/bundle_lanes.json'];
    const result = assessObserverHealth(data);
    assert.equal(result.healthy, false);
    assert.ok(has(result, 'watchdog', 'process_identity_mismatch'));
  }
  const data = fixture(); data.processes[3].cwd = ROOT;
  data.processes[3].argv = ['/usr/bin/python3', '-m', MOD + 'supervisor_watchdog', '--repo-root', '.',
    '--manifest-path', 'data/watchdog/bundle_lanes.json'];
  assert.equal(assessObserverHealth(data).healthy, true);
});

test('a guardian owners-list PID cannot silently disagree with every current owner identity', () => {
  const data = fixture(); data.snapshots.guardian.data.owners = [{ pid: 99, start_ticks: '999' }];
  const result = assessObserverHealth(data);
  assert.equal(result.healthy, false);
  assert.ok(has(result, 'watchdog', 'guardian_owner_pid_mismatch'));
});

test('accepted string PIDs cannot bypass available guardian or dispatcher kernel start-time fences', () => {
  for (const role of ['guardian', 'dispatcher']) {
    const data = fixture();
    if (role === 'guardian') data.snapshots.guardian.data.owners = [{ pid: '3', start_ticks: 'old-start' }];
    else data.snapshots.dispatcher.data.owner = { pid: '3', start_ticks: 'old-start' };
    const result = assessObserverHealth(data);
    assert.equal(result.healthy, false);
    assert.ok(has(result, 'watchdog', 'start_ticks_mismatch'));
  }
});

test('dispatcher relative manifest uses its actual configured root while relative repo root still uses actual cwd', () => {
  const data = fixture(); data.processes[2].cwd = '/unrelated/project';
  data.processes[2].argv = ['/usr/bin/python3', '-m', MOD + 'repair_dispatcher', '--repo-root', ROOT,
    '--manifest-path', 'data/watchdog/bundle_lanes.json'];
  assert.equal(assessObserverHealth(data).healthy, true);
  data.processes[2].argv[4] = '.';
  const result = assessObserverHealth(data);
  assert.equal(result.healthy, false);
  assert.ok(has(result, 'dispatcher', 'process_identity_mismatch'));
});

test('freshness bounds follow actual current process poll/monitor configuration', () => {
  const data = fixture();
  data.processes[1].argv.push('--poll-seconds', '10');
  data.processes[2].argv.push('--interval', '15', '--report-seconds', '300', '--heartbeat-seconds', '90');
  data.processes[3].argv.push('--check-interval', '60');
  const result = assessObserverHealth(data);
  assert.equal(result.reports.guardian.stale_after_seconds, 30);
  assert.equal(result.reports.dispatcher.stale_after_seconds, 45);
  assert.equal(result.reports.watchdog.normal_poll_seconds, 60);
  assert.equal(result.reports.watchdog.stale_after_seconds, 300);
  assert.equal(result.reports.lane.stale_after_seconds, 90);
});

test('overdue normal poll and future report timestamps warn before a false healthy projection', () => {
  const data = fixture(); data.snapshots.dispatcher.data.observed_at = (NOW - 70000) / 1000;
  const overdue = assessObserverHealth(data);
  assert.ok(has(overdue, 'dispatcher', 'report_poll_overdue'));
  assert.equal(overdue.healthy, false);
  data.snapshots.dispatcher.data.observed_at = (NOW + 60000) / 1000;
  assert.ok(has(assessObserverHealth(data), 'dispatcher', 'future_report_timestamp'));
});

test('an intentional stopped lane exposes its old age and dead PID without inventing a monitoring stall', () => {
  const data = fixture(); Object.assign(data.snapshots.lane.data, { state: 'stopped', terminal_reason: 'resume_stopped', heartbeat_at_ms: NOW - 86400000 });
  data.processes[4].alive = false;
  const result = assessObserverHealth(data);
  assert.equal(result.healthy, true);
  assert.equal(result.state, 'paused');
  assert.equal(result.reports.lane.process.expected_running, false);
  assert.equal(result.reports.lane.process.alive, false);
  assert.equal(result.reports.lane.age_seconds, 86400);
  assert.deepEqual(result.warnings, []);
});

test('old terminal status cannot mark a contradictory live current lane owner as intentionally paused', () => {
  const data = fixture(); Object.assign(data.snapshots.lane.data, { state: 'stopped', terminal_reason: 'resume_stopped' });
  data.pids.lane = 44; data.processes[44] = { ...data.processes[4], pid: 44, start_ticks: '144' };
  delete data.processes[4];
  const result = assessObserverHealth(data);
  assert.equal(result.healthy, false);
  assert.ok(has(result, 'lane', 'reported_pid_mismatch'));
  assert.ok(has(result, 'lane', 'terminal_status_with_live_owner'));
});

test('terminal status also warns when its same recorded lane PID is still a verified live owner', () => {
  const data = fixture(); Object.assign(data.snapshots.lane.data, { state: 'stopped', terminal_reason: 'resume_stopped' });
  const result = assessObserverHealth(data);
  assert.equal(result.healthy, false);
  assert.ok(has(result, 'lane', 'terminal_status_with_live_owner'));
});

test('an explicit operator hold remains informational while stale monitoring still warns', () => {
  const data = fixture(); data.snapshots.dispatcher.data.held = true;
  assert.equal(assessObserverHealth(data).state, 'paused');
  data.snapshots.dispatcher.data.observed_at = (NOW - 500000) / 1000;
  const result = assessObserverHealth(data);
  assert.equal(result.healthy, false);
  assert.ok(has(result, 'dispatcher', 'stale_report'));
});

function heldAggregateFixture() {
  const data = fixture();
  data.snapshots.dispatcher.data.held = true;
  Object.assign(data.snapshots.lane.data, { state: 'stopped', terminal_reason: 'resume_stopped' });
  data.processes[4].alive = false;
  data.snapshots.watchdog.data.status.state = 'stopped';
  return data;
}

test('a fresh live watchdog aggregating an explicitly held stopped lane is informational', () => {
  const result = assessObserverHealth(heldAggregateFixture());
  assert.equal(result.healthy, true);
  assert.equal(result.state, 'paused');
  assert.deepEqual(result.warnings, []);
  assert.ok(result.notices.some(item => item.component === 'watchdog' && item.code === 'operator_held_aggregate'));
  assert.equal(result.reports.watchdog.process.expected_running, true);
  assert.equal(result.reports.watchdog.process.identity_verified, true);
  assert.equal(result.work_complete, false);
  assert.equal(result.completion_authority, false);
});

test('an explicitly held paused lane corroborates a paused watchdog aggregate', () => {
  const data = heldAggregateFixture();
  Object.assign(data.snapshots.lane.data, { state: 'paused', phase: 'operator_hold', terminal_reason: '' });
  data.snapshots.watchdog.data.status.state = 'paused';
  const result = assessObserverHealth(data);
  assert.equal(result.healthy, true);
  assert.equal(result.state, 'paused');
  assert.ok(result.notices.some(item => item.component === 'watchdog' && item.code === 'operator_held_aggregate'));
});

test('a nonhealthy aggregate without both canonical lane intent and explicit hold still warns', () => {
  for (const missing of ['hold', 'lane-intent']) {
    const data = heldAggregateFixture();
    if (missing === 'hold') data.snapshots.dispatcher.data.held = false;
    else Object.assign(data.snapshots.lane.data, { state: 'stopped', terminal_reason: 'unexpected_exit' });
    const result = assessObserverHealth(data);
    assert.equal(result.healthy, false);
    assert.ok(has(result, 'watchdog', 'reported_state_not_healthy'));
  }
  for (const state of ['blocked', 'waiting', 'failed']) {
    for (const data of [fixture(), heldAggregateFixture()]) {
      data.snapshots.watchdog.data.status.state = state;
      const result = assessObserverHealth(data);
      assert.equal(result.healthy, false);
      assert.ok(has(result, 'watchdog', 'reported_state_not_healthy'));
    }
  }
});

test('an intentionally held aggregate retains stale live-daemon warnings', () => {
  for (const role of ['guardian', 'dispatcher', 'watchdog']) {
    const data = heldAggregateFixture(), old = NOW - 601000;
    if (role === 'guardian') data.snapshots.guardian.data.observed_at_ms = old;
    if (role === 'dispatcher') data.snapshots.dispatcher.data.observed_at = old / 1000;
    if (role === 'watchdog') data.snapshots.watchdog.data.timestamp = new Date(old).toISOString();
    const result = assessObserverHealth(data);
    assert.equal(result.healthy, false);
    assert.ok(has(result, role, 'stale_report'));
  }
});

test('an intentionally held aggregate retains watchdog death, identity and start-time fence warnings', () => {
  for (const fault of ['dead', 'identity', 'pid', 'start']) {
    const data = heldAggregateFixture();
    if (fault === 'dead') data.processes[3].alive = false;
    if (fault === 'identity') data.processes[3].argv[2] = MOD + 'unrelated';
    if (fault === 'pid') data.snapshots.watchdog.data.status.pid = 99;
    if (fault === 'start') data.snapshots.guardian.data.owners[0].start_ticks = 'old-start';
    const result = assessObserverHealth(data);
    const expected = { dead: 'process_dead_or_unknown', identity: 'process_identity_mismatch', pid: 'reported_pid_mismatch', start: 'start_ticks_mismatch' }[fault];
    assert.equal(result.healthy, false);
    assert.ok(has(result, 'watchdog', expected));
  }
});

test('an intentional guardian stop does not demand forever-fresh exited watchdog/lane heartbeats', () => {
  const data = fixture(); Object.assign(data.snapshots.guardian.data, { hold_markers: ['OPERATOR_STOP'], owner_alive: false, owners: [], report_health: 'stale' });
  data.snapshots.dispatcher.data.held = true;
  data.processes[3].alive = data.processes[4].alive = false;
  delete data.processes[3].start_ticks; delete data.processes[4].start_ticks;
  data.snapshots.watchdog.data.timestamp = new Date(NOW - 86400000).toISOString();
  Object.assign(data.snapshots.lane.data, { state: 'stopped', terminal_reason: 'resume_stopped', heartbeat_at_ms: NOW - 86400000 });
  assert.equal(assessObserverHealth(data).healthy, true);
});

test('health projection excludes private command arguments and never produces acceptance authority', () => {
  const data = fixture(); data.processes[2].argv.push('--private-setting', 'DO_NOT_EXPOSE_THIS_VALUE');
  const result = assessObserverHealth(data);
  assert.equal(JSON.stringify(result).includes('DO_NOT_EXPOSE_THIS_VALUE'), false);
  assert.equal(result.observation_only, true);
  assert.equal(result.work_complete, false);
  assert.equal(result.completion_authority, false);
});

test('real proc-file probe checks UID/state and rejects a zombie without exposing argv in public projection', t => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'vdg-observer-proc-'));
  t.after(() => fs.rmSync(directory, { recursive: true, force: true }));
  const processDir = path.join(directory, '123'); fs.mkdirSync(processDir);
  const fields = ['S', ...Array(18).fill('0'), '98765'];
  fs.writeFileSync(path.join(processDir, 'stat'), `123 (python worker) ${fields.join(' ')}\n`);
  fs.writeFileSync(path.join(processDir, 'cmdline'), '/usr/bin/python3\0-m\0example\0');
  fs.symlinkSync(directory, path.join(processDir, 'cwd'), 'dir');
  const result = probeProcess(123, directory);
  assert.equal(result.alive, true); assert.equal(result.uid, process.getuid()); assert.equal(result.start_ticks, '98765');
  assert.equal(result.cwd, fs.realpathSync(directory));
  fields[0] = 'Z'; fs.writeFileSync(path.join(processDir, 'stat'), `123 (python worker) ${fields.join(' ')}\n`);
  assert.equal(probeProcess(123, directory).alive, false);
  assert.equal(probeProcess(124, directory).alive, false);
});
