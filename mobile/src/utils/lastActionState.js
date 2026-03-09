import { getNotificationTaskState } from './notificationCards';

export function isTerminalTaskState(state) {
  return state === 'completed' || state === 'failed';
}

export function shouldClearLastActionFromResults(lastAction, results = []) {
  const followOnTaskId = lastAction?.taskUpdate?.task_id;
  if (!followOnTaskId || !Array.isArray(results)) {
    return false;
  }

  const matchingResult = results.find((item) => item?.task_id === followOnTaskId);
  return Boolean(matchingResult && isTerminalTaskState(matchingResult.state));
}

export function shouldClearLastActionFromNotifications(lastAction, notifications = []) {
  const followOnTaskId = lastAction?.taskUpdate?.task_id;
  if (!followOnTaskId || !Array.isArray(notifications)) {
    return false;
  }

  const matchingNotification = notifications.find((item) => {
    const taskId = item?.metadata?.task_id || item?.card?.task_id;
    return taskId === followOnTaskId;
  });
  if (!matchingNotification) {
    return false;
  }

  return isTerminalTaskState(getNotificationTaskState(matchingNotification));
}

export function shouldClearLastActionFromTaskDetail(lastAction, taskId, spawnedTaskDetail) {
  const followOnTaskId = lastAction?.taskUpdate?.task_id;
  if (!followOnTaskId || followOnTaskId === taskId) {
    return false;
  }

  return isTerminalTaskState(spawnedTaskDetail?.state);
}
