import React from 'react';
import { ScrollView, StyleSheet, Text, View } from 'react-native';

import PeerChatDiagnosticsPanel from '../components/PeerChatDiagnosticsPanel';
import { useNowTicker } from '../hooks/useNowTicker';
import { usePeerChatDiagnostics } from '../hooks/usePeerChatDiagnostics';
import { formatPeerChatSessionLabel } from '../utils/peerChatSession';
import { formatPeerChatLastSynced, getPeerChatSyncHealth } from '../utils/peerChatSyncStatus';

export default function PeerChatDiagnosticsScreen() {
  const diagnostics = usePeerChatDiagnostics();
  const syncStatusNow = useNowTicker(1000);
  const syncHealth = getPeerChatSyncHealth(diagnostics.lastSyncedAt, syncStatusNow);
  const transportSessions = diagnostics.transportSessions || [];

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <View style={styles.card}>
        <Text style={styles.title}>Peer Chat Diagnostics</Text>
        <Text style={styles.text}>Local peer ID: {diagnostics.localPeerId}</Text>
        <Text style={styles.text}>
          Session: {formatPeerChatSessionLabel(diagnostics.peerChatHandsetSession)}
        </Text>
        <Text style={styles.text}>Recommended poll: {diagnostics.recommendedOutboxPollMs}ms</Text>
        <Text style={styles.text}>
          Selected conversation: {diagnostics.selectedConversation?.conversation_id || 'none'}
        </Text>
        <Text style={styles.text}>Transport sessions: {transportSessions.length}</Text>
        <Text style={styles.text}>
          Last synced: {formatPeerChatLastSynced(diagnostics.lastSyncedAt, syncStatusNow)}
        </Text>
        <Text style={styles.text}>Sync health: {syncHealth}</Text>
        <Text style={styles.text}>Last event: {diagnostics.lastEvent}</Text>
        {diagnostics.lastError ? <Text style={styles.errorText}>Error: {diagnostics.lastError}</Text> : null}
      </View>

      <PeerChatDiagnosticsPanel
        headerText="Backend-focused peer chat controls using the shared handset peer identity."
        onRefreshAll={diagnostics.refreshAllPeerChatDiagnostics}
        isRefreshingAll={diagnostics.isRefreshingAllPeerChatDiagnostics}
        isLoadingPeerChatHistory={diagnostics.isLoadingPeerChatHistory}
        onLoadPeerChatHistory={diagnostics.loadPeerChatHistory}
        isLoadingPeerChatConversations={diagnostics.isLoadingPeerChatConversations}
        onLoadRecentPeerChatConversations={diagnostics.loadRecentPeerChatConversations}
        isSendingPeerChatViaBackend={diagnostics.isSendingPeerChatViaBackend}
        onSendNormalPeerChat={() => diagnostics.sendPeerChatViaBackend('normal')}
        onSendUrgentPeerChat={() => diagnostics.sendPeerChatViaBackend('urgent')}
        isFetchingPeerChatOutbox={diagnostics.isFetchingPeerChatOutbox}
        onRefreshOutboxStatus={diagnostics.refreshPeerChatOutboxStatus}
        onReleaseLeasedMessages={diagnostics.releaseLeasedPeerChatOutboxMessages}
        onPromoteHeldMessages={diagnostics.promoteHeldPeerChatOutboxMessages}
        peerChatOutboxSummary={diagnostics.peerChatOutboxSummary}
        selectedOutboxPreview={diagnostics.selectedOutboxPreview}
        onSelectOutboxMessage={diagnostics.setSelectedOutboxMessageId}
        onReleaseOutboxMessage={(outboxMessageId) => diagnostics.releasePeerChatOutboxMessages([outboxMessageId])}
        onPromoteOutboxMessage={(outboxMessageId) => diagnostics.promotePeerChatOutboxMessages([outboxMessageId])}
        peerChatHistory={diagnostics.peerChatHistory}
        peerChatConversations={diagnostics.peerChatConversations}
        selectedConversationId={diagnostics.selectedConversation?.conversation_id}
        onSelectConversation={diagnostics.setSelectedConversation}
        transportSessions={transportSessions}
        isLoadingTransportSessions={diagnostics.isLoadingTransportSessions}
        isClearingTransportSession={diagnostics.isClearingTransportSession}
        onLoadTransportSessions={diagnostics.loadTransportSessions}
        onClearTransportSession={diagnostics.clearTransportSession}
      />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f3f4f6',
  },
  content: {
    padding: 16,
  },
  card: {
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
    fontSize: 18,
    fontWeight: '700',
    color: '#111827',
    marginBottom: 10,
  },
  text: {
    fontSize: 14,
    color: '#374151',
    marginBottom: 6,
  },
  errorText: {
    fontSize: 14,
    color: '#b91c1c',
    marginTop: 8,
  },
});
