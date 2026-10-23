// Fix-4 check: the VDA-G054 section must not render SAMPLE checkpoint /
// receipt refs against a live snapshot, and its actions must navigate to
// the real panes. (DOM click wiring is exercised in the browser drive.)
import { AgentSupervisorApp } from '/home/hatch/workspace/lift_coding/swissknife/web/js/apps/agent-supervisor.js';

const liveSnapshot = {
  health: { status: 'available', active_goal_count: 0, queued_task_count: 0, running_task_count: 0, backends: [] },
  goals: [], subgoals: [], queue: [], taskboardLinks: [], logs: [], receipts: [], runHistory: [],
  policyAssist: null, semanticGoalAssist: null,
};

const app = new AgentSupervisorApp(null, {});
app.state.snapshot = liveSnapshot;
app.state.status = 'ready';
app.state.transportMode = 'live';
const liveHtml = app.renderShell();
const leakedRefs = ['bafyagentg054', 'receipt:agent-supervisor:g054'].filter(s => liveHtml.includes(s));
console.log('live-mode SAMPLE refs leaked:', leakedRefs.length ? leakedRefs : 'none');
const buttonCount = (liveHtml.match(/data-svd-workflow-action=/g) || []).length;
console.log('workflow action buttons rendered:', buttonCount);

app.showEmptyState(); // fixture mode keeps its own honest state; snapshot replaced
app.state.snapshot = JSON.parse(JSON.stringify(liveSnapshot));
app.state.status = 'ready';
app.handleWorkflowProofAction('open-receipt-visibility');
console.log('after open-receipt-visibility activeTab:', app.state.activeTab);
app.handleWorkflowProofAction('preview-steering-prompt');
console.log('after preview-steering-prompt activeTab:', app.state.activeTab);
app.handleWorkflowProofAction('inspect-kda-evidence');
console.log('after inspect-kda-evidence activeTab:', app.state.activeTab);

if (leakedRefs.length || buttonCount !== 8) { console.error('FAIL refs/buttons'); process.exit(1); }
if (app.state.activeTab !== 'health') { console.error('FAIL navigation'); process.exit(1); }
console.log('FIX4 CHECK PASSED');
