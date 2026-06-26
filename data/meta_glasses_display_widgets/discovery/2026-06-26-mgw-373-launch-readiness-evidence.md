# MGW-373 Expanded Meta Glasses I/O Launch Readiness Evidence

Date: 2026-06-26
Task: MGW-373
Status: hardware-free ready; physical validation pending

MGW-373 aggregates the expanded Meta glasses I/O launch evidence for camera,
microphone, speaker/headphone, display, Meta Neural Band, captouch,
motion/orientation, phone GPS, control plane, IPFS, libp2p, MCP++, and
Playwright coverage.

## Evidence Summary

- Official Meta research baseline:
  `2026-06-23-mgw-363-meta-glasses-io-research.md` and
  `2026-06-23-mgw-413-expanded-io-source-refresh.md` keep native DAT,
  Bluetooth audio routes, display Web Apps, Meta Neural Band, captouch,
  motion/GPS, and unsupported surfaces separated.
- Capability contract:
  `swissknife/docs/meta-glasses-io-contract.md` defines required camera,
  microphone, headphone, display, Meta Neural Band, captouch, motion, GPS,
  permission, fallback, control-plane, IPFS/libp2p, and MCP++ receipt fields.
- Mocks:
  `swissknife/test/fixtures/meta-glasses-io/hardware-free-expanded-io.json`
  provides camera, microphone, speaker/headphone, display, Meta Neural Band,
  captouch, motion/GPS, app binding, control-plane envelope, and fallback
  fixtures without Meta credentials or hardware.
- Bluetooth/Wi-Fi envelope:
  `docs/meta-glasses-io-transport-envelope.md` and
  `docs/meta-glasses-mobile-bridge-routes.md` enforce app-level bridge metadata
  and keep raw Bluetooth/Wi-Fi separate from IPFS/libp2p/MCP++.
- Swissknife app interaction bindings:
  `swissknife/docs/meta-glasses-input-app-descriptors.md` and
  `swissknife/docs/meta-glasses-control-plane-routing.md` map camera,
  microphone, headphone, display, Meta Neural Band, captouch, motion/GPS events
  to app bindings, ORB/MCP++ operations, Hallucinate App policy handoff, and
  deterministic receipts.
- Conformance:
  `docs/meta-glasses-io-conformance.md`,
  `tests/test_meta_glasses_io_mcpplusplus_contract.py`, and
  `swissknife/test/mcp-plus-plus/meta-glasses-io-conformance.test.ts` assert
  content CIDs, libp2p peer/session IDs, MCP++ receipts, policy decisions,
  privacy metadata, bridge route state, control-plane route decisions, fallback
  behavior, malformed envelope failures, and unauthorized control-plane handoff
  failures.
- Playwright:
  `swissknife/docs/meta-glasses-io-playwright.md` and
  `swissknife/test/e2e/meta-glasses-io-apps.spec.ts` validate visible
  Swissknife app state, camera permission flows, microphone/speaker/headphone
  route state, Meta Neural Band and captouch input, motion/GPS context, display
  diagnostics, IPFS/libp2p/MCP++ handoff evidence, and fallback UI without
  physical glasses.

## Launch Position

The launch readiness state is `hardware_free_ready_physical_validation_pending`.
The checked-in evidence is sufficient for CI, launch replay, and fallback
contract review. It is not sufficient for production hardware rollout until
operators complete physical DAT, display Web App, Bluetooth audio route, and
permission-denial evidence in
`docs/meta-wearables-dat-display-rollout-evidence-template.md`.

## Required Fallback Evidence

Physical validation must prove:

- unsupported hardware returns structured unsupported/fallback receipts;
- missing DAT credentials or package access keeps native DAT disabled and emits
  package or release-channel unavailable evidence;
- missing display access emits display SDK, DAM, target, firmware, DAT app, or
  lifecycle failure evidence with Web App/mobile fallback;
- denied camera, microphone, headphone, display, Meta Neural Band, captouch,
  motion, GPS, or control-plane permissions emit MCP++ policy-denial receipts;
- unavailable audio routes return route-lost, route-unavailable, or degraded
  behavior without raw-audio leakage.

