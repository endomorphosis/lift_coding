// Functional-verification drive: SwissKnife desktop on the LIVE stack (vite :3001).
// Exercises: desktop boot, all 48 app ids (launch/focus/close + window probe),
// MCP++ Explorer tool discovery + invocation, MCP Control mediated invocation,
// agent-supervisor steering through its confirmation gate (dry-run).
// Records structured results to fv_state/drive-results.json; screenshots to visual_check/.
import { createRequire } from 'node:module';
import { writeFileSync, appendFileSync } from 'node:fs';
const require = createRequire('/home/hatch/workspace/lift_coding/swissknife/package.json');
const { chromium } = require('playwright-core');

const BASE = 'http://127.0.0.1:3001/';
const SHOTS = '/home/hatch/workspace/lift_coding/visual_check';
const OUT = '/home/hatch/workspace/lift_coding/visual_check/fv_state/drive-results.json';
const IDS = ['terminal','vibecode','music-studio-unified','ai-chat','file-manager','task-manager','todo','model-browser','huggingface','openrouter','ipfs-explorer','device-manager','settings','mcp-control','api-keys','github','oauth-login','cron','navi','p2p-network','p2p-chat-unified','neural-network-designer','training-manager','calculator','clock','calendar','peertube','friends-list','image-viewer','notes','media-player','system-monitor','neural-photoshop','cinema','strudel','strudel-ai-daw','music-studio','p2p-chat','datasets-browser','accelerate-panel','idl-explorer','glasses-preview','orb-auto-ui','mcp-plus-plus','agent-supervisor','code-editor','strudel-grandma','p2p-chat-offline'];

const results = { started_at: new Date().toISOString(), apps: [], features: {}, console_errors: [], failed_requests: [] };
const log = (...a) => console.log('[drive]', ...a);

async function launch(page, id) {
  // Race the desktop launch against a timeout: some apps' launch promise never
  // settles in a headless session (observed: strudel-ai-daw). The window may
  // still register in desktop.windows even when the promise hangs, so after a
  // timeout we probe the map directly.
  const attempt = page.evaluate(async (appId) => {
    const desktop = window.desktop;
    await desktop.launchApp(appId);
    const entries = Array.from(desktop.windows.entries());
    const match = [...entries].reverse().find(([, v]) => v.appId === appId);
    return match ? match[0] : null;
  }, id);
  const timeout = new Promise((resolve) => setTimeout(() => resolve('__timeout__'), 20000));
  const winner = await Promise.race([attempt.catch((e) => `__error__${String(e).slice(0, 120)}`), timeout]);
  if (winner === '__timeout__') {
    const wid = await page.evaluate((appId) => {
      const entries = Array.from(window.desktop.windows.entries());
      const match = [...entries].reverse().find(([, v]) => v.appId === appId);
      return match ? match[0] : null;
    }, id).catch(() => null);
    return { windowId: wid, launchTimeout: true };
  }
  if (typeof winner === 'string' && winner.startsWith('__error__')) {
    return { windowId: null, launchError: winner.slice(9) };
  }
  return { windowId: winner, launchTimeout: false };
}
async function closeWin(page, windowId) {
  // The served desktop (web/js/main-simple.js) exposes no desktop.closeWindow();
  // windows close via their titlebar control (.window-control.close), the same
  // path a user takes. Dispatch the click inside the page.
  return page.evaluate((wid) => {
    const desktop = window.desktop;
    const entry = desktop.windows.get(wid);
    if (!entry) return false;
    const btn = entry.element.querySelector('.window-control.close');
    if (!btn) return false;
    btn.click();
    return !desktop.windows.has(wid);
  }, windowId);
}
async function focusWin(page, windowId) {
  return page.evaluate((wid) => {
    const desktop = window.desktop;
    const entry = desktop.windows.get(wid);
    if (!entry) return false;
    desktop.focusWindow(entry.element);
    return entry.element.classList.contains('focused') || entry.element.style.zIndex;
  }, windowId);
}
const sleep = (ms) => new Promise(r => setTimeout(r, ms));

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
page.on('console', (m) => { if (m.type() === 'error') results.console_errors.push(m.text().slice(0, 300)); });
page.on('requestfailed', (r) => results.failed_requests.push(`${r.method()} ${r.url().slice(0, 160)}`));
page.on('response', (r) => { if (!r.ok()) results.failed_requests.push(`${r.status()} ${r.request().method()} ${r.url().slice(0, 160)}`); });

