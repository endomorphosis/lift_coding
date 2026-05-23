import { sendActionCommand } from '../api/client';
import { getMetaWearablesDat } from '../native/metaWearablesDat';
import { isDisplayWidgetActionId } from './metaWearablesDatDisplayWidgetContract';

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
    provider_label:
      typeof response?.follow_on_task?.provider_label === 'string'
        ? response.follow_on_task.provider_label
        : typeof toolTask?.provider_label === 'string'
          ? toolTask.provider_label
          : null,
    capability:
      typeof response?.follow_on_task?.capability === 'string'
        ? response.follow_on_task.capability
        : typeof toolTask?.capability === 'string'
          ? toolTask.capability
          : null,
    summary:
      typeof response?.follow_on_task?.summary === 'string'
        ? response.follow_on_task.summary
        : null,
  };
}

export function buildLastActionLines(lastAction) {
  if (!lastAction?.message) {
    return [];
  }

  const lines = [lastAction.message];
  if (
    typeof lastAction?.taskUpdate?.summary === 'string' &&
    lastAction.taskUpdate.summary &&
    lastAction.taskUpdate.summary !== lastAction.message
  ) {
    lines.push(lastAction.taskUpdate.summary);
  }
  return lines;
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

function navigateToWearablesDiagnostics(navigation) {
  if (navigation?.navigate) {
    navigation.navigate('Glasses');
  }
}

function getDisplayWidgetActionPayload(actionItem) {
  const params = actionItem?.params || {};
  if (params.display_widget_action && typeof params.display_widget_action === 'object') {
    return params.display_widget_action;
  }
  if (actionItem?.mobile_payload && typeof actionItem.mobile_payload === 'object') {
    return actionItem.mobile_payload;
  }
  if (params.mobile_payload && typeof params.mobile_payload === 'object') {
    return params.mobile_payload;
  }
  return params;
}

function getDisplayWidgetId(payload) {
  return payload?.widget_id || payload?.widgetId || payload?.manifest?.widget_id || payload?.manifest?.id || null;
}

function getDisplayWidgetFocusDirection(payload) {
  if (payload?.focus?.direction) {
    return payload.focus.direction;
  }
  if (payload?.operation === 'focus_previous') {
    return 'previous';
  }
  return payload?.direction || 'next';
}

function getDisplayWidgetActivatedActionId(payload) {
  return (
    payload?.activated_action_id ||
    payload?.activatedActionId ||
    payload?.action_id ||
    payload?.actionId ||
    null
  );
}

function getDisplayWidgetVideoPayload(payload) {
  if (payload?.video && typeof payload.video === 'object') {
    return payload.video;
  }
  if (payload?.video_url || payload?.videoUrl) {
    return { uri: payload.video_url || payload.videoUrl };
  }
  if (Array.isArray(payload?.manifest?.media)) {
    const video = payload.manifest.media.find((item) => item?.type === 'video');
    if (video) {
      return video;
    }
  }
  return payload;
}

function getDisplayWidgetSubscriptionPayload(payload) {
  if (payload?.subscription && typeof payload.subscription === 'object') {
    return payload.subscription;
  }
  return {
    widget_id: getDisplayWidgetId(payload),
    correlation_id: payload?.correlation_id || payload?.correlationId || null,
    request_id: payload?.request_id || payload?.requestId || null,
  };
}

async function executeLocalDisplayWidgetAction({ actionItem, navigation }) {
  if (!isDisplayWidgetActionId(actionItem?.id)) {
    return { handled: false };
  }

  const payload = getDisplayWidgetActionPayload(actionItem);
  const dat = await getMetaWearablesDat();
  let response;

  if (actionItem?.id === 'mobile_render_display_widget') {
    response = await dat.renderDisplayWidget(payload?.manifest || payload, payload);
  } else if (actionItem?.id === 'mobile_update_display_widget') {
    response = await dat.updateDisplayWidget(payload?.patch || payload, payload);
  } else if (actionItem?.id === 'mobile_clear_display_widget') {
    response = await dat.clearDisplayWidget(getDisplayWidgetId(payload), payload);
  } else if (actionItem?.id === 'mobile_focus_display_widget') {
    response = await dat.focusDisplayWidget(getDisplayWidgetFocusDirection(payload), payload);
  } else if (actionItem?.id === 'mobile_activate_display_widget_action') {
    response = await dat.activateDisplayWidgetAction(getDisplayWidgetActivatedActionId(payload), payload);
  } else if (actionItem?.id === 'mobile_reset_display_widget_session') {
    response = await dat.resetDisplayWidgetSession(payload);
  } else if (actionItem?.id === 'mobile_play_display_widget_video') {
    response = await dat.playDisplayWidgetVideo(getDisplayWidgetVideoPayload(payload), payload);
  } else if (actionItem?.id === 'mobile_subscribe_display_widget_updates') {
    response = await dat.subscribeDisplayWidgetUpdates(getDisplayWidgetSubscriptionPayload(payload), payload);
  } else {
    return { handled: false };
  }

  navigateToWearablesDiagnostics(navigation);
  return {
    handled: true,
    message: response?.message || 'Display widget action requested.',
    response,
  };
}

export async function executeLocalStructuredAction({ actionItem, navigation }) {
  if (actionItem?.id === 'mobile_open_wearables_diagnostics') {
    navigateToWearablesDiagnostics(navigation);

    return {
      handled: true,
      message: 'Opened wearables bridge diagnostics.',
      response: null,
    };
  }

  if (actionItem?.id === 'mobile_render_wearables_display_test') {
    const dat = await getMetaWearablesDat();
    const response = await dat.renderDisplayTest();
    const message = response?.message || 'Display test rendering requested (not yet implemented in DAT bridge).';
    navigateToWearablesDiagnostics(navigation);
    return {
      handled: true,
      message,
      response,
    };
  }

  if (actionItem?.id === 'mobile_clear_wearables_display') {
    const dat = await getMetaWearablesDat();
    const response = await dat.clearDisplay();
    const message = response?.message || 'Display clear requested (not yet implemented in DAT bridge).';
    navigateToWearablesDiagnostics(navigation);
    return {
      handled: true,
      message,
      response,
    };
  }

  if (actionItem?.id === 'mobile_play_wearables_display_video') {
    const dat = await getMetaWearablesDat();
    const videoUrl = String(actionItem?.params?.video_url || 'https://example.com/demo.mp4');
    const response = await dat.playDisplayVideo(videoUrl);
    const message = response?.message || 'Display video playback requested.';
    navigateToWearablesDiagnostics(navigation);
    return {
      handled: true,
      message,
      response,
    };
  }

  if (actionItem?.id === 'mobile_reset_wearables_display_session') {
    const dat = await getMetaWearablesDat();
    const response = await dat.resetDisplaySession();
    const message = response?.message || 'Display session reset requested.';
    navigateToWearablesDiagnostics(navigation);
    return {
      handled: true,
      message,
      response,
    };
  }

  const displayWidgetOutcome = await executeLocalDisplayWidgetAction({ actionItem, navigation });
  if (displayWidgetOutcome.handled) {
    return displayWidgetOutcome;
  }

  if (actionItem?.id !== 'mobile_reconnect_wearables_target') {
    return { handled: false };
  }

  const dat = await getMetaWearablesDat();
  const response = await dat.reconnectSelectedDeviceTarget();
  const targetLabel = response?.deviceName || response?.deviceId || 'selected target';
  const connectionState = response?.targetConnectionState || response?.state || 'unknown';
  const message =
    connectionState === 'unselected' || !response?.deviceId
      ? 'No selected wearables target is available to reconnect.'
      : `Reconnect attempted for ${targetLabel}. State: ${connectionState}.`;

  navigateToWearablesDiagnostics(navigation);

  return {
    handled: true,
    message,
    response,
  };
}
