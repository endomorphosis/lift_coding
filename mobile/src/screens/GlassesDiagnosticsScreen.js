import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, ScrollView, Switch, TouchableOpacity, Alert } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Audio } from 'expo-av';
import * as FileSystem from 'expo-file-system';
import { uploadDevAudio, sendAudioCommand } from '../api/client';
import * as GlassesAudio from '../../modules/expo-glasses-audio';

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

  // Load dev mode setting and setup native audio route monitoring
  useEffect(() => {
    loadDevMode();
    checkAudioRoute();

    // Setup native audio route change listener (when not in dev mode)
    let routeSubscription;
    if (!devMode) {
      try {
        routeSubscription = GlassesAudio.addAudioRouteChangeListener((routeInfo) => {
          console.log('Audio route changed:', routeInfo);
          const { inputDevice, outputDevice, isBluetoothConnected } = routeInfo;
          setAudioRoute(`${inputDevice} → ${outputDevice}`);
          setConnectionState(isBluetoothConnected ? '✓ Bluetooth Connected' : '⚠ Phone Audio');
        });
      } catch (error) {
        console.log('Native audio monitoring not available:', error);
      }
    }

    // Cleanup
    return () => {
      if (sound) {
        sound.unloadAsync();
      }
      if (routeSubscription) {
        routeSubscription.remove();
      }
    };
  }, [devMode]);

  // Monitor audio route when mode changes
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
      checkAudioRoute();
    } catch (error) {
      setLastError('Failed to save dev mode setting');
      console.error('Failed to save dev mode:', error);
    }
  };

  const checkAudioRoute = async () => {
    try {
      // Request permissions
      const { status } = await Audio.requestPermissionsAsync();
      if (status !== 'granted') {
        setConnectionState('Permission denied');
        setAudioRoute('No permission');
        setLastError('Microphone permission required');
        return;
      }

      if (devMode) {
        // Dev mode uses standard expo-av
        await Audio.setAudioModeAsync({
          allowsRecordingIOS: true,
          playsInSilentModeIOS: true,
          staysActiveInBackground: false,
          shouldDuckAndroid: true,
          playThroughEarpieceAndroid: false,
        });
        
        setConnectionState('✓ DEV Mode Active');
        setAudioRoute('Phone mic → Phone speaker');
      } else {
        // Glasses mode uses native Bluetooth routing
        try {
          const routeInfo = GlassesAudio.getAudioRoute();
          const { inputDevice, outputDevice, isBluetoothConnected } = routeInfo;
          
          setAudioRoute(`${inputDevice} → ${outputDevice}`);
          setConnectionState(isBluetoothConnected ? '✓ Bluetooth Connected' : '⚠ No Bluetooth Device');
        } catch (error) {
          console.log('Native audio route check failed:', error);
          setConnectionState('⚠ Native module not available');
          setAudioRoute('Run in dev client build to use native Bluetooth');
        }
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
      setIsRecording(true);
      
      if (devMode) {
        // Dev mode: Use expo-av for phone recording
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
      } else {
        // Glasses mode: Use native Bluetooth recording (10 second duration)
        GlassesAudio.startRecording(10)
          .then((result) => {
            setIsRecording(false);
            setLastRecordingUri(result.uri);
            Alert.alert(
              'Recording Complete',
              `Audio saved to native storage.\n\nRecorded via Bluetooth from glasses.\n\nFile: ${result.uri}\nSize: ${result.size} bytes`,
              [{ text: 'OK' }]
            );
          })
          .catch((error) => {
            setIsRecording(false);
            setLastError(`Native recording failed: ${error.message}`);
          });
      }
    } catch (error) {
      setLastError(`Recording failed: ${error.message}`);
      setIsRecording(false);
      console.error('Failed to start recording:', error);
    }
  };

  const stopRecording = async () => {
    try {
      setIsRecording(false);
      
      if (devMode && recording) {
        // Dev mode: Stop expo-av recording
        await recording.stopAndUnloadAsync();
        const uri = recording.getURI();
        setRecording(null);
        setLastRecordingUri(uri);
        
        Alert.alert(
          'Recording Complete',
          `Audio saved locally.\n\nIn DEV mode.\n\nReady to play back or send to backend.`,
          [{ text: 'OK' }]
        );
      } else {
        // Glasses mode: Native recording stops automatically after duration
        await GlassesAudio.stopRecording();
      }
    } catch (error) {
      setLastError(`Stop recording failed: ${error.message}`);
      console.error('Failed to stop recording:', error);
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

      // Step 1: Read audio file and encode as base64
      // Note: expo-av HIGH_QUALITY preset uses m4a format on iOS and Android
      const audioBase64 = await FileSystem.readAsStringAsync(lastRecordingUri, {
        encoding: FileSystem.EncodingType.Base64,
      });

      // Step 2: Upload to /v1/dev/audio
      const { uri: fileUri, format } = await uploadDevAudio(audioBase64, 'm4a');

      // Step 3: Send to /v1/command
      const response = await sendAudioCommand(fileUri, format, {
        profile: 'dev',
        client_context: {
          device: 'mobile',
          app_version: '1.0.0',
          mode: devMode ? 'dev' : 'glasses',
        },
      });

      setCommandResponse(response);

      Alert.alert(
        'Pipeline Complete',
        `Command processed successfully!\n\n${response.spoken_text || 'Response received (no text content)'}\n\nNote: TTS playback not yet implemented.`,
        [{ text: 'OK' }]
      );

      // TODO: Step 4 & 5 - Implement TTS playback
      // Currently the backend returns audio as a blob, but we need to handle
      // binary audio data differently in React Native. Options:
      // 1. Have backend return base64-encoded audio
      // 2. Download audio to file using FileSystem.downloadAsync
      // 3. Use a streaming approach with expo-av
      // For now, displaying the text response is sufficient to demonstrate
      // the pipeline is working.

    } catch (error) {
      setLastError(`Pipeline failed: ${error.message}`);
      console.error('Failed to process audio through pipeline:', error);
      Alert.alert('Error', `Failed to process command: ${error.message}`);
    } finally {
      setIsProcessing(false);
    }
  };

  const playRecording = async () => {
    if (!lastRecordingUri) {
      Alert.alert('No Recording', 'Please record audio first.');
      return;
    }

    try {
      setLastError(null);
      setIsPlaying(true);
      
      if (devMode) {
        // Dev mode: Use expo-av for playback
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
          { uri: lastRecordingUri },
          { shouldPlay: true }
        );
        
        setSound(newSound);

        newSound.setOnPlaybackStatusUpdate((status) => {
          if (status.didJustFinish) {
            setIsPlaying(false);
          }
        });

        Alert.alert(
          'Playing Recording',
          `Playback through phone speaker`
        );
      } else {
        // Glasses mode: Use native Bluetooth playback
        await GlassesAudio.playAudio(lastRecordingUri);
        
        // TODO: Replace with native playback status listener
        // For now, simulate playback completion with estimated duration
        // In production, use GlassesAudio.addPlaybackStatusListener to get real status
        setTimeout(() => {
          setIsPlaying(false);
        }, 3000);
        
        Alert.alert(
          'Playing Recording',
          `Playback through Bluetooth glasses speakers`
        );
      }
    } catch (error) {
      setLastError(`Playback failed: ${error.message}`);
      console.error('Failed to play recording:', error);
      setIsPlaying(false);
    }
  };

  const stopPlayback = async () => {
    try {
      if (devMode && sound) {
        await sound.stopAsync();
        await sound.unloadAsync();
        setSound(null);
      } else {
        await GlassesAudio.stopPlayback();
      }
      setIsPlaying(false);
    } catch (error) {
      setLastError(`Stop playback failed: ${error.message}`);
      console.error('Failed to stop playback:', error);
    }
  };

  const testAudioPipeline = () => {
    Alert.alert(
      'Audio Pipeline Flow',
      devMode
        ? '📱 DEV MODE\n\nRecord from: Phone mic\nPlayback through: Phone speaker\n\nBackend pipeline:\n1. Record audio\n2. Upload to /v1/dev/audio\n3. Send to /v1/command\n4. Receive response\n\n✓ Steps 1-4 implemented\n⏳ TTS playback (step 5) coming soon'
        : '👓 GLASSES MODE\n\nRecord from: Glasses mic (Bluetooth)\nPlayback through: Glasses speakers\n\nBackend pipeline:\n1. Record audio\n2. Upload to /v1/dev/audio\n3. Send to /v1/command\n4. Receive response\n\n⚠️ Requires native Bluetooth implementation',
      [{ text: 'OK' }]
    );
  };

  const getStatusIcon = () => {
    if (connectionState.includes('✓')) return '🟢';
    if (connectionState.includes('✗')) return '🔴';
    if (connectionState.includes('⚠')) return '🟡';
    return '⚪';
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text style={styles.title}>Glasses Audio Diagnostics</Text>

      {/* Mode Toggle */}
      <View style={styles.card}>
        <View style={styles.toggleContainer}>
          <View style={styles.toggleLabel}>
            <Text style={styles.cardTitle}>
              {devMode ? '📱 DEV Mode' : '👓 Glasses Mode'}
            </Text>
            <Text style={styles.subtext}>
              {devMode
                ? 'Phone mic/speaker for rapid iteration'
                : 'Glasses mic/speaker (requires native implementation)'}
            </Text>
          </View>
          <Switch
            value={devMode}
            onValueChange={toggleDevMode}
            trackColor={{ false: '#767577', true: '#81b0ff' }}
            thumbColor={devMode ? '#007AFF' : '#f4f3f4'}
          />
        </View>
      </View>

      {/* Connection State */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Connection State</Text>
        <View style={styles.statusRow}>
          <Text style={styles.statusLabel}>Status:</Text>
          <Text style={styles.statusValue}>
            {getStatusIcon()} {connectionState}
          </Text>
        </View>
        <View style={styles.statusRow}>
          <Text style={styles.statusLabel}>Audio Route:</Text>
          <Text style={styles.statusValue}>{audioRoute}</Text>
        </View>
        <TouchableOpacity 
          style={[styles.button, styles.buttonSecondary]} 
          onPress={checkAudioRoute}
        >
          <Text style={styles.buttonTextSecondary}>🔄 Refresh Status</Text>
        </TouchableOpacity>
      </View>

      {/* Error Display */}
      {lastError && (
        <View style={[styles.card, styles.errorCard]}>
          <Text style={styles.cardTitle}>⚠️ Last Error</Text>
          <Text style={styles.errorText}>{lastError}</Text>
          <TouchableOpacity 
            style={[styles.button, styles.buttonSecondary]} 
            onPress={() => setLastError(null)}
          >
            <Text style={styles.buttonTextSecondary}>Clear Error</Text>
          </TouchableOpacity>
        </View>
      )}

      {/* Recording Controls */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Audio Recording</Text>
        <Text style={styles.text}>
          {devMode
            ? '📱 Recording from phone microphone'
            : '👓 Recording from glasses microphone (when implemented)'}
        </Text>
        <TouchableOpacity
          style={[styles.button, isRecording && styles.buttonRecording]}
          onPress={isRecording ? stopRecording : startRecording}
        >
          <Text style={styles.buttonText}>
            {isRecording ? '⏹ Stop Recording' : '🎤 Start Recording'}
          </Text>
        </TouchableOpacity>
        {lastRecordingUri && (
          <Text style={styles.successText}>✓ Recording saved locally</Text>
        )}
      </View>

      {/* Playback Controls */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Audio Playback (Local)</Text>
        <Text style={styles.text}>
          {devMode
            ? '📱 Playing through phone speaker'
            : '👓 Playing through glasses speakers (when implemented)'}
        </Text>
        <TouchableOpacity
          style={[
            styles.button,
            !lastRecordingUri && styles.buttonDisabled,
            isPlaying && styles.buttonRecording,
          ]}
          onPress={isPlaying ? stopPlayback : playRecording}
          disabled={!lastRecordingUri}
        >
          <Text style={styles.buttonText}>
            {isPlaying ? '⏹ Stop Playback' : '▶️ Play Last Recording'}
          </Text>
        </TouchableOpacity>
        {!lastRecordingUri && (
          <Text style={styles.hintText}>Record audio first to enable playback</Text>
        )}
      </View>

      {/* Backend Pipeline Test */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Backend Command Pipeline</Text>
        <Text style={styles.text}>
          Process recording through backend pipeline:
        </Text>
        <Text style={styles.mono}>
          Record → /v1/dev/audio → /v1/command
        </Text>
        <TouchableOpacity
          style={[
            styles.button,
            (!lastRecordingUri || isProcessing) && styles.buttonDisabled,
          ]}
          onPress={processAudioThroughPipeline}
          disabled={!lastRecordingUri || isProcessing}
        >
          <Text style={styles.buttonText}>
            {isProcessing ? '⏳ Processing...' : '🚀 Send to Backend & Get Response'}
          </Text>
        </TouchableOpacity>
        {!lastRecordingUri && (
          <Text style={styles.hintText}>Record audio first to enable</Text>
        )}
        {commandResponse && (
          <View style={styles.responseContainer}>
            <Text style={styles.responseTitle}>Backend Response:</Text>
            <Text style={styles.responseText}>{commandResponse.spoken_text}</Text>
            {commandResponse.ui_cards && commandResponse.ui_cards.length > 0 && (
              <Text style={styles.hintText}>
                {commandResponse.ui_cards.length} UI card(s) received
              </Text>
            )}
          </View>
        )}
        <Text style={styles.hintText}>
          Note: TTS playback will be added in a future update
        </Text>
      </View>

      {/* Pipeline Test */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Audio Command Pipeline</Text>
        <Text style={styles.text}>
          Both modes use the same backend pipeline:
        </Text>
        <Text style={styles.mono}>
          Record → /v1/dev/audio → /v1/command → Response
        </Text>
        <TouchableOpacity style={[styles.button, styles.buttonSecondary]} onPress={testAudioPipeline}>
          <Text style={styles.buttonTextSecondary}>ℹ️ View Pipeline Details</Text>
        </TouchableOpacity>
      </View>

      {/* Implementation Status */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Implementation Status</Text>
        <Text style={styles.text}>✓ DEV mode (phone mic/speaker) - Working</Text>
        <Text style={styles.text}>✓ Glasses mode native Bluetooth - Implemented</Text>
        <Text style={styles.text}>✓ Recording and playback - Working</Text>
        <Text style={styles.text}>✓ Backend pipeline integration - Working</Text>
        <Text style={styles.text}>✓ Error handling - Working</Text>
        <Text style={styles.text}>✓ Native module bridge (iOS/Android) - Complete</Text>
        <Text style={styles.mono}>⚠️  Requires expo-dev-client build to test native Bluetooth</Text>
      </View>

      {/* Docs */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Documentation</Text>
        <Text style={styles.mono}>docs/meta-ai-glasses-audio-routing.md</Text>
        <Text style={styles.mono}>mobile/glasses/README.md</Text>
        <Text style={styles.mono}>mobile/glasses/TODO.md</Text>
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
    marginBottom: 4,
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
    alignItems: 'center',
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
  errorCard: {
    backgroundColor: '#fff3cd',
    borderLeftWidth: 4,
    borderLeftColor: '#ff9800',
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
