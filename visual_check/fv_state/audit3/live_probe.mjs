// Audit3 step 8: live verification of the interaction-coverage fixes on
// the real stack (vite :3001 + the three mediated adapters). Drives the
// supervisor console's full interaction set and the two repaired surfaces
// (datasets-browser, accelerate-panel) and records program state.
import { createRequire } from 'node:module';
import { writeFileSync } from 'node:fs';
const require = createRequire('/home/hatch/workspace/lift_coding/swissknife/package.json');
const { chromium } = require('playwright-core');

const BASE = 'http://127.0.0.1:3001/';
const SHOTS = '/home/hatch/workspace/lift_coding/visual_check';
const OUT = '/home/hatch/workspace/lift_coding/visual_check/fv_state/audit3/live-probe-results.json';
const sleep = (ms) => new Promise(r => setTimeout(r, ms));

const results = { started_at: new Date().toISOString(), console_errors: [] };
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
page.on('console', (m) => { if (m.type() === 'error') results.console_errors.push(m.text().slice(0, 240)); });
page.on('pageerror', (e) => results.console_errors.push(`pageerror: ${String(e).slice(0, 240)}`));

await page.goto(BASE, { waitUntil: 'domcontentloaded' });
await page.waitForFunction(() => Boolean(window.desktop), null, { timeout: 90000 });
await sleep(2000);

// ---------- Supervisor console ----------
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
      errorCaps: (s.errors || []).map(e => e.capability_id),
      healthStatus: s.snapshot?.health?.status ?? null,
      queue: s.snapshot?.queue?.length ?? null,
      goals: s.snapshot?.goals?.length ?? null,
      receipts: s.snapshot?.receipts?.length ?? null,
      taskboardLinks: s.snapshot?.taskboardLinks?.length ?? null,
      logs: (s.snapshot?.logs || []).map(l => ({ log_id: l.log_id, level: l.level, scope: l.scope })),
      runHistory: s.snapshot?.runHistory?.length ?? null,
      gatewayInstalled: Boolean(window.agentSupervisorGateway),
    };
  }).catch(() => null);
  if (consoleState && consoleState.transportMode !== 'fallback' && consoleState.status !== 'loading') break;
}
results.console = consoleState;
results.console_sample_leak = await page.evaluate(() => {
  const text = document.body.innerText || '';
  return {
    hasSampleCid: text.includes('bafyagent'),
    hasSampleReceipt: text.includes('receipt:agent-supervisor:g054'),
    hasSampleTaskboardTitle: text.includes('Imported the current development taskboard'),
  };
});

// VDA-G054 buttons navigate (fix 4)
results.g054_navigation = await page.evaluate(async () => {
  const app = window.agentSupervisorApp;
  const out = {};
  const click = (action) => document.querySelector(`[data-svd-workflow-action="${action}"]`)?.click();
  click('open-receipt-visibility');
  out.after_receipt_visibility = app.state.activeTab;
  click('preview-steering-prompt');
  out.after_preview_steering = app.state.activeTab;
  click('inspect-kda-evidence');
  out.after_kda = app.state.activeTab;
  click('open-taskboard-links');
  out.after_taskboard = app.state.activeTab;
  return out;
});

