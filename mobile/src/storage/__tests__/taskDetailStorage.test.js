jest.mock('@react-native-async-storage/async-storage', () => ({
  __esModule: true,
  default: {
    getItem: jest.fn(),
    setItem: jest.fn(),
  },
}));

import AsyncStorage from '@react-native-async-storage/async-storage';
import {
  DEFAULT_TASK_DETAIL_STATE,
  getTaskDetailScreenState,
  setTaskDetailScreenState,
  taskDetailStorageKey,
} from '../taskDetailStorage';

describe('taskDetailStorage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('returns defaults when nothing is stored', async () => {
    AsyncStorage.getItem.mockResolvedValue(null);

    await expect(getTaskDetailScreenState('task-123')).resolves.toEqual(DEFAULT_TASK_DETAIL_STATE);
    expect(AsyncStorage.getItem).toHaveBeenCalledWith(taskDetailStorageKey('task-123'));
  });

  it('persists sanitized lastAction state per task id', async () => {
    AsyncStorage.setItem.mockResolvedValue(undefined);

    await setTaskDetailScreenState('task-123', {
      lastAction: {
        actionId: 'rerun_workflow',
        message: 'Started a follow-on task.',
        status: 'completed',
        taskUpdate: { task_id: 'task-456', provider: 'ignored' },
      },
    });

    expect(AsyncStorage.setItem).toHaveBeenCalledWith(
      taskDetailStorageKey('task-123'),
      JSON.stringify({
        lastAction: {
          actionId: 'rerun_workflow',
          message: 'Started a follow-on task.',
          status: 'completed',
          taskUpdate: { task_id: 'task-456' },
        },
      })
    );
  });

  it('restores sanitized lastAction state per task id', async () => {
    AsyncStorage.getItem.mockResolvedValue(
      JSON.stringify({
        lastAction: {
          actionId: 'rerun_workflow',
          message: 'Started a follow-on task.',
          status: 'completed',
          taskUpdate: { task_id: 'task-456', provider: 'ignored' },
        },
      })
    );

    await expect(getTaskDetailScreenState('task-123')).resolves.toEqual({
      lastAction: {
        actionId: 'rerun_workflow',
        message: 'Started a follow-on task.',
        status: 'completed',
        taskUpdate: { task_id: 'task-456' },
      },
    });
  });
});
