import {
  findMatchingTransportSession,
  formatTransportSessionAge,
  getTransportSessionPeerTarget,
  getTransportSessionHealth,
  isStaleTransportSessionSuspected,
} from '../peerTransportSessions';

describe('peerTransportSessions', () => {
  it('prefers the active peer when resolving the transport-session target', () => {
    expect(
      getTransportSessionPeerTarget({
        activePeer: { peerRef: 'peer://active', peerId: '12D3KooWactive' },
        selectedPeerRef: 'peer://selected',
        discoveredPeers: [{ peerRef: 'peer://selected', peerId: '12D3KooWselected' }],
      })
    ).toEqual({
      peerRef: 'peer://active',
      peerId: '12D3KooWactive',
      label: '12D3KooWactive',
      source: 'active',
    });
  });

  it('falls back to the selected discovered peer when no active peer exists', () => {
    expect(
      getTransportSessionPeerTarget({
        activePeer: null,
        selectedPeerRef: 'peer://selected',
        discoveredPeers: [{ peerRef: 'peer://selected', peerId: '12D3KooWselected' }],
      })
    ).toEqual({
      peerRef: 'peer://selected',
      peerId: '12D3KooWselected',
      label: '12D3KooWselected',
      source: 'selected',
    });
  });

  it('matches transport sessions by peer id first, then by peer ref', () => {
    const sessions = [
      { peer_id: '12D3KooWother', peer_ref: 'peer://other', session_id: 'session-1' },
      { peer_id: '12D3KooWselected', peer_ref: 'peer://selected', session_id: 'session-2' },
    ];

    expect(
      findMatchingTransportSession(sessions, {
        peerId: '12D3KooWselected',
        peerRef: 'peer://mismatch',
      })
    ).toEqual(sessions[1]);

    expect(
      findMatchingTransportSession(sessions, {
        peerId: null,
        peerRef: 'peer://other',
      })
    ).toEqual(sessions[0]);
  });

  it('returns null when no target or matching session exists', () => {
    expect(findMatchingTransportSession([], null)).toBeNull();
    expect(
      findMatchingTransportSession([{ peer_id: '12D3KooWother', session_id: 'session-1' }], {
        peerId: '12D3KooWmissing',
        peerRef: 'peer://missing',
      })
    ).toBeNull();
  });

  it('flags a stale transport-session suspicion when a matched cursor exists without an active connection', () => {
    expect(
      isStaleTransportSessionSuspected({
        targetPeer: { peerId: '12D3KooWselected', peerRef: 'peer://selected' },
        matchedSession: { peer_id: '12D3KooWselected', session_id: 'session-2' },
        activePeer: null,
      })
    ).toBe(true);

    expect(
      isStaleTransportSessionSuspected({
        targetPeer: { peerId: '12D3KooWselected', peerRef: 'peer://selected' },
        matchedSession: { peer_id: '12D3KooWselected', session_id: 'session-2' },
        activePeer: { peerId: '12D3KooWselected', peerRef: 'peer://selected' },
      })
    ).toBe(false);
  });

  it('formats transport-session age labels', () => {
    expect(formatTransportSessionAge(null, 100_000)).toBe('unknown');
    expect(formatTransportSessionAge(98_000, 100_000)).toBe('just now');
    expect(formatTransportSessionAge(70_000, 100_000)).toBe('30s ago');
    expect(formatTransportSessionAge(40_000, 100_000)).toBe('1m ago');
    expect(formatTransportSessionAge(3_600_000, 7_200_000)).toBe('1h ago');
  });

  it('classifies transport-session health from cursor age', () => {
    expect(getTransportSessionHealth(null, 100_000)).toBe('unknown');
    expect(getTransportSessionHealth(70_000, 100_000)).toBe('fresh');
    expect(getTransportSessionHealth(100_000, 220_000)).toBe('aging');
    expect(getTransportSessionHealth(100_000, 900_000)).toBe('stale');
  });
});
