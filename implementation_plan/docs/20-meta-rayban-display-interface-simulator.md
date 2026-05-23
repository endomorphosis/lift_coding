# Meta Ray-Ban Display Interface Simulator Plan

## Goal

Build a hardware-free simulator for the Meta Ray-Ban Display interface so we can validate layout, focus navigation, action payloads, sensor/location behavior, and mobile handoff behavior before moving the experience to iPhone.

The simulator should not pretend to be an official glasses emulator. Public Meta materials currently expose two useful pre-hardware paths:

- Web Apps: browser-based preview with a fixed 600x600 viewport, arrow-key/Enter input, and Chrome DevTools sensors.
- DAT native mobile: Mock Device Kit for simulated devices, app registration, permissions, camera/video/photo flows, device state, and some captouch session gestures.

The plan below uses the Web Apps path as the primary surface for visual interface simulation, while preserving a bridge-compatible path for the existing mobile DAT implementation.

Refresh note, 2026-05-23: the Wearables Developer Center pages require login in this environment, so public verification used Meta's official GitHub repositories and maintainer discussion where available. Those sources still confirm the same implementation direction: Web Apps are browser-testable, the Web App AI Toolkit documents arrow-key D-pad simulation plus Chrome Sensors, the DAT Android/iOS repos ship MockDeviceKit guidance, and a maintainer announcement for DAT 0.6 specifically calls out video-streaming simulation using the phone camera plus permission/configuration simulation with the Meta AI app.

## Source Findings

### Web Apps path

Official Web Apps docs describe Meta Ray-Ban Display Web Apps as standard HTML/CSS/JavaScript rendered on the glasses display. They currently expose:

- MRBD display.
- Input from Meta Neural Band and glasses captouch controls.
- Device motion/orientation via `DeviceMotionEvent` and `DeviceOrientationEvent`.
- Location via `navigator.geolocation`, sourced from the paired phone.
- `localStorage` and `sessionStorage`.

Relevant constraints from the public docs and Meta Web App AI Toolkit:

- The viewport is fixed at 600x600 pixels.
- The display is additive: black is effectively transparent, bright UI is visible, and dark backgrounds are preferred.
- Navigation is D-pad style only. Neural Band and captouch input map to `ArrowUp`, `ArrowDown`, `ArrowLeft`, `ArrowRight`, and `Enter`.
- Interactive elements must be focusable.
- Chrome browser testing is valid for first-pass preview. Arrow keys and Enter simulate glasses input.
- Chrome DevTools Sensors can simulate location and orientation.
- The deployed app must be hosted at a publicly reachable HTTPS URL before loading on glasses.
- Unsupported Web App capabilities include camera, microphone, text input, offline support, notifications, back navigation, and continuous cursor support.

Sources:

- https://wearables.developer.meta.com/docs/develop/webapps/
- https://wearables.developer.meta.com/docs/develop/webapps/setup/
- https://wearables.developer.meta.com/docs/develop/webapps/build/
- https://wearables.developer.meta.com/docs/develop/webapps/test/
- https://github.com/facebookincubator/meta-wearables-webapp
- https://github.com/facebook/meta-wearables-dat-ios
- https://github.com/facebook/meta-wearables-dat-android
- https://github.com/facebook/meta-wearables-dat-ios/discussions/141

### DAT native display path

The DAT display docs describe a session model where the phone app creates a device session, attaches a display capability, and sends complete UI content to the glasses. The supported native display components are `FlexBox`, `Text`, `Image`, `Button`, `Icon`, and MP4 video playback.

Important constraints:

- Display content is sent as whole views. There is no partial update mechanism.
- The glasses display resolution is 600x600.
- One display capability is active per device session.
- The display dims after 20 seconds of inactivity and sleeps at 25 seconds, without ending the DAT session.
- Video must be HTTPS MP4, one video at a time, under 400px per side and 70,000 total pixels.
- DAT display needs Meta AI app v272+ and glasses firmware v125+.

Sources:

- https://wearables.developer.meta.com/docs/develop/dat/display-overview/
- https://wearables.developer.meta.com/docs/develop/dat/display-ios/
- https://wearables.developer.meta.com/docs/develop/dat/display-android/
- https://github.com/facebook/meta-wearables-dat-ios
- https://github.com/facebook/meta-wearables-dat-android

### Simulation tools found

Meta-supported options:

