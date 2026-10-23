// Audit3 static interaction inventory scanner.
// Reads the SERVED implementation of each canonical app and extracts:
//  - DOM interaction sites (buttons/inputs/selects/textareas/forms, listeners)
//  - backing calls (fetch URLs, invokeCapability ids, descriptor operations)
//  - fixture markers (canned VDA receipt/CID strings)
import { readFileSync } from 'node:fs';

const SK = process.env.HOME + '/workspace/lift_coding/swissknife';
const APPS = {
  'terminal': ['web/js/apps/terminal.js'],
  'vibecode': ['web/js/apps/vibecode.js'],
  'music-studio-unified': ['web/js/apps/music-studio-unified.js'],
  'ai-chat': ['web/js/apps/ai-chat.js'],
  'file-manager': ['web/js/apps/file-manager.js'],
  'task-manager': ['web/js/apps/task-manager.js'],
  'todo': ['web/js/apps/todo.js'],
  'model-browser': ['web/js/apps/model-browser.js'],
  'huggingface': ['web/js/apps/huggingface.js'],
  'openrouter': ['web/js/apps/openrouter.js'],
  'ipfs-explorer': ['web/js/apps/ipfs-explorer.js'],
  'device-manager': ['web/js/apps/device-manager.js'],
  'settings': ['web/js/apps/settings.js'],
  'mcp-control': ['web/js/apps/mcp-control.js'],
  'api-keys': ['web/js/apps/api-keys.js'],
  'github': ['web/js/apps/github.js'],
  'oauth-login': ['web/js/apps/oauth-login.js'],
  'cron': ['web/js/apps/cron.js'],
  'navi': ['web/js/apps/navi.js'],
  'p2p-network': ['web/js/apps/p2p-network.js'],
  'p2p-chat-unified': ['web/js/apps/p2p-chat-unified.js'],
  'neural-network-designer': ['web/js/apps/neural-network-designer.js'],
  'training-manager': ['web/js/apps/training-manager.js'],
  'calculator': ['web/js/apps/calculator.js'],
  'clock': ['web/js/apps/clock.js'],
  'calendar': ['web/js/apps/calendar.js'],
  'peertube': ['web/js/apps/peertube.js'],
  'friends-list': ['web/js/apps/friends-list.js'],
  'image-viewer': ['web/js/apps/image-viewer.js'],
  'notes': ['web/js/apps/notes.js'],
  'media-player': ['web/js/apps/media-player.js'],
  'system-monitor': ['web/js/apps/system-monitor.js'],
  'neural-photoshop': ['web/js/apps/neural-photoshop.js'],
  'cinema': ['web/js/apps/cinema.js'],
  'strudel': ['web/js/apps/strudel-grandma.js'],
  'strudel-ai-daw': ['web/js/apps/strudel-ai-daw.js'],
  'music-studio': ['web/js/apps/music-studio.js'],
  'p2p-chat': ['web/js/apps/p2p-chat.js'],
  'datasets-browser': ['SURFACE:createDatasetsBrowserSurface'],
  'accelerate-panel': ['SURFACE:createAcceleratePanelSurface'],
  'idl-explorer': ['SURFACE:createIDLExplorerSurface'],
  'glasses-preview': ['SURFACE:createGlassesPreviewSurface'],
  'orb-auto-ui': ['SURFACE:createORBAutoUISurface'],
  'mcp-plus-plus': ['web/js/apps/mcp-plus-plus-explorer.js'],
  'agent-supervisor': ['web/js/apps/agent-supervisor.js'],
};

