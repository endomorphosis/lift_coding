import { Alert, AppState, ScrollView, StyleSheet, Switch, Text, TouchableOpacity, View } from 'react-native';
import React, { useEffect, useState, useRef } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Audio } from 'expo-av';
import * as FileSystem from 'expo-file-system';
import {
  deleteDevTransportSession,
  fetchTTS,
  getDevTransportSessions,
  postDevPeerEnvelope,
  sendAudioCommand,
  uploadDevAudio,
} from '../api/client';
import { getDebugState, simulateNotificationForDev } from '../push';
import ExpoGlassesAudio from 'expo-glasses-audio';
import { getWearablesBridge } from '../native/wearablesBridge';
import {
  createAckEnvelope,
  createChatMessageEnvelope,
  createHandshakeEnvelope,
  createSessionId,
  decodeEnvelopeBase64,
  encodeEnvelopeBase64,
} from '../utils/peerEnvelope';
import { getOrCreateLocalPeerId } from '../utils/localPeerIdentity';
import { buildPeerBackendValidationResult, replayBackendAckFrame } from '../utils/peerDiagnostics';
import {
  findMatchingTransportSession,
  formatTransportSessionAge,
  getTransportSessionPeerTarget,
  getTransportSessionHealth,
  isStaleTransportSessionSuspected,
} from '../utils/peerTransportSessions';

const DEV_MODE_KEY = '@glasses_dev_mode';
const NATIVE_RECORDING_DURATION_SECONDS = 10;
const NATIVE_MODULE_NOT_AVAILABLE_MESSAGE = 'Native glasses audio module not available. Please switch to DEV mode or ensure the native module is properly installed.';
const PEER_TEST_PAYLOAD_BASE64 = 'cGluZw==';
// Supported audio formats that the backend can accept
// Note: 'caf' is not included here as it needs to be converted to 'm4a' (see inferAudioFormatFromUri)
const SUPPORTED_AUDIO_FORMATS = ['wav', 'mp3', 'opus', 'm4a'];
// Regex pattern to match audio file extensions before query params or hash fragments
// Matches: .wav, .mp3, .opus, or .m4a followed by end of string, ?, or #
// Group 1 captures the format (e.g., 'wav', 'mp3', 'opus', 'm4a')
const AUDIO_FORMAT_REGEX = new RegExp(`\\.(${SUPPORTED_AUDIO_FORMATS.join('|')})(?=\\?|#|$)`);
const NATIVE_MODULE_REQUIRED_METHODS = [
  'getAudioRoute',
  'startRecording',
  'stopRecording',
  'playAudio',
  'stopPlayback',
  'addRecordingProgressListener',
  'addPlaybackStatusListener',
  'getPeerAdapterState',
  'scanPeers',
  'advertiseIdentity',
  'connectPeer',
  'sendFrame',
  'addPeerDiscoveredListener',
  'addPeerConnectedListener',
  'addPeerDisconnectedListener',
  'addFrameReceivedListener',
];

function normalizeLocalFileUriForFileSystem(uri) {
  if (!uri || typeof uri !== 'string') return uri;
  if (uri.startsWith('file://')) return uri;
  if (uri.startsWith('/')) return `file://${uri}`;
  return uri;
}

function inferAudioFormatFromUri(uri) {
  const lower = String(uri || '').toLowerCase();

  // Remove query parameters and fragments to focus on the path / filename.
  const pathWithoutQueryOrFragment = lower.split('?')[0].split('#')[0];

  const lastDotIndex = pathWithoutQueryOrFragment.lastIndexOf('.');
  if (lastDotIndex === -1) {
    // No extension found; fall back to default.
    return 'm4a';
  }

  const ext = pathWithoutQueryOrFragment.slice(lastDotIndex + 1);
  switch (ext) {
    case 'wav':
    case 'mp3':
    case 'm4a':
    case 'aac':
      return ext;
    default:
      // Unknown extension; keep existing behavior of defaulting to m4a.
      return 'm4a';
  }
}

