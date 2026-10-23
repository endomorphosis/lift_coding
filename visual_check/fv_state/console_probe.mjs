// Item 4 probe: Agent Supervisor console gateway state on the live stack.
// Opens the console, waits for its refresh to settle, and records the app
// state (status / transportMode / errors / live-vs-sample snapshot shape).
import { createRequire } from 'node:module';
import { writeFileSync } from 'node:fs';
const require = createRequire('/home/hatch/workspace/lift_coding/swissknife/package.json');
const { chromium } = require('playwright-core');

const BASE = 'http://127.0.0.1:3001/';
const SHOTS = '/home/hatch/workspace/lift_coding/visual_check';
const OUT = '/home/hatch/workspace/lift_coding/visual_check/fv_state/console-probe-results.json';
const sleep = (ms) => new Promise(r => setTimeout(r, ms));

const results = { started_at: new Date().toISOString(), console_errors: [] };
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
page.on('console', (m) => { if (m.type() === 'error') results.console_errors.push(m.text().slice(0, 240)); });

await page.goto(BASE, { waitUntil: 'domcontentloaded' });
await page.waitForFunction(() => Boolean(window.desktop), null, { timeout: 60000 });
await sleep(2000);
await page.evaluate(async () => { await window.desktop.launchApp('agent-supervisor'); });

// Poll the app state until the refresh settles out of loading/fallback.
let state = null;
for (let i = 0; i < 40; i++) {
  await sleep(3000);
  state = await page.evaluate(() => {
    const app = window.agentSupervisorApp;
    if (!app) return null;
    const s = app.state;
    return {
      status: s.status,
      transportMode: s.transportMode,
      errors: s.errors,
      health: s.snapshot?.health ?? null,
      queueLength: s.snapshot?.queue?.length ?? null,
      goalsLength: s.snapshot?.goals?.length ?? null,
      receiptsLength: s.snapshot?.receipts?.length ?? null,
      firstQueueTitle: s.snapshot?.queue?.[0]?.title ?? null,
      gatewayInstalled: Boolean(window.agentSupervisorGateway),
    };
  }).catch(() => null);
  if (state && state.transportMode !== 'fallback' && state.status !== 'loading') break;
}
results.console = state;
await page.screenshot({ path: `${SHOTS}/fv-12-supervisor-console-live.png` });
results.finished_at = new Date().toISOString();
writeFileSync(OUT, JSON.stringify(results, null, 2));
console.log(JSON.stringify(state, null, 2));
await browser.close();