const mainSimple = readFileSync(SK + '/web/js/main-simple.js', 'utf8').split('\n');
function surfaceSlice(fnName) {
  const defRe = new RegExp('^    (async )?' + fnName + '\\(contentElement\\) \\{');
  const start = mainSimple.findIndex(l => defRe.test(l));
  if (start < 0) return '';
  // find next sibling method at same indent ("    async " or "    create") after start+1
  let end = mainSimple.length;
  for (let i = start + 1; i < mainSimple.length; i++) {
    if (/^    (async )?[A-Za-z_$][\w$]*\(/.test(mainSimple[i]) && !mainSimple[i].includes(fnName)) { end = i; break; }
  }
  return mainSimple.slice(start, end).join('\n');
}

function uniq(a) { return [...new Set(a)]; }
function scan(src) {
  const lines = src.split('\n');
  const buttons = [];
  const reBtn = /<button[^>]*>/g;
  let m;
  while ((m = reBtn.exec(src))) {
    const tag = m[0];
    const line = src.slice(0, m.index).split('\n').length;
    const after = src.slice(m.index, m.index + 220);
    const label = (after.match(/>([^<>{}]{2,60})</) || [])[1]?.trim() || '';
    buttons.push({
      line,
      action: (tag.match(/data-action="([^"]+)"/) || [])[1] || (tag.match(/data-svd-workflow-action="([^"]+)"/) || [])[1] || null,
      testid: (tag.match(/data-testid="([^"]+)"/) || [])[1] || null,
      label: label.replace(/\$\{[^}]*\}/g, '…'),
    });
  }
  const listeners = [];
  const reLis = /addEventListener\(\s*'([a-z]+)'/g;
  while ((m = reLis.exec(src))) {
    const line = src.slice(0, m.index).split('\n').length;
    const ctx = lines[line - 1].trim().slice(0, 140);
    listeners.push({ type: m[1], line, ctx });
  }
  const byType = {};
  for (const l of listeners) byType[l.type] = (byType[l.type] || 0) + 1;
  const fetches = uniq([...src.matchAll(/fetch\(\s*`([^`]{1,120})`|fetch\(\s*'([^']{1,120})'|fetch\(\s*"([^"]{1,120})"/g)].map(x => x[1] || x[2] || x[3]));
  const invokeCaps = uniq([...src.matchAll(/invokeCapability\(\s*'([^']+)'/g)].map(x => x[1]));
  const descriptorOps = uniq([...src.matchAll(/invokeDescriptorOperation\(\s*\{[^}]*?descriptor_id:\s*'([^']+)'[^}]*?operation:\s*'([^']+)'/gs)].map(x => x[1] + '.' + x[2]));
  const descriptorOpsDyn = /invokeDescriptorOperation\(/.test(src) ? (src.match(/invokeDescriptorOperation\(/g) || []).length : 0;
  const extHosts = uniq([...src.matchAll(/https:\/\/([a-z0-9.-]+)/gi)].map(x => x[1]));
  return {
    loc: lines.length,
    buttons,
    buttonCount: buttons.length,
    inputs: (src.match(/<input[\s>]/g) || []).length,
    selects: (src.match(/<select[\s>]/g) || []).length,
    textareas: (src.match(/<textarea[\s>]/g) || []).length,
    forms: (src.match(/<form[\s>]/g) || []).length,
    onclickAttrs: (src.match(/onclick=/g) || []).length,
    listenersByType: byType,
    listenerSites: listeners,
    fetches,
    invokeCaps,
    descriptorOps,
    descriptorOpCalls: descriptorOpsDyn,
    extHosts,
    localStorage: (src.match(/localStorage/g) || []).length,
    sessionStorage: (src.match(/sessionStorage/g) || []).length,
    indexedDB: (src.match(/indexedDB/g) || []).length,
    imports: uniq([...src.matchAll(/from\s+'([^']+)'/g)].map(x => x[1]).filter(s => s.includes('capabilit') || s.includes('gateway') || s.includes('orb') || s.includes('descriptor') || s.includes('mcp'))),
    fixtureReceipts: uniq([...src.matchAll(/receipt:[a-z0-9-]+:g\d+:[a-z0-9:-]+/gi)].map(x => x[0])).slice(0, 14),
    fixtureCids: uniq([...src.matchAll(/bafy[a-z0-9]*g\d{3}[a-z0-9]*/gi)].map(x => x[0])).slice(0, 14),
    hardcodedCidStrings: (src.match(/'bafy[a-z0-9]+'/g) || []).length,
  };
}

const out = {};
for (const [app, files] of Object.entries(APPS)) {
  const parts = [];
  for (const f of files) {
    if (f.startsWith('SURFACE:')) parts.push(surfaceSlice(f.slice(8)));
    else parts.push(readFileSync(SK + '/' + f, 'utf8'));
  }
  out[app] = { files, ...scan(parts.join('\n')) };
}
console.log(JSON.stringify(out, null, 1));
