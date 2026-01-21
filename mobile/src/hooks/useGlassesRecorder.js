import { useState, useCallback } from 'react';
import { Alert } from 'react-native';
import ExpoGlassesAudio from 'expo-glasses-audio';
import { useAudioSource, AUDIO_SOURCES } from './useAudioSource';

let ExpoGlassesAudio = null;

try {
  ExpoGlassesAudio = require('expo-glasses-audio').default;
} catch (error) {
  // Module missing in Expo Go / non-dev-client builds.
}

function getExpoGlassesAudioOrThrow() {
  if (!ExpoGlassesAudio) {
    throw new Error(
      'Native expo-glasses-audio module not available. This feature requires a development build (expo-dev-client).'
    );
  }
  return ExpoGlassesAudio;
}

/**
 * Hook to record audio using the expo-glasses-audio module
 * with audio source preference from useAudioSource
 */
export function useGlassesRecorder() {
  const { audioSource } = useAudioSource();
  const [isRecording, setIsRecording] = useState(false);
  const [recordingUri, setRecordingUri] = useState(null);

  const startRecording = useCallback(async (durationSeconds = 5) => {
    try {
      const module = getExpoGlassesAudioOrThrow();
      setIsRecording(true);
      setRecordingUri(null);

      // Map audio source to the format expected by native module
      let nativeAudioSource = audioSource;
      
      // If glasses/Bluetooth is selected, check if it's available
      if (audioSource === AUDIO_SOURCES.GLASSES) {
        const routeInfo = await module.getAudioRoute();
        if (!routeInfo.isBluetoothConnected) {
          Alert.alert(
            'Bluetooth Not Available',
            'Glasses/Bluetooth mic is not connected. Falling back to phone microphone.',
            [{ text: 'OK' }]
          );
          nativeAudioSource = AUDIO_SOURCES.PHONE;
        }
      }

      const result = await module.startRecording(durationSeconds, nativeAudioSource);
      
      setRecordingUri(result.uri);
      setIsRecording(false);
      
      return result;
    } catch (error) {
      setIsRecording(false);
      console.error('Recording failed:', error);
      throw error;
    }
  }, [audioSource]);

  const stopRecording = useCallback(async () => {
    try {
      const module = getExpoGlassesAudioOrThrow();
      const result = await module.stopRecording();
      setIsRecording(false);
      if (result.uri) {
        setRecordingUri(result.uri);
      }
      return result;
    } catch (error) {
      setIsRecording(false);
      console.error('Stop recording failed:', error);
      throw error;
    }
  }, []);

  return {
    isRecording,
    recordingUri,
    startRecording,
    stopRecording,
    audioSource,
  };
}
