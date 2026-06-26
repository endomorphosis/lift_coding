export const META_WEARABLES_DAT_SOURCE_MATRIX = {
  id: 'mgw-415-public-dat-webapps-source-matrix',
  profile: 'handsfree.meta-glasses/io-source-matrix',
  profileVersion: '0.1.0',
  hardwareFree: true,
  credentialsRequired: false,
  datPackageAccessRequired: false,
  pairedGlassesRequired: false,
  physicalHardwareRequired: false,
  sourceFamilies: [
    'android-dat-displayaccess-v0.7',
    'ios-dat-displayaccess-v0.7',
    'dat-cameraaccess-v0.7',
    'meta-display-webapps-inputs',
    'bluetooth-audio-route-readiness',
  ],
  displayAccessLifecycleV07: [
    'sdk_package_checked',
    'release_channel_checked',
    'credentials_checked',
    'developer_mode_checked',
    'display_target_selected',
    'device_session_starting',
    'device_session_started',
    'display_attaching',
    'display_attached',
    'display_ready',
    'display_content_sent',
    'display_video_player_ready',
    'display_content_replaced',
    'display_session_stopped',
  ],
  cameraAccessLifecycleV07: [
    'camera_permission_required',
    'camera_permission_granted',
    'camera_session_started',
    'camera_stream_ready',
    'camera_stream_started',
    'camera_photo_requested',
    'camera_photo_captured',
    'camera_stream_stopped',
    'camera_session_stopped',
  ],
  audioRouteStates: [
    { capability: 'microphone.input', route: 'bluetooth-hfp-input', readiness: 'ready' },
    { capability: 'speaker.output', route: 'bluetooth-a2dp-output', readiness: 'ready' },
    { capability: 'headphone.output', route: 'bluetooth-a2dp-output', readiness: 'ready' },
  ],
  webAppInputs: [
    { key: 'ArrowLeft', intent: 'navigate_previous', capability: 'captouch.input' },
    { key: 'ArrowRight', intent: 'navigate_next', capability: 'captouch.input' },
    { key: 'Enter', intent: 'activate_selected', capability: 'captouch.input' },
    { gesture: 'pinch', intent: 'activate_selected', capability: 'neural_band.input' },
    { touch: 'swipe_forward', intent: 'navigate_next', capability: 'captouch.input' },
  ],
  sensorContexts: [
    {
      id: 'motion-orientation',
      capability: 'motion.orientation',
      sample: { yaw: 12.5, pitch: -2.25, roll: 0.75, quaternion: [0.99, 0.02, -0.04, 0.1] },
    },
    {
      id: 'phone-gps',
      capability: 'phone_gps.context',
      sample: { source: 'phone-os-mock', latitude: 37.789, longitude: -122.401, accuracyM: 8 },
    },
  ],
  failureModes: [
    { id: 'permission_denial', capability: 'camera.photo_capture', readiness: 'permission_denied' },
    { id: 'unsupported_display', capability: 'display.output', readiness: 'unsupported' },
    { id: 'release_channel_missing', capability: 'display.output', readiness: 'package_or_release_channel_unavailable' },
    { id: 'firmware_update_required', capability: 'display.output', readiness: 'firmware_update_required' },
    { id: 'dat_app_update_required', capability: 'display.output', readiness: 'dat_app_update_required' },
    { id: 'route_loss', capability: 'microphone.input', readiness: 'route_lost' },
    { id: 'backpressure', capability: 'camera.video_capture', readiness: 'degraded' },
    { id: 'local_storage_limit', capability: 'display.output', readiness: 'degraded' },
    { id: 'recovery', capability: 'microphone.input', readiness: 'ready' },
  ],
};

export function createMetaWearablesDatSourceMatrixMock() {
  return {
    ...META_WEARABLES_DAT_SOURCE_MATRIX,
    scenarios: {
      displayReady: META_WEARABLES_DAT_SOURCE_MATRIX.displayAccessLifecycleV07,
      cameraReady: META_WEARABLES_DAT_SOURCE_MATRIX.cameraAccessLifecycleV07,
      webAppInputs: META_WEARABLES_DAT_SOURCE_MATRIX.webAppInputs,
      audioRoutes: META_WEARABLES_DAT_SOURCE_MATRIX.audioRouteStates,
    },
  };
}

export default META_WEARABLES_DAT_SOURCE_MATRIX;
