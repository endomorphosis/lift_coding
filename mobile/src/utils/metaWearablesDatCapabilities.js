const CAPABILITY_LABELS = {
  session: 'session',
  camera: 'camera',
  photoCapture: 'photo',
  videoStream: 'video',
  audio: 'audio',
};

function buildCapabilityEntries(capabilities = {}) {
  return Object.entries(CAPABILITY_LABELS).map(([key, label]) => ({
    key,
    label,
    available: Boolean(capabilities?.[key]),
  }));
}

export function summarizeMetaWearablesDat(diagnostics) {
  const entries = buildCapabilityEntries(diagnostics?.capabilities);
  const availableCapabilities = entries.filter((entry) => entry.available).map((entry) => entry.label);
  const unavailableCapabilities = entries
    .filter((entry) => !entry.available)
    .map((entry) => entry.label);

  let readiness = 'unavailable';
  if (diagnostics?.available) {
    if (diagnostics?.sdkLinked && diagnostics?.sdkConfigured) {
      readiness = 'sdk_ready';
    } else if (diagnostics?.sdkLinked) {
      readiness = 'sdk_linked';
    } else {
      readiness = 'bridge_ready';
    }
  }

  return {
    readiness,
    availableCapabilities,
    unavailableCapabilities,
    availableSummary: availableCapabilities.join(', ') || 'none',
    matrixSummary: entries
      .map((entry) => `${entry.label}:${entry.available ? 'on' : 'off'}`)
      .join(', '),
  };
}

export { CAPABILITY_LABELS };