- Browser simulation for Web Apps:
  - 600x600 viewport.
  - Arrow keys and Enter for Neural Band/captouch-equivalent input.
  - Chrome DevTools Sensors for geolocation and orientation.
- Meta Web App AI Toolkit:
  - Scaffolding and guidance for Web Apps.
  - Example browser testing flow.
  - Optional QR/deeplink publish workflow.
- DAT Mock Device Kit:
  - Simulates app connection/registration, permission requests, paired mock devices, power/don/unfold state, camera feed, photo capture, and captouch gestures in the CameraAccess path.
  - Supports automated testing through iOS XCTest/XCUITest and Android instrumentation patterns.
  - Public DAT 0.6 maintainer notes also call out phone-camera video streaming simulation and permission/configuration simulation with the Meta AI app.

Gap:

- I did not find a public official desktop simulator that renders the native DAT Display component tree exactly as the glasses would.
- I did not find public docs saying Mock Device Kit renders DAT Display UI output. Treat MDK as device/session/media simulation, not as the visual display simulator.

## Existing Repo Fit

The repo already has useful pieces:

- `dev/simulator.html`: existing generic dev simulator.
- `mobile/src/native/wearablesBridge.js`: bridge wrapper for native DAT actions and structured fallback results.
- `mobile/modules/expo-meta-wearables-dat`: Expo native module with display action scaffolding.
- `mobile/src/native/__fixtures__/metaWearablesDisplayStates.js`: hardware-free display state fixtures.
- `src/handsfree/display_webapp_compat.py`: Web App readiness evaluator.
- `scripts/lint_display_webapp_readiness.py`: CLI readiness linter.
- `config/display_webapp_readiness.example.json`: 600x600/D-pad/contrast readiness example.
- `docs/meta-wearables-dat-display-physical-validation-checklist.md`: later hardware validation gate.
- `external/meta-wearables-dat-android/samples/DisplayAccess`: checked-in Android DisplayAccess sample reference.

The simulator should extend these instead of creating an unrelated surface.

## Recommended Architecture

### 1. Canonical Display Manifest

Keep the current display widget manifest as the single source of truth. A manifest should describe:

- `viewport`: exactly `{ "width": 600, "height": 600 }`.
- `regions`: text, status, progress, list, image, button/action, and video intent regions.
- `focus_order`: deterministic list of action IDs.
- `state`: runtime values.
- `fallback`: mobile-card/audio-summary/display-webapp fallback metadata.
- `media`: HTTPS-only image/video metadata plus fallback text.

Output targets:

- Browser simulator.
- Web App deployable bundle.
- Mobile card fallback.
- DAT native renderer adapter.

### 2. Browser Simulator Surface

Create a new MRBD-specific simulator, preferably:

- `dev/meta-rayban-display-simulator/`
- `index.html`
- `styles.css`
- `simulator.js`
- `fixtures/*.json`

The browser simulator should render a 600x600 canvas/frame, not a full desktop dashboard. It should include a separate control panel outside the frame for fixtures, device state, sensor values, and logs.

Inside the 600x600 frame:

- Dark/transparent-first theme.
- High contrast text and focus ring.
- No scrolling by default.
- Stable 88px minimum focus target where actions are represented.
- Keyboard input:
  - `ArrowUp`, `ArrowDown`, `ArrowLeft`, `ArrowRight`: move focus.
  - `Enter`: activate focused action.
  - `Escape`: simulate universal/back/session-end behavior where supported.

Outside the frame:

- Fixture picker.
- Display state picker: unavailable, disabled, unsupported, firmware update required, DAT app update required, lifecycle error, ready.
- Sensor controls: heading, tilt, roll, acceleration, location.
- Event log with correlation ID, request ID, action ID, and fallback reason.
- Export button for readiness JSON and captured event trace.

### 3. Renderer Adapter Layer

Implement a pure JS renderer that accepts the same manifest shape the mobile bridge sees:

```text
manifest -> normalized view model -> browser DOM
manifest -> normalized view model -> Web App bundle
manifest -> normalized view model -> DAT native adapter
```

The browser renderer must validate before rendering:

- Viewport is 600x600.
- All focusable action IDs exist in `focus_order`.
- Regions fit inside the viewport.
- Video media is HTTPS MP4 and is rendered as a root video intent, not as nested content.
- Image media is HTTPS URL or has fallback text.
- Contrast and dark-theme metadata pass readiness checks.

### 4. Local Action Bridge Simulation

