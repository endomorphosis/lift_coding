export function normalizePeerChatOutboxSummary(response) {
  if (!response) {
    return null;
  }

  return {
    queued_total: response.queued_total ?? 0,
    queued_urgent: response.queued_urgent ?? 0,
    queued_normal: response.queued_normal ?? 0,
    deliverable_now: response.deliverable_now ?? 0,
    held_now: response.held_now ?? 0,
    delivery_mode: response.delivery_mode || 'unknown',
    preview_messages: response.preview_messages || [],
  };
}

export function selectNextOutboxMessageId(summary, currentMessageId = null) {
  const previewMessages = summary?.preview_messages || [];
  if (!previewMessages.length) {
    return null;
  }
  if (currentMessageId && previewMessages.some((message) => message.outbox_message_id === currentMessageId)) {
    return currentMessageId;
  }
  return previewMessages[0].outbox_message_id;
}

export function getSelectedOutboxPreview(summary, selectedMessageId = null) {
  if (!summary?.preview_messages?.length || !selectedMessageId) {
    return null;
  }

  return summary.preview_messages.find(
    (message) => message.outbox_message_id === selectedMessageId
  ) || null;
}

export function getOutboxMessageIdsByState(summary, state) {
  return (summary?.preview_messages || [])
    .filter((message) => message.state === state)
    .map((message) => message.outbox_message_id);
}
