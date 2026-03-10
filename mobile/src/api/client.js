/**
 * API Client for Handsfree Backend
 *
 * Aligned with spec/openapi.yaml.
 *
 * Endpoints:
 * - GET /v1/status
 * - POST /v1/command
 * - POST /v1/commands/action
 * - POST /v1/commands/confirm
 * - GET /v1/inbox
 * - GET /v1/notifications
 * - POST /v1/notifications/subscriptions
 * - DELETE /v1/notifications/subscriptions/{subscription_id}
 * - POST /v1/tts
 */

import { getBaseUrl, getHeaders } from './config';

function defaultClientContext(overrides = {}) {
  // Keep this dependency-free; callers can override anything they know.
  return {
    device: 'mobile',
    locale: 'en-US',
    timezone: 'UTC',
    app_version: 'dev',
    noise_mode: false,
    debug: false,
    privacy_mode: 'strict',
    ...overrides,
  };
}

function defaultProfile(profile) {
  return profile || 'default';
}

function normalizeAgentTaskControlResponse(data) {
  if (!data || typeof data !== 'object') {
    throw new Error('Task control returned an invalid response payload');
  }

  const taskId = typeof data.task_id === 'string' ? data.task_id : null;
  const state = typeof data.state === 'string' ? data.state : null;
  const message = typeof data.message === 'string' ? data.message : null;
  const updatedAt =
    typeof data.updated_at === 'string' || data.updated_at === null ? data.updated_at : null;

  if (!taskId || !state || !message) {
    throw new Error('Task control response is missing required fields');
  }

  return {
    task_id: taskId,
    state,
    message,
    updated_at: updatedAt,
  };
}

function normalizeFollowOnTask(data) {
  if (!data || typeof data !== 'object') {
    return null;
  }

  const taskId = typeof data.task_id === 'string' ? data.task_id : null;
  if (!taskId) {
    return null;
  }

  return {
    task_id: taskId,
    state: typeof data.state === 'string' ? data.state : null,
    provider: typeof data.provider === 'string' ? data.provider : null,
    provider_label: typeof data.provider_label === 'string' ? data.provider_label : null,
    capability: typeof data.capability === 'string' ? data.capability : null,
    summary: typeof data.summary === 'string' ? data.summary : null,
    mcp_execution_mode:
      typeof data.mcp_execution_mode === 'string' ? data.mcp_execution_mode : null,
    mcp_preferred_execution_mode:
      typeof data.mcp_preferred_execution_mode === 'string'
        ? data.mcp_preferred_execution_mode
        : null,
    result_preview: typeof data.result_preview === 'string' ? data.result_preview : null,
  };
}

function normalizeCommandResponse(data) {
  if (!data || typeof data !== 'object') {
    throw new Error('Command returned an invalid response payload');
  }

  return {
    ...data,
    follow_on_task: normalizeFollowOnTask(data.follow_on_task),
  };
}

