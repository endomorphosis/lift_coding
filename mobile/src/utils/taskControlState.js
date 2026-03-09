import { buildNotificationPreview, mergeNotificationTaskDetail } from './notificationCards';

export function applyTaskControlResponse(task, response) {
  if (!task || !response?.task_id || task.id !== response.task_id) {
    return task;
  }

  return {
    ...task,
    state: response.state || task.state,
    updated_at: response.updated_at || task.updated_at || new Date().toISOString(),
  };
}

export function applyNotificationTaskControlResponse(notification, response) {
  if (!notification || !response?.task_id) {
    return notification;
  }

  const taskId = notification?.metadata?.task_id || notification?.card?.task_id;
  if (taskId !== response.task_id) {
    return notification;
  }

  return mergeNotificationTaskDetail(
    buildNotificationPreview(notification),
    {
      id: response.task_id,
      state: response.state,
      updated_at: response.updated_at || null,
    }
  );
}
