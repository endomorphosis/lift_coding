import { sendActionCommand } from '../api/client';

export function buildPromptDraft(actionItem, card, valueOverride = undefined) {
  if (!actionItem?.prompt_key) {
    return null;
  }

  return {
    actionId: actionItem.id,
    taskId: card?.task_id || null,
    promptKey: actionItem.prompt_key,
    value:
      valueOverride !== undefined
        ? valueOverride
        : actionItem.params?.[actionItem.prompt_key] || '',
  };
}

export function extractActionTaskUpdate(response) {
  const explicitTaskId =
    typeof response?.follow_on_task?.task_id === 'string' ? response.follow_on_task.task_id : null;
  const intentTaskId =
    typeof response?.intent?.entities?.task_id === 'string' ? response.intent.entities.task_id : null;
  const toolCalls = Array.isArray(response?.debug?.tool_calls) ? response.debug.tool_calls : [];
  const toolTask = toolCalls.find((toolCall) => typeof toolCall?.task_id === 'string') || null;
  const taskId = explicitTaskId || intentTaskId || toolTask?.task_id || null;

  if (!taskId) {
    return null;
  }

  return {
    task_id: taskId,
    state:
      typeof response?.follow_on_task?.state === 'string'
        ? response.follow_on_task.state
        : typeof toolTask?.state === 'string'
          ? toolTask.state
          : typeof response?.intent?.entities?.state === 'string'
            ? response.intent.entities.state
            : null,
    provider:
      typeof response?.follow_on_task?.provider === 'string'
        ? response.follow_on_task.provider
        : typeof toolTask?.provider === 'string'
          ? toolTask.provider
          : typeof response?.intent?.entities?.provider === 'string'
            ? response.intent.entities.provider
            : null,
  };
}

export async function executeStructuredAction({
  actionItem,
  profile,
  baseParams = {},
  extraParams = {},
}) {
  const response = await sendActionCommand(actionItem.id, {
    profile,
    params: {
      ...(actionItem.params || {}),
      ...baseParams,
      ...extraParams,
    },
  });

  if (response.pending_action?.summary) {
    return {
      kind: 'pending_confirmation',
      message: response.pending_action.summary,
      taskUpdate: extractActionTaskUpdate(response),
      response,
    };
  }

  if (response.spoken_text) {
    return {
      kind: 'completed',
      message: response.spoken_text,
      taskUpdate: extractActionTaskUpdate(response),
      response,
    };
  }

  return {
    kind: 'completed',
    message: 'Action completed.',
    taskUpdate: extractActionTaskUpdate(response),
    response,
  };
}