function normalizeAgentTask(data) {
  if (!data || typeof data !== 'object') {
    throw new Error('Agent task returned an invalid response payload');
  }

  const trace = data.trace && typeof data.trace === 'object' ? data.trace : {};
  const resultEnvelope =
    data.result_envelope && typeof data.result_envelope === 'object'
      ? data.result_envelope
      : trace.mcp_result_envelope && typeof trace.mcp_result_envelope === 'object'
        ? trace.mcp_result_envelope
        : null;
  const normalized = {
    ...data,
  };

  if (typeof normalized.description !== 'string' && typeof normalized.instruction === 'string') {
    normalized.description = normalized.instruction;
  }
  if (typeof normalized.instruction !== 'string' && typeof normalized.description === 'string') {
    normalized.instruction = normalized.description;
  }
  if (typeof normalized.provider_label !== 'string' && typeof trace.provider_label === 'string') {
    normalized.provider_label = trace.provider_label;
  }
  if (
    typeof normalized.mcp_execution_mode !== 'string' &&
    typeof trace.mcp_execution_mode === 'string'
  ) {
    normalized.mcp_execution_mode = trace.mcp_execution_mode;
  }
  if (
    typeof normalized.mcp_preferred_execution_mode !== 'string' &&
    typeof trace.mcp_preferred_execution_mode === 'string'
  ) {
    normalized.mcp_preferred_execution_mode = trace.mcp_preferred_execution_mode;
  }
  if (
    typeof normalized.mcp_execution_mode !== 'string' &&
    typeof resultEnvelope?.execution_mode === 'string'
  ) {
    normalized.mcp_execution_mode = resultEnvelope.execution_mode;
  }
  if (
    typeof normalized.mcp_preferred_execution_mode !== 'string' &&
    typeof resultEnvelope?.preferred_execution_mode === 'string'
  ) {
    normalized.mcp_preferred_execution_mode = resultEnvelope.preferred_execution_mode;
  }
  if (typeof normalized.result_preview !== 'string') {
    if (typeof trace.mcp_result_preview === 'string') {
      normalized.result_preview = trace.mcp_result_preview;
    } else if (typeof resultEnvelope?.summary === 'string') {
      normalized.result_preview = resultEnvelope.summary;
    }
  }
  if (normalized.result_output === undefined) {
    if (trace.mcp_result_output !== undefined) {
      normalized.result_output = trace.mcp_result_output;
    } else if (resultEnvelope && resultEnvelope.structured_output !== undefined) {
      normalized.result_output = resultEnvelope.structured_output;
    }
  }
  if (!normalized.result_envelope && resultEnvelope) {
    normalized.result_envelope = resultEnvelope;
  }
  if (!Array.isArray(normalized.follow_up_actions) && Array.isArray(resultEnvelope?.follow_up_actions)) {
    normalized.follow_up_actions = resultEnvelope.follow_up_actions;
  }
  if (!Array.isArray(normalized.media_attachments) && Array.isArray(trace.wearables_dat_media)) {
    normalized.media_attachments = trace.wearables_dat_media;
  }

  return normalized;
}

function normalizeAgentTaskListResponse(data) {
  if (!data || typeof data !== 'object') {
    throw new Error('Agent task list returned an invalid response payload');
  }

  return {
    ...data,
    tasks: Array.isArray(data.tasks) ? data.tasks.map(normalizeAgentTask) : [],
  };
}

function normalizePeerChatMessage(message) {
  if (!message || typeof message !== 'object') {
    return message;
  }

  return {
    ...message,
    task_snapshot: normalizeFollowOnTask(message.task_snapshot),
  };
}

function normalizePeerChatHistoryResponse(data) {
  if (!data || typeof data !== 'object') {
    throw new Error('Peer chat history returned an invalid response payload');
  }

  return {
    ...data,
    messages: Array.isArray(data.messages) ? data.messages.map(normalizePeerChatMessage) : [],
  };
}

function normalizePeerChatConversationsResponse(data) {
  if (!data || typeof data !== 'object') {
    throw new Error('Peer chat conversations returned an invalid response payload');
  }

  return {
    ...data,
    conversations: Array.isArray(data.conversations)
      ? data.conversations.map(normalizePeerChatMessage)
      : [],
  };
}

function normalizePeerChatOutboxResponse(data) {
  if (!data || typeof data !== 'object') {
    throw new Error('Peer chat outbox returned an invalid response payload');
  }

  return {
    ...data,
    messages: Array.isArray(data.messages) ? data.messages.map(normalizePeerChatMessage) : [],
    preview_messages: Array.isArray(data.preview_messages)
      ? data.preview_messages.map(normalizePeerChatMessage)
      : [],
  };
}

function normalizePeerEnvelopeResponse(data) {
  if (!data || typeof data !== 'object') {
    throw new Error('Peer envelope returned an invalid response payload');
  }

  return {
    ...data,
    payload_json:
      data.payload_json && typeof data.payload_json === 'object'
        ? normalizePeerChatMessage(data.payload_json)
        : data.payload_json ?? null,
  };
}

