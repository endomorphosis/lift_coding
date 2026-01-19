import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { PROFILES } from '../storage/profileStorage';

/**
 * ProfileSelector Component
 * 
 * A simple button-based profile selector for choosing between
 * default, workout, commute, and kitchen profiles.
 */
export default function ProfileSelector({ currentProfile, onProfileChange }) {
  return (
    <View style={styles.container}>
      <Text style={styles.label}>Profile:</Text>
      <View style={styles.buttonRow}>
        {PROFILES.map((profile) => (
          <TouchableOpacity
            key={profile}
            style={[
              styles.profileButton,
              currentProfile === profile && styles.profileButtonActive,
            ]}
            onPress={() => onProfileChange(profile)}
          >
            <Text
              style={[
                styles.profileButtonText,
                currentProfile === profile && styles.profileButtonTextActive,
              ]}
            >
              {profile.charAt(0).toUpperCase() + profile.slice(1)}
            </Text>
          </TouchableOpacity>
        ))}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    marginBottom: 15,
  },
  label: {
    fontSize: 14,
    fontWeight: '600',
    marginBottom: 8,
    color: '#333',
  },
  buttonRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  profileButton: {
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 20,
    backgroundColor: '#f0f0f0',
    borderWidth: 1,
    borderColor: '#ddd',
  },
  profileButtonActive: {
    backgroundColor: '#007AFF',
    borderColor: '#007AFF',
  },
  profileButtonText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#666',
  },
  profileButtonTextActive: {
    color: 'white',
  },
});
