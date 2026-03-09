import AsyncStorage from '@react-native-async-storage/async-storage';

export function taskDetailStorageKey(taskId) {
  return `@handsfree_task_detail_state:${taskId || 'unknown'}`;
}

export const DEFAULT_TASK_DETAIL_STATE = {
  lastAction: null,
};

function sanitizeLastAction(value) {
  if (!value || typeof value !== 'object') {
    return null;
  }

  const actionId = typeof value.actionId === 'string' ? value.actionId : null;
  const message = typeof value.message === 'string' ? value.message : null;
  const status = typeof value.status === 'string' ? value.status : null;
  const taskId =
    typeof value.taskUpdate?.task_id === 'string' ? value.taskUpdate.task_id : null;

  if (!message) {
    return null;
  }

  return {
    actionId,
    message,
    status,
    taskUpdate: taskId ? { task_id: taskId } : null,
  };
}

export async function getTaskDetailScreenState(taskId) {
  if (!taskId) {
    return { ...DEFAULT_TASK_DETAIL_STATE };
  }

  try {
    const raw = await AsyncStorage.getItem(taskDetailStorageKey(taskId));
    if (!raw) {
      return { ...DEFAULT_TASK_DETAIL_STATE };
    }

    const parsed = JSON.parse(raw);
    return {
      lastAction: sanitizeLastAction(parsed?.lastAction),
    };
  } catch (error) {
    console.error('Failed to load task detail screen state from storage:', error);
    return { ...DEFAULT_TASK_DETAIL_STATE };
  }
}

export async function setTaskDetailScreenState(taskId, state) {
  if (!taskId) {
    return;
  }

  try {
    await AsyncStorage.setItem(
      taskDetailStorageKey(taskId),
      JSON.stringify({
        lastAction: sanitizeLastAction(state?.lastAction),
      })
    );
  } catch (error) {
    console.error('Failed to save task detail screen state to storage:', error);
    throw error;
  }
}
