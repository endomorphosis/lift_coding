jest.mock('@react-native-async-storage/async-storage', () => ({
  __esModule: true,
  default: {
    getItem: jest.fn(),
    setItem: jest.fn(),
    removeItem: jest.fn(),
  },
}));

import AsyncStorage from '@react-native-async-storage/async-storage';
import {
  META_GLASSES_ORB_EDGE_SESSION_STORAGE_KEY,
  createMetaGlassesOrbEdgeSessionStore,
  normalizeMetaGlassesOrbEdgeSession,
} from '../metaGlassesOrbEdgeSession';

describe('metaGlassesOrbEdgeSession', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('normalizes persisted edge session snapshots', () => {
    expect(
      normalizeMetaGlassesOrbEdgeSession({
        edge_session_id: 'edge-session-1',
        edge_id: 'handsfree-mobile-orb-edge',
        platform: 'ios',
        policy_cid: 'sha256:policy',
        accepted_interface_cids: ['sha256:mobile', null, 'sha256:display'],
        dat_capabilities: {
          session: true,
          display: true,
        },
      })
    ).toEqual({
      edge_session_id: 'edge-session-1',
      edge_id: 'handsfree-mobile-orb-edge',
      platform: 'ios',
      device_id: null,
      policy_cid: 'sha256:policy',
      accepted_interface_cids: ['sha256:mobile', 'sha256:display'],
      dat_capabilities: {
        session: true,
        camera: false,
        photoCapture: false,
        videoStream: false,
        audio: false,
        display: true,
        displayVideo: false,
        webAppDisplay: false,
      },
      registered_at: '1970-01-01T00:00:00.000Z',
      expires_at: null,
    });
  });

  it('returns null for invalid persisted sessions', () => {
    expect(normalizeMetaGlassesOrbEdgeSession({ policy_cid: 'sha256:policy' })).toBeNull();
    expect(normalizeMetaGlassesOrbEdgeSession({ edge_session_id: 'edge' })).toBeNull();
  });

  it('loads and sanitizes a stored session', async () => {
    AsyncStorage.getItem.mockResolvedValue(
      JSON.stringify({
        edge_session_id: 'edge-session-1',
        platform: 'bogus',
        policy_cid: 'sha256:policy',
        accepted_interface_cids: ['sha256:mobile'],
        dat_capabilities: { audio: true },
      })
    );
    const store = createMetaGlassesOrbEdgeSessionStore();

    await expect(store.load()).resolves.toEqual(
      expect.objectContaining({
        edge_session_id: 'edge-session-1',
        edge_id: 'handsfree-mobile-orb-edge',
        platform: 'simulator',
        dat_capabilities: expect.objectContaining({
          audio: true,
          display: false,
        }),
      })
    );
    expect(AsyncStorage.getItem).toHaveBeenCalledWith(
      META_GLASSES_ORB_EDGE_SESSION_STORAGE_KEY
    );
  });

  it('persists normalized sessions and clears storage', async () => {
    AsyncStorage.setItem.mockResolvedValue(undefined);
    AsyncStorage.removeItem.mockResolvedValue(undefined);
    const store = createMetaGlassesOrbEdgeSessionStore();

    await expect(
      store.save({
        edge_session_id: 'edge-session-1',
        edge_id: 'edge',
        platform: 'android',
        policy_cid: 'sha256:policy',
        accepted_interface_cids: ['sha256:mobile'],
        dat_capabilities: { session: true },
        registered_at: '2026-05-23T12:00:00.000Z',
      })
    ).resolves.toEqual(
      expect.objectContaining({
        edge_session_id: 'edge-session-1',
        platform: 'android',
      })
    );

    expect(AsyncStorage.setItem).toHaveBeenCalledWith(
      META_GLASSES_ORB_EDGE_SESSION_STORAGE_KEY,
      expect.any(String)
    );
    expect(JSON.parse(AsyncStorage.setItem.mock.calls[0][1])).toEqual(
      expect.objectContaining({
        edge_session_id: 'edge-session-1',
        platform: 'android',
      })
    );

    await store.clear();
    expect(AsyncStorage.removeItem).toHaveBeenCalledWith(
      META_GLASSES_ORB_EDGE_SESSION_STORAGE_KEY
    );
  });
});
