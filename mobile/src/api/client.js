/**
 * API Client for Handsfree Backend
 * 
 * Provides methods to interact with:
 * - GET /v1/status
 * - POST /v1/command
 * - POST /v1/commands/confirm
 * - POST /v1/tts
 */

import { BASE_URL, getHeaders } from './config';

/**
 * Get backend status
 * @returns {Promise<Object>} Status object with { status, version, user_id }
 */
export async function getStatus() {
  const response = await fetch(`${BASE_URL}/v1/status`, {
    method: 'GET',
    headers: getHeaders(false), // Status doesn't require auth
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
  const body = {
    text,
    ...options,
  };

  const response = await fetch(`${BASE_URL}/v1/command`, {
    method: 'POST',
    headers: getHeaders(),
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
export async function confirmCommand(actionId, choice = 'confirm') {
  const body = {
    action_id: actionId,
    choice,
  };

  const response = await fetch(`${BASE_URL}/v1/commands/confirm`, {
    method: 'POST',
    headers: getHeaders(),
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
  const body = { text };

  const response = await fetch(`${BASE_URL}/v1/tts`, {
    method: 'POST',
    headers: getHeaders(),
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
  const response = await fetch(`${BASE_URL}/v1/notifications`, {
    method: 'GET',
    headers: getHeaders(),
  });

  if (!response.ok) {
    throw new Error(`Get notifications failed: ${response.status}`);
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
  const body = {
    audio_base64: audioBase64,
    format,
  };

  const response = await fetch(`${BASE_URL}/v1/dev/audio`, {
    method: 'POST',
    headers: getHeaders(),
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.message || `Upload failed: ${response.status}`);
  }

  return await response.json();
}

/**
 * Send an audio command to the backend
 * @param {string} uri - Audio URI (file:// or pre-signed URL)
 * @param {string} format - Audio format (m4a, wav, mp3, opus)
 * @param {number} durationMs - Optional duration in milliseconds
 * @param {Object} options - Optional parameters (profile, client_context)
 * @returns {Promise<Object>} Command response with spoken_text, ui_cards, etc.
 */
export async function sendAudioCommand(uri, format = 'm4a', durationMs = null, options = {}) {
  const body = {
    input: {
      type: 'audio',
      uri,
      format,
      ...(durationMs && { duration_ms: durationMs }),
    },
    profile: options.profile || 'dev',
    client_context: options.client_context || {
      device_type: 'mobile',
      app_version: '1.0.0',
    },
  };

  const response = await fetch(`${BASE_URL}/v1/command`, {
    method: 'POST',
    headers: getHeaders(),
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.error || `Command failed: ${response.status}`);
  }

  return await response.json();
}
