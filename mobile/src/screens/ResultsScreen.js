import React, { useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  Button,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';

import ActionPromptModal from '../components/ActionPromptModal';
import EmptyStateCard from '../components/EmptyStateCard';
import InfoCard from '../components/InfoCard';
import ScreenHeader from '../components/ScreenHeader';
import SegmentedControl from '../components/SegmentedControl';
import UICardList from '../components/UICardList';
import { getAgentResults } from '../api/client';
import { getProfile } from '../storage/profileStorage';
import {
  getResultsScreenState,
  setResultsScreenState,
} from '../storage/resultsScreenStorage';
import {
  buildLastActionLines,
  buildPromptDraft,
  executeStructuredAction,
} from '../utils/agentActions';
import { buildAgentResultCard } from '../utils/agentCards';
import { shouldClearLastActionFromResults } from '../utils/lastActionState';

const RESULT_VIEWS = [
  { id: 'overview', label: 'Overview' },
  { id: 'datasets', label: 'Datasets' },
  { id: 'ipfs', label: 'IPFS' },
  { id: 'fetches', label: 'Fetches' },
];

export default function ResultsScreen({ navigation }) {
  const [currentProfile, setCurrentProfile] = useState('default');
  const [selectedView, setSelectedView] = useState('overview');
  const [currentOffset, setCurrentOffset] = useState(0);
  const [latestOnly, setLatestOnly] = useState(false);
  const [sort, setSort] = useState('updated_at');
  const [direction, setDirection] = useState('desc');
  const [resultsResponse, setResultsResponse] = useState(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState(null);
  const [promptAction, setPromptAction] = useState(null);
  const [promptValue, setPromptValue] = useState('');
  const [lastAction, setLastAction] = useState(null);
  const [savedPromptDraft, setSavedPromptDraft] = useState(null);

  const loadResults = async (
    view = selectedView,
    offset = currentOffset,
    persistedLastAction = lastAction,
    options = {}
  ) => {
    const nextLatestOnly = options.latestOnly ?? latestOnly;
    const nextSort = options.sort ?? sort;
    const nextDirection = options.direction ?? direction;
    setLoading(true);
    setError(null);
    try {
      const data = await getAgentResults({
        view,
        limit: 20,
        offset,
        latest_only: nextLatestOnly,
        sort: nextSort,
        direction: nextDirection,
      });
      setResultsResponse(data);
      setSelectedView(view);
      setCurrentOffset(offset);
      setLatestOnly(nextLatestOnly);
      setSort(nextSort);
      setDirection(nextDirection);
      await setResultsScreenState({
        selectedView: view,
        offset,
        latestOnly: nextLatestOnly,
        sort: nextSort,
        direction: nextDirection,
        lastAction: persistedLastAction,
        promptDraft: savedPromptDraft,
      });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const executeAction = async (actionItem, card, extraParams = {}) => {
    if (!actionItem?.id || !card?.task_id) {
      Alert.alert('Action Unavailable', 'This result action is missing task context.');
      return;
    }

    setActionLoading(true);
    try {
      const outcome = await executeStructuredAction({
        actionItem,
        profile: currentProfile,
        baseParams: {
          task_id: card.task_id,
        },
        extraParams,
      });

      let nextLastAction = null;

      if (outcome.kind === 'pending_confirmation') {
        nextLastAction = {
          actionId: actionItem.id,
          message: outcome.message,
          status: 'pending_confirmation',
          taskUpdate: outcome.taskUpdate || null,
        };
        setLastAction(nextLastAction);
        await setResultsScreenState({
          selectedView,
          offset: currentOffset,
          latestOnly,
          sort,
          direction,
          lastAction: nextLastAction,
          promptDraft: null,
        });
        Alert.alert('Confirmation Required', outcome.message);
      } else {
        const taskSuffix = outcome.taskUpdate?.task_id
          ? ` Task ${outcome.taskUpdate.task_id.slice(0, 8)} is ready to track.`
          : '';
        nextLastAction = {
          actionId: actionItem.id,
          message: `${outcome.message}${taskSuffix}`,
          status: 'completed',
          taskUpdate: outcome.taskUpdate || null,
        };
        setLastAction(nextLastAction);
        await setResultsScreenState({
          selectedView,
          offset: currentOffset,
          latestOnly,
          sort,
          direction,
          lastAction: nextLastAction,
          promptDraft: null,
        });
        Alert.alert('Action Complete', outcome.message);
      }

      await loadResults(selectedView, currentOffset, nextLastAction);
    } catch (err) {
      Alert.alert('Error', `Failed to run result action: ${err.message}`);
    } finally {
      setActionLoading(false);
    }
  };

  const handleActionPress = async (actionItem, card) => {
    if (actionItem?.prompt_key) {
      const nextPromptDraft = buildPromptDraft(actionItem, card);
      setPromptAction({ actionItem, card });
      setPromptValue(nextPromptDraft.value);
      setSavedPromptDraft(nextPromptDraft);
      await setResultsScreenState({
        selectedView,
        offset: currentOffset,
        latestOnly,
        sort,
        direction,
        lastAction,
        promptDraft: nextPromptDraft,
      });
      return;
    }

    await executeAction(actionItem, card);
  };

  useEffect(() => {
    (async () => {
      try {
        const savedState = await getResultsScreenState();
        const profile = await getProfile();
        setCurrentProfile(profile);
        setLastAction(savedState.lastAction || null);
        setSavedPromptDraft(savedState.promptDraft || null);
        setSelectedView(savedState.selectedView || 'overview');
        setCurrentOffset(savedState.offset || 0);
        setLatestOnly(Boolean(savedState.latestOnly));
        setSort(savedState.sort || 'updated_at');
        setDirection(savedState.direction || 'desc');
        await loadResults(
          savedState.selectedView || 'overview',
          savedState.offset || 0,
          savedState.lastAction || null,
          {
            latestOnly: Boolean(savedState.latestOnly),
            sort: savedState.sort || 'updated_at',
            direction: savedState.direction || 'desc',
          }
        );
      } catch (err) {
        console.error('Failed to load profile:', err);
        await loadResults('overview', 0, null, {
          latestOnly: false,
          sort: 'updated_at',
          direction: 'desc',
        });
      }
    })();
  }, []);

  const cards = Array.isArray(resultsResponse?.results)
    ? resultsResponse.results.map((item) => buildAgentResultCard(item))
    : [];

  useEffect(() => {
    if (!shouldClearLastActionFromResults(lastAction, resultsResponse?.results)) {
      return;
    }

    setLastAction(null);
    setResultsScreenState({
      selectedView,
      offset: currentOffset,
      latestOnly,
      sort,
      direction,
      lastAction: null,
      promptDraft: savedPromptDraft,
    }).catch(() => {});
  }, [
    currentOffset,
    direction,
    lastAction,
    latestOnly,
    resultsResponse,
    savedPromptDraft,
    selectedView,
    sort,
  ]);

  useEffect(() => {
    if (!savedPromptDraft || promptAction || cards.length === 0) {
      return;
    }

    const matchingCard = cards.find((card) => card.task_id === savedPromptDraft.taskId);
    if (!matchingCard) {
      return;
    }

    const matchingAction = matchingCard.action_items?.find(
      (actionItem) => actionItem.id === savedPromptDraft.actionId
    );
    if (!matchingAction) {
      return;
    }

    setPromptAction({ actionItem: matchingAction, card: matchingCard });
    setPromptValue(savedPromptDraft.value || '');
  }, [cards, promptAction, savedPromptDraft]);

  useEffect(() => {
    if (!promptAction?.actionItem?.prompt_key || !promptAction?.card?.task_id) {
      return;
    }

    const nextPromptDraft = {
      actionId: promptAction.actionItem.id,
      taskId: promptAction.card.task_id,
      promptKey: promptAction.actionItem.prompt_key,
      value: promptValue,
    };
    setSavedPromptDraft(nextPromptDraft);
    setResultsScreenState({
      selectedView,
      offset: currentOffset,
      latestOnly,
      sort,
      direction,
      lastAction,
      promptDraft: nextPromptDraft,
    }).catch(() => {});
  }, [currentOffset, direction, lastAction, latestOnly, promptAction, promptValue, selectedView, sort]);

  return (
    <ScrollView style={styles.container}>
      <ScreenHeader
        title="Agent Results"
        subtitle="Browse completed MCP-backed results and run follow-up actions directly."
        actionLabel={loading ? 'Refreshing...' : 'Refresh Results'}
        onActionPress={() => loadResults(selectedView)}
        actionDisabled={loading || actionLoading}
      />

      <SegmentedControl
        options={RESULT_VIEWS.map((view) => ({ value: view.id, label: view.label }))}
        selectedValue={selectedView}
        onChange={(value) => loadResults(value, 0)}
        disabled={loading || actionLoading}
      />

      <SegmentedControl
        options={[
          { value: 'all', label: 'Latest Off' },
          { value: 'latest', label: 'Latest On' },
        ]}
        selectedValue={latestOnly ? 'latest' : 'all'}
        onChange={(value) => loadResults(selectedView, 0, lastAction, { latestOnly: value === 'latest' })}
        disabled={loading || actionLoading}
      />
      <SegmentedControl
        options={[
          { value: 'updated_at', label: 'Sort Updated' },
          { value: 'created_at', label: 'Sort Created' },
        ]}
        selectedValue={sort}
        onChange={(value) => loadResults(selectedView, 0, lastAction, { sort: value })}
        disabled={loading || actionLoading}
      />
      <SegmentedControl
        options={[
          { value: 'desc', label: 'Newest First' },
          { value: 'asc', label: 'Oldest First' },
        ]}
        selectedValue={direction}
        onChange={(value) => loadResults(selectedView, 0, lastAction, { direction: value })}
        disabled={loading || actionLoading}
      />

      {resultsResponse?.summary ? (
        <InfoCard
          title="Summary"
          tone="info"
          lines={[
            `Total results: ${resultsResponse.summary.total_results || 0}`,
            `View: ${resultsResponse.filters?.view || 'custom'}`,
            `Latest only: ${latestOnly ? 'yes' : 'no'}`,
            `Sort: ${sort} • ${direction}`,
            `Offset: ${resultsResponse.pagination?.offset || 0}`,
          ]}
        />
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
              ? async () => {
                  setLastAction(null);
                  await setResultsScreenState({
                    selectedView,
                    offset: currentOffset,
                    latestOnly,
                    sort,
                    direction,
                    lastAction: null,
                    promptDraft: savedPromptDraft,
                  });
                  navigation.navigate('TaskDetail', { taskId: lastAction.taskUpdate.task_id });
                }
              : null
          }
        />
      ) : null}

      {loading ? <ActivityIndicator size="large" color="#007AFF" style={styles.loader} /> : null}

      {error ? (
        <View style={styles.errorContainer}>
          <Text style={styles.errorText}>{error}</Text>
        </View>
      ) : null}

      {!loading && !error && cards.length === 0 ? (
        <EmptyStateCard
          title="No results yet"
          message="Try another saved view or run an MCP-backed command first."
        />
      ) : null}

      <UICardList
        cards={cards}
        title={cards.length > 0 ? 'Completed Results:' : null}
        disabled={loading || actionLoading}
        onActionPress={handleActionPress}
        onCardPress={(card) => {
          if (!card.task_id) {
            return;
          }
          navigation.navigate('TaskDetail', { taskId: card.task_id });
        }}
        cardPressLabel="Open Task Detail"
      />

      {resultsResponse?.pagination ? (
        <View style={styles.paginationRow}>
          <View style={styles.paginationButton}>
            <Button
              title="Previous"
              onPress={() =>
                loadResults(selectedView, Math.max(0, currentOffset - (resultsResponse.pagination.limit || 20)))
              }
              disabled={loading || actionLoading || currentOffset <= 0}
            />
          </View>
          <View style={styles.paginationButton}>
            <Button
              title="Next"
              onPress={() =>
                loadResults(selectedView, currentOffset + (resultsResponse.pagination.limit || 20))
              }
              disabled={loading || actionLoading || !resultsResponse.pagination.has_more}
            />
          </View>
        </View>
      ) : null}

      <ActionPromptModal
        visible={Boolean(promptAction)}
        title={promptAction?.actionItem?.label || 'Result Action'}
        promptLabel={promptAction?.actionItem?.prompt_label || 'Enter a value'}
        value={promptValue}
        onChangeValue={setPromptValue}
        onCancel={() => {
          setPromptAction(null);
          setPromptValue('');
          setSavedPromptDraft(null);
          setResultsScreenState({
            selectedView,
            offset: currentOffset,
            latestOnly,
            sort,
            direction,
            lastAction,
            promptDraft: null,
          }).catch(() => {});
        }}
        onRun={async () => {
          if (!promptAction?.actionItem?.prompt_key) {
            return;
          }
          const { actionItem, card } = promptAction;
          const promptKey = actionItem.prompt_key;
          setPromptAction(null);
          setSavedPromptDraft(null);
          await setResultsScreenState({
            selectedView,
            offset: currentOffset,
            latestOnly,
            sort,
            direction,
            lastAction,
            promptDraft: null,
          });
          await executeAction(actionItem, card, { [promptKey]: promptValue.trim() });
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
  errorContainer: {
    backgroundColor: '#ffebee',
    padding: 15,
    borderRadius: 5,
    marginTop: 15,
  },
  errorText: {
    color: '#c62828',
    fontSize: 14,
  },
  paginationRow: {
    flexDirection: 'row',
    marginTop: 12,
    marginBottom: 24,
  },
  paginationButton: {
    flex: 1,
    marginRight: 8,
  },
});
