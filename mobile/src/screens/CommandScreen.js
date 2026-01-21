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
  Modal,
  Platform,
} from 'react-native';
import { Audio } from 'expo-av';
import * as FileSystem from 'expo-file-system';
import { sendCommand, uploadDevAudio, sendAudioCommand, fetchTTS, confirmCommand } from '../api/client';
import { inferConfirmationDecision } from '../utils/voiceConfirmation';
import { getProfile } from '../storage/profileStorage';

export default function CommandScreen() {
  const [commandText, setCommandText] = useState('');
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState(null);
  const [error, setError] = useState(null);
  
  // Profile state
  const [currentProfile, setCurrentProfile] = useState('default');
  
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

  // State for repeat/next functionality
  const [lastSpokenText, setLastSpokenText] = useState(null);

  // Confirmation modal state
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [pendingAction, setPendingAction] = useState(null);
  const [confirmLoading, setConfirmLoading] = useState(false);
  const [voiceConfirmLoading, setVoiceConfirmLoading] = useState(false);
  const [voiceConfirmTranscript, setVoiceConfirmTranscript] = useState(null);

  const RECORDING_OPTIONS_M4A = {
    android: {
      extension: '.m4a',
      outputFormat: Audio.RECORDING_OPTION_ANDROID_OUTPUT_FORMAT_MPEG_4,
      audioEncoder: Audio.RECORDING_OPTION_ANDROID_AUDIO_ENCODER_AAC,
      sampleRate: 44100,
      numberOfChannels: 1,
      bitRate: 128000,
    },
    ios: {
      extension: '.m4a',
      audioQuality: Audio.RECORDING_OPTION_IOS_AUDIO_QUALITY_MAX,
      outputFormat: Audio.RECORDING_OPTION_IOS_OUTPUT_FORMAT_MPEG4AAC,
      sampleRate: 44100,
      numberOfChannels: 1,
      bitRate: 128000,
      linearPCMBitDepth: 16,
      linearPCMIsBigEndian: false,
      linearPCMIsFloat: false,
    },
    web: {
      mimeType: 'audio/webm',
      bitsPerSecond: 128000,
    },
  };

  const inferAudioFormatFromUri = (uri) => {
    if (!uri) return 'm4a';
    const lower = String(uri).toLowerCase();

    // Handle common/expected extensions
    if (lower.endsWith('.wav')) return 'wav';
    if (lower.endsWith('.mp3')) return 'mp3';
    if (lower.endsWith('.opus')) return 'opus';
    if (lower.endsWith('.m4a')) return 'm4a';

    // iOS can sometimes produce .caf with defaults; backend doesn't accept 'caf'.
    if (lower.endsWith('.caf')) return 'm4a';

    // Fallback: try to parse last extension
    const match = lower.match(/\.([a-z0-9]+)(\?|#|$)/);
    if (match?.[1] === 'wav') return 'wav';
    if (match?.[1] === 'mp3') return 'mp3';
    if (match?.[1] === 'opus') return 'opus';
    if (match?.[1] === 'm4a') return 'm4a';

    return 'm4a';
  };

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

    // Load current profile
    (async () => {
      try {
        const profile = await getProfile();
        setCurrentProfile(profile);
      } catch (err) {
        console.error('Failed to load profile:', err);
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

      // Fetch TTS audio (default backend format is WAV)
      const audioBlob = await fetchTTS(text, { format: 'wav', accept: 'audio/wav' });

      // Convert blob to base64
      const reader = new FileReader();
      reader.readAsDataURL(audioBlob);
      reader.onloadend = async () => {
        const base64Audio = reader.result;

        // Write to temporary file for better compatibility
        const tempUri = `${FileSystem.cacheDirectory}tts_${Date.now()}.wav`;
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
            FileSystem.deleteAsync(tempUri, { idempotent: true }).catch(() => {});
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
      const data = await sendCommand(commandText, { profile: currentProfile });
      setResponse(data);
      
      // Store for repeat functionality
      if (data.spoken_text) {
        setLastSpokenText(data.spoken_text);
      }
      
      // Check if confirmation is required
      if (data.pending_action) {
        console.log('[CommandScreen] Pending action detected:', {
          token: data.pending_action.token,
          summary: data.pending_action.summary,
          expires_at: data.pending_action.expires_at,
        });
        setPendingAction(data.pending_action);
        setShowConfirmModal(true);
        
        // Auto-play confirmation prompt if TTS is enabled
        if (autoPlayTts && data.spoken_text) {
          await playTTS(data.spoken_text);
        }
      } else {
        // Auto-play TTS if enabled and spoken_text is available
        if (autoPlayTts && data.spoken_text) {
          await playTTS(data.spoken_text);
        }
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
        RECORDING_OPTIONS_M4A
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
      const uploadFormat = inferAudioFormatFromUri(audioUri);

      // Read audio file as base64
      const audioBase64 = await FileSystem.readAsStringAsync(audioUri, {
        encoding: FileSystem.EncodingType.Base64,
      });

      // Upload to dev endpoint
      const { uri: fileUri, format } = await uploadDevAudio(audioBase64, uploadFormat);

      // Send as audio command with duration in ms and current profile
      const data = await sendAudioCommand(fileUri, format, {
        duration_ms: recordingDuration * 1000,
        profile: currentProfile,
      });
      setResponse(data);
      
      // Store for repeat functionality
      if (data.spoken_text) {
        setLastSpokenText(data.spoken_text);
      }
      
      // Check if confirmation is required
      if (data.pending_action) {
        console.log('[CommandScreen] Pending action detected (audio):', {
          token: data.pending_action.token,
          summary: data.pending_action.summary,
          expires_at: data.pending_action.expires_at,
        });
        setPendingAction(data.pending_action);
        setShowConfirmModal(true);
        
        // Auto-play confirmation prompt if TTS is enabled
        if (autoPlayTts && data.spoken_text) {
          await playTTS(data.spoken_text);
        }
      } else {
        // Auto-play TTS if enabled and spoken_text is available
        if (autoPlayTts && data.spoken_text) {
          await playTTS(data.spoken_text);
        }
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

  const confirmPendingAction = async ({ source = 'tap' } = {}) => {
    if (!pendingAction?.token) return;

    console.log('[CommandScreen] Confirming action with token:', pendingAction.token, 'source:', source);
    setConfirmLoading(true);

    try {
      const confirmResponse = await confirmCommand(pendingAction.token);
      console.log('[CommandScreen] Confirmation successful:', confirmResponse);

      // Update response with confirmation result
      setResponse(confirmResponse);
      setShowConfirmModal(false);
      setPendingAction(null);
      setVoiceConfirmTranscript(null);

      // Auto-play TTS if enabled
      if (autoPlayTts && confirmResponse.spoken_text) {
        await playTTS(confirmResponse.spoken_text);
      }

      if (source === 'tap') {
        Alert.alert('Success', 'Action confirmed successfully');
      }
    } catch (err) {
      console.error('[CommandScreen] Confirmation failed:', err);
      Alert.alert('Error', `Confirmation failed: ${err.message}`);
    } finally {
      setConfirmLoading(false);
    }
  };

  const handleConfirmAction = async () => {
    await confirmPendingAction({ source: 'tap' });
  };

  const handleCancelAction = ({ silent = false } = {}) => {
    console.log('[CommandScreen] User cancelled confirmation');
    setShowConfirmModal(false);
    setPendingAction(null);
    setVoiceConfirmTranscript(null);
    if (!silent) {
      Alert.alert('Cancelled', 'Action was not confirmed');
    }
  };

  const inferConfirmationDecision = (transcript) => {
    if (!transcript) return null;

    const t = transcript.toLowerCase().trim();
    // Prefer explicit cancel if present
    const cancelKeywords = ['cancel', 'stop', 'no', 'never mind', 'nevermind', 'abort', 'dont', "don't"];
    const confirmKeywords = ['confirm', 'yes', 'do it', 'proceed', 'ok', 'okay', 'approve'];

    if (cancelKeywords.some((k) => t.includes(k))) return 'cancel';
    if (confirmKeywords.some((k) => t.includes(k))) return 'confirm';
    return null;
  };

  const handleRepeat = async () => {
    if (!lastSpokenText) {
      Alert.alert('No Response', 'No previous response to repeat');
      return;
    }

    setLoading(true);
    setError(null);
    
    // Replay the stored TTS locally
    await playTTS(lastSpokenText);
    setLoading(false);
  };

  const handleNext = async () => {
    setLoading(true);
    setError(null);
    setResponse(null);

    try {
      // Send canonical "next" command to server
      const data = await sendCommand('next');
      setResponse(data);
      
      // Store for repeat functionality
      if (data.spoken_text) {
        setLastSpokenText(data.spoken_text);
      }
      
      // Check if confirmation is required
      if (data.pending_action) {
        console.log('[CommandScreen] Pending action detected (next):', {
          token: data.pending_action.token,
          summary: data.pending_action.summary,
          expires_at: data.pending_action.expires_at,
        });
        setPendingAction(data.pending_action);
        setShowConfirmModal(true);
        
        // Auto-play confirmation prompt if TTS is enabled
        if (autoPlayTts && data.spoken_text) {
          await playTTS(data.spoken_text);
        }
      } else {
        // Auto-play TTS if enabled and spoken_text is available
        if (autoPlayTts && data.spoken_text) {
          await playTTS(data.spoken_text);
        }
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleVoiceConfirm = async () => {
    if (!pendingAction?.token) return;

    setVoiceConfirmLoading(true);
    setVoiceConfirmTranscript(null);
    try {
      const { status } = await Audio.requestPermissionsAsync();
      if (status !== 'granted') {
        Alert.alert('Permission Required', 'Microphone permission is required for voice confirmation.');
        return;
      }

      // Record a short clip (kept short to reduce latency)
      await Audio.setAudioModeAsync({
        allowsRecordingIOS: true,
        playsInSilentModeIOS: true,
      });

      const { recording: voiceRecording } = await Audio.Recording.createAsync(RECORDING_OPTIONS_M4A);

      const clipDurationMs = 1400;
      await new Promise((resolve) => setTimeout(resolve, clipDurationMs));
      await voiceRecording.stopAndUnloadAsync();
      const voiceUri = voiceRecording.getURI();

      if (!voiceUri) {
        throw new Error('No recording URI returned');
      }

      const uploadFormat = inferAudioFormatFromUri(voiceUri);

      // Upload the clip and run it through /v1/command with debug transcript enabled
      const audioBase64 = await FileSystem.readAsStringAsync(voiceUri, {
        encoding: FileSystem.EncodingType.Base64,
      });

      const { uri: fileUri, format } = await uploadDevAudio(audioBase64, uploadFormat);

      const sttResult = await sendAudioCommand(fileUri, format, {
        duration_ms: clipDurationMs,
        profile: 'workout',
        client_context: {
          debug: true,
          // Avoid redaction in transcript during dev testing
          privacy_mode: 'off',
        },
      });

      const transcript = (sttResult?.debug?.transcript || '').trim();
      setVoiceConfirmTranscript(transcript || '(no transcript)');

      const decision = inferConfirmationDecision(transcript);
      if (decision === 'confirm') {
        await confirmPendingAction({ source: 'voice' });
        return;
      }

      if (decision === 'cancel') {
        handleCancelAction({ silent: true });
        return;
      }

      Alert.alert(
        'Voice Confirmation',
        `I heard: "${transcript || '...'}"\n\nSay "confirm" or "cancel", or use the buttons.`,
        [{ text: 'OK' }]
      );
    } catch (err) {
      console.error('[CommandScreen] Voice confirmation failed:', err);
      Alert.alert('Voice Confirmation Failed', err.message);
    } finally {
      setVoiceConfirmLoading(false);
    }
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
      {/* Confirmation Modal */}
      <Modal
        visible={showConfirmModal}
        transparent={true}
        animationType="fade"
        onRequestClose={handleCancelAction}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContainer}>
            <Text style={styles.modalTitle}>⚠️ Confirmation Required</Text>
            
            {pendingAction?.summary && (
              <Text style={styles.modalSummary}>{pendingAction.summary}</Text>
            )}
            
            {showDebugPanel && pendingAction?.token && (
              <View style={styles.modalDebug}>
                <Text style={styles.modalDebugLabel}>Token:</Text>
                <Text style={styles.modalDebugText}>{pendingAction.token}</Text>
              </View>
            )}
            
            {showDebugPanel && pendingAction?.expires_at && (
              <View style={styles.modalDebug}>
                <Text style={styles.modalDebugLabel}>Expires:</Text>
                <Text style={styles.modalDebugText}>
                  {new Date(pendingAction.expires_at).toLocaleString()}
                </Text>
              </View>
            )}
            
            <Text style={styles.modalPrompt}>
              Do you want to proceed with this action?
            </Text>
            
            {confirmLoading ? (
              <ActivityIndicator size="large" color="#007AFF" style={styles.modalLoading} />
            ) : (
              <View style={styles.modalButtons}>
                <TouchableOpacity
                  style={[styles.modalButton, styles.confirmButton]}
                  onPress={handleConfirmAction}
                >
                  <Text style={styles.confirmButtonText}>✓ Confirm</Text>
                </TouchableOpacity>
                
                <TouchableOpacity
                  style={[styles.modalButton, styles.cancelButton]}
                  onPress={() => handleCancelAction()}
                >
                  <Text style={styles.cancelButtonText}>✗ Cancel</Text>
                </TouchableOpacity>
              </View>
            )}

            <View style={styles.modalVoiceSection}>
              {voiceConfirmLoading ? (
                <View style={styles.modalVoiceLoading}>
                  <ActivityIndicator size="small" color="#007AFF" />
                  <Text style={styles.modalVoiceText}>Listening…</Text>
                </View>
              ) : (
                <TouchableOpacity
                  style={[styles.modalButton, styles.voiceButton]}
                  onPress={handleVoiceConfirm}
                >
                  <Text style={styles.voiceButtonText}>🎙 Voice: say “confirm” or “cancel”</Text>
                </TouchableOpacity>
              )}

              {showDebugPanel && voiceConfirmTranscript ? (
                <Text style={styles.modalVoiceTranscript}>Heard: {voiceConfirmTranscript}</Text>
              ) : null}
            </View>
          </View>
        </View>
      </Modal>

      <Text style={styles.title}>Send Command</Text>

      {/* Profile Indicator */}
      <View style={styles.profileIndicator}>
        <Text style={styles.profileLabel}>Current Profile:</Text>
        <Text style={styles.profileValue}>{currentProfile}</Text>
      </View>

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

      {/* Repeat/Next Quick Controls */}
      <View style={styles.quickControlsSection}>
        <Text style={styles.quickControlsHeader}>Quick Controls</Text>
        <Text style={styles.quickControlsHelper}>
          Use these buttons to navigate through responses:
        </Text>
        <View style={styles.quickControlsRow}>
          <TouchableOpacity
            style={[styles.quickControlButton, (loading || !lastSpokenText) && styles.quickControlButtonDisabled]}
            onPress={handleRepeat}
            disabled={loading || !lastSpokenText}
            accessibilityLabel="Repeat last response"
            accessibilityHint="Replays the text-to-speech audio from the most recent command response"
            accessibilityState={{ disabled: loading || !lastSpokenText }}
          >
            <Text style={styles.quickControlButtonText}>🔄 Repeat</Text>
            <Text style={styles.quickControlButtonSubtext}>Replay last TTS response</Text>
          </TouchableOpacity>
          
          <TouchableOpacity
            style={[styles.quickControlButton, loading && styles.quickControlButtonDisabled]}
            onPress={handleNext}
            disabled={loading}
            accessibilityLabel="Next item"
            accessibilityHint="Advances to the next item in the current inbox or summary sequence"
            accessibilityState={{ disabled: loading }}
          >
            <Text style={styles.quickControlButtonText}>⏭ Next</Text>
            <Text style={styles.quickControlButtonSubtext}>Advance to next item</Text>
          </TouchableOpacity>
        </View>
      </View>

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
  profileIndicator: {
    backgroundColor: '#e3f2fd',
    padding: 12,
    borderRadius: 8,
    marginBottom: 15,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
  },
  profileLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#1976d2',
    marginRight: 8,
  },
  profileValue: {
    fontSize: 14,
    fontWeight: 'bold',
    color: '#1565c0',
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
    justifyContent: 'space-between',
  },
  sendAudioButton: {
    flex: 1,
    backgroundColor: '#2e7d32',
    padding: 12,
    borderRadius: 8,
    alignItems: 'center',
    marginRight: 5,
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
    marginLeft: 5,
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
  },
  ttsLoadingText: {
    fontSize: 14,
    color: '#666',
    marginLeft: 10,
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
  // Confirmation Modal styles
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  modalContainer: {
    backgroundColor: 'white',
    borderRadius: 12,
    padding: 20,
    width: '100%',
    maxWidth: 400,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 4,
    elevation: 5,
  },
  modalTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#ff6b00',
    marginBottom: 15,
    textAlign: 'center',
  },
  modalSummary: {
    fontSize: 16,
    color: '#333',
    marginBottom: 15,
    textAlign: 'center',
    lineHeight: 22,
  },
  modalPrompt: {
    fontSize: 15,
    color: '#666',
    marginBottom: 20,
    textAlign: 'center',
  },
  modalDebug: {
    backgroundColor: '#f5f5f5',
    padding: 10,
    borderRadius: 5,
    marginBottom: 10,
  },
  modalDebugLabel: {
    fontSize: 12,
    fontWeight: '600',
    color: '#666',
    marginBottom: 3,
  },
  modalDebugText: {
    fontSize: 11,
    fontFamily: 'monospace',
    color: '#333',
  },
  modalLoading: {
    marginVertical: 20,
  },
  modalButtons: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  modalButton: {
    flex: 1,
    padding: 16,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
  },
  confirmButton: {
    backgroundColor: '#28a745',
    marginRight: 5,
  },
  confirmButtonText: {
    color: 'white',
    fontSize: 18,
    fontWeight: 'bold',
  },
  cancelButton: {
    backgroundColor: '#dc3545',
    marginLeft: 5,
  },
  cancelButtonText: {
    color: 'white',
    fontSize: 18,
    fontWeight: 'bold',
  },
  modalVoiceSection: {
    marginTop: 12,
  },
  modalVoiceLoading: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 10,
  },
  modalVoiceText: {
    marginLeft: 8,
    fontSize: 14,
    color: '#007AFF',
    fontWeight: '600',
  },
  voiceButton: {
    backgroundColor: '#f0f7ff',
    borderWidth: 1,
    borderColor: '#cfe6ff',
    marginTop: 8,
  },
  voiceButtonText: {
    color: '#007AFF',
    fontSize: 14,
    fontWeight: '700',
  },
  modalVoiceTranscript: {
    marginTop: 8,
    fontSize: 12,
    color: '#555',
    fontStyle: 'italic',
    textAlign: 'center',
  },
  // Quick Controls styles
  quickControlsSection: {
    backgroundColor: 'white',
    padding: 15,
    borderRadius: 8,
    marginBottom: 15,
  },
  quickControlsHeader: {
    fontSize: 18,
    fontWeight: '600',
    color: '#333',
    marginBottom: 5,
  },
  quickControlsHelper: {
    fontSize: 13,
    color: '#666',
    marginBottom: 12,
  },
  quickControlsRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  quickControlButton: {
    flex: 1,
    backgroundColor: '#007AFF',
    padding: 15,
    borderRadius: 8,
    alignItems: 'center',
    marginHorizontal: 5,
  },
  quickControlButtonDisabled: {
    backgroundColor: '#cccccc',
  },
  quickControlButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 4,
  },
  quickControlButtonSubtext: {
    color: 'white',
    fontSize: 11,
    opacity: 0.9,
  },
});
