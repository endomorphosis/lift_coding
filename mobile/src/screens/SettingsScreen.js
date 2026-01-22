import React, { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  Button,
  ScrollView,
  StyleSheet,
  Switch,
  Text,
  TextInput,
  View,
} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as WebBrowser from 'expo-web-browser';
import { completeGitHubOAuth, startGitHubOAuth } from '../api/client';
import {
  DEFAULT_BASE_URL,
  STORAGE_KEYS,
  getSpeakNotifications,
  setSpeakNotifications,
} from '../api/config';
import { dispatchViaPhone, getPhoneDispatcherUrl, setPhoneDispatcherUrl } from '../api/phoneDispatcher';
import { registerForPushAsync, registerSubscriptionWithBackend, unregisterSubscriptionWithBackend, listSubscriptions } from '../push/pushClient';
import { getAutoSpeakEnabled, setAutoSpeakEnabled } from '../utils/notificationSettings';
import { clearGlassesAudioCache, getSimulateGlassesAudio, setSimulateGlassesAudio } from '../native/glassesAudio';

export default function SettingsScreen() {
  const [loading, setLoading] = useState(true);

  const [userId, setUserId] = useState('');
  const [baseUrl, setBaseUrl] = useState(DEFAULT_BASE_URL);
  const [useCustomUrl, setUseCustomUrl] = useState(false);

  const [speakNotifications, setSpeakNotificationsState] = useState(__DEV__);
  const [autoSpeakNotifications, setAutoSpeakNotifications] = useState(false);

  // Push notification state
  const [pushToken, setPushToken] = useState(null);
  const [subscriptions, setSubscriptions] = useState([]);
  const [pushLoading, setPushLoading] = useState(false);

  // GitHub OAuth state
  const [githubConnectionId, setGithubConnectionId] = useState(null);
  const [connectingGithub, setConnectingGithub] = useState(false);

  // Dev tooling state
  const [simulateGlassesAudio, setSimulateGlassesAudioState] = useState(false);
  const [phoneDispatcherUrl, setPhoneDispatcherUrlState] = useState('');
  const [dispatchTesting, setDispatchTesting] = useState(false);

  const loadPushStatus = useCallback(async () => {
    try {
      const subs = await listSubscriptions();
      setSubscriptions(subs);
    } catch (error) {
      console.error('Failed to load subscriptions:', error);
    }
  }, []);

  const handleOAuthCallback = useCallback(async (code, state) => {
    try {
      setConnectingGithub(true);
      const response = await completeGitHubOAuth(code, state);
      if (response.connection_id) {
        await AsyncStorage.setItem(STORAGE_KEYS.GITHUB_CONNECTION_ID, response.connection_id);
        setGithubConnectionId(response.connection_id);
        Alert.alert('Success', `GitHub connected successfully!\nScopes: ${response.scopes || 'default'}`);
      }
    } catch (error) {
      console.error('OAuth callback error:', error);
      Alert.alert('OAuth Error', `Failed to complete GitHub connection: ${error.message}`);
    } finally {
      setConnectingGithub(false);
    }
  }, []);

  const checkPendingOAuthCallback = useCallback(async () => {
    try {
      const pendingJson = await AsyncStorage.getItem(STORAGE_KEYS.GITHUB_OAUTH_PENDING);
      if (!pendingJson) return;
      const { code, state } = JSON.parse(pendingJson);
      await AsyncStorage.removeItem(STORAGE_KEYS.GITHUB_OAUTH_PENDING);
      await handleOAuthCallback(code, state);
    } catch (error) {
      console.error('Error checking pending OAuth:', error);
    }
  }, [handleOAuthCallback]);

  const loadSettings = useCallback(async () => {
    try {
      const [
        savedUserId,
        savedBaseUrl,
        savedUseCustomUrl,
        savedGithubConnectionId,
        savedSpeakNotifications,
        savedAutoSpeak,
        savedSimulate,
        savedPhoneUrl,
      ] = await Promise.all([
        AsyncStorage.getItem(STORAGE_KEYS.USER_ID),
        AsyncStorage.getItem(STORAGE_KEYS.BASE_URL),
        AsyncStorage.getItem(STORAGE_KEYS.USE_CUSTOM_URL),
        AsyncStorage.getItem(STORAGE_KEYS.GITHUB_CONNECTION_ID),
        getSpeakNotifications(),
        getAutoSpeakEnabled(),
        getSimulateGlassesAudio(),
        getPhoneDispatcherUrl(),
      ]);

      if (savedUserId) setUserId(savedUserId);
      if (savedBaseUrl) setBaseUrl(savedBaseUrl);
      if (savedUseCustomUrl) setUseCustomUrl(savedUseCustomUrl === 'true');
      if (savedGithubConnectionId) setGithubConnectionId(savedGithubConnectionId);

      setSpeakNotificationsState(Boolean(savedSpeakNotifications));
      setAutoSpeakNotifications(Boolean(savedAutoSpeak));
      setSimulateGlassesAudioState(Boolean(savedSimulate));
      setPhoneDispatcherUrlState(savedPhoneUrl || '');

      await loadPushStatus();
      await checkPendingOAuthCallback();
    } catch (error) {
      console.error('Failed to load settings:', error);
    } finally {
      setLoading(false);
    }
  }, [checkPendingOAuthCallback, loadPushStatus]);

  useEffect(() => {
    loadSettings();
  }, [loadSettings]);

  const maskToken = (token) => {
    if (!token) return 'Not set';
    if (token.length <= 10) return token;
    return `${token.substring(0, 6)}...${token.substring(token.length - 4)}`;
  };

  const handleRequestPermission = async () => {
    setPushLoading(true);
    try {
      const token = await registerForPushAsync();
      if (token) {
        setPushToken(token);
        Alert.alert('Success', 'Push permission granted and token obtained!');
      } else {
        Alert.alert('Error', 'Failed to get push token. Make sure you are on a physical device.');
      }
    } catch (error) {
      Alert.alert('Error', `Failed to request permission: ${error.message}`);
    } finally {
      setPushLoading(false);
    }
  };

  const handleRegisterSubscription = async () => {
    if (!pushToken) {
      Alert.alert('Error', 'Please request push permission first to get a token.');
      return;
    }

    setPushLoading(true);
    try {
      const subscription = await registerSubscriptionWithBackend(pushToken);
      await loadPushStatus();
      Alert.alert('Success', `Registered subscription: ${subscription.id}`);
    } catch (error) {
      Alert.alert('Error', `Failed to register: ${error.message}`);
    } finally {
      setPushLoading(false);
    }
  };

  const handleUnregisterSubscription = async (subscriptionId) => {
    Alert.alert('Unregister Subscription', `Are you sure you want to unregister subscription ${subscriptionId}?`, [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Unregister',
        style: 'destructive',
        onPress: async () => {
          setPushLoading(true);
          try {
            await unregisterSubscriptionWithBackend(subscriptionId);
            await loadPushStatus();
            Alert.alert('Success', 'Subscription unregistered');
          } catch (error) {
            Alert.alert('Error', `Failed to unregister: ${error.message}`);
          } finally {
            setPushLoading(false);
          }
        },
      },
    ]);
  };

  const handleAutoSpeakToggle = async (value) => {
    const previousValue = autoSpeakNotifications;
    setAutoSpeakNotifications(value);
    try {
      await setAutoSpeakEnabled(value);
    } catch (error) {
      console.error('Failed to save auto-speak setting:', error);
      setAutoSpeakNotifications(previousValue);
      Alert.alert('Error', 'Failed to save auto-speak setting');
    }
  };

  const generateUserId = () => {
    const uuid = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
      const r = (Math.random() * 16) | 0;
      const v = c === 'x' ? r : (r & 0x3) | 0x8;
      return v.toString(16);
    });
    setUserId(uuid);
  };

  const connectGitHub = async () => {
    try {
      setConnectingGithub(true);
      const response = await startGitHubOAuth();
      if (!response.authorize_url) {
        throw new Error('No authorization URL received from server');
      }

      const result = await WebBrowser.openAuthSessionAsync(
        response.authorize_url,
        'handsfree://oauth/callback'
      );

      if (result.type === 'cancel') {
        Alert.alert('Cancelled', 'GitHub authorization was cancelled');
      } else if (result.type === 'dismiss') {
        Alert.alert('Dismissed', 'GitHub authorization was dismissed');
      }
    } catch (error) {
      console.error('GitHub OAuth error:', error);
      Alert.alert('Connection Error', `Failed to connect GitHub: ${error.message}`);
    } finally {
      setConnectingGithub(false);
    }
  };

  const disconnectGitHub = async () => {
    Alert.alert('Disconnect GitHub', 'Are you sure you want to disconnect GitHub?', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Disconnect',
        style: 'destructive',
        onPress: async () => {
          try {
            await AsyncStorage.removeItem(STORAGE_KEYS.GITHUB_CONNECTION_ID);
            setGithubConnectionId(null);
            Alert.alert('Success', 'GitHub disconnected');
          } catch (error) {
            Alert.alert('Error', `Failed to disconnect: ${error.message}`);
          }
        },
      },
    ]);
  };

  const saveSettings = async () => {
    try {
      await AsyncStorage.setItem(STORAGE_KEYS.USER_ID, userId);
      await AsyncStorage.setItem(STORAGE_KEYS.BASE_URL, baseUrl);
      await AsyncStorage.setItem(STORAGE_KEYS.USE_CUSTOM_URL, useCustomUrl.toString());
      await setSpeakNotifications(speakNotifications);

      await setSimulateGlassesAudio(simulateGlassesAudio);
      clearGlassesAudioCache();

      await setPhoneDispatcherUrl(phoneDispatcherUrl);

      Alert.alert('Success', 'Settings saved! Changes take effect immediately on next use.');
    } catch (error) {
      Alert.alert('Error', `Failed to save settings: ${error.message}`);
    }
  };

  const resetToDefaults = () => {
    Alert.alert('Reset Settings', 'Are you sure you want to reset to default values?', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Reset',
        style: 'destructive',
        onPress: async () => {
          setUserId('');
          setBaseUrl(DEFAULT_BASE_URL);
          setUseCustomUrl(false);
          setSpeakNotificationsState(__DEV__);
          setAutoSpeakNotifications(false);
          setSimulateGlassesAudioState(false);
          setPhoneDispatcherUrlState('');

          try {
            await AsyncStorage.multiRemove([
              STORAGE_KEYS.USER_ID,
              STORAGE_KEYS.BASE_URL,
              STORAGE_KEYS.USE_CUSTOM_URL,
              STORAGE_KEYS.GITHUB_CONNECTION_ID,
              STORAGE_KEYS.SPEAK_NOTIFICATIONS,
            ]);
            await setSpeakNotifications(__DEV__);
            await setAutoSpeakEnabled(false);
            await setSimulateGlassesAudio(false);
            clearGlassesAudioCache();
            await setPhoneDispatcherUrl('');

            Alert.alert('Success', 'Settings reset to defaults');
          } catch (error) {
            Alert.alert('Error', `Failed to reset settings: ${error.message}`);
          }
        },
      },
    ]);
  };

  const testPhoneDispatch = async () => {
    setDispatchTesting(true);
    try {
      const result = await dispatchViaPhone({
        title: `handsfree mobile dispatch test (${new Date().toISOString()})`,
        body: 'This is a test dispatch from the mobile app. If you see this, the phone-local dispatcher wiring works.',
        labels: ['handsfree', 'mobile-test'],
      });
      const pretty = typeof result === 'string' ? result : JSON.stringify(result, null, 2);
      Alert.alert('Dispatch Succeeded', pretty.length > 200 ? `${pretty.slice(0, 200)}…` : pretty);
    } catch (error) {
      Alert.alert('Dispatch Failed', String(error?.message || error));
    } finally {
      setDispatchTesting(false);
    }
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

  const connectGitHub = async () => {
    try {
      setConnectingGithub(true);

      // Start OAuth flow
      const response = await startGitHubOAuth();
      
      if (!response.authorize_url) {
        throw new Error('No authorization URL received from server');
      }

      // Open GitHub OAuth page in system browser
      const result = await WebBrowser.openAuthSessionAsync(
        response.authorize_url,
        'handsfree://oauth/callback'
      );

      if (result.type === 'cancel') {
        Alert.alert('Cancelled', 'GitHub authorization was cancelled');
      } else if (result.type === 'dismiss') {
        Alert.alert('Dismissed', 'GitHub authorization was dismissed');
      }
      // If successful, the deep link handler will process the callback
    } catch (error) {
      console.error('GitHub OAuth error:', error);
      Alert.alert(
        'Connection Error',
        `Failed to connect GitHub: ${error.message}`,
        [{ text: 'OK' }]
      );
    } finally {
      setConnectingGithub(false);
    }
  };

  const disconnectGitHub = async () => {
    Alert.alert(
      'Disconnect GitHub',
      'Are you sure you want to disconnect GitHub?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Disconnect',
          style: 'destructive',
          onPress: async () => {
            try {
              await AsyncStorage.removeItem(STORAGE_KEYS.GITHUB_CONNECTION_ID);
              setGithubConnectionId(null);
              Alert.alert('Success', 'GitHub disconnected');
            } catch (error) {
              Alert.alert('Error', `Failed to disconnect: ${error.message}`);
            }
          },
        },
      ]
    );
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

      {/* GitHub Connection Section */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>GitHub Connection</Text>
        <Text style={styles.helpText}>
          Connect your GitHub account to enable OAuth-based features.
        </Text>

        {connectingGithub && (
          <View style={styles.loadingContainer}>
            <ActivityIndicator size="small" color="#007AFF" />
            <Text style={styles.loadingText}>Connecting to GitHub...</Text>
          </View>
        )}

        {githubConnectionId ? (
          <>
            <View style={styles.connectedContainer}>
              <Text style={styles.connectedText}>✓ GitHub Connected</Text>
              <Text style={styles.connectionIdText}>
                Connection ID: {githubConnectionId?.length > 8 
                  ? `${githubConnectionId.substring(0, 8)}...` 
                  : githubConnectionId}
              </Text>
            </View>
            <View style={styles.buttonContainer}>
              <Button
                title="Disconnect GitHub"
                onPress={disconnectGitHub}
                color="#dc3545"
                disabled={connectingGithub}
              />
            </View>
          </>
        ) : (
          <View style={styles.buttonContainer}>
            <Button
              title="Connect GitHub"
              onPress={connectGitHub}
              color="#28a745"
              disabled={connectingGithub}
            />
          </View>
        )}
      </View>

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

      {/* Dev Tools */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Dev Tools</Text>

        <View style={styles.switchContainer}>
          <Text style={styles.switchLabel}>Simulate glasses audio</Text>
          <Switch
            value={simulateGlassesAudio}
            onValueChange={setSimulateGlassesAudioState}
            trackColor={{ false: '#767577', true: '#81b0ff' }}
            thumbColor={simulateGlassesAudio ? '#007AFF' : '#f4f3f4'}
          />
        </View>
        <Text style={styles.helpText}>
          When enabled, the app uses an expo-av based simulation instead of the native glasses module.
        </Text>

        <Text style={styles.sectionSubtitle}>Phone Dispatcher</Text>
        <Text style={styles.helpText}>
          Base URL for a phone-local dispatcher service (expects POST /dispatch). Example: http://192.168.1.42:8765
        </Text>
        <TextInput
          style={styles.input}
          placeholder="http://192.168.1.42:8765"
          value={phoneDispatcherUrl}
          onChangeText={setPhoneDispatcherUrlState}
          autoCapitalize="none"
          autoCorrect={false}
          keyboardType="url"
        />
        <View style={styles.buttonContainer}>
          <Button
            title={dispatchTesting ? 'Testing…' : 'Test Phone Dispatch'}
            onPress={testPhoneDispatch}
            disabled={dispatchTesting}
            color="#4CAF50"
          />
        </View>
      </View>

      {/* Push Notifications Configuration */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Push Notifications</Text>
        
        <Text style={styles.helpText}>
          Manage push notification permissions and subscriptions.
        </Text>

        {/* Push Token Display */}
        <View style={styles.infoRow}>
          <Text style={styles.infoLabel}>Push Token:</Text>
          <Text style={styles.infoValue}>{maskToken(pushToken)}</Text>
        </View>

        {/* Subscription Status */}
        <View style={styles.infoRow}>
          <Text style={styles.infoLabel}>Active Subscriptions:</Text>
          <Text style={styles.infoValue}>{subscriptions.length}</Text>
        </View>

        {/* Push Action Buttons */}
        <View style={styles.buttonContainer}>
          <Button
            title="Request Permission & Get Token"
            onPress={handleRequestPermission}
            disabled={pushLoading}
            color="#007AFF"
          />
        </View>

        <View style={styles.buttonContainer}>
          <Button
            title="Register Subscription"
            onPress={handleRegisterSubscription}
            disabled={pushLoading || !pushToken}
            color="#28a745"
          />
        </View>

        {/* List Active Subscriptions */}
        {subscriptions.length > 0 && (
          <View style={styles.subscriptionList}>
            <Text style={styles.subscriptionListTitle}>Active Subscriptions:</Text>
            {subscriptions.map((sub) => (
              <View key={sub.id} style={styles.subscriptionItem}>
                <View style={styles.subscriptionInfo}>
                  <Text style={styles.subscriptionId}>ID: {sub.id}</Text>
                  <Text style={styles.subscriptionPlatform}>Platform: {sub.platform}</Text>
                  <Text style={styles.subscriptionEndpoint}>
                    Token: {maskToken(sub.endpoint)}
                  </Text>
                </View>
                <View style={styles.subscriptionActions}>
                  <Button
                    title="Unregister"
                    onPress={() => handleUnregisterSubscription(sub.id)}
                    disabled={pushLoading}
                    color="#dc3545"
                  />
                </View>
              </View>
            ))}
          </View>
        )}

        {/* Auto-speak Toggle */}
        <View style={styles.switchContainer}>
          <Text style={styles.switchLabel}>Auto-speak notifications</Text>
          <Switch
            value={autoSpeakNotifications}
            onValueChange={handleAutoSpeakToggle}
            trackColor={{ false: '#767577', true: '#81b0ff' }}
            thumbColor={autoSpeakNotifications ? '#007AFF' : '#f4f3f4'}
          />
        </View>
        <Text style={styles.helpText}>
          When enabled, notifications will be automatically spoken aloud.
        </Text>
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
          When enabled, incoming notifications will be spoken via TTS.
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
        <Text style={styles.debugText}>
          Simulate glasses audio: {simulateGlassesAudio ? 'Enabled' : 'Disabled'}
        </Text>
        <Text style={styles.debugText}>
          Phone dispatcher URL: {phoneDispatcherUrl || '(not set)'}
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
  sectionSubtitle: {
    fontSize: 15,
    fontWeight: '600',
    marginTop: 5,
    marginBottom: 5,
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
  infoRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 10,
    paddingVertical: 5,
  },
  infoLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
  },
  infoValue: {
    fontSize: 14,
    color: '#666',
    fontFamily: 'monospace',
  },
  subscriptionList: {
    marginTop: 15,
    paddingTop: 15,
    borderTopWidth: 1,
    borderTopColor: '#e0e0e0',
  },
  subscriptionListTitle: {
    fontSize: 14,
    fontWeight: '600',
    marginBottom: 10,
    color: '#333',
  },
  subscriptionItem: {
    backgroundColor: '#f8f9fa',
    padding: 10,
    borderRadius: 5,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: '#e0e0e0',
  },
  subscriptionInfo: {
    marginBottom: 10,
  },
  subscriptionId: {
    fontSize: 12,
    fontWeight: '600',
    marginBottom: 3,
    color: '#333',
  },
  subscriptionPlatform: {
    fontSize: 12,
    marginBottom: 3,
    color: '#666',
  },
  subscriptionEndpoint: {
    fontSize: 11,
    color: '#666',
    fontFamily: 'monospace',
  },
  subscriptionActions: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
  },
  loadingContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 15,
    padding: 10,
    backgroundColor: '#f0f0f0',
    borderRadius: 5,
  },
  loadingText: {
    marginLeft: 10,
    fontSize: 14,
    color: '#666',
  },
  connectedContainer: {
    backgroundColor: '#d4edda',
    padding: 12,
    borderRadius: 5,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: '#c3e6cb',
  },
  connectedText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#155724',
    marginBottom: 5,
  },
  connectionIdText: {
    fontSize: 12,
    fontFamily: 'monospace',
    color: '#155724',
  },
});
