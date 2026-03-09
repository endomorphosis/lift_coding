import {
  isTerminalTaskState,
  shouldClearLastActionFromNotifications,
  shouldClearLastActionFromResults,
  shouldClearLastActionFromTaskDetail,
} from '../lastActionState';

describe('lastActionState helpers', () => {
  it('detects terminal task states', () => {
    expect(isTerminalTaskState('completed')).toBe(true);
    expect(isTerminalTaskState('failed')).toBe(true);
    expect(isTerminalTaskState('running')).toBe(false);
  });

  it('clears result lastAction when the spawned task is terminal in the result feed', () => {
    expect(
      shouldClearLastActionFromResults(
        { taskUpdate: { task_id: 'task-123' } },
        [{ task_id: 'task-123', state: 'completed' }]
      )
    ).toBe(true);
    expect(
      shouldClearLastActionFromResults(
        { taskUpdate: { task_id: 'task-123' } },
        [{ task_id: 'task-123', state: 'running' }]
      )
    ).toBe(false);
  });

  it('clears notification lastAction when the linked notification is terminal', () => {
    expect(
      shouldClearLastActionFromNotifications(
        { taskUpdate: { task_id: 'task-123' } },
        [{ metadata: { task_id: 'task-123', state: 'completed' } }]
      )
    ).toBe(true);
    expect(
      shouldClearLastActionFromNotifications(
        { taskUpdate: { task_id: 'task-123' } },
        [{ metadata: { task_id: 'task-123', state: 'running' } }]
      )
    ).toBe(false);
  });

  it('clears task-detail lastAction only for a different spawned task in terminal state', () => {
    expect(
      shouldClearLastActionFromTaskDetail(
        { taskUpdate: { task_id: 'task-456' } },
        'task-123',
        { state: 'failed' }
      )
    ).toBe(true);
    expect(
      shouldClearLastActionFromTaskDetail(
        { taskUpdate: { task_id: 'task-123' } },
        'task-123',
        { state: 'completed' }
      )
    ).toBe(false);
  });
});
