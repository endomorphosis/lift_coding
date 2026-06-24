const {
  MCP_PLUS_PLUS_ENVELOPE_PROFILE,
  META_GLASSES_CONTROL_PLANE_DEVICES,
  META_GLASSES_CONTROL_PLANE_EVENT_TYPES,
  META_GLASSES_TRANSPORT_ASSUMPTIONS,
  buildMetaGlassesControlPlaneEvent,
} = require('../metaGlassesMultimodalIoTransportContract');

describe('Meta glasses multimodal IO transport contract', () => {
  test('defines the hardware-free control-plane devices and transport assumptions', () => {
    expect(META_GLASSES_CONTROL_PLANE_DEVICES).toEqual(
      expect.arrayContaining([
        'camera',
        'microphone',
        'headphones',
        'display',
        'captouch',
        'Neural Band',
      ])
    );
    expect(META_GLASSES_CONTROL_PLANE_EVENT_TYPES).toEqual(
      expect.arrayContaining([
        'camera.photo_ref',
        'microphone.route_state',
        'headphones.route_state',
        'display.lifecycle_state',
        'captouch.intent',
        'Neural Band.intent',
        'transport.handoff',
      ])
    );
    expect(META_GLASSES_TRANSPORT_ASSUMPTIONS.ipfsLibp2pHandoff).toContain(
      'IPFS CIDs'
    );
    expect(META_GLASSES_TRANSPORT_ASSUMPTIONS.mcpPlusPlus).toContain('MCP++');
  });

  test('builds an MCP++ compatible mock control-plane event envelope', () => {
    const envelope = buildMetaGlassesControlPlaneEvent({
      event_type: 'Neural Band.intent',
      device: 'Neural Band',
      edge_session_id: 'edge-session-1',
      app_binding_id: 'app-binding-neural',
      correlation_id: 'corr-1',
      payload: { key: 'ArrowRight' },
      handoff: {
        ipfs_cids: ['bafyreceipt'],
        libp2p_peer_id: 'peer-1',
        libp2p_session_id: 'session-1',
      },
      fallback: { dat_available: false, state: 'mock_ready' },
    });

    expect(envelope.profile).toBe(MCP_PLUS_PLUS_ENVELOPE_PROFILE);
    expect(envelope.control_plane.operation).toBe('publish_glasses_event');
    expect(envelope.transport.bluetooth).toBe('route-state');
    expect(envelope.transport.wifi).toBe('app-level-handoff');
    expect(envelope.handoff.ipfs_cids).toEqual(['bafyreceipt']);
    expect(envelope.handoff.libp2p_peer_id).toBe('peer-1');
    expect(envelope.fallback.dat_available).toBe(false);
  });
});
