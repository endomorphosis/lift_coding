/**
 * Tests for GlassesAudio native module wrapper
 * 
 * These are unit tests for the JavaScript wrapper.
 * They test the fallback behavior and API surface.
 * 
 * Native functionality testing requires physical device with Meta AI Glasses.
 */

import { Platform } from 'react-native';
import GlassesAudio from '../index';

// Mock NativeModules
jest.mock('react-native', () => ({
  Platform: {
    OS: 'ios',
  },
  NativeModules: {
    GlassesAudioModule: null, // Simulate module not available
  },
  NativeEventEmitter: jest.fn(),
}));

describe('GlassesAudio Module', () => {
  describe('isAvailable()', () => {
    it('should return false when native module is not available', () => {
      expect(GlassesAudio.isAvailable()).toBe(false);
    });

    it('should check for iOS platform', () => {
      expect(GlassesAudio.isAvailable()).toBe(false);
    });
  });

  describe('API methods when module not available', () => {
    it('should throw error on startRouteMonitoring', async () => {
      await expect(
        GlassesAudio.startRouteMonitoring(() => {})
      ).rejects.toThrow('Glasses audio module not available');
    });

    it('should throw error on getCurrentRoute', async () => {
      await expect(
        GlassesAudio.getCurrentRoute()
      ).rejects.toThrow('Glasses audio module not available');
    });

    it('should throw error on isBluetoothConnected', async () => {
      await expect(
        GlassesAudio.isBluetoothConnected()
      ).rejects.toThrow('Glasses audio module not available');
    });

    it('should throw error on startRecording', async () => {
      await expect(
        GlassesAudio.startRecording(10.0)
      ).rejects.toThrow('Glasses audio module not available');
    });

    it('should throw error on playAudio', async () => {
      await expect(
        GlassesAudio.playAudio('file:///test.wav')
      ).rejects.toThrow('Glasses audio module not available');
    });
  });

  describe('stopRouteMonitoring when module not available', () => {
    it('should not throw when stopping monitoring', async () => {
      await expect(
        GlassesAudio.stopRouteMonitoring()
      ).resolves.toBeUndefined();
    });
  });
});

describe('API Contract', () => {
  it('should have all required methods', () => {
    const expectedMethods = [
      'isAvailable',
      'startRouteMonitoring',
      'stopRouteMonitoring',
      'getCurrentRoute',
      'isBluetoothConnected',
      'getDetailedRouteInfo',
      'startRecording',
      'stopRecording',
      'isRecording',
      'getRecordingDuration',
      'playAudio',
      'stopPlayback',
      'pausePlayback',
      'resumePlayback',
      'isPlaying',
      'getPlaybackProgress',
    ];

    expectedMethods.forEach(method => {
      expect(typeof GlassesAudio[method]).toBe('function');
    });
  });

  it('should export as default', () => {
    expect(GlassesAudio).toBeDefined();
  });
});

/**
 * Integration tests (require physical device)
 * 
 * These tests should be run manually on a physical iOS device
 * with Meta AI Glasses paired via Bluetooth.
 * 
 * Manual test procedure:
 * 
 * 1. Pair Meta AI Glasses via iOS Settings > Bluetooth
 * 2. Build development client: npx expo run:ios --device
 * 3. Run these tests:
 *    - Navigate to Glasses Diagnostics screen
 *    - Toggle Glasses mode (disable DEV mode)
 *    - Verify: Connection state shows "✓ Bluetooth Connected"
 *    - Verify: Audio route shows Bluetooth device name
 *    - Tap "Start Recording"
 *    - Speak into glasses microphone
 *    - Wait 10 seconds for auto-stop
 *    - Verify: Success message with file path
 *    - Tap "Play Last Recording"
 *    - Verify: Audio plays through glasses speakers
 *    - Verify: Audio is clear and audible
 *    - Disconnect glasses
 *    - Verify: Connection state changes to "⚠ No Bluetooth Device"
 *    - Reconnect glasses
 *    - Verify: Connection state changes back to "✓ Bluetooth Connected"
 * 
 * Expected results:
 * - All connection state changes detected
 * - Recording creates valid 16kHz WAV file
 * - Playback routes to Bluetooth speakers
 * - No errors or crashes
 */
