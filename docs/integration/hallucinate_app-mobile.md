# hallucinate_app and mobile interoperability

VAIOS-G707 proves that `hallucinate_app` and `mobile` can exchange dashboard
handoffs through an importable interface contract, a visible Electron test
surface, mobile-side validation utilities, and benchmark receipt storage.

## Contract

- Contract: `handsfree.hallucinate_app/mobile-handoff@0.1.0`
- Interface descriptor: `hallucinate_app.mobile.interface_descriptor.v1`
- Producer: `hallucinate_app`
- Consumer: `mobile`
- Runtime event: `hallucinate-app:mobile-handoff`
- Validation command: `python -m pytest tests/integration -q`

Every handoff contains:

```json
{
  "contract": "handsfree.hallucinate_app/mobile-handoff@0.1.0",
  "descriptor": "hallucinate_app.mobile.interface_descriptor.v1",
  "operation": "search",
  "request_id": "hao-mobile-search-...",
  "source": "hallucinate_app",
  "target": "mobile",
  "payload": {},
  "handoff": {},
  "policy": {},
  "created_at": "2026-07-08T00:00:00.000Z"
}
```

Supported operations are `search`, `filter`, `clear`, `module_test`, and
`benchmark_telemetry`.

## Runtime handoff

`hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js`
exports the shared descriptor and builds mobile handoff envelopes for content
browser search, filter, and clear actions. Direct component listeners receive a
`mobile-handoff` event. When `mobileInterop.enabled` is set, the component also
emits `hallucinate-app:mobile-handoff` on the dashboard event bus.

`mobile/src/utils/hallucinateAppInterop.js` is the mobile-side contract module.
It builds mobile handoff envelopes for native surfaces, validates incoming
handoffs from `hallucinate_app`, and creates receipt objects that can be stored
or returned to the producer.

## Operator test surface

`hallucinate_app/hallucinate_app/node/views/test_interface.html` includes a
Mobile Handoff module test. The test parses the descriptor, verifies the shared
contract and required fields, and records a pass/fail result in the same summary
table used by the other module tests.

## Receipt storage

`hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql`
and `hallucinate_app/ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py`
define `hallucinate_app_mobile_handoffs`. The table stores request payloads,
policy state, handoff routing metadata, mobile receipts, status, and
acknowledgement timestamps for replay and objective validation.

## Evidence

- `tests/integration/test_hallucinate_app_mobile_interop.py`
- `docs/integration/hallucinate_app-mobile.md`
- `mobile/src/utils/hallucinateAppInterop.js`
- `hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js`
- `hallucinate_app/hallucinate_app/node/views/test_interface.html`
- `hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql`
- `hallucinate_app/ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py`

