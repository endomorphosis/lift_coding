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

export const SWISSKNIFE_MOBILE_INTEROP_OPERATIONS = [
  'register_edge_capabilities',
  'render_widget',
  'update_widget',
  'clear_widget',
  'focus_next',
  'activate',
  'dispatch_glasses_response',
];

export const SWISSKNIFE_MOBILE_INTEROP_INTERFACE = {
  name: 'swissknife_mobile_interop',
  namespace: 'handsfree.meta_glasses.interop',
  version: '0.1.0',
  specPath: 'docs/integration/swissknife-mobile.md',
  contractRefs: {
    control_surface_contract:
      'https://hallucinate.app/contracts/control_surface_contract.schema.json',
    interaction_envelope:
      'https://hallucinate.app/contracts/interaction_envelope.schema.json',
    mcp_plus_plus_compatibility_receipt:
      'https://hallucinate.app/contracts/mcp_plus_plus_compatibility_receipt.schema.json',
    mediation_receipt:
      'https://hallucinate.app/contracts/mediation_receipt.schema.json',
  },
  surfaces: ['swissknife', 'mobile', 'meta_glasses_display'],
  mobileContracts: ['handsfree.meta-glasses/display-widget-action@0.1.0'],
  handoff: {
    producer: 'swissknife',
    edge_runtime: 'mobile',
    control_surface_contract_ref: 'control_surface_contract',
    interaction_envelope_schema_ref: 'interaction_envelope',
    receipt_schema_ref: 'mediation_receipt',
    transport_preferences: ['local', 'http', 'websocket', 'mcp-server'],
  },
  methods: SWISSKNIFE_MOBILE_INTEROP_OPERATIONS.map((name) => ({
    name,
    control_surface_contract_ref: 'control_surface_contract',
    interaction_envelope_schema_ref: 'interaction_envelope',
    receipt_schema_ref: 'mediation_receipt',
  })),
  requires: [
    'mcp++/profile-a-idl',
    'mcp++/receipts',
    'control_surface_contract',
    'interaction_envelope',
  ],
  compatibility: {
    swissknife: {
      contracts: [
        'control_surface_contract',
        'interaction_envelope',
        'mcp_plus_plus_compatibility_receipt',
        'mediation_receipt',
      ],
    },
    mobile: {
      contracts: ['display_widget_action'],
      descriptors: ['mobile_orb_bridge', 'display_widget_bridge'],
    },
  },
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
  if (descriptor.contractRefs && typeof descriptor.contractRefs === 'object') {
    ref.contract_refs = descriptor.contractRefs;
  }
  if (Array.isArray(descriptor.surfaces)) {
    ref.surfaces = descriptor.surfaces;
  }
  if (Array.isArray(descriptor.mobileContracts)) {
    ref.mobile_contracts = descriptor.mobileContracts;
  }
  if (descriptor.handoff && typeof descriptor.handoff === 'object') {
    ref.handoff = descriptor.handoff;
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