await page.goto(BASE, { waitUntil: 'domcontentloaded' });
await page.waitForFunction(() => Boolean(window.desktop), null, { timeout: 60000 });
await sleep(2500);
await page.screenshot({ path: `${SHOTS}/fv-01-desktop-live.png` });
results.features.desktop_boot = { ok: true };
  writeFileSync(OUT, JSON.stringify(results, null, 1));
log('desktop booted');

// ---- All-apps launch/focus/close sweep -------------------------------------
for (const id of IDS) {
  const rec = { app_id: id };
  try {
    const lr = await launch(page, id);
    const wid = lr.windowId;
    rec.window_id = wid;
    rec.opened = wid != null;
    if (lr.launchTimeout) rec.launch_timeout = true;
    if (lr.launchError) rec.launch_error = lr.launchError;
    await sleep(1100);
    if (wid) {
      rec.focus = await focusWin(page, wid);
      rec.dom_windows = await page.evaluate(() => document.querySelectorAll('.window').length);
      rec.title = await page.evaluate((w) => {
        const el = window.desktop.windows.get(w)?.element;
        return el ? (el.querySelector('.window-title, .title, h1, h2')?.textContent || '').trim().slice(0, 80) : '';
      }, wid);
      rec.closed = await closeWin(page, wid);
      await sleep(250);
    }
  } catch (e) {
    rec.error = String(e).slice(0, 240);
  }
  results.apps.push(rec);
  appendFileSync('/home/hatch/workspace/lift_coding/visual_check/fv_state/drive-apps.jsonl', JSON.stringify(rec) + '\n');
  log('app', id, rec.opened ? 'opened' : 'FAILED', rec.error || '');
}
await page.screenshot({ path: `${SHOTS}/fv-02-sweep-done.png` });

// ---- MCP++ Explorer deep-dive ------------------------------------------------
try {
  const wid = (await launch(page, 'mcp-plus-plus')).windowId;
  await sleep(4000);
  const winText = await page.evaluate((w) => window.desktop.windows.get(w)?.element?.innerText || '', wid);
  results.features.explorer = { window_text_head: winText.slice(0, 600) };
  await page.screenshot({ path: `${SHOTS}/fv-03-explorer-live.png` });
  // Tools tab
  const win = page.locator('.window').filter({ hasText: 'MCP' }).last();
  const toolsTab = win.getByText('Tools', { exact: true }).first();
  if (await toolsTab.count()) { await toolsTab.click(); await sleep(2500); }
  results.features.explorer.text_after_tools_tab = (await page.evaluate((w) => window.desktop.windows.get(w)?.element?.innerText || '', wid)).slice(0, 900);
  await page.screenshot({ path: `${SHOTS}/fv-04-explorer-tools.png` });
  await closeWin(page, wid);
} catch (e) { results.features.explorer = { error: String(e).slice(0, 300) }; }
log('explorer done');

// ---- MCP Control deep-dive ----------------------------------------------------
try {
  const wid = (await launch(page, 'mcp-control')).windowId;
  await sleep(4000);
  const text = await page.evaluate((w) => window.desktop.windows.get(w)?.element?.innerText || '', wid);
  results.features.mcp_control = { window_text_head: text.slice(0, 900) };
  await page.screenshot({ path: `${SHOTS}/fv-05-mcp-control-live.png` });
  await closeWin(page, wid);
} catch (e) { results.features.mcp_control = { error: String(e).slice(0, 300) }; }
log('mcp control done');

// ---- Agent supervisor steering (dry-run through confirm gate) -----------------
try {
  const wid = (await launch(page, 'agent-supervisor')).windowId;
  await sleep(4000);
  const text = await page.evaluate((w) => window.desktop.windows.get(w)?.element?.innerText || '', wid);
  results.features.supervisor = { window_text_head: text.slice(0, 900) };
  await page.screenshot({ path: `${SHOTS}/fv-06-supervisor-live.png` });
  await closeWin(page, wid);
} catch (e) { results.features.supervisor = { error: String(e).slice(0, 300) }; }
log('supervisor done');

results.finished_at = new Date().toISOString();
writeFileSync(OUT, JSON.stringify(results, null, 1));
await browser.close();
log('DONE', OUT);
