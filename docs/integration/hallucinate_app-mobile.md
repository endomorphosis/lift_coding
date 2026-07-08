# Hallucinate App Mobile Interop

MGW-579 objective validation repair proves VAIOS-G707 with a non-skipped
validation gate: `tests/integration/test_hallucinate_app_mobile_interop.py`.
MGW-582 keeps the same repair aligned with the retry-budget evidence for:

```bash
python -m pytest tests/integration -q
```

## Contract

- Contract: `interface contract hallucinate_app mobile`
- Event: `hallucinate-app:mobile-interop-handoff`
- Source: `hallucinate_app.content_browser.search_interface`
- Target: `mobile.meta_glasses.mobile_orb_bridge`
- Mobile interface: `handsfree.meta_glasses.mobile.hallucinate_app_mobile_interop@0.1.0`
- DuckDB event table: `hallucinate_app_mobile_interop_events`
- DuckDB receipt table: `hallucinate_mobile_handoff_receipts`

## Runtime Path

1. `hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js`
   builds a `HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR` payload and emits
   `hallucinate-app:mobile-interop-handoff` when search, filter, or clear
   actions change the content browser state.
2. `mobile/src/orb/metaGlassesOrbDescriptors.js` defines the matching
   `HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE`.
3. `mobile/src/orb/metaGlassesMobileOrbBridge.js` and
   `mobile/src/orb/metaGlassesMobileOrbRuntime.js` advertise the descriptor
   with the mobile ORB and display-widget descriptors during edge registration.
4. `hallucinate_app/hallucinate_app/node/views/test_interface.html` exposes a
   machine-readable JSON fixture for dashboard tests.
5. DuckDB records the event in `hallucinate_app_mobile_interop_events` and the
   receipt in `hallucinate_mobile_handoff_receipts`.

The integration test validates these files without Electron, React Native,
physical glasses, or a live DuckDB service. When the `duckdb` Python package is
available it also creates a temporary database and inserts sample handoff data.
