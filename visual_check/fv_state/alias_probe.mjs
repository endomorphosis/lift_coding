// X1 probe: raw alias launches through the served desktop's launchApp.
// For each alias, launchApp(alias) must open a window registered under the
// CANONICAL app id; unknown ids must remain a clean no-op; canonical ids
// must behave exactly as before.
import { createRequire } from 'node:module';
import { writeFileSync } from 'node:fs';
const require = createRequire('/home/hatch/workspace/lift_coding/swissknife/package.json');
const { chromium } = require('playwright-core');

const BASE = 'http://127.0.0.1:3001/';
const OUT = '/home/hatch/workspace/lift_coding/visual_check/fv_state/alias-probe-results.json';
const sleep = (ms) => new Promise(r => setTimeout(r, ms));
const ALIASES = [
  ['code-editor', 'vibecode'],
  ['strudel-grandma', 'strudel'],
  ['p2p-chat-offline', 'p2p-chat'],
];

const results = { started_at: new Date().toISOString(), aliases: [], canonical: null, unknown: null, console_errors: [] };
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
page.on('console', (m) => { if (m.type() === 'error') results.console_errors.push(m.text().slice(0, 200)); });
await page.goto(BASE, { waitUntil: 'domcontentloaded' });
await page.waitForFunction(() => Boolean(window.desktop), null, { timeout: 60000 });
await sleep(2000);

async function launchAndFind(appId, expectAppId) {
  await page.evaluate(async (id) => { await window.desktop.launchApp(id); }, appId).catch(() => {});
  await sleep(1200);
  return page.evaluate((expected) => {
    const entries = Array.from(window.desktop.windows.entries());
    const match = [...entries].reverse().find(([, v]) => v.appId === expected);
    return match ? match[0] : null;
  }, expectAppId);
}
async function closeWin(windowId) {
  return page.evaluate((wid) => {
    const entry = window.desktop.windows.get(wid);
    if (!entry) return false;
    const btn = entry.element.querySelector('.window-control.close');
    if (!btn) return false;
    btn.click();
    return !window.desktop.windows.has(wid);
  }, windowId);
}

for (const [alias, canonical] of ALIASES) {
  const wid = await launchAndFind(alias, canonical);
  const closed = wid ? await closeWin(wid) : false;
  results.aliases.push({ alias, canonical, windowId: wid, opened: Boolean(wid), closed });
  console.log(alias, '->', canonical, 'opened:', Boolean(wid), 'closed:', closed);
}

const termWid = await launchAndFind('terminal', 'terminal');
results.canonical = { id: 'terminal', windowId: termWid, opened: Boolean(termWid), closed: termWid ? await closeWin(termWid) : false };
console.log('terminal opened:', Boolean(termWid));

const before = await page.evaluate(() => window.desktop.windows.size);
await page.evaluate(async () => { await window.desktop.launchApp('no-such-app-xyz'); }).catch(() => {});
await sleep(600);
const after = await page.evaluate(() => window.desktop.windows.size);
results.unknown = { id: 'no-such-app-xyz', windowsBefore: before, windowsAfter: after, noWindowOpened: before === after };
console.log('unknown id no-op:', before === after);

results.finished_at = new Date().toISOString();
writeFileSync(OUT, JSON.stringify(results, null, 2));
await browser.close();
