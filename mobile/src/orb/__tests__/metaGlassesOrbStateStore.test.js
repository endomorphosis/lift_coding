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
  META_GLASSES_ORB_STATE_STORAGE_KEY,
  createMetaGlassesOrbStateStore,
  normalizeMetaGlassesOrbBridgeState,
} from '../metaGlassesOrbStateStore';

describe('metaGlassesOrbStateStore', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('normalizes binding and subscription snapshots for persistence', () => {
    expect(
      normalizeMetaGlassesOrbBridgeState({
        edge_session_id: 'edge-session-1',
        bindings: [
          {
            binding_handle: 'binding-1',
            service_interface_cid: 'sha256:service',
            operation: 'get_task_status',
            transport: 'mcp-server',
            orb_binding: {
              service_id: 'task_status_service',
              operation: 'get_task_status',
              transport: 'mcp-server',
            },
          },
          { service_interface_cid: 'missing-handle' },
        ],
        subscriptions: [
          {
            subscription_id: 'subscription-1',
            binding_handle: 'binding-1',
            operation: 'get_task_status',
            stream: 'task-status',
            generation_key: 'binding-1:get_task_status:task-status',
          },
          {
            subscription_id: 'orphan',
            binding_handle: 'missing-binding',
            operation: 'get_task_status',
          },
        ],
      })
    ).toEqual(
      expect.objectContaining({
        edge_session_id: 'edge-session-1',
        bindings: [
          expect.objectContaining({
            binding_handle: 'binding-1',
            service_interface_cid: 'sha256:service',
            operation: 'get_task_status',
          }),
        ],
        subscriptions: [
          expect.objectContaining({
            subscription_id: 'subscription-1',
            binding_handle: 'binding-1',
            stream: 'task-status',
          }),
        ],
      })
    );
  });

  it('loads, saves, and clears AsyncStorage bridge state', async () => {
    AsyncStorage.getItem.mockResolvedValue(
      JSON.stringify({
        edge_session_id: 'edge-session-1',
        bindings: [{ binding_handle: 'binding-1' }],
        subscriptions: [{ subscription_id: 'subscription-1', binding_handle: 'binding-1' }],
      })
    );
    AsyncStorage.setItem.mockResolvedValue(undefined);
    AsyncStorage.removeItem.mockResolvedValue(undefined);
    const store = createMetaGlassesOrbStateStore();

    await expect(store.load()).resolves.toEqual(
      expect.objectContaining({
        edge_session_id: 'edge-session-1',
        bindings: [expect.objectContaining({ binding_handle: 'binding-1' })],
      })
    );
    expect(AsyncStorage.getItem).toHaveBeenCalledWith(
      META_GLASSES_ORB_STATE_STORAGE_KEY
    );

    await store.save({
      edge_session_id: 'edge-session-1',
      bindings: [{ binding_handle: 'binding-1' }],
      subscriptions: [],
      saved_at: '2026-05-23T12:00:00.000Z',
    });
    expect(AsyncStorage.setItem).toHaveBeenCalledWith(
      META_GLASSES_ORB_STATE_STORAGE_KEY,
      expect.any(String)
    );
    expect(JSON.parse(AsyncStorage.setItem.mock.calls[0][1])).toEqual(
      expect.objectContaining({
        edge_session_id: 'edge-session-1',
        saved_at: '2026-05-23T12:00:00.000Z',
      })
    );

    await store.clear();
    expect(AsyncStorage.removeItem).toHaveBeenCalledWith(
      META_GLASSES_ORB_STATE_STORAGE_KEY
    );
  });
});
