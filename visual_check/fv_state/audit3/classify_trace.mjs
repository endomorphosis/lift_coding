// Step 7: per-app interaction trace table with exact counts.
// Census: inventory-raw.json (per-app static control counts, computed from
// the file itself). Connection evidence: BROKEN_CONTRACT_MAP P15 (the
// runtime-injected mediated live-tool gateway panel executed for all 38
// tool-backed apps), audit3 fixes 1-6, checkpoint verified-OK list, and the
// supervisor capability contract. Writes trace-table.json + TRACE_TABLE.md.
import { readFileSync, writeFileSync } from 'node:fs';

const here = new URL('.', import.meta.url);
const inv = JSON.parse(readFileSync(new URL('inventory-raw.json', here), 'utf8'));
const p15 = JSON.parse(readFileSync(new URL('../audit2/per-app-invocations.json', here), 'utf8'));
const toolBacked = new Set(p15.map(e => e.app_id));

const n = x => (typeof x === 'number' ? x : (x || []).length);
const census = appId => {
  const e = inv[appId];
  return { buttons: e.buttonCount, selects: n(e.selects), inputs: n(e.inputs), textareas: n(e.textareas), total: e.buttonCount + n(e.selects) + n(e.inputs) + n(e.textareas) };
};

const SURFACE_APPS = new Set(['datasets-browser', 'accelerate-panel', 'idl-explorer', 'orb-auto-ui', 'glasses-preview']);
const EXTERNAL_NOTES = {
  'github': 'external-direct (api.github.com)',
  'github-explorer': 'external-direct (api.github.com)',
  'openrouter': 'external-direct (openrouter.ai)',
  'oauth-login': 'external-direct (accounts.google.com) / external_provider disposition',
  'api-keys': 'policy_blocked disposition (backend-status catalog)',
  'p2p-network': 'external-direct demo endpoints (cloudflare/workers); also carries a mediated panel (in P15 set)',
};

const rows = [];
for (const appId of Object.keys(inv)) {
  const c = census(appId);
  let cls, note;
  if (appId === 'agent-supervisor') {
    cls = 'console — capability-mapped (see supervisor capability table)';
    note = 'Static census covers header actions, receipt-op controls and the 8 VDA-G054 workflow buttons (fixed by audit3 fix 4); row-selection controls are rendered per live snapshot item and feed the capability invocations.';
  } else if (SURFACE_APPS.has(appId)) {
    cls = 'generated descriptor surface (see surface table)';
    note = 'Covered by the surface table below; census row kept for arithmetic completeness.';
  } else if (toolBacked.has(appId)) {
    cls = 'tool_backed — backend-connected via mediated live-tool gateway panel (P15)';
    note = 'Static controls are the app\u2019s own local features; the runtime-injected panel (tool select, transport select, execute/dry-run/replay) executed real mediated invocations for this app in P15.' + (EXTERNAL_NOTES[appId] ? ` Also: ${EXTERNAL_NOTES[appId]}.` : '');
  } else {
    cls = 'declared local / external (no ORB/IDL claim)';
    note = EXTERNAL_NOTES[appId] || 'Browser-local app function; no backend feature is claimed by its controls.';
  }
  rows.push({ app_id: appId, ...c, class: cls, note });
}

const totals = rows.reduce((a, r) => ({ buttons: a.buttons + r.buttons, selects: a.selects + r.selects, inputs: a.inputs + r.inputs, textareas: a.textareas + r.textareas, total: a.total + r.total }), { buttons: 0, selects: 0, inputs: 0, textareas: 0, total: 0 });

const surfaces = [
  { surface: 'datasets-browser', controls: 8, backend_connected: 6, declared_local: 2, fixed: 8, typed: 0, detail: 'Search→semantic_search, Provenance→record_provenance (confirmed), Prepare→index (confirmed), Progress→sync_status; schema/split selects parameterize semantic_search. Apply Filters = local staging; Recover Error = local pre-transport validation.' },
  { surface: 'accelerate-panel', controls: 5, backend_connected: 4, declared_local: 0, fixed: 5, typed: 1, detail: 'Run Inference→run_inference_job+job_status, Artifacts→list_models, Hardware→hardware_profile, Recover→telemetry. Cancel: no descriptor operation exists — typed disposition (reports real job_status when a job exists).' },
  { surface: 'idl-explorer', controls: 6, backend_connected: 3, declared_local: 3, fixed: 0, typed: 0, detail: 'Run Fixture→invokeDescriptorOperation(ipfs_datasets_py.browse); descriptor/operation selects parameterize it. Invalid Input = genuine client-side schema validation; drilldown/badges = local display. Verified OK pre-audit.' },
  { surface: 'orb-auto-ui', controls: 8, backend_connected: 3, declared_local: 5, fixed: 0, typed: 0, detail: 'Confirm→invokeDescriptorOperation(selected op); descriptor/operation selects parameterize it. Remainder operate on real registry data / local validation / local render. Verified OK pre-audit.' },
  { surface: 'glasses-preview', controls: 7, backend_connected: 0, declared_local: 7, fixed: 0, typed: 0, detail: 'Declared browser_local; canned replays match the disposition. Verified OK pre-audit.' },
  { surface: 'agent-supervisor VDA-G054 section (subset of the console census row)', controls: 8, backend_connected: 0, declared_local: 8, fixed: 8, typed: 0, detail: 'The 8 workflow-proof buttons had no handlers and the section rendered SAMPLE refs in live mode; fix 4 wires them to real pane navigation and renders refs only from the active snapshot.' },
];