/**
 * Get backend status
 * @returns {Promise<Object>} Status object with { status, version, user_id }
 */
export async function getStatus() {
  const baseUrl = await getBaseUrl();
  const headers = await getHeaders(false); // Status doesn't require auth

  const response = await fetch(`${baseUrl}/v1/status`, {
    method: 'GET',
    headers,
  });

  if (!response.ok) {
    throw new Error(`Status check failed: ${response.status}`);
  }

  return normalizeCommandResponse(await response.json());
}

/**
 * Send a text command to the backend
 * @param {string} text - The command text
 * @param {Object} options - Optional parameters
 * @returns {Promise<Object>} Command response with spoken_text, ui_cards, etc.
 */
export async function sendCommand(text, options = {}) {
  const baseUrl = await getBaseUrl();
  const headers = await getHeaders();

  const body = {
    input: {
      type: 'text',
      text,
    },
    profile: defaultProfile(options.profile),
    client_context: defaultClientContext(options.client_context),
    idempotency_key: options.idempotency_key || undefined,
  };

  const response = await fetch(`${baseUrl}/v1/command`, {
    method: 'POST',
    headers,
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.error || `Command failed: ${response.status}`);
  }

  return normalizeCommandResponse(await response.json());
}

function buildWearablesBridgeDelegationPrompt(device = {}, options = {}) {
  const deviceName = device?.deviceName || device?.deviceId || 'connected wearable target';
  const targetState = device?.targetConnectionState || 'connected';
  const parts = [
    `Delegate to an agent: inspect the ${deviceName} wearables bridge target connection.`,
    `Use the MCP and IPFS toolchain to capture a connectivity receipt and summarize next steps.`,
    `Target state is ${targetState}.`,
  ];

  if (device?.deviceId) {
    parts.push(`Device id: ${device.deviceId}.`);
  }
  if (device?.targetRssi != null) {
    parts.push(`Observed RSSI: ${device.targetRssi}.`);
  }
  if (device?.targetLastSeenAt) {
    parts.push(`Last seen at unix ms ${device.targetLastSeenAt}.`);
  }
  if (options?.extraContext) {
    parts.push(String(options.extraContext));
  }

  return parts.join(' ');
}

export async function delegateWearablesBridgeTask(device = {}, options = {}) {
  const prompt = buildWearablesBridgeDelegationPrompt(device, options);
  return await sendCommand(prompt, {
    ...options,
    client_context: defaultClientContext({
      feature: 'wearables_bridge',
      trigger: 'target_connected',
      device_id: device?.deviceId || null,
      device_name: device?.deviceName || null,
      target_connection_state: device?.targetConnectionState || null,
      target_last_seen_at: device?.targetLastSeenAt || null,
      target_rssi: device?.targetRssi ?? null,
      ...(options.client_context || {}),
    }),
  });
}

/**
 * Send a structured card action to the backend.
 * @param {string} actionId - Stable action identifier from card.action_items[]
 * @param {Object} options - Optional action parameters and request metadata
 * @returns {Promise<Object>} Command response with spoken_text, cards, etc.
 */
export async function sendActionCommand(actionId, options = {}) {
  const baseUrl = await getBaseUrl();
  const headers = await getHeaders();

  const body = {
    action_id: actionId,
    params: options.params || {},
    profile: defaultProfile(options.profile),
    client_context: defaultClientContext(options.client_context),
    idempotency_key: options.idempotency_key || undefined,
  };

  const response = await fetch(`${baseUrl}/v1/commands/action`, {
    method: 'POST',
    headers,
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.error || `Action failed: ${response.status}`);
  }

  return normalizeCommandResponse(await response.json());
}

/**
 * Send an audio command to the backend.
 * Note: the backend expects an audio URI it can fetch (https:// or file:// for dev).
 */
