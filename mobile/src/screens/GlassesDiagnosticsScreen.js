import { Alert, AppState, ScrollView, StyleSheet, Switch, Text, TouchableOpacity, View } from 'react-native';
import React, { useEffect, useState, useRef } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Audio } from 'expo-av';
import * as FileSystem from 'expo-file-system';
import { fetchTTS, sendAudioCommand, uploadDevAudio } from '../api/client';
import { getDebugState, simulateNotificationForDev } from '../push';
import ExpoGlassesAudio from '../../modules/expo-glasses-audio/src/ExpoGlassesAudioModule';

const DEV_MODE_KEY = '@glasses_dev_mode';
const NATIVE_RECORDING_DURATION_SECONDS = 10;
const NATIVE_PLAYBACK_TIMEOUT_MS = 30000; // 30 seconds to accommodate longer TTS and audio files
const NATIVE_MODULE_NOT_AVAILABLE_MESSAGE = 'Native glasses audio module not available. Please switch to DEV mode or ensure the native module is properly installed.';
const NATIVE_MODULE_REQUIRED_METHODS = ['getAudioRoute', 'startRecording', 'stopRecording', 'playAudio', 'stopPlayback'];
const SUPPORTED_AUDIO_FORMATS = ['wav', 'mp3', 'opus', 'm4a'];
// Regex pattern to match audio file extensions before query params or hash fragments
// Matches: .wav, .mp3, .opus, or .m4a followed by end of string, ?, or #
// Group 1 captures the format (e.g., 'wav', 'mp3', 'opus', 'm4a')
const AUDIO_FORMAT_REGEX = new RegExp(`\\.(${SUPPORTED_AUDIO_FORMATS.join('|')})(?=\\?|#|$)`);

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
  const playbackTimeoutRef = useRef(null);
  const soundRef = useRef(null);
  const recordingTimeoutRef = useRef(null);

  const inferAudioFormatFromUri = (uri) => {
    if (!uri) return 'm4a';
    const lower = String(uri).toLowerCase();

    // iOS can sometimes produce .caf with defaults; backend doesn't accept 'caf'.
    if (lower.endsWith('.caf')) return 'm4a';

    const match = lower.match(AUDIO_FORMAT_REGEX);
    if (match?.[1]) return match[1];

    return 'm4a';
  };

  useEffect(() => {
    (async () => {
      try {
        const saved = await AsyncStorage.getItem(DEV_MODE_KEY);
        if (saved !== null) setDevMode(JSON.parse(saved));
      } catch {
        // ignore
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
    let isActive = AppState.currentState === 'active';
    
    const appStateSubscription = AppState.addEventListener('change', (nextAppState) => {
      isActive = nextAppState === 'active';
    });

    // Periodically refresh push debug state (every 5 seconds) but only when active
    const interval = setInterval(() => {
      if (!isActive) {
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
      if (sound) {
        sound.unloadAsync();
      // Use ref to ensure we cleanup the latest sound instance
      if (soundRef.current) {
        soundRef.current.unloadAsync();
      }
      if (playbackTimeoutRef.current) {
        clearTimeout(playbackTimeoutRef.current);
      }
      if (recordingTimeoutRef.current) {
        clearTimeout(recordingTimeoutRef.current);
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    checkAudioRoute();
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
          await ExpoGlassesAudio.startRecording(NATIVE_RECORDING_DURATION_SECONDS);
          setIsRecording(true);
          
          // Set up timeout to update UI when native module auto-stops recording
          const timeoutId = setTimeout(() => {
            setIsRecording(false);
            recordingTimeoutRef.current = null;
            // This is expected behavior, not an error - recording duration limit reached
            Alert.alert('Recording Complete', `Recording stopped after ${NATIVE_RECORDING_DURATION_SECONDS} seconds.`);
          }, NATIVE_RECORDING_DURATION_SECONDS * 1000);
          recordingTimeoutRef.current = timeoutId;
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
      setIsRecording(false);
      
      // Clear recording timeout if it exists
      if (recordingTimeoutRef.current) {
        clearTimeout(recordingTimeoutRef.current);
        recordingTimeoutRef.current = null;
      }
      
      if (devMode) {
        // DEV mode: use expo-av
        if (recording) {
          await recording.stopAndUnloadAsync();
          const uri = recording.getURI();
          setRecording(null);
          setLastRecordingUri(uri);
          Alert.alert('Recording Complete', 'Saved locally.');
        } else {
          setLastError('No active recording to stop.');
        }
      } else {
        // Glasses mode: use native module if available
        if (nativeModuleAvailable) {
          const result = await ExpoGlassesAudio.stopRecording();
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
    }
  };

  const stopPlayback = async () => {
    try {
      // Clear any pending timeout and reset ref
      if (playbackTimeoutRef.current) {
        clearTimeout(playbackTimeoutRef.current);
        playbackTimeoutRef.current = null;
      }
      
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
      setIsPlaying(false);
    } catch (error) {
      setLastError(`Stop playback failed: ${error.message}`);
      // Ensure ref is cleared even on error
      if (playbackTimeoutRef.current) {
        clearTimeout(playbackTimeoutRef.current);
        playbackTimeoutRef.current = null;
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
          // Set a timeout to mark playback as finished (since native module doesn't have status callbacks yet)
          // NOTE: This is a limitation - if playback finishes earlier or runs longer than the timeout,
          // the UI state will be inaccurate. TODO: add event-based status updates to native module.
          const timeoutId = setTimeout(() => {
            // Only update state if component is still mounted (playbackTimeoutRef will be cleared on unmount)
            if (playbackTimeoutRef.current === timeoutId) {
              setIsPlaying(false);
              playbackTimeoutRef.current = null;
            }
          }, NATIVE_PLAYBACK_TIMEOUT_MS);
          playbackTimeoutRef.current = timeoutId;
        } else {
          setLastError(NATIVE_MODULE_NOT_AVAILABLE_MESSAGE);
        }
      }
    } catch (error) {
      // Ensure any pending native playback timeout is cleared on error
      if (playbackTimeoutRef.current) {
        clearTimeout(playbackTimeoutRef.current);
        playbackTimeoutRef.current = null;
      }
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
      const audioBlob = await fetchTTS(text);
      const base64Audio = await new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onerror = () => reject(new Error('Failed to read TTS audio'));
        reader.onloadend = () => resolve(reader.result);
        reader.readAsDataURL(audioBlob);
      });

      const base64Data = String(base64Audio).split(',')[1];
      tempUri = `${FileSystem.cacheDirectory}tts_${Date.now()}.mp3`;
      await FileSystem.writeAsStringAsync(tempUri, base64Data, {
        encoding: FileSystem.EncodingType.Base64,
      });
      await playUri(tempUri);
    } finally {
      if (tempUri) {
        FileSystem.deleteAsync(tempUri, { idempotent: true }).catch(() => {});
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
      const audioBase64 = await FileSystem.readAsStringAsync(lastRecordingUri, {
        encoding: FileSystem.EncodingType.Base64,
      });
      const uploadFormat = inferAudioFormatFromUri(lastRecordingUri);
      const { uri: fileUri, format } = await uploadDevAudio(audioBase64, uploadFormat);
      const response = await sendAudioCommand(fileUri, format, {
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
});
