jest.mock('@react-native-async-storage/async-storage', () => ({
  __esModule: true,
  default: {
    getItem: jest.fn(),
    setItem: jest.fn(),
  },
}));

import AsyncStorage from '@react-native-async-storage/async-storage';
import { getOrCreateLocalPeerId } from '../localPeerIdentity';

describe('localPeerIdentity', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('returns an existing persisted peer id when present', async () => {
    AsyncStorage.getItem.mockResolvedValue('12D3KooWlocalexisting1234');

    await expect(getOrCreateLocalPeerId()).resolves.toBe('12D3KooWlocalexisting1234');

    expect(AsyncStorage.getItem).toHaveBeenCalledWith('@handsfree_local_peer_id');
    expect(AsyncStorage.setItem).not.toHaveBeenCalled();
  });

  it('creates and persists a peer id when none exists', async () => {
    AsyncStorage.getItem.mockResolvedValue(null);
    AsyncStorage.setItem.mockResolvedValue(undefined);

    const peerId = await getOrCreateLocalPeerId();

    expect(peerId).toMatch(/^12D3KooWlocal[0-9a-f]{16}$/);
    expect(AsyncStorage.getItem).toHaveBeenCalledWith('@handsfree_local_peer_id');
    expect(AsyncStorage.setItem).toHaveBeenCalledWith('@handsfree_local_peer_id', peerId);
  });
});
