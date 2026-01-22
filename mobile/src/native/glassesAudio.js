import { Audio } from 'expo-av';
import AsyncStorage from '@react-native-async-storage/async-storage';

const STORAGE_KEYS = {
  DEV_SIMULATE_GLASSES_AUDIO: '@handsfree_dev_simulate_glasses_audio',
};

function createSubscription(removeFn) {
  return { remove: removeFn };
}

function createSimulatedGlassesAudio() {
  let currentRecording = null;
  let currentSound = null;

  const recordingListeners = new Set();
  const playbackListeners = new Set();
  const routeListeners = new Set();

  function emitRecordingProgress(isRecording, duration) {
    for (const listener of recordingListeners) {
      try {
        listener({ isRecording, duration });
      } catch {
        // ignore
      }
    }
  }

  function emitPlaybackStatus(isPlaying, error) {
    for (const listener of playbackListeners) {
      try {
        listener(error ? { isPlaying, error } : { isPlaying });
      } catch {
        // ignore
      }
    }
  }

  function emitRouteChange(route) {
    for (const listener of routeListeners) {
      try {
        listener(route);
      } catch {
        // ignore
      }
    }
  }

  return {
    __simulated: true,

    async getAudioRoute() {
      const route = {
        inputDevice: 'Simulated glasses mic',
        outputDevice: 'Phone speaker',
        sampleRate: 48000,
        isBluetoothConnected: true,
      };
      emitRouteChange(route);
      return route;
    },

    addAudioRouteChangeListener(listener) {
      routeListeners.add(listener);
      return createSubscription(() => routeListeners.delete(listener));
    },

    addRecordingProgressListener(listener) {
      recordingListeners.add(listener);
      return createSubscription(() => recordingListeners.delete(listener));
    },

    addPlaybackStatusListener(listener) {
      playbackListeners.add(listener);
      return createSubscription(() => playbackListeners.delete(listener));
    },

    async startRecording(durationSeconds = 5, _audioSource) {
      const { status } = await Audio.requestPermissionsAsync();
      if (status !== 'granted') {
        throw new Error('Microphone permission not granted');
      }

      await Audio.setAudioModeAsync({
        allowsRecordingIOS: true,
        playsInSilentModeIOS: true,
        staysActiveInBackground: false,
      });

      if (currentRecording) {
        try {
          await currentRecording.stopAndUnloadAsync();
        } catch {
          // ignore
        }
        currentRecording = null;
      }

      emitRecordingProgress(true, 0);

      const { recording } = await Audio.Recording.createAsync(
        Audio.RecordingOptionsPresets.HIGH_QUALITY
      );
      currentRecording = recording;

      // Timer-based stop to match the native module contract.
      await new Promise((resolve) => setTimeout(resolve, Math.max(0, durationSeconds) * 1000));

      const result = await this.stopRecording();
      return result;
    },

    async stopRecording() {
      if (!currentRecording) {
        emitRecordingProgress(false, 0);
        return { uri: '', duration: 0, size: 0 };
      }

      let uri = '';
      try {
        await currentRecording.stopAndUnloadAsync();
        uri = currentRecording.getURI() || '';
      } finally {
        currentRecording = null;
      }

      emitRecordingProgress(false, 0);

      // Size is optional; return 0 if unavailable.
      return { uri, duration: 0, size: 0 };
    },

    async playAudio(fileUri) {
      try {
        await this.stopPlayback();

        await Audio.setAudioModeAsync({
          allowsRecordingIOS: false,
          playsInSilentModeIOS: true,
          staysActiveInBackground: false,
        });

        emitPlaybackStatus(true);
        const { sound } = await Audio.Sound.createAsync({ uri: fileUri }, { shouldPlay: true });
        currentSound = sound;

        sound.setOnPlaybackStatusUpdate((status) => {
          if (!status || !status.isLoaded) return;
          if (status.didJustFinish) {
            emitPlaybackStatus(false);
          }
        });
      } catch (e) {
        emitPlaybackStatus(false, String(e?.message || e));
        throw e;
      }
    },

    async stopPlayback() {
      if (!currentSound) {
        emitPlaybackStatus(false);
        return;
      }

      try {
        await currentSound.stopAsync();
      } catch {
        // ignore
      }
      try {
        await currentSound.unloadAsync();
      } catch {
        // ignore
      }
      currentSound = null;
      emitPlaybackStatus(false);
    },
  };
}

async function shouldSimulate() {
  try {
    const v = await AsyncStorage.getItem(STORAGE_KEYS.DEV_SIMULATE_GLASSES_AUDIO);
    if (v === null) return false;
    return v === 'true';
  } catch {
    return false;
  }
}

export async function setSimulateGlassesAudio(enabled) {
  await AsyncStorage.setItem(STORAGE_KEYS.DEV_SIMULATE_GLASSES_AUDIO, enabled ? 'true' : 'false');
}

export async function getSimulateGlassesAudio() {
  return await shouldSimulate();
}

// Export an object that prefers the native expo-glasses-audio module when present.
// If not present, it automatically falls back to a JS simulation (expo-av).
let cached = null;

export async function getGlassesAudio() {
  if (cached) return cached;

  let native = null;
  try {
    native = require('expo-glasses-audio').default;
  } catch {
    native = null;
  }

  const simulate = await shouldSimulate();
  if (!native || simulate) {
    cached = createSimulatedGlassesAudio();
    return cached;
  }

  cached = native;
  return cached;
}

export function clearGlassesAudioCache() {
  cached = null;
}

export { STORAGE_KEYS as GLASSES_AUDIO_STORAGE_KEYS };
