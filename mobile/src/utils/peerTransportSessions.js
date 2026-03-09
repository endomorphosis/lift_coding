export function getTransportSessionPeerTarget({ activePeer = null, selectedPeerRef = null, discoveredPeers = [] } = {}) {
  if (activePeer?.peerRef || activePeer?.peerId) {
    return {
      peerRef: activePeer.peerRef || null,
      peerId: activePeer.peerId || null,
      label: activePeer.peerId || activePeer.peerRef,
      source: 'active',
    };
  }

  const selectedPeer = discoveredPeers.find((peer) => peer?.peerRef === selectedPeerRef);
  if (selectedPeer?.peerRef || selectedPeer?.peerId) {
    return {
      peerRef: selectedPeer.peerRef || null,
      peerId: selectedPeer.peerId || null,
      label: selectedPeer.peerId || selectedPeer.peerRef,
      source: 'selected',
    };
  }

  return null;
}

export function findMatchingTransportSession(sessions, targetPeer) {
  if (!Array.isArray(sessions) || !targetPeer) {
    return null;
  }

  return (
    sessions.find((session) => session?.peer_id && targetPeer.peerId && session.peer_id === targetPeer.peerId) ||
    sessions.find((session) => session?.peer_ref && targetPeer.peerRef && session.peer_ref === targetPeer.peerRef) ||
    null
  );
}

export function isStaleTransportSessionSuspected({ targetPeer = null, matchedSession = null, activePeer = null } = {}) {
  if (!targetPeer || !matchedSession) {
    return false;
  }

  return !(activePeer?.peerRef || activePeer?.peerId);
}

export function formatTransportSessionAge(updatedAtMs, nowMs = Date.now()) {
  if (!updatedAtMs || !Number.isFinite(updatedAtMs)) {
    return 'unknown';
  }

  const ageMs = Math.max(0, nowMs - updatedAtMs);
  if (ageMs < 5_000) {
    return 'just now';
  }
  if (ageMs < 60_000) {
    return `${Math.floor(ageMs / 1000)}s ago`;
  }
  if (ageMs < 3_600_000) {
    return `${Math.floor(ageMs / 60_000)}m ago`;
  }
  return `${Math.floor(ageMs / 3_600_000)}h ago`;
}

export function getTransportSessionHealth(updatedAtMs, nowMs = Date.now()) {
  if (!updatedAtMs || !Number.isFinite(updatedAtMs)) {
    return 'unknown';
  }

  const ageMs = Math.max(0, nowMs - updatedAtMs);
  if (ageMs < 60_000) {
    return 'fresh';
  }
  if (ageMs < 10 * 60_000) {
    return 'aging';
  }
  return 'stale';
}
