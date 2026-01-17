import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, ScrollView, Switch, TouchableOpacity, Alert } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Audio } from 'expo-av';

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

  // Load dev mode setting
  useEffect(() => {
    loadDevMode();
    checkAudioRoute();

    // Cleanup
    return () => {
      if (sound) {
        sound.unloadAsync();
      }
    };
  }, []);

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

      // Set audio mode
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
        // In production mode, we would check for Bluetooth connection
        // For now, we simulate this
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
      
      // Configure recording for current mode
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
        `Audio saved locally.\n\nIn ${devMode ? 'DEV' : 'Glasses'} mode.\n\nReady to play back or upload to backend.`,
        [{ text: 'OK' }]
      );
    } catch (error) {
      setLastError(`Stop recording failed: ${error.message}`);
      console.error('Failed to stop recording:', error);
    }
  };

  const playRecording = async () => {
    if (!lastRecordingUri) {
      Alert.alert('No Recording', 'Please record audio first.');
      return;
    }

    try {
      setLastError(null);
      
      // Unload any existing sound
      if (sound) {
        await sound.unloadAsync();
        setSound(null);
      }

      // Configure audio mode for playback
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
      setIsPlaying(true);

      // Set up playback status update
      newSound.setOnPlaybackStatusUpdate((status) => {
        if (status.didJustFinish) {
          setIsPlaying(false);
        }
      });

      Alert.alert(
        'Playing Recording',
        `Playback through ${devMode ? 'phone speaker' : 'glasses (if connected, else phone speaker)'}`
      );
    } catch (error) {
      setLastError(`Playback failed: ${error.message}`);
      console.error('Failed to play recording:', error);
      setIsPlaying(false);
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
      console.error('Failed to stop playback:', error);
    }
  };

  const testAudioPipeline = () => {
    Alert.alert(
      'Audio Pipeline Flow',
      devMode
        ? '📱 DEV MODE\n\nRecord from: Phone mic\nPlayback through: Phone speaker\n\nFull pipeline:\n1. Record audio\n2. Upload to /v1/dev/audio\n3. Send to /v1/command\n4. Receive /v1/tts response\n5. Play through phone speaker'
        : '👓 GLASSES MODE\n\nRecord from: Glasses mic (Bluetooth)\nPlayback through: Glasses speakers\n\nFull pipeline:\n1. Record audio\n2. Upload to /v1/dev/audio\n3. Send to /v1/command\n4. Receive /v1/tts response\n5. Play through glasses speakers\n\n⚠️ Requires native Bluetooth implementation',
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
        <Text style={styles.cardTitle}>Audio Playback</Text>
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

      {/* Pipeline Test */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Audio Command Pipeline</Text>
        <Text style={styles.text}>
          Both modes use the same backend pipeline:
        </Text>
        <Text style={styles.mono}>
          Record → /v1/dev/audio → /v1/command → /v1/tts → Play
        </Text>
        <TouchableOpacity style={[styles.button, styles.buttonSecondary]} onPress={testAudioPipeline}>
          <Text style={styles.buttonTextSecondary}>ℹ️ View Pipeline Details</Text>
        </TouchableOpacity>
      </View>

      {/* Implementation Status */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Implementation Status</Text>
        <Text style={styles.text}>✓ DEV mode (phone mic/speaker) - Working</Text>
        <Text style={styles.text}>✓ Recording and playback - Working</Text>
        <Text style={styles.text}>✓ Error handling - Working</Text>
        <Text style={styles.text}>⚠ Glasses mode - Requires native Bluetooth code</Text>
        <Text style={styles.text}>⚠ Backend integration - Ready for implementation</Text>
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
});
