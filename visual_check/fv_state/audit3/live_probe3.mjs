// Audit3 step 8 (final settle check): receipts.read flaked once with
// server_unavailable during a concurrent refresh burst; all three
// services answer mcp++/tasks/list instantly by direct RPC. Refresh the
// console again and record the settled error set + a direct gateway
// receipts.read invocation.
import { createRequire } from 'node:module';
import { writeFileSync } from 'node:fs';
const require = createRequire('/home/hatch/workspace/lift_coding/swissknife/package.json');
const { chromium } = require('playwright-core');
const sleep = (ms) => new Promise(r => setTimeout(r, ms));
const results = { started_at: new Date().toISOString() };
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
await page.goto('http://127.0.0.1:3001/', { waitUntil: 'domcontentloaded' });
await page.waitForFunction(() => Boolean(window.desktop), null, { timeout: 90000 });
await sleep(2000);
await page.evaluate(async () => { await window.desktop.launchApp('agent-supervisor'); });
await sleep(6000);
await page.evaluate(async () => { await window.agentSupervisorApp.refresh(true); }).catch(() => null);
await sleep(6000);
results.console = await page.evaluate(() => {
  const s = window.agentSupervisorApp.state;
  return {
    status: s.status, transportMode: s.transportMode,
    errorCaps: (s.errors || []).map(e => e.capability_id),
    healthStatus: s.snapshot?.health?.status ?? null,
    receipts: s.snapshot?.receipts?.length ?? null,
    logs: (s.snapshot?.logs || []).length,
  };
});
results.direct_receipts_read = await page.evaluate(async () => {
  const r = await window.agentSupervisorGateway.invoke({
    capability_id: 'supervisor.receipts.read', owner: 'ipfs_kit_py', access: 'read',
    payload: {}, correlation_id: 'audit3-3-receipts',
  });
  return { state: r?.state, reason: r?.reason || null, count: Array.isArray(r?.data) ? r.data.length : null };
});
await page.screenshot({ path: '/home/hatch/workspace/lift_coding/visual_check/fv-17-supervisor-console-audit3-warm.png' });
results.finished_at = new Date().toISOString();
writeFileSync('/home/hatch/workspace/lift_coding/visual_check/fv_state/audit3/live-probe3-results.json', JSON.stringify(results, null, 2));
console.log(JSON.stringify(results, null, 2));
await browser.close().catch(() => null);
process.exit(0);