// Gateway-level receipt round-trip through the SAME gateway object the
// console invokes (fix 3): persist -> retrieve -> checkpoint -> logs.
results.gateway_roundtrip = await page.evaluate(async () => {
  const gw = window.agentSupervisorGateway;
  if (!gw) return { error: 'gateway not installed' };
  const receiptRecord = {
    receipt_id: 'rcpt-audit3-live-1', capability_id: 'supervisor.queue.read',
    owner: 'ipfs_kit_py', status: 'persisted', cid: '', created_at: '2026-10-14T00:00:00.000Z',
    correlation_id: 'audit3-live-probe',
  };
  const denied = await gw.invoke({
    capability_id: 'supervisor.receipts.persist', owner: 'ipfs_kit_py', access: 'governed-write',
    policy_class: 'confirm', payload: { receipt: receiptRecord }, correlation_id: 'audit3-live-denied',
  });
  const persisted = await gw.invoke({
    capability_id: 'supervisor.receipts.persist', owner: 'ipfs_kit_py', access: 'governed-write',
    policy_class: 'confirm',
    payload: { receipt: receiptRecord, confirmation_token: 'confirm-agent-supervisor:receipt:rcpt-audit3-live-1:audit3' },
    correlation_id: 'audit3-live-persist',
  });
  const cid = persisted?.receipt?.cid || persisted?.data?.cid || null;
  const retrieved = cid ? await gw.invoke({
    capability_id: 'supervisor.content.retrieve', owner: 'ipfs_kit_py', access: 'read',
    payload: { cid }, correlation_id: 'audit3-live-retrieve',
  }) : null;
  const checkpoint = await gw.invoke({
    capability_id: 'supervisor.event-dag.checkpoint', owner: 'ipfs_kit_py', access: 'governed-write',
    policy_class: 'confirm',
    payload: { receipt: { receipt_id: 'rcpt-audit3-live-1', cid }, confirmation_token: 'confirm-agent-supervisor:receipt:rcpt-audit3-live-1:audit3' },
    correlation_id: 'audit3-live-checkpoint',
  });
  const logs = await gw.invoke({
    capability_id: 'supervisor.logs.read', owner: 'ipfs_accelerate_py', access: 'read',
    payload: { limit: 10 }, correlation_id: 'audit3-live-logs',
  });
  return {
    persist_denied_without_confirmation: { state: denied?.state, reason: denied?.reason },
    persisted: { state: persisted?.state, cid, backend: persisted?.data?.backend, verified: persisted?.data?.verified },
    retrieved: retrieved && { state: retrieved.state, cid: retrieved.data?.cid, verified: retrieved.data?.verified, backend: retrieved.data?.backend, content_bytes: retrieved.data?.content_bytes },
    checkpoint: { state: checkpoint?.state, event_cid: checkpoint?.data?.event_dag?.cid, receipt_id: checkpoint?.receipt?.receipt_id },
    logs: { state: logs?.state, count: Array.isArray(logs?.data) ? logs.data.length : null, first: Array.isArray(logs?.data) ? logs.data[0] : null },
  };
});

// Steering dry-run local preview + confirmed typed error (fix 2), driven
// through the console's own invokeCapability.
results.steering = await page.evaluate(async () => {
  const app = window.agentSupervisorApp;
  const target = app.state.snapshot?.queue?.[0] || app.state.snapshot?.goals?.[0];
  if (!target) return { skipped: 'no live queue/goal target in snapshot' };
  const targetId = target.task_id || target.goal_cid || target.goal_id;
  const targetType = target.task_id ? 'task' : 'goal';
  const dry = await app.invokeCapability('supervisor.prompt-steering.request', {
    target_type: targetType, target_id: targetId, prompt: 'Audit3 live dry-run preview.', dry_run: true,
    client_request_id: 'audit3-live-dry',
  });
  const confirmed = await app.invokeCapability('supervisor.prompt-steering.request', {
    target_type: targetType, target_id: targetId, prompt: 'Audit3 live confirmed submission.', dry_run: false,
    confirmation_token: `confirm-agent-supervisor:${targetType}:${targetId}:audit3`,
    client_request_id: 'audit3-live-confirmed',
  });
  return {
    target: { targetType, targetId },
    dry_run: { state: dry?.state, accepted: dry?.data?.accepted, receipt: dry?.data?.receipt?.receipt_id },
    confirmed: { state: confirmed?.state, reason: confirmed?.reason },
  };
});
await page.screenshot({ path: `${SHOTS}/fv-14-supervisor-console-audit3.png` });

// ---------- datasets-browser (fix 5) ----------
await page.evaluate(async () => { await window.desktop.launchApp('datasets-browser'); });
await sleep(4000);
results.datasets_initial = await page.evaluate(() => {
  const win = [...document.querySelectorAll('.window')].find(w => w.innerText.includes('IPFS Datasets Browser'));
  const text = win?.innerText || '';
  return {
    found: Boolean(win),
    hasCannedCid: text.includes('bafydatasetg048'),
    hasCannedReceipt: text.includes('receipt:datasets-browser:g048'),
    semanticStatus: win?.querySelector('#datasets-semantic-status')?.textContent?.trim() || null,
  };
});
await page.evaluate(() => {
  [...document.querySelectorAll('.window')].find(w => w.innerText.includes('IPFS Datasets Browser'))
    ?.querySelector('[data-svd-workflow-action="run-semantic-search"]')?.click();
});
await sleep(6000);
await page.evaluate(() => {
  [...document.querySelectorAll('.window')].find(w => w.innerText.includes('IPFS Datasets Browser'))
    ?.querySelector('[data-svd-workflow-action="record-provenance"]')?.click();
});
await sleep(6000);
await page.evaluate(() => {
  const win = [...document.querySelectorAll('.window')].find(w => w.innerText.includes('IPFS Datasets Browser'));
  win?.querySelector('[data-svd-workflow-action="start-preparation-job"]')?.click();
});
await sleep(6000);
await page.evaluate(() => {
  const win = [...document.querySelectorAll('.window')].find(w => w.innerText.includes('IPFS Datasets Browser'));
  win?.querySelector('[data-svd-workflow-action="apply-schema-filter"]')?.click();
  win?.querySelector('[data-svd-workflow-action="show-schema-error"]')?.click();
  win?.querySelector('[data-svd-workflow-action="refresh-progress"]')?.click();
});
await sleep(6000);
results.datasets_after = await page.evaluate(() => {
  const win = [...document.querySelectorAll('.window')].find(w => w.innerText.includes('IPFS Datasets Browser'));
  return {
    semanticStatus: win?.querySelector('#datasets-semantic-status')?.textContent?.trim() || null,
    provenanceStatus: win?.querySelector('#datasets-provenance-status')?.textContent?.trim() || null,
    preparationStatus: win?.querySelector('#datasets-preparation-status')?.textContent?.trim() || null,
    errorStatus: win?.querySelector('#datasets-error-status')?.textContent?.trim() || null,
    progressStatus: win?.querySelector('#datasets-progress-status')?.textContent?.trim() || null,
    envelopeRendered: Boolean(win?.querySelector('#datasets-envelope-result .app-capability-envelope')),
    envelopeStatus: win?.querySelector('#datasets-envelope-result .app-capability-envelope')?.getAttribute('data-envelope-status') || null,
    logEntries: [...(win?.querySelectorAll('#datasets-workflow-log li') || [])].map(li => li.textContent.trim().slice(0, 200)),
  };
});
await page.screenshot({ path: `${SHOTS}/fv-15-datasets-browser-audit3.png` });

