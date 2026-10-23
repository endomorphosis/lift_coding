/**
 * Sharpened-requirement audit, steps 1/2/4 (mediator side):
 * for each of the 38 tool_backed apps, execute representative mediated
 * invocations through POST /mcp/tools/call on the live vite mediator,
 * constructing calls EXACTLY as the apps' own live-tool-gateway panel
 * does (web/js/live-tool-gateway.js invokeControl):
 *  - read controls: policy allow / consent not_required / dry_run false
 *  - governed (mutating) controls: the panel's governed shape
 *    (require_confirmation + consent granted + dry_run true — the desktop
 *    only ever rehearses mutating controls)
 *  - governed controls additionally get a NEGATIVE probe: dry_run false +
 *    consent not_required must be denied `confirmation_required` by the
 *    mediator before any adapter is touched.
 *  - controls declaring libp2p additionally get the same call with
 *    transport 'libp2p' (what the panel's replay-override produces),
 *    which must come back with an application_transport_observation of
 *    transport 'libp2p' and ucan_did_verified true.
 * Results: audit2/per-app-invocations.json (+ stdout summary).
 */
import { readFileSync, writeFileSync } from 'node:fs';

const BASE = 'http://127.0.0.1:3001';
const catalog = JSON.parse(readFileSync(new URL('./bindings.json', import.meta.url), 'utf8'));
const controls = catalog.controls;

const byApp = new Map();
for (const control of controls) {
  if (!byApp.has(control.app_id)) byApp.set(control.app_id, []);
  byApp.get(control.app_id).push(control);
}

let correlationCounter = 0;
function buildCall(control, { transport, governedShape, negativeProbe }) {
  const governed = control.mutates_remote_state === true;
  const dryRun = negativeProbe ? false : governedShape ? governed : false;
  const correlationId = `audit2:${control.binding_id}:${Date.now()}:${correlationCounter++}`;
  const payload = control.safe_payload ??
    (dryRun
      ? { dry_run: true, scope: control.capability_id, limit: 1 }
      : { scope: control.capability_id, limit: 1, cursor: 'desktop-read-only' });
  const policy = negativeProbe
    ? {
        decision_id: `audit2-policy:${control.binding_id}`,
        outcome: 'allow',
        reason: 'Negative probe: mutating control without consent must be denied by the mediator.',
        consent: 'not_required',
        dry_run: false,
      }
    : governed
      ? {
          decision_id: `desktop-policy:${control.binding_id}`,
          outcome: 'require_confirmation',
          reason: 'The governed desktop request is explicitly confirmed and executes only as a no-side-effect dry run.',
          consent: 'granted',
          dry_run: true,
        }
      : {
          decision_id: `desktop-policy:${control.binding_id}`,
          outcome: 'allow',
          reason: 'Narrow non-mutating desktop read request.',
          consent: 'not_required',
          dry_run: false,
        };
  return {
    protocol: 'swissknife.all-app-tool-gateway.v1',
    route: '/mcp/tools/call',
    binding_id: control.binding_id,
    app_id: control.app_id,
    intent_id: control.intent_id,
    owner: control.owner,
    tool_id: control.selected_tool_id,
    transport,
    correlation_id: correlationId,
    input: { correlation_id: correlationId, payload, policy },
    receipt_required: true,
  };
}

async function fire(call) {
  const started = Date.now();
  try {
    const response = await fetch(`${BASE}/mcp/tools/call`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(call),
      signal: AbortSignal.timeout(180_000),
    });
    const body = await response.json();
    return {
      http_status: response.status,
      outcome: body.outcome ?? null,
      ok: body.ok ?? null,
      transport: body.transport ?? null,
      receipt_id: body.receipt?.receipt_id ?? null,
      event_ref: body.receipt?.event_dag_refs?.[0] ?? null,
      persistence: body.receipt?.persistence?.status ?? null,
      observation: body.result?.application_transport_observation ?? null,
      error: body.result?.error ?? body.error ?? null,
      ms: Date.now() - started,
    };
  } catch (error) {
    return { http_status: 0, outcome: 'fetch_failed', error: String(error?.message ?? error), ms: Date.now() - started };
  }
}

const results = [];
for (const [appId, appControls] of byApp) {
  // Representative: prefer a non-mutating available control; else the first.
  const representative =
    appControls.find(c => c.status === 'available' && c.mutates_remote_state !== true) ??
    appControls.find(c => c.status === 'available') ??
    appControls[0];
  const entry = {
    app_id: appId,
    controls_total: appControls.length,
    controls_available: appControls.filter(c => c.status === 'available').length,
    mutating_controls: appControls.filter(c => c.mutates_remote_state === true).length,
    libp2p_controls: appControls.filter(c => c.transports?.includes('libp2p')).map(c => c.binding_id),
    representative: {
      binding_id: representative.binding_id,
      owner: representative.owner,
      tool_id: representative.selected_tool_id,
      mutates_remote_state: representative.mutates_remote_state === true,
      confirmation_required: representative.confirmation_required === true,
      transports: representative.transports,
    },
    http_call: null,
    libp2p_call: null,
    negative_probe: null,
  };
  entry.http_call = await fire(buildCall(representative, {
    transport: representative.transport ?? 'http',
    governedShape: true,
    negativeProbe: false,
  }));
  const libp2pControl =
    appControls.find(c => c.status === 'available' && c.transports?.includes('libp2p')) ?? null;
  if (libp2pControl) {
    entry.libp2p_control = libp2pControl.binding_id;
    entry.libp2p_call = await fire(buildCall(libp2pControl, {
      transport: 'libp2p',
      governedShape: true,
      negativeProbe: false,
    }));
  }
  if (representative.mutates_remote_state === true) {
    entry.negative_probe = await fire(buildCall(representative, {
      transport: representative.transport ?? 'http',
      governedShape: false,
      negativeProbe: true,
    }));
  }
  results.push(entry);
  console.log(`${appId}: http=${entry.http_call.outcome} libp2p=${entry.libp2p_call?.outcome ?? '-'} neg=${entry.negative_probe?.outcome ?? '-'}`);
}

writeFileSync(new URL('./per-app-invocations.json', import.meta.url), `${JSON.stringify(results, null, 2)}\n`);
const executed = results.filter(r => r.http_call.outcome === 'executed').length;
console.log(`APPS ${results.length} | http executed ${executed} | libp2p executed ${results.filter(r => r.libp2p_call?.outcome === 'executed').length} | negative probes denied ${results.filter(r => r.negative_probe?.outcome === 'denied').length}/${results.filter(r => r.negative_probe).length}`);
