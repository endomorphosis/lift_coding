jest.mock('expo-modules-core', () => {
  class MockEventEmitter {
    addListener(_eventName, listener) {
      return {
        remove() {
          return listener;
        },
      };
    }
  }

  return {
    EventEmitter: MockEventEmitter,
    requireOptionalNativeModule: jest.fn(),
  };
});

describe('expo-meta-wearables-dat module wrapper', () => {
  afterEach(() => {
    jest.resetModules();
    delete process.env.EXPO_OS;
  });

  test('returns safe fallbacks when native module is absent', async () => {
    process.env.EXPO_OS = 'android';
    const { requireOptionalNativeModule } = require('expo-modules-core');
    requireOptionalNativeModule.mockReturnValue(undefined);

    const module = require('..').default;

    await expect(module.isDatAvailable()).resolves.toBe(false);
    await expect(module.getConfiguration()).resolves.toMatchObject({
      sdkLinked: false,
      sdkConfigured: false,
      integrationMode: 'unavailable',
    });
    await expect(module.getCapabilities()).resolves.toEqual({
      session: false,
      camera: false,
      photoCapture: false,
      videoStream: false,
      audio: false,
    });
    await expect(module.getDiagnostics()).resolves.toMatchObject({
      available: false,
      sessionState: 'unavailable',
      targetConnectionState: 'unselected',
      knownDeviceCount: 0,
    });
    await expect(module.capturePhoto()).resolves.toMatchObject({
      action: 'capture_photo',
      supported: false,
    });
    await expect(module.startVideoStream()).resolves.toMatchObject({
      action: 'start_video_stream',
      supported: false,
    });
    await expect(module.reconnectSelectedDeviceTarget()).resolves.toMatchObject({
      mode: 'unavailable',
      targetConnectionState: 'unselected',
    });
    expect(module.addStateListener(() => {})).toMatchObject({
      remove: expect.any(Function),
    });
  });

  test('delegates to the native module when linked', async () => {
    const nativeModule = {
      isDatAvailable: jest.fn(async () => true),
      getConfiguration: jest.fn(async () => ({
        platform: 'ios',
        sdkLinked: true,
        sdkConfigured: true,
        analyticsOptOut: true,
        sdkVersion: '0.5.0',
        applicationId: 'handsfree-dev',
        provider: 'internal_bridge',
        integrationMode: 'sdk_reflection',
      })),
      getCapabilities: jest.fn(async () => ({
        session: true,
        camera: true,
        photoCapture: true,
        videoStream: false,
        audio: false,
      })),
      getDiagnostics: jest.fn(async () => ({
        available: true,
        platform: 'ios',
        sdkLinked: true,
        sdkConfigured: true,
        analyticsOptOut: true,
        sdkVersion: '0.5.0',
        applicationId: 'handsfree-dev',
        provider: 'internal_bridge',
        integrationMode: 'sdk_reflection',
        capabilities: {
          session: true,
          camera: true,
          photoCapture: true,
          videoStream: false,
          audio: false,
        },
        sessionState: 'target_ready',
      })),
      capturePhoto: jest.fn(async () => ({
        state: 'ready',
        mode: 'sdk_reflection',
        supported: true,
        action: 'capture_photo',
        message: 'Captured photo.',
      })),
    };

    const { requireOptionalNativeModule } = require('expo-modules-core');
    requireOptionalNativeModule.mockReturnValue(nativeModule);

    const module = require('..').default;

    await expect(module.isDatAvailable()).resolves.toBe(true);
    await expect(module.getConfiguration()).resolves.toMatchObject({
      sdkLinked: true,
      sdkConfigured: true,
      integrationMode: 'sdk_reflection',
    });
    await expect(module.getCapabilities()).resolves.toMatchObject({
      camera: true,
      photoCapture: true,
    });
    await expect(module.getDiagnostics()).resolves.toMatchObject({
      available: true,
      sessionState: 'target_ready',
    });
    await expect(module.capturePhoto()).resolves.toMatchObject({
      action: 'capture_photo',
      supported: true,
      message: 'Captured photo.',
    });
  });
});