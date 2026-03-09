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
import ScreenHeader from '../components/ScreenHeader';
import SegmentedControl from '../components/SegmentedControl';
import UICardList from '../components/UICardList';
import {
  getAgentTaskDetail,
  getAgentTasks,
  postAgentTaskControl,
} from '../api/client';
import {
  getActiveTasksScreenState,
  setActiveTasksScreenState,
} from '../storage/agentSurfaceStorage';
import { buildTaskLifecycleActionItems } from '../utils/agentCards';
import { applyTaskControlResponse } from '../utils/taskControlState';

const POLL_INTERVAL_MS = 5000;

function taskTimestamp(task) {
  return task.updated_at || task.created_at || '';
}

function compareTasksDesc(a, b) {
  return taskTimestamp(b).localeCompare(taskTimestamp(a));
}

function dedupeTasks(tasks) {
  const seen = new Set();
  return tasks.filter((task) => {
    if (!task?.id || seen.has(task.id)) {
      return false;
    }
    seen.add(task.id);
    return true;
  });
}

function buildTaskCard(task) {
  const lines = [];
  if (task.description) {
    lines.push(task.description);
  }
  if (task.provider) {
    lines.push(`Provider: ${task.provider}`);
  }
  if (task.result?.capability) {
    lines.push(`Capability: ${task.result.capability}`);
  }
  if (task.updated_at) {
    lines.push(`Updated: ${new Date(task.updated_at).toLocaleTimeString()}`);
  }

  const actionItems = [
    { id: 'mobile_refresh_task', label: 'Refresh Task', phrase: 'refresh this task' },
    { id: 'mobile_open_task_detail', label: 'Open Detail', phrase: 'open task detail' },
    ...buildTaskLifecycleActionItems(task),
  ];

  return {
    title: task.provider_label || task.provider || 'Agent Task',
    subtitle: `${task.state || 'unknown'}${task.result?.capability ? ` • ${task.result.capability}` : ''}`,
    lines,
    action_items: actionItems,
    task_id: task.id,
  };
}

