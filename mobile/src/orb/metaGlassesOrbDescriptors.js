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

export const SWISSKNIFE_MOBILE_INTEROP_INTERFACE = {
  name: 'swissknife_mobile_interop',
  namespace: 'handsfree.interop.swissknife_mobile',
  version: '0.1.0',
  metadata: {
    interface_contract: 'interface contract swissknife mobile',
    goal_packet: 'goal_packet/interoperability/swissknife/06921590135c',
    source_surface: 'swissknife',
    target_surface: 'mobile',
  },
  objective_goals: [
    'VAIOS-G700',
    'VAIOS-G701',
    'VAIOS-G702',
    'VAIOS-G703',
    'VAIOS-G704',
    'VAIOS-G705',
    'VAIOS-G706',
  ],
  methods: [
    ...MOBILE_ORB_BRIDGE_OPERATIONS.map((name) => ({
      name,
      surface: 'mobile_orb_bridge',
      contract_ref: 'swissknife/contracts/control_surface_contract.schema.json',
    })),
    ...DISPLAY_WIDGET_BRIDGE_OPERATIONS.map((name) => ({
      name,
      surface: 'display_widget_bridge',
      contract_ref: 'swissknife/contracts/interaction_envelope.schema.json',
    })),
  ],
  errors: [
    {
      name: 'policy_mediation_required',
      code: 409,
    },
    {
      name: 'unsupported_mobile_surface',
      code: 422,
    },
  ],
  requires: [
    'mcp++/profile-a-idl',
    'mcp++/profile-b-cid-artifacts',
    'mcp++/profile-d-policy',
    'mobile/meta-wearables-dat',
  ],
  compatibility: {
    swissknife_control_surface_contract:
      'swissknife/contracts/control_surface_contract.schema.json',
    swissknife_interaction_envelope:
      'swissknife/contracts/interaction_envelope.schema.json',
    display_widget_dat_contract:
      'mobile/src/utils/metaWearablesDatDisplayWidgetContract.js',
  },
};

export const SWISSKNIFE_MOBILE_INTEROP_DESCRIPTOR = {
  descriptor_id: 'swissknife-mobile-interop@0.1.0',
  interface: SWISSKNIFE_MOBILE_INTEROP_INTERFACE,
  schema_refs: {
    control_surface_contract: 'swissknife/contracts/control_surface_contract.schema.json',
    interaction_envelope: 'swissknife/contracts/interaction_envelope.schema.json',
    mediation_receipt: 'swissknife/contracts/mediation_receipt.schema.json',
    mcp_plus_plus_compatibility_receipt:
      'swissknife/contracts/mcp_plus_plus_compatibility_receipt.schema.json',
  },
  runtime_handoff: {
    source_surface: 'swissknife',
    target_surface: 'mobile',
    allowed_surfaces: ['agent', 'remote_client', 'mobile', 'meta_glasses'],
    dat_methods: DISPLAY_WIDGET_BRIDGE_OPERATIONS,
    mobile_orb_methods: MOBILE_ORB_BRIDGE_OPERATIONS,
    control_surface_policy_id: 'policy:swissknife:mobile-interop',
  },
  validation: {
    task_id: 'MGW-569',
    repair_task_id: 'MGW-583',
    hao_task_id: 'HAO-730',
    hao_attempt: 4,
    objective_gap_ref:
      'data/meta_glasses_display_widgets/discovery/2026-07-08-mgw-569-objective-gap-d33307f93408.md',
    hao_objective_gap_ref:
      'data/hallucinate_multimodal_control/discovery/2026-07-08-hao-730-objective-gap-d33307f93408.md',
    hao_validation_confirmation_ref:
      'data/hallucinate_multimodal_control/discovery/2026-07-08-hao-730-attempt-4-validation-confirmation.md',
    retry_budget_ref:
      'data/meta_glasses_display_widgets/discovery/2026-07-08-mgw-583-mgw-569-retry-budget.md',
    evidence: 'objective validation repair',
  },
};

export const IPFS_ACCELERATE_BENCHMARK_WIDGET_OPERATIONS = [
  'render_performance_benchmark_widget',
  'update_performance_benchmark_widget',
  'clear_performance_benchmark_widget',
  'refresh_performance_benchmark_metrics',
];

