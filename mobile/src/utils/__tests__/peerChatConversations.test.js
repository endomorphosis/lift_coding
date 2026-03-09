import {
  normalizePeerChatConversations,
  selectNextConversation,
} from '../peerChatConversations';

describe('peerChatConversations', () => {
  const conversations = [
    {
      conversation_id: 'chat-1',
      peer_id: 'peer-a',
      last_text: 'first',
    },
    {
      conversation_id: 'chat-2',
      peer_id: 'peer-b',
      last_text: 'second',
    },
  ];

  it('normalizes backend conversation responses into a list', () => {
    expect(normalizePeerChatConversations({ conversations })).toEqual(conversations);
    expect(normalizePeerChatConversations({})).toEqual([]);
    expect(normalizePeerChatConversations(null)).toEqual([]);
  });

  it('keeps the current selection when the conversation still exists', () => {
    expect(
      selectNextConversation(conversations, { conversation_id: 'chat-2' })
    ).toEqual(conversations[1]);
  });

  it('falls back to the first conversation when selection is missing', () => {
    expect(selectNextConversation(conversations, null)).toEqual(conversations[0]);
    expect(
      selectNextConversation(conversations, { conversation_id: 'missing' })
    ).toEqual(conversations[0]);
    expect(selectNextConversation([], { conversation_id: 'chat-1' })).toBeNull();
  });
});
