import React from 'react';
import { StyleSheet, Text, TouchableOpacity, View } from 'react-native';

export default function PeerChatOutboxPanel({
  summary,
  selectedMessage,
  onSelectMessage,
  onReleaseMessage,
  onPromoteMessage,
}) {
  if (!summary) {
    return null;
  }

  return (
    <>
      <View style={styles.container}>
        <Text style={styles.title}>Backend Outbox</Text>
        <Text style={styles.text}>mode {summary.delivery_mode}</Text>
        <Text style={styles.text}>
          total {summary.queued_total} • deliverable {summary.deliverable_now} • held {summary.held_now}
        </Text>
        <Text style={styles.text}>
          urgent {summary.queued_urgent} • normal {summary.queued_normal}
        </Text>
        {summary.preview_messages?.map((message) => (
          <TouchableOpacity
            key={message.outbox_message_id}
            style={styles.previewCard}
            onPress={() => onSelectMessage?.(message.outbox_message_id)}
          >
            <Text style={styles.text}>
              [{message.priority}] {message.state} • {message.text}
              {message.hold_reason ? ` (${message.hold_reason})` : ''}
            </Text>
            {message.state === 'leased' ? (
              <TouchableOpacity
                style={[styles.button, styles.buttonSecondary]}
                onPress={() => onReleaseMessage?.(message.outbox_message_id)}
              >
                <Text style={styles.buttonTextSecondary}>Release This Message</Text>
              </TouchableOpacity>
            ) : null}
            {message.state === 'held_by_policy' ? (
              <TouchableOpacity
                style={[styles.button, styles.buttonSecondary]}
                onPress={() => onPromoteMessage?.(message.outbox_message_id)}
              >
                <Text style={styles.buttonTextSecondary}>Promote This Message</Text>
              </TouchableOpacity>
            ) : null}
          </TouchableOpacity>
        ))}
      </View>
      {selectedMessage ? (
        <View style={styles.container}>
          <Text style={styles.title}>Selected Outbox Message</Text>
          <Text style={styles.text}>id {selectedMessage.outbox_message_id}</Text>
          <Text style={styles.text}>
            state {selectedMessage.state} • priority {selectedMessage.priority}
          </Text>
          <Text style={styles.text}>conversation {selectedMessage.conversation_id}</Text>
          <Text style={styles.text}>sender {selectedMessage.sender_peer_id}</Text>
          <Text style={styles.text}>timestamp {selectedMessage.timestamp_ms}</Text>
          <Text style={styles.text}>lease {selectedMessage.leased_until_ms || 'none'}</Text>
          <Text style={styles.text}>hold reason {selectedMessage.hold_reason || 'none'}</Text>
          <Text style={styles.text}>text {selectedMessage.text}</Text>
        </View>
      ) : null}
    </>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
    shadowColor: '#000',
    shadowOpacity: 0.05,
    shadowRadius: 8,
    shadowOffset: { width: 0, height: 2 },
    elevation: 2,
  },
  title: {
    fontSize: 16,
    fontWeight: '600',
    color: '#111827',
    marginBottom: 8,
  },
  text: {
    fontSize: 14,
    color: '#374151',
    marginBottom: 6,
  },
  previewCard: {
    backgroundColor: '#f9fafb',
    borderRadius: 10,
    padding: 12,
    marginTop: 10,
  },
  button: {
    borderRadius: 10,
    paddingVertical: 10,
    paddingHorizontal: 14,
    alignItems: 'center',
    marginTop: 10,
  },
  buttonSecondary: {
    borderWidth: 1,
    borderColor: '#cbd5e1',
    backgroundColor: '#fff',
  },
  buttonTextSecondary: {
    color: '#0f172a',
    fontWeight: '600',
  },
});
