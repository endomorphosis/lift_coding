const PROTOCOL_ID = '/handsfree/bluetooth/1.0.0';
const PROTOCOL_MAJOR = 1;
const PROTOCOL_MINOR = 0;
const DEFAULT_APP_PROTOCOL = '/handsfree/app/1.0.0';
const CHAT_PROTOCOL = '/handsfree/chat/1.0.0';

function randomHex(bytes = 8) {
  const alphabet = '0123456789abcdef';
  let out = '';
  for (let i = 0; i < bytes * 2; i += 1) {
    out += alphabet[Math.floor(Math.random() * alphabet.length)];
  }
  return out;
}

function timestampMs() {
  return Date.now();
}

function encodeJsonBase64(value) {
  return btoa(unescape(encodeURIComponent(JSON.stringify(value))));
}

function decodeJsonBase64(value) {
  const json = decodeURIComponent(escape(atob(value)));
  return JSON.parse(json);
}

function encodeProtocolPayload(protocol, payload) {
  return encodeJsonBase64({
    protocol: protocol || DEFAULT_APP_PROTOCOL,
    payload_b64: typeof payload === 'string' ? payload : encodeJsonBase64(payload),
  });
}

export function createPeerEnvelope(kind, {
  peerId,
  sessionId,
  payloadBase64,
  ackedMessageId,
  capabilities,
  errorCode,
  errorDetail,
  messageId,
  nonce,
  timestamp,
} = {}) {
  if (!peerId) {
    throw new Error('peerId is required');
  }
  if (!sessionId) {
    throw new Error('sessionId is required');
  }

  return {
    kind,
    peer_id: peerId,
    session_id: sessionId,
    protocol_id: PROTOCOL_ID,
    version_major: PROTOCOL_MAJOR,
    version_minor: PROTOCOL_MINOR,
    message_id: messageId || randomHex(8),
    timestamp_ms: timestamp || timestampMs(),
    nonce: nonce || randomHex(12),
    payload_b64: payloadBase64 || null,
    acked_message_id: ackedMessageId || null,
    capabilities: capabilities || null,
    error_code: errorCode || null,
    error_detail: errorDetail || null,
  };
}

export function createHandshakeEnvelope({ peerId, sessionId, capabilities = [] }) {
  return createPeerEnvelope('handshake', { peerId, sessionId, capabilities });
}

export function createMessageEnvelope({ peerId, sessionId, payload }) {
  return createPeerEnvelope('message', {
    peerId,
    sessionId,
    payloadBase64: encodeProtocolPayload(DEFAULT_APP_PROTOCOL, payload),
  });
}

export function createProtocolMessageEnvelope({ peerId, sessionId, protocol, payload }) {
  return createPeerEnvelope('message', {
    peerId,
    sessionId,
    payloadBase64: encodeProtocolPayload(protocol, payload),
  });
}

export function createChatMessageEnvelope({
  peerId,
  sessionId,
  text,
  senderPeerId,
  conversationId,
  priority = 'normal',
}) {
  if (!text) {
    throw new Error('text is required');
  }
  if (!['normal', 'urgent'].includes(priority)) {
    throw new Error('priority must be normal or urgent');
  }
  return createProtocolMessageEnvelope({
    peerId,
    sessionId,
    protocol: CHAT_PROTOCOL,
    payload: {
      type: 'chat',
      text,
      priority,
      ...(conversationId ? { conversation_id: conversationId } : {}),
      ...(senderPeerId ? { sender_peer_id: senderPeerId } : {}),
      timestamp_ms: timestampMs(),
    },
  });
}

export function createAckEnvelope({ peerId, sessionId, ackedMessageId }) {
  return createPeerEnvelope('ack', { peerId, sessionId, ackedMessageId });
}

export function encodeEnvelopeBase64(envelope) {
  return btoa(unescape(encodeURIComponent(JSON.stringify(envelope))));
}

export function decodeEnvelopeBase64(payloadBase64) {
  const json = decodeURIComponent(escape(atob(payloadBase64)));
  return JSON.parse(json);
}

export function decodeEnvelopePayload(payloadBase64) {
  const decoded = decodeJsonBase64(payloadBase64);
  if (decoded && typeof decoded === 'object' && typeof decoded.protocol === 'string' && decoded.payload_b64) {
    return {
      protocol: decoded.protocol,
      payload: decodeJsonBase64(decoded.payload_b64),
    };
  }
  return {
    protocol: DEFAULT_APP_PROTOCOL,
    payload: decoded,
  };
}

export function createSessionId() {
  return randomHex(8);
}

export { CHAT_PROTOCOL, DEFAULT_APP_PROTOCOL, PROTOCOL_ID, PROTOCOL_MAJOR, PROTOCOL_MINOR };
