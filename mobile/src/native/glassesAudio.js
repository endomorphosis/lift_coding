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
  const peers = new Map();
  const connectedPeers = new Set();

  const recordingListeners = new Set();
  const playbackListeners = new Set();
  const routeListeners = new Set();
  const peerDiscoveredListeners = new Set();
  const peerConnectedListeners = new Set();
  const peerDisconnectedListeners = new Set();
  const frameReceivedListeners = new Set();

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

  function emitPeerDiscovered(peer) {
    for (const listener of peerDiscoveredListeners) {
      try {
        listener({ peer });
      } catch {
        // ignore
      }
    }
  }

  function emitPeerConnected(event) {
    for (const listener of peerConnectedListeners) {
      try {
        listener(event);
      } catch {
        // ignore
      }
    }
  }

  function emitPeerDisconnected(event) {
    for (const listener of peerDisconnectedListeners) {
      try {
        listener(event);
      } catch {
        // ignore
      }
    }
  }

  function emitFrameReceived(event) {
    for (const listener of frameReceivedListeners) {
      try {
        listener(event);
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

    addPeerDiscoveredListener(listener) {
      peerDiscoveredListeners.add(listener);
      return createSubscription(() => peerDiscoveredListeners.delete(listener));
    },

    addPeerConnectedListener(listener) {
      peerConnectedListeners.add(listener);
      return createSubscription(() => peerConnectedListeners.delete(listener));
    },

    addPeerDisconnectedListener(listener) {
      peerDisconnectedListeners.add(listener);
      return createSubscription(() => peerDisconnectedListeners.delete(listener));
    },

    addFrameReceivedListener(listener) {
      frameReceivedListeners.add(listener);
      return createSubscription(() => frameReceivedListeners.delete(listener));
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

    async scanPeers(_timeoutMs = 5000) {
      return Array.from(peers.values());
    },

    async getPeerAdapterState() {
      return {
        transport: 'simulated',
        adapterAvailable: true,
        adapterEnabled: true,
        scanPermissionGranted: true,
        connectPermissionGranted: true,
        advertisePermissionGranted: true,
        advertising: false,
        scanning: false,
        state: 'simulated',
      };
    },

    async advertiseIdentity(identity) {
      if (!identity?.peerId) {
        throw new Error('peerId cannot be empty');
      }
      return {
        peerId: identity.peerId,
        displayName: identity.displayName || '',
      };
    },

    async connectPeer(peerRef) {
      if (!peerRef) {
        throw new Error('peerRef cannot be empty');
      }
      connectedPeers.add(peerRef);
      const peer = peers.get(peerRef);
      const event = {
        peerRef,
        peerId: peer?.peerId || '',
        transport: peer?.transport || 'simulated',
        connectedAt: Date.now(),
      };
      emitPeerConnected(event);
      return event;
    },

    async disconnectPeer(peerRef, reason = 'manual') {
      connectedPeers.delete(peerRef);
      emitPeerDisconnected({ peerRef, reason });
    },

    async sendFrame(peerRef, payloadBase64) {
      if (!connectedPeers.has(peerRef)) {
        throw new Error('peerRef is not connected');
      }
      if (!payloadBase64) {
        throw new Error('payloadBase64 cannot be empty');
      }
    },

    async simulatePeerDiscovery(peer) {
      if (!peer?.peerRef || !peer?.peerId) {
        throw new Error('peerRef and peerId are required');
      }
      const normalized = {
        peerRef: peer.peerRef,
        peerId: peer.peerId,
        displayName: peer.displayName,
        transport: peer.transport || 'simulated',
        rssi: peer.rssi,
      };
      peers.set(normalized.peerRef, normalized);
      emitPeerDiscovered(normalized);
      return normalized;
    },

    async simulatePeerConnection(peerRef) {
      return await this.connectPeer(peerRef);
    },

    async simulateFrameReceived(peerRef, payloadBase64, peerId) {
      emitFrameReceived({
        peerRef,
        peerId: peerId || peers.get(peerRef)?.peerId || '',
        payloadBase64,
      });
    },

    async resetPeerSimulation() {
      peers.clear();
      connectedPeers.clear();
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
