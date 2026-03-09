import {
  applyNotificationTaskControlResponse,
  applyTaskControlResponse,
} from '../taskControlState';

describe('taskControlState helpers', () => {
  it('applies lifecycle state and updated_at to a task detail object', () => {
    const updated = applyTaskControlResponse(
      {
        id: 'task-123',
        state: 'running',
        updated_at: '2026-03-09T18:00:00Z',
      },
      {
        task_id: 'task-123',
        state: 'needs_input',
        updated_at: '2026-03-09T18:30:00Z',
        message: 'Task paused successfully',
      }
    );

    expect(updated.state).toBe('needs_input');
    expect(updated.updated_at).toBe('2026-03-09T18:30:00Z');
  });

  it('applies lifecycle state and updated_at to a notification preview', () => {
    const updated = applyNotificationTaskControlResponse(
      {
        id: 'notif-123',
        event_type: 'task_running',
        timestamp: '2026-03-09T18:00:00Z',
        metadata: {
          task_id: 'task-123',
          state: 'running',
        },
        card: {
          title: 'Task running',
          subtitle: 'Task task-123 • running',
          lines: ['Working...'],
        },
      },
      {
        task_id: 'task-123',
        state: 'needs_input',
        updated_at: '2026-03-09T18:30:00Z',
        message: 'Task paused successfully',
      }
    );

    expect(updated.metadata.state).toBe('needs_input');
    expect(updated.metadata.updated_at).toBe('2026-03-09T18:30:00Z');
    expect(updated.timestamp).toBe('2026-03-09T18:30:00Z');
    expect(updated.card.subtitle).toBe('Task task-123 • needs_input');
  });
});
