export const DEFAULT_PEER_CHAT_POLL_MS = 4000;

export function normalizePeerChatHandsetSession(session) {
  if (!session) {
    return null;
  }

  return {
    status: session.status || 'unknown',
    delivery_mode: session.delivery_mode || 'unknown',
    recommended_poll_ms: session.recommended_poll_ms ?? DEFAULT_PEER_CHAT_POLL_MS,
    recommended_lease_ms: session.recommended_lease_ms ?? 0,
    last_seen_age_ms: session.last_seen_age_ms ?? 0,
    last_seen_ms: session.last_seen_ms ?? null,
    last_fetch_ms: session.last_fetch_ms ?? null,
    last_ack_ms: session.last_ack_ms ?? null,
  };
}

export function getPeerChatRecommendedPollMs(source) {
  return source?.recommended_poll_ms ?? DEFAULT_PEER_CHAT_POLL_MS;
}

export function formatPeerChatSessionLabel(session) {
  if (!session) {
    return 'unknown';
  }

  return `${session.status} • ${session.delivery_mode}`;
}
