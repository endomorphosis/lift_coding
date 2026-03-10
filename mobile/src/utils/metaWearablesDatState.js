export function mergeMetaWearablesDatState(current, event) {
  if (!event || typeof event !== 'object') {
    return current || null;
  }

  return {
    ...(current || {}),
    sessionState: event.sessionState || event.state || current?.sessionState || 'unknown',
    activeDeviceId: event.deviceId ?? current?.activeDeviceId ?? null,
    selectedDeviceId: event.deviceId ?? current?.selectedDeviceId ?? null,
    selectedDeviceName: event.deviceName ?? current?.selectedDeviceName ?? null,
    targetConnectionState: event.targetConnectionState ?? current?.targetConnectionState ?? 'unknown',
    targetLastSeenAt: event.targetLastSeenAt ?? current?.targetLastSeenAt ?? null,
    targetRssi: event.targetRssi ?? current?.targetRssi ?? null,
  };
}