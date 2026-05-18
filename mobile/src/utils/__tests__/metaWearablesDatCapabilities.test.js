const { summarizeMetaWearablesDat } = require('../metaWearablesDatCapabilities');

describe('summarizeMetaWearablesDat', () => {
  test('reports unavailable diagnostics cleanly', () => {
    expect(summarizeMetaWearablesDat(null)).toEqual({
      readiness: 'unavailable',
      availableCapabilities: [],
      unavailableCapabilities: ['session', 'camera', 'photo', 'video', 'audio', 'display', 'display_video'],
      displayReady: false,
      sdkMeetsMinimum: true,
      configWarnings: [],
      availableSummary: 'none',
      matrixSummary: 'session:off, camera:off, photo:off, video:off, audio:off, display:off, display_video:off',
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
          display: false,
          displayVideo: false,
        },
      })
    ).toMatchObject({
      readiness: 'bridge_ready',
      availableSummary: 'session',
      matrixSummary:
        'session:on, camera:off, photo:off, video:off, audio:off, display:off, display_video:off',
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
          display: true,
          displayVideo: true,
        },
      })
    ).toMatchObject({
      readiness: 'sdk_ready',
      availableCapabilities: ['session', 'camera', 'photo', 'video', 'display', 'display_video'],
    });
  });
});
