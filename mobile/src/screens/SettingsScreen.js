import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  TextInput,
  Button,
  StyleSheet,
  ScrollView,
  Alert,
  Switch,
} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { DEFAULT_BASE_URL, getSpeakNotifications, setSpeakNotifications } from '../api/config';

const STORAGE_KEYS = {
  USER_ID: '@handsfree_user_id',
  BASE_URL: '@handsfree_base_url',
  USE_CUSTOM_URL: '@handsfree_use_custom_url',
};

export default function SettingsScreen() {
  const [userId, setUserId] = useState('');
  const [baseUrl, setBaseUrl] = useState(DEFAULT_BASE_URL);
  const [useCustomUrl, setUseCustomUrl] = useState(false);
  const [speakNotifications, setSpeakNotificationsState] = useState(__DEV__);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      const savedUserId = await AsyncStorage.getItem(STORAGE_KEYS.USER_ID);
      const savedBaseUrl = await AsyncStorage.getItem(STORAGE_KEYS.BASE_URL);
      const savedUseCustomUrl = await AsyncStorage.getItem(STORAGE_KEYS.USE_CUSTOM_URL);
      const savedSpeakNotifications = await getSpeakNotifications();

      if (savedUserId) setUserId(savedUserId);
      if (savedBaseUrl) setBaseUrl(savedBaseUrl);
      if (savedUseCustomUrl) setUseCustomUrl(savedUseCustomUrl === 'true');
      setSpeakNotificationsState(savedSpeakNotifications);
    } catch (error) {
      console.error('Failed to load settings:', error);
    } finally {
      setLoading(false);
    }
  };

  const saveSettings = async () => {
    try {
      await AsyncStorage.setItem(STORAGE_KEYS.USER_ID, userId);
      await AsyncStorage.setItem(STORAGE_KEYS.BASE_URL, baseUrl);
      await AsyncStorage.setItem(STORAGE_KEYS.USE_CUSTOM_URL, useCustomUrl.toString());
      await setSpeakNotifications(speakNotifications);

      Alert.alert(
        'Success',
        'Settings saved! Please restart the app for changes to take full effect.',
        [{ text: 'OK' }]
      );
    } catch (error) {
      Alert.alert('Error', `Failed to save settings: ${error.message}`);
    }
  };

  const resetToDefaults = () => {
    Alert.alert(
      'Reset Settings',
      'Are you sure you want to reset to default values?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Reset',
          style: 'destructive',
          onPress: async () => {
            setUserId('');
            setBaseUrl(DEFAULT_BASE_URL);
            setUseCustomUrl(false);
            setSpeakNotificationsState(__DEV__);
            try {
              await AsyncStorage.multiRemove([
                STORAGE_KEYS.USER_ID,
                STORAGE_KEYS.BASE_URL,
                STORAGE_KEYS.USE_CUSTOM_URL,
              ]);
              await setSpeakNotifications(__DEV__);
              Alert.alert('Success', 'Settings reset to defaults');
            } catch (error) {
              Alert.alert('Error', `Failed to reset settings: ${error.message}`);
            }
          },
        },
      ]
    );
  };

  const generateUserId = () => {
    // Generate a simple UUID v4
    const uuid = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
      const r = (Math.random() * 16) | 0;
      const v = c === 'x' ? r : (r & 0x3) | 0x8;
      return v.toString(16);
    });
    setUserId(uuid);
  };

  if (loading) {
    return (
      <View style={styles.container}>
        <Text>Loading settings...</Text>
      </View>
    );
  }

  return (
    <ScrollView style={styles.container}>
      <Text style={styles.title}>Developer Settings</Text>

      <Text style={styles.description}>
        Configure the X-User-ID header and backend URL for testing.
      </Text>

      {/* User ID Configuration */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>User ID</Text>
        <Text style={styles.helpText}>
          Sets the X-User-ID header for API requests. Leave empty to omit the header.
        </Text>

        <TextInput
          style={styles.input}
          placeholder="e.g., 00000000-0000-0000-0000-000000000001"
          value={userId}
          onChangeText={setUserId}
          autoCapitalize="none"
          autoCorrect={false}
        />

        <View style={styles.buttonContainer}>
          <Button
            title="Generate UUID"
            onPress={generateUserId}
            color="#28a745"
          />
        </View>
      </View>

      {/* Backend URL Configuration */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Backend URL</Text>

        <View style={styles.switchContainer}>
          <Text style={styles.switchLabel}>Use custom URL</Text>
          <Switch
            value={useCustomUrl}
            onValueChange={setUseCustomUrl}
            trackColor={{ false: '#767577', true: '#81b0ff' }}
            thumbColor={useCustomUrl ? '#007AFF' : '#f4f3f4'}
          />
        </View>

        {useCustomUrl && (
          <>
            <Text style={styles.helpText}>
              Custom backend URL. Default: {DEFAULT_BASE_URL}
            </Text>
            <TextInput
              style={styles.input}
              placeholder={DEFAULT_BASE_URL}
              value={baseUrl}
              onChangeText={setBaseUrl}
              autoCapitalize="none"
              autoCorrect={false}
              keyboardType="url"
            />
          </>
        )}

        {!useCustomUrl && (
          <Text style={styles.helpText}>
            Currently using default URL: {DEFAULT_BASE_URL}
          </Text>
        )}
      </View>

      {/* Notification Settings */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Notifications</Text>

        <View style={styles.switchContainer}>
          <Text style={styles.switchLabel}>Speak notifications</Text>
          <Switch
            value={speakNotifications}
            onValueChange={setSpeakNotificationsState}
            trackColor={{ false: '#767577', true: '#81b0ff' }}
            thumbColor={speakNotifications ? '#007AFF' : '#f4f3f4'}
          />
        </View>

        <Text style={styles.helpText}>
          When enabled, incoming push notifications will be automatically spoken via TTS. 
          {__DEV__ ? ' (Default: ON in development)' : ' (Default: OFF in production)'}
        </Text>
      </View>

      {/* Action Buttons */}
      <View style={styles.section}>
        <View style={styles.buttonContainer}>
          <Button title="Save Settings" onPress={saveSettings} />
        </View>

        <View style={styles.buttonContainer}>
          <Button
            title="Reset to Defaults"
            onPress={resetToDefaults}
            color="#dc3545"
          />
        </View>
      </View>

      {/* Info Section */}
      <View style={styles.infoContainer}>
        <Text style={styles.infoTitle}>ℹ️ Note:</Text>
        <Text style={styles.infoText}>
          Changes to these settings will take effect on the next API request. For BASE_URL
          changes, you may need to restart the app.
        </Text>
      </View>

      {/* Current Values Display */}
      <View style={styles.debugSection}>
        <Text style={styles.debugTitle}>Current Configuration:</Text>
        <Text style={styles.debugText}>User ID: {userId || '(not set)'}</Text>
        <Text style={styles.debugText}>
          Base URL: {useCustomUrl ? baseUrl : `${DEFAULT_BASE_URL} (default)`}
        </Text>
        <Text style={styles.debugText}>
          X-User-ID header: {userId ? 'Will be sent' : 'Will not be sent'}
        </Text>
        <Text style={styles.debugText}>
          Speak notifications: {speakNotifications ? 'Enabled' : 'Disabled'}
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
  description: {
    fontSize: 14,
    color: '#666',
    marginBottom: 20,
  },
  section: {
    backgroundColor: 'white',
    padding: 15,
    borderRadius: 5,
    marginBottom: 15,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    marginBottom: 10,
  },
  helpText: {
    fontSize: 13,
    color: '#666',
    marginBottom: 10,
  },
  input: {
    backgroundColor: '#f8f9fa',
    padding: 12,
    borderRadius: 5,
    fontSize: 14,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: '#e0e0e0',
  },
  buttonContainer: {
    marginTop: 10,
  },
  switchContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 15,
  },
  switchLabel: {
    fontSize: 16,
    color: '#333',
  },
  infoContainer: {
    backgroundColor: '#e3f2fd',
    padding: 15,
    borderRadius: 5,
    marginBottom: 15,
  },
  infoTitle: {
    fontSize: 14,
    fontWeight: '600',
    marginBottom: 5,
    color: '#1976d2',
  },
  infoText: {
    fontSize: 13,
    color: '#1976d2',
  },
  debugSection: {
    backgroundColor: '#f0f0f0',
    padding: 15,
    borderRadius: 5,
    marginBottom: 20,
  },
  debugTitle: {
    fontSize: 14,
    fontWeight: '600',
    marginBottom: 10,
  },
  debugText: {
    fontSize: 12,
    fontFamily: 'monospace',
    color: '#333',
    marginBottom: 5,
  },
});
