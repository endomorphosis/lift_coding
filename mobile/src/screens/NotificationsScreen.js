import React, { useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';

import RefreshStatusCard from '../components/RefreshStatusCard';
import EmptyStateCard from '../components/EmptyStateCard';
import InfoCard from '../components/InfoCard';
import ScreenHeader from '../components/ScreenHeader';
import SegmentedControl from '../components/SegmentedControl';
import UICardList from '../components/UICardList';
import {
  getAgentTaskDetail,
  getNotificationDetail,
  getNotifications,
  postAgentTaskControl,
} from '../api/client';
import {
  getNotificationsScreenState,
  setNotificationsScreenState,
} from '../storage/agentSurfaceStorage';
import { getProfile } from '../storage/profileStorage';
import { buildLastActionLines, executeStructuredAction } from '../utils/agentActions';
import { buildAgentNotificationCard } from '../utils/agentCards';
import {
  buildNotificationPreview,
  isActiveTaskNotification,
  mergeNotificationTaskDetail,
} from '../utils/notificationCards';
import { shouldClearLastActionFromNotifications } from '../utils/lastActionState';
import { applyNotificationTaskControlResponse } from '../utils/taskControlState';

const POLL_INTERVAL_MS = 10000;

export default function NotificationsScreen({ navigation }) {
  const [currentProfile, setCurrentProfile] = useState('default');
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [backgroundRefreshing, setBackgroundRefreshing] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState(null);
  const [lastRefreshedAt, setLastRefreshedAt] = useState(null);
  const [selectedFilter, setSelectedFilter] = useState('all');
  const [lastAction, setLastAction] = useState(null);

  const refreshActiveNotificationTasks = async (items) => {
    const activeItems = (items || []).filter(isActiveTaskNotification);
    if (activeItems.length === 0) {
      return items || [];
    }

    const taskDetails = await Promise.all(
      activeItems.map(async (item) => {
        const taskId = item?.metadata?.task_id || item?.card?.task_id;
        if (!taskId) {
          return null;
        }
        try {
          return {
            notificationId: item.id,
            taskDetail: await getAgentTaskDetail(taskId),
          };
        } catch (err) {
          return null;
        }
      })
    );

    const taskDetailsByNotificationId = new Map(
      taskDetails.filter(Boolean).map((entry) => [entry.notificationId, entry.taskDetail])
    );

    return (items || []).map((item) => {
      const taskDetail = taskDetailsByNotificationId.get(item.id);
      return taskDetail ? mergeNotificationTaskDetail(item, taskDetail) : item;
    });
  };

  const loadNotifications = async ({ silent = false } = {}) => {
    if (silent) {
      setBackgroundRefreshing(true);
    } else {
      setLoading(true);
      setError(null);
    }

    try {
      const data = await getNotifications({ limit: 20 });
      let items = Array.isArray(data.notifications)
        ? data.notifications.map(buildNotificationPreview)
        : [];
      items = await refreshActiveNotificationTasks(items);
      setNotifications(items);
      setLastRefreshedAt(new Date().toISOString());
    } catch (err) {
      setError(err.message);
    } finally {
      if (silent) {
        setBackgroundRefreshing(false);
      } else {
        setLoading(false);
      }
    }
  };

  const loadNotificationDetail = async (notificationId) => {
    if (!notificationId) {
      return null;
    }
    try {
      const detail = await getNotificationDetail(notificationId);
      let normalized = buildNotificationPreview(detail);
      if (isActiveTaskNotification(normalized)) {
        const taskId = normalized?.metadata?.task_id || normalized?.card?.task_id;
        if (taskId) {
          try {
            const taskDetail = await getAgentTaskDetail(taskId);
            normalized = mergeNotificationTaskDetail(normalized, taskDetail);
          } catch (taskErr) {
            // Keep the notification payload if task detail refresh fails.
          }
        }
      }
      setNotifications((current) =>
        current.map((item) => (item.id === notificationId ? normalized : item))
      );
      return normalized;
    } catch (err) {
      console.log('Could not load notification detail:', err.message);
      return null;
    }
  };

  useEffect(() => {
    (async () => {
      try {
        const profile = await getProfile();
        setCurrentProfile(profile);
      } catch (err) {
        console.error('Failed to load profile:', err);
      }
      try {
        const savedState = await getNotificationsScreenState();
        setSelectedFilter(savedState.filter);
        setLastAction(savedState.lastAction || null);
      } catch (err) {
        console.error('Failed to load notifications filter:', err);
      }
      await loadNotifications({ silent: false });
    })();
  }, []);

  useEffect(() => {
    setNotificationsScreenState({ filter: selectedFilter, lastAction }).catch((err) => {
      console.error('Failed to save notifications filter:', err);
    });
  }, [lastAction, selectedFilter]);

  useEffect(() => {
    if (!shouldClearLastActionFromNotifications(lastAction, notifications)) {
      return;
    }

    setLastAction(null);
  }, [lastAction, notifications]);

  useEffect(() => {
    const intervalId = setInterval(() => {
      loadNotifications({ silent: true }).catch(() => {});
    }, POLL_INTERVAL_MS);

    return () => clearInterval(intervalId);
  }, []);

  const handleNotificationAction = async (actionItem, card) => {
    const notificationId = card?.notification_id;
    const taskId = card?.task_id;
    if (!actionItem?.id || !notificationId) {
      Alert.alert('Action Unavailable', 'This notification action is missing context.');
      return;
    }

    setActionLoading(true);
    try {
      if (actionItem.id === 'mobile_pause_task' && taskId) {
        const response = await postAgentTaskControl(taskId, 'pause');
        setNotifications((current) =>
          current.map((item) =>
            item.id === notificationId ? applyNotificationTaskControlResponse(item, response) : item
          )
        );
        Alert.alert('Task Paused', response.message || 'Task paused successfully.');
        return;
      }
      if (actionItem.id === 'mobile_resume_task' && taskId) {
        const response = await postAgentTaskControl(taskId, 'resume');
        setNotifications((current) =>
          current.map((item) =>
            item.id === notificationId ? applyNotificationTaskControlResponse(item, response) : item
          )
        );
        Alert.alert('Task Resumed', response.message || 'Task resumed successfully.');
        return;
      }
      if (actionItem.id === 'mobile_cancel_task' && taskId) {
        const response = await postAgentTaskControl(taskId, 'cancel');
        setNotifications((current) =>
          current.map((item) =>
            item.id === notificationId ? applyNotificationTaskControlResponse(item, response) : item
          )
        );
        Alert.alert('Task Cancelled', response.message || 'Task cancelled successfully.');
        return;
      }

      const outcome = await executeStructuredAction({
        actionItem,
        profile: currentProfile,
        baseParams: {
          notification_id: notificationId,
        },
      });

      if (outcome.kind === 'pending_confirmation') {
        setLastAction({
          actionId: actionItem.id,
          message: outcome.message,
          status: 'pending_confirmation',
          taskUpdate: outcome.taskUpdate || null,
        });
        Alert.alert('Confirmation Required', outcome.message);
      } else {
        setLastAction({
          actionId: actionItem.id,
          message: outcome.message,
          status: 'completed',
          taskUpdate: outcome.taskUpdate || null,
        });
        Alert.alert('Action Complete', outcome.message, [
          outcome.taskUpdate?.task_id
            ? {
                text: 'Open Task Detail',
                onPress: () =>
                  navigation.navigate('TaskDetail', { taskId: outcome.taskUpdate.task_id }),
              }
            : null,
          { text: 'OK', style: 'cancel' },
        ].filter(Boolean));
      }

      await loadNotificationDetail(notificationId);
    } catch (err) {
      Alert.alert('Error', `Failed to run notification action: ${err.message}`);
    } finally {
      setActionLoading(false);
    }
  };

  const filteredNotifications = notifications.filter((notification) => {
    if (selectedFilter === 'tasks') {
      return Boolean(notification?.metadata?.task_id || notification?.card?.task_id);
    }
    if (selectedFilter === 'active') {
      return isActiveTaskNotification(notification);
    }
    return true;
  });

  const cards = filteredNotifications.map((notification) => ({
    ...buildAgentNotificationCard(notification),
    sync_hint: isActiveTaskNotification(notification)
      ? backgroundRefreshing
        ? 'Syncing linked task...'
        : 'Watching linked task status'
      : null,
    is_syncing: backgroundRefreshing && isActiveTaskNotification(notification),
  }));

  return (
    <ScrollView style={styles.container}>
      <ScreenHeader
        title="Notifications"
        subtitle="Browse recent notifications, inspect MCP completions, and run follow-up actions."
        actionLabel={loading ? 'Refreshing...' : 'Refresh'}
        onActionPress={() => loadNotifications({ silent: false })}
        actionDisabled={loading || actionLoading}
      />

      <SegmentedControl
        options={[
          { value: 'all', label: 'All' },
          { value: 'tasks', label: 'Tasks' },
          { value: 'active', label: 'Active Tasks' },
        ]}
        selectedValue={selectedFilter}
        onChange={setSelectedFilter}
        disabled={loading || actionLoading}
      />

      <RefreshStatusCard
        intervalSeconds={POLL_INTERVAL_MS / 1000}
        backgroundRefreshing={backgroundRefreshing}
        lastRefreshedAt={lastRefreshedAt}
      />

      {loading ? <ActivityIndicator size="large" color="#007AFF" style={styles.loader} /> : null}

      {error ? (
        <View style={styles.errorCard}>
          <Text style={styles.errorText}>{error}</Text>
        </View>
      ) : null}

      {lastAction?.message ? (
        <InfoCard
          title="Last Action"
          tone="warning"
          accent={lastAction.status || 'completed'}
          lines={buildLastActionLines(lastAction)}
          actionLabel={lastAction.taskUpdate?.task_id ? 'Open Task Detail' : null}
          onActionPress={
            lastAction.taskUpdate?.task_id
              ? () => {
                  const nextTaskId = lastAction.taskUpdate.task_id;
                  setLastAction(null);
                  navigation.navigate('TaskDetail', { taskId: nextTaskId });
                }
              : null
          }
        />
      ) : null}

      {!loading && !error && cards.length === 0 ? (
        <EmptyStateCard
          title="No notifications yet"
          message={
            selectedFilter === 'all'
              ? 'Push and webhook-backed notifications will show up here automatically.'
              : selectedFilter === 'tasks'
                ? 'No task-linked notifications right now.'
                : 'No active task notifications right now.'
          }
        />
      ) : null}

      <UICardList
        cards={cards}
        title={cards.length > 0 ? 'Recent Notifications:' : null}
        disabled={loading || actionLoading}
        onActionPress={handleNotificationAction}
        onCardPress={(card) => {
          if (!card.task_id) return;
          navigation.navigate('TaskDetail', { taskId: card.task_id });
        }}
        cardPressLabel="Open Task Detail"
      />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 20,
    backgroundColor: '#f5f5f5',
  },
  loader: {
    marginTop: 24,
  },
  errorCard: {
    backgroundColor: '#ffebee',
    borderRadius: 10,
    padding: 16,
  },
  errorText: {
    color: '#c62828',
    fontSize: 14,
  },
});
