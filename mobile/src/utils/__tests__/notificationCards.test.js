import {
  buildNotificationPreview,
  getNotificationTaskState,
  isActiveTaskNotification,
  mergeNotificationTaskDetail,
} from '../notificationCards';

describe('notificationCards helpers', () => {
  it('detects active task notifications from metadata and event type', () => {
    expect(
      isActiveTaskNotification(
        buildNotificationPreview({
          id: 'notif-1',
          event_type: 'task_paused',
          metadata: { task_id: 'task-123' },
        })
      )
    ).toBe(true);
    expect(getNotificationTaskState({ event_type: 'task_resumed', metadata: { task_id: 'task-123' } })).toBe(
      'running'
    );
  });

  it('merges live task detail into notification metadata', () => {
    const merged = mergeNotificationTaskDetail(
      buildNotificationPreview({
        id: 'notif-2',
        event_type: 'task_running',
        metadata: { task_id: 'task-456', state: 'running' },
        card: {
          subtitle: 'Task task-456 • running',
        },
      }),
      {
        id: 'task-456',
        state: 'completed',
        result_preview: 'Expanded legal query',
        result_output: { message: 'Expanded legal query' },
        provider: 'ipfs_datasets_mcp',
        instruction: 'find legal datasets',
      }
    );

    expect(merged.metadata.state).toBe('completed');
    expect(merged.metadata.result_preview).toBe('Expanded legal query');
    expect(merged.metadata.result_output.message).toBe('Expanded legal query');
    expect(merged.card.subtitle).toBe('Task task-456 • completed');
  });

  it('merges result envelope and follow-up actions from task detail', () => {
    const merged = mergeNotificationTaskDetail(
      buildNotificationPreview({
        id: 'notif-3',
        event_type: 'task_running',
        metadata: { task_id: 'task-789', state: 'running' },
      }),
      {
        id: 'task-789',
        state: 'completed',
        result_envelope: {
          summary: 'Pinned bafy123.',
          artifact_refs: { result_cid: 'bafy123' },
        },
        follow_up_actions: [{ id: 'read_cid', label: 'Read CID', phrase: 'read the cid' }],
      }
    );

    expect(merged.metadata.result_envelope.summary).toBe('Pinned bafy123.');
    expect(merged.metadata.follow_up_actions[0].id).toBe('read_cid');
  });
});
