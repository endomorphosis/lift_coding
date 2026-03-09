jest.mock('@react-native-async-storage/async-storage', () => ({
  __esModule: true,
  default: {
    getItem: jest.fn(),
    setItem: jest.fn(),
  },
}));

import AsyncStorage from '@react-native-async-storage/async-storage';
import {
  ACTIVE_TASKS_STORAGE_KEY,
  DEFAULT_ACTIVE_TASKS_STATE,
  DEFAULT_NOTIFICATIONS_STATE,
  NOTIFICATIONS_STORAGE_KEY,
  getActiveTasksScreenState,
  getNotificationsScreenState,
  setActiveTasksScreenState,
  setNotificationsScreenState,
} from '../agentSurfaceStorage';

describe('agentSurfaceStorage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('returns defaults for active tasks when nothing is stored', async () => {
    AsyncStorage.getItem.mockResolvedValue(null);

    await expect(getActiveTasksScreenState()).resolves.toEqual(DEFAULT_ACTIVE_TASKS_STATE);
    expect(AsyncStorage.getItem).toHaveBeenCalledWith(ACTIVE_TASKS_STORAGE_KEY);
  });

  it('returns defaults for notifications when nothing is stored', async () => {
    AsyncStorage.getItem.mockResolvedValue(null);

    await expect(getNotificationsScreenState()).resolves.toEqual(DEFAULT_NOTIFICATIONS_STATE);
    expect(AsyncStorage.getItem).toHaveBeenCalledWith(NOTIFICATIONS_STORAGE_KEY);
  });

  it('sanitizes invalid stored filters', async () => {
    AsyncStorage.getItem.mockResolvedValue(JSON.stringify({ filter: 'bogus' }));

    await expect(getActiveTasksScreenState()).resolves.toEqual(DEFAULT_ACTIVE_TASKS_STATE);
    await expect(getNotificationsScreenState()).resolves.toEqual(DEFAULT_NOTIFICATIONS_STATE);
  });

  it('persists active task filter state', async () => {
    AsyncStorage.setItem.mockResolvedValue(undefined);

    await setActiveTasksScreenState({ filter: 'paused' });

    expect(AsyncStorage.setItem).toHaveBeenCalledWith(
      ACTIVE_TASKS_STORAGE_KEY,
      JSON.stringify({ filter: 'paused' })
    );
  });

  it('persists notifications filter state', async () => {
    AsyncStorage.setItem.mockResolvedValue(undefined);

    await setNotificationsScreenState({
      filter: 'active',
      lastAction: {
        actionId: 'rerun_workflow',
        message: 'Started a follow-on task.',
        status: 'completed',
        taskUpdate: { task_id: 'task-123' },
      },
    });

    expect(AsyncStorage.setItem).toHaveBeenCalledWith(
      NOTIFICATIONS_STORAGE_KEY,
      JSON.stringify({
        filter: 'active',
        lastAction: {
          actionId: 'rerun_workflow',
          message: 'Started a follow-on task.',
          status: 'completed',
          taskUpdate: { task_id: 'task-123' },
        },
      })
    );
  });

  it('restores and sanitizes persisted notifications lastAction state', async () => {
    AsyncStorage.getItem.mockResolvedValue(
      JSON.stringify({
        filter: 'tasks',
        lastAction: {
          actionId: 'rerun_workflow',
          message: 'Started a follow-on task.',
          status: 'completed',
          taskUpdate: { task_id: 'task-123', provider: 'ignored' },
        },
      })
    );

    await expect(getNotificationsScreenState()).resolves.toEqual({
      filter: 'tasks',
      lastAction: {
        actionId: 'rerun_workflow',
        message: 'Started a follow-on task.',
        status: 'completed',
        taskUpdate: { task_id: 'task-123' },
      },
    });
  });
});
