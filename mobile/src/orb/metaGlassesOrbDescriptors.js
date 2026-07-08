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

export const HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT = {
  contract_id: 'interface contract hallucinate_app mobile',
  name: 'hallucinate_app_mobile_orb_handoff',
  namespace: 'handsfree.hallucinate_app.mobile',
  version: '0.1.0',
  source_surface: 'hallucinate_app',
  target_surface: 'mobile',
  control_surface_contract_ref: 'control_surface_contract:hallucinate-app:remote-client',
  runtime_routes: [
    '/v1/mobile/orb/register_edge_capabilities',
    '/v1/mobile/orb/publish_glasses_event',
    '/v1/mobile/orb/bind_service',
    '/v1/mobile/orb/invoke_service',
    '/v1/mobile/orb/dispatch_glasses_response',
    '/v1/mobile/orb/diagnostics',
  ],
  descriptor_paths: [
    'hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js',
    'hallucinate_app/hallucinate_app/node/views/test_interface.html',
    'mobile/src/orb/metaGlassesOrbDescriptors.js',
  ],
  artifact_refs: [
    'interaction_envelope',
    'policy_decision',
    'mediation_receipt',
    'mobile_orb_bridge',
  ],
};

export const HALLUCINATE_APP_MOBILE_HANDOFF_INTERFACE = {
  name: HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT.name,
  namespace: HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT.namespace,
  version: HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT.version,
  metadata: {
    contract_id: HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT.contract_id,
    source_surface: HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT.source_surface,
    target_surface: HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT.target_surface,
    control_surface_contract_ref:
      HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT.control_surface_contract_ref,
  },
  methods: [
    {
      name: 'register_edge_capabilities',
      inputSchema: { type: 'object', required: ['edge_id', 'platform'] },
      outputSchema: { type: 'object', required: ['edge_session_id', 'mediation_receipt'] },
    },
    {
      name: 'invoke_service',
      inputSchema: { type: 'object', required: ['binding_handle', 'operation'] },
      outputSchema: { type: 'object', required: ['ok', 'receipt_cid', 'service_result'] },
    },
    {
      name: 'dispatch_glasses_response',
      inputSchema: { type: 'object', required: ['edge_session_id', 'result'] },
      outputSchema: { type: 'object', required: ['receipt_cid', 'dispatched_actions'] },
    },
  ],
  requires: [
    'control_surface_contract',
    'interaction_envelope',
    'policy_decision',
    'mediation_receipt',
  ],
  compatibility: {
    mobile_orb_bridge: MOBILE_ORB_BRIDGE_INTERFACE.name,
    display_widget_bridge: DISPLAY_WIDGET_BRIDGE_INTERFACE.name,
  },
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

export function hallucinateAppMobileInteropDescriptorRef(interfaceCid = null) {
  return mcpServiceDescriptorRef(
    HALLUCINATE_APP_MOBILE_HANDOFF_INTERFACE,
    interfaceCid,
    HALLUCINATE_APP_MOBILE_HANDOFF_INTERFACE.metadata
  );
}
