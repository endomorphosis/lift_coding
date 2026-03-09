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
    ScrollView: makeComponent('ScrollView'),
    Text: makeComponent('Text'),
    View: makeComponent('View'),
  };
});

const mockPanelSpy = jest.fn(() => null);
const mockUsePeerChatDiagnostics = jest.fn();
const mockUseNowTicker = jest.fn();

jest.mock('../../components/PeerChatDiagnosticsPanel', () => (props) => mockPanelSpy(props));
jest.mock('../../hooks/usePeerChatDiagnostics', () => ({
  usePeerChatDiagnostics: (...args) => mockUsePeerChatDiagnostics(...args),
}));
jest.mock('../../hooks/useNowTicker', () => ({
  useNowTicker: (...args) => mockUseNowTicker(...args),
}));

import PeerChatDiagnosticsScreen from '../PeerChatDiagnosticsScreen';

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

function collectText(node) {
  return expandTree(node)
    .filter((entry) => typeof entry === 'string' || typeof entry === 'number')
    .map(String)
    .join(' ')
    .replace(/\s+/g, ' ')
    .trim();
}

describe('PeerChatDiagnosticsScreen', () => {
  beforeEach(() => {
    mockPanelSpy.mockClear();
    mockUsePeerChatDiagnostics.mockReset();
    mockUseNowTicker.mockReset();
    mockUseNowTicker.mockReturnValue(1700000000500);
  });

  it('renders summary text and passes hook state/actions into the diagnostics panel', () => {
    const diagnostics = {
      localPeerId: '12D3KooWlocal1234',
      lastEvent: 'Loaded recent peer chat conversations',
      lastError: 'backend unavailable',
      peerChatConversations: [{ conversation_id: 'chat-1' }],
      isLoadingPeerChatConversations: false,
      selectedConversation: { conversation_id: 'chat-1' },
      setSelectedConversation: jest.fn(),
      peerChatHistory: { conversation_id: 'chat-1', messages: [] },
      isLoadingPeerChatHistory: false,
      peerChatOutboxSummary: { delivery_mode: 'hold', preview_messages: [] },
      selectedOutboxMessageId: 'msg-1',
      setSelectedOutboxMessageId: jest.fn(),
      selectedOutboxPreview: { outbox_message_id: 'msg-1' },
      isFetchingPeerChatOutbox: false,
      isSendingPeerChatViaBackend: false,
      isRefreshingAllPeerChatDiagnostics: false,
      peerChatHandsetSession: { status: 'active', delivery_mode: 'short_retry' },
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
      recommendedOutboxPollMs: 5000,
      lastSyncedAt: 1700000000000,
      refreshAllPeerChatDiagnostics: jest.fn(),
      loadRecentPeerChatConversations: jest.fn(),
      loadPeerChatHistory: jest.fn(),
      refreshPeerChatOutboxStatus: jest.fn(),
      sendPeerChatViaBackend: jest.fn(),
      releaseLeasedPeerChatOutboxMessages: jest.fn(),
      promoteHeldPeerChatOutboxMessages: jest.fn(),
      releasePeerChatOutboxMessages: jest.fn(),
      promotePeerChatOutboxMessages: jest.fn(),
      loadTransportSessions: jest.fn(),
      clearTransportSession: jest.fn(),
    };
    mockUsePeerChatDiagnostics.mockReturnValue(diagnostics);

    const tree = PeerChatDiagnosticsScreen();
    const text = collectText(tree);

    expect(text).toContain('Peer Chat Diagnostics');
    expect(text).toContain('Local peer ID: 12D3KooWlocal1234');
    expect(text).toContain('Session: active • short_retry');
    expect(text).toContain('Recommended poll: 5000 ms');
    expect(text).toContain('Selected conversation: chat-1');
    expect(text).toContain('Transport sessions: 1');
    expect(text).toContain('Last synced:');
    expect(text).toContain('just now');
    expect(text).toContain('Sync health: fresh');
    expect(text).toContain('Last event: Loaded recent peer chat conversations');
    expect(text).toContain('Error: backend unavailable');

    expect(mockPanelSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        selectedConversationId: 'chat-1',
        peerChatConversations: diagnostics.peerChatConversations,
        peerChatHistory: diagnostics.peerChatHistory,
        peerChatOutboxSummary: diagnostics.peerChatOutboxSummary,
        selectedOutboxPreview: diagnostics.selectedOutboxPreview,
        onRefreshAll: diagnostics.refreshAllPeerChatDiagnostics,
        onLoadPeerChatHistory: diagnostics.loadPeerChatHistory,
        onLoadRecentPeerChatConversations: diagnostics.loadRecentPeerChatConversations,
        onRefreshOutboxStatus: diagnostics.refreshPeerChatOutboxStatus,
        onReleaseLeasedMessages: diagnostics.releaseLeasedPeerChatOutboxMessages,
        onPromoteHeldMessages: diagnostics.promoteHeldPeerChatOutboxMessages,
        onSelectConversation: diagnostics.setSelectedConversation,
        onSelectOutboxMessage: diagnostics.setSelectedOutboxMessageId,
        transportSessions: diagnostics.transportSessions,
        isLoadingTransportSessions: diagnostics.isLoadingTransportSessions,
        isClearingTransportSession: diagnostics.isClearingTransportSession,
        onLoadTransportSessions: diagnostics.loadTransportSessions,
        onClearTransportSession: diagnostics.clearTransportSession,
      })
    );

    const panelProps = mockPanelSpy.mock.calls[0][0];
    panelProps.onRefreshAll();
    panelProps.onSendNormalPeerChat();
    panelProps.onSendUrgentPeerChat();
    panelProps.onReleaseOutboxMessage('msg-2');
    panelProps.onPromoteOutboxMessage('msg-3');
    panelProps.onLoadTransportSessions();
    panelProps.onClearTransportSession('12D3KooWpeer');

    expect(diagnostics.refreshAllPeerChatDiagnostics).toHaveBeenCalledTimes(1);
    expect(diagnostics.sendPeerChatViaBackend).toHaveBeenNthCalledWith(1, 'normal');
    expect(diagnostics.sendPeerChatViaBackend).toHaveBeenNthCalledWith(2, 'urgent');
    expect(diagnostics.releasePeerChatOutboxMessages).toHaveBeenCalledWith(['msg-2']);
    expect(diagnostics.promotePeerChatOutboxMessages).toHaveBeenCalledWith(['msg-3']);
    expect(diagnostics.loadTransportSessions).toHaveBeenCalledTimes(1);
    expect(diagnostics.clearTransportSession).toHaveBeenCalledWith('12D3KooWpeer');
  });
});