export async function sendAudioCommand(uri, format = 'm4a', options = {}) {
  const baseUrl = await getBaseUrl();
  const headers = await getHeaders();

  const body = {
    input: {
      type: 'audio',
      format,
      uri,
      duration_ms: options.duration_ms || undefined,
    },
    profile: defaultProfile(options.profile),
    client_context: defaultClientContext(options.client_context),
    idempotency_key: options.idempotency_key || undefined,
  };

  const response = await fetch(`${baseUrl}/v1/command`, {
    method: 'POST',
    headers,
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.error || `Command failed: ${response.status}`);
  }

  return normalizeCommandResponse(await response.json());
}

/**
 * Confirm a pending action
 * @param {string} actionId - The action ID to confirm
 * @param {string} choice - One of: 'confirm', 'cancel', 'repeat', 'next'
 * @returns {Promise<Object>} Confirmation response
 */
export async function confirmCommand(token, idempotencyKey = undefined) {
  const baseUrl = await getBaseUrl();
  const headers = await getHeaders();

  const body = {
    token,
    idempotency_key: idempotencyKey,
  };

  const response = await fetch(`${baseUrl}/v1/commands/confirm`, {
    method: 'POST',
    headers,
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.error || `Confirmation failed: ${response.status}`);
  }

  return normalizeCommandResponse(await response.json());
}

/**
 * Fetch TTS audio for given text
 * @param {string} text - Text to convert to speech
 * @param {Object} [options] - Optional TTS configuration
 * @param {string} [options.format='wav'] - Output audio format (e.g. 'wav')
 * @param {string} [options.voice] - Voice identifier to use for synthesis
 * @param {string} [options.accept] - Value for the HTTP Accept header (e.g. 'audio/wav')
 * @returns {Promise<Blob>} Audio data as blob
 */
export async function fetchTTS(text, options = {}) {
  const baseUrl = await getBaseUrl();
  const headers = await getHeaders();

  if (options.accept) {
    headers.Accept = options.accept;
  }

  const body = {
    text,
    format: options.format || 'wav',
    voice: options.voice || undefined,
  };

  // Add format to body if specified
  if (options.format) {
    body.format = options.format;
  }

  const response = await fetch(`${baseUrl}/v1/tts`, {
    method: 'POST',
    headers,
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    throw new Error(`TTS failed: ${response.status}`);
  }

  return await response.blob();
}

/**
 * Get notifications (polling fallback)
 * @param {Object} options - Optional query params
 * @returns {Promise<Object>} Notification list response
 */
export async function getNotifications(options = {}) {
  const baseUrl = await getBaseUrl();
  const headers = await getHeaders();
  const params = new URLSearchParams();

  if (options.since) {
    params.append('since', options.since);
  }
  if (typeof options.limit === 'number') {
    params.append('limit', String(options.limit));
  }

  const queryString = params.toString();
  const url = `${baseUrl}/v1/notifications${queryString ? `?${queryString}` : ''}`;

  const response = await fetch(url, {
    method: 'GET',
    headers,
  });

  if (!response.ok) {
    throw new Error(`Get notifications failed: ${response.status}`);
  }

  return await response.json();
}

/**
 * Get a single notification by id.
 * @param {string} notificationId - Notification identifier
 * @returns {Promise<Object>} Notification detail response
 */
export async function getNotificationDetail(notificationId) {
  const baseUrl = await getBaseUrl();
  const headers = await getHeaders();

  const response = await fetch(
    `${baseUrl}/v1/notifications/${encodeURIComponent(notificationId)}`,
    {
      method: 'GET',
      headers,
    }
  );

  if (!response.ok) {
    throw new Error(`Get notification failed: ${response.status}`);
  }

  return await response.json();
}

/**
 * Get completed MCP-backed task results with optional saved-view filtering.
 * @param {Object} options - Optional query params
 * @returns {Promise<Object>} Results feed response
 */
export async function getAgentResults(options = {}) {
  const baseUrl = await getBaseUrl();
  const headers = await getHeaders();
  const params = new URLSearchParams();

  if (options.view) {
    params.append('view', options.view);
  }
  if (options.provider) {
    params.append('provider', options.provider);
  }
  if (options.capability) {
    params.append('capability', options.capability);
  }
  if (options.preset) {
    params.append('preset', options.preset);
  }
  if (typeof options.latest_only === 'boolean') {
    params.append('latest_only', String(options.latest_only));
  }
  if (options.sort) {
    params.append('sort', options.sort);
  }
  if (options.direction) {
    params.append('direction', options.direction);
  }
  if (typeof options.limit === 'number') {
    params.append('limit', String(options.limit));
  }
  if (typeof options.offset === 'number') {
    params.append('offset', String(options.offset));
  }

  const queryString = params.toString();
  const url = `${baseUrl}/v1/agents/results${queryString ? `?${queryString}` : ''}`;

  const response = await fetch(url, {
    method: 'GET',
    headers,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.error || `Get agent results failed: ${response.status}`);
  }

  return await response.json();
}

/**
 * Get a single agent task detail record.
 * @param {string} taskId - Agent task identifier
 * @returns {Promise<Object>} Task detail response
 */
export async function getAgentTaskDetail(taskId) {
  const baseUrl = await getBaseUrl();
  const headers = await getHeaders();

  const response = await fetch(
    `${baseUrl}/v1/agents/tasks/${encodeURIComponent(taskId)}`,
    {
      method: 'GET',
      headers,
    }
  );

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.error || `Get agent task failed: ${response.status}`);
  }

  return normalizeAgentTask(await response.json());
}

