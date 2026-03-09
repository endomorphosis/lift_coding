import React from 'react';
import { StyleSheet, Text, View } from 'react-native';

export default function RefreshStatusCard({
  intervalSeconds,
  backgroundRefreshing = false,
  lastRefreshedAt = null,
  idleLabel = null,
}) {
  if (!backgroundRefreshing && !lastRefreshedAt && !intervalSeconds && !idleLabel) {
    return null;
  }

  return (
    <View style={styles.statusCard}>
      {intervalSeconds ? (
        <Text style={styles.statusTitle}>
          Auto-refreshing every {intervalSeconds}s
        </Text>
      ) : idleLabel ? (
        <Text style={styles.statusTitle}>{idleLabel}</Text>
      ) : null}
      {backgroundRefreshing ? (
        <Text style={styles.statusText}>Refreshing in background...</Text>
      ) : null}
      {lastRefreshedAt ? (
        <Text style={styles.statusText}>
          Last refreshed: {new Date(lastRefreshedAt).toLocaleTimeString()}
        </Text>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  statusCard: {
    backgroundColor: '#eef6ff',
    borderRadius: 8,
    padding: 12,
    marginBottom: 12,
  },
  statusTitle: {
    fontSize: 13,
    fontWeight: '700',
    color: '#0b5394',
  },
  statusText: {
    fontSize: 12,
    color: '#234',
    marginTop: 4,
  },
});
