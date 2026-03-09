import { AppState } from 'react-native';
import { useEffect, useMemo, useRef, useState } from 'react';

import {
  deleteDevTransportSession,
  getDevPeerChatConversations,
  getDevPeerChatHandsetSession,
  getDevPeerChatHistory,
  getDevPeerChatOutboxStatus,
  getDevTransportSessions,
  postDevPeerChatHandsetHeartbeat,
  postDevPeerChatOutboxPromote,
  postDevPeerChatOutboxRelease,
  postDevPeerChatSend,
} from '../api/client';
import {
  getOutboxMessageIdsByState,
  getSelectedOutboxPreview,
  normalizePeerChatOutboxSummary,
  selectNextOutboxMessageId,
} from '../utils/peerChatOutbox';
import {
  normalizePeerChatConversations,
  selectNextConversation,
} from '../utils/peerChatConversations';
import {
  getBackendSentChatEvent,
  getLoadedChatHistoryEvent,
  getLoadedConversationsEvent,
  getNoHeldMessagesEvent,
  getNoLeasedMessagesEvent,
  getPromotedOutboxMessagesEvent,
  getRefreshedAllPeerChatDiagnosticsEvent,
  getRefreshedOutboxStatusEvent,
  getReleasedOutboxMessagesEvent,
  getSelectConversationEvent,
} from '../utils/peerChatEvents';
import {
  getPeerChatRecommendedPollMs,
  normalizePeerChatHandsetSession,
} from '../utils/peerChatSession';
import { getOrCreateLocalPeerId } from '../utils/localPeerIdentity';

const PEER_TEST_PAYLOAD = 'ping';

