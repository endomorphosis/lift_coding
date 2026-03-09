import React from 'react';
import { StyleSheet, Text, View } from 'react-native';

export default function EmptyStateCard({ title, message }) {
  if (!title && !message) {
    return null;
  }

  return (
    <View style={styles.card}>
      {title ? <Text style={styles.title}>{title}</Text> : null}
      {message ? <Text style={styles.message}>{message}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: '#fff',
    padding: 16,
    borderRadius: 10,
    marginTop: 12,
  },
  title: {
    fontSize: 16,
    fontWeight: 'bold',
    marginBottom: 6,
    color: '#222',
  },
  message: {
    fontSize: 13,
    color: '#666',
  },
});
