// Finisher drive: console steering-pane drive on the live stack at
// the NEW datasets pin. Mirrors steering_route/drive_console.mjs (same
// payloads, same target CID) with pin_advance evidence names:
//   fv-20 steering pane live state, fv-21 steering pane after the
//   console-path confirmed attempt, fv-22 console health tab.
// Cases: dry-run -> gateway typed capability_unavailable (console local
// preview engages); unconfirmed -> denied/confirmation_required;
// confirmed -> dispatched through the route; outcome recorded verbatim.
import { createRequire } from 'node:module';
import { writeFileSync } from 'node:fs';
const require = createRequire('/home/hatch/workspace/lift_coding/swissknife/package.json');
const { chromium } = require('playwright-core');

const BASE = 'http://127.0.0.1:3001/';
const SHOTS = '/home/hatch/workspace/lift_coding/visual_check';
const OUT = '/home/hatch/workspace/lift_coding/visual_check/fv_state/pin_advance/drive-results-finisher.json';
const TASK_CID = 'baguqeeraeap3lbljfvub7cws37dmtb2dwti2scbdhk4hou7rikrbfir7utgq'; // seed-chain task CID (see steering_route/seed_profile_g.out)
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
for (let i = 0; i < 40; i++) {
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
      gatewayInstalled: Boolean(window.agentSupervisorGateway),
    };
  }).catch(() => null);
  if (consoleState && consoleState.transportMode !== 'fallback' && consoleState.status !== 'loading') break;
}
results.console = consoleState;

await page.evaluate(() => {
  const app = window.agentSupervisorApp;
  app.state.activeTab = 'steering';
  app.update();
});
await sleep(1200);
await page.screenshot({ path: `${SHOTS}/fv-23-supervisor-steering-finisher.png` });
results.steering_pane_text = await page.evaluate(() => {
  const win = document.querySelector('.window.focused') || document.body;
  return (win.innerText || '').slice(0, 1200);
});

const basePayload = {
  target_type: 'task',
  target_id: TASK_CID,
  prompt: 'Prioritize the steering verification task; keep all other scope unchanged.',
  expected_normalized_target: `task:${TASK_CID}`,
  client_request_id: 'drive-finisher-1',
};

results.gateway = await page.evaluate(async ({ basePayload }) => {
  const invocation = (payload) => ({
    capability_id: 'supervisor.prompt-steering.request',
    method: 'agent_supervisor.prompt_steering.request',
    owner: 'ipfs_accelerate_py',
    access: 'governed-write',
    policy_class: 'confirm',
    correlation_id: 'drive-finisher',
    payload,
  });
  const gateway = window.agentSupervisorGateway;
  const dry = await gateway.invoke(invocation({ ...basePayload, dry_run: true }));
  const unconfirmed = await gateway.invoke(invocation({ ...basePayload, dry_run: false }));
  const confirmed = await gateway.invoke(invocation({
    ...basePayload,
    dry_run: false,
    confirmation_token: `confirm-agent-supervisor:task:${basePayload.target_id}:drive-finisher-1`,
  }));
  const pick = (r) => ({ state: r.state, reason: r.reason || null, message: r.message || null, required_confirmation: r.required_confirmation || false, receipt: r.data?.receipt || null });
  return { dry: pick(dry), unconfirmed: pick(unconfirmed), confirmed: pick(confirmed) };
}, { basePayload });

results.console_path = await page.evaluate(async ({ basePayload }) => {
  const app = window.agentSupervisorApp;
  const dry = await app.invokeCapability('supervisor.prompt-steering.request', { ...basePayload, dry_run: true, client_request_id: 'drive-fin-dry' });
  const confirmed = await app.invokeCapability('supervisor.prompt-steering.request', {
    ...basePayload,
    dry_run: false,
    confirmation_token: `confirm-agent-supervisor:task:${basePayload.target_id}:drive-fin-confirmed`,
    client_request_id: 'drive-fin-confirmed',
  });
  return {
    dry: { state: dry.state, accepted: dry.data?.accepted ?? null, dry_run: dry.data?.dry_run ?? null, receipt_id: dry.data?.receipt?.receipt_id || null },
    confirmed: { state: confirmed.state, reason: confirmed.reason || null, message: confirmed.message || null },
  };
}, { basePayload });

await sleep(1000);
await page.screenshot({ path: `${SHOTS}/fv-24-supervisor-steering-finisher-after-confirmed.png` });
results.steering_pane_after_text = await page.evaluate(() => {
  const win = document.querySelector('.window.focused') || document.body;
  return (win.innerText || '').slice(0, 1600);
});

await page.evaluate(() => {
  const app = window.agentSupervisorApp;
  app.state.activeTab = 'health';
  app.update();
});
await sleep(800);
await page.screenshot({ path: `${SHOTS}/fv-25-supervisor-console-finisher.png` });

results.finished_at = new Date().toISOString();
writeFileSync(OUT, JSON.stringify(results, null, 2));
console.log(JSON.stringify(results, null, 2));
await browser.close();
