import { clearWearablesBridgeCache, getWearablesBridge } from './wearablesBridge';

let cached = null;

export async function getMetaWearablesDat() {
  if (cached) {
    return cached;
  }

  const bridge = await getWearablesBridge();
  cached = {
    ...bridge,
    isDatAvailable: async () => bridge.isBridgeAvailable(),
  };
  return cached;
}

export function clearMetaWearablesDatCache() {
  cached = null;
  clearWearablesBridgeCache();
}