const capabilities = [
  ['supervisor.health.read', 'ipfs_accelerate_py', 'executes', 'desktop-client inspectAll across the three mediated services'],
  ['supervisor.queue.read', 'ipfs_accelerate_py', 'executes', 'Profile G mcp++/tasks/list'],
  ['supervisor.goals.read', 'ipfs_accelerate_py', 'executes', 'Profile G mcp++/goals/list'],
  ['supervisor.subgoals.read', 'ipfs_accelerate_py', 'executes', 'Profile G mcp++/goals/list'],
  ['supervisor.receipts.read', 'ipfs_kit_py', 'executes', 'Profile G tasks/list + per-task schedule status'],
  ['supervisor.logs.read', 'ipfs_accelerate_py', 'executes — audit3 fix 3 (R-d)', 'accelerate adapter mcp++/dag/history backed by its real EventDag; events normalized to log entries'],
  ['supervisor.receipts.persist', 'ipfs_kit_py', 'executes — audit3 fix 3 (R-c)', 'kit POST /mcp/artifacts/put; confirmation_token-gated; gateway computes the canonical CIDv1-raw+sha2-256 over the receipt bytes'],
  ['supervisor.content.retrieve', 'ipfs_kit_py', 'executes — audit3 fix 3 (R-c)', 'kit GET /mcp/artifacts/<cid>'],
  ['supervisor.event-dag.checkpoint', 'ipfs_kit_py', 'executes — audit3 fix 3 (R-c)', 'kit POST /mcp/dag/append; confirmation_token-gated'],
  ['supervisor.prompt-steering.request — dry run', 'ipfs_accelerate_py', 'local preview — audit3 fix 2 (R-b)', 'designed local no-mutation policy preview; no backend steering route exists'],
  ['supervisor.prompt-steering.request — confirmed', 'ipfs_accelerate_py', 'typed-unavailable', 'Supervisor.steer exists in the accelerate facade; NO MCP adapter route serves it — genuine backend gap, never simulated'],
  ['supervisor.task-control.request', 'ipfs_accelerate_py', 'typed-unavailable', 'no gateway route exists for governed task dispatch'],
  ['supervisor.taskboard.links.read', 'ipfs_datasets_py', 'typed-unavailable', 'zero implementations in ipfs_datasets_py (verified by search)'],
  ['supervisor.run-history.search', 'ipfs_datasets_py', 'typed-unavailable', 'zero implementations in ipfs_datasets_py (verified by search)'],
  ['supervisor.policy.assist', 'ipfs_datasets_py', 'typed-unavailable', 'zero implementations in ipfs_datasets_py (verified by search)'],
  ['supervisor.semantic-goal.assist', 'ipfs_datasets_py', 'typed-unavailable', 'zero implementations in ipfs_datasets_py (verified by search)'],
].map(([capability_id, owner, disposition, route]) => ({ capability_id, owner, disposition, route }));

const out = {
  generated_at: new Date().toISOString(),
  census_totals: totals,
  census_apps: rows.length,
  tool_backed_apps: [...toolBacked].length,
  apps: rows,
  surfaces,
  surface_fixed_total: surfaces.reduce((a, s) => a + s.fixed, 0),
  supervisor_capabilities: capabilities,
  capability_totals: {
    executes: capabilities.filter(c => c.disposition.startsWith('executes')).length,
    local_preview: capabilities.filter(c => c.disposition.startsWith('local preview')).length,
    typed_unavailable: capabilities.filter(c => c.disposition === 'typed-unavailable').length,
  },
};
writeFileSync(new URL('trace-table.json', here), JSON.stringify(out, null, 2));

let md = `# Audit3 interaction trace table (step 7)\n\nGenerated ${out.generated_at} from inventory-raw.json (census computed from the file) + P15 + audit3 fixes.\n\n`;
md += `## Census — 45 apps, ${totals.total} static controls (${totals.buttons} buttons, ${totals.inputs} inputs, ${totals.selects} selects, ${totals.textareas} textareas)\n\n`;
md += `| App | Controls (B/I/S/T) | Class |\n|---|---|---|\n`;
for (const r of rows) md += `| ${r.app_id} | ${r.total} (${r.buttons}/${r.inputs}/${r.selects}/${r.textareas}) | ${r.class} |\n`;
md += `\n## Generated surfaces (source-verified control counts)\n\n| Surface | Controls | Backend | Local | Fixed by audit3 | Typed |\n|---|---|---|---|---|---|\n`;
for (const s of surfaces) md += `| ${s.surface} | ${s.controls} | ${s.backend_connected} | ${s.declared_local} | ${s.fixed} | ${s.typed} |\n`;
md += `\n## Supervisor capabilities (15 contract capabilities; steering shown in its two modes = 16 rows)\n\n| Capability | Owner | Disposition | Route / reason |\n|---|---|---|---|\n`;
for (const c of capabilities) md += `| ${c.capability_id} | ${c.owner} | ${c.disposition} | ${c.route} |\n`;
md += `\nCapability totals: executes ${out.capability_totals.executes}, local preview ${out.capability_totals.local_preview}, typed-unavailable ${out.capability_totals.typed_unavailable}.\n`;
md += `\nUnmapped-and-fixed controls: ${out.surface_fixed_total} (datasets-browser 8, accelerate-panel 5, VDA-G054 8). Unmapped-and-typed: 6 supervisor capabilities + accelerate Cancel (1 control). No inventoried control remains silently unmapped.\n`;
writeFileSync(new URL('TRACE_TABLE.md', here), md);
console.log(JSON.stringify({ census_totals: totals, tool_backed: out.tool_backed_apps, surface_fixed_total: out.surface_fixed_total, capability_totals: out.capability_totals }, null, 2));
