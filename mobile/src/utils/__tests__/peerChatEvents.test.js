import {
  getBackendSentChatEvent,
  getLoadedChatHistoryEvent,
  getLoadedConversationsEvent,
  getNoHeldMessagesEvent,
  getNoLeasedMessagesEvent,
  getPromotedOutboxMessagesEvent,
  getRefreshedAllPeerChatDiagnosticsEvent,
  getRefreshedOutboxStatusEvent,
  getReleasedOutboxMessagesEvent,
  getSelectConversationEvent,
} from '../peerChatEvents';

describe('peerChatEvents', () => {
  it('formats conversation-selection and history messages', () => {
    expect(getSelectConversationEvent()).toBe('Select a recent conversation first');
    expect(getLoadedConversationsEvent()).toBe('Loaded recent peer chat conversations');
    expect(getLoadedChatHistoryEvent('chat-123')).toBe('Loaded chat history for chat-123');
  });

  it('formats outbox status and queue-action messages', () => {
    expect(getRefreshedAllPeerChatDiagnosticsEvent()).toBe('Refreshed all peer chat diagnostics');
    expect(getRefreshedOutboxStatusEvent('hold')).toBe('Refreshed backend outbox status (hold)');
    expect(getReleasedOutboxMessagesEvent(2)).toBe('Released 2 leased backend outbox message(s)');
    expect(getPromotedOutboxMessagesEvent(3)).toBe('Promoted 3 backend outbox message(s) to urgent');
    expect(getNoLeasedMessagesEvent()).toBe('No leased backend outbox messages to release');
    expect(getNoHeldMessagesEvent()).toBe('No policy-held backend outbox messages to promote');
  });

  it('formats backend send messages', () => {
    expect(getBackendSentChatEvent('urgent', '12D3KooWpeer')).toBe(
      'Backend sent urgent chat to 12D3KooWpeer'
    );
  });
});
