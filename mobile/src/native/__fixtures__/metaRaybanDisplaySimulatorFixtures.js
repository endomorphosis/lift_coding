const TASK_PROGRESS_SIMULATOR_MANIFEST = {
  schema: 'handsfree.meta-rayban-display/simulator-manifest',
  schema_version: '0.1.0',
  widget_id: 'org.handsfree.meta_glasses.task-progress-simulator@1.0.0',
  widget_cid: 'sha256:task-progress-simulator-fixture',
  descriptor_cid: 'sha256:display-widget-interface',
  orb_receipt_cid: 'sha256:simulator-receipt',
  correlation_id: 'simulator-task-progress',
  viewport: {
    width: 600,
    height: 600,
  },
  state: {
    title: 'Sync dataset',
    status: 'Running',
    summary: '42 percent complete. Indexing source records.',
    progress: 0.42,
  },
  focus_order: ['pause', 'dismiss'],
  fallback: {
    reason: 'dat_native_display_unavailable',
    renderPath: 'display-webapp',
    message: 'Native display unavailable. Showing simulator preview.',
  },
};

const TASK_PROGRESS_SIMULATOR_DISPLAY_ACTION = {
  contract: 'handsfree.meta-glasses/display-widget-action@0.1.0',
  type: 'mobile_render_display_widget',
  action: 'render',
  operation: 'render_widget',
  descriptor_cid: TASK_PROGRESS_SIMULATOR_MANIFEST.descriptor_cid,
  widget_id: TASK_PROGRESS_SIMULATOR_MANIFEST.widget_id,
  widget_cid: TASK_PROGRESS_SIMULATOR_MANIFEST.widget_cid,
  orb_receipt_cid: TASK_PROGRESS_SIMULATOR_MANIFEST.orb_receipt_cid,
  policy_decision: {
    outcome: 'permit',
    reasons: ['simulator fixture'],
  },
  correlation_id: TASK_PROGRESS_SIMULATOR_MANIFEST.correlation_id,
  manifest: TASK_PROGRESS_SIMULATOR_MANIFEST,
  fallback: TASK_PROGRESS_SIMULATOR_MANIFEST.fallback,
};

module.exports = {
  TASK_PROGRESS_SIMULATOR_DISPLAY_ACTION,
  TASK_PROGRESS_SIMULATOR_MANIFEST,
};
