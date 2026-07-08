# SwissKnife / external/meta-wearables-dat-android Interop

HAO-735 repairs the VAIOS-G705 objective validation gap for the shared
`goal_packet/interoperability/swissknife/06921590135c` packet covering
VAIOS-G700, VAIOS-G701, VAIOS-G702, VAIOS-G703, VAIOS-G704, VAIOS-G705, and
VAIOS-G706.

The repaired `interface contract swissknife external/meta-wearables-dat-android`
path is:

- `external/meta-wearables-dat-android/.cursor/rules/display-access.mdc`
  documents the on-device Display capability: `Wearables.createSession(...)`,
  `session.addDisplay()`, `Display.sendContent { ... }` with a root `flexBox`
  or `video`, and waiting for `DisplayState.STARTED` before enabling
  user-triggered content.
- `external/meta-wearables-dat-android/.cursor/rules/session-lifecycle.mdc`
  documents the `DeviceSession`/`Display` state machine
  (`IDLE`, `STARTING`, `STARTED`, `PAUSED`, `STOPPING`, `STOPPED`) that
  SwissKnife's runtime handoff mirrors.
- `external/meta-wearables-dat-android/.cursor/rules/permissions-registration.mdc`
  documents the registration/permission flow: `Wearables.startRegistration(activity)`,
  `Wearables.checkPermissionStatus(...)`, `Wearables.RequestPermissionContract()`,
  and `PermissionStatus.Granted`.
- `external/meta-wearables-dat-android/samples/DisplayAccess/app/src/main/AndroidManifest.xml`
  is the real DisplayAccess sample manifest, declaring the
  `com.meta.wearable.mwdat.APPLICATION_ID`/`CLIENT_TOKEN` metadata keys and
  `android.permission.BLUETOOTH`/`BLUETOOTH_CONNECT`/`INTERNET` permissions
  that SwissKnife's mobile bridge can validate before delegating to a
  companion app.
- `external/meta-wearables-dat-android/samples/DisplayAccess/app/src/main/java/com/meta/wearable/dat/externalsampleapps/displayaccess/display/DisplayViewModel.kt`
  exercises concrete `IconName` (`CHECKMARK`, `TRIANGLE_LEFT_VERTICAL_LINE`,
  `TRIANGLE_RIGHT_VERTICAL_LINE`, `VIDEO_CAMERA`) and `ButtonStyle`
  (`PRIMARY`, `SECONDARY`) values that SwissKnife's widget compiler can emit
  when it targets a Meta Wearables Display session.
- `src/handsfree/swissknife_meta_wearables_dat_android_interop.py` statically
  discovers those five descriptors (without compiling any Kotlin/Android
  code), verifies the required Display API symbols, registration/permission
  API symbols, session states, manifest metadata keys/permissions, and
  `IconName`/`ButtonStyle` values are present, and builds a deterministic
  `SwissKnifeMetaWearablesDATAndroidHandoff` receipt.
- `swissknife/src/services/mcp/meta-wearables-dat-android-display-interop-descriptor.ts`
  exports `SWISSKNIFE_META_WEARABLES_DAT_ANDROID_INTEROP_INTERFACE` (a
  canonical MCP-IDL Profile A `MCPPPInterfaceDescriptor`) and
  `SWISSKNIFE_META_WEARABLES_DAT_ANDROID_INTEROP_DESCRIPTOR`, plus
  `registerSwissKnifeMetaWearablesDATAndroidDisplayInterop()` /
  `createMCPPlusPlusClientWithSwissKnifeMetaWearablesDATAndroidInterop()` to
  register the descriptor on a live `MCPPlusPlus` runtime registry alongside
  the pre-built IPFS interfaces, and
  `buildSwissKnifeMetaWearablesDATAndroidControlSurfaceContract()` /
  `buildSwissKnifeMetaWearablesDATAndroidInteractionEnvelope()` to build
  representative control-surface and interaction-envelope payloads.
- `swissknife/contracts/control_surface_contract.schema.json` and
  `swissknife/contracts/interaction_envelope.schema.json` validate those
  SwissKnife-to-`external/meta-wearables-dat-android` control surface and
  interaction envelope payloads (preserving the scanner-visible
  `agent_identity`, `allowed_surfaces`, and `arguments_hash` norm refs), and
  `swissknife/contracts/mcp_plus_plus_compatibility_receipt.schema.json` plus
  `swissknife/contracts/mediation_receipt.schema.json` remain the receipt
  schema refs advertised by the descriptor.

## Runtime handoff

1. `SWISSKNIFE_META_WEARABLES_DAT_ANDROID_INTEROP_INTERFACE` registers six
   `meta_wearables_dat_android.*` operations (`registration.start`,
   `registration.check_permission_status`, `session.create`,
   `session.start`, `display.attach`, `display.send_content`) as an MCP-IDL
   Profile A interface descriptor, compatible with the same `MCPPlusPlus`
   runtime registry as the pre-built IPFS interfaces.
2. A SwissKnife control-surface event (for example `send_content`) resolves
   to `meta_wearables_dat_android.display.send_content` via the
   `swissknife.meta_wearables_dat_android.display-service` control surface,
   mediated by the
   `policy:swissknife:meta-wearables-dat-android-display-interop` policy
   bundle.
3. `src/handsfree/swissknife_meta_wearables_dat_android_interop.py` builds a
   deterministic, content-addressed receipt (`sha256:` content CID) for the
   Display-session handoff via
   `build_swissknife_meta_wearables_dat_android_handoff()`, which statically
   re-derives the same `DeviceSession`/`Display` state set, `IconName`
   values, and `ButtonStyle` values advertised by the TypeScript descriptor.

## Validation evidence

Validation evidence lives in
`tests/integration/test_swissknife_external_meta_wearables_dat_android_interop.py`.
It verifies the Display-capability/session-lifecycle/permission-registration
descriptors and the real `DisplayAccess` sample manifest/view-model under
`external/meta-wearables-dat-android` exist and declare the expected
API symbols/states/keys/permissions/icons/styles, exercises the Python
`swissknife_meta_wearables_dat_android_interop` discovery and handoff
builder, statically inspects the SwissKnife TypeScript descriptor module for
the expected exports/goal-packet metadata, validates representative
SwissKnife control-surface and interaction-envelope payloads, and asserts
this objective validation repair is recorded in
`data/hallucinate_multimodal_control/discovery/2026-07-08-hao-735-validation-repair.md`
and the objective heap
(`implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md`).
