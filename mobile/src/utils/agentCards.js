import { getNotificationTaskState } from './notificationCards';

function getResultEnvelope(source = {}) {
  const envelope = source?.result_envelope || source?.resultEnvelope || source?.result?.result_envelope;
  return envelope && typeof envelope === 'object' ? envelope : null;
}

function getArtifactRefs(source = {}) {
  const envelope = getResultEnvelope(source);
  const artifactRefs = envelope?.artifact_refs || envelope?.artifactRefs;
  return artifactRefs && typeof artifactRefs === 'object' ? artifactRefs : {};
}

function normalizeResult(item = {}) {
  const result = item?.result && typeof item.result === 'object' ? { ...item.result } : {};
  const envelope = getResultEnvelope(item) || getResultEnvelope(result) || item?.result_envelope;
  const artifactRefs = getArtifactRefs(item);
  const structuredOutput = envelope?.structured_output || envelope?.structuredOutput || item?.result_output;

  if (envelope) {
    if (!result.message && typeof structuredOutput?.message === 'string') {
      result.message = structuredOutput.message;
    }
    if (!result.status && typeof envelope.status === 'string') {
      result.status = envelope.status;
    }
    if (!result.provider_label && typeof envelope.provider_label === 'string') {
      result.provider_label = envelope.provider_label;
    }
    if (!result.execution_mode && typeof envelope.execution_mode === 'string') {
      result.execution_mode = envelope.execution_mode;
    }
  }

  if (!result.cid && typeof artifactRefs?.result_cid === 'string') {
    result.cid = artifactRefs.result_cid;
  }
  if (!result.cid && typeof structuredOutput?.cid === 'string') {
    result.cid = structuredOutput.cid;
  }

  return result;
}

function getResultPreview(item = {}) {
  const envelope = getResultEnvelope(item);
  if (typeof envelope?.summary === 'string' && envelope.summary) {
    return envelope.summary;
  }
  return item?.result_preview || null;
}

function getFollowUpActionItems(item = {}, fallbackItems = []) {
  const envelope = getResultEnvelope(item);
  const actions = envelope?.follow_up_actions || envelope?.followUpActions || item?.follow_up_actions;
  return Array.isArray(actions) && actions.length > 0 ? actions : fallbackItems;
}

function relativeTimestampLabel(value) {
  if (!value) {
    return null;
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return null;
  }

  const deltaSeconds = Math.max(0, Math.round((Date.now() - date.getTime()) / 1000));
  if (deltaSeconds < 60) {
    return 'Updated just now';
  }
  if (deltaSeconds < 3600) {
    const minutes = Math.floor(deltaSeconds / 60);
    return `Updated ${minutes}m ago`;
  }
  if (deltaSeconds < 86400) {
    const hours = Math.floor(deltaSeconds / 3600);
    return `Updated ${hours}h ago`;
  }
  const days = Math.floor(deltaSeconds / 86400);
  return `Updated ${days}d ago`;
}

function statusTone(state) {
  if (state === 'running' || state === 'created') {
    return 'active';
  }
  if (state === 'needs_input') {
    return 'paused';
  }
  if (state === 'completed') {
    return 'success';
  }
  if (state === 'failed') {
    return 'danger';
  }
  return 'neutral';
}

function statusBadge(state) {
  if (!state) {
    return null;
  }
  if (state === 'needs_input') {
    return 'Paused';
  }
  return state.charAt(0).toUpperCase() + state.slice(1);
}

function isLiveState(state) {
  return state === 'running' || state === 'created';
}

function buildResultLines(result = {}, options = {}) {
  const lines = [];

  if (options.instruction) {
    lines.push(`Instruction: ${options.instruction}`);
  }
  if (result.message) {
    lines.push(result.message);
  }
  if (result.status) {
    lines.push(`Status: ${result.status}`);
  }
  if (result.cid) {
    lines.push(`CID: ${result.cid}`);
  }
  if (Array.isArray(result.dataset_queries) && result.dataset_queries.length > 0) {
    lines.push(`Queries: ${result.dataset_queries.join(', ')}`);
  }
  if (Array.isArray(result.target_terms) && result.target_terms.length > 0) {
    lines.push(`Targets: ${result.target_terms.join(', ')}`);
  }
  if (Array.isArray(result.seed_urls) && result.seed_urls.length > 0) {
    lines.push(`Seed URLs: ${result.seed_urls.join(', ')}`);
  }
  if (options.resultPreview && !lines.includes(options.resultPreview)) {
    lines.unshift(options.resultPreview);
  }

  return lines;
}

function executionModeLabel(mode) {
  if (mode === 'direct_import') {
    return 'Local';
  }
  if (mode === 'mcp_remote') {
    return 'Remote';
  }
  return null;
}