/**
 * Get agent tasks with optional status/provider filters.
 * @param {Object} options - Optional query params
 * @returns {Promise<Object>} Task list response
 */
export async function getAgentTasks(options = {}) {
  const baseUrl = await getBaseUrl();
  const headers = await getHeaders();
  const params = new URLSearchParams();

  if (options.status) {
    params.append('status', options.status);
  }
  if (options.provider) {
    params.append('provider', options.provider);
  }
  if (options.capability) {
    params.append('capability', options.capability);
  }
  if (options.result_view) {
    params.append('result_view', options.result_view);
  }
  if (typeof options.results_only === 'boolean') {
    params.append('results_only', String(options.results_only));
  }
  if (options.sort) {
    params.append('sort', options.sort);
  }
  if (options.direction) {
    params.append('direction', options.direction);
  }
  if (typeof options.limit === 'number') {
    params.append('limit', String(options.limit));
  }
  if (typeof options.offset === 'number') {
    params.append('offset', String(options.offset));
  }

  const queryString = params.toString();
  const url = `${baseUrl}/v1/agents/tasks${queryString ? `?${queryString}` : ''}`;

  const response = await fetch(url, {
    method: 'GET',
    headers,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.error || `Get agent tasks failed: ${response.status}`);
  }

  return normalizeAgentTaskListResponse(await response.json());
}

/**
 * Invoke a task lifecycle control endpoint.
 * @param {string} taskId - Agent task identifier
 * @param {'start'|'complete'|'fail'|'pause'|'resume'|'cancel'} action - Lifecycle action
 * @returns {Promise<Object>} Task control response
 */
export async function postAgentTaskControl(taskId, action) {
  const allowedActions = new Set(['start', 'complete', 'fail', 'pause', 'resume', 'cancel']);
  if (!allowedActions.has(action)) {
    throw new Error(`Unsupported task control action: ${action}`);
  }

  const baseUrl = await getBaseUrl();
  const headers = await getHeaders();

  const response = await fetch(
    `${baseUrl}/v1/agents/tasks/${encodeURIComponent(taskId)}/${action}`,
    {
      method: 'POST',
      headers,
    }
  );

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.error || `Task ${action} failed: ${response.status}`);
  }

  return normalizeAgentTaskControlResponse(await response.json());
}

/**
 * Get inbox items (PRs, mentions, failing checks)
 * @param {Object} options - Optional parameters
 * @returns {Promise<Object>} Inbox response
 */
