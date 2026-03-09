export function formatPeerChatLastSynced(lastSyncedAt, nowMs = Date.now()) {
  if (!lastSyncedAt) {
    return 'never';
  }

  const ageMs = Math.max(0, nowMs - lastSyncedAt);
  const ageSeconds = Math.floor(ageMs / 1000);

  if (ageSeconds < 5) {
    return 'just now';
  }
  if (ageSeconds < 60) {
    return `${ageSeconds}s ago`;
  }

  const ageMinutes = Math.floor(ageSeconds / 60);
  if (ageMinutes < 60) {
    return `${ageMinutes}m ago`;
  }

  const ageHours = Math.floor(ageMinutes / 60);
  return `${ageHours}h ago`;
}

export function getPeerChatSyncHealth(lastSyncedAt, nowMs = Date.now()) {
  if (!lastSyncedAt) {
    return 'unknown';
  }

  const ageMs = Math.max(0, nowMs - lastSyncedAt);
  if (ageMs < 30_000) {
    return 'fresh';
  }
  if (ageMs < 120_000) {
    return 'aging';
  }
  return 'stale';
}
