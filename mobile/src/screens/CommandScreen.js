import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  TextInput,
  Button,
  StyleSheet,
  ScrollView,
  ActivityIndicator,
  Alert,
  TouchableOpacity,
  Switch,
} from 'react-native';
import { Audio } from 'expo-av';
import * as FileSystem from 'expo-file-system';
import { sendCommand, uploadDevAudio, sendAudioCommand, fetchTTS } from '../api/client';

export default function CommandScreen() {
  const [commandText, setCommandText] = useState('');
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState(null);
  const [error, setError] = useState(null);
  
  // Audio recording state
  const [recording, setRecording] = useState(null);
  const [isRecording, setIsRecording] = useState(false);
  const [recordingDuration, setRecordingDuration] = useState(0);
  const [recordingIntervalId, setRecordingIntervalId] = useState(null);
  const [audioUri, setAudioUri] = useState(null);
  const [audioSize, setAudioSize] = useState(0);

  // TTS playback state
  const [ttsSound, setTtsSound] = useState(null);
  const [isTtsPlaying, setIsTtsPlaying] = useState(false);
  const [ttsLoading, setTtsLoading] = useState(false);

  // Dev mode toggle
  const [showDebugPanel, setShowDebugPanel] = useState(true);
  const [autoPlayTts, setAutoPlayTts] = useState(true);

  useEffect(() => {
    // Request audio permissions on mount
    (async () => {
      try {
        await Audio.requestPermissionsAsync();
        await Audio.setAudioModeAsync({
          allowsRecordingIOS: true,
          playsInSilentModeIOS: true,
        });
      } catch (err) {
        console.error('Failed to get audio permissions:', err);
      }
    })();

    // Cleanup TTS sound on unmount
    return () => {
      if (ttsSound) {
        ttsSound.unloadAsync();
      }
    };
  }, []);

  const playTTS = async (text) => {
    if (!text) return;

    setTtsLoading(true);
    try {
      // Stop any currently playing TTS
      if (ttsSound) {
        await ttsSound.stopAsync();
        await ttsSound.unloadAsync();
        setTtsSound(null);
      }

      // Fetch TTS audio
      const audioBlob = await fetchTTS(text);

      // Convert blob to base64
      const reader = new FileReader();
      reader.readAsDataURL(audioBlob);
      reader.onloadend = async () => {
        const base64Audio = reader.result;

        // Write to temporary file for better compatibility
        const tempUri = `${FileSystem.cacheDirectory}tts_${Date.now()}.mp3`;
        const base64Data = base64Audio.split(',')[1]; // Remove data:audio/...;base64, prefix
        await FileSystem.writeAsStringAsync(tempUri, base64Data, {
          encoding: FileSystem.EncodingType.Base64,
        });

        // Load and play audio from file
        const { sound: newSound } = await Audio.Sound.createAsync(
          { uri: tempUri },
          { shouldPlay: true }
        );

        setTtsSound(newSound);
        setIsTtsPlaying(true);

        // Set up playback status listener
        newSound.setOnPlaybackStatusUpdate((status) => {
          if (status.didJustFinish) {
            setIsTtsPlaying(false);
            // Clean up temp file
            FileSystem.deleteAsync(tempUri, { idempotentError: true }).catch(() => {});
          }
        });
      };
    } catch (err) {
      console.error('TTS playback failed:', err);
      Alert.alert('TTS Error', `Failed to play audio: ${err.message}`);
    } finally {
      setTtsLoading(false);
    }
  };

  const stopTTS = async () => {
    if (ttsSound) {
      await ttsSound.stopAsync();
      setIsTtsPlaying(false);
    }
  };

  const handleSendCommand = async () => {
    if (!commandText.trim()) {
      Alert.alert('Error', 'Please enter a command');
      return;
    }

    setLoading(true);
    setError(null);
    setResponse(null);

    try {
      const data = await sendCommand(commandText);
      setResponse(data);
      
      // Auto-play TTS if enabled and spoken_text is available
      if (autoPlayTts && data.spoken_text) {
        await playTTS(data.spoken_text);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const startRecording = async () => {
    try {
      const { recording: newRecording } = await Audio.Recording.createAsync(
        Audio.RecordingOptionsPresets.HIGH_QUALITY
      );
      setRecording(newRecording);
      setIsRecording(true);
      setRecordingDuration(0);
      setAudioUri(null);
      setAudioSize(0);

      // Update duration every second
      const interval = setInterval(() => {
        setRecordingDuration((prev) => prev + 1);
      }, 1000);

      // Store interval ID in state
      setRecordingIntervalId(interval);
    } catch (err) {
      console.error('Failed to start recording:', err);
      Alert.alert('Error', 'Failed to start recording');
    }
  };

  const stopRecording = async () => {
    if (!recording) return;

    try {
      // Clear duration interval
      if (recordingIntervalId) {
        clearInterval(recordingIntervalId);
        setRecordingIntervalId(null);
      }

      setIsRecording(false);
      await recording.stopAndUnloadAsync();
      const uri = recording.getURI();
      
      // Get file size
      const fileInfo = await FileSystem.getInfoAsync(uri);
      const sizeKB = Math.round(fileInfo.size / 1024);

      setAudioUri(uri);
      setAudioSize(sizeKB);
      setRecording(null);
    } catch (err) {
      console.error('Failed to stop recording:', err);
      Alert.alert('Error', 'Failed to stop recording');
    }
  };

  const sendAudioAsCommand = async () => {
    if (!audioUri) {
      Alert.alert('Error', 'No audio recorded');
      return;
    }

    setLoading(true);
    setError(null);
    setResponse(null);

    try {
      // Read audio file as base64
      const audioBase64 = await FileSystem.readAsStringAsync(audioUri, {
        encoding: FileSystem.EncodingType.Base64,
      });

      // Upload to dev endpoint
      // Note: Format is hardcoded as 'm4a' which is the default for expo-av HIGH_QUALITY preset
      // On iOS this produces .caf or .m4a, on Android typically .m4a
      // For production, consider detecting format from file extension or Recording.getStatusAsync()
      const { uri: fileUri, format } = await uploadDevAudio(audioBase64, 'm4a');

      // Send as audio command with duration in ms
      const data = await sendAudioCommand(fileUri, format, {
        duration_ms: recordingDuration * 1000,
      });
      setResponse(data);
      
      // Auto-play TTS if enabled and spoken_text is available
      if (autoPlayTts && data.spoken_text) {
        await playTTS(data.spoken_text);
      }
      
      // Clear recorded audio
      setAudioUri(null);
      setRecordingDuration(0);
      setAudioSize(0);
    } catch (err) {
      console.error('Audio command failed:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const formatDuration = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const getErrorHint = (errorMessage) => {
    if (!errorMessage) return null;
    
    if (errorMessage.includes('403') || errorMessage.includes('forbidden')) {
      return '💡 Hint: The backend dev mode may be disabled. Check HANDSFREE_AUTH_MODE=dev.';
    }
    
    if (errorMessage.includes('fetch') || errorMessage.includes('Network') || errorMessage.includes('Failed to fetch')) {
      return '💡 Hint: Cannot reach backend. Ensure it\'s running and accessible.';
    }
    
    return null;
  };

  const renderUICards = (cards) => {
    if (!cards || cards.length === 0) return null;

    return (
      <View style={styles.cardsContainer}>
        <Text style={styles.sectionTitle}>UI Cards:</Text>
        {cards.map((card, index) => (
          <View key={index} style={styles.card}>
            <Text style={styles.cardTitle}>{card.title || `Card ${index + 1}`}</Text>
            {card.subtitle ? (
              <Text style={styles.cardSubtitle}>{card.subtitle}</Text>
            ) : null}
            {Array.isArray(card.lines)
              ? card.lines.map((line, idx) => (
                  <Text key={idx} style={styles.cardLine}>
                    {line}
                  </Text>
                ))
              : null}
            {card.deep_link ? (
              <Text style={styles.cardLink}>{card.deep_link}</Text>
            ) : null}
          </View>
        ))}
      </View>
    );
  };

  return (
    <ScrollView style={styles.container}>
      <Text style={styles.title}>Send Command</Text>

      {/* Dev Mode Settings */}
      <View style={styles.devSettingsSection}>
        <View style={styles.settingRow}>
          <Text style={styles.settingLabel}>Show Debug Panel</Text>
          <Switch
            value={showDebugPanel}
            onValueChange={setShowDebugPanel}
          />
        </View>
        <View style={styles.settingRow}>
          <Text style={styles.settingLabel}>Auto-play TTS</Text>
          <Switch
            value={autoPlayTts}
            onValueChange={setAutoPlayTts}
          />
        </View>
      </View>

      {/* TTS Playback Controls */}
      {(ttsLoading || isTtsPlaying) && (
        <View style={styles.ttsControlsSection}>
          {ttsLoading && (
            <View style={styles.ttsLoadingContainer}>
              <ActivityIndicator size="small" color="#007AFF" />
              <Text style={styles.ttsLoadingText}>Loading TTS...</Text>
            </View>
          )}
          {isTtsPlaying && (
            <View style={styles.ttsPlayingContainer}>
              <Text style={styles.ttsPlayingText}>🔊 Playing TTS...</Text>
              <TouchableOpacity
                style={styles.ttsStopButton}
                onPress={stopTTS}
              >
                <Text style={styles.ttsStopButtonText}>⏹ Stop</Text>
              </TouchableOpacity>
            </View>
          )}
        </View>
      )}

      {/* Text Command Section */}
      <View style={styles.section}>
        <Text style={styles.sectionHeader}>Text Command</Text>
        <TextInput
          style={styles.input}
          placeholder="Enter command (e.g., 'what's in my inbox?')"
          value={commandText}
          onChangeText={setCommandText}
          multiline
          editable={!loading}
        />

        <Button
          title={loading ? 'Sending...' : 'Send Command'}
          onPress={handleSendCommand}
          disabled={loading}
        />
      </View>

      {/* Audio Command Section */}
      <View style={styles.section}>
        <Text style={styles.sectionHeader}>Audio Command (Dev)</Text>
        
        {!isRecording && !audioUri && (
          <TouchableOpacity
            style={styles.recordButton}
            onPress={startRecording}
            disabled={loading}
          >
            <Text style={styles.recordButtonText}>🎤 Start Recording</Text>
          </TouchableOpacity>
        )}

        {isRecording && (
          <View style={styles.recordingContainer}>
            <Text style={styles.recordingText}>🔴 Recording...</Text>
            <Text style={styles.durationText}>{formatDuration(recordingDuration)}</Text>
            <TouchableOpacity
              style={styles.stopButton}
              onPress={stopRecording}
            >
              <Text style={styles.stopButtonText}>⏹ Stop</Text>
            </TouchableOpacity>
          </View>
        )}

        {audioUri && !isRecording && (
          <View style={styles.audioReadyContainer}>
            <Text style={styles.audioReadyText}>✓ Audio ready</Text>
            <Text style={styles.audioInfoText}>
              Duration: {formatDuration(recordingDuration)} • Size: {audioSize} KB
            </Text>
            <View style={styles.audioButtonsRow}>
              <TouchableOpacity
                style={styles.sendAudioButton}
                onPress={sendAudioAsCommand}
                disabled={loading}
              >
                <Text style={styles.sendAudioButtonText}>
                  {loading ? 'Sending...' : 'Send Audio'}
                </Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={styles.discardButton}
                onPress={() => {
                  setAudioUri(null);
                  setRecordingDuration(0);
                  setAudioSize(0);
                }}
                disabled={loading}
              >
                <Text style={styles.discardButtonText}>Discard</Text>
              </TouchableOpacity>
            </View>
          </View>
        )}
      </View>

      {loading && (
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#007AFF" />
        </View>
      )}

      {error && (
        <View style={styles.errorContainer}>
          <Text style={styles.errorTitle}>⚠️ Error</Text>
          <Text style={styles.errorText}>{error}</Text>
          {getErrorHint(error) && (
            <Text style={styles.errorHint}>{getErrorHint(error)}</Text>
          )}
        </View>
      )}

      {response && (
        <View style={styles.responseContainer}>
          <Text style={styles.sectionTitle}>Response:</Text>

          {showDebugPanel && response.status && (
            <View style={styles.spokenTextContainer}>
              <Text style={styles.label}>Status:</Text>
              <Text style={styles.value}>{response.status}</Text>
            </View>
          )}

          {showDebugPanel && response.intent && response.intent.name && (
            <View style={styles.spokenTextContainer}>
              <Text style={styles.label}>Intent:</Text>
              <Text style={styles.value}>{response.intent.name}</Text>
            </View>
          )}

          {response.spoken_text && (
            <View style={styles.spokenTextContainer}>
              <Text style={styles.label}>Spoken Text:</Text>
              <Text style={styles.value}>{response.spoken_text}</Text>
              {!autoPlayTts && (
                <TouchableOpacity
                  style={styles.manualTtsButton}
                  onPress={() => playTTS(response.spoken_text)}
                  disabled={ttsLoading || isTtsPlaying}
                >
                  <Text style={styles.manualTtsButtonText}>
                    {ttsLoading ? 'Loading...' : isTtsPlaying ? 'Playing...' : '🔊 Play TTS'}
                  </Text>
                </TouchableOpacity>
              )}
            </View>
          )}

          {response.pending_action && (
            <View style={styles.confirmationNotice}>
              <Text style={styles.confirmationText}>
                ⚠️ This action requires confirmation
              </Text>
              <Text style={styles.actionIdText}>
                Token: {response.pending_action.token}
              </Text>
              {response.pending_action.summary ? (
                <Text style={styles.actionIdText}>
                  Summary: {response.pending_action.summary}
                </Text>
              ) : null}
            </View>
          )}

          {renderUICards(response.cards)}

          {showDebugPanel && response.debug && (
            <View style={styles.debugContainer}>
              <Text style={styles.label}>Debug Info:</Text>
              <Text style={styles.debugText}>
                {JSON.stringify(response.debug, null, 2)}
              </Text>
            </View>
          )}
        </View>
      )}
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
  loadingContainer: {
    marginVertical: 20,
    alignItems: 'center',
  },
  errorContainer: {
    backgroundColor: '#ffebee',
    padding: 15,
    borderRadius: 5,
    marginTop: 15,
  },
  errorTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#c62828',
    marginBottom: 5,
  },
  errorText: {
    color: '#c62828',
    fontSize: 14,
  },
  errorHint: {
    color: '#d84315',
    fontSize: 13,
    marginTop: 8,
    fontStyle: 'italic',
  },
  responseContainer: {
    backgroundColor: 'white',
    padding: 15,
    borderRadius: 5,
    marginTop: 15,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 10,
  },
  spokenTextContainer: {
    marginBottom: 15,
  },
  label: {
    fontSize: 14,
    fontWeight: '600',
    marginBottom: 5,
    color: '#666',
  },
  value: {
    fontSize: 16,
    color: '#000',
  },
  confirmationNotice: {
    backgroundColor: '#fff3cd',
    padding: 10,
    borderRadius: 5,
    marginBottom: 15,
  },
  confirmationText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#856404',
  },
  actionIdText: {
    fontSize: 12,
    color: '#856404',
    marginTop: 5,
  },
  cardsContainer: {
    marginTop: 10,
  },
  card: {
    backgroundColor: '#f8f9fa',
    padding: 12,
    borderRadius: 5,
    marginBottom: 10,
    borderLeftWidth: 4,
    borderLeftColor: '#007AFF',
  },
  cardTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    marginBottom: 5,
  },
  cardSubtitle: {
    fontSize: 13,
    color: '#666',
    marginBottom: 5,
  },
  cardLine: {
    fontSize: 13,
    color: '#333',
    marginTop: 3,
  },
  cardLink: {
    fontSize: 12,
    color: '#007AFF',
    marginTop: 6,
  },
  debugContainer: {
    marginTop: 15,
    backgroundColor: '#f0f0f0',
    padding: 10,
    borderRadius: 5,
  },
  debugText: {
    fontSize: 12,
    fontFamily: 'monospace',
    color: '#333',
  },
  section: {
    marginBottom: 25,
    backgroundColor: 'white',
    padding: 15,
    borderRadius: 8,
  },
  sectionHeader: {
    fontSize: 18,
    fontWeight: '600',
    marginBottom: 12,
    color: '#333',
  },
  recordButton: {
    backgroundColor: '#007AFF',
    padding: 15,
    borderRadius: 8,
    alignItems: 'center',
  },
  recordButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: '600',
  },
  recordingContainer: {
    alignItems: 'center',
    padding: 20,
    backgroundColor: '#ffebee',
    borderRadius: 8,
  },
  recordingText: {
    fontSize: 18,
    fontWeight: '600',
    color: '#c62828',
    marginBottom: 10,
  },
  durationText: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 15,
  },
  stopButton: {
    backgroundColor: '#c62828',
    paddingHorizontal: 30,
    paddingVertical: 12,
    borderRadius: 8,
  },
  stopButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: '600',
  },
  audioReadyContainer: {
    padding: 15,
    backgroundColor: '#e8f5e9',
    borderRadius: 8,
  },
  audioReadyText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#2e7d32',
    marginBottom: 5,
  },
  audioInfoText: {
    fontSize: 13,
    color: '#555',
    marginBottom: 15,
  },
  audioButtonsRow: {
    flexDirection: 'row',
    gap: 10,
  },
  sendAudioButton: {
    flex: 1,
    backgroundColor: '#2e7d32',
    padding: 12,
    borderRadius: 8,
    alignItems: 'center',
  },
  sendAudioButtonText: {
    color: 'white',
    fontSize: 15,
    fontWeight: '600',
  },
  discardButton: {
    flex: 1,
    backgroundColor: '#666',
    padding: 12,
    borderRadius: 8,
    alignItems: 'center',
  },
  discardButtonText: {
    color: 'white',
    fontSize: 15,
    fontWeight: '600',
  },
  devSettingsSection: {
    backgroundColor: 'white',
    padding: 15,
    borderRadius: 8,
    marginBottom: 15,
  },
  settingRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 8,
  },
  settingLabel: {
    fontSize: 15,
    color: '#333',
  },
  ttsControlsSection: {
    backgroundColor: 'white',
    padding: 15,
    borderRadius: 8,
    marginBottom: 15,
  },
  ttsLoadingContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  ttsLoadingText: {
    fontSize: 14,
    color: '#666',
  },
  ttsPlayingContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  ttsPlayingText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#1976d2',
  },
  ttsStopButton: {
    backgroundColor: '#c62828',
    paddingHorizontal: 15,
    paddingVertical: 8,
    borderRadius: 6,
  },
  ttsStopButtonText: {
    color: 'white',
    fontSize: 14,
    fontWeight: '600',
  },
  manualTtsButton: {
    backgroundColor: '#1976d2',
    padding: 10,
    borderRadius: 6,
    alignItems: 'center',
    marginTop: 10,
  },
  manualTtsButtonText: {
    color: 'white',
    fontSize: 14,
    fontWeight: '600',
  },
});
