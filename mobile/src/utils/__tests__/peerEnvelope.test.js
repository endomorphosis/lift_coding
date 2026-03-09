import {
  CHAT_PROTOCOL,
  DEFAULT_APP_PROTOCOL,
  PROTOCOL_ID,
  PROTOCOL_MAJOR,
  PROTOCOL_MINOR,
  createAckEnvelope,
  createChatMessageEnvelope,
  createHandshakeEnvelope,
  createMessageEnvelope,
  createSessionId,
  decodeEnvelopeBase64,
  decodeEnvelopePayload,
  encodeEnvelopeBase64,
} from '../peerEnvelope';

describe('peerEnvelope', () => {
  it('creates handshake envelopes with the expected protocol metadata', () => {
    const envelope = createHandshakeEnvelope({
      peerId: '12D3KooWpeer',
      sessionId: 'session-1',
      capabilities: ['handshake-v1'],
    });

    expect(envelope.kind).toBe('handshake');
    expect(envelope.peer_id).toBe('12D3KooWpeer');
    expect(envelope.session_id).toBe('session-1');
    expect(envelope.protocol_id).toBe(PROTOCOL_ID);
    expect(envelope.version_major).toBe(PROTOCOL_MAJOR);
    expect(envelope.version_minor).toBe(PROTOCOL_MINOR);
    expect(envelope.capabilities).toEqual(['handshake-v1']);
    expect(envelope.payload_b64).toBe(null);
  });

  it('round-trips message envelopes and decodes JSON payloads', () => {
    const envelope = createMessageEnvelope({
      peerId: '12D3KooWpeer',
      sessionId: 'session-2',
      payload: { type: 'ping', body: 'hello' },
    });

    const encoded = encodeEnvelopeBase64(envelope);
    const decoded = decodeEnvelopeBase64(encoded);

    expect(decoded.kind).toBe('message');
    expect(decoded.peer_id).toBe('12D3KooWpeer');
    expect(decodeEnvelopePayload(decoded.payload_b64)).toEqual({
      protocol: DEFAULT_APP_PROTOCOL,
      payload: { type: 'ping', body: 'hello' },
    });
  });

  it('creates chat envelopes using the chat protocol wrapper', () => {
    const envelope = createChatMessageEnvelope({
      peerId: '12D3KooWpeer',
      sessionId: 'session-chat',
      text: 'hello from glasses',
      senderPeerId: '12D3KooWsender',
      priority: 'urgent',
    });

    expect(decodeEnvelopePayload(envelope.payload_b64)).toEqual({
      protocol: CHAT_PROTOCOL,
      payload: expect.objectContaining({
        type: 'chat',
        text: 'hello from glasses',
        sender_peer_id: '12D3KooWsender',
        priority: 'urgent',
      }),
    });
  });

  it('creates ack envelopes referencing the acked message id', () => {
    const envelope = createAckEnvelope({
      peerId: '12D3KooWpeer',
      sessionId: 'session-3',
      ackedMessageId: 'message-123',
    });

    expect(envelope.kind).toBe('ack');
    expect(envelope.acked_message_id).toBe('message-123');
    expect(envelope.payload_b64).toBe(null);
  });

  it('creates stable-length session ids', () => {
    const sessionId = createSessionId();
    expect(typeof sessionId).toBe('string');
    expect(sessionId).toHaveLength(16);
  });

  it('rejects envelope creation without peer id', () => {
    expect(() =>
      createHandshakeEnvelope({
        peerId: '',
        sessionId: 'session-4',
      })
    ).toThrow('peerId is required');
  });
});
