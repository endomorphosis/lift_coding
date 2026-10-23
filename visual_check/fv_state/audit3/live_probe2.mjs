// Audit3 step 8 (warm-stack re-drive): the first probe ran against a cold
// stack under load ~10 and the Profile G Python bridges timed out. This
// re-drive refreshes the console until its reads settle, then exercises
// the fix-3 gateway round-trip and the fix-2 steering paths live.
import { createRequire } from 'node:module';
import { writeFileSync } from 'node:fs';
const require = createRequire('/home/hatch/workspace/lift_coding/swissknife/package.json');
const { chromium } = require('playwright-core');

const BASE = 'http://127.0.0.1:3001/';
const SHOTS = '/home/hatch/workspace/lift_coding/visual_check';
const OUT = '/home/hatch/workspace/lift_coding/visual_check/fv_state/audit3/live-probe2-results.json';
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
await sleep(5000);

const readState = () => page.evaluate(() => {
  const app = window.agentSupervisorApp;
  if (!app) return null;
  const s = app.state;
  return {
    status: s.status, transportMode: s.transportMode,
    errorCaps: (s.errors || []).map(e => e.capability_id),
    errorReasons: (s.errors || []).map(e => `${e.capability_id}:${e.reason}`),
    healthStatus: s.snapshot?.health?.status ?? null,
    backends: (s.snapshot?.health?.backends || []).map(b => `${b.owner}:${b.status}`),
    queue: s.snapshot?.queue?.length ?? null,
    goals: s.snapshot?.goals?.length ?? null,
    receipts: s.snapshot?.receipts?.length ?? null,
    taskboardLinks: s.snapshot?.taskboardLinks?.length ?? null,
    logs: (s.snapshot?.logs || []).length,
    runHistory: s.snapshot?.runHistory?.length ?? null,
    firstQueue: s.snapshot?.queue?.[0] ? { task_id: s.snapshot.queue[0].task_id, title: s.snapshot.queue[0].title } : null,
    firstReceipt: s.snapshot?.receipts?.[0] ? { receipt_id: s.snapshot.receipts[0].receipt_id, cid: s.snapshot.receipts[0].cid } : null,
  };
}).catch(() => null);

let state = await readState();
results.refresh_attempts = [{ attempt: 0, errorCaps: state?.errorCaps ?? null }];
for (let attempt = 1; attempt <= 6; attempt++) {
  const settled = state && !state.errorCaps.includes('supervisor.queue.read') && !state.errorCaps.includes('supervisor.logs.read');
  if (settled) break;
  await page.evaluate(async () => { await window.agentSupervisorApp.refresh(true); }).catch(() => null);
  await sleep(8000);
  state = await readState();
  results.refresh_attempts.push({ attempt, errorCaps: state?.errorCaps ?? null });
}
results.console = state;
results.console_sample_leak = await page.evaluate(() => {
  const text = document.body.innerText || '';
  return { hasSampleCid: text.includes('bafyagent'), hasSampleReceipt: text.includes('receipt:agent-supervisor:g054') };
});

// Fix 3 round-trip through the console's gateway object.
results.gateway_roundtrip = await page.evaluate(async () => {
  const gw = window.agentSupervisorGateway;
  if (!gw) return { error: 'gateway not installed' };
  const receiptRecord = {
    receipt_id: 'rcpt-audit3-live-2', capability_id: 'supervisor.queue.read',
    owner: 'ipfs_kit_py', status: 'persisted', cid: '', created_at: '2026-10-14T00:00:00.000Z',
    correlation_id: 'audit3-live-probe-2',
  };
  const denied = await gw.invoke({
    capability_id: 'supervisor.receipts.persist', owner: 'ipfs_kit_py', access: 'governed-write',
    policy_class: 'confirm', payload: { receipt: receiptRecord }, correlation_id: 'audit3-2-denied',
  });
  const persisted = await gw.invoke({
    capability_id: 'supervisor.receipts.persist', owner: 'ipfs_kit_py', access: 'governed-write',
    policy_class: 'confirm',
    payload: { receipt: receiptRecord, confirmation_token: 'confirm-agent-supervisor:receipt:rcpt-audit3-live-2:audit3' },
    correlation_id: 'audit3-2-persist',
  });
  const cid = persisted?.receipt?.cid || persisted?.data?.cid || null;
  const retrieved = cid ? await gw.invoke({
    capability_id: 'supervisor.content.retrieve', owner: 'ipfs_kit_py', access: 'read',
    payload: { cid }, correlation_id: 'audit3-2-retrieve',
  }) : null;
  const checkpoint = await gw.invoke({
    capability_id: 'supervisor.event-dag.checkpoint', owner: 'ipfs_kit_py', access: 'governed-write',
    policy_class: 'confirm',
    payload: { receipt: { receipt_id: 'rcpt-audit3-live-2', cid }, confirmation_token: 'confirm-agent-supervisor:receipt:rcpt-audit3-live-2:audit3' },
    correlation_id: 'audit3-2-checkpoint',
  });
  const logs = await gw.invoke({
    capability_id: 'supervisor.logs.read', owner: 'ipfs_accelerate_py', access: 'read',
    payload: { limit: 10 }, correlation_id: 'audit3-2-logs',
  });
  return {
    persist_denied_without_confirmation: { state: denied?.state, reason: denied?.reason },
    persisted: { state: persisted?.state, reason: persisted?.reason || null, cid, backend: persisted?.data?.backend, verified: persisted?.data?.verified },
    retrieved: retrieved && { state: retrieved.state, cid: retrieved.data?.cid, verified: retrieved.data?.verified, backend: retrieved.data?.backend, content_bytes: retrieved.data?.content_bytes },
    checkpoint: { state: checkpoint?.state, reason: checkpoint?.reason || null, event_cid: checkpoint?.data?.event_dag?.cid, receipt_id: checkpoint?.receipt?.receipt_id },
    logs: { state: logs?.state, reason: logs?.reason || null, count: Array.isArray(logs?.data) ? logs.data.length : null },
  };
});

