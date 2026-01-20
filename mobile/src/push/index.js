/**
 * Push Notifications Module
 * 
 * Exports all push notification functionality
 */

export {
  registerForPushAsync,
  registerSubscriptionWithBackend,
  unregisterSubscriptionWithBackend,
  listSubscriptions,
} from './pushClient';

export {
  setupNotificationListeners,
  speakNotification,
  startNotificationPolling,
  checkAndSpeakLatestNotification,
  simulateNotificationForDev,
  getDebugState,
} from './notificationsHandler';
