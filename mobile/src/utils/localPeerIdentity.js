import AsyncStorage from '@react-native-async-storage/async-storage';

const LOCAL_PEER_ID_KEY = '@handsfree_local_peer_id';

function randomHex(bytes = 8) {
  const alphabet = '0123456789abcdef';
  let out = '';
  for (let i = 0; i < bytes * 2; i += 1) {
    out += alphabet[Math.floor(Math.random() * alphabet.length)];
  }
  return out;
}

function createLocalPeerId() {
  return `12D3KooWlocal${randomHex(8)}`;
}

export async function getOrCreateLocalPeerId() {
  const existing = await AsyncStorage.getItem(LOCAL_PEER_ID_KEY);
  if (existing) {
    return existing;
  }

  const created = createLocalPeerId();
  await AsyncStorage.setItem(LOCAL_PEER_ID_KEY, created);
  return created;
}
