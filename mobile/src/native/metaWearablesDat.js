import { clearWearablesBridgeCache, getWearablesBridge } from './wearablesBridge';

let cached = null;

function createMetaWearablesDatAdapter(bridge) {
  return {
    ...bridge,
    isDatAvailable: async () => bridge.isBridgeAvailable(),
    renderDisplayWidget: (...args) => bridge.renderDisplayWidget(...args),
    updateDisplayWidget: (...args) => bridge.updateDisplayWidget(...args),
    clearDisplayWidget: (...args) => bridge.clearDisplayWidget(...args),
    focusDisplayWidget: (...args) => bridge.focusDisplayWidget(...args),
    activateDisplayWidgetAction: (...args) => bridge.activateDisplayWidgetAction(...args),
    resetDisplayWidgetSession: (...args) => bridge.resetDisplayWidgetSession(...args),
    playDisplayWidgetVideo: (...args) => bridge.playDisplayWidgetVideo(...args),
    subscribeDisplayWidgetUpdates: (...args) => bridge.subscribeDisplayWidgetUpdates(...args),
  };
}

export async function getMetaWearablesDat() {
  if (cached) {
    return cached;
  }

  const bridge = await getWearablesBridge();
  cached = createMetaWearablesDatAdapter(bridge);
  return cached;
}

export function clearMetaWearablesDatCache() {
  cached = null;
  clearWearablesBridgeCache();
}
