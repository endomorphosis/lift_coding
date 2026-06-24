# MGW-519 Meta Glasses Control-Plane Mocks and Playwright Fixtures

Date: 2026-06-24

MGW-519 adds reusable Meta glasses control-plane mocks for Swissknife validation
without paired hardware. The fixture path is intentionally the same as the
MGW-518 route contract: camera, microphone, headphones, display, and Neural Band
events are emitted as MCP++-compatible control-plane envelopes instead of raw
Bluetooth, Wi-Fi, audio, camera, or neural-band packets.

Implemented artifacts:

- Swissknife builder:
  `swissknife/src/services/meta-glasses-multimodal-io-transport-contract.ts`
- Playwright-ready JSON fixture:
  `swissknife/test/e2e/fixtures/mgw-519-meta-glasses-control-plane.json`
- Swissknife fixture tests:
  `swissknife/test/mcp-plus-plus/meta-glasses-control-plane-fixtures.test.ts`
- Mobile mock builder:
  `mobile/src/utils/metaGlassesMultimodalIoTransportContract.js`
- Backend/Python fixture builder:
  `src/handsfree/meta_glasses_multimodal_io_transport_contract.py`
- Focused Python coverage:
  `tests/test_meta_glasses_multimodal_io_transport_contract.py`

Fixture behavior:

- `camera.photo_ref` carries only a content-addressed photo reference and
  redaction metadata.
- `microphone.transcript_ref` carries a transcript CID and explicitly excludes
  raw-audio payloads.
- `headphones.playback_state` models Bluetooth A2DP output state.
- `display.action` models a Swissknife display widget render through the
  control-plane route.
- `Neural Band.intent` models an Enter activation intent.
- Every event uses `swissknife.mobile_orb.publish_glasses_event` and the
  `swissknife.mcp++/event-envelope@0.1.0` profile.
- DAT availability is represented as `dat_unavailable`, so Playwright can run
  without physical Meta glasses while preserving the same fallback boundary.
- Each event includes a receipt CID, and `replay_receipts` marks those receipts
  with `preserve_for_dat_replay: true` for later physical DAT replay sessions.

The checked-in Playwright fixture is a static JSON artifact so browser tests can
load it directly. The Python, Swissknife TypeScript, and mobile JavaScript
builders generate the same deterministic event sequence for unit tests and
application-level mocks.
