export const HALLUCINATE_APP_MOBILE_HANDOFF_CONTRACT =
  'handsfree.hallucinate_app/mobile-handoff@0.1.0';

export const HALLUCINATE_APP_MOBILE_INTERFACE_DESCRIPTOR =
  'hallucinate_app.mobile.interface_descriptor.v1';

export const HALLUCINATE_APP_MOBILE_OPERATIONS = [
  'search',
  'filter',
  'clear',
  'module_test',
  'benchmark_telemetry',
];

export const HALLUCINATE_APP_MOBILE_REQUIRED_FIELDS = [
  'contract',
  'descriptor',
  'operation',
  'request_id',
  'source',
  'target',
  'payload',
  'handoff',
  'policy',
  'created_at',
];

const OPERATION_SET = new Set(HALLUCINATE_APP_MOBILE_OPERATIONS);

function isObject(value) {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
}

function randomSuffix() {
  return Math.random().toString(16).slice(2, 10);
}

function nowIso() {
  return new Date().toISOString();
}

export function normalizeHallucinateAppMobileOperation(operation) {
  const normalized = String(operation || '').trim();
  if (!OPERATION_SET.has(normalized)) {
    throw new Error(`Unsupported hallucinate_app mobile operation: ${operation}`);
  }
  return normalized;
}

export function buildHallucinateAppMobileHandoff({
  operation = 'search',
  requestId,
  source = 'hallucinate_app',
  target = 'mobile',
  payload = {},
  handoff = {},
  policy = {},
  createdAt,
} = {}) {
  const normalizedOperation = normalizeHallucinateAppMobileOperation(operation);
  const normalizedPayload = isObject(payload) ? payload : { value: payload };

  return {
    contract: HALLUCINATE_APP_MOBILE_HANDOFF_CONTRACT,
    descriptor: HALLUCINATE_APP_MOBILE_INTERFACE_DESCRIPTOR,
    operation: normalizedOperation,
    request_id: requestId || `hao-mobile-${Date.now()}-${randomSuffix()}`,
    source,
    target,
    payload: normalizedPayload,
    handoff: {
      transport: 'local-ipc-or-http',
      route: 'hallucinate_app.dashboard.mobile_handoff',
      mobile_surface: 'handsfree-mobile',
      receipt_required: true,
      ...handoff,
    },
    policy: {
      user_visible: true,
      requires_mobile_ack: true,
      ...policy,
    },
    created_at: createdAt || nowIso(),
  };
}

export function validateHallucinateAppMobileHandoff(handoff) {
  if (!isObject(handoff)) {
    return { valid: false, errors: ['handoff must be an object'] };
  }

  const errors = [];
  HALLUCINATE_APP_MOBILE_REQUIRED_FIELDS.forEach((field) => {
    if (handoff[field] === undefined || handoff[field] === null || handoff[field] === '') {
      errors.push(`missing field: ${field}`);
    }
  });

  if (handoff.contract !== HALLUCINATE_APP_MOBILE_HANDOFF_CONTRACT) {
    errors.push(`contract must be ${HALLUCINATE_APP_MOBILE_HANDOFF_CONTRACT}`);
  }
  if (handoff.descriptor !== HALLUCINATE_APP_MOBILE_INTERFACE_DESCRIPTOR) {
    errors.push(`descriptor must be ${HALLUCINATE_APP_MOBILE_INTERFACE_DESCRIPTOR}`);
  }
  if (!OPERATION_SET.has(handoff.operation)) {
    errors.push(`operation must be one of ${HALLUCINATE_APP_MOBILE_OPERATIONS.join(', ')}`);
  }
  if (!isObject(handoff.payload)) {
    errors.push('payload must be an object');
  }
  if (!isObject(handoff.handoff)) {
    errors.push('handoff must be an object');
  }
  if (!isObject(handoff.policy)) {
    errors.push('policy must be an object');
  }

  return { valid: errors.length === 0, errors };
}

export function createHallucinateAppMobileReceipt(handoff, {
  status = 'accepted',
  mobileSessionId,
  receivedAt,
  details = {},
} = {}) {
  const validation = validateHallucinateAppMobileHandoff(handoff);
  if (!validation.valid) {
    throw new Error(`Invalid hallucinate_app mobile handoff: ${validation.errors.join('; ')}`);
  }

  return {
    contract: HALLUCINATE_APP_MOBILE_HANDOFF_CONTRACT,
    descriptor: HALLUCINATE_APP_MOBILE_INTERFACE_DESCRIPTOR,
    request_id: handoff.request_id,
    operation: handoff.operation,
    status,
    source: 'mobile',
    target: 'hallucinate_app',
    mobile_session_id: mobileSessionId || `mobile-${handoff.request_id}`,
    received_at: receivedAt || nowIso(),
    details,
  };
}

