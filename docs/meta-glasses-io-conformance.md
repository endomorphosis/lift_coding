# Meta Glasses I/O Conformance

MGW-371 adds a focused conformance gate for the Meta glasses I/O bridge and
Swissknife MCP++ control-plane router.

The Jest suite covers camera, audio, Neural Band, captouch, motion/GPS, and
display mock flows. Each accepted route must expose stable content CIDs when
payloads are persisted, libp2p peer/session identifiers for Wi-Fi app-layer
network routes, MCP++ tool/event receipts, explicit policy decisions, privacy
redaction metadata, bridge route state, control-plane route decisions, app
binding IDs, fallback behavior, and Bluetooth/Wi-Fi envelope metadata.

Required invariants:

- stable content CIDs
- libp2p peer/session identifiers
- MCP++ tool/event receipts
- explicit policy decisions
- privacy redaction metadata
- bridge route state
- control-plane route decisions
- app binding IDs
- fallback behavior
- Bluetooth/Wi-Fi envelope metadata
- malformed envelopes
- unauthorized control-plane handoffs

The same suite also checks deterministic validation failures for malformed
envelopes and unauthorized control-plane handoffs. The malformed envelopes must
report stable transport error codes for invalid app-layer claims, bad content
CIDs, and missing MCP++ receipts. Unauthorized handoffs must terminate as a
policy-denied control-plane route with a deterministic replay key and receipt
CID.

Validation commands:

```bash
PYTHONPATH=./src pytest tests/test_meta_glasses_io_mcpplusplus_contract.py
cd swissknife && npx jest test/mcp-plus-plus/meta-glasses-io-conformance.test.ts --config=config/jest/jest.config.cjs --runInBand
```