Connect the simulator to the existing action contract:

- `render_widget`
- `update_widget`
- `clear_widget`
- `focus_next`
- `activate`
- `reset_session`
- `play_video`
- `subscribe_updates`

Each simulated action should produce the same structured result fields used by `mobile/src/native/wearablesBridge.js`:

- `supported`
- `renderPath`
- `reason`
- `requiredAction`
- `displayConnectionState`
- `displayLastAction`
- `displayLastStatus`
- `displayLastError`
- `displayLifecycleStages`
- `widgetId`
- `widgetCid`
- `orbReceiptCid`
- `correlationId`
- `requestId`
- `fallback`

This makes simulator traces directly comparable to mobile diagnostics.

### 5. Web App Compatibility Mode

Add a "MRBD Web App mode" that renders the same interface as deployable HTML/CSS/JS:

- Fixed 600x600 body.
- `overflow: hidden`.
- D-pad focus manager.
- `.focusable` class on every interactive element.
- dark background and bright UI.
- no unsupported browser APIs.
- `navigator.geolocation` and IMU usage behind user-initiated permission buttons.
- PNG app icons and web manifest; no SVG-only icon dependency.

This should become the artifact we can host on Vercel/GitHub Pages/Netlify and later add through Meta AI App > App Connections > Web Apps.

### 6. iPhone Handoff Path

The simulator should export artifacts that the iPhone implementation can consume:

- `manifest.json`: canonical widget manifest.
- `readiness.json`: input for `scripts/lint_display_webapp_readiness.py`.
- `trace.json`: action/focus/sensor event trace.
- `webapp/`: static deployable 600x600 Web App.
- `mobile_fixture.json`: fixture for Jest tests and Expo diagnostics.

On the iPhone side:

- Keep the current Expo DAT bridge as the mobile-native boundary.
- Use the simulator trace to drive `wearablesBridge` tests.
- Use the mobile fixture to verify fallback reasons and display state messaging before physical hardware.
- For native DAT display, map the canonical manifest to `FlexBox`, `Text`, `Image`, `Button`, `Icon`, and root `VideoPlayer` content.

## Implementation Phases

### Phase 0 - Confirm Scope and Inputs

Deliverables:

- Decide first simulated experience: command status widget, inbox widget, task progress widget, or diagnostics widget.
- Pick one canonical fixture as the golden path.
- Define any data fields that must round-trip to backend/mobile.

Acceptance:

- One manifest fixture represents the first iPhone-bound interface.
- Every action has an ID, display label, focus order, and expected result payload.

### Phase 1 - Simulator Shell

Deliverables:

- Add `dev/meta-rayban-display-simulator/index.html`.
- Add `dev/meta-rayban-display-simulator/styles.css`.
- Add `dev/meta-rayban-display-simulator/simulator.js`.
- Add one golden fixture.
- Keep `dev/simulator.html` intact unless we intentionally link to the new simulator.

Acceptance:

- Opening the HTML locally shows a 600x600 MRBD frame.
- Arrow keys move focus.
- Enter activates actions.
- Event log records every focus and activation.
- Layout stays inside 600x600.

### Phase 2 - Manifest Renderer and Validation

Deliverables:

- Add a manifest normalizer.
- Add viewport, focus order, media, and region-bound validation.
- Render text, status, progress, image fallback, and actions.
- Add optional visual warnings outside the 600x600 frame.

Acceptance:

- Invalid manifests fail visibly and produce machine-readable errors.
- Valid manifests render deterministically.
- Golden fixture passes local validation.

### Phase 3 - Contract Simulation

Deliverables:

- Add a simulated display bridge module for browser use.
- Mirror the action result shape from `wearablesBridge.js`.
- Add display state fixtures matching `DAT_DISPLAY_STATES`.
- Add trace export.

Acceptance:

- Simulator can replay unavailable, unsupported, update-required, lifecycle-error, and ready states.
- Results match the mobile bridge field names.
- Trace export can be checked into tests as a fixture.

### Phase 4 - Web App Build Target

Deliverables:

- Add a static Web App export target.
- Generate `index.html`, `styles.css`, `app.js`, and `manifest.webmanifest`.
- Add PNG app icon requirement to readiness metadata.
- Add deploy instructions for one HTTPS host.

Acceptance:

- Web App runs in desktop Chrome.
- Chrome viewport set to 600x600 matches the simulator frame.
- Arrow keys and Enter fully operate the app.
- `scripts/lint_display_webapp_readiness.py` passes against exported readiness JSON.

