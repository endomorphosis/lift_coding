import React from 'react';
import { StyleSheet, Text, TouchableOpacity, View } from 'react-native';

import PeerChatOutboxPanel from './PeerChatOutboxPanel';

export default function PeerChatDiagnosticsPanel({
  onRefreshAll,
  isRefreshingAll,
  isLoadingPeerChatHistory,
  onLoadPeerChatHistory,
  isLoadingPeerChatConversations,
  onLoadRecentPeerChatConversations,
  isSendingPeerChatViaBackend,
  onSendNormalPeerChat,
  onSendUrgentPeerChat,
  isFetchingPeerChatOutbox,
  onRefreshOutboxStatus,
  onReleaseLeasedMessages,
  onPromoteHeldMessages,
  onFetchPeerChatOutbox,
  headerText,
  peerChatOutboxSummary,
  selectedOutboxPreview,
  onSelectOutboxMessage,
  onReleaseOutboxMessage,
  onPromoteOutboxMessage,
  peerChatHistory,
  peerChatConversations,
  selectedConversationId,
  onSelectConversation,
  transportSessions,
  isLoadingTransportSessions,
  isClearingTransportSession,
  onLoadTransportSessions,
  onClearTransportSession,
}) {
  return (
    <>
      <View style={styles.container}>
        <Text style={styles.title}>Peer Chat Diagnostics</Text>
        <Text style={styles.subtext}>
          {headerText || 'Inspect normalized chat history, conversation summaries, and relay-queue behavior.'}
        </Text>
        {onRefreshAll ? (
          <TouchableOpacity
            style={[styles.button, styles.buttonSecondary, isRefreshingAll && styles.buttonDisabled]}
            onPress={onRefreshAll}
            disabled={isRefreshingAll}
          >
            <Text style={styles.buttonTextSecondary}>
              {isRefreshingAll ? 'Refreshing Peer Chat Diagnostics...' : 'Refresh All Peer Chat Diagnostics'}
            </Text>
          </TouchableOpacity>
        ) : null}
        {onLoadPeerChatHistory ? (
          <TouchableOpacity
            style={[styles.button, styles.buttonSecondary, isLoadingPeerChatHistory && styles.buttonDisabled]}
            onPress={onLoadPeerChatHistory}
            disabled={isLoadingPeerChatHistory}
          >
            <Text style={styles.buttonTextSecondary}>
              {isLoadingPeerChatHistory ? 'Loading Chat History...' : 'Load Chat History'}
            </Text>
          </TouchableOpacity>
        ) : null}
        {onLoadRecentPeerChatConversations ? (
          <TouchableOpacity
            style={[styles.button, styles.buttonSecondary, isLoadingPeerChatConversations && styles.buttonDisabled]}
            onPress={onLoadRecentPeerChatConversations}
            disabled={isLoadingPeerChatConversations}
          >
            <Text style={styles.buttonTextSecondary}>
              {isLoadingPeerChatConversations ? 'Loading Conversations...' : 'Load Recent Conversations'}
            </Text>
          </TouchableOpacity>
        ) : null}
        {onSendNormalPeerChat ? (
          <TouchableOpacity
            style={[styles.button, styles.buttonSecondary, isSendingPeerChatViaBackend && styles.buttonDisabled]}
            onPress={onSendNormalPeerChat}
            disabled={isSendingPeerChatViaBackend}
          >
            <Text style={styles.buttonTextSecondary}>
              {isSendingPeerChatViaBackend ? 'Sending Backend Chat...' : 'Send Normal Chat via Backend'}
            </Text>
          </TouchableOpacity>
        ) : null}
        {onSendUrgentPeerChat ? (
          <TouchableOpacity
            style={[styles.button, styles.buttonSecondary, isSendingPeerChatViaBackend && styles.buttonDisabled]}
            onPress={onSendUrgentPeerChat}
            disabled={isSendingPeerChatViaBackend}
          >
            <Text style={styles.buttonTextSecondary}>
              {isSendingPeerChatViaBackend ? 'Sending Backend Chat...' : 'Send Urgent Chat via Backend'}
            </Text>
          </TouchableOpacity>
        ) : null}
        {onRefreshOutboxStatus ? (
          <TouchableOpacity
            style={[styles.button, styles.buttonSecondary, isFetchingPeerChatOutbox && styles.buttonDisabled]}
            onPress={onRefreshOutboxStatus}
            disabled={isFetchingPeerChatOutbox}
          >
            <Text style={styles.buttonTextSecondary}>Refresh Backend Outbox Status</Text>
          </TouchableOpacity>
        ) : null}
        {onReleaseLeasedMessages ? (
          <TouchableOpacity
            style={[styles.button, styles.buttonSecondary, isFetchingPeerChatOutbox && styles.buttonDisabled]}
            onPress={onReleaseLeasedMessages}
            disabled={isFetchingPeerChatOutbox}
          >
            <Text style={styles.buttonTextSecondary}>Release Leased Backend Messages</Text>
          </TouchableOpacity>
        ) : null}
        {onPromoteHeldMessages ? (
          <TouchableOpacity
            style={[styles.button, styles.buttonSecondary, isFetchingPeerChatOutbox && styles.buttonDisabled]}
            onPress={onPromoteHeldMessages}
            disabled={isFetchingPeerChatOutbox}
          >
            <Text style={styles.buttonTextSecondary}>Promote Held Messages to Urgent</Text>
          </TouchableOpacity>
        ) : null}
        {onFetchPeerChatOutbox ? (
          <TouchableOpacity
            style={[styles.button, styles.buttonSecondary, isFetchingPeerChatOutbox && styles.buttonDisabled]}
            onPress={onFetchPeerChatOutbox}
            disabled={isFetchingPeerChatOutbox}
          >
            <Text style={styles.buttonTextSecondary}>
              {isFetchingPeerChatOutbox ? 'Fetching Backend Outbox...' : 'Fetch Backend Outbox'}
            </Text>
          </TouchableOpacity>
        ) : null}
        {onLoadTransportSessions ? (
          <TouchableOpacity
            style={[styles.button, styles.buttonSecondary, isLoadingTransportSessions && styles.buttonDisabled]}
            onPress={onLoadTransportSessions}
            disabled={isLoadingTransportSessions}
          >
            <Text style={styles.buttonTextSecondary}>
              {isLoadingTransportSessions ? 'Loading Transport Sessions...' : 'Load Transport Sessions'}
            </Text>
          </TouchableOpacity>
        ) : null}
      </View>

      <PeerChatOutboxPanel
        summary={peerChatOutboxSummary}
        selectedMessage={selectedOutboxPreview}
        onSelectMessage={onSelectOutboxMessage}
        onReleaseMessage={onReleaseOutboxMessage}
        onPromoteMessage={onPromoteOutboxMessage}
      />

      {peerChatHistory ? (
        <View style={styles.container}>
          <Text style={styles.title}>Chat History</Text>
          <Text style={styles.text}>conversation {peerChatHistory.conversation_id}</Text>
          {peerChatHistory.messages.map((message, index) => (
            <Text key={`${message.timestamp_ms}-${index}`} style={styles.text}>
              [{message.priority || 'normal'}] {message.sender_peer_id}: {message.text}
            </Text>
          ))}
        </View>
      ) : null}

      {peerChatConversations.length > 0 ? (
        <View style={styles.container}>
          <Text style={styles.title}>Recent Conversations</Text>
          {peerChatConversations.map((conversation) => (
            <TouchableOpacity
              key={conversation.conversation_id}
              style={styles.previewCard}
              onPress={() => onSelectConversation?.(conversation)}
            >
              <Text style={styles.text}>
                {conversation.conversation_id} • {conversation.message_count} messages
              </Text>
              <Text style={styles.text}>
                [{conversation.priority || 'normal'}] {conversation.sender_peer_id}: {conversation.last_text}
              </Text>
              {selectedConversationId === conversation.conversation_id ? (
                <Text style={styles.selectedText}>Selected Conversation</Text>
              ) : null}
            </TouchableOpacity>
          ))}
        </View>
      ) : null}

      {transportSessions?.length ? (
        <View style={styles.container}>
          <Text style={styles.title}>Transport Sessions</Text>
          {transportSessions.map((session) => (
            <View key={`${session.peer_id}-${session.session_id}`} style={styles.previewCard}>
              <Text style={styles.text}>{session.peer_id}</Text>
              <Text style={styles.text}>session {session.session_id}</Text>
              <Text style={styles.text}>resume {session.resume_token}</Text>
              <Text style={styles.text}>capabilities: {(session.capabilities || []).join(', ') || 'none'}</Text>
              {onClearTransportSession ? (
                <TouchableOpacity
                  style={[styles.button, styles.buttonSecondary, isClearingTransportSession && styles.buttonDisabled]}
                  onPress={() => onClearTransportSession(session.peer_id)}
                  disabled={isClearingTransportSession}
                >
                  <Text style={styles.buttonTextSecondary}>
                    {isClearingTransportSession ? 'Clearing Transport Session...' : 'Clear Transport Session'}
                  </Text>
                </TouchableOpacity>
              ) : null}
            </View>
          ))}
        </View>
      ) : null}
    </>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
    shadowColor: '#000',
    shadowOpacity: 0.05,
    shadowRadius: 8,
    shadowOffset: { width: 0, height: 2 },
    elevation: 2,
  },
  title: {
    fontSize: 16,
    fontWeight: '600',
    color: '#111827',
    marginBottom: 8,
  },
  subtext: {
    fontSize: 13,
    color: '#6b7280',
    marginBottom: 10,
  },
  text: {
    fontSize: 14,
    color: '#374151',
    marginBottom: 6,
  },
  previewCard: {
    backgroundColor: '#f9fafb',
    borderRadius: 10,
    padding: 12,
    marginTop: 10,
  },
  selectedText: {
    fontSize: 12,
    color: '#2563eb',
    fontWeight: '600',
  },
  button: {
    borderRadius: 10,
    paddingVertical: 10,
    paddingHorizontal: 14,
    alignItems: 'center',
    marginTop: 10,
  },
  buttonSecondary: {
    borderWidth: 1,
    borderColor: '#cbd5e1',
    backgroundColor: '#fff',
  },
  buttonDisabled: {
    opacity: 0.5,
  },
  buttonTextSecondary: {
    color: '#0f172a',
    fontWeight: '600',
  },
});
