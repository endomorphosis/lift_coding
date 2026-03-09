import AsyncStorage from '@react-native-async-storage/async-storage';

export const ACTIVE_TASKS_STORAGE_KEY = '@handsfree_active_tasks_state';
export const NOTIFICATIONS_STORAGE_KEY = '@handsfree_notifications_state';

export const DEFAULT_ACTIVE_TASKS_STATE = {
  filter: 'all',
};

export const DEFAULT_NOTIFICATIONS_STATE = {
  filter: 'all',
  lastAction: null,
};

function sanitizeFilter(value, allowed, fallback) {
  return typeof value === 'string' && allowed.has(value) ? value : fallback;
}

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

export async function getActiveTasksScreenState() {
  try {
    const raw = await AsyncStorage.getItem(ACTIVE_TASKS_STORAGE_KEY);
    if (!raw) {
      return { ...DEFAULT_ACTIVE_TASKS_STATE };
    }
    const parsed = JSON.parse(raw);
    return {
      filter: sanitizeFilter(
        parsed?.filter,
        new Set(['all', 'running', 'paused', 'created']),
        DEFAULT_ACTIVE_TASKS_STATE.filter
      ),
    };
  } catch (error) {
    console.error('Failed to load active tasks screen state from storage:', error);
    return { ...DEFAULT_ACTIVE_TASKS_STATE };
  }
}

export async function setActiveTasksScreenState(state) {
  try {
    await AsyncStorage.setItem(
      ACTIVE_TASKS_STORAGE_KEY,
      JSON.stringify({
        filter: sanitizeFilter(
          state?.filter,
          new Set(['all', 'running', 'paused', 'created']),
          DEFAULT_ACTIVE_TASKS_STATE.filter
        ),
      })
    );
  } catch (error) {
    console.error('Failed to save active tasks screen state to storage:', error);
    throw error;
  }
}

export async function getNotificationsScreenState() {
  try {
    const raw = await AsyncStorage.getItem(NOTIFICATIONS_STORAGE_KEY);
    if (!raw) {
      return { ...DEFAULT_NOTIFICATIONS_STATE };
    }
    const parsed = JSON.parse(raw);
    return {
      filter: sanitizeFilter(
        parsed?.filter,
        new Set(['all', 'tasks', 'active']),
        DEFAULT_NOTIFICATIONS_STATE.filter
      ),
      lastAction: sanitizeLastAction(parsed?.lastAction),
    };
  } catch (error) {
    console.error('Failed to load notifications screen state from storage:', error);
    return { ...DEFAULT_NOTIFICATIONS_STATE };
  }
}

export async function setNotificationsScreenState(state) {
  try {
    await AsyncStorage.setItem(
      NOTIFICATIONS_STORAGE_KEY,
      JSON.stringify({
        filter: sanitizeFilter(
          state?.filter,
          new Set(['all', 'tasks', 'active']),
          DEFAULT_NOTIFICATIONS_STATE.filter
        ),
        lastAction: sanitizeLastAction(state?.lastAction),
      })
    );
  } catch (error) {
    console.error('Failed to save notifications screen state to storage:', error);
    throw error;
  }
}
