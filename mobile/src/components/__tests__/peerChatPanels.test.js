import React from 'react';

jest.mock('react-native', () => {
  const ReactNativeReact = require('react');

  const makeComponent = (name) => {
    const Component = ({ children, ...props }) =>
      ReactNativeReact.createElement(name, props, children);
    Component.displayName = name;
    return Component;
  };

  return {
    StyleSheet: { create: (styles) => styles },
    Text: makeComponent('Text'),
    TouchableOpacity: makeComponent('TouchableOpacity'),
    View: makeComponent('View'),
  };
});

import PeerChatDiagnosticsPanel from '../PeerChatDiagnosticsPanel';
import PeerChatOutboxPanel from '../PeerChatOutboxPanel';

function expandTree(node) {
  if (node == null || typeof node === 'boolean') {
    return [];
  }
  if (Array.isArray(node)) {
    return node.flatMap(expandTree);
  }
  if (!React.isValidElement(node)) {
    return [node];
  }
  if (typeof node.type === 'function') {
    return expandTree(node.type(node.props));
  }
  return [node, ...expandTree(node.props?.children)];
}

function collectTextContent(node) {
  return expandTree(node)
    .filter((entry) => typeof entry === 'string' || typeof entry === 'number')
    .map(String)
    .join(' ');
}

function collectNormalizedText(node) {
  return collectTextContent(node).replace(/\s+/g, ' ').trim();
}

function findPressableByText(node, label, { exact = false } = {}) {
  return expandTree(node).find(
    (entry) => {
      if (!React.isValidElement(entry) || typeof entry.props?.onPress !== 'function') {
        return false;
      }
      const normalizedText = collectNormalizedText(entry);
      return exact ? normalizedText === label : normalizedText.includes(label);
    }
  );
}

describe('PeerChatOutboxPanel', () => {
  const summary = {
    delivery_mode: 'hold',
    queued_total: 2,
    deliverable_now: 1,
    held_now: 1,
    queued_urgent: 1,
    queued_normal: 1,
    preview_messages: [
      {
        outbox_message_id: 'msg-1',
        state: 'leased',
        priority: 'normal',
        text: 'leased message',
        conversation_id: 'chat-1',
        sender_peer_id: 'peer-a',
        timestamp_ms: 111,
        leased_until_ms: 222,
        hold_reason: null,
      },
      {
        outbox_message_id: 'msg-2',
        state: 'held_by_policy',
        priority: 'urgent',
        text: 'held message',
        conversation_id: 'chat-2',
        sender_peer_id: 'peer-b',
        timestamp_ms: 333,
        leased_until_ms: null,
        hold_reason: 'offline_normal_held',
      },
    ],
  };

  it('renders queue summary, selected message detail, and per-message actions', () => {
    const onSelectMessage = jest.fn();
    const onReleaseMessage = jest.fn();
    const onPromoteMessage = jest.fn();

    const tree = PeerChatOutboxPanel({
      summary,
      selectedMessage: summary.preview_messages[1],
      onSelectMessage,
      onReleaseMessage,
      onPromoteMessage,
    });

    const normalizedText = collectNormalizedText(tree);

    expect(normalizedText).toContain('Backend Outbox');
    expect(normalizedText).toContain('mode hold');
    expect(normalizedText).toContain('total 2');
    expect(normalizedText).toContain('Selected Outbox Message');
    expect(normalizedText).toContain('hold reason offline_normal_held');

    findPressableByText(tree, 'Release This Message', { exact: true }).props.onPress();
    findPressableByText(tree, 'Promote This Message', { exact: true }).props.onPress();
    findPressableByText(tree, '[ normal ] leased • leased message').props.onPress();

    expect(onReleaseMessage).toHaveBeenCalledWith('msg-1');
    expect(onPromoteMessage).toHaveBeenCalledWith('msg-2');
    expect(onSelectMessage).toHaveBeenCalledWith('msg-1');
  });
});

