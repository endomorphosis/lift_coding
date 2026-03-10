const { summarizeMetaWearablesDat } = require('../metaWearablesDatCapabilities');

describe('summarizeMetaWearablesDat', () => {
  test('reports unavailable diagnostics cleanly', () => {
    expect(summarizeMetaWearablesDat(null)).toEqual({
      readiness: 'unavailable',
      availableCapabilities: [],
      unavailableCapabilities: ['session', 'camera', 'photo', 'video', 'audio'],
      availableSummary: 'none',
      matrixSummary: 'session:off, camera:off, photo:off, video:off, audio:off',
    });
  });

  test('distinguishes bridge-only and sdk-ready states', () => {
    expect(
      summarizeMetaWearablesDat({
        available: true,
        sdkLinked: false,
        sdkConfigured: false,
        capabilities: {
          session: true,
          camera: false,
          photoCapture: false,
          videoStream: false,
          audio: false,
        },
      })
    ).toMatchObject({
      readiness: 'bridge_ready',
      availableSummary: 'session',
      matrixSummary: 'session:on, camera:off, photo:off, video:off, audio:off',
    });

    expect(
      summarizeMetaWearablesDat({
        available: true,
        sdkLinked: true,
        sdkConfigured: true,
        capabilities: {
          session: true,
          camera: true,
          photoCapture: true,
          videoStream: true,
          audio: false,
        },
      })
    ).toMatchObject({
      readiness: 'sdk_ready',
      availableCapabilities: ['session', 'camera', 'photo', 'video'],
    });
  });
});