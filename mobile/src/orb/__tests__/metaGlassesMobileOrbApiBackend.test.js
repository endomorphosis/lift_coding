jest.mock('../../api/client', () => ({
  registerMobileOrbEdgeCapabilities: jest.fn(async (payload) => ({
    operation: 'register',
    payload,
  })),
  publishMobileOrbGlassesEvent: jest.fn(async (payload) => ({
    operation: 'publish_event',
    payload,
  })),
  bindMobileOrbService: jest.fn(async (payload) => ({
    operation: 'bind_service',
    payload,
  })),
  invokeMobileOrbService: jest.fn(async (payload) => ({
    operation: 'invoke_service',
    payload,
  })),
  subscribeMobileOrbServiceUpdates: jest.fn(async (payload) => ({
    operation: 'subscribe_updates',
    payload,
  })),
  dispatchMobileOrbGlassesResponse: jest.fn(async (payload) => ({
    operation: 'dispatch_response',
    payload,
  })),
  revokeMobileOrbBinding: jest.fn(async (payload) => ({
    operation: 'revoke_binding',
    payload,
  })),
  getMobileOrbDiagnostics: jest.fn(async (payload) => ({
    operation: 'diagnostics',
    payload,
  })),
}));

import {
  bindMobileOrbService,
  dispatchMobileOrbGlassesResponse,
  getMobileOrbDiagnostics,
  invokeMobileOrbService,
  publishMobileOrbGlassesEvent,
  registerMobileOrbEdgeCapabilities,
  revokeMobileOrbBinding,
  subscribeMobileOrbServiceUpdates,
} from '../../api/client';
import { createMetaGlassesMobileOrbApiBackend } from '../metaGlassesMobileOrbApiBackend';

describe('createMetaGlassesMobileOrbApiBackend', () => {
  afterEach(() => {
    jest.clearAllMocks();
  });

  it('maps ORB backend methods to mobile API helpers without reshaping payloads', async () => {
    const backend = createMetaGlassesMobileOrbApiBackend();

    const calls = [
      [
        backend.registerEdgeCapabilities,
        registerMobileOrbEdgeCapabilities,
        { edge_id: 'edge', platform: 'ios' },
      ],
      [
        backend.publishGlassesEvent,
        publishMobileOrbGlassesEvent,
        { edge_session_id: 'session', event_type: 'captouch' },
      ],
      [
        backend.bindService,
        bindMobileOrbService,
        { edge_session_id: 'session', service_interface_cid: 'sha256:service' },
      ],
      [
        backend.invokeService,
        invokeMobileOrbService,
        { binding_handle: 'binding', operation: 'get_task_status' },
      ],
      [
        backend.subscribeServiceUpdates,
        subscribeMobileOrbServiceUpdates,
        { binding_handle: 'binding', operation: 'get_task_status' },
      ],
      [
        backend.dispatchGlassesResponse,
        dispatchMobileOrbGlassesResponse,
        { edge_session_id: 'session', result: {} },
      ],
      [
        backend.revokeBinding,
        revokeMobileOrbBinding,
        { binding_handle: 'binding', reason: 'done' },
      ],
      [
        backend.getDiagnostics,
        getMobileOrbDiagnostics,
        { edge_session_id: 'session' },
      ],
    ];

    const responses = [];
    for (const [method, helper, payload] of calls) {
      responses.push(await method(payload));
      expect(helper).toHaveBeenCalledWith(payload);
    }

    expect(responses.map((response) => response.operation)).toEqual([
      'register',
      'publish_event',
      'bind_service',
      'invoke_service',
      'subscribe_updates',
      'dispatch_response',
      'revoke_binding',
      'diagnostics',
    ]);
  });
});
