import React from 'react';
import { StyleSheet, Text, TouchableOpacity, View } from 'react-native';

export default function InfoCard({
  title,
  lines = [],
  tone = 'neutral',
  accent = null,
  actionLabel = null,
  onActionPress = null,
}) {
  if (!title && (!Array.isArray(lines) || lines.length === 0)) {
    return null;
  }

  const toneStyles = {
    neutral: [styles.card, styles.cardNeutral],
    info: [styles.card, styles.cardInfo],
    warning: [styles.card, styles.cardWarning],
    danger: [styles.card, styles.cardDanger],
  }[tone] || [styles.card, styles.cardNeutral];

  return (
    <View style={toneStyles}>
      {title ? <Text style={styles.title}>{title}</Text> : null}
      {accent ? <Text style={styles.accent}>{accent}</Text> : null}
      {Array.isArray(lines)
        ? lines.map((line, index) => (
            <Text key={`${line}-${index}`} style={styles.line}>
              {line}
            </Text>
          ))
        : null}
      {actionLabel && typeof onActionPress === 'function' ? (
        <TouchableOpacity style={styles.actionButton} onPress={onActionPress}>
          <Text style={styles.actionText}>{actionLabel}</Text>
        </TouchableOpacity>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    borderRadius: 10,
    padding: 12,
    marginBottom: 12,
  },
  cardNeutral: {
    backgroundColor: '#fff',
  },
  cardInfo: {
    backgroundColor: '#eef6ff',
  },
  cardWarning: {
    backgroundColor: '#fff7e6',
  },
  cardDanger: {
    backgroundColor: '#ffebee',
  },
  title: {
    fontSize: 16,
    fontWeight: 'bold',
    marginBottom: 6,
    color: '#1f2937',
  },
  accent: {
    fontSize: 12,
    color: '#92400e',
    textTransform: 'uppercase',
    marginBottom: 4,
  },
  line: {
    fontSize: 13,
    color: '#374151',
    marginTop: 2,
  },
  actionButton: {
    marginTop: 10,
    alignSelf: 'flex-start',
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 8,
    backgroundColor: '#dbeafe',
  },
  actionText: {
    fontSize: 13,
    fontWeight: '600',
    color: '#1d4ed8',
  },
});
