import React, { useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';

import ActionPromptModal from '../components/ActionPromptModal';
import InfoCard from '../components/InfoCard';
import RefreshStatusCard from '../components/RefreshStatusCard';
import ScreenHeader from '../components/ScreenHeader';
import UICardList from '../components/UICardList';
import { getAgentTaskDetail, postAgentTaskControl } from '../api/client';
import { getProfile } from '../storage/profileStorage';
import {
  getTaskDetailScreenState,
  setTaskDetailScreenState,
} from '../storage/taskDetailStorage';
import {
  buildLastActionLines,
  buildPromptDraft,
  executeLocalStructuredAction,
  executeStructuredAction,
} from '../utils/agentActions';
import { buildAgentTaskCard } from '../utils/agentCards';
import { shouldClearLastActionFromTaskDetail } from '../utils/lastActionState';
import { applyTaskControlResponse } from '../utils/taskControlState';

export default function TaskDetailScreen({ route }) {
  const POLL_INTERVAL_MS = 5000;
  const taskId = route?.params?.taskId;
  const [task, setTask] = useState(null);
  const [loading, setLoading] = useState(Boolean(taskId));
  const [backgroundRefreshing, setBackgroundRefreshing] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState(null);
  const [currentProfile, setCurrentProfile] = useState('default');
  const [promptAction, setPromptAction] = useState(null);
  const [promptValue, setPromptValue] = useState('');
  const [isPolling, setIsPolling] = useState(false);
  const [lastRefreshedAt, setLastRefreshedAt] = useState(null);
  const [lastAction, setLastAction] = useState(null);

  const shouldPollTask = (taskState) => {
    return taskState === 'created' || taskState === 'running';
  };

  const loadTask = async ({ silent = false } = {}) => {
    if (!taskId) {
      setError('No task selected.');
      setLoading(false);
      setBackgroundRefreshing(false);
      return;
    }

    if (silent) {
      setBackgroundRefreshing(true);
    } else {
      setLoading(true);
      setError(null);
    }
    try {
      const data = await getAgentTaskDetail(taskId);
      setTask(data);
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
        const profile = await getProfile();
        setCurrentProfile(profile);
      } catch (err) {
        console.error('Failed to load profile:', err);
      }
      try {
        const savedState = await getTaskDetailScreenState(taskId);
        setLastAction(savedState.lastAction || null);
      } catch (err) {
        console.error('Failed to load task detail state:', err);
      }
      await loadTask({ silent: false });
    })();
  }, [taskId]);

  useEffect(() => {
    setTaskDetailScreenState(taskId, { lastAction }).catch((err) => {
      console.error('Failed to save task detail state:', err);
    });
  }, [lastAction, taskId]);

  useEffect(() => {
    const followOnTaskId = lastAction?.taskUpdate?.task_id;
    if (!followOnTaskId || followOnTaskId === taskId) {
      return;
    }

    let cancelled = false;
    (async () => {
      try {
        const detail = await getAgentTaskDetail(followOnTaskId);
        if (!cancelled && shouldClearLastActionFromTaskDetail(lastAction, taskId, detail)) {
          setLastAction(null);
        }
      } catch (err) {
        // Ignore spawned-task lookup failures and keep the shortcut visible.
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [lastAction, taskId]);

  useEffect(() => {
    if (!taskId || !shouldPollTask(task?.state) || actionLoading || promptAction) {
      setIsPolling(false);
      return;
    }

    setIsPolling(true);
    const intervalId = setInterval(() => {
      loadTask({ silent: true }).catch(() => {});
    }, POLL_INTERVAL_MS);

    return () => {
      clearInterval(intervalId);
      setIsPolling(false);
    };
  }, [actionLoading, promptAction, task?.state, taskId]);

  const taskCard = task
    ? {
        ...buildAgentTaskCard(task),
        sync_hint: isPolling
          ? backgroundRefreshing
            ? 'Syncing task detail...'
            : 'Watching this task every 5s'
          : null,
        is_syncing: backgroundRefreshing,
      }
    : null;
  const resultLines = taskCard ? taskCard.lines : [];

  const executeAction = async (actionItem, extraParams = {}) => {
    if (!actionItem?.id || !task?.id) {
      Alert.alert('Action Unavailable', 'This task action is missing context.');
      return;
    }

    setActionLoading(true);
    try {
      const outcome = await executeStructuredAction({
        actionItem,
        profile: currentProfile,
        baseParams: {
          task_id: task.id,
        },
        extraParams,
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

      await loadTask({ silent: false });
    } catch (err) {
      Alert.alert('Error', `Failed to run task action: ${err.message}`);
    } finally {
      setActionLoading(false);
    }
  };

  const executeLifecycleControl = async (action, successTitle, errorTitle) => {
    if (!task?.id) {
      Alert.alert('Action Unavailable', 'This task is missing context.');
      return;
    }

    setActionLoading(true);
    try {
      const response = await postAgentTaskControl(task.id, action);
      setTask((current) => applyTaskControlResponse(current, response));
      setLastRefreshedAt(response.updated_at || new Date().toISOString());
      Alert.alert(successTitle, response.message || `Task ${action} completed.`);
      await loadTask({ silent: true });
    } catch (err) {
      Alert.alert(errorTitle, err.message);
    } finally {
      setActionLoading(false);
    }
  };

  const handleActionPress = async (actionItem) => {
    const localOutcome = await executeLocalStructuredAction({ actionItem, navigation });
    if (localOutcome.handled) {
      Alert.alert('Wearables Bridge', localOutcome.message);
      return;
    }

    if (actionItem?.id === 'mobile_pause_task') {
      await executeLifecycleControl('pause', 'Task Paused', 'Pause Failed');
      return;
    }
    if (actionItem?.id === 'mobile_resume_task') {
      await executeLifecycleControl('resume', 'Task Resumed', 'Resume Failed');
      return;
    }
    if (actionItem?.id === 'mobile_cancel_task') {
      await executeLifecycleControl('cancel', 'Task Cancelled', 'Cancel Failed');
      return;
    }
    if (actionItem?.prompt_key) {
      setPromptAction(actionItem);
      setPromptValue(actionItem.params?.[actionItem.prompt_key] || '');
      return;
    }
    await executeAction(actionItem);
  };

  return (
    <ScrollView style={styles.container}>
      <ScreenHeader
        title="Task Detail"
        actionLabel={loading ? 'Refreshing...' : 'Refresh'}
        onActionPress={() => loadTask({ silent: false })}
        actionDisabled={loading || actionLoading}
      />

      <RefreshStatusCard
        intervalSeconds={isPolling ? POLL_INTERVAL_MS / 1000 : null}
        backgroundRefreshing={backgroundRefreshing}
        lastRefreshedAt={lastRefreshedAt}
        idleLabel={!isPolling && lastRefreshedAt ? 'Auto-refresh idle' : null}
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

      {task ? (
        <View style={styles.detailCard}>
          <Text style={styles.sectionTitle}>{task.provider_label || task.provider || 'Task'}</Text>
          <Text style={styles.metaLine}>State: {task.state}</Text>
          <Text style={styles.metaLine}>Task ID: {task.id}</Text>
          {task.result?.capability ? (
            <Text style={styles.metaLine}>Capability: {task.result.capability}</Text>
          ) : null}
          {task.instruction ? (
            <>
              <Text style={styles.subheading}>Instruction</Text>
              <Text style={styles.bodyText}>{task.instruction}</Text>
            </>
          ) : null}
          {task.result_preview ? (
            <>
              <Text style={styles.subheading}>Preview</Text>
              <Text style={styles.bodyText}>{task.result_preview}</Text>
            </>
          ) : null}
          {resultLines.length > 0 ? (
            <>
              <Text style={styles.subheading}>Normalized Result</Text>
              {resultLines.map((line, index) => (
                <Text key={`${line}-${index}`} style={styles.bodyText}>
                  {line}
                </Text>
              ))}
            </>
          ) : null}
        </View>
      ) : null}

      <UICardList
        cards={taskCard ? [taskCard] : []}
        title={taskCard ? 'Task Actions:' : null}
        disabled={loading || actionLoading}
        onActionPress={(actionItem) => handleActionPress(actionItem)}
      />

      <ActionPromptModal
        visible={Boolean(promptAction)}
        title={promptAction?.label || 'Task Action'}
        promptLabel={promptAction?.prompt_label || 'Enter a value'}
        value={promptValue}
        onChangeValue={setPromptValue}
        onCancel={() => {
          setPromptAction(null);
          setPromptValue('');
        }}
        onRun={async () => {
          if (!promptAction?.prompt_key) {
            return;
          }
          const promptKey = promptAction.prompt_key;
          const actionItem = promptAction;
          setPromptAction(null);
          await executeAction(actionItem, { [promptKey]: promptValue.trim() });
          setPromptValue('');
        }}
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
  detailCard: {
    backgroundColor: '#fff',
    borderRadius: 10,
    padding: 16,
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
  sectionTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 8,
    color: '#111827',
  },
  metaLine: {
    fontSize: 13,
    color: '#4b5563',
    marginTop: 2,
  },
  subheading: {
    fontSize: 14,
    fontWeight: '700',
    marginTop: 14,
    marginBottom: 6,
    color: '#1f2937',
  },
  bodyText: {
    fontSize: 14,
    color: '#333',
    marginTop: 4,
  },
});