### Phase 5 - Automated Checks

Deliverables:

- Add unit tests for manifest normalization and validation.
- Add Jest tests for focus movement and activation.
- Add a Playwright smoke test if a JS/browser test stack is already acceptable for this repo.
- Add Python readiness checks for exported fixtures if the source remains backend-owned.

Acceptance:

- Tests cover valid render, invalid viewport, missing focus target, out-of-bounds region, unsupported media, and fallback rendering.
- CI can run all hardware-free checks without DAT credentials.

### Phase 6 - Mobile Integration Prep

Deliverables:

- Add generated mobile fixture under `mobile/src/native/__fixtures__/`.
- Add or update `wearablesBridge` tests to replay the simulator trace.
- Document iPhone handoff steps:
  - Web App path for fastest glass display validation.
  - Native DAT path for app-mediated display integration.

Acceptance:

- iPhone work can start from a stable manifest and trace.
- Mobile tests can validate fallback and native-ready result fields without real glasses.
- The physical validation checklist remains the final gate, not the first discovery step.

## Technical Rules for the Simulator

- Use only standard browser APIs for the Web App target.
- Treat camera and microphone as unavailable for MRBD Web Apps.
- Treat location and IMU as permission-gated.
- Keep all UI within 600x600.
- Do not depend on mouse/touch interaction for core flows.
- Do not rely on scrolling.
- Keep action targets large and sparse.
- Use HTTPS URLs for media that will reach glasses.
- Prefer PNG app icons of at least 52x52.
- Keep all simulator logs structured JSON.

## Recommended Milestone Order

1. Build the browser-only simulator shell.
2. Render the canonical manifest and focus model.
3. Add state/fallback simulation.
4. Add trace export and tests.
5. Add Web App export and readiness linter integration.
6. Host the Web App over HTTPS.
7. Load it through the Meta AI app on glasses.
8. Move the validated manifest and trace into the iPhone DAT bridge path.
9. Run the existing physical validation checklist.

## Open Questions

- Which first interface should be treated as the golden fixture: inbox, task progress, diagnostics, or command confirmation?
- Should the Web App be the first production path, or only a pre-iPhone simulator path?
- Will iPhone display output target Web Apps first, native DAT Display first, or both?
- Do we want to install Meta's Web App AI Toolkit locally, or keep this repo self-contained?

## Proposed First Task

Implement Phase 1 and Phase 2 for a single task-progress fixture:

- 600x600 display frame.
- Title, status, progress, two action buttons, and one media fallback area.
- Arrow/Enter focus navigation.
- Manifest validation.
- Structured event log.
- Readiness JSON export that passes the existing linter.

This gives us a concrete, testable interface simulator without waiting for iPhone build signing, DAT credentials, or physical glasses.

## Implementation Progress

- Added `dev/meta-rayban-display-simulator/index.html` as a static browser simulator shell.
- Added `dev/meta-rayban-display-simulator/simulator.js` with manifest normalization, validation, D-pad focus handling, bridge-shaped action results, trace export, and readiness export.
- Added `dev/meta-rayban-display-simulator/styles.css` for the fixed 600x600 display frame and external control panel.
- Added `dev/meta-rayban-display-simulator/fixtures/task-progress.json` as the golden task-progress fixture.
- Added backend routes at `/simulator/meta-rayban-display` and `/simulator/meta-rayban-display/{asset_path}` so simulator fixtures and assets load over HTTP.
- Added `mobile/src/native/__fixtures__/metaRaybanDisplaySimulatorFixtures.js` and replay coverage in `wearablesBridge` tests so the simulator fixture exercises the mobile DAT fallback path.
- Added `dev/meta-rayban-display-simulator/webapp/` as a deployable-style fixed 600x600 Web App preview with D-pad/Enter handling, event metadata persisted to `sessionStorage`, `manifest.webmanifest`, and `readiness.json`.
- The Web App preview now registers a simulator ORB edge, publishes `display_action` activation events, binds a task-service MCP-IDL descriptor, subscribes to task-progress updates, invokes the bound service, and dispatches the result back through display/audio/mobile render targets when served from the backend, while preserving local-only event storage and clearing stale cached bindings as fallback.
- Added `tests/test_meta_rayban_display_simulator.py` to verify readiness, viewport bounds, focus/action consistency, simulator JS validation, and bridge-result metadata.
