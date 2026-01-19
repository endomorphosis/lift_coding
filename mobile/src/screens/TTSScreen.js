import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  Button,
  StyleSheet,
  ScrollView,
  ActivityIndicator,
  Alert,
  Platform,
} from 'react-native';
import { fetchTTS } from '../api/client';
import { Audio } from 'expo-av';
import { simulateNotificationForDev } from '../push/notificationsHandler';

export default function TTSScreen() {
  const [text, setText] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [sound, setSound] = useState(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [notificationLoading, setNotificationLoading] = useState(false);

  const handleFetchAndPlay = async () => {
    if (!text.trim()) {
      Alert.alert('Error', 'Please enter some text');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // Stop any currently playing sound
      if (sound) {
        await sound.stopAsync();
        await sound.unloadAsync();
        setSound(null);
      }

      // Fetch TTS audio
      const audioBlob = await fetchTTS(text);

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
    } finally {
      setLoading(false);
    }
  };

  const handleStop = async () => {
    if (sound) {
      await sound.stopAsync();
      setIsPlaying(false);
    }
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
    return sound
      ? () => {
          sound.unloadAsync();
        }
      : undefined;
  }, [sound]);

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
