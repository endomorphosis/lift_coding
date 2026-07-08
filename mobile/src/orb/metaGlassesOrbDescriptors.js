export const MOBILE_ORB_BRIDGE_INTERFACE = {
  name: 'mobile_orb_bridge',
  namespace: 'handsfree.meta_glasses.mobile',
  version: '0.1.0',
  specPath: 'spec/meta_glasses_mobile_orb_bridge_interface.json',
};

export const MOBILE_ORB_BRIDGE_OPERATIONS = [
  'register_edge_capabilities',
  'publish_glasses_event',
  'bind_service',
  'invoke_service',
  'subscribe_service_updates',
  'dispatch_glasses_response',
  'revoke_binding',
];

export const DISPLAY_WIDGET_BRIDGE_INTERFACE = {
  name: 'display_widget_bridge',
  namespace: 'handsfree.meta_glasses.display',
  version: '0.1.0',
  specPath: 'spec/meta_glasses_display_widget_orb_interface.json',
};

export const DISPLAY_WIDGET_BRIDGE_OPERATIONS = [
  'render_widget',
  'update_widget',
  'clear_widget',
  'focus_next',
  'focus_previous',
  'activate',
  'reset_session',
  'play_video',
  'subscribe_updates',
];

export const TASK_STATUS_SERVICE_INTERFACE = {
  name: 'task_status_service',
  namespace: 'handsfree.services.tasks',
  version: '0.1.0',
  metadata: {
    server_family: 'ipfs_datasets',
    tool_name: 'tools_dispatch',
    provider_name: 'ipfs_datasets_mcp',
  },
  methods: [
    {
      name: 'get_task_status',
      inputSchema: {
        type: 'object',
        properties: {
          task_id: { type: 'string' },
        },
      },
      outputSchema: {
        type: 'object',
        properties: {
          status: { type: 'string' },
          display_widget_action: { type: 'object' },
          spoken_text: { type: 'string' },
        },
      },
    },
  ],
  errors: [
    {
      name: 'task_not_found',
      code: 404,
    },
  ],
  requires: [
    'mcp++/profile-a-idl',
    'mcp++/profile-b-cid-artifacts',
    'mcp++/invoke',
    'mcp++/receipts',
  ],
  compatibility: {},
};

export const HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT =
  'interface contract hallucinate_app mobile';

export const HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE = {
  name: 'hallucinate_app_mobile_content_browser',
  namespace: 'handsfree.hallucinate_app.mobile',
  version: '0.1.0',
  objective_id: 'VAIOS-G707',
  contract: HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT,
  source_surface: 'hallucinate_app',
  target_surface: 'mobile',
  methods: [
    {
      name: 'ingest_content_search',
      inputSchema: {
        type: 'object',
        required: ['query', 'filter'],
        properties: {
          query: { type: 'string' },
          filter: { type: 'object' },
          result_limit: { type: ['integer', 'null'] },
        },
      },
      outputSchema: {
        type: 'object',
        properties: {
          accepted: { type: 'boolean' },
          route: { type: 'string' },
        },
      },
    },
    {
      name: 'apply_content_filter',
      inputSchema: {
        type: 'object',
        required: ['filter'],
        properties: {
          filter: { type: 'object' },
        },
      },
      outputSchema: {
        type: 'object',
        properties: {
          accepted: { type: 'boolean' },
        },
      },
    },
    {
      name: 'open_module_test_interface',
      inputSchema: {
        type: 'object',
        properties: {
          module_id: { type: 'string' },
          environment: { type: 'string' },
        },
      },
      outputSchema: {
        type: 'object',
        properties: {
          accepted: { type: 'boolean' },
        },
      },
    },
    {
      name: 'record_benchmark_timeseries_sample',
      inputSchema: {
        type: 'object',
        required: ['event_id', 'metric_name', 'metric_value'],
        properties: {
          event_id: { type: 'string' },
          metric_name: { type: 'string' },
          metric_value: { type: 'number' },
        },
      },
      outputSchema: {
        type: 'object',
        properties: {
          recorded: { type: 'boolean' },
        },
      },
    },
  ],
  requires: [
    'content-browser/search-interface',
    'hallucinate_app/node/views/test_interface.html',
    'duckdb/time_series_schema',
  ],
  compatibility: {
    mobile_route: 'mobile://hallucinate_app/content-browser/search',
    storage_table: 'hallucinate_app_mobile_interop_events',
  },
};

const HALLUCINATE_APP_MOBILE_INTEROP_METHOD_SET = new Set(
  HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE.methods.map((method) => method.name)
);

export function buildHallucinateAppMobileInteropReceipt(handoff = {}) {
  const action = HALLUCINATE_APP_MOBILE_INTEROP_METHOD_SET.has(handoff.action)
    ? handoff.action
    : 'ingest_content_search';
  const descriptor = descriptorRef(
    HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE,
    localInterfaceKey(HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE)
  );
  return {
    contract: HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT,
    objective_id: 'VAIOS-G707',
    source: handoff.source || 'hallucinate_app',
    target: handoff.target || 'mobile',
    accepted: handoff.target === undefined || handoff.target === 'mobile',
    action,
    descriptor,
    query: typeof handoff.query === 'string' ? handoff.query : '',
    filter:
      handoff.filter && typeof handoff.filter === 'object' && !Array.isArray(handoff.filter)
        ? handoff.filter
        : {},
    mobile_route:
      handoff.mobile_payload?.route ||
      HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE.compatibility.mobile_route,
    received_at: handoff.timestamp || new Date().toISOString(),
  };
}

function normalizeDescriptorMetadata(metadata = {}) {
  if (!metadata || typeof metadata !== 'object' || Array.isArray(metadata)) {
    return null;
  }
  const normalized = {
    provider_name: metadata.provider_name,
    server_family: metadata.server_family || metadata.mcp_server_family,
    tool_name: metadata.tool_name || metadata.default_tool_name || metadata.operation_tool_name,
  };
  return Object.fromEntries(
    Object.entries(normalized).filter(([, value]) => typeof value === 'string' && value.length > 0)
  );
}

export function descriptorRef(descriptor, interfaceCid = null) {
  const ref = {
    name: descriptor.name,
    namespace: descriptor.namespace,
    version: descriptor.version,
    interface_cid: interfaceCid || descriptor.interface_cid || descriptor.schemaHash || null,
    spec_path: descriptor.specPath || descriptor.spec_path || null,
  };
  if (Array.isArray(descriptor.methods)) {
    ref.methods = descriptor.methods;
  }
  if (Array.isArray(descriptor.errors)) {
    ref.errors = descriptor.errors;
  }
  if (Array.isArray(descriptor.requires)) {
    ref.requires = descriptor.requires;
  }
  if (descriptor.compatibility && typeof descriptor.compatibility === 'object') {
    ref.compatibility = descriptor.compatibility;
  }
  const metadata = normalizeDescriptorMetadata(descriptor.metadata);
  if (metadata && Object.keys(metadata).length > 0) {
    ref.metadata = metadata;
  }
  return ref;
}

export function mcpServiceDescriptorRef(descriptor, interfaceCid = null, metadata = null) {
  const ref = descriptorRef(descriptor, interfaceCid);
  const normalizedMetadata = normalizeDescriptorMetadata(metadata || descriptor.metadata);
  if (normalizedMetadata && Object.keys(normalizedMetadata).length > 0) {
    ref.metadata = normalizedMetadata;
  }
  return ref;
}

export function localInterfaceKey(descriptor) {
  return `${descriptor.namespace}.${descriptor.name}@${descriptor.version}`;
}
