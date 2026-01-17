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
  const [actionId, setActionId] = useState('');
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState(null);
  const [error, setError] = useState(null);

  const handleConfirm = async (choice) => {
    if (!actionId.trim()) {
      Alert.alert('Error', 'Please enter an action ID');
      return;
    }

    setLoading(true);
    setError(null);
    setResponse(null);

    try {
      const data = await confirmCommand(actionId, choice);
      setResponse({ choice, data });
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
        Enter an action ID from a previous command that requires confirmation.
      </Text>

      <TextInput
        style={styles.input}
        placeholder="Action ID (e.g., action_123...)"
        value={actionId}
        onChangeText={setActionId}
        editable={!loading}
        autoCapitalize="none"
      />

      <View style={styles.buttonRow}>
        <View style={styles.button}>
          <Button
            title="Confirm"
            onPress={() => handleConfirm('confirm')}
            disabled={loading}
            color="#28a745"
          />
        </View>
        <View style={styles.button}>
          <Button
            title="Cancel"
            onPress={() => handleConfirm('cancel')}
            disabled={loading}
            color="#dc3545"
          />
        </View>
      </View>

      <View style={styles.buttonRow}>
        <View style={styles.button}>
          <Button
            title="Repeat"
            onPress={() => handleConfirm('repeat')}
            disabled={loading}
            color="#007AFF"
          />
        </View>
        <View style={styles.button}>
          <Button
            title="Next"
            onPress={() => handleConfirm('next')}
            disabled={loading}
            color="#6c757d"
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
          <Text style={styles.choiceText}>Choice: {response.choice}</Text>

          {response.data.spoken_text && (
            <View style={styles.spokenTextContainer}>
              <Text style={styles.label}>Spoken Text:</Text>
              <Text style={styles.value}>{response.data.spoken_text}</Text>
            </View>
          )}

          {response.data.status && (
            <View style={styles.statusContainer}>
              <Text style={styles.label}>Status:</Text>
              <Text style={styles.value}>{response.data.status}</Text>
            </View>
          )}

          <View style={styles.rawContainer}>
            <Text style={styles.label}>Full Response:</Text>
            <Text style={styles.rawText}>
              {JSON.stringify(response.data, null, 2)}
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
  choiceText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#007AFF',
    marginBottom: 15,
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
