import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ActivityIndicator,
  Button,
  TextInput,
  ScrollView,
  Alert,
} from 'react-native';
import {
  getStatus,
  listRepoSubscriptions,
  createRepoSubscription,
  deleteRepoSubscription,
  sendTestPullRequestOpenedWebhook,
} from '../api/client';
import {
  registerForPushAsync,
  registerSubscriptionWithBackend,
  unregisterSubscriptionWithBackend,
  listSubscriptions,
} from '../push/pushClient';
import {
  setupNotificationListeners,
  checkAndSpeakLatestNotification,
} from '../push/notificationsHandler';

export default function StatusScreen() {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Push notification state
  const [pushToken, setPushToken] = useState(null);
  const [subscriptionId, setSubscriptionId] = useState(null);
  const [pushLoading, setPushLoading] = useState(false);
  const [lastNotification, setLastNotification] = useState(null);

  // Repo subscriptions (used to map webhooks -> users)
  const [repoSubscriptions, setRepoSubscriptions] = useState([]);
  const [repoSubLoading, setRepoSubLoading] = useState(false);
  const [repoFullName, setRepoFullName] = useState('');

  const fetchStatus = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getStatus();
      setStatus(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const checkExistingSubscription = async () => {
    try {
      const subscriptions = await listSubscriptions();
      if (subscriptions.length > 0) {
        // Use the first subscription (most recent)
        const sub = subscriptions[0];
        setSubscriptionId(sub.id);
        setPushToken(sub.endpoint);
      }
    } catch (err) {
      console.log('Could not check existing subscriptions:', err.message);
    }
  };

  const handleEnablePush = async () => {
    setPushLoading(true);
    try {
      // Get push token
      const token = await registerForPushAsync();
      if (!token) {
        Alert.alert('Push Not Available', 'Push notifications are not available on this device or permission was denied.');
        return;
      }
      
      setPushToken(token);
      
      // Register with backend
      const subscription = await registerSubscriptionWithBackend(token);
      setSubscriptionId(subscription.id);
      
      Alert.alert('Push Enabled', 'Push notifications are now enabled!');
    } catch (err) {
      Alert.alert('Error', `Failed to enable push: ${err.message}`);
    } finally {
      setPushLoading(false);
    }
  };

  const handleDisablePush = async () => {
    if (!subscriptionId) {
      Alert.alert('No Subscription', 'No active push subscription found.');
      return;
    }
    
    setPushLoading(true);
    try {
      await unregisterSubscriptionWithBackend(subscriptionId);
      setSubscriptionId(null);
      setPushToken(null);
      Alert.alert('Push Disabled', 'Push notifications have been disabled.');
    } catch (err) {
      Alert.alert('Error', `Failed to disable push: ${err.message}`);
    } finally {
      setPushLoading(false);
    }
  };

  const handleTestNotification = async () => {
    try {
      const notification = await checkAndSpeakLatestNotification();
      if (notification) {
        Alert.alert('Success', 'Spoke latest notification via TTS!');
      } else {
        Alert.alert('No Notifications', 'No notifications available to speak.');
      }
    } catch (err) {
      Alert.alert('Error', `Failed to test notification: ${err.message}`);
    }
  };

  const refreshRepoSubscriptions = async () => {
    setRepoSubLoading(true);
    try {
      const subs = await listRepoSubscriptions();
      setRepoSubscriptions(subs);
    } catch (err) {
      console.log('Could not list repo subscriptions:', err.message);
    } finally {
      setRepoSubLoading(false);
    }
  };

  const handleSubscribeRepo = async () => {
    const repo = (repoFullName || '').trim();
    if (!repo) {
      Alert.alert('Missing Repo', "Enter a repo like 'owner/repo'.");
      return;
    }

    setRepoSubLoading(true);
    try {
      await createRepoSubscription(repo);
      setRepoFullName('');
      await refreshRepoSubscriptions();
      Alert.alert('Subscribed', `Subscribed to ${repo}`);
    } catch (err) {
      Alert.alert('Error', `Failed to subscribe: ${err.message}`);
    } finally {
      setRepoSubLoading(false);
    }
  };

  const handleUnsubscribeRepo = async (repo) => {
    setRepoSubLoading(true);
    try {
      await deleteRepoSubscription(repo);
      await refreshRepoSubscriptions();
    } catch (err) {
      Alert.alert('Error', `Failed to unsubscribe: ${err.message}`);
    } finally {
      setRepoSubLoading(false);
    }
  };

  const handleSendTestWebhook = async () => {
    const repo = (repoFullName || '').trim() || (repoSubscriptions[0] && repoSubscriptions[0].repo_full_name);
    if (!repo) {
      Alert.alert('Missing Repo', "Enter a repo like 'owner/repo' or subscribe to one first.");
      return;
    }

    setRepoSubLoading(true);
    try {
      await sendTestPullRequestOpenedWebhook({
        repo_full_name: repo,
        pr_number: 123,
        pr_title: 'Test PR opened (mobile)',
      });
      Alert.alert('Webhook Sent', 'Sent pull_request.opened webhook. If you are subscribed and push is enabled, a notification should arrive shortly.');
    } catch (err) {
      Alert.alert('Error', `Failed to send webhook: ${err.message}`);
    } finally {
      setRepoSubLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
    checkExistingSubscription();
    refreshRepoSubscriptions();
    
    // Setup notification listeners
    const cleanup = setupNotificationListeners((notification) => {
      console.log('Notification received in StatusScreen:', notification);
      // Update UI with latest notification
      setLastNotification({
        title: notification.request.content.title,
        body: notification.request.content.body,
        timestamp: new Date().toISOString(),
      });
    });
    
    return cleanup;
  }, []);

  return (
    <ScrollView style={styles.container}>
      <Text style={styles.title}>Backend Status</Text>

      {loading && <ActivityIndicator size="large" color="#007AFF" />}

      {error && (
        <View style={styles.errorContainer}>
          <Text style={styles.errorText}>Error: {error}</Text>
          <Button title="Retry" onPress={fetchStatus} />
        </View>
      )}

      {status && (
        <View style={styles.statusContainer}>
          <Text style={styles.label}>Status:</Text>
          <Text style={styles.value}>{status.status || 'unknown'}</Text>

          {status.version && (
            <>
              <Text style={styles.label}>Version:</Text>
              <Text style={styles.value}>{status.version}</Text>
            </>
          )}

          {status.user_id && (
            <>
              <Text style={styles.label}>User ID:</Text>
              <Text style={styles.value}>{status.user_id}</Text>
            </>
          )}

          <View style={styles.buttonContainer}>
            <Button title="Refresh" onPress={fetchStatus} />
          </View>
        </View>
      )}

      {/* Push Notifications Section */}
      <View style={styles.pushContainer}>
        <Text style={styles.sectionTitle}>Push Notifications</Text>
        
        {pushToken && (
          <View style={styles.tokenContainer}>
            <Text style={styles.label}>Token:</Text>
            <Text style={styles.tokenText} numberOfLines={1} ellipsizeMode="middle">
              {pushToken}
            </Text>
            <Text style={styles.label}>Status:</Text>
            <Text style={[styles.value, styles.statusActive]}>
              {subscriptionId ? '✓ Active' : 'Inactive'}
            </Text>
          </View>
        )}

        <View style={styles.buttonRow}>
          {!subscriptionId ? (
            <Button
              title="Enable Push"
              onPress={handleEnablePush}
              disabled={pushLoading}
            />
          ) : (
            <Button
              title="Disable Push"
              onPress={handleDisablePush}
              disabled={pushLoading}
              color="#c62828"
            />
          )}
        </View>

        <View style={styles.buttonRow}>
          <Button
            title="Test Notification (Polling)"
            onPress={handleTestNotification}
            color="#4CAF50"
          />
        </View>

        {pushLoading && <ActivityIndicator size="small" color="#007AFF" />}
        
        {lastNotification && (
          <View style={styles.lastNotificationContainer}>
            <Text style={styles.label}>Last Notification:</Text>
            <Text style={styles.notificationTitle}>{lastNotification.title || 'N/A'}</Text>
            <Text style={styles.notificationBody} numberOfLines={2}>
              {lastNotification.body}
            </Text>
            <Text style={styles.notificationTime}>
              {new Date(lastNotification.timestamp).toLocaleTimeString()}
            </Text>
          </View>
        )}
        
        <Text style={styles.helpText}>
          Enable push to receive real-time notifications. Use "Test Notification" to poll and speak the latest notification via TTS.
        </Text>
      </View>

      {/* Repo Subscriptions Section */}
      <View style={styles.pushContainer}>
        <Text style={styles.sectionTitle}>Repo Subscriptions</Text>
        <Text style={styles.helperText}>
          Subscribe to repos so webhook replays generate notifications for you.
        </Text>

        <View style={styles.repoInputRow}>
          <TextInput
            style={styles.repoInput}
            placeholder="owner/repo"
            value={repoFullName}
            autoCapitalize="none"
            autoCorrect={false}
            onChangeText={setRepoFullName}
          />
          <View style={styles.repoButton}>
            <Button title="Subscribe" onPress={handleSubscribeRepo} disabled={repoSubLoading} />
          </View>
        </View>

        <View style={styles.buttonRow}>
          <Button title="Refresh" onPress={refreshRepoSubscriptions} disabled={repoSubLoading} />
        </View>

        <View style={styles.buttonRow}>
          <Button
            title="Send Test Webhook (PR Opened)"
            onPress={handleSendTestWebhook}
            disabled={repoSubLoading}
            color="#4CAF50"
          />
        </View>

        {repoSubLoading && <ActivityIndicator size="small" color="#007AFF" />}

        {repoSubscriptions.length === 0 ? (
          <Text style={styles.emptyText}>No repo subscriptions yet.</Text>
        ) : (
          <View style={styles.repoList}>
            {repoSubscriptions.map((sub) => (
              <View key={sub.id} style={styles.repoRow}>
                <Text style={styles.repoText}>{sub.repo_full_name}</Text>
                <Button
                  title="Remove"
                  color="#c62828"
                  onPress={() => handleUnsubscribeRepo(sub.repo_full_name)}
                  disabled={repoSubLoading}
                />
              </View>
            ))}
          </View>
        )}
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
    marginBottom: 20,
  },
  errorContainer: {
    backgroundColor: '#ffebee',
    padding: 15,
    borderRadius: 5,
    marginVertical: 10,
  },
  errorText: {
    color: '#c62828',
    marginBottom: 10,
  },
  statusContainer: {
    backgroundColor: 'white',
    padding: 15,
    borderRadius: 5,
  },
  label: {
    fontSize: 14,
    fontWeight: '600',
    marginTop: 10,
    color: '#666',
  },
  value: {
    fontSize: 16,
    marginTop: 5,
    color: '#000',
  },
  buttonContainer: {
    marginTop: 20,
  },
  pushContainer: {
    backgroundColor: 'white',
    padding: 15,
    borderRadius: 5,
    marginTop: 20,
  },
  helperText: {
    fontSize: 12,
    color: '#666',
    marginBottom: 10,
  },
  repoInputRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 10,
  },
  repoInput: {
    flex: 1,
    borderWidth: 1,
    borderColor: '#ddd',
    backgroundColor: '#fff',
    borderRadius: 5,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 14,
  },
  repoButton: {
    marginLeft: 10,
  },
  repoList: {
    marginTop: 8,
  },
  repoRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#eee',
  },
  repoText: {
    flex: 1,
    marginRight: 10,
    fontSize: 14,
    color: '#111',
  },
  emptyText: {
    fontSize: 13,
    color: '#666',
    marginTop: 6,
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    marginBottom: 15,
    color: '#000',
  },
  tokenContainer: {
    backgroundColor: '#f5f5f5',
    padding: 10,
    borderRadius: 5,
    marginBottom: 15,
  },
  tokenText: {
    fontSize: 12,
    fontFamily: 'monospace',
    color: '#333',
    marginTop: 5,
    marginBottom: 10,
  },
  statusActive: {
    color: '#4CAF50',
    fontWeight: 'bold',
  },
  buttonRow: {
    marginVertical: 5,
  },
  helpText: {
    fontSize: 12,
    color: '#666',
    marginTop: 15,
    fontStyle: 'italic',
  },
  lastNotificationContainer: {
    backgroundColor: '#e3f2fd',
    padding: 10,
    borderRadius: 5,
    marginTop: 15,
  },
  notificationTitle: {
    fontSize: 14,
    fontWeight: 'bold',
    marginTop: 5,
    color: '#000',
  },
  notificationBody: {
    fontSize: 13,
    marginTop: 5,
    color: '#333',
  },
  notificationTime: {
    fontSize: 11,
    marginTop: 5,
    color: '#666',
    fontStyle: 'italic',
  },
});
