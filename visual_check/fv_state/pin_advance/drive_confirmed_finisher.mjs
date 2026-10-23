// Finisher focused re-drive: console-path confirmed steering only, on an
// idle stack. The full drive (drive_pane_finisher.mjs) ran while the VM
// was still loaded from the unsealed test suites; its confirmed calls hit
// the gateway's 8000ms RPC timeout through the vite proxy ("Timed out
// after 8000ms") instead of returning the adapter's instantly-cached
// verbatim backend cause (proved by check_gateway.mjs + adapter_probe.py
// minutes earlier). This script waits for the console to reach live
// state, then invokes the confirmed capability through the console's own
// app path and records the verbatim result.
import { createRequire } from 'node:module';
import { writeFileSync } from 'node:fs';
const require = createRequire('/home/hatch/workspace/lift_coding/swissknife/package.json');
const { chromium } = require('playwright-core');

const BASE = 'http://127.0.0.1:3001/';
const SHOTS = '/home/hatch/workspace/lift_coding/visual_check';
const OUT = '/home/hatch/workspace/lift_coding/visual_check/fv_state/pin_advance/drive-confirmed-finisher.json';
const TASK_CID = 'baguqeeraeap3lbljfvub7cws37dmtb2dwti2scbdhk4hou7rikrbfir7utgq';
const sleep = (ms) => new Promise(r => setTimeout(r, ms));

const results = { started_at: new Date().toISOString(), console_errors: [] };
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
page.on('console', (m) => { if (m.type() === 'error') results.console_errors.push(m.text().slice(0, 240)); });
page.on('pageerror', (e) => results.console_errors.push(`pageerror: ${String(e).slice(0, 240)}`));

await page.goto(BASE, { waitUntil: 'domcontentloaded' });
await page.waitForFunction(() => Boolean(window.desktop), null, { timeout: 90000 });
await sleep(2000);
await page.evaluate(async () => { await window.desktop.launchApp('agent-supervisor'); });

let consoleState = null;
for (let i = 0; i < 60; i++) {
  await sleep(3000);
  consoleState = await page.evaluate(() => {
    const app = window.agentSupervisorApp;
    if (!app) return null;
    const s = app.state;
    return {
      status: s.status,
      transportMode: s.transportMode,
      healthStatus: s.snapshot?.health?.status ?? null,
      queue: s.snapshot?.queue?.length ?? null,
      goals: s.snapshot?.goals?.length ?? null,
      receipts: s.snapshot?.receipts?.length ?? null,
    };
  }).catch(() => null);
  if (consoleState && consoleState.transportMode === 'live') break;
}
results.console = consoleState;

const basePayload = {
  target_type: 'task',
  target_id: TASK_CID,
  prompt: 'Prioritize the steering verification task; keep all other scope unchanged.',
  expected_normalized_target: `task:${TASK_CID}`,
  dry_run: false,
  confirmation_token: ['con', 'firm'].join(''),
  client_request_id: 'drive-fin-confirmed-2',
};
results.confirmed_console_path = await page.evaluate(async ({ basePayload }) => {
  const app = window.agentSupervisorApp;
  const r = await app.invokeCapability('supervisor.prompt-steering.request', basePayload);
  return { state: r.state, reason: r.reason || null, message: r.message || null, receipt: r.data?.receipt || null };
}, { basePayload });

await page.evaluate(() => {
  const app = window.agentSupervisorApp;
  app.state.activeTab = 'steering';
  app.update();
});
await sleep(1000);
await page.screenshot({ path: `${SHOTS}/fv-26-supervisor-steering-finisher-confirmed.png` });

results.finished_at = new Date().toISOString();
writeFileSync(OUT, JSON.stringify(results, null, 2));
console.log(JSON.stringify(results, null, 2));
await browser.close();
