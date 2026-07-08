# SwissKnife / external/meta-wearables-dat-ios Interop

HAO-736 repairs the VAIOS-G706 objective validation gap for the shared
`goal_packet/interoperability/swissknife/06921590135c` packet covering
VAIOS-G700, VAIOS-G701, VAIOS-G702, VAIOS-G703, VAIOS-G704, VAIOS-G705, and
VAIOS-G706. VAI-667 first recorded this proof in the virtual_ai_os lane; this
document is the hallucinate_multimodal_control lane objective validation repair
for `data/hallucinate_multimodal_control/discovery/2026-07-08-hao-736-objective-gap-d6bdae3a60cc.md`.

The repaired `interface contract swissknife external/meta-wearables-dat-ios`
path is:

- `external/meta-wearables-dat-ios/.cursor/rules/display-access.mdc`
  documents the iOS Display capability: `Wearables.configure()`,
  `AutoDeviceSelector(... filter: { $0.supportsDisplay() })`,
  `Wearables.shared.createSession(deviceSelector:)`, waiting for
  `DeviceSessionState.started`, `DeviceSession.addDisplay()`, `Display.start()`,
  waiting for `DisplayState.started`, and `display.send(...)` with a root
  `FlexBox` or `VideoPlayer`.
- `external/meta-wearables-dat-ios/.cursor/rules/session-lifecycle.mdc`
  documents the `DeviceSession` state set (`idle`, `starting`, `started`,
  `paused`, `stopping`, `stopped`) that SwissKnife mirrors before routing
  display work.
- `external/meta-wearables-dat-ios/.cursor/rules/permissions-registration.mdc`
  documents the registration and URL callback flow:
  `Wearables.shared.startRegistration()`, `Wearables.shared.handleUrl(_:)`,
  `registrationStateStream()`, `checkPermissionStatus(...)`, and
  `requestPermission(...)`.
- `external/meta-wearables-dat-ios/samples/DisplayAccess/DisplayAccess/Info.plist`
  is the real DisplayAccess sample plist. It declares `CFBundleURLTypes`, the
  `MWDAT` dictionary (`AppLinkURLScheme`, `MetaAppID`, `ClientToken`,
  `TeamID`), `UIBackgroundModes`, `NSBluetoothAlwaysUsageDescription`,
  `NSLocalNetworkUsageDescription`, and `NSBonjourServices`.
- `external/meta-wearables-dat-ios/samples/DisplayAccess/DisplayAccess/ViewModels/DisplayViewModel.swift`
  implements the runtime session handoff: create session, observe
  `stateStream()`/`errorStream()`, call `addDisplay()`, listen for
  `DisplayState.started`, execute pending display sends, and stop Display
  before stopping the parent session.
- `external/meta-wearables-dat-ios/samples/DisplayAccess/DisplayAccess/Samples/CarMaintenanceDisplay.swift`
  exercises concrete Display DSL values SwissKnife can target:
  `FlexBox`, `Text`, `Button`, `Image`, `VideoPlayer`, icon names
  `checkmark`, `triangleLeftVerticalLine`, `triangleRightVerticalLine`,
  `videoCamera`, and `ButtonStyle` values `primary` and `secondary`.
- `src/handsfree/swissknife_meta_wearables_dat_ios_interop.py` statically
  discovers those six descriptors without compiling Swift or importing DAT,
  verifies the required session states, plist keys, background modes, display
  view types, icon names, button styles, and API symbols, and builds a
  deterministic `SwissKnifeMetaWearablesDATIOSHandoff` receipt.
- `swissknife/src/services/mcp/meta-wearables-dat-ios-display-interop-descriptor.ts`
  exports `SWISSKNIFE_META_WEARABLES_DAT_IOS_INTEROP_INTERFACE` (a canonical
  MCP-IDL Profile A `MCPPPInterfaceDescriptor`) and
  `SWISSKNIFE_META_WEARABLES_DAT_IOS_INTEROP_DESCRIPTOR`, plus
  `registerSwissKnifeMetaWearablesDATIOSDisplayInterop()` /
  `createMCPPlusPlusClientWithSwissKnifeMetaWearablesDATIOSInterop()` to
  register the descriptor on a live `MCPPlusPlus` runtime registry, and
  `buildSwissKnifeMetaWearablesDATIOSControlSurfaceContract()` /
  `buildSwissKnifeMetaWearablesDATIOSInteractionEnvelope()` to build
  representative control-surface and interaction-envelope payloads.
- `swissknife/contracts/control_surface_contract.schema.json`,
  `swissknife/contracts/interaction_envelope.schema.json`,
  `swissknife/contracts/mcp_plus_plus_compatibility_receipt.schema.json`, and
  `swissknife/contracts/mediation_receipt.schema.json` remain the shared
  SwissKnife schemas advertised by the descriptor. The iOS compatibility
  receipt uses `task_id: HAO-736`, `daemon_id: meta-wearables-dat-ios`, and
  `server_package: meta_wearables_dat_ios`. The payloads preserve the
  scanner-visible `agent_identity`, `allowed_surfaces`, and `arguments_hash`
  norm refs.

## Runtime Handoff

1. `SWISSKNIFE_META_WEARABLES_DAT_IOS_INTEROP_INTERFACE` registers eight
   `meta_wearables_dat_ios.*` operations (`registration.start`,
   `registration.handle_url`, `registration.check_permission_status`,
   `session.create`, `session.start`, `display.attach`, `display.send`, and
   `display.stop`) as an MCP-IDL Profile A interface descriptor.
2. A SwissKnife control-surface event such as `send_display_view` resolves to
   `meta_wearables_dat_ios.display.send` via the
   `swissknife.meta_wearables_dat_ios.display-service` control surface,
   mediated by the
   `policy:swissknife:meta-wearables-dat-ios-display-interop` policy bundle.
3. `build_swissknife_meta_wearables_dat_ios_handoff()` builds a deterministic,
   content-addressed receipt (`sha256:` content CID) for the Display-session
   handoff by re-deriving the iOS DAT `DeviceSession` state set, Info.plist
   keys, background modes, Display DSL view types, icon names, and button
   styles advertised by the TypeScript descriptor.

## Validation Evidence

Validation evidence lives in
`tests/integration/test_swissknife_external_meta_wearables_dat_ios_interop.py`.
It verifies the Display/session/permission descriptors and real DisplayAccess
sample files under `external/meta-wearables-dat-ios`, exercises the Python
discovery and handoff builder, statically inspects the SwissKnife TypeScript
descriptor module for the expected exports and goal-packet metadata, validates
representative SwissKnife control-surface, interaction-envelope, and MCP++
compatibility receipt payloads,
and asserts this objective validation repair is recorded in
`data/hallucinate_multimodal_control/discovery/2026-07-08-hao-736-validation-repair.md`
and `implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md`.
