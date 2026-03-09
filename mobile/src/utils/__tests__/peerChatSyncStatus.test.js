import { formatPeerChatLastSynced, getPeerChatSyncHealth } from '../peerChatSyncStatus';

describe('peerChatSyncStatus', () => {
  it('returns never when nothing has been synced yet', () => {
    expect(formatPeerChatLastSynced(null, 1000)).toBe('never');
  });

  it('returns just now for very recent syncs', () => {
    expect(formatPeerChatLastSynced(9800, 10000)).toBe('just now');
  });

  it('formats seconds, minutes, and hours ago', () => {
    expect(formatPeerChatLastSynced(10000, 25000)).toBe('15s ago');
    expect(formatPeerChatLastSynced(10000, 130000)).toBe('2m ago');
    expect(formatPeerChatLastSynced(10000, 7210000)).toBe('2h ago');
  });

  it('classifies sync freshness for operator visibility', () => {
    expect(getPeerChatSyncHealth(null, 1000)).toBe('unknown');
    expect(getPeerChatSyncHealth(90_000, 100_000)).toBe('fresh');
    expect(getPeerChatSyncHealth(20_000, 100_000)).toBe('aging');
    expect(getPeerChatSyncHealth(10_000, 200_000)).toBe('stale');
  });
});
