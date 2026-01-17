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
import { sendCommand } from '../api/client';

export default function CommandScreen() {
  const [commandText, setCommandText] = useState('');
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState(null);
  const [error, setError] = useState(null);

  const handleSendCommand = async () => {
    if (!commandText.trim()) {
      Alert.alert('Error', 'Please enter a command');
      return;
    }

    setLoading(true);
    setError(null);
    setResponse(null);

    try {
      const data = await sendCommand(commandText);
      setResponse(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const renderUICards = (cards) => {
    if (!cards || cards.length === 0) return null;

    return (
      <View style={styles.cardsContainer}>
        <Text style={styles.sectionTitle}>UI Cards:</Text>
        {cards.map((card, index) => (
          <View key={index} style={styles.card}>
            <Text style={styles.cardTitle}>{card.title || `Card ${index + 1}`}</Text>
            {card.body && <Text style={styles.cardBody}>{card.body}</Text>}
            {card.fields && card.fields.map((field, idx) => (
              <Text key={idx} style={styles.cardField}>
                {field.label}: {field.value}
              </Text>
            ))}
          </View>
        ))}
      </View>
    );
  };

  return (
    <ScrollView style={styles.container}>
      <Text style={styles.title}>Send Command</Text>

      <TextInput
        style={styles.input}
        placeholder="Enter command (e.g., 'what's in my inbox?')"
        value={commandText}
        onChangeText={setCommandText}
        multiline
        editable={!loading}
      />

      <Button
        title={loading ? 'Sending...' : 'Send Command'}
        onPress={handleSendCommand}
        disabled={loading}
      />

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

          {response.needs_confirmation && (
            <View style={styles.confirmationNotice}>
              <Text style={styles.confirmationText}>
                ⚠️ This action requires confirmation
              </Text>
              {response.action_id && (
                <Text style={styles.actionIdText}>
                  Action ID: {response.action_id}
                </Text>
              )}
            </View>
          )}

          {renderUICards(response.ui_cards)}

          {response.debug_info && (
            <View style={styles.debugContainer}>
              <Text style={styles.label}>Debug Info:</Text>
              <Text style={styles.debugText}>
                {JSON.stringify(response.debug_info, null, 2)}
              </Text>
            </View>
          )}
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
  input: {
    backgroundColor: 'white',
    padding: 15,
    borderRadius: 5,
    fontSize: 16,
    marginBottom: 15,
    minHeight: 100,
    textAlignVertical: 'top',
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
  confirmationNotice: {
    backgroundColor: '#fff3cd',
    padding: 10,
    borderRadius: 5,
    marginBottom: 15,
  },
  confirmationText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#856404',
  },
  actionIdText: {
    fontSize: 12,
    color: '#856404',
    marginTop: 5,
  },
  cardsContainer: {
    marginTop: 10,
  },
  card: {
    backgroundColor: '#f8f9fa',
    padding: 12,
    borderRadius: 5,
    marginBottom: 10,
    borderLeftWidth: 4,
    borderLeftColor: '#007AFF',
  },
  cardTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    marginBottom: 5,
  },
  cardBody: {
    fontSize: 14,
    color: '#333',
    marginBottom: 5,
  },
  cardField: {
    fontSize: 13,
    color: '#555',
    marginTop: 3,
  },
  debugContainer: {
    marginTop: 15,
    backgroundColor: '#f0f0f0',
    padding: 10,
    borderRadius: 5,
  },
  debugText: {
    fontSize: 12,
    fontFamily: 'monospace',
    color: '#333',
  },
});