export const IPFS_ACCELERATE_MOBILE_INTEROP_INTERFACE = {
  name: 'ipfs_accelerate_mobile_interop',
  namespace: 'handsfree.interop.ipfs_accelerate_mobile',
  version: '0.1.0',
  metadata: {
    interface_contract: 'interface contract mobile external/ipfs_accelerate',
    goal_id: 'VAIOS-G719',
    source_surface: 'external/ipfs_accelerate',
    target_surface: 'mobile',
  },
  objective_goals: ['VAIOS-G719'],
  methods: [
    ...MOBILE_ORB_BRIDGE_OPERATIONS.map((name) => ({
      name,
      surface: 'mobile_orb_bridge',
      contract_ref: 'external/ipfs_accelerate/data/duckdb/db_schema/time_series_schema.sql',
    })),
    ...IPFS_ACCELERATE_BENCHMARK_WIDGET_OPERATIONS.map((name) => ({
      name,
      surface: 'display_widget_bridge',
      contract_ref: 'mobile/src/utils/ipfsAccelerateBenchmarkWidgetContract.js',
    })),
  ],
  errors: [
    {
      name: 'benchmark_schema_unavailable',
      code: 409,
    },
    {
      name: 'unsupported_mobile_surface',
      code: 422,
    },
  ],
  requires: [
    'mcp++/profile-a-idl',
    'mcp++/profile-b-cid-artifacts',
    'mobile/meta-wearables-dat',
  ],
  compatibility: {
    ipfs_accelerate_time_series_schema:
      'external/ipfs_accelerate/data/duckdb/db_schema/time_series_schema.sql',
    ipfs_accelerate_benchmark_schema_script:
      'external/ipfs_accelerate/data/duckdb/scripts/create_benchmark_schema.py',
    ipfs_accelerate_check_database_schema:
      'external/ipfs_accelerate/data/duckdb/utils/check_database_schema.py',
    ipfs_accelerate_check_db_schema:
      'external/ipfs_accelerate/data/duckdb/utils/check_db_schema.py',
    mobile_benchmark_widget_contract:
      'mobile/src/utils/ipfsAccelerateBenchmarkWidgetContract.js',
  },
};

export const IPFS_ACCELERATE_MOBILE_INTEROP_DESCRIPTOR = {
  descriptor_id: 'ipfs-accelerate-mobile-interop@0.1.0',
  interface: IPFS_ACCELERATE_MOBILE_INTEROP_INTERFACE,
  schema_refs: {
    time_series_schema: 'external/ipfs_accelerate/data/duckdb/db_schema/time_series_schema.sql',
    benchmark_schema_script:
      'external/ipfs_accelerate/data/duckdb/scripts/create_benchmark_schema.py',
    check_database_schema:
      'external/ipfs_accelerate/data/duckdb/utils/check_database_schema.py',
    check_db_schema: 'external/ipfs_accelerate/data/duckdb/utils/check_db_schema.py',
    benchmark_widget_contract: 'mobile/src/utils/ipfsAccelerateBenchmarkWidgetContract.js',
  },
  runtime_handoff: {
    source_surface: 'external/ipfs_accelerate',
    target_surface: 'mobile',
    allowed_surfaces: ['agent', 'mcp_server', 'mobile', 'meta_glasses'],
    dat_methods: IPFS_ACCELERATE_BENCHMARK_WIDGET_OPERATIONS,
    mobile_orb_methods: MOBILE_ORB_BRIDGE_OPERATIONS,
    time_series_tables: [
      'performance_baselines',
      'performance_regressions',
      'performance_trends',
      'regression_notifications',
    ],
  },
  validation: {
    task_id: 'VAI-672',
    goal_id: 'VAIOS-G719',
    objective_gap_ref:
      'data/virtual_ai_os/discovery/2026-07-08-vai-672-objective-gap-c1edafa875e6.md',
    validation_repair_ref:
      'data/virtual_ai_os/discovery/2026-07-08-vai-672-objective-validation-repair.md',
    evidence: 'objective validation repair',
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
