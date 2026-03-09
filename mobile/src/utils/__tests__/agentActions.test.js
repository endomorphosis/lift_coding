import { buildLastActionLines, extractActionTaskUpdate } from '../agentActions';

describe('agentActions helpers', () => {
  it('extracts task metadata from structured action responses', () => {
    expect(
      extractActionTaskUpdate({
        follow_on_task: {
          task_id: 'task-123',
          state: 'running',
          provider: 'ipfs_accelerate_mcp',
          provider_label: 'IPFS Accelerate',
          capability: 'agentic_fetch',
          summary: 'IPFS Accelerate agentic fetch running.',
        },
        intent: {
          entities: {
            task_id: 'task-123',
          },
        },
        debug: {
          tool_calls: [
            {
              task_id: 'task-123',
              state: 'running',
              provider: 'ipfs_accelerate_mcp',
            },
          ],
        },
      })
    ).toEqual({
      task_id: 'task-123',
      state: 'running',
      provider: 'ipfs_accelerate_mcp',
      provider_label: 'IPFS Accelerate',
      capability: 'agentic_fetch',
      summary: 'IPFS Accelerate agentic fetch running.',
    });
  });

  it('builds last action lines with follow-on summary when present', () => {
    expect(
      buildLastActionLines({
        message: 'Workflow rerun requested.',
        taskUpdate: {
          task_id: 'task-123',
          summary: 'IPFS Accelerate agentic fetch running.',
        },
      })
    ).toEqual([
      'Workflow rerun requested.',
      'IPFS Accelerate agentic fetch running.',
    ]);
  });

  it('returns null when the action response has no task context', () => {
    expect(
      extractActionTaskUpdate({
        intent: { entities: {} },
        debug: { tool_calls: [] },
      })
    ).toBeNull();
  });
});