export async function getInbox(options = {}) {
  const baseUrl = await getBaseUrl();
  const headers = await getHeaders();

  // Build query params
  const params = new URLSearchParams();
  if (options.profile) {
    params.append('profile', options.profile);
  }

  const queryString = params.toString();
  const url = `${baseUrl}/v1/inbox${queryString ? `?${queryString}` : ''}`;

  const response = await fetch(url, {
    method: 'GET',
    headers,
  });

  if (!response.ok) {
    throw new Error(`Get inbox failed: ${response.status}`);
  }

  return await response.json();
}

export async function attachAgentTaskMedia(taskId, media = {}) {
  const baseUrl = await getBaseUrl();
  const headers = await getHeaders();

  const response = await fetch(`${baseUrl}/v1/agents/tasks/${taskId}/media`, {
    method: 'POST',
    headers,
    body: JSON.stringify(media),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail?.message || errorData.message || `Task media attach failed: ${response.status}`);
  }

  return await response.json();
}

/**
 * Upload audio bytes to dev endpoint and get file:// URI
 * @param {string} audioBase64 - Base64-encoded audio data
 * @param {string} format - Audio format (m4a, wav, mp3, opus)
 * @returns {Promise<Object>} Object with { uri, format }
 */
export async function uploadDevAudio(audioBase64, format = 'm4a') {
  return await uploadDevMedia(audioBase64, {
    media_kind: 'audio',
    format,
  }, '/v1/dev/audio');
}

/**
 * Upload generic media bytes to a dev endpoint and get a file:// URI.
 * @param {string} dataBase64 - Base64-encoded media data
 * @param {Object} options - Media metadata such as format, media_kind, and mime_type
 * @param {string} pathname - Endpoint pathname override for compatibility wrappers
 * @returns {Promise<Object>} Object with upload metadata including uri and bytes
 */
export async function uploadDevMedia(dataBase64, options = {}, pathname = '/v1/dev/media') {
  const baseUrl = await getBaseUrl();
  const headers = await getHeaders();

  const body = {
    data_base64: dataBase64,
    format: options.format || 'jpg',
    media_kind: options.media_kind || 'image',
    mime_type: options.mime_type || undefined,
  };

  const response = await fetch(`${baseUrl}${pathname}`, {
    method: 'POST',
    headers,
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.message || `Upload failed: ${response.status}`);
  }

  return await response.json();
}

async function throwPeerChatClientError(response, fallbackMessage) {
  const errorData = await response.json().catch(() => ({}));
  throw new Error(
    errorData.detail?.message || errorData.message || `${fallbackMessage}: ${response.status}`
  );
}

async function fetchPeerChatJson(url, options, fallbackMessage) {
  const response = await fetch(url, options);
  if (!response.ok) {
    await throwPeerChatClientError(response, fallbackMessage);
  }
  return await response.json();
}

async function peerChatRequest(pathname, {
  method = 'GET',
  body = undefined,
  searchParams = null,
  fallbackMessage,
} = {}) {
  const baseUrl = await getBaseUrl();
  const headers = await getHeaders();
  const url = new URL(pathname, baseUrl);

  if (searchParams) {
    Object.entries(searchParams).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        url.searchParams.set(key, String(value));
      }
    });
  }

  return await fetchPeerChatJson(
    url.toString(),
    {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    },
    fallbackMessage
  );
}

/**
 * Validate a peer transport frame against the backend dev ingress endpoint.
 * @param {string} peerRef - Stable peer reference from the mobile bridge
 * @param {string} frameBase64 - Base64-encoded transport envelope
 * @returns {Promise<Object>} Dev ingress response with optional ack_frame_base64
 */
export async function postDevPeerEnvelope(peerRef, frameBase64) {
  const response = await peerChatRequest('/v1/dev/peer-envelope', {
    method: 'POST',
    body: {
      peer_ref: peerRef,
      frame_base64: frameBase64,
    },
    fallbackMessage: 'Peer envelope validation failed',
  });

  return normalizePeerEnvelopeResponse(response);
}

