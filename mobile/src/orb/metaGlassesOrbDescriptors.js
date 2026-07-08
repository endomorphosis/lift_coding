export const MOBILE_ORB_BRIDGE_INTERFACE = {
  name: 'mobile_orb_bridge',
  namespace: 'handsfree.meta_glasses.mobile',
  version: '0.1.0',
  specPath: 'spec/meta_glasses_mobile_orb_bridge_interface.json',
  interop_contract: 'interface contract swissknife mobile',
  schema_refs: [
    'control_surface_contract',
    'interaction_envelope',
    'mcp_plus_plus_compatibility_receipt',
    'mediation_receipt',
  ],
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
  interop_contract: 'interface contract swissknife mobile',
  action_contract: 'handsfree.meta-glasses/display-widget-action@0.1.0',
  schema_refs: [
    'control_surface_contract',
    'interaction_envelope',
    'mcp_plus_plus_compatibility_receipt',
    'mediation_receipt',
  ],
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

export const SWISSKNIFE_MOBILE_INTEROP_INTERFACE = {
  name: 'swissknife_mobile_display_widget_interop',
  namespace: 'handsfree.interop.swissknife_mobile',
  version: '0.1.0',
  interop_contract: 'interface contract swissknife mobile',
  producer: 'swissknife',
  consumer: 'mobile',
  mobile_surface: 'meta-wearables-dat',
  swissknife_surface: 'meta-glasses-display-orb',
  descriptors: [
    MOBILE_ORB_BRIDGE_INTERFACE,
    DISPLAY_WIDGET_BRIDGE_INTERFACE,
  ],
  operations: DISPLAY_WIDGET_BRIDGE_OPERATIONS,
  required_payload_fields: [
    'contract',
    'interop_contract',
    'type',
    'operation',
    'dat_method',
    'widget_id',
    'interface_cid',
    'orb_receipt_cid',
    'control_surface_contract_ref',
    'interaction_envelope',
    'mediation_receipt',
  ],
  schema_refs: [
    'control_surface_contract',
    'interaction_envelope',
    'mcp_plus_plus_compatibility_receipt',
    'mediation_receipt',
  ],
};

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
  if (descriptor.interop_contract) {
    ref.interop_contract = descriptor.interop_contract;
  }
  if (descriptor.action_contract) {
    ref.action_contract = descriptor.action_contract;
  }
  if (Array.isArray(descriptor.schema_refs)) {
    ref.schema_refs = descriptor.schema_refs;
  }
  if (Array.isArray(descriptor.operations)) {
    ref.operations = descriptor.operations;
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
