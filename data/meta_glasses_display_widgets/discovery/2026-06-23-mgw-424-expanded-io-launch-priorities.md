# MGW-424 Expanded I/O Launch Priorities

Date: 2026-06-23
Task: MGW-424
Depends on: MGW-413, MGW-414, MGW-415, MGW-416, MGW-417, MGW-418, MGW-419, MGW-420, MGW-421, MGW-422, MGW-423

This note aggregates the expanded Meta glasses I/O launch priorities for the
supervisor. Prefer implementation tasks that make Swissknife applications use
Meta glasses interaction methods through explicit contracts, deterministic
mocks, privacy and policy checks, control-plane routes, IPFS/libp2p/MCP++
receipts, and Playwright validation.

## Priority Rule

Prioritize open P0/P1 expanded-I/O tasks when they close one of these launch
gaps:

- Swissknife applications can request camera, microphone, speaker/headphone,
  display, Meta Neural Band, captouch, motion/orientation, and phone GPS
  capabilities through app-facing contracts instead of importing native DAT or
  Web Apps implementation details.
- Hardware-free mocks cover camera photo/video references, Bluetooth
  microphone and speaker/headphone route state, native display lifecycle,
  Meta Neural Band and captouch Arrow/Enter intents, motion/orientation, phone
  GPS, permission denial, unsupported capability, degraded route, route loss,
  and fallback states.
- Hallucinate App policy checks run before expanded-I/O events or payload
  references enter the Swissknife control-plane routes.
- Control-plane routes produce app binding IDs, route decisions, IPFS CIDs,
  libp2p peer/session IDs, replay/backpressure metadata, and MCP++ receipts
  without claiming raw Bluetooth or Wi-Fi packet compatibility.
- Playwright opens Swissknife applications against the mocked expanded-I/O
  surface and verifies visible app state, permission or denial behavior,
  fallback UI, app interaction bindings, content-addressed capture references,
  control-plane receipts, and no unauthorized handoff.
- Native DAT or physical-device work remains gated by package credentials,
  release channel or Developer Mode, app registration, firmware/glasses-app
  update state, paired hardware, runtime capability checks, and rollback
  evidence.

Deprioritize generic code-annotation cleanup whenever any open P0/P1
expanded-I/O task still lacks contracts, mocks, policy tests, control-plane
route coverage, IPFS/libp2p/MCP++ receipt evidence, Playwright validation, or
launch-readiness evidence. Code-annotation tasks should only outrank this
stream when they directly block those deliverables or break the validation
commands for them.

## Aggregated Dependency Signals

- MGW-413 is the source gate: native DAT owns camera photo/video, native display
  lifecycle, and Bluetooth audio route modeling; display Web Apps own Meta
  Neural Band, captouch, motion/orientation, phone GPS, browser-tested D-pad
  input, and local storage.
- MGW-414 through MGW-418 define the contract and mock surface required before
  Swissknife applications can consume expanded Meta glasses I/O without
  hardware or Meta package credentials.
- MGW-419 through MGW-420 keep expanded I/O behind policy decisions and
  app-level IPFS/libp2p/MCP++ bridge envelopes with receipts.
- MGW-421 through MGW-422 turn the contracts into app-level proof by requiring a
  Swissknife demo and Playwright validation for mocked camera, audio, display,
  Meta Neural Band, captouch, motion/GPS, and control-plane handoff.
- MGW-423 keeps native DAT and physical validation optional until feature gates,
  package/release-channel state, paired hardware, capability checks, and
  fallback evidence are present.

The supervisor should treat this stream as launch-enabling work, not scan
churn. The next accepted task should increase the amount of evidence that a
Swissknife application can bind to Meta glasses interaction methods, exercise
them in CI-safe mocks, pass policy and routing checks, and produce receipts that
operators can inspect.
