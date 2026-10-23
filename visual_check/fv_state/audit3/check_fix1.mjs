// Fix-1 check: in live mode, capabilities the gateway does not serve must
// contribute EMPTY lists — never SAMPLE fixtures. Full SAMPLE renders only
// when no capability is available at all.
import { AgentSupervisorApp } from '/home/hatch/workspace/lift_coding/swissknife/web/js/apps/agent-supervisor.js';

const partialGateway = {
  invoke: async (invocation) => {
    if (invocation.capability_id === 'supervisor.queue.read') {
      return {
        state: 'available', capability_id: invocation.capability_id, owner: invocation.owner,
        correlation_id: invocation.correlation_id,
        data: [{ task_id: 'LIVE-1', title: 'Live task', status: 'ready', goal_id: 'G1', subgoal_id: 'SG1', dependencies: [] }],
      };
    }
    return {
      state: 'unavailable', capability_id: invocation.capability_id, owner: invocation.owner,
      reason: 'capability_unavailable', message: 'not mapped', correlation_id: invocation.correlation_id,
    };
  },
};

const app = new AgentSupervisorApp(null, { gateway: partialGateway });
const live = await app.readLiveSnapshot();
console.log('ok:', live.ok);
console.log('queue:', JSON.stringify(live.snapshot.queue.map(t => t.task_id)));
console.log('taskboardLinks:', live.snapshot.taskboardLinks.length, 'logs:', live.snapshot.logs.length,
  'runHistory:', live.snapshot.runHistory.length, 'goals:', live.snapshot.goals.length,
  'receipts:', live.snapshot.receipts.length);
console.log('health status:', live.snapshot.health.status);
console.log('errors:', live.errors.map(e => e.capability_id).join(','));

const leaked = ['taskboardLinks', 'logs', 'runHistory', 'goals', 'subgoals', 'receipts']
  .filter(key => live.snapshot[key].length !== 0);
if (!live.ok || live.snapshot.queue.length !== 1 || leaked.length) {
  console.error('FAIL: SAMPLE leak or missing live data', leaked);
  process.exit(1);
}
console.log('FIX1 CHECK PASSED');
