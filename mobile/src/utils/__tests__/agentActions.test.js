import { extractActionTaskUpdate } from '../agentActions';

describe('agentActions helpers', () => {
  it('extracts task metadata from structured action responses', () => {
    expect(
      extractActionTaskUpdate({
        follow_on_task: {
          task_id: 'task-123',
          state: 'running',
          provider: 'ipfs_accelerate_mcp',
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
    });
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
