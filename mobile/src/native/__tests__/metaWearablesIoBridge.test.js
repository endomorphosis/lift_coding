const {
  META_WEARABLES_IO_BRIDGE_CONTRACT,
  META_WEARABLES_IO_BRIDGE_EVENT_TYPES,
  buildMetaWearablesIoBridgeRouteEvents,
  normalizeMetaWearablesIoBridgeEvent,
} = require('../metaWearablesIoBridge');

describe('Meta Wearables mobile I/O bridge route contract', () => {
  test('builds normalized route events for every required camera, audio, display, and failure state', () => {
    const events = buildMetaWearablesIoBridgeRouteEvents();
    const eventTypes = events.map((event) => event.eventType);

    expect(eventTypes).toEqual(META_WEARABLES_IO_BRIDGE_EVENT_TYPES);
    expect(eventTypes).toEqual(
      expect.arrayContaining([
        'camera',
        'microphone_route',
        'speaker_route',
        'headphone_route',
        'display',
        'permission',
        'unsupported',
        'disconnected',
        'stale_session',
        'degraded_route',
        'firmware_update',
        'dat_app_update',
        'fallback',
      ])
    );

    expect(events.every((event) => event.contract === META_WEARABLES_IO_BRIDGE_CONTRACT)).toBe(true);
    expect(events.every((event) => event.appBindingId === 'swissknife.meta-glasses.binding.mgw-417')).toBe(true);
    expect(events.every((event) => event.bridgeRoute.rawTransportIsIpfsLibp2pOrMcp === false)).toBe(true);
    expect(events.every((event) => event.policyDecision.decisionId)).toBe(true);
    expect(events.every((event) => event.controlPlaneDecision.decisionId)).toBe(true);
    expect(events.every((event) => event.receipts[0].receiptCid.includes('mgw417'))).toBe(true);
  });

  test('carries Bluetooth and Wi-Fi route labels without treating raw radio links as IPFS/libp2p transports', () => {
    const events = buildMetaWearablesIoBridgeRouteEvents();
    const microphone = events.find((event) => event.eventType === 'microphone_route');
    const speaker = events.find((event) => event.eventType === 'speaker_route');
    const headphone = events.find((event) => event.eventType === 'headphone_route');
    const display = events.find((event) => event.eventType === 'display');

    expect(microphone.bridgeRoute).toMatchObject({
      route: 'phone-os-audio-input',
      bluetoothRouteLabel: 'bluetooth-hfp-input',
      wifiRouteLabel: null,
      rawTransportIsIpfsLibp2pOrMcp: false,
    });
    expect(speaker.bridgeRoute.bluetoothRouteLabel).toBe('bluetooth-a2dp-output');
    expect(headphone.bridgeRoute.bluetoothRouteLabel).toBe('bluetooth-a2dp-output');
    expect(display.bridgeRoute).toMatchObject({
      route: 'dat-native-display',
      wifiRouteLabel: 'display-webapp-handoff',
      rawTransportIsIpfsLibp2pOrMcp: false,
    });
  });

  test('normalizes payload CIDs, privacy redaction, latency, backpressure, policy, and MCP++ receipts', () => {
    const event = normalizeMetaWearablesIoBridgeEvent({
      eventType: 'camera',
      appBindingId: 'app-binding-camera',
      correlationId: 'corr-camera',
      payloadCid: 'sha256:redacted-camera-photo',
      policyDecision: {
        outcome: 'allow',
        reason: 'foreground_camera_consent',
        decisionId: 'policy-camera',
      },
      controlPlaneDecision: {
        route: 'swissknife.mobile_orb.publish_camera_ref',
        operation: 'publish_camera_ref',
        decisionId: 'route-camera',
      },
      privacy: {
        redactionStrategy: 'faces_and_screens_redacted',
        redactedFields: ['faces', 'screens', 'raw_payload'],
        retention: 'session',
        metadataCid: 'sha256:camera-redaction-metadata',
      },
      flowControl: {
        latencyMs: 48,
        backpressure: 'none',
        queueDepth: 1,
        droppedMessages: 0,
      },
      receipts: ['sha256:camera-mcp-receipt'],
    });

    expect(event.payload).toEqual({
      cids: ['sha256:redacted-camera-photo'],
      cidEnabled: true,
      inlinePayloadRedacted: true,
      summary: null,
    });
    expect(event.privacy).toMatchObject({
      redactionStrategy: 'faces_and_screens_redacted',
      redactedFields: ['faces', 'screens', 'raw_payload'],
      retention: 'session',
      metadataCid: 'sha256:camera-redaction-metadata',
      rawPayloadIncluded: false,
    });
    expect(event.flowControl).toEqual({
      latencyMs: 48,
      backpressure: 'none',
      queueDepth: 1,
      droppedMessages: 0,
    });
    expect(event.policyDecision).toMatchObject({
      outcome: 'allow',
      reason: 'foreground_camera_consent',
      decisionId: 'policy-camera',
    });
    expect(event.controlPlaneDecision).toMatchObject({
      route: 'swissknife.mobile_orb.publish_camera_ref',
      operation: 'publish_camera_ref',
      decisionId: 'route-camera',
      capability: 'camera.photo_capture',
      allowed: true,
    });
    expect(event.receipts).toEqual([
      {
        kind: 'mcp++/mobile-bridge-route',
        receiptCid: 'sha256:camera-mcp-receipt',
        issuedBy: 'mobile-meta-wearables-io-bridge',
      },
    ]);
  });

  test('requires supported event types and app binding IDs', () => {
    expect(() =>
      normalizeMetaWearablesIoBridgeEvent({
        eventType: 'unknown',
        appBindingId: 'app-binding',
      })
    ).toThrow('Unsupported Meta Wearables I/O bridge event type');

    expect(() =>
      normalizeMetaWearablesIoBridgeEvent({
        eventType: 'display',
      })
    ).toThrow('require appBindingId');
  });
});