function executionModeDetailLine(source = {}, result = {}) {
  const preferredMode =
    source?.mcp_preferred_execution_mode ||
    source?.mcpPreferredExecutionMode ||
    source?.result_envelope?.preferred_execution_mode ||
    source?.resultEnvelope?.preferredExecutionMode ||
    null;
  const resolvedMode =
    source?.mcp_execution_mode ||
    source?.mcpExecutionMode ||
    result?.execution_mode ||
    source?.result_envelope?.execution_mode ||
    source?.resultEnvelope?.executionMode ||
    null;
  const label = executionModeLabel(resolvedMode);

  if (!label) {
    return null;
  }
  if (preferredMode === 'direct_import' && resolvedMode === 'mcp_remote') {
    return `Execution: ${label} (local unavailable)`;
  }
  return `Execution: ${label}`;
}

function appendExecutionModeLine(lines = [], source = {}, result = {}) {
  const executionLine = executionModeDetailLine(source, result);
  if (!executionLine || lines.includes(executionLine)) {
    return lines;
  }
  return [...lines, executionLine];
}

export function buildTaskLifecycleActionItems(task = {}) {
  const actions = [];
  const state = task?.state;

  if (state === 'created') {
    actions.push({ id: 'mobile_cancel_task', label: 'Cancel', phrase: 'cancel this task' });
  }

  if (state === 'running') {
    actions.push(
      { id: 'mobile_pause_task', label: 'Pause', phrase: 'pause this task' },
      { id: 'mobile_cancel_task', label: 'Cancel', phrase: 'cancel this task' }
    );
  }

  if (state === 'needs_input') {
    actions.push(
      { id: 'mobile_resume_task', label: 'Resume', phrase: 'resume this task' },
      { id: 'mobile_cancel_task', label: 'Cancel', phrase: 'cancel this task' }
    );
  }

  return actions;
}

export function buildAgentActionItems({
  provider,
  instruction = '',
  result = {},
  includeDetails = true,
}) {
  const actions = [];

  if (includeDetails) {
    actions.push(
      { id: 'show_result_details', label: 'Details', phrase: 'show task details for that result' },
      { id: 'show_related_results', label: 'Related', phrase: 'show another result like this' }
    );
  }

  if (result.cid) {
    actions.push(
      { id: 'open_result', label: 'Open', phrase: 'open that result', params: { cid: result.cid } },
      { id: 'read_cid', label: 'Read CID', phrase: 'read the cid', params: { cid: result.cid } },
      { id: 'share_cid', label: 'Share CID', phrase: 'share that cid', params: { cid: result.cid } },
      {
        id: 'save_result_to_ipfs_local',
        label: 'Save JSON Locally',
        phrase: 'save that result to ipfs locally',
        execution_mode: 'direct_import',
        execution_mode_label: 'Local',
        params: { mcp_preferred_execution_mode: 'direct_import' },
      },
      {
        id: 'save_result_to_ipfs_remote',
        label: 'Save JSON Remotely',
        phrase: 'save that result to ipfs remotely',
        execution_mode: 'mcp_remote',
        execution_mode_label: 'Remote',
        params: { mcp_preferred_execution_mode: 'mcp_remote' },
      },
      { id: 'pin_result', label: 'Pin', phrase: 'pin that', params: { cid: result.cid } },
      {
        id: 'pin_result_local',
        label: 'Pin Locally',
        phrase: 'pin that locally',
        execution_mode: 'direct_import',
        execution_mode_label: 'Local',
        params: { cid: result.cid, mcp_preferred_execution_mode: 'direct_import' },
      },
      {
        id: 'pin_result_remote',
        label: 'Pin Remotely',
        phrase: 'pin that remotely',
        execution_mode: 'mcp_remote',
        execution_mode_label: 'Remote',
        params: { cid: result.cid, mcp_preferred_execution_mode: 'mcp_remote' },
      },
      {
        id: 'unpin_result_local',
        label: 'Unpin Locally',
        phrase: 'unpin that locally',
        execution_mode: 'direct_import',
        execution_mode_label: 'Local',
        params: { cid: result.cid, mcp_preferred_execution_mode: 'direct_import' },
      },
      {
        id: 'unpin_result_remote',
        label: 'Unpin Remotely',
        phrase: 'unpin that remotely',
        execution_mode: 'mcp_remote',
        execution_mode_label: 'Remote',
        params: { cid: result.cid, mcp_preferred_execution_mode: 'mcp_remote' },
      },
      { id: 'unpin_result', label: 'Unpin', phrase: 'unpin that', params: { cid: result.cid } },
      { id: 'save_result_to_ipfs', label: 'Save JSON', phrase: 'save that result to ipfs' }
    );
  }

  if (result.capability === 'dataset_discovery') {
    actions.push({
      id: 'rerun_dataset_search',
      label: 'Rerun Search',
      phrase: 'rerun that dataset search with ...',
      execution_mode: 'mcp_remote',
      execution_mode_label: 'Remote',
      params: { mcp_input: result.dataset_queries?.[0] || instruction || '' },
      prompt_label: 'New dataset query',
      prompt_key: 'mcp_input',
    });
  }

  if (provider === 'ipfs_accelerate_mcp' || result.capability === 'agentic_fetch') {
    actions.push({
      id: 'rerun_workflow',
      label: 'Rerun',
      phrase: 'rerun that workflow',
      execution_mode: 'mcp_remote',
      execution_mode_label: 'Remote',
      params: { mcp_preferred_execution_mode: 'mcp_remote' },
    });
    actions.push({
      id: 'rerun_fetch_with_url',
      label: 'Rerun URL',
      phrase: 'rerun that fetch with https://...',
      execution_mode: 'mcp_remote',
      execution_mode_label: 'Remote',
      params: {
        mcp_seed_url: result.seed_urls?.[0] || '',
        mcp_preferred_execution_mode: 'mcp_remote',
      },
      prompt_label: 'New seed URL',
      prompt_key: 'mcp_seed_url',
    });
  }

  return actions;
}

