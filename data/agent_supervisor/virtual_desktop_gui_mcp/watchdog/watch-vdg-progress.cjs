'use strict';
// Read-only operational observations; never completion or acceptance authority.
const fs = require('node:fs');
const path = require('node:path');
const { observeDaemonHealth } = require('./vdg-observer-health.cjs');
const root = '/home/barberb/lift_coding';
const sourceRoot = path.join(root, 'swissknife');
const evidenceRoot = path.join(sourceRoot, 'test-results/virtual-desktop-ipfs-mcp-orb');
const watchdog = path.join(root, 'data/agent_supervisor/virtual_desktop_gui_mcp/watchdog');
for (const line of fs.readFileSync(path.join(watchdog, 'backends/client.env'), 'utf8').split('\n')) {
 if (!line || line.startsWith('#')) continue;
 const at = line.indexOf('='); process.env[line.slice(0, at)] = line.slice(at + 1);
}
const { FAMILIES } = require(path.join(sourceRoot, 'scripts/vdg-evidence.cjs'));
const { captureInputFingerprint } = require(path.join(sourceRoot, 'scripts/vdg-capture-fingerprint.cjs'));
const { checkCapture } = require(path.join(sourceRoot, 'scripts/check-vdg-capture.cjs'));
const { inspectInventory } = require(path.join(sourceRoot, 'scripts/vdg-inventory-contract.cjs'));
function read(filename) { try { return JSON.parse(fs.readFileSync(filename, 'utf8')); } catch { return null; } }
const matrix = read(path.join(evidenceRoot, 'control-tool-matrix.json'));
const progress = [];
for (const [family, definition] of Object.entries(FAMILIES)) {
 for (const transport of ['http', 'libp2p']) {
  const fingerprint = captureInputFingerprint(family, transport, { sourceRoot, evidenceRoot, definition });
  const checkpoint = path.join(evidenceRoot, 'vdg/checkpoints', `${definition.target}-${transport}-${fingerprint}.json`);
  const stored = read(checkpoint);
  let complete = false;
  try { complete = checkCapture(family, transport, { sourceRoot, evidenceRoot }).capture_complete === true; } catch {}
  if (!stored && !complete) continue;
  const payload = stored?.payload || {};
  const rows = payload.rows || [], observations = payload.observations || [];
  const failures = rows.filter(row => row.failure_reasons?.length || row.pageerrors?.length);
  progress.push({ family, transport, acquisition_complete:complete,
   rows:rows.length, expected:matrix?.rows?.filter(row => row.family === family).length,
   observations:observations.length, owner_failure_count:observations.filter(item => item.owner_result_verified !== true).length,
   owner_failures:observations.filter(item => item.owner_result_verified !== true).slice(0, 5),
   failure_count:failures.length, failures:failures.slice(0, 5).map(row => ({ app_id:row.app_id, selector:row.selector,
    failure_reasons:row.failure_reasons, pageerrors:row.pageerrors })),
   last_app:rows.at(-1)?.app_id,
   pageerrors:payload.pageerrors || [], updated_at:stored?.observed_at });
 }
}
const state = read(path.join(watchdog, 'lanes/vdg-planning/vdg_planning_status.json'));
const dispatcher = read(path.join(watchdog, 'repair-dispatcher/status.json'));
let health;
try { health = observeDaemonHealth({ repoRoot:root, watchdogDir:watchdog }); }
catch { health = { schema:'swissknife.vdg-observer-health.v1', healthy:false, state:'attention_required',
 warnings:[{ component:'observer', code:'health_observation_failed' }], observation_only:true,
 work_complete:false, completion_authority:false }; }
const report = { observed_at:new Date().toISOString(),
 inventory:inspectInventory({ sourceRoot, evidenceRoot }),
 lane:{pid:state?.pid, state:state?.state, phase:state?.phase, task:state?.active_task_id, heartbeat:state?.heartbeat_at_ms},
 dispatcher:{action:dispatcher?.action, held:dispatcher?.held, incidents:dispatcher?.incidents}, health, progress,
 work_complete:false, completion_authority:false };
if (process.argv.includes('--brief')) {
 console.log(JSON.stringify({ observed_at:report.observed_at,
  inventory_current:report.inventory.current, lane:report.lane,
  dispatcher:report.dispatcher, health:report.health,
  completed_transport_cells:progress.filter(cell => cell.acquisition_complete).length,
  active:progress.filter(cell => !cell.acquisition_complete).map(cell => ({
   family:cell.family, transport:cell.transport, rows:cell.rows, expected:cell.expected,
   last_app:cell.last_app, observations:cell.observations, updated_at:cell.updated_at,
  })),
  failures:progress.filter(cell => cell.failure_count || cell.owner_failure_count || cell.pageerrors.length),
  work_complete:false, completion_authority:false }));
} else console.log(JSON.stringify(report));
