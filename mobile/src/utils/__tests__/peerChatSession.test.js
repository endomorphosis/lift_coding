import {
  DEFAULT_PEER_CHAT_POLL_MS,
  formatPeerChatSessionLabel,
  getPeerChatRecommendedPollMs,
  normalizePeerChatHandsetSession,
} from '../peerChatSession';

describe('peerChatSession', () => {
  it('normalizes a handset session into a stable mobile shape', () => {
    expect(
      normalizePeerChatHandsetSession({
        status: 'active',
        delivery_mode: 'short_retry',
        recommended_poll_ms: 5000,
        recommended_lease_ms: 6000,
        last_seen_age_ms: 1200,
        last_seen_ms: 10,
        last_fetch_ms: 20,
        last_ack_ms: 30,
      })
    ).toEqual({
      status: 'active',
      delivery_mode: 'short_retry',
      recommended_poll_ms: 5000,
      recommended_lease_ms: 6000,
      last_seen_age_ms: 1200,
      last_seen_ms: 10,
      last_fetch_ms: 20,
      last_ack_ms: 30,
    });
  });

  it('fills missing handset session fields with stable defaults', () => {
    expect(normalizePeerChatHandsetSession({})).toEqual({
      status: 'unknown',
      delivery_mode: 'unknown',
      recommended_poll_ms: DEFAULT_PEER_CHAT_POLL_MS,
      recommended_lease_ms: 0,
      last_seen_age_ms: 0,
      last_seen_ms: null,
      last_fetch_ms: null,
      last_ack_ms: null,
    });
    expect(normalizePeerChatHandsetSession(null)).toBeNull();
  });

  it('derives a recommended poll interval from a session or response-like object', () => {
    expect(getPeerChatRecommendedPollMs({ recommended_poll_ms: 9000 })).toBe(9000);
    expect(getPeerChatRecommendedPollMs(null)).toBe(DEFAULT_PEER_CHAT_POLL_MS);
  });

  it('formats the handset session label for display', () => {
    expect(
      formatPeerChatSessionLabel({ status: 'stale', delivery_mode: 'long_retry' })
    ).toBe('stale • long_retry');
    expect(formatPeerChatSessionLabel(null)).toBe('unknown');
  });
});