export default function GlassesDiagnosticsScreen() {
  const [devMode, setDevMode] = useState(false);
  const [audioRoute, setAudioRoute] = useState('Unknown');
  const [connectionState, setConnectionState] = useState('Checking...');
  const [lastError, setLastError] = useState(null);
  const [isRecording, setIsRecording] = useState(false);
  const [recording, setRecording] = useState(null);
  const [lastRecordingUri, setLastRecordingUri] = useState(null);
  const [sound, setSound] = useState(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [commandResponse, setCommandResponse] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [pushDebugState, setPushDebugState] = useState(null);
  const [nativeModuleAvailable, setNativeModuleAvailable] = useState(false);
  const [wearablesBridgeAvailable, setWearablesBridgeAvailable] = useState(false);
  const [wearablesDiagnostics, setWearablesDiagnostics] = useState(null);
  const [wearablesSessionState, setWearablesSessionState] = useState('unknown');
  const [discoveredPeers, setDiscoveredPeers] = useState([]);
  const [selectedPeerRef, setSelectedPeerRef] = useState(null);
  const [activePeer, setActivePeer] = useState(null);
  const [lastPeerEvent, setLastPeerEvent] = useState('No peer activity yet');
  const [isScanningPeers, setIsScanningPeers] = useState(false);
  const [peerAdapterState, setPeerAdapterState] = useState(null);
  const [advertisedPeerIdentity, setAdvertisedPeerIdentity] = useState(null);
  const [autoValidateInboundPeerFrames, setAutoValidateInboundPeerFrames] = useState(false);
  const [lastInboundBackendValidation, setLastInboundBackendValidation] = useState(null);
  const [lastOutboundPeerFrameBase64, setLastOutboundPeerFrameBase64] = useState(null);
  const [lastOutboundPeerEnvelope, setLastOutboundPeerEnvelope] = useState(null);
  const [lastInboundPeerEnvelope, setLastInboundPeerEnvelope] = useState(null);
  const [peerBackendValidation, setPeerBackendValidation] = useState(null);
  const [isValidatingPeerFrame, setIsValidatingPeerFrame] = useState(false);
  const [transportSessions, setTransportSessions] = useState([]);
  const [isLoadingTransportSessions, setIsLoadingTransportSessions] = useState(false);
  const [isClearingTransportSession, setIsClearingTransportSession] = useState(false);
  const [localPeerId, setLocalPeerId] = useState(`12D3KooWlocal${createSessionId()}`);
  const peerSessionRef = useRef(createSessionId());
  const peerConversationRef = useRef(`chat-${createSessionId()}`);
  const localPeerIdRef = useRef(localPeerId);
  const soundRef = useRef(null);
  const pendingTtsTempUriRef = useRef(null);
  const recordingPromiseRef = useRef(null);
  const appIsActiveRef = useRef(AppState.currentState === 'active');
  const wearablesBridgeRef = useRef(null);
  const transportSessionTarget = getTransportSessionPeerTarget({
    activePeer,
    selectedPeerRef,
    discoveredPeers,
  });
  const matchedTransportSession = findMatchingTransportSession(transportSessions, transportSessionTarget);
  const staleTransportSessionSuspected = isStaleTransportSessionSuspected({
    targetPeer: transportSessionTarget,
    matchedSession: matchedTransportSession,
    activePeer,
  });

  const handleInboundPeerFrame = async (event, envelope = null) => {
    if (!event?.peerRef || !autoValidateInboundPeerFrames) {
      return;
    }

    try {
      const response = await postDevPeerEnvelope(event.peerRef, event.payloadBase64);
      const validationResult = buildPeerBackendValidationResult(response);
      setLastInboundBackendValidation(validationResult);
      if (validationResult.ack_frame_base64) {
        await ExpoGlassesAudio.sendFrame(event.peerRef, validationResult.ack_frame_base64);
        setLastPeerEvent(
          `Auto-acked ${validationResult.kind} for ${event.peerId || event.peerRef}`
        );
      } else if (envelope?.kind) {
        setLastPeerEvent(
          `Validated inbound ${envelope.kind} for ${event.peerId || event.peerRef}`
        );
      }
    } catch (error) {
      setLastError(`Inbound backend validation failed: ${error.message}`);
    }
  };

  useEffect(() => {
    (async () => {
      try {
        const saved = await AsyncStorage.getItem(DEV_MODE_KEY);
        if (saved !== null) setDevMode(JSON.parse(saved));
      } catch {
        // ignore
      }
      try {
        const resolvedLocalPeerId = await getOrCreateLocalPeerId();
        localPeerIdRef.current = resolvedLocalPeerId;
        setLocalPeerId(resolvedLocalPeerId);
        try {
          const response = await getDevTransportSessions();
          setTransportSessions(Array.isArray(response?.sessions) ? response.sessions : []);
        } catch {
          // keep transport-session diagnostics best-effort
        }
      } catch {
        // keep fallback in-memory peer id
      }
      // Check if native module is available
      try {
        if (ExpoGlassesAudio) {
          const allMethodsAvailable = NATIVE_MODULE_REQUIRED_METHODS.every(
            method => typeof ExpoGlassesAudio[method] === 'function'
          );
          if (allMethodsAvailable) {
            setNativeModuleAvailable(true);
          }
        }
      } catch {
        setNativeModuleAvailable(false);
      }
      await checkAudioRoute();
      await refreshPeerAdapterState();
      await refreshWearablesDiagnostics();
    })();

    // Fetch initial debug state immediately
    try {
      const state = getDebugState();
      setPushDebugState(state);
    } catch (error) {
      console.error('Failed to get initial push debug state:', error);
    }

    // Track app state to pause polling when backgrounded
    // Initialize based on current state rather than defaulting to true
    const appStateSubscription = AppState.addEventListener('change', (nextAppState) => {
      appIsActiveRef.current = nextAppState === 'active';
    });

    // Periodically refresh push debug state (every 5 seconds) but only when active
    const interval = setInterval(() => {
      if (!appIsActiveRef.current) {
        return; // Skip polling when app is backgrounded
      }
      try {
        const state = getDebugState();
        setPushDebugState(state);
      } catch (error) {
        console.error('Failed to get push debug state:', error);
      }
    }, 5000);

    return () => {
      clearInterval(interval);
      appStateSubscription.remove();
      // Use ref to ensure we cleanup the latest sound instance
      if (soundRef.current) {
        soundRef.current.unloadAsync().catch(() => {});
        soundRef.current = null;
      }
      if (pendingTtsTempUriRef.current) {
        FileSystem.deleteAsync(pendingTtsTempUriRef.current, { idempotent: true }).catch(() => {});
        pendingTtsTempUriRef.current = null;
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    let subscription = null;
    let cancelled = false;

    (async () => {
      try {
        const module = wearablesBridgeRef.current || (await getWearablesBridge());
        if (cancelled || !module?.addStateListener) {
          return;
        }
        wearablesBridgeRef.current = module;
        subscription = module.addStateListener((event) => {
          setWearablesSessionState(event?.state || 'unknown');
          refreshWearablesDiagnostics().catch(() => {});
        });
      } catch {
        // keep DAT diagnostics best-effort
      }
    })();

    return () => {
      cancelled = true;
      try {
        subscription?.remove?.();
      } catch {
        // ignore
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (devMode || !nativeModuleAvailable) {
      return;
    }

    let recordingSub = null;
    let playbackSub = null;
    let peerDiscoveredSub = null;
    let peerConnectedSub = null;
    let peerDisconnectedSub = null;
    let frameReceivedSub = null;

    try {
      recordingSub = ExpoGlassesAudio.addRecordingProgressListener((event) => {
        if (!event || typeof event !== 'object') return;
        if (typeof event.isRecording === 'boolean') {
          setIsRecording(event.isRecording);
        }
      });
    } catch (error) {
      console.warn('Failed to subscribe to recording progress:', error);
    }

    try {
      playbackSub = ExpoGlassesAudio.addPlaybackStatusListener((event) => {
        if (!event || typeof event !== 'object') return;
        if (typeof event.isPlaying === 'boolean') {
          setIsPlaying(event.isPlaying);
          if (event.isPlaying === false && pendingTtsTempUriRef.current) {
            const tempUri = pendingTtsTempUriRef.current;
            pendingTtsTempUriRef.current = null;
            FileSystem.deleteAsync(tempUri, { idempotent: true }).catch(() => {});
          }
        }
        if (event.error) {
          setLastError(`Playback error: ${event.error}`);
        }
      });
    } catch (error) {
      console.warn('Failed to subscribe to playback status:', error);
    }

    try {
      peerDiscoveredSub = ExpoGlassesAudio.addPeerDiscoveredListener((event) => {
        const peer = event?.peer;
        if (!peer?.peerRef) return;
        setDiscoveredPeers((current) => {
          const next = current.filter((item) => item.peerRef !== peer.peerRef);
          return [...next, peer];
        });
        setLastPeerEvent(`Discovered ${peer.displayName || peer.peerId || peer.peerRef}`);
      });
    } catch (error) {
      console.warn('Failed to subscribe to peer discovery:', error);
    }

    try {
      peerConnectedSub = ExpoGlassesAudio.addPeerConnectedListener((event) => {
        if (!event?.peerRef) return;
        setActivePeer(event);
        setLastPeerEvent(`Connected to ${event.peerId || event.peerRef}`);
      });
    } catch (error) {
      console.warn('Failed to subscribe to peer connection:', error);
    }

    try {
      peerDisconnectedSub = ExpoGlassesAudio.addPeerDisconnectedListener((event) => {
        if (event?.peerRef && activePeer?.peerRef === event.peerRef) {
          setActivePeer(null);
        }
        setLastPeerEvent(`Disconnected ${event?.peerRef || 'peer'} (${event?.reason || 'unknown'})`);
      });
    } catch (error) {
      console.warn('Failed to subscribe to peer disconnects:', error);
    }

    try {
      frameReceivedSub = ExpoGlassesAudio.addFrameReceivedListener((event) => {
        if (!event?.peerRef) return;
        try {
          const envelope = decodeEnvelopeBase64(event.payloadBase64);
          setLastInboundPeerEnvelope(envelope);
          setLastPeerEvent(
            `Frame received from ${event.peerId || event.peerRef}: ${envelope.kind} ${envelope.message_id}`
          );
          handleInboundPeerFrame(event, envelope).catch(() => {});
        } catch {
          setLastInboundPeerEnvelope(null);
          setLastPeerEvent(`Frame received from ${event.peerId || event.peerRef}: ${event.payloadBase64}`);
          handleInboundPeerFrame(event, null).catch(() => {});
        }
      });
    } catch (error) {
      console.warn('Failed to subscribe to peer frames:', error);
    }

    return () => {
      try {
        recordingSub?.remove?.();
      } catch {
        // ignore
      }
      try {
        playbackSub?.remove?.();
      } catch {
        // ignore
      }
      try {
        peerDiscoveredSub?.remove?.();
      } catch {
        // ignore
      }
      try {
        peerConnectedSub?.remove?.();
      } catch {
        // ignore
      }
      try {
        peerDisconnectedSub?.remove?.();
      } catch {
        // ignore
      }
      try {
        frameReceivedSub?.remove?.();
      } catch {
        // ignore
      }
    };
  }, [activePeer?.peerRef, autoValidateInboundPeerFrames, devMode, nativeModuleAvailable]);

  useEffect(() => {
    checkAudioRoute();
    refreshPeerAdapterState();
    refreshWearablesDiagnostics();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [devMode]);

  const toggleDevMode = async (value) => {
    setDevMode(value);
    try {
      await AsyncStorage.setItem(DEV_MODE_KEY, JSON.stringify(value));
    } catch (error) {
      setLastError(`Failed to save setting: ${error.message}`);
    }
  };

  const checkAudioRoute = async () => {
    try {
      const { status } = await Audio.requestPermissionsAsync();
      if (status !== 'granted') {
        setConnectionState('Permission denied');
        setAudioRoute('No permission');
        setLastError('Microphone permission required');
        return;
      }

      await Audio.setAudioModeAsync({
        allowsRecordingIOS: true,
        playsInSilentModeIOS: true,
        staysActiveInBackground: false,
        shouldDuckAndroid: true,
        playThroughEarpieceAndroid: false,
      });

      if (devMode) {
        setConnectionState('✓ DEV Mode Active');
        setAudioRoute('Phone mic → Phone speaker');
        setLastError(null);
      } else {
        // Use native module if available
        if (nativeModuleAvailable) {
          try {
            const route = await ExpoGlassesAudio.getAudioRoute();
            // Validate response structure
            if (!route || typeof route !== 'object') {
              throw new Error('Invalid audio route returned from native module');
            }
            const { inputDevice, outputDevice, isBluetoothConnected } = route;
            
            if (isBluetoothConnected) {
              setConnectionState('✓ Glasses Mode Active');
              setAudioRoute(`${inputDevice} → ${outputDevice}`);
            } else {
              setConnectionState('⚠ Glasses Mode (Bluetooth not connected)');
              setAudioRoute(`${inputDevice} → ${outputDevice}`);
            }
            setLastError(null);
          } catch (err) {
            setConnectionState('⚠ Glasses mode (native module error)');
            setAudioRoute('Could not read native route');
            setLastError(`Native module error: ${err.message}`);
          }
        } else {
          setConnectionState('⚠ Glasses mode (native routing module required)');
          setAudioRoute('Bluetooth HFP routing not active in Expo-only build');
          setLastError(null);
        }
      }
    } catch (error) {
      setLastError(`Audio setup failed: ${error.message}`);
      setConnectionState('✗ Error');
      setAudioRoute('Unknown');
    }
  };

  const refreshPeerAdapterState = async () => {
    try {
      if (typeof ExpoGlassesAudio.getPeerAdapterState === 'function') {
        const adapterState = await ExpoGlassesAudio.getPeerAdapterState();
        setPeerAdapterState(adapterState);
      } else {
        setPeerAdapterState(null);
      }
    } catch (error) {
      setLastError(`Peer adapter check failed: ${error.message}`);
    }
  };

  const refreshWearablesDiagnostics = async () => {
    try {
      const module = await getWearablesBridge();
      wearablesBridgeRef.current = module;
      setWearablesBridgeAvailable(Boolean(module?.isBridgeAvailable?.()));
      const diagnostics = await module.getDiagnostics();
      setWearablesDiagnostics(diagnostics);
      setWearablesSessionState(diagnostics?.sessionState || 'unknown');
    } catch (error) {
      setLastError(`Wearables bridge diagnostics failed: ${error.message}`);
    }
  };

  const startWearablesSession = async () => {
    try {
      setLastError(null);
      const module = wearablesBridgeRef.current || (await getWearablesBridge());
      wearablesBridgeRef.current = module;
      const result = await module.startBridgeSession();
      setWearablesSessionState(result?.state || 'unknown');
      await refreshWearablesDiagnostics();
    } catch (error) {
      setLastError(`Wearables bridge session start failed: ${error.message}`);
    }
  };

  const stopWearablesSession = async () => {
    try {
      setLastError(null);
      const module = wearablesBridgeRef.current || (await getWearablesBridge());
      wearablesBridgeRef.current = module;
      const result = await module.stopBridgeSession();
      setWearablesSessionState(result?.state || 'unknown');
      await refreshWearablesDiagnostics();
    } catch (error) {
      setLastError(`Wearables bridge session stop failed: ${error.message}`);
    }
  };

  const loadTransportSessions = async () => {
    try {
      setLastError(null);
      setIsLoadingTransportSessions(true);
      const response = await getDevTransportSessions();
      const sessions = Array.isArray(response?.sessions) ? response.sessions : [];
      setTransportSessions(sessions);
      setLastPeerEvent(`Loaded ${sessions.length} transport session cursor${sessions.length === 1 ? '' : 's'}`);
    } catch (error) {
      setLastError(`Transport session load failed: ${error.message}`);
    } finally {
      setIsLoadingTransportSessions(false);
    }
  };

  const clearTransportSession = async (peerId) => {
    try {
      setLastError(null);
      setIsClearingTransportSession(true);
      const response = await deleteDevTransportSession(peerId);
      setTransportSessions((current) => current.filter((session) => session.peer_id !== peerId));
      setLastPeerEvent(
        response?.cleared
          ? `Cleared transport session for ${peerId}`
          : `No transport session found for ${peerId}`
      );
    } catch (error) {
      setLastError(`Transport session clear failed: ${error.message}`);
    } finally {
      setIsClearingTransportSession(false);
    }
  };

  const startRecording = async () => {
    try {
      setLastError(null);

      if (devMode) {
        // DEV mode: use expo-av
        await Audio.setAudioModeAsync({
          allowsRecordingIOS: true,
          playsInSilentModeIOS: true,
          staysActiveInBackground: false,
          shouldDuckAndroid: true,
          playThroughEarpieceAndroid: false,
        });

        const { recording: newRecording } = await Audio.Recording.createAsync(
          Audio.RecordingOptionsPresets.HIGH_QUALITY
        );
        setRecording(newRecording);
        setIsRecording(true);
      } else {
        // Glasses mode: use native module if available
        if (nativeModuleAvailable) {
          // Start recording with configured duration. The native module will auto-stop after this duration
          // if the user doesn't manually stop it first.
          const recordingPromise = ExpoGlassesAudio.startRecording(NATIVE_RECORDING_DURATION_SECONDS);
          recordingPromiseRef.current = recordingPromise;
          // Recording has started; update UI state immediately.
          setIsRecording(true);
          recordingPromise
            .then((result) => {
              // Recording has completed successfully.
              setIsRecording(false);
              if (result?.uri) {
                setLastRecordingUri(result.uri);
              }
            })
            .catch((error) => {
              setLastError(`Recording failed: ${error.message}`);
              setIsRecording(false);
            })
            .finally(() => {
              if (recordingPromiseRef.current === recordingPromise) {
                recordingPromiseRef.current = null;
              }
            });
        } else {
          setLastError(NATIVE_MODULE_NOT_AVAILABLE_MESSAGE);
        }
      }
    } catch (error) {
      setLastError(`Recording failed: ${error.message}`);
      setIsRecording(false);
    }
  };

  const stopRecording = async () => {
    try {
      if (devMode) {
        // DEV mode: use expo-av
        if (recording) {
          await recording.stopAndUnloadAsync();
          const uri = recording.getURI();
          setRecording(null);
          setLastRecordingUri(uri);
          setIsRecording(false);
          Alert.alert('Recording Complete', 'Saved locally.');
        } else {
          setLastError('No active recording to stop.');
        }
      } else {
        // Glasses mode: use native module if available
        if (nativeModuleAvailable) {
          const result = await ExpoGlassesAudio.stopRecording();
          setIsRecording(false);
          if (result && result.uri) {
            setLastRecordingUri(result.uri);
            Alert.alert('Recording Complete', 'Saved locally.');
          } else {
            // No URI returned; avoid implying the recording was saved
            Alert.alert(
              'Recording Finished',
              'Recording stopped, but no file URI was returned by the native module.'
            );
            setLastError('Recording stopped, but no file URI was returned by the native module.');
          }
        }
      }
    } catch (error) {
      setLastError(`Stop recording failed: ${error.message}`);
      setIsRecording(false);
    }
  };

  const stopPlayback = async () => {
    try {
      if (devMode) {
        // DEV mode: use expo-av
        if (sound) {
          await sound.stopAsync();
          await sound.unloadAsync();
          setSound(null);
          soundRef.current = null;
        }
      } else {
        // Glasses mode: use native module if available
        if (nativeModuleAvailable) {
          await ExpoGlassesAudio.stopPlayback();
        }
      }

      if (pendingTtsTempUriRef.current) {
        const tempUri = pendingTtsTempUriRef.current;
        pendingTtsTempUriRef.current = null;
        FileSystem.deleteAsync(tempUri, { idempotent: true }).catch(() => {});
      }
      setIsPlaying(false);
    } catch (error) {
      setLastError(`Stop playback failed: ${error.message}`);

      if (pendingTtsTempUriRef.current) {
        const tempUri = pendingTtsTempUriRef.current;
        pendingTtsTempUriRef.current = null;
        FileSystem.deleteAsync(tempUri, { idempotent: true }).catch(() => {});
      }
    }
  };

  const playUri = async (uri) => {
    try {
      if (devMode) {
        // DEV mode: use expo-av
        if (sound) {
          await sound.unloadAsync();
          setSound(null);
          soundRef.current = null;
        }

        await Audio.setAudioModeAsync({
          allowsRecordingIOS: false,
          playsInSilentModeIOS: true,
          staysActiveInBackground: false,
          shouldDuckAndroid: false,
          playThroughEarpieceAndroid: false,
        });

        const { sound: newSound } = await Audio.Sound.createAsync({ uri }, { shouldPlay: true });
        setSound(newSound);
        soundRef.current = newSound;
        setIsPlaying(true);

        newSound.setOnPlaybackStatusUpdate((status) => {
          if (status.didJustFinish) {
            setIsPlaying(false);
            if (pendingTtsTempUriRef.current) {
              const tempUri = pendingTtsTempUriRef.current;
              pendingTtsTempUriRef.current = null;
              FileSystem.deleteAsync(tempUri, { idempotent: true }).catch(() => {});
            }
          }
          if (status.error) {
            setLastError(`Playback error: ${status.error}`);
          }
        });
      } else {
        // Glasses mode: use native module if available
        if (nativeModuleAvailable) {
          await ExpoGlassesAudio.playAudio(uri);
          setIsPlaying(true);
        } else {
          setLastError(NATIVE_MODULE_NOT_AVAILABLE_MESSAGE);
        }
      }
    } catch (error) {
      setLastError(`Playback failed: ${error.message}`);
      setIsPlaying(false);
    }
  };

  const playRecording = async () => {
    if (!lastRecordingUri) {
      Alert.alert('No Recording', 'Please record audio first.');
      return;
    }

    try {
      setLastError(null);
      await playUri(lastRecordingUri);
    } catch (error) {
      setLastError(`Playback failed: ${error.message}`);
      setIsPlaying(false);
    }
  };

  const speakText = async (text) => {
    if (!text) return;

    let tempUri = null;
    try {
      const ttsFormat = 'wav';
      const audioBlob = await fetchTTS(text, { format: ttsFormat });
      const base64Audio = await new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onerror = () => reject(new Error('Failed to read TTS audio'));
        reader.onloadend = () => resolve(reader.result);
        reader.readAsDataURL(audioBlob);
      });

      const base64Data = String(base64Audio).split(',')[1];
      tempUri = `${FileSystem.cacheDirectory}tts_${Date.now()}.wav`;
      await FileSystem.writeAsStringAsync(tempUri, base64Data, {
        encoding: FileSystem.EncodingType.Base64,
      });

      // Ensure any previous temp file is removed before we swap.
      if (pendingTtsTempUriRef.current) {
        FileSystem.deleteAsync(pendingTtsTempUriRef.current, { idempotent: true }).catch(() => {});
      }
      pendingTtsTempUriRef.current = tempUri;
      await playUri(tempUri);
    } catch (error) {
      setLastError(`TTS failed: ${error.message}`);
      // Best-effort cleanup of the temp file if anything failed after creation.
      if (tempUri) {
        FileSystem.deleteAsync(tempUri, { idempotent: true }).catch(() => {});
      }
      if (pendingTtsTempUriRef.current === tempUri) {
        pendingTtsTempUriRef.current = null;
      }
    }
  };

  const processAudioThroughPipeline = async () => {
    if (!lastRecordingUri) {
      Alert.alert('No Recording', 'Please record audio first.');
      return;
    }

    setIsProcessing(true);
    setLastError(null);
    setCommandResponse(null);
    try {
      const localUriForRead = normalizeLocalFileUriForFileSystem(lastRecordingUri);
      const uploadFormat = inferAudioFormatFromUri(lastRecordingUri);
      const audioBase64 = await FileSystem.readAsStringAsync(localUriForRead, {
        encoding: FileSystem.EncodingType.Base64,
      });
      const uploaded = await uploadDevAudio(audioBase64, uploadFormat);
      const fileUri = uploaded?.uri;
      if (!fileUri) {
        setLastError('Pipeline failed: missing file URI from upload.');
        Alert.alert('Upload Error', 'The audio upload did not return a valid file location.');
        return;
      }
      const commandFormat = uploaded?.format || uploadFormat;
      const response = await sendAudioCommand(fileUri, commandFormat, {
        profile: 'dev',
        client_context: { device: 'mobile', mode: devMode ? 'dev' : 'glasses' },
      });
      setCommandResponse(response);
      if (response?.spoken_text) {
        await speakText(response.spoken_text);
      }
    } catch (error) {
      setLastError(`Pipeline failed: ${error.message}`);
    } finally {
      setIsProcessing(false);
    }
  };

  const scanPeers = async () => {
    try {
      setLastError(null);
      setIsScanningPeers(true);
      await refreshPeerAdapterState();
      const peers = await ExpoGlassesAudio.scanPeers(5000);
      setDiscoveredPeers(Array.isArray(peers) ? peers : []);
      setLastPeerEvent(`Scan complete (${Array.isArray(peers) ? peers.length : 0} peers)`);
    } catch (error) {
      setLastError(`Peer scan failed: ${error.message}`);
    } finally {
      setIsScanningPeers(false);
    }
  };

  const seedDemoPeer = async () => {
    try {
      setLastError(null);
      await refreshPeerAdapterState();
      const peer = await ExpoGlassesAudio.simulatePeerDiscovery({
        peerRef: 'peer://demo-glasses',
        peerId: '12D3KooWdemoGlasses',
        displayName: 'Demo Glasses Peer',
        transport: 'simulated',
        rssi: -42,
      });
      setDiscoveredPeers((current) => {
        const next = current.filter((item) => item.peerRef !== peer.peerRef);
        return [...next, peer];
      });
    } catch (error) {
      setLastError(`Demo peer failed: ${error.message}`);
    }
  };

  const advertiseLocalPeer = async () => {
    try {
      setLastError(null);
      const identity = await ExpoGlassesAudio.advertiseIdentity({
        peerId: localPeerIdRef.current,
        displayName: 'HandsFree Glasses',
      });
      setAdvertisedPeerIdentity(identity);
      await refreshPeerAdapterState();
      setLastPeerEvent(`Advertising as ${identity.displayName || identity.peerId}`);
    } catch (error) {
      setLastError(`Advertise identity failed: ${error.message}`);
    }
  };

  const sendEnvelopeToPeer = async (peerRef, envelope, successMessage) => {
    const encodedEnvelope = encodeEnvelopeBase64(envelope);
    await ExpoGlassesAudio.sendFrame(peerRef, encodedEnvelope);
    setLastOutboundPeerEnvelope(envelope);
    setLastOutboundPeerFrameBase64(encodedEnvelope);
    setPeerBackendValidation(null);
    setLastPeerEvent(successMessage);
    return encodedEnvelope;
  };

  const getSelectedOrActivePeer = () => {
    if (activePeer?.peerRef) {
      return {
        peerRef: activePeer.peerRef,
        peerId: activePeer.peerId || activePeer.peerRef,
      };
    }
    const selectedPeer = discoveredPeers.find((peer) => peer.peerRef === selectedPeerRef);
    if (selectedPeer?.peerRef) {
      return {
        peerRef: selectedPeer.peerRef,
        peerId: selectedPeer.peerId || selectedPeer.peerRef,
      };
    }
    return null;
  };

  const connectToPeer = async (peer) => {
    try {
      setLastError(null);
      await refreshPeerAdapterState();
      if (!peer?.peerRef) {
        Alert.alert('No Peer', 'Run a peer scan or add the demo peer first.');
        return;
      }
      const connection = await ExpoGlassesAudio.connectPeer(peer.peerRef);
      setActivePeer(connection);
      setSelectedPeerRef(peer.peerRef);
      const handshake = createHandshakeEnvelope({
        peerId: connection.peerId || connection.peerRef,
        sessionId: peerSessionRef.current,
        capabilities: ['bluetooth-driver-bridge', 'handshake-v1', 'ack-v1'],
      });
      await sendEnvelopeToPeer(
        connection.peerRef,
        handshake,
        `Connected and sent handshake to ${connection.peerId || connection.peerRef}`
      );
    } catch (error) {
      setLastError(`Peer connect failed: ${error.message}`);
    }
  };

  const connectFirstPeer = async () => {
    await connectToPeer(discoveredPeers[0]);
  };

  const disconnectActivePeer = async () => {
    try {
      setLastError(null);
      if (!activePeer?.peerRef) {
        Alert.alert('No Active Peer', 'Connect to a peer first.');
        return;
      }
      await ExpoGlassesAudio.disconnectPeer(activePeer.peerRef, 'manual');
      setLastPeerEvent(`Disconnected ${activePeer.peerId || activePeer.peerRef}`);
      setActivePeer(null);
    } catch (error) {
      setLastError(`Peer disconnect failed: ${error.message}`);
    }
  };

  const clearPeerState = () => {
    setDiscoveredPeers([]);
    setSelectedPeerRef(null);
    setActivePeer(null);
    setLastPeerEvent('Peer state cleared');
    setLastOutboundPeerFrameBase64(null);
    setLastOutboundPeerEnvelope(null);
    setLastInboundPeerEnvelope(null);
    setPeerBackendValidation(null);
    setLastInboundBackendValidation(null);
  };

  const resetPeerSimulation = async () => {
    try {
      setLastError(null);
      if (typeof ExpoGlassesAudio.resetPeerSimulation === 'function') {
        await ExpoGlassesAudio.resetPeerSimulation();
      }
      clearPeerState();
      await refreshPeerAdapterState();
      setLastPeerEvent('Peer simulation reset');
    } catch (error) {
      setLastError(`Peer simulation reset failed: ${error.message}`);
    }
  };

  const sendPeerPing = async () => {
    try {
      setLastError(null);
      if (!activePeer?.peerRef) {
        Alert.alert('No Active Peer', 'Connect to a peer first.');
        return;
      }
      const messageEnvelope = createChatMessageEnvelope({
        peerId: activePeer.peerId || activePeer.peerRef,
        sessionId: peerSessionRef.current,
        text: `ping:${atob(PEER_TEST_PAYLOAD_BASE64)}`,
        senderPeerId: localPeerIdRef.current,
        conversationId: peerConversationRef.current,
      });
      await sendEnvelopeToPeer(
        activePeer.peerRef,
        messageEnvelope,
        `Sent message envelope to ${activePeer.peerId || activePeer.peerRef}`
      );
    } catch (error) {
      setLastError(`Send frame failed: ${error.message}`);
    }
  };

  const simulatePeerReply = async () => {
    try {
      setLastError(null);
      const targetPeer = getSelectedOrActivePeer();
      if (!targetPeer?.peerRef) {
        Alert.alert('No Peer', 'Select or connect to a peer first.');
        return;
      }
      const ackEnvelope = createAckEnvelope({
        peerId: targetPeer.peerId,
        sessionId: peerSessionRef.current,
        ackedMessageId: 'simulated-ack',
      });
      await ExpoGlassesAudio.simulateFrameReceived(
        targetPeer.peerRef,
        encodeEnvelopeBase64(ackEnvelope),
        targetPeer.peerId
      );
    } catch (error) {
      setLastError(`Simulate frame failed: ${error.message}`);
    }
  };

  const validateLastPeerFrameViaBackend = async () => {
    try {
      setLastError(null);
      setIsValidatingPeerFrame(true);
      const targetPeer = getSelectedOrActivePeer();
      if (!targetPeer?.peerRef || !lastOutboundPeerFrameBase64) {
        Alert.alert('No Frame', 'Select or connect to a peer, then send a handshake or ping frame first.');
        return;
      }
      const response = await postDevPeerEnvelope(targetPeer.peerRef, lastOutboundPeerFrameBase64);
      const validationResult = buildPeerBackendValidationResult(response);
      if (validationResult.ackEnvelope) {
        setLastInboundPeerEnvelope(validationResult.ackEnvelope);
        await replayBackendAckFrame(ExpoGlassesAudio, targetPeer.peerRef, validationResult);
      }
      setPeerBackendValidation(validationResult);
      setLastPeerEvent(`Backend accepted ${response.kind} envelope for ${response.peer_id}`);
    } catch (error) {
      setLastError(`Backend validation failed: ${error.message}`);
    } finally {
      setIsValidatingPeerFrame(false);
    }
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text style={styles.title}>Glasses Audio Diagnostics</Text>

      <View style={styles.card}>
        <View style={styles.toggleContainer}>
          <View style={styles.toggleLabel}>
            <Text style={styles.cardTitle}>{devMode ? '📱 DEV Mode' : '👓 Glasses Mode'}</Text>
            <Text style={styles.subtext}>{devMode ? 'Phone mic/speaker' : 'Native Bluetooth routing not enabled here'}</Text>
          </View>
          <Switch value={devMode} onValueChange={toggleDevMode} />
        </View>
      </View>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>Connection State</Text>
        <Text style={styles.text}>{connectionState}</Text>
        <Text style={styles.text}>{audioRoute}</Text>
        <TouchableOpacity style={[styles.button, styles.buttonSecondary]} onPress={checkAudioRoute}>
          <Text style={styles.buttonTextSecondary}>Refresh</Text>
        </TouchableOpacity>
      </View>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>Wearables Bridge</Text>
        <Text style={styles.subtext}>First-party wearables diagnostics bridge for config, capability, and session visibility.</Text>
        <Text style={styles.text}>Module available: {wearablesBridgeAvailable ? 'yes' : 'no'}</Text>
        <Text style={styles.text}>Provider: {wearablesDiagnostics?.provider || 'internal_bridge'}</Text>
        <Text style={styles.text}>Integration mode: {wearablesDiagnostics?.integrationMode || 'unknown'}</Text>
        <Text style={styles.text}>Platform: {wearablesDiagnostics?.platform || 'unknown'}</Text>
        <Text style={styles.text}>SDK linked: {wearablesDiagnostics?.sdkLinked ? 'yes' : 'no'}</Text>
        <Text style={styles.text}>SDK configured: {wearablesDiagnostics?.sdkConfigured ? 'yes' : 'no'}</Text>
        <Text style={styles.text}>SDK version: {wearablesDiagnostics?.sdkVersion || 'not linked'}</Text>
        <Text style={styles.text}>Analytics opt-out: {wearablesDiagnostics?.analyticsOptOut ? 'enabled' : 'disabled'}</Text>
        <Text style={styles.text}>Application ID: {wearablesDiagnostics?.applicationId || 'not configured'}</Text>
        <Text style={styles.text}>Session state: {wearablesSessionState}</Text>
        <Text style={styles.text}>Registration state: {wearablesDiagnostics?.registrationState || 'unknown'}</Text>
        <Text style={styles.text}>Active device: {wearablesDiagnostics?.activeDeviceId || 'none'}</Text>
        <Text style={styles.text}>Device count: {wearablesDiagnostics?.deviceCount ?? 0}</Text>
        <Text style={styles.text}>
          Capabilities: {wearablesDiagnostics?.capabilities
            ? [
                wearablesDiagnostics.capabilities.session ? 'session' : null,
                wearablesDiagnostics.capabilities.camera ? 'camera' : null,
                wearablesDiagnostics.capabilities.photoCapture ? 'photo' : null,
                wearablesDiagnostics.capabilities.videoStream ? 'video' : null,
                wearablesDiagnostics.capabilities.audio ? 'audio' : null,
              ].filter(Boolean).join(', ') || 'none'
            : 'unknown'}
        </Text>
        <TouchableOpacity style={[styles.button, styles.buttonSecondary]} onPress={refreshWearablesDiagnostics}>
          <Text style={styles.buttonTextSecondary}>Refresh Bridge Diagnostics</Text>
        </TouchableOpacity>
        <TouchableOpacity style={[styles.button, !wearablesBridgeAvailable && styles.buttonDisabled]} onPress={startWearablesSession} disabled={!wearablesBridgeAvailable}>
          <Text style={styles.buttonText}>Start Bridge Session</Text>
        </TouchableOpacity>
        <TouchableOpacity style={[styles.button, styles.buttonSecondary, !wearablesBridgeAvailable && styles.buttonDisabled]} onPress={stopWearablesSession} disabled={!wearablesBridgeAvailable}>
          <Text style={styles.buttonTextSecondary}>Stop Bridge Session</Text>
        </TouchableOpacity>
      </View>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>Peer Bridge</Text>
        <Text style={styles.subtext}>Exercise Bluetooth peer discovery, connection, and frame events.</Text>
        <Text style={styles.subtext}>Backend validation accepts the last outbound frame and replays any ack into the local diagnostics event flow.</Text>
        <Text style={styles.text}>
          Adapter: {peerAdapterState?.state || 'unknown'} / {peerAdapterState?.transport || 'n/a'}
        </Text>
        <Text style={styles.text}>
          Ready: {peerAdapterState ? `${peerAdapterState.adapterEnabled ? 'adapter-on' : 'adapter-off'}, ${peerAdapterState.scanPermissionGranted ? 'scan-ok' : 'scan-missing'}, ${peerAdapterState.connectPermissionGranted ? 'connect-ok' : 'connect-missing'}, ${peerAdapterState.advertisePermissionGranted === false ? 'advertise-missing' : 'advertise-ok'}` : 'not checked'}
        </Text>
        <Text style={styles.text}>
          Activity: {peerAdapterState ? `${peerAdapterState.scanning ? 'scanning' : 'idle'} / ${peerAdapterState.advertising ? 'advertising' : 'not-advertising'}` : 'unknown'}
        </Text>
        <Text style={styles.text}>Local peer ID: {localPeerId}</Text>
        <Text style={styles.text}>
          Advertised identity: {advertisedPeerIdentity?.displayName || advertisedPeerIdentity?.peerId || 'none'}
        </Text>
        <Text style={styles.text}>
          Auto-validate inbound frames: {autoValidateInboundPeerFrames ? 'on' : 'off'}
        </Text>
        <Text style={styles.text}>
          Selected peer: {selectedPeerRef || 'None'}
        </Text>
        <Text style={styles.text}>Active peer: {activePeer?.peerId || activePeer?.peerRef || 'None'}</Text>
        <Text style={styles.text}>Transport sessions: {transportSessions.length}</Text>
        <Text style={styles.text}>
          Matched transport session: {matchedTransportSession?.session_id || 'none'}
        </Text>
        <Text style={styles.text}>
          Matched transport session health: {getTransportSessionHealth(matchedTransportSession?.updated_at_ms)} • {formatTransportSessionAge(matchedTransportSession?.updated_at_ms)}
        </Text>
        {staleTransportSessionSuspected ? (
          <Text style={styles.errorText}>
            Stale cursor suspected: matched persisted transport session exists without an active peer connection.
          </Text>
        ) : null}
        <Text style={styles.text}>Last event: {lastPeerEvent}</Text>
        <Text style={styles.text}>
          Last outbound frame: {lastOutboundPeerEnvelope?.kind || 'None'}
        </Text>
        <Text style={styles.text}>
          Last inbound frame: {lastInboundPeerEnvelope?.kind || 'None'}
        </Text>
        <TouchableOpacity
          style={[styles.button, styles.buttonSecondary]}
          onPress={refreshPeerAdapterState}
        >
          <Text style={styles.buttonTextSecondary}>Refresh Peer Adapter State</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.button, styles.buttonSecondary, isLoadingTransportSessions && styles.buttonDisabled]}
          onPress={loadTransportSessions}
          disabled={isLoadingTransportSessions}
        >
          <Text style={styles.buttonTextSecondary}>
            {isLoadingTransportSessions ? 'Loading Transport Sessions...' : 'Load Transport Sessions'}
          </Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.button, styles.buttonSecondary]}
          onPress={advertiseLocalPeer}
        >
          <Text style={styles.buttonTextSecondary}>Advertise Local Identity</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.button, styles.buttonSecondary]}
          onPress={() => setAutoValidateInboundPeerFrames((current) => !current)}
        >
          <Text style={styles.buttonTextSecondary}>
            {autoValidateInboundPeerFrames ? 'Disable Auto Inbound Validation' : 'Enable Auto Inbound Validation'}
          </Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.button, styles.buttonSecondary]}
          onPress={clearPeerState}
        >
          <Text style={styles.buttonTextSecondary}>Clear Peer State</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.button, styles.buttonSecondary]}
          onPress={resetPeerSimulation}
        >
          <Text style={styles.buttonTextSecondary}>Reset Peer Simulation</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.button, (isScanningPeers || !nativeModuleAvailable) && styles.buttonDisabled]}
          onPress={scanPeers}
          disabled={isScanningPeers || !nativeModuleAvailable}
        >
          <Text style={styles.buttonText}>{isScanningPeers ? 'Scanning...' : 'Scan Nearby Peers'}</Text>
        </TouchableOpacity>
        <TouchableOpacity style={[styles.button, styles.buttonSecondary]} onPress={seedDemoPeer}>
          <Text style={styles.buttonTextSecondary}>Add Demo Peer</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.button, discoveredPeers.length === 0 && styles.buttonDisabled]}
          onPress={connectFirstPeer}
          disabled={discoveredPeers.length === 0}
        >
          <Text style={styles.buttonText}>Connect First Peer</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.button, styles.buttonSecondary, !activePeer?.peerRef && styles.buttonDisabled]}
          onPress={disconnectActivePeer}
          disabled={!activePeer?.peerRef}
        >
          <Text style={styles.buttonTextSecondary}>Disconnect Active Peer</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.button, !activePeer?.peerRef && styles.buttonDisabled]}
          onPress={sendPeerPing}
          disabled={!activePeer?.peerRef}
        >
          <Text style={styles.buttonText}>Send Ping Frame</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.button, styles.buttonSecondary, discoveredPeers.length === 0 && styles.buttonDisabled]}
          onPress={simulatePeerReply}
          disabled={discoveredPeers.length === 0}
        >
          <Text style={styles.buttonTextSecondary}>Simulate Inbound Frame</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[
            styles.button,
            styles.buttonSecondary,
            (!lastOutboundPeerFrameBase64 || isValidatingPeerFrame) && styles.buttonDisabled,
          ]}
          onPress={validateLastPeerFrameViaBackend}
          disabled={!lastOutboundPeerFrameBase64 || isValidatingPeerFrame}
        >
          <Text style={styles.buttonTextSecondary}>
            {isValidatingPeerFrame ? 'Validating...' : 'Validate + Replay Ack via Backend'}
          </Text>
        </TouchableOpacity>
        {lastOutboundPeerEnvelope ? (
          <View style={styles.debugInfo}>
            <Text style={styles.debugLabel}>Outbound Envelope</Text>
            <Text style={styles.debugValue}>
              {lastOutboundPeerEnvelope.kind} • {lastOutboundPeerEnvelope.message_id}
            </Text>
            <Text style={styles.debugValue}>{lastOutboundPeerEnvelope.peer_id}</Text>
            <Text style={styles.debugValue}>{lastOutboundPeerEnvelope.session_id}</Text>
          </View>
        ) : null}
        {peerBackendValidation ? (
          <View style={styles.responseContainer}>
            <Text style={styles.responseTitle}>Backend Validation</Text>
            <Text style={styles.responseText}>
              Accepted {peerBackendValidation.kind} for {peerBackendValidation.peer_id}
            </Text>
            <Text style={styles.responseText}>
              session {peerBackendValidation.session_id} • message {peerBackendValidation.message_id}
            </Text>
            {peerBackendValidation.protocol ? (
              <Text style={styles.responseText}>
                protocol {peerBackendValidation.protocol}
              </Text>
            ) : null}
            {peerBackendValidation.conversation_id ? (
              <Text style={styles.responseText}>
                conversation {peerBackendValidation.conversation_id}
              </Text>
            ) : null}
            {peerBackendValidation.payload_text ? (
              <Text style={styles.responseText}>
                payload {peerBackendValidation.payload_text}
              </Text>
            ) : null}
            {peerBackendValidation.payload_json ? (
              <Text style={styles.responseText}>
                payload json {JSON.stringify(peerBackendValidation.payload_json)}
              </Text>
            ) : null}
            {peerBackendValidation.ackEnvelope ? (
              <Text style={styles.responseText}>
                ack {peerBackendValidation.ackEnvelope.kind} for {peerBackendValidation.ackEnvelope.acked_message_id}
              </Text>
            ) : null}
          </View>
        ) : null}
        {lastInboundBackendValidation ? (
          <View style={styles.responseContainer}>
            <Text style={styles.responseTitle}>Inbound Backend Validation</Text>
            <Text style={styles.responseText}>
              Accepted {lastInboundBackendValidation.kind} for {lastInboundBackendValidation.peer_id}
            </Text>
            <Text style={styles.responseText}>
              session {lastInboundBackendValidation.session_id} • message {lastInboundBackendValidation.message_id}
            </Text>
            {lastInboundBackendValidation.ackEnvelope ? (
              <Text style={styles.responseText}>
                ack {lastInboundBackendValidation.ackEnvelope.kind} for {lastInboundBackendValidation.ackEnvelope.acked_message_id}
              </Text>
            ) : null}
          </View>
        ) : null}
        {discoveredPeers.length > 0 ? (
          <View style={styles.peerList}>
            {discoveredPeers.map((peer) => (
              <View key={peer.peerRef} style={styles.peerRow}>
                <Text style={styles.peerTitle}>{peer.displayName || peer.peerId}</Text>
                <Text style={styles.peerMeta}>{peer.peerRef}</Text>
                <Text style={styles.peerMeta}>
                  {peer.transport}
                  {typeof peer.rssi === 'number' ? ` • RSSI ${peer.rssi}` : ''}
                </Text>
                <TouchableOpacity
                  style={[
                    styles.peerActionButton,
                    styles.peerActionButtonSecondary,
                    selectedPeerRef === peer.peerRef ? styles.buttonDisabled : null,
                  ]}
                  onPress={() => setSelectedPeerRef(peer.peerRef)}
                  disabled={selectedPeerRef === peer.peerRef}
                >
                  <Text style={styles.peerActionTextSecondary}>
                    {selectedPeerRef === peer.peerRef ? 'Selected' : 'Select Peer'}
                  </Text>
                </TouchableOpacity>
                <TouchableOpacity
                  style={[
                    styles.peerActionButton,
                    activePeer?.peerRef === peer.peerRef ? styles.buttonDisabled : null,
                  ]}
                  onPress={() => connectToPeer(peer)}
                  disabled={activePeer?.peerRef === peer.peerRef}
                >
                  <Text style={styles.peerActionText}>
                    {activePeer?.peerRef === peer.peerRef ? 'Connected' : 'Connect This Peer'}
                  </Text>
                </TouchableOpacity>
              </View>
            ))}
          </View>
        ) : null}
        {transportSessionTarget ? (
          <View style={styles.debugInfo}>
            <Text style={styles.debugLabel}>Transport Session Target</Text>
            <Text style={styles.debugValue}>
              {transportSessionTarget.source} peer {transportSessionTarget.label}
            </Text>
            <Text style={styles.debugValue}>
              {matchedTransportSession
                ? `matched ${matchedTransportSession.session_id}`
                : 'no persisted transport session matched this peer'}
            </Text>
            {matchedTransportSession ? (
              <TouchableOpacity
                style={[
                  styles.peerActionButton,
                  styles.peerActionButtonSecondary,
                  isClearingTransportSession ? styles.buttonDisabled : null,
                ]}
                onPress={() => clearTransportSession(matchedTransportSession.peer_id)}
                disabled={isClearingTransportSession}
              >
                <Text style={styles.peerActionTextSecondary}>
                  {isClearingTransportSession
                    ? 'Clearing Matched Transport Session...'
                    : 'Clear Matched Transport Session'}
                </Text>
              </TouchableOpacity>
            ) : null}
          </View>
        ) : null}
        {transportSessions.length > 0 ? (
          <View style={styles.peerList}>
            {transportSessions.map((session) => (
              <View key={`${session.peer_id}-${session.session_id}`} style={styles.peerRow}>
                <Text style={styles.peerTitle}>{session.peer_id}</Text>
                {matchedTransportSession?.session_id === session.session_id ? (
                  <Text style={styles.selectedText}>Matched Current Peer</Text>
                ) : null}
                <Text style={styles.peerMeta}>session {session.session_id}</Text>
                {session.peer_ref ? (
                  <Text style={styles.peerMeta}>{session.peer_ref}</Text>
                ) : null}
                <Text style={styles.peerMeta}>
                  {getTransportSessionHealth(session.updated_at_ms)} • {formatTransportSessionAge(session.updated_at_ms)}
                </Text>
                <Text style={styles.peerMeta}>resume {session.resume_token}</Text>
                <Text style={styles.peerMeta}>
                  capabilities: {(session.capabilities || []).join(', ') || 'none'}
                </Text>
                <TouchableOpacity
                  style={[
                    styles.peerActionButton,
                    styles.peerActionButtonSecondary,
                    isClearingTransportSession ? styles.buttonDisabled : null,
                  ]}
                  onPress={() => clearTransportSession(session.peer_id)}
                  disabled={isClearingTransportSession}
                >
                  <Text style={styles.peerActionTextSecondary}>
                    {isClearingTransportSession ? 'Clearing Transport Session...' : 'Clear Transport Session'}
                  </Text>
                </TouchableOpacity>
              </View>
            ))}
          </View>
        ) : null}
      </View>

      {lastError && (
        <View style={[styles.card, styles.warningCard]}>
          <Text style={styles.cardTitle}>⚠️ Last Error</Text>
          <Text style={styles.errorText}>{lastError}</Text>
        </View>
      )}

      <View style={styles.card}>
        <Text style={styles.cardTitle}>Recording</Text>
        <TouchableOpacity style={[styles.button, isRecording && styles.buttonRecording]} onPress={isRecording ? stopRecording : startRecording}>
          <Text style={styles.buttonText}>{isRecording ? 'Stop Recording' : 'Start Recording'}</Text>
        </TouchableOpacity>
        {lastRecordingUri && <Text style={styles.successText}>✓ Recording saved</Text>}
      </View>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>Playback</Text>
        <TouchableOpacity
          style={[styles.button, !lastRecordingUri && styles.buttonDisabled, isPlaying && styles.buttonRecording]}
          onPress={isPlaying ? stopPlayback : playRecording}
          disabled={!lastRecordingUri}
        >
          <Text style={styles.buttonText}>{isPlaying ? 'Stop Playback' : 'Play Last Recording'}</Text>
        </TouchableOpacity>
      </View>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>Backend Pipeline</Text>
        <Text style={styles.mono}>/v1/dev/audio → /v1/command → /v1/tts</Text>
        <TouchableOpacity
          style={[styles.button, (!lastRecordingUri || isProcessing) && styles.buttonDisabled]}
          onPress={processAudioThroughPipeline}
          disabled={!lastRecordingUri || isProcessing}
        >
          <Text style={styles.buttonText}>{isProcessing ? 'Processing...' : 'Send + Speak'}</Text>
        </TouchableOpacity>
        {commandResponse?.spoken_text ? (
          <View style={styles.responseContainer}>
            <Text style={styles.responseTitle}>spoken_text</Text>
            <Text style={styles.responseText}>{commandResponse.spoken_text}</Text>
          </View>
        ) : null}
      </View>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>Push Notifications Debug</Text>
        <TouchableOpacity
          style={styles.button}
          onPress={async () => {
            try {
              setLastError(null);
              await simulateNotificationForDev('Test notification from diagnostics screen');
              Alert.alert('Success', 'Simulated notification sent');
            } catch (error) {
              setLastError(`Simulate notification failed: ${error.message}`);
            }
          }}
        >
          <Text style={styles.buttonText}>🔔 Simulate Test Notification</Text>
        </TouchableOpacity>
        
        {pushDebugState && (
          <View style={styles.debugInfo}>
            <Text style={styles.debugLabel}>App State:</Text>
            <Text style={styles.debugValue}>
              {pushDebugState.isAppInBackground ? '🌙 Backgrounded' : '☀️ Foreground'}
            </Text>
            
            {pushDebugState.pendingCount > 0 && (
              <>
                <Text style={styles.debugLabel}>Pending Speak Queue:</Text>
                <Text style={styles.debugValue}>{pushDebugState.pendingCount} deferred</Text>
              </>
            )}
            
            {pushDebugState.lastNotificationTime && (
              <>
                <Text style={styles.debugLabel}>Last Notification:</Text>
                <Text style={styles.debugValue}>
                  {new Date(pushDebugState.lastNotificationTime).toLocaleTimeString()}
                </Text>
              </>
            )}
            
            {pushDebugState.lastSpokenText && (
              <>
                <Text style={styles.debugLabel}>Last Spoken:</Text>
                <Text style={styles.debugValue}>{pushDebugState.lastSpokenText}</Text>
              </>
            )}
            
            {pushDebugState.lastPlaybackError && (
              <>
                <Text style={styles.debugLabel}>Last TTS Error:</Text>
                <Text style={[styles.debugValue, styles.errorText]}>
                  {pushDebugState.lastPlaybackError}
                </Text>
              </>
            )}
          </View>
        )}
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f5f5f5' },
  content: { padding: 20, paddingBottom: 40 },
  title: { fontSize: 24, fontWeight: 'bold', marginBottom: 12 },
  card: {
    backgroundColor: 'white',
    padding: 15,
    borderRadius: 8,
    marginBottom: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 2,
    elevation: 2,
  },
  warningCard: { backgroundColor: '#fff3cd', borderLeftWidth: 4, borderLeftColor: '#ff9800' },
  cardTitle: { fontSize: 16, fontWeight: '600', marginBottom: 8, color: '#000' },
  text: { fontSize: 14, color: '#333', marginBottom: 6, lineHeight: 20 },
  mono: { fontSize: 12, fontFamily: 'monospace', color: '#555', marginBottom: 8, backgroundColor: '#f5f5f5', padding: 8, borderRadius: 4 },
  toggleContainer: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  toggleLabel: { flex: 1, marginRight: 12 },
  subtext: { fontSize: 12, color: '#666', marginTop: 4, lineHeight: 16 },
  errorText: { color: '#d32f2f', fontSize: 14 },
  successText: { color: '#4caf50', fontSize: 14, marginTop: 8, textAlign: 'center' },
  button: { backgroundColor: '#007AFF', padding: 14, borderRadius: 8, alignItems: 'center', marginTop: 12 },
  buttonSecondary: { backgroundColor: '#f0f0f0' },
  buttonRecording: { backgroundColor: '#d32f2f' },
  buttonDisabled: { backgroundColor: '#ccc', opacity: 0.6 },
  buttonText: { color: 'white', fontSize: 16, fontWeight: '600' },
  buttonTextSecondary: { color: '#007AFF', fontSize: 16, fontWeight: '600' },
  responseContainer: {
    marginTop: 12,
    padding: 12,
    backgroundColor: '#e8f5e9',
    borderRadius: 8,
    borderLeftWidth: 4,
    borderLeftColor: '#4caf50',
  },
  responseTitle: { fontSize: 14, fontWeight: '600', color: '#2e7d32', marginBottom: 6 },
  responseText: { fontSize: 14, color: '#1b5e20', lineHeight: 20 },
  debugInfo: { marginTop: 12, padding: 12, backgroundColor: '#f5f5f5', borderRadius: 8 },
  debugLabel: { fontSize: 13, fontWeight: '600', color: '#666', marginTop: 8 },
  debugValue: { fontSize: 13, color: '#333', marginTop: 2, marginLeft: 8 },
  peerList: { marginTop: 12, gap: 8 },
  peerRow: { padding: 10, borderRadius: 6, backgroundColor: '#f5f5f5' },
  peerTitle: { fontSize: 14, fontWeight: '600', color: '#111' },
  peerMeta: { fontSize: 12, color: '#666', marginTop: 2 },
  peerActionButton: { marginTop: 10, backgroundColor: '#007AFF', paddingVertical: 8, paddingHorizontal: 10, borderRadius: 6, alignItems: 'center' },
  peerActionText: { color: '#fff', fontSize: 13, fontWeight: '600' },
  peerActionButtonSecondary: { backgroundColor: '#f0f0f0' },
  peerActionTextSecondary: { color: '#007AFF', fontSize: 13, fontWeight: '600' },
});