/**
 * Fetch stored dev peer chat history for a conversation.
 * @param {string} conversationId - Stable dev conversation id
 * @returns {Promise<Object>} Chat history response
 */
export async function getDevPeerChatHistory(conversationId) {
  const response = await peerChatRequest(`/v1/dev/peer-chat/${encodeURIComponent(conversationId)}`, {
    fallbackMessage: 'Peer chat history fetch failed',
  });

  return normalizePeerChatHistoryResponse(response);
}

/**
 * Fetch recent dev peer chat conversations.
 * @param {number} limit - Maximum number of conversations to return
 * @returns {Promise<Object>} Recent chat conversation summaries
 */
export async function getDevPeerChatConversations(limit = 20) {
  const response = await peerChatRequest('/v1/dev/peer-chat', {
    searchParams: { limit },
    fallbackMessage: 'Peer chat conversations fetch failed',
  });

  return normalizePeerChatConversationsResponse(response);
}

/**
 * Send an outbound dev peer chat message through the backend transport surface.
 * @param {string} peerId - Target remote peer id
 * @param {string} text - Chat message text
 * @param {string | null} conversationId - Optional conversation id
 * @param {string} priority - Message delivery priority: normal or urgent
 * @returns {Promise<Object>} Outbound chat send response
 */
export async function postDevPeerChatSend(
  peerId,
  text,
  conversationId = null,
  priority = 'normal',
  taskId = null
) {
  const response = await peerChatRequest('/v1/dev/peer-chat/send', {
    method: 'POST',
    body: {
      peer_id: peerId,
      text,
      conversation_id: conversationId,
      priority,
      task_id: taskId,
    },
    fallbackMessage: 'Peer chat send failed',
  });

  return normalizePeerChatMessage(response);
}

/**
 * Fetch queued outbound dev peer chat messages for a handset peer id.
 * @param {string} peerId - Recipient handset peer id
 * @param {number | undefined} leaseMs - Visibility lease duration for fetched messages
 * @returns {Promise<Object>} Outbox response
 */
export async function getDevPeerChatOutbox(peerId, leaseMs = undefined) {
  const response = await peerChatRequest(`/v1/dev/peer-chat/outbox/${encodeURIComponent(peerId)}`, {
    searchParams: { lease_ms: leaseMs },
    fallbackMessage: 'Peer chat outbox fetch failed',
  });

  return normalizePeerChatOutboxResponse(response);
}

/**
 * Fetch backend peer chat outbox status without leasing messages.
 * @param {string} peerId - Recipient handset peer id
 * @returns {Promise<Object>} Outbox status response
 */
export async function getDevPeerChatOutboxStatus(peerId) {
  const response = await peerChatRequest(`/v1/dev/peer-chat/outbox/${encodeURIComponent(peerId)}/status`, {
    fallbackMessage: 'Peer chat outbox status failed',
  });

  return normalizePeerChatOutboxResponse(response);
}

/**
 * Acknowledge handset-delivered dev peer chat outbox messages.
 * @param {string} peerId - Recipient handset peer id
 * @param {string[]} outboxMessageIds - Queue message ids that were replayed successfully
 * @returns {Promise<Object>} Outbox ack response
 */
export async function postDevPeerChatOutboxAck(peerId, outboxMessageIds) {
  return await peerChatRequest(`/v1/dev/peer-chat/outbox/${encodeURIComponent(peerId)}/ack`, {
    method: 'POST',
    body: {
      outbox_message_ids: outboxMessageIds,
    },
    fallbackMessage: 'Peer chat outbox ack failed',
  });
}

/**
 * Release leased outbox messages back into a deliverable state.
 * @param {string} peerId - Recipient handset peer id
 * @param {string[]} outboxMessageIds - Queue message ids to release
 * @returns {Promise<Object>} Outbox release response
 */