describe('PeerChatDiagnosticsPanel', () => {
  it('renders controls and marks the selected conversation', () => {
    const onLoadPeerChatHistory = jest.fn();
    const onLoadRecentPeerChatConversations = jest.fn();
    const onRefreshAll = jest.fn();
    const onSendNormalPeerChat = jest.fn();
    const onSendUrgentPeerChat = jest.fn();
    const onRefreshOutboxStatus = jest.fn();
    const onReleaseLeasedMessages = jest.fn();
    const onPromoteHeldMessages = jest.fn();
    const onLoadTransportSessions = jest.fn();
    const onClearTransportSession = jest.fn();
    const onSelectConversation = jest.fn();

    const tree = PeerChatDiagnosticsPanel({
      headerText: 'Backend-focused peer chat controls.',
      onRefreshAll,
      isRefreshingAll: false,
      isLoadingPeerChatHistory: false,
      onLoadPeerChatHistory,
      isLoadingPeerChatConversations: false,
      onLoadRecentPeerChatConversations,
      isSendingPeerChatViaBackend: false,
      onSendNormalPeerChat,
      onSendUrgentPeerChat,
      isFetchingPeerChatOutbox: false,
      onRefreshOutboxStatus,
      onReleaseLeasedMessages,
      onPromoteHeldMessages,
      peerChatOutboxSummary: {
        delivery_mode: 'short_retry',
        queued_total: 0,
        deliverable_now: 0,
        held_now: 0,
        queued_urgent: 0,
        queued_normal: 0,
        preview_messages: [],
      },
      selectedOutboxPreview: null,
      onSelectOutboxMessage: jest.fn(),
      onReleaseOutboxMessage: jest.fn(),
      onPromoteOutboxMessage: jest.fn(),
      peerChatHistory: {
        conversation_id: 'chat-1',
        messages: [
          { timestamp_ms: 1, priority: 'urgent', sender_peer_id: 'peer-a', text: 'hello' },
        ],
      },
      peerChatConversations: [
        {
          conversation_id: 'chat-1',
          message_count: 2,
          priority: 'urgent',
          sender_peer_id: 'peer-a',
          last_text: 'latest',
        },
      ],
      selectedConversationId: 'chat-1',
      onSelectConversation,
      transportSessions: [
        {
          peer_id: '12D3KooWpeer',
          session_id: 'session-1',
          resume_token: 'resume-1',
          capabilities: ['chat'],
        },
      ],
      isLoadingTransportSessions: false,
      isClearingTransportSession: false,
      onLoadTransportSessions,
      onClearTransportSession,
    });

    const normalizedText = collectNormalizedText(tree);

    expect(normalizedText).toContain('Backend-focused peer chat controls.');
    expect(normalizedText).toContain('Selected Conversation');
    expect(normalizedText).toContain('[ urgent ] peer-a : hello');
    expect(normalizedText).toContain('Transport Sessions');
    expect(normalizedText).toContain('session session-1');

    findPressableByText(tree, 'Refresh All Peer Chat Diagnostics', { exact: true }).props.onPress();
    findPressableByText(tree, 'Load Chat History', { exact: true }).props.onPress();
    findPressableByText(tree, 'Load Recent Conversations', { exact: true }).props.onPress();
    findPressableByText(tree, 'Send Normal Chat via Backend', { exact: true }).props.onPress();
    findPressableByText(tree, 'Send Urgent Chat via Backend', { exact: true }).props.onPress();
    findPressableByText(tree, 'Refresh Backend Outbox Status', { exact: true }).props.onPress();
    findPressableByText(tree, 'Release Leased Backend Messages', { exact: true }).props.onPress();
    findPressableByText(tree, 'Promote Held Messages to Urgent', { exact: true }).props.onPress();
    findPressableByText(tree, 'Load Transport Sessions', { exact: true }).props.onPress();
    findPressableByText(tree, 'Clear Transport Session', { exact: true }).props.onPress();
    findPressableByText(tree, 'chat-1 • 2 messages').props.onPress();

    expect(onRefreshAll).toHaveBeenCalledTimes(1);
    expect(onLoadPeerChatHistory).toHaveBeenCalledTimes(1);
    expect(onLoadRecentPeerChatConversations).toHaveBeenCalledTimes(1);
    expect(onSendNormalPeerChat).toHaveBeenCalledTimes(1);
    expect(onSendUrgentPeerChat).toHaveBeenCalledTimes(1);
    expect(onRefreshOutboxStatus).toHaveBeenCalledTimes(1);
    expect(onReleaseLeasedMessages).toHaveBeenCalledTimes(1);
    expect(onPromoteHeldMessages).toHaveBeenCalledTimes(1);
    expect(onLoadTransportSessions).toHaveBeenCalledTimes(1);
    expect(onClearTransportSession).toHaveBeenCalledWith('12D3KooWpeer');
    expect(onSelectConversation).toHaveBeenCalledWith(
      expect.objectContaining({ conversation_id: 'chat-1' })
    );
  });

  it('shows a loading label while the full diagnostics refresh is running', () => {
    const tree = PeerChatDiagnosticsPanel({
      headerText: 'Backend-focused peer chat controls.',
      onRefreshAll: jest.fn(),
      isRefreshingAll: true,
      isLoadingPeerChatHistory: false,
      isLoadingPeerChatConversations: false,
      isSendingPeerChatViaBackend: false,
      isFetchingPeerChatOutbox: false,
      peerChatOutboxSummary: null,
      selectedOutboxPreview: null,
      peerChatHistory: null,
      peerChatConversations: [],
    });

    expect(collectNormalizedText(tree)).toContain('Refreshing Peer Chat Diagnostics...');
  });
});
