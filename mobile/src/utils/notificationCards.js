export function buildNotificationPreview(notification) {
  if (!notification) return null;

  return {
    ...notification,
    title:
      notification.title ||
      notification.card?.title ||
      notification.message ||
      'Notification',
    body:
      notification.body ||
      notification.card?.subtitle ||
      notification.message ||
      '',
    timestamp: notification.timestamp || notification.created_at || new Date().toISOString(),
  };
}

export function getNotificationTaskState(notification) {
  const state = notification?.metadata?.state;
  if (state === 'paused') {
    return 'needs_input';
  }
  if (state === 'resumed') {
    return 'running';
  }
  if (typeof state === 'string' && state) {
    return state;
  }

  const eventType = notification?.event_type || '';
  if (eventType === 'task_paused') {
    return 'needs_input';
  }
  if (eventType === 'task_resumed' || eventType === 'task_running') {
    return 'running';
  }
  if (eventType === 'task_created') {
    return 'created';
  }
  if (eventType === 'task_cancelled' || eventType === 'task_failed') {
    return 'failed';
  }
  if (eventType === 'task_completed') {
    return 'completed';
  }
  return null;
}

export function isActiveTaskNotification(notification) {
  const state = getNotificationTaskState(notification);
  return (
    Boolean(notification?.metadata?.task_id || notification?.card?.task_id) &&
    ['created', 'running', 'needs_input'].includes(state)
  );
}

export function mergeNotificationTaskDetail(notification, taskDetail) {
  if (!notification || !taskDetail?.id) {
    return notification;
  }

  const nextState = taskDetail.state;
  const nextMetadata = {
    ...(notification.metadata || {}),
    task_id: taskDetail.id,
    state: nextState,
  };

  if (typeof taskDetail.result_preview === 'string' && taskDetail.result_preview) {
    nextMetadata.result_preview = taskDetail.result_preview;
  }
  if (taskDetail.result_output !== undefined) {
    nextMetadata.result_output = taskDetail.result_output;
  }
  if (taskDetail.result_envelope && typeof taskDetail.result_envelope === 'object') {
    nextMetadata.result_envelope = taskDetail.result_envelope;
  }
  if (Array.isArray(taskDetail.follow_up_actions)) {
    nextMetadata.follow_up_actions = taskDetail.follow_up_actions;
  }
  if (typeof taskDetail.provider === 'string' && taskDetail.provider) {
    nextMetadata.provider = taskDetail.provider;
  }
  if (typeof taskDetail.provider_label === 'string' && taskDetail.provider_label) {
    nextMetadata.provider_label = taskDetail.provider_label;
  }
  if (typeof taskDetail.instruction === 'string' && taskDetail.instruction) {
    nextMetadata.instruction = taskDetail.instruction;
  }
  if (typeof taskDetail.updated_at === 'string' && taskDetail.updated_at) {
    nextMetadata.updated_at = taskDetail.updated_at;
  }

  return buildNotificationPreview({
    ...notification,
    timestamp: taskDetail.updated_at || notification.timestamp || notification.created_at,
    metadata: nextMetadata,
    card: notification.card
      ? {
          ...notification.card,
          subtitle: notification.card.subtitle
            ? notification.card.subtitle.replace(/\s[•-]\s.+$/, ` • ${nextState}`)
            : notification.card.subtitle,
        }
      : notification.card,
  });
}
