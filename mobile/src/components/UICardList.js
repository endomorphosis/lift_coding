import React from 'react';
import {
  Alert,
  Linking,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';

async function openDeepLink(deepLink) {
  if (!deepLink) {
    return;
  }

  try {
    const supported = await Linking.canOpenURL(deepLink);
    if (!supported) {
      Alert.alert('Unsupported Link', deepLink);
      return;
    }
    await Linking.openURL(deepLink);
  } catch (err) {
    Alert.alert('Open Link Failed', err.message || 'Unable to open this link.');
  }
}

function UICardView({
  card,
  index,
  disabled = false,
  onActionPress = null,
  onCardPress = null,
  cardPressLabel = 'Open Details',
}) {
  const badgeToneStyle = {
    active: styles.cardBadgeActive,
    paused: styles.cardBadgePaused,
    success: styles.cardBadgeSuccess,
    danger: styles.cardBadgeDanger,
    neutral: styles.cardBadgeNeutral,
  }[card.status_tone || 'neutral'];

  return (
    <View style={styles.card}>
      <Text style={styles.cardTitle}>{card.title || `Card ${index + 1}`}</Text>
      {card.status_badge || card.timestamp_label || card.is_live ? (
        <View style={styles.cardMetaRow}>
          {card.status_badge ? (
            <View style={[styles.cardBadge, badgeToneStyle]}>
              <Text style={styles.cardBadgeText}>{card.status_badge}</Text>
            </View>
          ) : null}
          {card.is_live ? (
            <View style={styles.cardLivePill}>
              <View style={styles.cardLiveDot} />
              <Text style={styles.cardLiveText}>{card.live_label || 'Live'}</Text>
            </View>
          ) : null}
          {card.timestamp_label ? (
            <Text style={styles.cardTimestamp}>{card.timestamp_label}</Text>
          ) : null}
        </View>
      ) : null}
      {card.sync_hint ? (
        <View style={styles.cardSyncRow}>
          <View style={[styles.cardSyncDot, card.is_syncing && styles.cardSyncDotActive]} />
          <Text style={styles.cardSyncText}>{card.sync_hint}</Text>
        </View>
      ) : null}
      {card.subtitle ? <Text style={styles.cardSubtitle}>{card.subtitle}</Text> : null}
      {Array.isArray(card.lines)
        ? card.lines.map((line, lineIndex) => (
            <Text key={`${line}-${lineIndex}`} style={styles.cardLine}>
              {line}
            </Text>
          ))
        : null}
      {card.deep_link ? (
        <TouchableOpacity
          style={styles.cardLinkButton}
          onPress={() => openDeepLink(card.deep_link)}
          disabled={disabled}
        >
          <Text style={styles.cardLinkText}>Open Link</Text>
          <Text style={styles.cardLinkValue}>{card.deep_link}</Text>
        </TouchableOpacity>
      ) : null}
      {Array.isArray(card.action_items) && card.action_items.length > 0 ? (
        <View style={styles.cardActionsContainer}>
          {card.action_items.map((actionItem, actionIndex) => (
            <TouchableOpacity
              key={`${actionItem.id}-${actionIndex}`}
              style={[
                styles.cardActionButton,
                disabled && styles.cardActionButtonDisabled,
              ]}
              onPress={() => onActionPress?.(actionItem, card)}
              disabled={disabled}
            >
              <View style={styles.cardActionButtonInner}>
                <Text style={styles.cardActionButtonText}>
                  {actionItem.label || actionItem.phrase || actionItem.id}
                </Text>
                {actionItem.execution_mode_label ? (
                  <View style={styles.cardActionModePill}>
                    <Text style={styles.cardActionModePillText}>
                      {actionItem.execution_mode_label}
                    </Text>
                  </View>
                ) : null}
              </View>
            </TouchableOpacity>
          ))}
        </View>
      ) : null}
      {onCardPress ? (
        <TouchableOpacity
          style={[styles.cardOpenButton, disabled && styles.cardActionButtonDisabled]}
          onPress={() => onCardPress(card)}
          disabled={disabled}
        >
          <Text style={styles.cardOpenButtonText}>{cardPressLabel}</Text>
        </TouchableOpacity>
      ) : null}
    </View>
  );
}

export default function UICardList({
  cards,
  title = 'UI Cards:',
  disabled = false,
  onActionPress = null,
  onCardPress = null,
  cardPressLabel = 'Open Details',
}) {
  if (!cards || cards.length === 0) return null;

  return (
    <View style={styles.cardsContainer}>
      {title ? <Text style={styles.sectionTitle}>{title}</Text> : null}
      {cards.map((card, index) => (
        <UICardView
          key={`${card.title || 'card'}-${index}`}
          card={card}
          index={index}
          disabled={disabled}
          onActionPress={onActionPress}
          onCardPress={onCardPress}
          cardPressLabel={cardPressLabel}
        />
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  cardsContainer: {
    marginTop: 10,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 10,
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
  cardMetaRow: {
    flexDirection: 'row',
    alignItems: 'center',
    flexWrap: 'wrap',
    marginBottom: 6,
  },
  cardBadge: {
    borderRadius: 999,
    paddingHorizontal: 8,
    paddingVertical: 4,
    marginRight: 8,
    marginBottom: 2,
  },
  cardBadgeActive: {
    backgroundColor: '#dbeafe',
  },
  cardBadgePaused: {
    backgroundColor: '#fef3c7',
  },
  cardBadgeSuccess: {
    backgroundColor: '#dcfce7',
  },
  cardBadgeDanger: {
    backgroundColor: '#fee2e2',
  },
  cardBadgeNeutral: {
    backgroundColor: '#e5e7eb',
  },
  cardBadgeText: {
    fontSize: 11,
    fontWeight: '700',
    color: '#1f2937',
  },
  cardTimestamp: {
    fontSize: 12,
    color: '#6b7280',
    marginBottom: 2,
  },
  cardLivePill: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#ecfccb',
    borderRadius: 999,
    paddingHorizontal: 8,
    paddingVertical: 4,
    marginRight: 8,
    marginBottom: 2,
  },
  cardLiveDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: '#65a30d',
    marginRight: 6,
  },
  cardLiveText: {
    fontSize: 11,
    fontWeight: '700',
    color: '#3f6212',
  },
  cardSubtitle: {
    fontSize: 13,
    color: '#666',
    marginBottom: 5,
  },
  cardSyncRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 6,
  },
  cardSyncDot: {
    width: 7,
    height: 7,
    borderRadius: 3.5,
    backgroundColor: '#cbd5e1',
    marginRight: 6,
  },
  cardSyncDotActive: {
    backgroundColor: '#0284c7',
  },
  cardSyncText: {
    fontSize: 12,
    color: '#475569',
  },
  cardLine: {
    fontSize: 13,
    color: '#333',
    marginTop: 3,
  },
  cardLinkButton: {
    marginTop: 10,
    backgroundColor: '#eef6ff',
    borderRadius: 8,
    padding: 10,
  },
  cardLinkText: {
    fontSize: 12,
  cardActionButtonInner: {
    flexDirection: 'row',
    alignItems: 'center',
  },
    fontWeight: '600',
    color: '#007AFF',
    marginBottom: 4,
  },
  cardLinkValue: {
    fontSize: 12,
    color: '#007AFF',
  cardActionModePill: {
    marginLeft: 8,
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 999,
    backgroundColor: 'rgba(255, 255, 255, 0.22)',
  },
  cardActionModePillText: {
    color: '#fff',
    fontSize: 11,
    fontWeight: '700',
    textTransform: 'uppercase',
  },
  },
  cardActionsContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginTop: 10,
  },
  cardActionButton: {
    backgroundColor: '#007AFF',
    borderRadius: 999,
    paddingHorizontal: 12,
    paddingVertical: 8,
    marginRight: 8,
    marginBottom: 8,
  },
  cardActionButtonDisabled: {
    opacity: 0.6,
  },
  cardActionButtonText: {
    color: '#fff',
    fontSize: 12,
    fontWeight: '600',
  },
  cardOpenButton: {
    backgroundColor: '#111827',
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 10,
    marginTop: -2,
    marginBottom: 10,
  },
  cardOpenButtonText: {
    color: '#fff',
    fontSize: 13,
    fontWeight: '600',
    textAlign: 'center',
  },
});
