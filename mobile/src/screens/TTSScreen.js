import React, { useState, useCallback } from 'react';
import {
  View,
  Text,
  TextInput,
  Button,
  StyleSheet,
  ScrollView,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { fetchTTS } from '../api/client';
import { Audio } from 'expo-av';
import * as FileSystem from 'expo-file-system';
import ExpoGlassesAudio from 'expo-glasses-audio';
import { simulateNotificationForDev } from '../push/notificationsHandler';
import * as FileSystem from 'expo-file-system';

export default function TTSScreen() {
  const [text, setText] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [sound, setSound] = useState(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [notificationLoading, setNotificationLoading] = useState(false);

  const nativePlaybackSubscriptionRef = React.useRef(null);
  const tempFileUriRef = React.useRef(null);

  const cleanupTempFile = useCallback(async () => {
    const uri = tempFileUriRef.current;
    if (!uri) return;
    try {
      await FileSystem.deleteAsync(uri, { idempotent: true });
      // Only clear the ref if it still points to the same URI we just deleted
      if (tempFileUriRef.current === uri) {
        tempFileUriRef.current = null;
      }
    } catch {
      // ignore; keep tempFileUriRef so deletion can be retried later
    }
  }, []);

  const blobToBase64 = (blob) => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onloadend = () => {
        if (!reader.result) {
          reject(new Error('FileReader returned null result'));
          return;
        }
        const resultStr = String(reader.result);
        const commaIndex = resultStr.indexOf(',');
        if (commaIndex === -1) {
          reject(new Error('Invalid data URL format'));
          return;
        }
        const base64 = resultStr.substring(commaIndex + 1);
        if (!base64) {
          reject(new Error('Empty base64 data'));
          return;
        }
        resolve(base64);
      };
      reader.onerror = () => reject(new Error('Failed to read audio data'));
      reader.readAsDataURL(blob);
    });
  };

  const stopNativePlaybackListener = useCallback(() => {
    if (nativePlaybackSubscriptionRef.current) {
      try {
        nativePlaybackSubscriptionRef.current.remove();
      } catch {
        // ignore
      }
      nativePlaybackSubscriptionRef.current = null;
    }
  }, []);

  const handleFetchAndPlay = async () => {
    if (!text.trim()) {
      Alert.alert('Error', 'Please enter some text');
      return;
    }

    setLoading(true);
    setError(null);

    let tempFileUri = null;
    let cleanedUp = false;

    const cleanupTempFile = async () => {
      if (!cleanedUp && tempFileUri) {
        cleanedUp = true;
        try {
          await FileSystem.deleteAsync(tempFileUri, { idempotent: true });
        } catch (error) {
          // Ignore cleanup errors
        }
      }
    };

    try {
      // Stop any currently playing sound
      if (sound) {
        await sound.stopAsync();
        await sound.unloadAsync();
        setSound(null);
      }

       stopNativePlaybackListener();
       await cleanupTempFile();

      // Fetch TTS audio (explicit format)
      const audioBlob = await fetchTTS(text, { format: 'wav', accept: 'audio/wav' });

      // Convert blob to base64 for React Native
      const reader = new FileReader();
      reader.readAsDataURL(audioBlob);
      reader.onloadend = async () => {
        const base64Audio = reader.result;

        // Load and play audio
        const { sound: newSound } = await Audio.Sound.createAsync(
          { uri: base64Audio },
          { shouldPlay: true }
        );

      setSound(newSound);
      setIsPlaying(true);

        // Set up playback status listener
        newSound.setOnPlaybackStatusUpdate((status) => {
          if (status.didJustFinish) {
            setIsPlaying(false);
          }
        });
      };
    } catch (err) {
      setError(err.message);
      await cleanupTempFile();
    } finally {
      setLoading(false);
    }
  };

  const handleStop = async () => {
    stopNativePlaybackListener();

    try {
      if (ExpoGlassesAudio && typeof ExpoGlassesAudio.stopPlayback === 'function') {
        await ExpoGlassesAudio.stopPlayback();
      }
    } catch {
      // ignore
    }

    if (sound) {
      try {
        await sound.stopAsync();
        await sound.unloadAsync();
      } catch {
        // ignore stop/unload errors
      } finally {
        setSound(null);
      }
    }
    setIsPlaying(false);
    await cleanupTempFile();
  };

  const handleTestNotification = async () => {
    if (!text.trim()) {
      Alert.alert('Error', 'Please enter some text to simulate a notification');
      return;
    }

    setNotificationLoading(true);
    setError(null);

    try {
      await simulateNotificationForDev(text);
      Alert.alert('Success', 'Notification simulated! TTS should play automatically.');
    } catch (err) {
      setError(`Notification simulation failed: ${err.message}`);
      Alert.alert('Error', `Failed to simulate notification: ${err.message}`);
    } finally {
      setNotificationLoading(false);
    }
  };

  React.useEffect(() => {
    return () => {
      if (sound) {
        sound.unloadAsync();
      }
      stopNativePlaybackListener();
      cleanupTempFile();
    };
  }, [sound, stopNativePlaybackListener, cleanupTempFile]);

  return (
    <ScrollView style={styles.container}>
      <Text style={styles.title}>Text-to-Speech</Text>

      <Text style={styles.instructions}>
        Enter text to convert to speech and play.
      </Text>

      <TextInput
        style={styles.input}
        placeholder="Enter text to speak..."
        value={text}
        onChangeText={setText}
        multiline
        editable={!loading}
      />

      <View style={styles.buttonContainer}>
        <Button
          title={loading ? 'Loading...' : 'Fetch & Play'}
          onPress={handleFetchAndPlay}
          disabled={loading || isPlaying}
        />
      </View>

      {isPlaying && (
        <View style={styles.buttonContainer}>
          <Button title="Stop" onPress={handleStop} color="#dc3545" />
        </View>
      )}

      {loading && (
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#007AFF" />
          <Text style={styles.loadingText}>Fetching audio...</Text>
        </View>
      )}

      {isPlaying && (
        <View style={styles.playingContainer}>
          <Text style={styles.playingText}>🔊 Playing audio...</Text>
        </View>
      )}

      {error && (
        <View style={styles.errorContainer}>
          <Text style={styles.errorText}>Error: {error}</Text>
        </View>
      )}

      {__DEV__ && (
        <View style={styles.devSection}>
          <Text style={styles.devSectionTitle}>🧪 Dev Helper: Test Notifications</Text>
          <Text style={styles.devSectionText}>
            Simulate a push notification with the text above. This tests the notification → TTS flow
            without needing real push notifications.
          </Text>
          <View style={styles.buttonContainer}>
            <Button
              title={notificationLoading ? 'Simulating...' : '🔔 Simulate Notification'}
              onPress={handleTestNotification}
              disabled={notificationLoading || loading}
              color="#FF9800"
            />
          </View>
        </View>
      )}

      <View style={styles.infoContainer}>
        <Text style={styles.infoTitle}>ℹ️ Note:</Text>
        <Text style={styles.infoText}>
          This screen fetches audio from the backend's TTS endpoint and plays it.
          Make sure your backend is running and accessible.
        </Text>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 20,
    backgroundColor: '#f5f5f5',
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 10,
  },
  instructions: {
    fontSize: 14,
    color: '#666',
    marginBottom: 20,
  },
  input: {
    backgroundColor: 'white',
    padding: 15,
    borderRadius: 5,
    fontSize: 16,
    marginBottom: 15,
    minHeight: 100,
    textAlignVertical: 'top',
  },
  buttonContainer: {
    marginBottom: 10,
  },
  loadingContainer: {
    marginVertical: 20,
    alignItems: 'center',
  },
  loadingText: {
    marginTop: 10,
    color: '#666',
  },
  playingContainer: {
    backgroundColor: '#e3f2fd',
    padding: 15,
    borderRadius: 5,
    marginVertical: 15,
    alignItems: 'center',
  },
  playingText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#1976d2',
  },
  errorContainer: {
    backgroundColor: '#ffebee',
    padding: 15,
    borderRadius: 5,
    marginTop: 15,
  },
  errorText: {
    color: '#c62828',
  },
  infoContainer: {
    backgroundColor: '#e8f5e9',
    padding: 15,
    borderRadius: 5,
    marginTop: 20,
  },
  infoTitle: {
    fontSize: 14,
    fontWeight: '600',
    marginBottom: 5,
  },
  infoText: {
    fontSize: 13,
    color: '#2e7d32',
  },
  devSection: {
    backgroundColor: '#fff3e0',
    padding: 15,
    borderRadius: 5,
    marginTop: 20,
    marginBottom: 10,
  },
  devSectionTitle: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 8,
    color: '#e65100',
  },
  devSectionText: {
    fontSize: 13,
    color: '#666',
    marginBottom: 10,
  },
});
