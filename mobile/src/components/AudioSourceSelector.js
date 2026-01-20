import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { AUDIO_SOURCES, AUDIO_SOURCE_LABELS } from '../hooks/useAudioSource';

/**
 * Audio source selector component
 * Allows user to choose between Phone Mic, Glasses/Bluetooth Mic, or Auto
 */
export default function AudioSourceSelector({ audioSource, onSelect, disabled = false }) {
  const options = [
    {
      value: AUDIO_SOURCES.PHONE,
      label: AUDIO_SOURCE_LABELS[AUDIO_SOURCES.PHONE],
      description: 'Use phone microphone (recommended for reliability)',
      icon: '📱',
    },
    {
      value: AUDIO_SOURCES.GLASSES,
      label: AUDIO_SOURCE_LABELS[AUDIO_SOURCES.GLASSES],
      description: 'Use Bluetooth/glasses microphone',
      icon: '👓',
    },
    {
      value: AUDIO_SOURCES.AUTO,
      label: AUDIO_SOURCE_LABELS[AUDIO_SOURCES.AUTO],
      description: 'Automatically select based on availability',
      icon: '🔄',
    },
  ];

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Audio Source</Text>
      <Text style={styles.subtitle}>Choose which microphone to use for recording</Text>
      
      {options.map((option) => (
        <TouchableOpacity
          key={option.value}
          style={[
            styles.optionButton,
            audioSource === option.value && styles.optionButtonSelected,
            disabled && styles.optionButtonDisabled,
          ]}
          onPress={() => !disabled && onSelect(option.value)}
          disabled={disabled}
        >
          <View style={styles.optionContent}>
            <Text style={styles.optionIcon}>{option.icon}</Text>
            <View style={styles.optionTextContainer}>
              <Text style={[
                styles.optionLabel,
                audioSource === option.value && styles.optionLabelSelected,
              ]}>
                {option.label}
              </Text>
              <Text style={[
                styles.optionDescription,
                audioSource === option.value && styles.optionDescriptionSelected,
              ]}>
                {option.description}
              </Text>
            </View>
            {audioSource === option.value && (
              <Text style={styles.checkmark}>✓</Text>
            )}
          </View>
        </TouchableOpacity>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
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
  title: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 4,
    color: '#000',
  },
  subtitle: {
    fontSize: 12,
    color: '#666',
    marginBottom: 12,
  },
  optionButton: {
    borderWidth: 2,
    borderColor: '#e0e0e0',
    borderRadius: 8,
    padding: 12,
    marginBottom: 8,
    backgroundColor: '#fff',
  },
  optionButtonSelected: {
    borderColor: '#007AFF',
    backgroundColor: '#f0f8ff',
  },
  optionButtonDisabled: {
    opacity: 0.5,
  },
  optionContent: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  optionIcon: {
    fontSize: 24,
    marginRight: 12,
  },
  optionTextContainer: {
    flex: 1,
  },
  optionLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#000',
    marginBottom: 2,
  },
  optionLabelSelected: {
    color: '#007AFF',
  },
  optionDescription: {
    fontSize: 12,
    color: '#666',
    lineHeight: 16,
  },
  optionDescriptionSelected: {
    color: '#0066cc',
  },
  checkmark: {
    fontSize: 20,
    color: '#007AFF',
    fontWeight: 'bold',
    marginLeft: 8,
  },
});
