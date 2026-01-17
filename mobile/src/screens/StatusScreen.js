import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ActivityIndicator,
  Button,
  ScrollView,
  Alert,
} from 'react-native';
import { getStatus } from '../api/client';
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

  useEffect(() => {
    fetchStatus();
    checkExistingSubscription();
    
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
