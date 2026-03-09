import React from 'react';
import { StyleSheet, Text, TouchableOpacity, View } from 'react-native';

export default function ScreenHeader({
  title,
  subtitle = null,
  actionLabel = null,
  onActionPress = null,
  actionDisabled = false,
}) {
  return (
    <View style={styles.container}>
      <Text style={styles.title}>{title}</Text>
      {subtitle ? <Text style={styles.subtitle}>{subtitle}</Text> : null}
      {actionLabel && onActionPress ? (
        <View style={styles.toolbar}>
          <TouchableOpacity
            style={[styles.actionButton, actionDisabled && styles.actionButtonDisabled]}
            onPress={onActionPress}
            disabled={actionDisabled}
          >
            <Text style={styles.actionButtonText}>{actionLabel}</Text>
          </TouchableOpacity>
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    marginBottom: 12,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 14,
    color: '#555',
    marginBottom: 12,
  },
  toolbar: {
    flexDirection: 'row',
  },
  actionButton: {
    backgroundColor: '#111827',
    borderRadius: 8,
    paddingHorizontal: 14,
    paddingVertical: 10,
  },
  actionButtonDisabled: {
    opacity: 0.6,
  },
  actionButtonText: {
    color: '#fff',
    fontSize: 13,
    fontWeight: '600',
  },
});
