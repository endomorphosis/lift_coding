// Shared Backend Client for Mobile Push Notifications
//
// This module provides a unified interface for interacting with the
// HandsFree backend API for push notifications, TTS, and polling.
//
// Usage:
// 1. Configure BACKEND_URL and USER_ID
// 2. Import functions as needed in your mobile app

/**
 * Configuration
 */
export const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8080';
export const USER_ID = process.env.USER_ID || '00000000-0000-0000-0000-000000000001';

/**
 * Type definitions
 */
export interface NotificationSubscription {
  id: string;
  user_id: string;
  endpoint: string;
  platform: 'apns' | 'fcm' | 'expo';
  subscription_keys?: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface Notification {
  id: string;
  user_id: string;
  event_type: string;
  message: string;
  data: Record<string, any>;
  priority: 'low' | 'medium' | 'high';
  created_at: string;
  read_at: string | null;
}

export interface TTSRequest {
  text: string;
  format?: 'mp3' | 'wav';
  voice?: string;
}

/**
 * Register push notification subscription with backend
 */
export async function registerPushSubscription(
  token: string,
  platform: 'apns' | 'fcm' | 'expo'
): Promise<NotificationSubscription> {
  const response = await fetch(`${BACKEND_URL}/v1/notifications/subscriptions`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-User-ID': USER_ID,
    },
    body: JSON.stringify({
      endpoint: token,
      platform: platform,
    }),
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Failed to register subscription: ${response.statusText} - ${error}`);
  }

  return await response.json();
}

/**
 * List all push notification subscriptions for current user
 */
export async function listPushSubscriptions(): Promise<NotificationSubscription[]> {
  const response = await fetch(`${BACKEND_URL}/v1/notifications/subscriptions`, {
    headers: {
      'X-User-ID': USER_ID,
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to list subscriptions: ${response.statusText}`);
  }

  const data = await response.json();
  return data.subscriptions || [];
}

/**
 * Delete a push notification subscription
 */
export async function deletePushSubscription(subscriptionId: string): Promise<void> {
  const response = await fetch(
    `${BACKEND_URL}/v1/notifications/subscriptions/${subscriptionId}`,
    {
      method: 'DELETE',
      headers: {
        'X-User-ID': USER_ID,
      },
    }
  );

  if (!response.ok && response.status !== 204) {
    throw new Error(`Failed to delete subscription: ${response.statusText}`);
  }
}

/**
 * Fetch notifications (polling fallback)
 */
export async function fetchNotifications(
  since?: string,
  limit: number = 50
): Promise<Notification[]> {
  const params = new URLSearchParams();
  if (since) {
    params.append('since', since);
  }
  params.append('limit', limit.toString());

  const response = await fetch(`${BACKEND_URL}/v1/notifications?${params.toString()}`, {
    headers: {
      'X-User-ID': USER_ID,
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch notifications: ${response.statusText}`);
  }

  const data = await response.json();
  return data.notifications || [];
}

/**
 * Fetch TTS audio from backend
 */
export async function fetchTTSAudio(request: TTSRequest): Promise<ArrayBuffer> {
  const response = await fetch(`${BACKEND_URL}/v1/tts`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-User-ID': USER_ID,
    },
    body: JSON.stringify({
      text: request.text,
      format: request.format || 'mp3',
      voice: request.voice || 'default',
    }),
  });

  if (!response.ok) {
    throw new Error(`TTS request failed: ${response.statusText}`);
  }

  return await response.arrayBuffer();
}

/**
 * Check backend health status
 */
export async function checkBackendHealth(): Promise<boolean> {
  try {
    const response = await fetch(`${BACKEND_URL}/v1/status`, {
      headers: {
        'X-User-ID': USER_ID,
      },
    });

    return response.ok;
  } catch (error) {
    console.error('Backend health check failed:', error);
    return false;
  }
}

/**
 * Submit a command to the backend
 */
export async function submitCommand(
  input: { type: 'text' | 'audio'; text?: string; uri?: string },
  profile: string = 'terse',
  clientContext?: Record<string, any>
): Promise<any> {
  const response = await fetch(`${BACKEND_URL}/v1/command`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-User-ID': USER_ID,
    },
    body: JSON.stringify({
      input,
      profile,
      client_context: clientContext,
    }),
  });

  if (!response.ok) {
    throw new Error(`Command submission failed: ${response.statusText}`);
  }

  return await response.json();
}

/**
 * Polling helper with automatic interval management
 */
export class NotificationPoller {
  private intervalId: NodeJS.Timeout | null = null;
  private lastTimestamp: string | null = null;
  private isPolling: boolean = false;

  constructor(
    private onNotifications: (notifications: Notification[]) => void,
    private intervalMs: number = 30000
  ) {}

  /**
   * Start polling for notifications
   */
  start(): void {
    if (this.isPolling) {
      console.warn('Polling already started');
      return;
    }

    this.isPolling = true;
    this.lastTimestamp = new Date().toISOString();

    this.intervalId = setInterval(async () => {
      try {
        const notifications = await fetchNotifications(this.lastTimestamp || undefined);

        if (notifications.length > 0) {
          this.onNotifications(notifications);

          // Update last timestamp to most recent notification
          const mostRecent = notifications.reduce((latest, n) =>
            new Date(n.created_at) > new Date(latest.created_at) ? n : latest
          );
          this.lastTimestamp = mostRecent.created_at;
        }
      } catch (error) {
        console.error('Polling error:', error);
      }
    }, this.intervalMs);

    console.log(`Started polling every ${this.intervalMs}ms`);
  }

  /**
   * Stop polling
   */
  stop(): void {
    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = null;
      this.isPolling = false;
      console.log('Stopped polling');
    }
  }

  /**
   * Check if currently polling
   */
  isActive(): boolean {
    return this.isPolling;
  }
}

/**
 * Retry helper with exponential backoff
 */
export async function retryWithBackoff<T>(
  fn: () => Promise<T>,
  maxRetries: number = 3,
  baseDelayMs: number = 1000
): Promise<T> {
  let lastError: Error | null = null;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error as Error;

      if (attempt < maxRetries) {
        const delayMs = baseDelayMs * Math.pow(2, attempt);
        console.log(`Retry attempt ${attempt + 1}/${maxRetries} after ${delayMs}ms`);
        await new Promise((resolve) => setTimeout(resolve, delayMs));
      }
    }
  }

  throw lastError;
}

// Example usage:
/*
import {
  registerPushSubscription,
  fetchNotifications,
  fetchTTSAudio,
  NotificationPoller,
} from './backend_client';

// Register push token
const subscription = await registerPushSubscription('device-token-123', 'apns');
console.log('Subscription ID:', subscription.id);

// Fetch notifications manually
const notifications = await fetchNotifications();
console.log('Received notifications:', notifications);

// Generate TTS audio
const audioData = await fetchTTSAudio({ text: 'Hello, developer', format: 'mp3' });

// Start polling with automatic interval
const poller = new NotificationPoller(
  (notifications) => {
    notifications.forEach((n) => console.log('New notification:', n.message));
  },
  30000 // Poll every 30 seconds
);

poller.start();

// Later: stop polling
poller.stop();
*/
