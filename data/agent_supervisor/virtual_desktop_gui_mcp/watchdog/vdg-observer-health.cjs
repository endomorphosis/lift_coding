'use strict';
// Read-only health projection. It never starts, signals or repairs a process.
const fs = require('node:fs');
const path = require('node:path');
const MODULE = 'ipfs_accelerate_py.agent_supervisor.rescue.';
const SCHEMAS = {
  guardian: 'ipfs_accelerate_py.agent_supervisor.watchdog-guardian@1',
  dispatcher: 'ipfs_accelerate_py.agent_supervisor.repair-dispatcher@1',
  lane: 'ipfs_accelerate_py/agent-supervisor/lifecycle-status@1',
};
const object = value => value && typeof value === 'object' && !Array.isArray(value);
const pidValue = value => (typeof value === 'number' || typeof value === 'string' && /^[1-9]\d*$/.test(value))
  && Number.isSafeInteger(Number(value)) && Number(value) > 0 ? Number(value) : null;
function option(argv, name) {
  const values = [];
  for (let index = 0; index < argv.length; index++) {
    if (argv[index] === name) values.push(argv[index + 1]);
    else if (argv[index].startsWith(`${name}=`)) values.push(argv[index].slice(name.length + 1));
  }
  return values.length === 1 ? values[0] : undefined;
}
function pythonModule(argv) {
  if (!/^(?:python|pypy)(?:\d+(?:\.\d+)*)?$/.test(path.basename(argv[0] || ''))) return '';
  for (let index = 1; index < argv.length; index++) {
    if (argv[index] === '-m') return argv[index + 1] || '';
    if (['-W', '-X', '--check-hash-based-pycs'].includes(argv[index])) { index++; continue; }
    if (/^-[uBIsSEqv]+$/.test(argv[index]) || /^-(?:W|X).+/.test(argv[index])) continue;
    // A script/command or unknown interpreter argument ends this identity.
    return '';
  }
  return '';
}
function readSnapshot(filename) {
  try {
    const data = JSON.parse(fs.readFileSync(filename, 'utf8'));
    return { data: object(data) ? data : null, mtimeMs: fs.statSync(filename).mtimeMs,
      error: object(data) ? '' : 'malformed_report' };
  } catch (error) { return { data: null, error: error.code === 'ENOENT' ? 'missing_report' : 'malformed_report' }; }
}
function readPid(filename) {
  try { return pidValue(fs.readFileSync(filename, 'utf8').trim()); } catch { return null; }
}
function probeProcess(pid, procRoot = '/proc') {
  if (!pidValue(pid)) return { pid, alive: false, error: 'pid_missing' };
  const directory = path.join(procRoot, String(pid));
  try {
    const identity = () => {
      const value = fs.readFileSync(path.join(directory, 'stat'), 'utf8');
      const fields = value.slice(value.lastIndexOf(')') + 2).trim().split(/\s+/);
      return { state: fields[0], start_ticks: fields[19] };
    };
    const before = identity();
    const argv = fs.readFileSync(path.join(directory, 'cmdline'), 'utf8').split('\0').filter(Boolean);
    const uid = fs.statSync(directory).uid;
    let cwd = null;
    try { cwd = fs.realpathSync(path.join(directory, 'cwd')); } catch { /* Relative identity paths remain unverifiable. */ }
    const after = identity();
    return { pid, alive: !['Z', 'X'].includes(after.state) && before.start_ticks === after.start_ticks,
      ...after, uid, argv, cwd, error: before.start_ticks === after.start_ticks ? '' : 'pid_changed_during_probe' };
  } catch (error) { return { pid, alive: false, error: error.code === 'ENOENT' || error.code === 'ESRCH' ? 'process_dead' : 'process_unreadable' }; }
}
function stamp(value) {
  if (typeof value === 'number' && Number.isFinite(value) && value > 0) return value > 1e11 ? value : value * 1000;
  if (typeof value === 'string') { const parsed = Date.parse(value); if (Number.isFinite(parsed)) return parsed; }
  return null;
}
function configuredNumber(process, flag, fallback) {
  const raw = option(process?.argv || [], flag);
  const number = Number(raw);
  return raw !== undefined && Number.isFinite(number) && number > 0 ? number : fallback;
}
function assessObserverHealth({ nowMs, repoRoot, manifestPath, laneStatusPath, snapshots, pids = {}, processes = {}, uid = process.getuid?.() }) {
  const warnings = [];
  const notices = [];
  const warn = (component, code) => warnings.push({ component, code });
  const guardian = snapshots.guardian?.data || {};
  const dispatcher = snapshots.dispatcher?.data || {};
  const watchdog = snapshots.watchdog?.data || {};
  const lane = snapshots.lane?.data || {};
  const ownerHeld = Array.isArray(guardian.hold_markers) && guardian.hold_markers.length > 0;
  const laneStopped = lane.state === 'stopped' && lane.terminal_reason === 'resume_stopped';
  const laneHeld = lane.state === 'paused' && (lane.phase === 'operator_hold' || lane.terminal_reason === 'operator_hold');
  // The live watchdog can aggregate an intentionally stopped lane. Keep its
  // process/freshness requirements; only the corroborated aggregate is paused.
  const heldAggregate = dispatcher.held === true && (laneStopped || laneHeld)
    && ['stopped', 'paused'].includes(watchdog.status?.state);
  const expectedRunning = { guardian: true, dispatcher: true, watchdog: !ownerHeld, lane: !ownerHeld && !laneStopped && !laneHeld };
  if (laneStopped || laneHeld) notices.push({ component: 'lane', code: 'intentional_stop_or_hold' });
  if (ownerHeld || dispatcher.held === true) notices.push({ component: 'dispatcher', code: 'operator_hold_observed' });
  const currentPids = {
    guardian: pidValue(guardian.guardian_pid), dispatcher: pidValue(pids.dispatcher),
    watchdog: pidValue(pids.watchdog) || pidValue(watchdog.status?.pid),
    lane: pidValue(pids.lane) || pidValue(lane.pid),
  };
  const identities = {};
  for (const [role, module] of Object.entries({ guardian: 'watchdog_guardian', dispatcher: 'repair_dispatcher', watchdog: 'supervisor_watchdog', lane: 'lane_resume' })) {
    const pid = currentPids[role], observed = processes[pid] || {};
    const argv = observed.argv || [];
    const matchesPath = (flag, expected) => {
      const actual = option(argv, flag);
      if (typeof actual !== 'string') return false;
      if (path.isAbsolute(actual)) return path.resolve(actual) === path.resolve(expected);
      if (role === 'dispatcher' && flag === '--manifest-path') {
        const configuredRoot = option(argv, '--repo-root');
        const actualRoot = typeof configuredRoot !== 'string' ? null : path.isAbsolute(configuredRoot) ? path.resolve(configuredRoot)
          : typeof observed.cwd === 'string' && path.isAbsolute(observed.cwd) ? path.resolve(observed.cwd, configuredRoot) : null;
        return actualRoot !== null && path.resolve(actualRoot, actual) === path.resolve(expected);
      }
      return typeof observed.cwd === 'string' && path.isAbsolute(observed.cwd)
        && path.resolve(observed.cwd, actual) === path.resolve(expected);
    };
    const identity = observed.alive === true && observed.uid === uid && observed.pid === pid
      && pythonModule(argv) === MODULE + module && matchesPath('--repo-root', repoRoot)
      && (role === 'lane' ? matchesPath('--status-path', laneStatusPath) && option(argv, '--bundle-key') === 'vdg-planning'
        : matchesPath('--manifest-path', manifestPath));
    identities[role] = { pid, alive: observed.alive === true, identity_verified: identity, expected_running: expectedRunning[role],
      start_ticks: observed.start_ticks || null };
    if (!identity && expectedRunning[role]) warn(role, observed.alive === true ? 'process_identity_mismatch' : 'process_dead_or_unknown');
  }
  const ownerFence = Array.isArray(guardian.owners) ? guardian.owners.find(item => pidValue(item?.pid) === currentPids.watchdog) : undefined;
  if (Array.isArray(guardian.owners) && guardian.owners.some(item => !pidValue(item?.pid) || Number(item.pid) !== currentPids.watchdog)) {
    warn('watchdog', 'guardian_owner_pid_mismatch');
  }
  if (expectedRunning.watchdog && ownerFence?.start_ticks !== undefined && String(ownerFence.start_ticks) !== String(identities.watchdog.start_ticks)) warn('watchdog', 'start_ticks_mismatch');
  const dispatcherFence = dispatcher.owner;
  if (expectedRunning.watchdog && pidValue(dispatcherFence?.pid) === currentPids.watchdog && dispatcherFence.start_ticks !== undefined
      && String(dispatcherFence.start_ticks) !== String(identities.watchdog.start_ticks)) warn('watchdog', 'start_ticks_mismatch');
  for (const [role, declared] of [['watchdog', watchdog.status?.pid], ['watchdog', guardian.owner_pid], ['watchdog', dispatcher.owner?.pid], ['lane', lane.pid]]) {
    if ((expectedRunning[role] || identities[role].alive) && (!pidValue(declared) || Number(declared) !== currentPids[role])) warn(role, 'reported_pid_mismatch');
  }
  if (laneStopped && identities.lane.alive && identities.lane.identity_verified) warn('lane', 'terminal_status_with_live_owner');
  const guardianPoll = configuredNumber(processes[currentPids.guardian], '--poll-seconds', 30);
  const dispatcherPoll = configuredNumber(processes[currentPids.dispatcher], '--interval', 30);
  const watchdogPoll = configuredNumber(processes[currentPids.watchdog], '--check-interval', 120);
  const reportBound = Math.min(600, configuredNumber(processes[currentPids.dispatcher], '--report-seconds', 600));
  const heartbeatBound = configuredNumber(processes[currentPids.dispatcher], '--heartbeat-seconds', 120);
  const settings = {
    guardian: { poll: guardianPoll, stale: guardianPoll * 3, value: guardian.observed_at_ms },
    dispatcher: { poll: dispatcherPoll, stale: dispatcherPoll * 3, value: dispatcher.observed_at },
    watchdog: { poll: watchdogPoll, stale: reportBound, value: watchdog.timestamp },
    lane: { poll: 5, stale: heartbeatBound, value: lane.heartbeat_at_ms },
  };
  const reports = {};
  for (const [role, config] of Object.entries(settings)) {
    const snapshot = snapshots[role] || {}, data = snapshot.data;
    const timestamp = stamp(config.value);
    const validSchema = role === 'watchdog' ? data?.status?.schema === SCHEMAS.lane : data?.schema === SCHEMAS[role];
    if (snapshot.error || !object(data)) warn(role, snapshot.error || 'missing_report');
    else if (!validSchema || timestamp === null || !Number.isFinite(snapshot.mtimeMs)) warn(role, 'malformed_report');
    const age = timestamp === null || !Number.isFinite(snapshot.mtimeMs) ? null
      : Math.max((nowMs - timestamp) / 1000, (nowMs - snapshot.mtimeMs) / 1000);
    if (timestamp !== null && (timestamp > nowMs + 5000 || snapshot.mtimeMs > nowMs + 5000)) warn(role, 'future_report_timestamp');
    if (expectedRunning[role] && age !== null && age > config.stale) warn(role, 'stale_report');
    else if (expectedRunning[role] && age !== null && role !== 'lane' && age > 2 * config.poll + 5) warn(role, 'report_poll_overdue');
    reports[role] = { age_seconds: age === null ? null : Math.round(Math.max(0, age) * 1000) / 1000,
      normal_poll_seconds: config.poll, stale_after_seconds: config.stale,
      bound_source: role === 'guardian' || role === 'dispatcher' ? 'three_configured_poll_cycles_observer_only' : 'existing_monitor_stale_bound',
      process: identities[role], stored_state: data?.state || data?.status?.state || null, stored_action: data?.action || null };
  }
  if (!Array.isArray(guardian.owners) || guardian.owners.length > 1 || typeof guardian.owner_alive !== 'boolean'
      || (!ownerHeld && (guardian.owner_alive !== true || guardian.owners.length !== 1 || guardian.report_health !== 'fresh'))
      || !Array.isArray(guardian.errors) || guardian.errors.length) warn('guardian', 'reported_owner_health_not_clear');
  if (!Array.isArray(dispatcher.incidents) || dispatcher.incidents.length || dispatcher.owner_discovery_uncertain !== false
      || !Array.isArray(dispatcher.owner_discovery_errors) || dispatcher.owner_discovery_errors.length) warn('dispatcher', 'reported_incidents_or_uncertain_owner');
  if (!Array.isArray(guardian.hold_markers) || typeof dispatcher.held !== 'boolean') warn('guardian', 'malformed_hold_state');
  if (expectedRunning.watchdog && !['healthy', 'starting'].includes(watchdog.status?.state)) {
    if (heldAggregate) notices.push({ component: 'watchdog', code: 'operator_held_aggregate' });
    else warn('watchdog', 'reported_state_not_healthy');
  }
  if (expectedRunning.lane && !['healthy', 'starting'].includes(lane.state)) warn('lane', 'reported_state_not_healthy');
  return { schema: 'swissknife.vdg-observer-health.v1', observed_at: new Date(nowMs).toISOString(),
    healthy: warnings.length === 0, state: warnings.length ? 'attention_required' : notices.length ? 'paused' : 'healthy', reports,
    warnings: [...new Map(warnings.map(item => [JSON.stringify(item), item])).values()],
    notices,
    observation_only: true, work_complete: false, completion_authority: false };
}
function observeDaemonHealth({ repoRoot, watchdogDir, nowMs = Date.now() }) {
  const laneStatusPath = path.join(watchdogDir, 'lanes/vdg-planning/vdg_planning_status.json');
  const snapshots = Object.fromEntries(Object.entries({ guardian: 'watchdog-guardian-status.json', dispatcher: 'repair-dispatcher/status.json', watchdog: 'watchdog-report.json', lane: 'lanes/vdg-planning/vdg_planning_status.json' })
    .map(([role, relative]) => [role, readSnapshot(path.join(watchdogDir, relative))]));
  const pids = { watchdog: readPid(path.join(watchdogDir, 'watchdog.pid')),
    dispatcher: readPid(path.join(watchdogDir, 'repair-dispatcher/dispatcher.lock')),
    lane: readPid(path.join(watchdogDir, 'lanes/vdg-planning/vdg_planning_bundle_supervisor.pid')) };
  const processes = Object.fromEntries([...new Set([snapshots.guardian.data?.guardian_pid, pids.dispatcher, pids.watchdog, pids.lane,
    snapshots.watchdog.data?.status?.pid, snapshots.lane.data?.pid].map(pidValue).filter(Boolean))].map(pid => [pid, probeProcess(pid)]));
  return assessObserverHealth({ nowMs, repoRoot, manifestPath: path.join(watchdogDir, 'bundle_lanes.json'), laneStatusPath, snapshots, pids, processes });
}
module.exports = { assessObserverHealth, observeDaemonHealth, probeProcess };
