import AsyncStorage from '@react-native-async-storage/async-storage';

const STORAGE_KEYS = {
  PHONE_DISPATCHER_URL: '@handsfree_phone_dispatcher_url',
  PHONE_DISPATCHER_SECRET: '@handsfree_phone_dispatcher_secret',
};

function normalizeBaseUrl(url) {
  const trimmed = (url || '').trim();
  if (!trimmed) return '';
  return trimmed.replace(/\/$/, '');
}

export async function getPhoneDispatcherUrl() {
  // Prefer Expo public env var if present (build-time config)
  const envUrl = typeof process !== 'undefined' ? process.env?.EXPO_PUBLIC_PHONE_DISPATCHER_URL : undefined;
  if (envUrl) return normalizeBaseUrl(envUrl);

  const stored = await AsyncStorage.getItem(STORAGE_KEYS.PHONE_DISPATCHER_URL);
  return normalizeBaseUrl(stored);
}

export async function getPhoneDispatcherSecret() {
  const envSecret = typeof process !== 'undefined' ? process.env?.EXPO_PUBLIC_PHONE_DISPATCHER_SECRET : undefined;
  if (envSecret) return String(envSecret).trim();

  const stored = await AsyncStorage.getItem(STORAGE_KEYS.PHONE_DISPATCHER_SECRET);
  return String(stored || '').trim();
}

export async function setPhoneDispatcherSecret(secret) {
  await AsyncStorage.setItem(STORAGE_KEYS.PHONE_DISPATCHER_SECRET, String(secret || '').trim());
}

export async function setPhoneDispatcherUrl(url) {
  const normalized = normalizeBaseUrl(url);
  await AsyncStorage.setItem(STORAGE_KEYS.PHONE_DISPATCHER_URL, normalized);
}

export async function dispatchViaPhone({ title, body = '', labels = [] }) {
  const baseUrl = await getPhoneDispatcherUrl();
  if (!baseUrl) {
    throw new Error('Phone dispatcher URL not configured');
  }

  const secret = await getPhoneDispatcherSecret();

  const headers = { 'Content-Type': 'application/json' };
  if (secret) headers['X-Handsfree-Dispatcher-Secret'] = secret;

  const resp = await fetch(`${baseUrl}/dispatch`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ title, body, labels }),
  });

  if (!resp.ok) {
    const text = await resp.text().catch(() => '');
    throw new Error(`Phone dispatch failed: ${resp.status} ${text}`);
  }

  return await resp.json();
}

export { STORAGE_KEYS as PHONE_DISPATCHER_STORAGE_KEYS };
