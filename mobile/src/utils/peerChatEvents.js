export function getSelectConversationEvent() {
  return 'Select a recent conversation first';
}

export function getLoadedConversationsEvent() {
  return 'Loaded recent peer chat conversations';
}

export function getRefreshedAllPeerChatDiagnosticsEvent() {
  return 'Refreshed all peer chat diagnostics';
}

export function getLoadedChatHistoryEvent(conversationId) {
  return `Loaded chat history for ${conversationId}`;
}

export function getRefreshedOutboxStatusEvent(deliveryMode) {
  return `Refreshed backend outbox status (${deliveryMode})`;
}

export function getBackendSentChatEvent(priority, peerId) {
  return `Backend sent ${priority} chat to ${peerId}`;
}

export function getReleasedOutboxMessagesEvent(count) {
  return `Released ${count} leased backend outbox message(s)`;
}

export function getPromotedOutboxMessagesEvent(count) {
  return `Promoted ${count} backend outbox message(s) to urgent`;
}

export function getNoLeasedMessagesEvent() {
  return 'No leased backend outbox messages to release';
}

export function getNoHeldMessagesEvent() {
  return 'No policy-held backend outbox messages to promote';
}
