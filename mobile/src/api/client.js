/**
 * API Client for Handsfree Backend
 *
 * Aligned with spec/openapi.yaml.
 *
 * Endpoints:
 * - GET /v1/status
 * - POST /v1/command
 * - POST /v1/commands/confirm
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

  return await response.json();
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

  return await response.json();
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

  return await response.json();
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

  return await response.json();
}

/**
 * Fetch TTS audio for given text
 * @param {string} text - Text to convert to speech
 * @returns {Promise<Blob>} Audio data as blob
 */
export async function fetchTTS(text) {
  const baseUrl = await getBaseUrl();
  const headers = await getHeaders();

  const body = { text };

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
 * @returns {Promise<Array>} Array of notifications
 */
export async function getNotifications() {
  const baseUrl = await getBaseUrl();
  const headers = await getHeaders();

  const response = await fetch(`${baseUrl}/v1/notifications`, {
    method: 'GET',
    headers,
  });

  if (!response.ok) {
    throw new Error(`Get notifications failed: ${response.status}`);
  }

  return await response.json();
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

/**
 * Upload audio bytes to dev endpoint and get file:// URI
 * @param {string} audioBase64 - Base64-encoded audio data
 * @param {string} format - Audio format (m4a, wav, mp3, opus)
 * @returns {Promise<Object>} Object with { uri, format }
 */
export async function uploadDevAudio(audioBase64, format = 'm4a') {
  const baseUrl = await getBaseUrl();
  const headers = await getHeaders();

  const body = {
    audio_base64: audioBase64,
    format,
  };

  const response = await fetch(`${baseUrl}/v1/dev/audio`, {
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
