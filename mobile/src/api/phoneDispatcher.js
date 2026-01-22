import AsyncStorage from '@react-native-async-storage/async-storage';

const STORAGE_KEYS = {
  PHONE_DISPATCHER_URL: '@handsfree_phone_dispatcher_url',
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

export async function setPhoneDispatcherUrl(url) {
  const normalized = normalizeBaseUrl(url);
  await AsyncStorage.setItem(STORAGE_KEYS.PHONE_DISPATCHER_URL, normalized);
}

export async function dispatchViaPhone({ title, body = '', labels = [] }) {
  const baseUrl = await getPhoneDispatcherUrl();
  if (!baseUrl) {
    throw new Error('Phone dispatcher URL not configured');
  }

  const resp = await fetch(`${baseUrl}/dispatch`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title, body, labels }),
  });

  if (!resp.ok) {
    const text = await resp.text().catch(() => '');
    throw new Error(`Phone dispatch failed: ${resp.status} ${text}`);
  }

  return await resp.json();
}

export { STORAGE_KEYS as PHONE_DISPATCHER_STORAGE_KEYS };
