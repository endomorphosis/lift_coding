# HAO-752 Objective Validation Repair

Date: 2026-07-08
Task: HAO-752 (attempt 1)
Depends on: none
Goal id: VAIOS-G707
Goal title: Interoperate hallucinate_app with mobile
Objective heap: implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md
Objective gap fingerprint: 7edb316279e5a093e45d963b421d143361ec8d50
Objective gap ref: data/hallucinate_multimodal_control/discovery/2026-07-08-hao-752-objective-gap-7edb316279e5.md
Missing evidence: objective validation repair
Bundle: objective/interoperability/hallucinate_app-mobile
Merge family: objective/VAIOS-G707

## Summary

`data/hallucinate_multimodal_control/discovery/2026-07-08-hao-752-objective-gap-7edb316279e5.md`
filed `objective validation repair` as the missing evidence for `VAIOS-G707`
(`interface contract hallucinate_app mobile`). Two of the task's already-present
interface descriptors —
`hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql`
and `hallucinate_app/ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py`
(both delivered by HAO-740) — referenced a
`mobile/src/orb/metaGlassesOrbDescriptors.js::HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT`
export that did not actually exist, and neither
`tests/integration/test_hallucinate_app_mobile_interop.py` nor
`docs/integration/hallucinate_app-mobile.md` existed to prove the runtime
handoff.

## Repair

1. Added `HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE`,
   `HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR`, and the scanner-visible
   `HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT_ID` /
   `HALLUCINATE_APP_MOBILE_INTEROP_RECEIPTS_TABLE` /
   `HALLUCINATE_APP_MOBILE_INTEROP_ROUTES` /
   `HALLUCINATE_APP_MOBILE_INTEROP_ARTIFACT_REFS` constants to
   `mobile/src/orb/metaGlassesOrbDescriptors.js`, closing the gap the DuckDB
   schema/script pair referenced.
2. Wired `HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR` into
   `mobile/src/orb/metaGlassesMobileOrbBridge.js`'s `registerEdgeCapabilities()`
   so the mobile ORB bridge advertises the Hallucinate App interop descriptor
   alongside the existing SwissKnife/mobile and ipfs_accelerate/mobile
   descriptors.
3. Added `tests/integration/test_hallucinate_app_mobile_interop.py`, which:
   - Loads the new JS descriptor exports via a sandboxed `vm` evaluation and
     asserts they match `interface contract hallucinate_app mobile`,
     `VAIOS-G707`, the mobile ORB operation set, and the DuckDB receipts
     table/routes/artifact refs.
   - Confirms `mobile/src/orb/metaGlassesMobileOrbBridge.js` remains valid ESM
     and wires the descriptor into edge-capability registration without
     disturbing the SwissKnife/ipfs_accelerate wiring.
   - Loads `HALLUCINATE_APP_MOBILE_SEARCH_INTEROP_CONTRACT` and invokes
     `buildHallucinateAppMobileSearchHandoff()` from
     `hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js`
     to prove the desktop-to-mobile handoff payload shape.
   - Parses the machine-readable fixture embedded in
     `hallucinate_app/hallucinate_app/node/views/test_interface.html`.
   - Cross-checks `hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql`
     and `hallucinate_app/ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py`
     against the JS descriptor constants.
   - Asserts this objective validation repair is recorded here and in the
     objective heap.
4. Added `docs/integration/hallucinate_app-mobile.md` documenting the repaired
   interop path end to end.
5. Recorded this objective validation repair in
   `implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md` under
   `VAIOS-G707`.

## Evidence

- `interface contract hallucinate_app mobile`
- `objective validation repair`
- `VAIOS-G707`
- `HAO-740`
- `HAO-752`
- `mobile/src/orb/metaGlassesOrbDescriptors.js`
- `mobile/src/orb/metaGlassesMobileOrbBridge.js`
- `hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js`
- `hallucinate_app/hallucinate_app/node/views/test_interface.html`
- `hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql`
- `hallucinate_app/ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py`
- `tests/integration/test_hallucinate_app_mobile_interop.py`
- `docs/integration/hallucinate_app-mobile.md`

This keeps `VAIOS-G707` a single interoperability goal for `hallucinate_app`
and `mobile`; no smaller child goals were required to close this validation
gap.