export async function postDevPeerChatOutboxRelease(peerId, outboxMessageIds) {
  return await peerChatRequest(`/v1/dev/peer-chat/outbox/${encodeURIComponent(peerId)}/release`, {
    method: 'POST',
    body: {
      outbox_message_ids: outboxMessageIds,
    },
    fallbackMessage: 'Peer chat outbox release failed',
  });
}

/**
 * Promote queued outbox messages to urgent priority.
 * @param {string} peerId - Recipient handset peer id
 * @param {string[]} outboxMessageIds - Queue message ids to promote
 * @returns {Promise<Object>} Outbox promote response
 */
export async function postDevPeerChatOutboxPromote(peerId, outboxMessageIds) {
  return await peerChatRequest(`/v1/dev/peer-chat/outbox/${encodeURIComponent(peerId)}/promote`, {
    method: 'POST',
    body: {
      outbox_message_ids: outboxMessageIds,
    },
    fallbackMessage: 'Peer chat outbox promote failed',
  });
}

/**
 * Record a lightweight handset heartbeat for the backend relay.
 * @param {string} peerId - Local handset peer id
 * @param {string | null} displayName - Optional local display name
 * @returns {Promise<Object>} Handset session response
 */
export async function postDevPeerChatHandsetHeartbeat(peerId, displayName = null) {
  return await peerChatRequest(`/v1/dev/peer-chat/handsets/${encodeURIComponent(peerId)}/heartbeat`, {
    method: 'POST',
    body: {
      display_name: displayName,
    },
    fallbackMessage: 'Peer chat handset heartbeat failed',
  });
}

/**
 * Fetch backend-observed handset relay session state.
 * @param {string} peerId - Local handset peer id
 * @returns {Promise<Object>} Handset session response
 */
export async function getDevPeerChatHandsetSession(peerId) {
  return await peerChatRequest(`/v1/dev/peer-chat/handsets/${encodeURIComponent(peerId)}`, {
    fallbackMessage: 'Peer chat handset status failed',
  });
}

/**
 * Fetch persisted backend transport session cursors for diagnostics.
 * @returns {Promise<Object>} Transport session diagnostics response
 */
export async function getDevTransportSessions() {
  return await peerChatRequest('/v1/dev/transport-sessions', {
    fallbackMessage: 'Transport session list failed',
  });
}

/**
 * Clear a persisted backend transport session cursor by peer id.
 * @param {string} peerId - Remote peer id whose transport cursor should be cleared
 * @returns {Promise<Object>} Clear response
 */
export async function deleteDevTransportSession(peerId) {
  return await peerChatRequest(`/v1/dev/transport-sessions/${encodeURIComponent(peerId)}`, {
    method: 'DELETE',
    fallbackMessage: 'Transport session clear failed',
  });
}

/**
 * Start GitHub OAuth flow
 * @param {string} scopes - Optional comma-separated OAuth scopes
 * @returns {Promise<Object>} Object with { authorize_url, state }
 */
export async function startGitHubOAuth(scopes = null) {
  const baseUrl = await getBaseUrl();
  const headers = await getHeaders();

  const url = new URL('/v1/github/oauth/start', baseUrl);
  if (scopes) {
    url.searchParams.set('scopes', scopes);
  }

  const response = await fetch(url.toString(), {
    method: 'GET',
    headers,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(
      errorData.error?.message || errorData.message || `OAuth start failed: ${response.status}`
    );
  }

  return await response.json();
}

/**
 * Complete GitHub OAuth callback
 * @param {string} code - Authorization code from GitHub
 * @param {string} state - State parameter for CSRF validation
 * @returns {Promise<Object>} Object with { connection_id, scopes }
 */
export async function completeGitHubOAuth(code, state) {
  const baseUrl = await getBaseUrl();
  const headers = await getHeaders();

  const url = new URL('/v1/github/oauth/callback', baseUrl);
  url.searchParams.set('code', code);
  url.searchParams.set('state', state);

  const response = await fetch(url.toString(), {
    method: 'GET',
    headers,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(
      errorData.error?.message || errorData.message || `OAuth callback failed: ${response.status}`
    );
  }

  return await response.json();
}
