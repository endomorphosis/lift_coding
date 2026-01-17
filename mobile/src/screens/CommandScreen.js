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
            {card.subtitle ? (
              <Text style={styles.cardSubtitle}>{card.subtitle}</Text>
            ) : null}
            {Array.isArray(card.lines)
              ? card.lines.map((line, idx) => (
                  <Text key={idx} style={styles.cardLine}>
                    {line}
                  </Text>
                ))
              : null}
            {card.deep_link ? (
              <Text style={styles.cardLink}>{card.deep_link}</Text>
            ) : null}
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

          {response.status && (
            <View style={styles.spokenTextContainer}>
              <Text style={styles.label}>Status:</Text>
              <Text style={styles.value}>{response.status}</Text>
            </View>
          )}

          {response.intent && response.intent.name && (
            <View style={styles.spokenTextContainer}>
              <Text style={styles.label}>Intent:</Text>
              <Text style={styles.value}>{response.intent.name}</Text>
            </View>
          )}

          {response.spoken_text && (
            <View style={styles.spokenTextContainer}>
              <Text style={styles.label}>Spoken Text:</Text>
              <Text style={styles.value}>{response.spoken_text}</Text>
            </View>
          )}

          {response.pending_action && (
            <View style={styles.confirmationNotice}>
              <Text style={styles.confirmationText}>
                ⚠️ This action requires confirmation
              </Text>
              <Text style={styles.actionIdText}>
                Token: {response.pending_action.token}
              </Text>
              {response.pending_action.summary ? (
                <Text style={styles.actionIdText}>
                  Summary: {response.pending_action.summary}
                </Text>
              ) : null}
            </View>
          )}

          {renderUICards(response.cards)}

          {response.debug && (
            <View style={styles.debugContainer}>
              <Text style={styles.label}>Debug Info:</Text>
              <Text style={styles.debugText}>
                {JSON.stringify(response.debug, null, 2)}
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
  cardSubtitle: {
    fontSize: 13,
    color: '#666',
    marginBottom: 5,
  },
  cardLine: {
    fontSize: 13,
    color: '#333',
    marginTop: 3,
  },
  cardLink: {
    fontSize: 12,
    color: '#007AFF',
    marginTop: 6,
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
