import React from 'react';
import { StyleSheet, Text, TouchableOpacity, View } from 'react-native';

export default function FollowOnTaskCard({ followOnTask, onOpenTask }) {
  if (!followOnTask?.task_id) {
    return null;
  }

  return (
    <View style={styles.container}>
      <Text style={styles.label}>Follow-on Task:</Text>
      {followOnTask.summary ? <Text style={styles.summary}>{followOnTask.summary}</Text> : null}
      <Text style={styles.value}>Task ID: {followOnTask.task_id}</Text>
      {followOnTask.state ? (
        <Text style={styles.value}>State: {followOnTask.state}</Text>
      ) : null}
      {followOnTask.provider_label || followOnTask.provider ? (
        <Text style={styles.value}>
          Provider: {followOnTask.provider_label || followOnTask.provider}
        </Text>
      ) : null}
      {followOnTask.capability ? (
        <Text style={styles.value}>Capability: {followOnTask.capability}</Text>
      ) : null}
      {followOnTask.provider_label && followOnTask.provider && followOnTask.provider_label !== followOnTask.provider ? (
        <Text style={styles.value}>Provider ID: {followOnTask.provider}</Text>
      ) : null}
      {typeof onOpenTask === 'function' ? (
        <TouchableOpacity style={styles.button} onPress={() => onOpenTask(followOnTask.task_id)}>
          <Text style={styles.buttonText}>Open Task Detail</Text>
        </TouchableOpacity>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: '#eef6ff',
    padding: 12,
    borderRadius: 8,
    marginBottom: 15,
  },
  label: {
    fontSize: 14,
    fontWeight: '600',
    marginBottom: 5,
    color: '#666',
  },
  summary: {
    fontSize: 14,
    color: '#1f2937',
    marginBottom: 6,
  },
  value: {
    fontSize: 16,
    color: '#000',
  },
  button: {
    marginTop: 10,
    alignSelf: 'flex-start',
    backgroundColor: '#dbeafe',
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 8,
  },
  buttonText: {
    color: '#1d4ed8',
    fontSize: 13,
    fontWeight: '600',
  },
});