export function buildAgentDeepLink(result = {}) {
  if (result.cid) {
    return `ipfs://${result.cid}`;
  }
  if (Array.isArray(result.seed_urls) && result.seed_urls[0]) {
    return result.seed_urls[0];
  }
  return null;
}

export function buildAgentResultCard(item) {
  const result = normalizeResult(item);
  const state = item?.state || 'completed';
  const fallbackActionItems = buildAgentActionItems({
    provider: item?.provider,
    instruction: item?.description || '',
    result,
    includeDetails: true,
  });
  return {
    title: result.provider_label || item?.provider || 'Result',
    subtitle: item?.description || result.capability || item?.state,
    status_badge: statusBadge(state),
    status_tone: statusTone(state),
    is_live: isLiveState(state),
    live_label: isLiveState(state) ? 'Live' : null,
    timestamp_label: relativeTimestampLabel(item?.updated_at || item?.created_at),
    lines: appendExecutionModeLine(
      buildResultLines(result, {
        resultPreview: getResultPreview(item),
      }),
      item,
      result
    ),
    deep_link: buildAgentDeepLink(result),
    action_items: getFollowUpActionItems(item, fallbackActionItems),
    task_id: item?.task_id,
  };
}

export function buildAgentTaskCard(task) {
  const result = normalizeResult(task);
  const state = task?.state;
  const instruction = task?.instruction || task?.description || '';
  const fallbackActionItems = buildAgentActionItems({
    provider: task?.provider,
    instruction,
    result,
    includeDetails: false,
  });
  return {
    title: task?.provider_label || task?.provider || 'Task',
    subtitle: result.capability || state || 'detail',
    status_badge: statusBadge(state),
    status_tone: statusTone(state),
    is_live: isLiveState(state),
    live_label: isLiveState(state) ? 'Live' : null,
    timestamp_label: relativeTimestampLabel(task?.updated_at || task?.created_at),
    lines: appendExecutionModeLine(
      buildResultLines(result, {
        instruction,
        resultPreview: getResultPreview(task),
      }),
      task,
      result
    ),
    deep_link: buildAgentDeepLink(result),
    action_items: [
      ...buildTaskLifecycleActionItems(task),
      ...getFollowUpActionItems(task, fallbackActionItems),
    ],
    task_id: task?.id,
  };
}

export function buildAgentNotificationCard(notification) {
  const taskId = notification?.metadata?.task_id || notification?.card?.task_id || null;
  const baseCard = notification?.card || {
    title: notification?.title || 'Notification',
    subtitle: notification?.body || notification?.message || '',
    lines: [],
  };
  const lifecycleState = getNotificationTaskState(notification);
  const lifecycleActions =
    taskId && lifecycleState
      ? buildTaskLifecycleActionItems({ state: lifecycleState })
      : [];

  return {
    ...baseCard,
    status_badge: statusBadge(lifecycleState),
    status_tone: statusTone(lifecycleState),
    is_live: isLiveState(lifecycleState),
    live_label: isLiveState(lifecycleState) ? 'Live' : null,
    timestamp_label: relativeTimestampLabel(notification?.timestamp || notification?.created_at),
    lines: appendExecutionModeLine(
      baseCard.lines || [],
      notification?.metadata || {},
      normalizeResult(notification?.metadata || {})
    ),
    action_items: [...lifecycleActions, ...(baseCard.action_items || [])],
    task_id: taskId,
    notification_id: notification?.id,
  };
}
