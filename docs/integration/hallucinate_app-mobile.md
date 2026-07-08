# Hallucinate App Mobile Interop

This note records the `interface contract hallucinate_app mobile` proof for
VAIOS-G707 / HAO-740.

## Contract

Hallucinate App is the desktop/operator surface. Mobile is the phone/glasses
edge surface. They interoperate through the mobile ORB routes exposed by the
handsfree backend:

- `/v1/mobile/orb/register_edge_capabilities`
- `/v1/mobile/orb/publish_glasses_event`
- `/v1/mobile/orb/bind_service`
- `/v1/mobile/orb/invoke_service`
- `/v1/mobile/orb/dispatch_glasses_response`
- `/v1/mobile/orb/diagnostics`

Every handoff carries `control_surface_contract:hallucinate-app:remote-client`
and the canonical control-surface artifacts:

- `interaction_envelope`
- `policy_decision`
- `mediation_receipt`

## Implemented Evidence

- `mobile/src/orb/metaGlassesOrbDescriptors.js` exports
  `HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT`,
  `HALLUCINATE_APP_MOBILE_HANDOFF_INTERFACE`, and
  `hallucinateAppMobileInteropDescriptorRef()`.
- `hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js`
  exports `HALLUCINATE_APP_MOBILE_SEARCH_INTEROP_CONTRACT` and
  `buildHallucinateAppMobileSearchHandoff()`, then emits
  `hallucinate_app-mobile:handoff` when a desktop search is submitted.
- `hallucinate_app/hallucinate_app/node/views/test_interface.html` advertises
  the same descriptor and includes the mobile ORB diagnostics route in the live
  backend test suite.
- `src/handsfree/meta_glasses_mobile_orb_artifacts.py` builds the runtime
  register, bind, invoke, and dispatch receipt artifacts used by the backend.
- `hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql`
  defines `hallucinate_app_mobile_interop_receipts` so benchmark runs can retain
  mobile handoff receipt evidence.

## Validation

`tests/integration/test_hallucinate_app_mobile_interop.py` proves the descriptor
terms, UI exposure, runtime handoff behavior, and DuckDB evidence paths. It is
included in the repository-wide integration command:

```bash
python -m pytest tests/integration -q
```
