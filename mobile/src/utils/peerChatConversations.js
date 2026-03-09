export function normalizePeerChatConversations(response) {
  return response?.conversations || [];
}

export function selectNextConversation(conversations, currentConversation = null) {
  if (!conversations.length) {
    return null;
  }

  if (!currentConversation?.conversation_id) {
    return conversations[0];
  }

  return conversations.find(
    (conversation) => conversation.conversation_id === currentConversation.conversation_id
  ) || conversations[0];
}
