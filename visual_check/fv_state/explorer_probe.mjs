// Focused probe: MCP++ Explorer health after the Profile G (R1) fix.
// Boots the desktop on the live stack, opens the Explorer, waits for its
// inspection to settle, and records the header state + message.
import { createRequire } from 'node:module';
import { writeFileSync } from 'node:fs';
const require = createRequire('/home/hatch/workspace/lift_coding/swissknife/package.json');
const { chromium } = require('playwright-core');

const BASE = 'http://127.0.0.1:3001/';
const SHOTS = '/home/hatch/workspace/lift_coding/visual_check';
const OUT = '/home/hatch/workspace/lift_coding/visual_check/fv_state/explorer-probe-results.json';
const sleep = (ms) => new Promise(r => setTimeout(r, ms));

const results = { started_at: new Date().toISOString(), console_errors: [] };
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
page.on('console', (m) => { if (m.type() === 'error') results.console_errors.push(m.text().slice(0, 300)); });

await page.goto(BASE, { waitUntil: 'domcontentloaded' });
await page.waitForFunction(() => Boolean(window.desktop), null, { timeout: 60000 });
await sleep(2000);

await page.evaluate(async () => { await window.desktop.launchApp('mcp-plus-plus'); });
await sleep(3000);

// Poll the Explorer DOM until the inspection settles (message shows "N/3 ... responded").
let snapshot = null;
for (let i = 0; i < 40; i++) {
  snapshot = await page.evaluate(() => {
    const root = document.querySelector('[data-testid="mcp-plus-plus-explorer"]');
    if (!root) return null;
    const state = root.querySelector('.mcppp-state')?.textContent?.trim() ?? null;
    const message = root.querySelector('.mcppp-message')?.textContent?.trim() ?? null;
    const services = [...root.querySelectorAll('.mcppp-service, [data-service]')].map(el => el.textContent.trim().slice(0, 120));
    return { state, message, services, text: root.textContent.slice(0, 4000) };
  });
  if (snapshot && snapshot.message && /responded/.test(snapshot.message) && snapshot.state !== 'loading') break;
  await sleep(3000);
}
results.explorer = snapshot;
await page.screenshot({ path: `${SHOTS}/fv-11-explorer-healthy.png` });
results.finished_at = new Date().toISOString();
writeFileSync(OUT, JSON.stringify(results, null, 2));
console.log(JSON.stringify({ state: snapshot?.state, message: snapshot?.message }, null, 2));
await browser.close();
