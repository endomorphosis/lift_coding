import { useState, useEffect } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';

const AUDIO_SOURCE_KEY = '@audio_source_preference';

export const AUDIO_SOURCES = {
  PHONE: 'phone',
  GLASSES: 'glasses',
  AUTO: 'auto',
};

export const AUDIO_SOURCE_LABELS = {
  [AUDIO_SOURCES.PHONE]: 'Phone Mic',
  [AUDIO_SOURCES.GLASSES]: 'Glasses/Bluetooth Mic',
  [AUDIO_SOURCES.AUTO]: 'Auto',
};

/**
 * Hook to manage audio source selection and persistence
 * @returns {Object} { audioSource, setAudioSource, isLoading }
 */
export function useAudioSource() {
  const [audioSource, setAudioSourceState] = useState(AUDIO_SOURCES.PHONE); // Default to phone for reliability
  const [isLoading, setIsLoading] = useState(true);

  // Load saved preference on mount
  useEffect(() => {
    (async () => {
      try {
        const saved = await AsyncStorage.getItem(AUDIO_SOURCE_KEY);
        if (saved && Object.values(AUDIO_SOURCES).includes(saved)) {
          setAudioSourceState(saved);
        }
      } catch (error) {
        console.error('Failed to load audio source preference:', error);
      } finally {
        setIsLoading(false);
      }
    })();
  }, []);

  // Save preference whenever it changes
  const setAudioSource = async (source) => {
    if (!Object.values(AUDIO_SOURCES).includes(source)) {
      console.error('Invalid audio source:', source);
      return;
    }

    try {
      await AsyncStorage.setItem(AUDIO_SOURCE_KEY, source);
      setAudioSourceState(source);
    } catch (error) {
      console.error('Failed to save audio source preference:', error);
      throw error;
    }
  };

  return {
    audioSource,
    setAudioSource,
    isLoading,
  };
}
