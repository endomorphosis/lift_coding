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

  // Load dev mode setting
  useEffect(() => {
    loadDevMode();
    checkAudioRoute();
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
        setConnectionState('DEV Mode Active');
        setAudioRoute('Phone mic → Phone speaker');
      } else {
        // In production mode, we would check for Bluetooth connection
        // For now, we simulate this
        setConnectionState('Glasses mode (requires native code)');
        setAudioRoute('Bluetooth HFP (native implementation pending)');
      }
      setLastError(null);
    } catch (error) {
      setLastError(`Audio setup failed: ${error.message}`);
      setConnectionState('Error');
      setAudioRoute('Unknown');
      console.error('Audio route check failed:', error);
    }
  };

  const startRecording = async () => {
    try {
      setLastError(null);
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
      
      Alert.alert(
        'Recording Complete',
        `Audio saved to: ${uri}\n\nIn production, this would be uploaded to /v1/dev/audio`,
        [{ text: 'OK' }]
      );
    } catch (error) {
      setLastError(`Stop recording failed: ${error.message}`);
      console.error('Failed to stop recording:', error);
    }
  };

  const testAudioPipeline = () => {
    Alert.alert(
      'Audio Pipeline Test',
      devMode
        ? 'DEV mode: Uses phone mic/speaker\n\nFlow: Record → /v1/dev/audio → /v1/command → /v1/tts → Play'
        : 'Glasses mode: Uses glasses mic/speaker\n\nFlow: Record → /v1/dev/audio → /v1/command → /v1/tts → Play\n\nNote: Requires native Bluetooth implementation',
      [{ text: 'OK' }]
    );
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
                ? 'Using phone mic/speaker (iteration mode)'
                : 'Using glasses mic/speaker (requires native code)'}
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
          <Text style={[styles.statusValue, connectionState.includes('Error') && styles.errorText]}>
            {connectionState}
          </Text>
        </View>
        <View style={styles.statusRow}>
          <Text style={styles.statusLabel}>Audio Route:</Text>
          <Text style={styles.statusValue}>{audioRoute}</Text>
        </View>
      </View>

      {/* Error Display */}
      {lastError && (
        <View style={[styles.card, styles.errorCard]}>
          <Text style={styles.cardTitle}>⚠️ Last Error</Text>
          <Text style={styles.errorText}>{lastError}</Text>
        </View>
      )}

      {/* Recording Controls */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Test Recording</Text>
        <Text style={styles.text}>
          {devMode
            ? 'Record using phone microphone'
            : 'Record using glasses microphone (native implementation pending)'}
        </Text>
        <TouchableOpacity
          style={[styles.button, isRecording && styles.buttonRecording]}
          onPress={isRecording ? stopRecording : startRecording}
        >
          <Text style={styles.buttonText}>
            {isRecording ? '⏹ Stop Recording' : '🎤 Start Recording'}
          </Text>
        </TouchableOpacity>
      </View>

      {/* Pipeline Test */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Audio Pipeline</Text>
        <Text style={styles.text}>
          Test the full command pipeline:
        </Text>
        <Text style={styles.mono}>
          Record → /v1/dev/audio → /v1/command → /v1/tts → Play
        </Text>
        <TouchableOpacity style={styles.button} onPress={testAudioPipeline}>
          <Text style={styles.buttonText}>ℹ️ View Pipeline Info</Text>
        </TouchableOpacity>
      </View>

      {/* Implementation Notes */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Implementation Notes</Text>
        <Text style={styles.text}>
          • DEV mode: Uses Expo Audio APIs with phone mic/speaker
        </Text>
        <Text style={styles.text}>
          • Glasses mode: Requires native iOS/Android implementation for Bluetooth routing
        </Text>
        <Text style={styles.text}>
          • Both modes use the same command pipeline on the backend
        </Text>
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
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 12,
  },
  card: {
    backgroundColor: 'white',
    padding: 15,
    borderRadius: 6,
    marginBottom: 12,
  },
  cardTitle: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 8,
  },
  text: {
    fontSize: 14,
    color: '#333',
    marginBottom: 6,
  },
  mono: {
    fontSize: 12,
    fontFamily: 'monospace',
    color: '#555',
    marginBottom: 4,
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
  },
  statusRow: {
    flexDirection: 'row',
    marginBottom: 8,
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
  },
  button: {
    backgroundColor: '#007AFF',
    padding: 12,
    borderRadius: 6,
    alignItems: 'center',
    marginTop: 12,
  },
  buttonRecording: {
    backgroundColor: '#d32f2f',
  },
  buttonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: '600',
  },
});
