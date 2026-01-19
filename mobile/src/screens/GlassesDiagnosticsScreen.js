import React, { useEffect, useState } from 'react';
import { Alert, ScrollView, StyleSheet, Switch, Text, TouchableOpacity, View } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Audio } from 'expo-av';
import * as FileSystem from 'expo-file-system';
import { fetchTTS, sendAudioCommand, uploadDevAudio } from '../api/client';
import { getDebugState, simulateNotificationForDev } from '../push';

const DEV_MODE_KEY = '@glasses_dev_mode';

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

  useEffect(() => {
    (async () => {
      try {
        const saved = await AsyncStorage.getItem(DEV_MODE_KEY);
        if (saved !== null) setDevMode(JSON.parse(saved));
      } catch {
        // ignore
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

    // Periodically refresh push debug state (every 5 seconds)
    const interval = setInterval(() => {
      try {
        const state = getDebugState();
        setPushDebugState(state);
      } catch (error) {
        console.error('Failed to get push debug state:', error);
      }
    }, 5000);

    return () => {
      clearInterval(interval);
      if (sound) {
        sound.unloadAsync();
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
      } else {
        setConnectionState('⚠ Glasses mode (native routing module required)');
        setAudioRoute('Bluetooth HFP routing not active in Expo-only build');
      }
      setLastError(null);
    } catch (error) {
      setLastError(`Audio setup failed: ${error.message}`);
      setConnectionState('✗ Error');
      setAudioRoute('Unknown');
    }
  };

  const startRecording = async () => {
    try {
      setLastError(null);

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
    } catch (error) {
      setLastError(`Recording failed: ${error.message}`);
      setIsRecording(false);
    }
  };

  const stopRecording = async () => {
    try {
      setIsRecording(false);
      await recording.stopAndUnloadAsync();
      const uri = recording.getURI();
      setRecording(null);
      setLastRecordingUri(uri);
      Alert.alert('Recording Complete', 'Saved locally.');
    } catch (error) {
      setLastError(`Stop recording failed: ${error.message}`);
    }
  };

  const stopPlayback = async () => {
    try {
      if (sound) {
        await sound.stopAsync();
        await sound.unloadAsync();
        setSound(null);
      }
      setIsPlaying(false);
    } catch (error) {
      setLastError(`Stop playback failed: ${error.message}`);
    }
  };

  const playUri = async (uri) => {
    if (sound) {
      await sound.unloadAsync();
      setSound(null);
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
    setIsPlaying(true);

    newSound.setOnPlaybackStatusUpdate((status) => {
      if (status.didJustFinish) {
        setIsPlaying(false);
      }
      if (status.error) {
        setLastError(`Playback error: ${status.error}`);
      }
    });
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
      const { uri: fileUri, format } = await uploadDevAudio(audioBase64, 'm4a');
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
  responseContainer: { marginTop: 12, padding: 12, backgroundColor: '#e8f5e9', borderRadius: 8, borderLeftWidth: 4, borderLeftColor: '#4caf50' },
  responseTitle: { fontSize: 14, fontWeight: '600', color: '#2e7d32', marginBottom: 6 },
  responseText: { fontSize: 14, color: '#1b5e20', lineHeight: 20 },
  debugInfo: { marginTop: 12, padding: 12, backgroundColor: '#f5f5f5', borderRadius: 8 },
  debugLabel: { fontSize: 13, fontWeight: '600', color: '#666', marginTop: 8 },
  debugValue: { fontSize: 13, color: '#333', marginTop: 2, marginLeft: 8 },
});

/*
Legacy implementation kept (commented out) while we stabilize diagnostics.

---

import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, ScrollView, Switch, TouchableOpacity, Alert, Platform } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Audio } from 'expo-av';
import * as FileSystem from 'expo-file-system';
import { uploadDevAudio, sendAudioCommand, fetchTTS } from '../api/client';
import GlassesAudio from '../../modules/glasses-audio';

const DEV_MODE_KEY = '@glasses_dev_mode';

export default function GlassesDiagnosticsScreen() {
  const [devMode, setDevMode] = useState(false);
  const [audioRoute, setAudioRoute] = useState('Unknown');
  const [audioRouteDetails, setAudioRouteDetails] = useState(null);
  const [connectionState, setConnectionState] = useState('Checking...');
  const [lastError, setLastError] = useState(null);
  const [isRecording, setIsRecording] = useState(false);
  const [recording, setRecording] = useState(null);
  const [lastRecordingUri, setLastRecordingUri] = useState(null);
  const [sound, setSound] = useState(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [commandResponse, setCommandResponse] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [nativeModuleAvailable, setNativeModuleAvailable] = useState(false);

  // Load dev mode setting and start monitoring
  useEffect(() => {
    loadDevMode();
    checkNativeModule();
    checkAudioRoute();
    setNativePlayerAvailable(isGlassesPlayerAvailable());

    // Start monitoring audio route changes (Android only)
    let subscription;
    if (Platform.OS === 'android') {
      try {
        GlassesAudio.startMonitoring();
        subscription = GlassesAudio.addAudioRouteChangeListener((event) => {
          console.log('Audio route changed:', event.route);
          updateAudioRouteFromNative(event.route);
        });
      import React, { useEffect, useState } from 'react';
      import { Alert, ScrollView, StyleSheet, Switch, Text, TouchableOpacity, View } from 'react-native';
      import AsyncStorage from '@react-native-async-storage/async-storage';
      import { Audio } from 'expo-av';
      import * as FileSystem from 'expo-file-system';
      import { fetchTTS, sendAudioCommand, uploadDevAudio } from '../api/client';

      const DEV_MODE_KEY = '@glasses_dev_mode';

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
        const [isSpeaking, setIsSpeaking] = useState(false);

        useEffect(() => {
          loadDevMode();
          checkAudioRoute();

          return () => {
            if (sound) {
              sound.unloadAsync();
            }
          };
        }, []);

        useEffect(() => {
          checkAudioRoute();
        }, [devMode]);

        const loadDevMode = async () => {
          try {
            const saved = await AsyncStorage.getItem(DEV_MODE_KEY);
            if (saved !== null) {
              setDevMode(JSON.parse(saved));
            }
          } catch (error) {
            console.error('Failed to load dev mode:', error);
          }
        };

        const toggleDevMode = async (value) => {
          try {
            setDevMode(value);
            await AsyncStorage.setItem(DEV_MODE_KEY, JSON.stringify(value));
            setLastError(null);
          } catch (error) {
            setLastError('Failed to save dev mode setting');
            console.error('Failed to save dev mode:', error);
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
            } else {
              setConnectionState('⚠ Glasses mode (native implementation needed)');
              setAudioRoute('Bluetooth HFP (requires native code)');
            }

            setLastError(null);
          } catch (error) {
            setLastError(`Audio setup failed: ${error.message}`);
            setConnectionState('✗ Error');
            setAudioRoute('Unknown');
            console.error('Audio route check failed:', error);
          }
        };

        const startRecording = async () => {
          try {
            setLastError(null);

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
          } catch (error) {
            setLastError(`Recording failed: ${error.message}`);
            console.error('Failed to start recording:', error);
          }
        };

        const stopRecording = async () => {
          try {
            setIsRecording(false);
            await recording.stopAndUnloadAsync();
            const uri = recording.getURI();
            setRecording(null);
            setLastRecordingUri(uri);

            Alert.alert(
              'Recording Complete',
              `Audio saved locally.\n\nIn ${devMode ? 'DEV' : 'Glasses'} mode.\n\nReady to play back or send to backend.`,
              [{ text: 'OK' }]
            );
          } catch (error) {
            setLastError(`Stop recording failed: ${error.message}`);
            console.error('Failed to stop recording:', error);
          }
        };

        const stopPlayback = async () => {
          try {
            if (sound) {
              await sound.stopAsync();
              await sound.unloadAsync();
              setSound(null);
            }
            setIsPlaying(false);
            setIsSpeaking(false);
          } catch (error) {
            setLastError(`Stop playback failed: ${error.message}`);
            console.error('Failed to stop playback:', error);
          }
        };

        const playUri = async (uri, { title } = {}) => {
          // Unload any existing sound
          if (sound) {
            await sound.unloadAsync();
            setSound(null);
          }

          await Audio.setAudioModeAsync({
            allowsRecordingIOS: false,
            playsInSilentModeIOS: true,
            staysActiveInBackground: false,
            shouldDuckAndroid: false,
            playThroughEarpieceAndroid: false,
          });

          const { sound: newSound } = await Audio.Sound.createAsync(
            { uri },
            { shouldPlay: true }
          );

          setSound(newSound);
          setIsPlaying(true);

          newSound.setOnPlaybackStatusUpdate((status) => {
            if (status.didJustFinish) {
              setIsPlaying(false);
            }
            if (status.error) {
              setLastError(`Playback error: ${status.error}`);
            }
          });

          if (title) {
            Alert.alert(title, devMode ? 'Playback through phone speaker' : 'Playback through phone audio (native glasses routing TBD)');
          }
        };

        const playRecording = async () => {
          if (!lastRecordingUri) {
            Alert.alert('No Recording', 'Please record audio first.');
            return;
          }

          try {
            setLastError(null);
            await playUri(lastRecordingUri, { title: 'Playing Recording' });
          } catch (error) {
            setLastError(`Playback failed: ${error.message}`);
            console.error('Failed to play recording:', error);
            setIsPlaying(false);
          }
        };

        const speakText = async (text) => {
          if (!text) return;

          setIsSpeaking(true);
          setLastError(null);

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
          } catch (error) {
            setLastError(`TTS failed: ${error.message}`);
            console.error('Failed to speak text:', error);
          } finally {
            setIsSpeaking(false);
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

          try {
            setIsProcessing(true);
            setLastError(null);
            setCommandResponse(null);

            const audioBase64 = await FileSystem.readAsStringAsync(lastRecordingUri, {
              encoding: FileSystem.EncodingType.Base64,
            });

            const { uri: fileUri, format } = await uploadDevAudio(audioBase64, 'm4a');

            const response = await sendAudioCommand(fileUri, format, {
              profile: 'dev',
              client_context: {
                device: 'mobile',
                app_version: '1.0.0',
                mode: devMode ? 'dev' : 'glasses',
              },
            });

            setCommandResponse(response);

            if (response.spoken_text) {
              await speakText(response.spoken_text);
            }

            Alert.alert(
              'Pipeline Complete',
              `Command processed successfully!\n\n${response.spoken_text || 'Response received (no text content)'}`,
              [{ text: 'OK' }]
            );
          } catch (error) {
            setLastError(`Pipeline failed: ${error.message}`);
            console.error('Failed to process audio through pipeline:', error);
            Alert.alert('Error', `Failed to process command: ${error.message}`);
          } finally {
            setIsProcessing(false);
          }
        };

        const getStatusIcon = () => {
          if (connectionState.includes('✓')) return '🟢';
          if (connectionState.includes('✗')) return '🔴';
          if (connectionState.includes('⚠')) return '🟡';
          return '⚪';
        };

        const showPipelineInfo = () => {
          Alert.alert(
            'Audio Pipeline Flow',
            devMode
              ? '📱 DEV MODE\n\nRecord from: Phone mic\nPlayback through: Phone speaker\n\nBackend pipeline:\n1. Record audio\n2. Upload to /v1/dev/audio\n3. Send to /v1/command\n4. Receive response\n5. Fetch /v1/tts + play audio\n\n✓ Steps 1-5 implemented'
              : '👓 GLASSES MODE\n\nThis screen runs in Expo-friendly mode.\n\nBackend pipeline:\n1. Record audio\n2. Upload to /v1/dev/audio\n3. Send to /v1/command\n4. Receive response\n5. Fetch /v1/tts + play audio\n\nNote: True Bluetooth routing requires the native glasses module.',
            [{ text: 'OK' }]
          );
        };

        return (
          <ScrollView style={styles.container} contentContainerStyle={styles.content}>
            <Text style={styles.title}>Glasses Audio Diagnostics</Text>

            <View style={styles.card}>
              <View style={styles.toggleContainer}>
                <View style={styles.toggleLabel}>
                  <Text style={styles.cardTitle}>{devMode ? '📱 DEV Mode' : '👓 Glasses Mode'}</Text>
                  <Text style={styles.subtext}>
                    {devMode ? 'Phone mic/speaker for rapid iteration' : 'Native glasses routing not enabled in this screen'}
                  </Text>
                </View>
                <Switch value={devMode} onValueChange={toggleDevMode} />
              </View>
            </View>

            <View style={styles.card}>
              <Text style={styles.cardTitle}>Connection State</Text>
              <View style={styles.statusRow}>
                <Text style={styles.statusLabel}>Status:</Text>
                <Text style={styles.statusValue}>{getStatusIcon()} {connectionState}</Text>
              </View>
              <View style={styles.statusRow}>
                <Text style={styles.statusLabel}>Audio Route:</Text>
                <Text style={styles.statusValue}>{audioRoute}</Text>
              </View>
              <TouchableOpacity style={[styles.button, styles.buttonSecondary]} onPress={checkAudioRoute}>
                <Text style={styles.buttonTextSecondary}>🔄 Refresh Status</Text>
              </TouchableOpacity>
            </View>

            {lastError && (
              <View style={[styles.card, styles.warningCard]}>
                <Text style={styles.cardTitle}>⚠️ Last Error</Text>
                <Text style={styles.errorText}>{lastError}</Text>
                <TouchableOpacity style={[styles.button, styles.buttonSecondary]} onPress={() => setLastError(null)}>
                  <Text style={styles.buttonTextSecondary}>Clear Error</Text>
                </TouchableOpacity>
              </View>
            )}

            <View style={styles.card}>
              <Text style={styles.cardTitle}>Audio Recording</Text>
              <TouchableOpacity
                style={[styles.button, isRecording && styles.buttonRecording]}
                onPress={isRecording ? stopRecording : startRecording}
              >
                <Text style={styles.buttonText}>{isRecording ? '⏹ Stop Recording' : '🎤 Start Recording'}</Text>
              </TouchableOpacity>
              {lastRecordingUri && <Text style={styles.successText}>✓ Recording saved locally</Text>}
            </View>

            <View style={styles.card}>
              <Text style={styles.cardTitle}>Audio Playback (Local)</Text>
              <TouchableOpacity
                style={[styles.button, !lastRecordingUri && styles.buttonDisabled, isPlaying && styles.buttonRecording]}
                onPress={isPlaying ? stopPlayback : playRecording}
                disabled={!lastRecordingUri}
              >
                <Text style={styles.buttonText}>{isPlaying ? '⏹ Stop Playback' : '▶️ Play Last Recording'}</Text>
              </TouchableOpacity>
            </View>

            <View style={styles.card}>
              <Text style={styles.cardTitle}>Backend Command Pipeline</Text>
              <Text style={styles.mono}>Record → /v1/dev/audio → /v1/command → /v1/tts</Text>
              <TouchableOpacity
                style={[styles.button, (!lastRecordingUri || isProcessing) && styles.buttonDisabled]}
                onPress={processAudioThroughPipeline}
                disabled={!lastRecordingUri || isProcessing}
              >
                <Text style={styles.buttonText}>{isProcessing ? '⏳ Processing...' : '🚀 Send to Backend & Speak Response'}</Text>
              </TouchableOpacity>

              {commandResponse && (
                <View style={styles.responseContainer}>
                  <Text style={styles.responseTitle}>Backend Response:</Text>
                  <Text style={styles.responseText}>{commandResponse.spoken_text}</Text>
                  {commandResponse.debug && (
                    <Text style={styles.hintText}>Debug info present</Text>
                  )}
                </View>
              )}

              <TouchableOpacity style={[styles.button, styles.buttonSecondary]} onPress={showPipelineInfo}>
                <Text style={styles.buttonTextSecondary}>ℹ️ View Pipeline Details</Text>
              </TouchableOpacity>
            </View>

            <View style={styles.card}>
              <Text style={styles.cardTitle}>Implementation Status</Text>
              <Text style={styles.text}>✓ DEV mode pipeline + TTS playback</Text>
              <Text style={styles.text}>⚠ Native glasses routing lives in native module builds</Text>
            </View>
          </ScrollView>
        );
      }

      const styles = StyleSheet.create({
        container: {
          flex: 1,
          backgroundColor: '#f5f5f5',
        },
        content: {
          padding: 20,
          paddingBottom: 40,
        },
        title: {
          fontSize: 24,
          fontWeight: 'bold',
          marginBottom: 12,
        },
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
        warningCard: {
          backgroundColor: '#fff3cd',
          borderLeftWidth: 4,
          borderLeftColor: '#ff9800',
        },
        cardTitle: {
          fontSize: 16,
          fontWeight: '600',
          marginBottom: 8,
          color: '#000',
        },
        text: {
          fontSize: 14,
          color: '#333',
          marginBottom: 6,
          lineHeight: 20,
        },
        mono: {
          fontSize: 12,
          fontFamily: 'monospace',
          color: '#555',
          marginBottom: 8,
          backgroundColor: '#f5f5f5',
          padding: 8,
          borderRadius: 4,
        },
        toggleContainer: {
          flexDirection: 'row',
          justifyContent: 'space-between',
          alignItems: 'center',
        },
        toggleLabel: {
          flex: 1,
          marginRight: 12,
        },
        subtext: {
          fontSize: 12,
          color: '#666',
          marginTop: 4,
          lineHeight: 16,
        },
        statusRow: {
          flexDirection: 'row',
          marginBottom: 8,
          alignItems: 'flex-start',
        },
        statusLabel: {
          fontSize: 14,
          fontWeight: '600',
          color: '#666',
          width: 100,
        },
        statusValue: {
          fontSize: 14,
          color: '#333',
          flex: 1,
        },
        errorText: {
          color: '#d32f2f',
          fontSize: 14,
          marginBottom: 8,
        },
        successText: {
          color: '#4caf50',
          fontSize: 14,
          marginTop: 8,
          textAlign: 'center',
        },
        hintText: {
          color: '#999',
          fontSize: 12,
          marginTop: 8,
          textAlign: 'center',
          fontStyle: 'italic',
        },
        button: {
          backgroundColor: '#007AFF',
          padding: 14,
          borderRadius: 8,
          alignItems: 'center',
          marginTop: 12,
        },
        buttonSecondary: {
          backgroundColor: '#f0f0f0',
        },
        buttonRecording: {
          backgroundColor: '#d32f2f',
        },
        buttonDisabled: {
          backgroundColor: '#ccc',
          opacity: 0.6,
        },
        buttonText: {
          color: 'white',
          fontSize: 16,
          fontWeight: '600',
        },
        buttonTextSecondary: {
          color: '#007AFF',
          fontSize: 16,
          fontWeight: '600',
        },
        responseContainer: {
          marginTop: 12,
          padding: 12,
          backgroundColor: '#e8f5e9',
          borderRadius: 8,
          borderLeftWidth: 4,
          borderLeftColor: '#4caf50',
        },
        responseTitle: {
          fontSize: 14,
          fontWeight: '600',
          color: '#2e7d32',
          marginBottom: 6,
        },
        responseText: {
          fontSize: 14,
          color: '#1b5e20',
          lineHeight: 20,
        },
      });
  },
  detailTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
    marginBottom: 4,
  },
  detailText: {
    fontSize: 13,
    color: '#555',
    marginLeft: 8,
    marginBottom: 2,
    lineHeight: 18,
  },
});
*/
