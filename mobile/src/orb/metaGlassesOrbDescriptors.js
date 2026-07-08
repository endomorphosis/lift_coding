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

export const HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE = {
  name: 'hallucinate_app_mobile_interop',
  namespace: 'handsfree.meta_glasses.mobile',
  version: '0.1.0',
  specPath: 'spec/hallucinate_app_mobile_interop_interface.json',
  metadata: {
    objective_id: 'VAIOS-G707',
    task_id: 'MGW-579',
    source_application: 'hallucinate_app',
    event_name: 'hallucinate-app:mobile-interop-handoff',
    contract: 'interface contract hallucinate_app mobile',
    persistence_table: 'hallucinate_app_mobile_interop_events',
  },
  methods: [
    {
      name: 'accept_handoff',
      inputSchema: {
        type: 'object',
        required: ['contract', 'source', 'action', 'query', 'filter', 'route', 'timestamp'],
        properties: {
          contract: { const: 'interface contract hallucinate_app mobile' },
          source: { const: 'hallucinate_app.content_browser.search_interface' },
          action: { enum: ['search', 'filter', 'clear'] },
          query: { type: 'string' },
          filter: { type: 'object' },
          route: {
            type: 'object',
            properties: {
              from: { const: 'hallucinate_app' },
              to: { const: 'mobile' },
              transport: { const: 'mobile_orb_bridge' },
              target_surface: { const: 'meta_glasses_display' },
            },
          },
          timestamp: { type: 'string', format: 'date-time' },
        },
      },
      outputSchema: {
        type: 'object',
        properties: {
          accepted: { type: 'boolean' },
          receipt_cid: { type: 'string' },
          display_widget_action: { type: 'object' },
        },
      },
    },
    {
      name: 'acknowledge_handoff',
      inputSchema: {
        type: 'object',
        required: ['receipt_cid', 'edge_session_id'],
        properties: {
          receipt_cid: { type: 'string' },
          edge_session_id: { type: 'string' },
        },
      },
      outputSchema: {
        type: 'object',
        properties: {
          acknowledged: { type: 'boolean' },
          stored_in: { const: 'hallucinate_app_mobile_interop_events' },
        },
      },
    },
  ],
  errors: [
    {
      name: 'invalid_hallucinate_app_mobile_handoff',
      code: 422,
    },
  ],
  requires: [
    'mobile_orb_bridge',
    'display_widget_bridge',
    'mcp++/profile-a-idl',
    'mcp++/receipts',
  ],
  compatibility: {
    hallucinate_app_event: 'hallucinate-app:mobile-interop-handoff',
    dashboard_descriptor: 'HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR',
    duckdb_table: 'hallucinate_app_mobile_interop_events',
  },
};

export const HALLUCINATE_APP_MOBILE_INTEROP_OPERATIONS = [
  'accept_handoff',
  'acknowledge_handoff',
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
