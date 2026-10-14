// Fix-2 check: steering dry-run falls back to the local preview ONLY for
// dry runs; confirmed submissions keep the gateway's typed error.
import { AgentSupervisorApp } from '/home/hatch/workspace/lift_coding/swissknife/web/js/apps/agent-supervisor.js';

const typedGateway = {
  invoke: async (invocation) => ({
    state: 'unavailable',
    capability_id: invocation.capability_id,
    owner: invocation.owner,
    reason: 'capability_unavailable',
    message: 'The requested Supervisor gateway capability is not mapped.',
    correlation_id: invocation.correlation_id,
  }),
};

const app = new AgentSupervisorApp(null, { gateway: typedGateway });

const dryRun = await app.invokeCapability('supervisor.prompt-steering.request', {
  target_type: 'task', target_id: 'SWR-105-1', prompt: 'Preview only, no mutation.', dry_run: true,
  client_request_id: 'check-fix2-dry',
});
console.log('dry-run state:', dryRun.state, '| accepted:', dryRun.data?.accepted, '| dry_run:', dryRun.data?.dry_run, '| receipt:', dryRun.data?.receipt?.receipt_id);

const confirmed = await app.invokeCapability('supervisor.prompt-steering.request', {
  target_type: 'task', target_id: 'SWR-105-1', prompt: 'Real submission.', dry_run: false,
  confirmation_token: 'confirm-agent-supervisor:task:SWR-105-1:check-fix2',
  client_request_id: 'check-fix2-confirmed',
});
console.log('confirmed state:', confirmed.state, '| reason:', confirmed.reason);

if (dryRun.state !== 'available' || dryRun.data?.accepted !== true || dryRun.data?.dry_run !== true) {
  console.error('FAIL: dry-run did not produce the local preview');
  process.exit(1);
}
if (confirmed.state !== 'unavailable' || confirmed.reason !== 'capability_unavailable') {
  console.error('FAIL: confirmed submission did not keep the typed error');
  process.exit(1);
}
console.log('FIX2 CHECK PASSED');