// Fix 2 steering through the console's own invokeCapability. If the live
// snapshot has no task/goal target, steer against the console's fixture
// target is NOT possible in live mode; report the skip honestly.
results.steering = await page.evaluate(async () => {
  const app = window.agentSupervisorApp;
  const target = app.state.snapshot?.queue?.[0] || app.state.snapshot?.goals?.[0];
  if (!target) return { skipped: 'live snapshot carries no queue/goal target on this stack (Profile G state is empty); unit check check_fix2.mjs covers the path' };
  const targetId = target.task_id || target.goal_cid || target.goal_id;
  const targetType = target.task_id ? 'task' : 'goal';
  const dry = await app.invokeCapability('supervisor.prompt-steering.request', {
    target_type: targetType, target_id: targetId, prompt: 'Audit3 warm-stack dry-run preview.', dry_run: true,
    client_request_id: 'audit3-2-dry',
  });
  const confirmed = await app.invokeCapability('supervisor.prompt-steering.request', {
    target_type: targetType, target_id: targetId, prompt: 'Audit3 warm-stack confirmed submission.', dry_run: false,
    confirmation_token: `confirm-agent-supervisor:${targetType}:${targetId}:audit3`,
    client_request_id: 'audit3-2-confirmed',
  });
  return {
    target: { targetType, targetId },
    dry_run: { state: dry?.state, accepted: dry?.data?.accepted, receipt: dry?.data?.receipt?.receipt_id },
    confirmed: { state: confirmed?.state, reason: confirmed?.reason },
  };
});

// Console receipt-op UI drive, if a live receipt exists.
results.receipt_ops_ui = await page.evaluate(async () => {
  const app = window.agentSupervisorApp;
  const first = app.state.snapshot?.receipts?.[0];
  if (!first) return { skipped: 'no live receipts in snapshot; gateway round-trip above covers the same invokeCapability path' };
  app.state.selectedReceiptId = first.receipt_id;
  app.state.activeTab = 'receipts';
  app.state.receiptOperation.confirm = true;
  await app.retrieveSelectedReceiptContent();
  const afterRetrieve = app.state.receiptOperation.result?.state || null;
  await app.persistSelectedReceipt();
  const persistResult = app.state.receiptOperation.result;
  await app.checkpointSelectedReceipt();
  const checkpointResult = app.state.receiptOperation.result;
  return {
    receipt_id: first.receipt_id,
    retrieve_state: afterRetrieve,
    persist_state: persistResult?.state || null,
    persist_cid: persistResult?.receipt?.cid || persistResult?.data?.cid || null,
    checkpoint_state: checkpointResult?.state || null,
    checkpoint_event_cid: checkpointResult?.data?.event_dag?.cid || null,
  };
});

await page.screenshot({ path: `${SHOTS}/fv-17-supervisor-console-audit3-warm.png` });
results.finished_at = new Date().toISOString();
writeFileSync(OUT, JSON.stringify(results, null, 2));
console.log(JSON.stringify(results, null, 2).slice(0, 5000));
await browser.close().catch(() => null);
process.exit(0);
