// Steering-route gateway check: the three governance cases against the
// LIVE stack (accelerate adapter :3003 must be running with the steering
// bridge). 1) dry run -> typed capability_unavailable (engages the
// console's local preview; backend never called). 2) confirmed payload
// WITHOUT confirmation_token -> denied / confirmation_required at the
// gateway. 3) confirmed WITH token -> dispatched through the route; today
// the backend session reports its typed run-creation boundary, which must
// surface as server_unavailable carrying the real cause — never as
// capability_unavailable (which would mask it with the local preview).
// Terminal cause (2026-10-14 finisher): with the datasets pin advanced
// (source_screening imports), the plan-scope projection fixed, and the
// facade's scanner-identity translation fixed, run creation reaches the
// backend's real directory scanner, which refuses — by designed,
// test-pinned policy (NestedRepositoryError) — to scan the only activated
// composition's repository, because ipfs_accelerate_py's HEAD contains
// tracked submodules (first: docs/fastmcp). No receipt may be fabricated
// past this boundary; the verbatim cause is the honest end state.
import { MCPPlusPlusDesktopClient } from '/home/hatch/workspace/lift_coding/swissknife/web/js/core/mcp-plus-plus-desktop-client.js';

// In the browser the client uses vite-relative service URLs; in node the
// same code path is exercised with the adapters' absolute endpoints.
const client = new MCPPlusPlusDesktopClient({
  services: [
    { id: 'ipfs_accelerate_py', baseUrl: 'http://127.0.0.1:3003', mcpPath: '/mcp' },
    { id: 'ipfs_datasets_py', baseUrl: 'http://127.0.0.1:3002', mcpPath: '/mcp' },
    { id: 'ipfs_kit_py', baseUrl: 'http://127.0.0.1:8014', mcpPath: '/mcp' },
  ],
});
const gateway = client.createSupervisorGateway();

function invocation(payload) {
  return {
    capability_id: 'supervisor.prompt-steering.request',
    method: 'agent_supervisor.prompt_steering.request',
    owner: 'ipfs_accelerate_py',
    access: 'governed-write',
    policy_class: 'confirm',
    correlation_id: 'check-steering-route',
    payload,
  };
}

const base = {
  target_type: 'task',
  target_id: 'bafychecktask',
  prompt: 'Prioritize the steering verification task; keep all other scope unchanged.',
  expected_normalized_target: 'task:bafychecktask',
  client_request_id: 'check-steering-1',
};

const dry = await gateway.invoke(invocation({ ...base, dry_run: true }));
console.log('dry-run:    ', dry.state, '|', dry.reason);

const unconfirmed = await gateway.invoke(invocation({ ...base, dry_run: false }));
console.log('unconfirmed:', unconfirmed.state, '|', unconfirmed.reason, '| required_confirmation:', unconfirmed.required_confirmation);

const confirmed = await gateway.invoke(invocation({
  ...base,
  dry_run: false,
  confirmation_token: 'confirm-agent-supervisor:task:bafychecktask:check-steering-1',
}));
console.log('confirmed:  ', confirmed.state, '|', confirmed.reason, '|', confirmed.message);

let failed = false;
if (dry.state !== 'unavailable' || dry.reason !== 'capability_unavailable') { console.error('FAIL: dry-run must stay typed capability_unavailable'); failed = true; }
if (unconfirmed.state !== 'denied' || unconfirmed.reason !== 'confirmation_required') { console.error('FAIL: unconfirmed must be denied confirmation_required'); failed = true; }
if (confirmed.state === 'available') {
  console.log('confirmed executed with receipt:', confirmed.data?.receipt?.receipt_id, '| cid:', confirmed.data?.receipt?.cid);
} else if (confirmed.state !== 'unavailable' || confirmed.reason !== 'server_unavailable' || !/NestedRepositoryError/.test(confirmed.message || '') || !/docs\/fastmcp/.test(confirmed.message || '')) {
  console.error('FAIL: confirmed must dispatch and surface the real backend cause');
  failed = true;
}
if (failed) process.exit(1);
console.log('GATEWAY CHECK PASSED');
