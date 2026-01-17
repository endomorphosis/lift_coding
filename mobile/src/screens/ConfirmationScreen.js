import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  Button,
  StyleSheet,
  ScrollView,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { confirmCommand } from '../api/client';

export default function ConfirmationScreen() {
  const [token, setToken] = useState('');
  const [idempotencyKey, setIdempotencyKey] = useState('');
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState(null);
  const [error, setError] = useState(null);

  const handleConfirm = async () => {
    if (!token.trim()) {
      Alert.alert('Error', 'Please enter a confirmation token');
      return;
    }

    setLoading(true);
    setError(null);
    setResponse(null);

    try {
      const data = await confirmCommand(token.trim(), idempotencyKey.trim() || undefined);
      setResponse(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <ScrollView style={styles.container}>
      <Text style={styles.title}>Confirmation</Text>

      <Text style={styles.instructions}>
        Paste the confirmation token from a command response that requires confirmation.
      </Text>

      <TextInput
        style={styles.input}
        placeholder="Confirmation token (e.g., conf-abc123...)"
        value={token}
        onChangeText={setToken}
        editable={!loading}
        autoCapitalize="none"
      />

      <TextInput
        style={styles.input}
        placeholder="Idempotency key (optional)"
        value={idempotencyKey}
        onChangeText={setIdempotencyKey}
        editable={!loading}
        autoCapitalize="none"
      />

      <View style={styles.buttonRow}>
        <View style={styles.button}>
          <Button
            title="Confirm"
            onPress={handleConfirm}
            disabled={loading}
            color="#28a745"
          />
        </View>
        <View style={styles.button}>
          <Button
            title="Clear"
            onPress={() => {
              setToken('');
              setIdempotencyKey('');
              setResponse(null);
              setError(null);
            }}
            disabled={loading}
            color="#dc3545"
          />
        </View>
      </View>

      {loading && (
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#007AFF" />
        </View>
      )}

      {error && (
        <View style={styles.errorContainer}>
          <Text style={styles.errorText}>Error: {error}</Text>
        </View>
      )}

      {response && (
        <View style={styles.responseContainer}>
          <Text style={styles.sectionTitle}>Response:</Text>

          {response.spoken_text && (
            <View style={styles.spokenTextContainer}>
              <Text style={styles.label}>Spoken Text:</Text>
              <Text style={styles.value}>{response.spoken_text}</Text>
            </View>
          )}

          {response.status && (
            <View style={styles.statusContainer}>
              <Text style={styles.label}>Status:</Text>
              <Text style={styles.value}>{response.status}</Text>
            </View>
          )}

          <View style={styles.rawContainer}>
            <Text style={styles.label}>Full Response:</Text>
            <Text style={styles.rawText}>
              {JSON.stringify(response, null, 2)}
            </Text>
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
    marginBottom: 10,
  },
  instructions: {
    fontSize: 14,
    color: '#666',
    marginBottom: 20,
  },
  input: {
    backgroundColor: 'white',
    padding: 15,
    borderRadius: 5,
    fontSize: 16,
    marginBottom: 15,
  },
  buttonRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 10,
  },
  button: {
    flex: 1,
    marginHorizontal: 5,
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
  errorText: {
    color: '#c62828',
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
  statusContainer: {
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
  rawContainer: {
    backgroundColor: '#f0f0f0',
    padding: 10,
    borderRadius: 5,
    marginTop: 10,
  },
  rawText: {
    fontSize: 12,
    fontFamily: 'monospace',
    color: '#333',
  },
});