export function usePeerChatDiagnostics() {
  const [localPeerId, setLocalPeerId] = useState('loading');
  const [lastEvent, setLastEvent] = useState('No peer chat activity yet');
  const [lastError, setLastError] = useState(null);
  const [peerChatConversations, setPeerChatConversations] = useState([]);
  const [isLoadingPeerChatConversations, setIsLoadingPeerChatConversations] = useState(false);
  const [selectedConversation, setSelectedConversation] = useState(null);
  const [peerChatHistory, setPeerChatHistory] = useState(null);
  const [isLoadingPeerChatHistory, setIsLoadingPeerChatHistory] = useState(false);
  const [peerChatOutboxSummary, setPeerChatOutboxSummary] = useState(null);
  const [selectedOutboxMessageId, setSelectedOutboxMessageId] = useState(null);
  const [isFetchingPeerChatOutbox, setIsFetchingPeerChatOutbox] = useState(false);
  const [isSendingPeerChatViaBackend, setIsSendingPeerChatViaBackend] = useState(false);
  const [isRefreshingAllPeerChatDiagnostics, setIsRefreshingAllPeerChatDiagnostics] = useState(false);
  const [peerChatHandsetSession, setPeerChatHandsetSession] = useState(null);
  const [transportSessions, setTransportSessions] = useState([]);
  const [isLoadingTransportSessions, setIsLoadingTransportSessions] = useState(false);
  const [isClearingTransportSession, setIsClearingTransportSession] = useState(false);
  const [recommendedOutboxPollMs, setRecommendedOutboxPollMs] = useState(4000);
  const [lastSyncedAt, setLastSyncedAt] = useState(null);
  const appIsActiveRef = useRef(AppState.currentState === 'active');

  const applyPeerChatOutboxSummary = (response) => {
    const nextSummary = normalizePeerChatOutboxSummary(response);
    setPeerChatOutboxSummary(nextSummary);
    setSelectedOutboxMessageId((current) => selectNextOutboxMessageId(nextSummary, current));
  };

  const bootstrapPeerChatDiagnostics = async (peerId, { refreshSession = true } = {}) => {
    const [conversationsResponse, outboxResponse, transportSessionsResponse] = await Promise.all([
      getDevPeerChatConversations(10),
      getDevPeerChatOutboxStatus(peerId),
      getDevTransportSessions(),
    ]);

    const conversations = normalizePeerChatConversations(conversationsResponse);
    setPeerChatConversations(conversations);
    setSelectedConversation((current) => selectNextConversation(conversations, current));

    applyPeerChatOutboxSummary(outboxResponse);
    setRecommendedOutboxPollMs(getPeerChatRecommendedPollMs(outboxResponse));
    setTransportSessions(Array.isArray(transportSessionsResponse?.sessions) ? transportSessionsResponse.sessions : []);

    if (!refreshSession) {
      setLastSyncedAt(Date.now());
      return;
    }

    try {
      const session = await getDevPeerChatHandsetSession(peerId);
      setPeerChatHandsetSession(normalizePeerChatHandsetSession(session));
    } catch {
      // keep bootstrap best-effort
    }
    setLastSyncedAt(Date.now());
  };

  useEffect(() => {
    const appStateSubscription = AppState.addEventListener('change', (nextAppState) => {
      appIsActiveRef.current = nextAppState === 'active';
    });

    return () => {
      appStateSubscription.remove();
    };
  }, []);

  useEffect(() => {
    (async () => {
      try {
        const resolvedLocalPeerId = await getOrCreateLocalPeerId();
        setLocalPeerId(resolvedLocalPeerId);
      } catch (error) {
        setLastError(`Local peer identity failed: ${error.message}`);
      }
    })();
  }, []);

  useEffect(() => {
    if (!localPeerId || localPeerId === 'loading') {
      return;
    }

    let cancelled = false;
    const heartbeat = async () => {
      if (cancelled || !appIsActiveRef.current) {
        return;
      }
      try {
        const session = await postDevPeerChatHandsetHeartbeat(localPeerId, 'HandsFree Peer Chat');
        if (!cancelled) {
          const normalizedSession = normalizePeerChatHandsetSession(session);
          setPeerChatHandsetSession(normalizedSession);
          setRecommendedOutboxPollMs(getPeerChatRecommendedPollMs(normalizedSession));
        }
      } catch {
        // Keep the screen usable without a live backend.
      }
    };

    heartbeat().catch(() => {});
    const interval = setInterval(() => {
      heartbeat().catch(() => {});
    }, 10000);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [localPeerId]);

  const loadRecentPeerChatConversations = async () => {
    try {
      setLastError(null);
      setIsLoadingPeerChatConversations(true);
      const response = await getDevPeerChatConversations(10);
      const conversations = normalizePeerChatConversations(response);
      setPeerChatConversations(conversations);
      setSelectedConversation((current) => selectNextConversation(conversations, current));
      setLastEvent(getLoadedConversationsEvent());
    } catch (error) {
      setLastError(`Load chat conversations failed: ${error.message}`);
    } finally {
      setIsLoadingPeerChatConversations(false);
    }
  };

  const refreshAllPeerChatDiagnostics = async () => {
    try {
      setLastError(null);
      if (!localPeerId || localPeerId === 'loading') {
        return;
      }
      setIsRefreshingAllPeerChatDiagnostics(true);
      await bootstrapPeerChatDiagnostics(localPeerId, { refreshSession: true });
      setLastEvent(getRefreshedAllPeerChatDiagnosticsEvent());
    } catch (error) {
      setLastError(`Refresh peer chat diagnostics failed: ${error.message}`);
    } finally {
      setIsRefreshingAllPeerChatDiagnostics(false);
    }
  };

  const loadPeerChatHistory = async () => {
    try {
      setLastError(null);
      if (!selectedConversation?.conversation_id) {
        setLastEvent(getSelectConversationEvent());
        return;
      }
      setIsLoadingPeerChatHistory(true);
      const history = await getDevPeerChatHistory(selectedConversation.conversation_id);
      setPeerChatHistory(history);
      setLastEvent(getLoadedChatHistoryEvent(selectedConversation.conversation_id));
    } catch (error) {
      setLastError(`Load chat history failed: ${error.message}`);
    } finally {
      setIsLoadingPeerChatHistory(false);
    }
  };

  const refreshPeerChatOutboxStatus = async () => {
    try {
      setLastError(null);
      setIsFetchingPeerChatOutbox(true);
      const response = await getDevPeerChatOutboxStatus(localPeerId);
      applyPeerChatOutboxSummary(response);
      setRecommendedOutboxPollMs(getPeerChatRecommendedPollMs(response));
      try {
        const session = await getDevPeerChatHandsetSession(localPeerId);
        setPeerChatHandsetSession(normalizePeerChatHandsetSession(session));
      } catch {
        // ignore
      }
      setLastEvent(getRefreshedOutboxStatusEvent(response.delivery_mode));
    } catch (error) {
      setLastError(`Refresh backend outbox status failed: ${error.message}`);
    } finally {
      setIsFetchingPeerChatOutbox(false);
    }
  };

  const loadTransportSessions = async () => {
    try {
      setLastError(null);
      setIsLoadingTransportSessions(true);
      const response = await getDevTransportSessions();
      setTransportSessions(Array.isArray(response?.sessions) ? response.sessions : []);
      setLastEvent('Loaded transport session cursors');
    } catch (error) {
      setLastError(`Load transport sessions failed: ${error.message}`);
    } finally {
      setIsLoadingTransportSessions(false);
    }
  };

  const clearTransportSession = async (peerId) => {
    try {
      setLastError(null);
      setIsClearingTransportSession(true);
      const response = await deleteDevTransportSession(peerId);
      setTransportSessions((current) => current.filter((session) => session.peer_id !== peerId));
      setLastEvent(response?.cleared ? `Cleared transport session for ${peerId}` : `No transport session found for ${peerId}`);
    } catch (error) {
      setLastError(`Clear transport session failed: ${error.message}`);
    } finally {
      setIsClearingTransportSession(false);
    }
  };

  useEffect(() => {
    if (!localPeerId || localPeerId === 'loading') {
      return;
    }

    let cancelled = false;
    bootstrapPeerChatDiagnostics(localPeerId).catch(() => {
      // keep the screen usable when the backend is unavailable
    });

    return () => {
      cancelled = true;
    };
  }, [localPeerId]);

  useEffect(() => {
    if (!localPeerId || localPeerId === 'loading') {
      return;
    }

    const appStateSubscription = AppState.addEventListener('change', (nextAppState) => {
      const isActive = nextAppState === 'active';
      appIsActiveRef.current = isActive;
      if (!isActive) {
        return;
      }

      bootstrapPeerChatDiagnostics(localPeerId, { refreshSession: true }).catch(() => {
        // keep foreground refresh best-effort
      });
    });

    return () => {
      appStateSubscription.remove();
    };
  }, [localPeerId]);

  const sendPeerChatViaBackend = async (priority = 'normal') => {
    try {
      setLastError(null);
      if (!selectedConversation?.peer_id) {
        setLastEvent(getSelectConversationEvent());
        return;
      }
      setIsSendingPeerChatViaBackend(true);
      const response = await postDevPeerChatSend(
        selectedConversation.peer_id,
        `backend-ping:${PEER_TEST_PAYLOAD}`,
        selectedConversation.conversation_id,
        priority
      );
      setLastEvent(getBackendSentChatEvent(response.priority, response.peer_id));
      const history = await getDevPeerChatHistory(response.conversation_id);
      setPeerChatHistory(history);
      await refreshPeerChatOutboxStatus();
    } catch (error) {
      setLastError(`Backend chat send failed: ${error.message}`);
    } finally {
      setIsSendingPeerChatViaBackend(false);
    }
  };

  const releasePeerChatOutboxMessages = async (outboxMessageIds) => {
    try {
      setLastError(null);
      if (!outboxMessageIds.length) {
        setLastEvent(getNoLeasedMessagesEvent());
        return;
      }
      const response = await postDevPeerChatOutboxRelease(localPeerId, outboxMessageIds);
      await refreshPeerChatOutboxStatus();
      setLastEvent(getReleasedOutboxMessagesEvent(response.released_message_ids.length));
    } catch (error) {
      setLastError(`Release backend outbox leases failed: ${error.message}`);
    }
  };

  const promotePeerChatOutboxMessages = async (outboxMessageIds) => {
    try {
      setLastError(null);
      if (!outboxMessageIds.length) {
        setLastEvent(getNoHeldMessagesEvent());
        return;
      }
      const response = await postDevPeerChatOutboxPromote(localPeerId, outboxMessageIds);
      await refreshPeerChatOutboxStatus();
      setLastEvent(getPromotedOutboxMessagesEvent(response.promoted_message_ids.length));
    } catch (error) {
      setLastError(`Promote backend outbox messages failed: ${error.message}`);
    }
  };

  const releaseLeasedPeerChatOutboxMessages = async () => {
    const leasedMessageIds = getOutboxMessageIdsByState(peerChatOutboxSummary, 'leased');
    await releasePeerChatOutboxMessages(leasedMessageIds);
  };

  const promoteHeldPeerChatOutboxMessages = async () => {
    const heldMessageIds = getOutboxMessageIdsByState(peerChatOutboxSummary, 'held_by_policy');
    await promotePeerChatOutboxMessages(heldMessageIds);
  };

  const selectedOutboxPreview = useMemo(
    () => getSelectedOutboxPreview(peerChatOutboxSummary, selectedOutboxMessageId),
    [peerChatOutboxSummary, selectedOutboxMessageId]
  );

  return {
    localPeerId,
    lastEvent,
    lastError,
    peerChatConversations,
    isLoadingPeerChatConversations,
    selectedConversation,
    setSelectedConversation,
    peerChatHistory,
    isLoadingPeerChatHistory,
    peerChatOutboxSummary,
    selectedOutboxMessageId,
    setSelectedOutboxMessageId,
    selectedOutboxPreview,
    isFetchingPeerChatOutbox,
    isSendingPeerChatViaBackend,
    isRefreshingAllPeerChatDiagnostics,
    peerChatHandsetSession,
    transportSessions,
    isLoadingTransportSessions,
    isClearingTransportSession,
    recommendedOutboxPollMs,
    lastSyncedAt,
    refreshAllPeerChatDiagnostics,
    loadRecentPeerChatConversations,
    loadPeerChatHistory,
    refreshPeerChatOutboxStatus,
    loadTransportSessions,
    clearTransportSession,
    sendPeerChatViaBackend,
    releaseLeasedPeerChatOutboxMessages,
    promoteHeldPeerChatOutboxMessages,
    releasePeerChatOutboxMessages,
    promotePeerChatOutboxMessages,
  };
}
