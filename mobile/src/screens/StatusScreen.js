import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ActivityIndicator,
  Button,
  ScrollView,
} from 'react-native';
import { getStatus } from '../api/client';

export default function StatusScreen() {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

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

  useEffect(() => {
    fetchStatus();
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
});
