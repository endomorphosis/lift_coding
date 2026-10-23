// Follow-up to drive_console.mjs: re-run the confirmed steering case
// through the page's own gateway + console path now that the route is
// warm, capturing the backend's verbatim boundary message in-browser.
import { createRequire } from 'node:module';
import { writeFileSync } from 'node:fs';
const require = createRequire('/home/hatch/workspace/lift_coding/swissknife/package.json');
const { chromium } = require('playwright-core');

const TASK_CID = 'baguqeeraeap3lbljfvub7cws37dmtb2dwti2scbdhk4hou7rikrbfir7utgq';
const sleep = (ms) => new Promise(r => setTimeout(r, ms));
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
await page.goto('http://127.0.0.1:3001/', { waitUntil: 'domcontentloaded' });
await page.waitForFunction(() => Boolean(window.desktop), null, { timeout: 90000 });
await sleep(1500);
await page.evaluate(async () => { await window.desktop.launchApp('agent-supervisor'); });
await sleep(6000);

const basePayload = {
  target_type: 'task',
  target_id: TASK_CID,
  prompt: 'Prioritize the steering verification task; keep all other scope unchanged.',
  expected_normalized_target: `task:${TASK_CID}`,
  client_request_id: 'drive-confirmed-2',
};
const out = await page.evaluate(async ({ basePayload }) => {
  const invocation = (payload) => ({
    capability_id: 'supervisor.prompt-steering.request',
    method: 'agent_supervisor.prompt_steering.request',
    owner: 'ipfs_accelerate_py',
    access: 'governed-write',
    policy_class: 'confirm',
    correlation_id: 'drive-steering-route-2',
    payload,
  });
  const confirmedPayload = {
    ...basePayload,
    dry_run: false,
    confirmation_token: `confirm-agent-supervisor:task:${basePayload.target_id}:drive-confirmed-2`,
  };
  const viaGateway = await window.agentSupervisorGateway.invoke(invocation(confirmedPayload));
  const viaConsole = await window.agentSupervisorApp.invokeCapability('supervisor.prompt-steering.request', confirmedPayload);
  const pick = (r) => ({ state: r.state, reason: r.reason || null, message: r.message || null });
  return { viaGateway: pick(viaGateway), viaConsole: pick(viaConsole) };
}, { basePayload });

console.log(JSON.stringify(out, null, 2));
writeFileSync('/home/hatch/workspace/lift_coding/visual_check/fv_state/steering_route/drive-confirmed-results.json', JSON.stringify(out, null, 2));
await browser.close();
