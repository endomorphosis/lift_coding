/**
 * Sharpened-requirement audit, steps 3/4 (browser side):
 * for a sample of apps spanning owners and dispositions, open the app on
 * the live desktop and read the mounted MCP++ actions panel
 * (live-tool-gateway): every control's button disabled state must match
 * the live catalog (enabled iff status 'available'), the output line
 * must read 'ready' iff available, and apps that are NOT tool_backed
 * must mount no panel at all. Then click one governed (mutating)
 * control in vibecode and record the result line — by design it can
 * only execute as a confirmation-gated dry run.
 * Results: audit2/ui-truthfulness.json; screenshot fv-13.
 */
import { chromium } from 'playwright';
import { readFileSync, writeFileSync } from 'node:fs';

const BASE = 'http://127.0.0.1:3001';
const catalog = JSON.parse(readFileSync(new URL('./bindings.json', import.meta.url), 'utf8'));
const byApp = new Map();
for (const c of catalog.controls) {
  if (!byApp.has(c.app_id)) byApp.set(c.app_id, []);
  byApp.get(c.app_id).push(c);
}

const SAMPLE = ['terminal', 'ai-chat', 'agent-supervisor', 'datasets-browser', 'mcp-plus-plus', 'vibecode'];
const NON_TOOL_BACKED = ['calculator', 'settings'];

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1500, height: 1050 } });
await page.goto(BASE, { waitUntil: 'domcontentloaded' });
await page.waitForFunction(() => Boolean(window.desktop), null, { timeout: 60_000 });

const report = { apps: {}, governed_click: null };
for (const appId of [...SAMPLE, ...NON_TOOL_BACKED]) {
  await page.evaluate(async (id) => {
    window.desktop.launchApp(id);
  }, appId);
  await page.waitForTimeout(3500);
  const state = await page.evaluate((id) => {
    const entry = [...window.desktop.windows.entries()].reverse().find(([, v]) => v.appId === id);
    if (!entry) return { window: false };
    const win = entry[1];
    const panel = win.element.querySelector('[data-testid="live-tool-gateway-panel"]');
    if (!panel) return { window: true, panel: false };
    const controls = [...panel.querySelectorAll('.live-tool-gateway-control')].map(row => {
      const button = row.querySelector('button');
      const output = row.querySelector('output');
      return {
        binding_id: button?.dataset.liveGatewayBinding,
        disabled: button?.disabled,
        output: output?.textContent?.trim(),
      };
    });
    return { window: true, panel: true, controls };
  }, appId);
  const expected = byApp.get(appId) ?? [];
  const mismatches = [];
  if (expected.length === 0 && state.panel) mismatches.push('panel mounted for non-tool-backed app');
  if (expected.length > 0 && !state.panel) mismatches.push('no panel for tool-backed app');
  for (const rendered of state.controls ?? []) {
    const truth = expected.find(c => c.binding_id === rendered.binding_id);
    if (!truth) { mismatches.push(`rendered control ${rendered.binding_id} not in catalog`); continue; }
    if (rendered.disabled !== (truth.status !== 'available')) {
      mismatches.push(`${rendered.binding_id}: disabled=${rendered.disabled} but catalog status=${truth.status}`);
    }
    if (truth.status === 'available' && rendered.output !== 'ready') {
      mismatches.push(`${rendered.binding_id}: output '${rendered.output}' != 'ready'`);
    }
  }
  report.apps[appId] = { rendered: state, expected_controls: expected.length, mismatches };
  console.log(`${appId}: panel=${state.panel} controls=${state.controls?.length ?? 0} mismatches=${mismatches.length}`);
  await page.evaluate((id) => {
    const entry = [...window.desktop.windows.entries()].reverse().find(([, v]) => v.appId === id);
    entry?.[1].element.querySelector('.window-control.close')?.click();
  }, appId);
  await page.waitForTimeout(600);
}

// Governed click in vibecode: the panel's mutating control can only run
// as a confirmation-gated dry run; record the visible result line.
await page.evaluate(() => window.desktop.launchApp('vibecode'));
await page.waitForTimeout(3500);
const governed = await page.evaluate(async () => {
  const entry = [...window.desktop.windows.entries()].reverse().find(([, v]) => v.appId === 'vibecode');
  const panel = entry?.[1].element.querySelector('[data-testid="live-tool-gateway-panel"]');
  if (!panel) return { panel: false };
  const rows = [...panel.querySelectorAll('.live-tool-gateway-control')];
  const target = rows
    .map(row => ({ row, button: row.querySelector('button'), output: row.querySelector('output') }))
    .find(({ button }) => button && !button.disabled);
  if (!target) return { panel: true, clicked: false };
  const binding = target.button.dataset.liveGatewayBinding;
  target.button.click();
  const deadline = Date.now() + 60_000;
  while (Date.now() < deadline) {
    const text = target.output.textContent?.trim() ?? '';
    if (text && text !== 'ready' && text !== 'pending') return { panel: true, clicked: true, binding, result_line: text };
    await new Promise(r => setTimeout(r, 500));
  }
  return { panel: true, clicked: true, binding, result_line: target.output.textContent?.trim(), timed_out: true };
});
report.governed_click = governed;
console.log('governed click:', JSON.stringify(governed).slice(0, 240));
await page.screenshot({ path: new URL('../../fv-13-ui-truthfulness.png', import.meta.url).pathname });
writeFileSync(new URL('./ui-truthfulness.json', import.meta.url), `${JSON.stringify(report, null, 2)}\n`);
await browser.close();
const totalMismatches = Object.values(report.apps).reduce((n, a) => n + a.mismatches.length, 0);
console.log(`TOTAL MISMATCHES: ${totalMismatches}`);
