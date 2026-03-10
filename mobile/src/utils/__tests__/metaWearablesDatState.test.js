const { mergeMetaWearablesDatState } = require('../metaWearablesDatState');

describe('mergeMetaWearablesDatState', () => {
  test('preserves existing diagnostics fields when the event is partial', () => {
    expect(
      mergeMetaWearablesDatState(
        {
          sessionState: 'idle',
          activeDeviceId: null,
          selectedDeviceId: 'AA:BB',
          selectedDeviceName: 'Ray-Ban Meta',
          targetConnectionState: 'selected',
          targetLastSeenAt: 10,
          targetRssi: -45,
          sdkLinked: true,
        },
        {
          state: 'target_connected',
          deviceId: 'AA:BB',
          targetConnectionState: 'connected',
        }
      )
    ).toEqual({
      sessionState: 'target_connected',
      activeDeviceId: 'AA:BB',
      selectedDeviceId: 'AA:BB',
      selectedDeviceName: 'Ray-Ban Meta',
      targetConnectionState: 'connected',
      targetLastSeenAt: 10,
      targetRssi: -45,
      sdkLinked: true,
    });
  });

  test('returns the current state when the event is invalid', () => {
    const current = { sessionState: 'idle' };
    expect(mergeMetaWearablesDatState(current, null)).toBe(current);
  });
});