export default function ActiveTasksScreen({ navigation }) {
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [backgroundRefreshing, setBackgroundRefreshing] = useState(false);
  const [error, setError] = useState(null);
  const [lastRefreshedAt, setLastRefreshedAt] = useState(null);
  const [selectedFilter, setSelectedFilter] = useState('all');

  const loadTasks = async ({ silent = false } = {}) => {
    if (silent) {
      setBackgroundRefreshing(true);
    } else {
      setLoading(true);
      setError(null);
    }

    try {
      const [createdData, runningData, needsInputData] = await Promise.all([
        getAgentTasks({
          status: 'created',
          sort: 'updated_at',
          direction: 'desc',
          limit: 20,
          result_view: 'normalized',
        }),
        getAgentTasks({
          status: 'running',
          sort: 'updated_at',
          direction: 'desc',
          limit: 20,
          result_view: 'normalized',
        }),
        getAgentTasks({
          status: 'needs_input',
          sort: 'updated_at',
          direction: 'desc',
          limit: 20,
          result_view: 'normalized',
        }),
      ]);

      const mergedTasks = dedupeTasks([
        ...(createdData.tasks || []),
        ...(runningData.tasks || []),
        ...(needsInputData.tasks || []),
      ]).sort(compareTasksDesc);

      setTasks(mergedTasks);
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

  useEffect(() => {
    (async () => {
      try {
        const savedState = await getActiveTasksScreenState();
        setSelectedFilter(savedState.filter);
      } catch (err) {
        console.error('Failed to load active tasks filter:', err);
      }
      await loadTasks({ silent: false });
    })().catch(() => {});
  }, []);

  useEffect(() => {
    setActiveTasksScreenState({ filter: selectedFilter }).catch((err) => {
      console.error('Failed to save active tasks filter:', err);
    });
  }, [selectedFilter]);

  useEffect(() => {
    const intervalId = setInterval(() => {
      loadTasks({ silent: true }).catch(() => {});
    }, POLL_INTERVAL_MS);

    return () => clearInterval(intervalId);
  }, []);

  const filteredTasks = tasks.filter((task) => {
    if (selectedFilter === 'running') {
      return task.state === 'running';
    }
    if (selectedFilter === 'paused') {
      return task.state === 'needs_input';
    }
    if (selectedFilter === 'created') {
      return task.state === 'created';
    }
    return true;
  });

  const cards = filteredTasks.map((task) => ({
    ...buildTaskCard(task),
    sync_hint: backgroundRefreshing ? 'Syncing active task state...' : 'Auto-refreshing every 5s',
    is_syncing: backgroundRefreshing,
  }));

  const refreshSingleTask = async (taskId) => {
    if (!taskId) {
      return;
    }

    try {
      const detail = await getAgentTaskDetail(taskId);
      setLastRefreshedAt(new Date().toISOString());
      setTasks((currentTasks) => {
        const updatedTasks = currentTasks
          .map((task) => (task.id === taskId ? { ...task, ...detail } : task))
          .filter((task) => ['created', 'running', 'needs_input'].includes(task.state))
          .sort(compareTasksDesc);
        return updatedTasks;
      });

      if (!['created', 'running', 'needs_input'].includes(detail.state)) {
        Alert.alert(
          'Task Updated',
          `Task is now ${detail.state}. You can open task detail to inspect the final result.`,
          [
            {
              text: 'Open Detail',
              onPress: () => navigation.navigate('TaskDetail', { taskId }),
            },
            { text: 'OK', style: 'cancel' },
          ]
        );
      }
    } catch (err) {
      Alert.alert('Refresh Failed', err.message);
    }
  };

  const applyTaskControlLocally = (response) => {
    setLastRefreshedAt(response.updated_at || new Date().toISOString());
    setTasks((currentTasks) =>
      currentTasks
        .map((task) => applyTaskControlResponse(task, response))
        .filter((task) => ['created', 'running', 'needs_input'].includes(task.state))
        .sort(compareTasksDesc)
    );
  };

  const handleTaskCardAction = async (actionItem, card) => {
    if (!card?.task_id) {
      return;
    }

    if (actionItem?.id === 'mobile_open_task_detail') {
      navigation.navigate('TaskDetail', { taskId: card.task_id });
      return;
    }

    if (actionItem?.id === 'mobile_refresh_task') {
      await refreshSingleTask(card.task_id);
      return;
    }

    if (actionItem?.id === 'mobile_pause_task') {
      try {
        const response = await postAgentTaskControl(card.task_id, 'pause');
        applyTaskControlLocally(response);
        await refreshSingleTask(card.task_id);
      } catch (err) {
        Alert.alert('Pause Failed', err.message);
      }
      return;
    }

    if (actionItem?.id === 'mobile_resume_task') {
      try {
        const response = await postAgentTaskControl(card.task_id, 'resume');
        applyTaskControlLocally(response);
        await refreshSingleTask(card.task_id);
      } catch (err) {
        Alert.alert('Resume Failed', err.message);
      }
      return;
    }

    if (actionItem?.id === 'mobile_cancel_task') {
      try {
        const response = await postAgentTaskControl(card.task_id, 'cancel');
        applyTaskControlLocally(response);
        await refreshSingleTask(card.task_id);
      } catch (err) {
        Alert.alert('Cancel Failed', err.message);
      }
    }
  };

  return (
    <ScrollView style={styles.container}>
      <ScreenHeader
        title="Active Tasks"
        subtitle="Track current MCP-backed work and jump straight into task detail."
        actionLabel={loading ? 'Refreshing...' : 'Refresh'}
        onActionPress={() => loadTasks({ silent: false })}
        actionDisabled={loading}
      />

      <SegmentedControl
        options={[
          { value: 'all', label: 'All' },
          { value: 'running', label: 'Running' },
          { value: 'paused', label: 'Paused' },
          { value: 'created', label: 'Queued' },
        ]}
        selectedValue={selectedFilter}
        onChange={setSelectedFilter}
        disabled={loading}
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

      {!loading && !error && cards.length === 0 ? (
        <EmptyStateCard
          title="No active tasks"
          message={
            selectedFilter === 'all'
              ? 'Created, running, and paused MCP tasks will appear here automatically.'
              : `No ${selectedFilter === 'created' ? 'queued' : selectedFilter} tasks right now.`
          }
        />
      ) : null}

      <UICardList
        cards={cards}
        title={cards.length > 0 ? 'Current Work:' : null}
        disabled={loading}
        onActionPress={handleTaskCardAction}
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