// ---------- accelerate-panel (fix 6) ----------
await page.evaluate(async () => { await window.desktop.launchApp('accelerate-panel'); });
await sleep(4000);
results.accelerate_initial = await page.evaluate(() => {
  const win = [...document.querySelectorAll('.window')].find(w => w.innerText.includes('IPFS Accelerate Panel'));
  const text = win?.innerText || '';
  return {
    found: Boolean(win),
    hasCannedCid: text.includes('bafyaccelerateg049'),
    hasCannedReceipt: text.includes('receipt:accelerate-panel:g049'),
    hasFakeWebGpuClaim: text.includes('completed through the WebGPU path'),
    primaryStatus: win?.querySelector('#accelerate-primary-status')?.textContent?.trim() || null,
  };
});
await page.evaluate(() => {
  [...document.querySelectorAll('.window')].find(w => w.innerText.includes('IPFS Accelerate Panel'))
    ?.querySelector('[data-svd-workflow-action="launch-primary-execution"]')?.click();
});
await sleep(8000);
await page.evaluate(() => {
  const win = [...document.querySelectorAll('.window')].find(w => w.innerText.includes('IPFS Accelerate Panel'));
  win?.querySelector('[data-svd-workflow-action="refresh-hardware-fit"]')?.click();
  win?.querySelector('[data-svd-workflow-action="inspect-model-artifacts"]')?.click();
});
await sleep(6000);
await page.evaluate(() => {
  const win = [...document.querySelectorAll('.window')].find(w => w.innerText.includes('IPFS Accelerate Panel'));
  win?.querySelector('[data-svd-workflow-action="recover-no-capacity"]')?.click();
  win?.querySelector('[data-svd-workflow-action="cancel-queued-job"]')?.click();
});
await sleep(6000);
results.accelerate_after = await page.evaluate(() => {
  const win = [...document.querySelectorAll('.window')].find(w => w.innerText.includes('IPFS Accelerate Panel'));
  return {
    primaryStatus: win?.querySelector('#accelerate-primary-status')?.textContent?.trim() || null,
    hardwareStatus: win?.querySelector('#accelerate-hardware-status')?.textContent?.trim() || null,
    modelStatus: win?.querySelector('#accelerate-model-status')?.textContent?.trim() || null,
    queueStatus: win?.querySelector('#accelerate-queue-status')?.textContent?.trim() || null,
    recoveryStatus: win?.querySelector('#accelerate-recovery-status')?.textContent?.trim() || null,
    envelopeRendered: Boolean(win?.querySelector('#accelerate-envelope-result .app-capability-envelope')),
    envelopeStatus: win?.querySelector('#accelerate-envelope-result .app-capability-envelope')?.getAttribute('data-envelope-status') || null,
    logEntries: [...(win?.querySelectorAll('#accelerate-workflow-log li') || [])].map(li => li.textContent.trim().slice(0, 200)),
  };
});
await page.screenshot({ path: `${SHOTS}/fv-16-accelerate-panel-audit3.png` });

results.finished_at = new Date().toISOString();
writeFileSync(OUT, JSON.stringify(results, null, 2));
console.log(JSON.stringify(results, null, 2).slice(0, 6000));
await browser.close();
