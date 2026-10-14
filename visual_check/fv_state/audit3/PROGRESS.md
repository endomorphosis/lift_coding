# Audit3 continuation progress (2026-10-14) — FINAL

- Fix 1 (R6) APPLIED + check_fix1.mjs PASSED + live-verified (zero SAMPLE
  leakage in both browser probes).
- Fix 2 (R7) APPLIED + check_fix2.mjs PASSED (dry-run local preview;
  confirmed keeps typed error). Live pane drive needs a seeded Profile G
  target — stack state empty; named remaining step (see notes).
- Fix 3 (P16) APPLIED + check_fix3.mjs PASSED + LIVE ROUND-TRIP PROVED:
  persist denied w/o token; persisted CID
  bafkreidjbmeouqe42mu3uioynseoqgdtfjzrs3yiqv743jcxd56ftvpkw4 (helia,
  verified); retrieve verified 206 bytes; checkpoint event
  bafkreicbw5f2hfeflzmtksufkqfzfwxhl6i25qyiu7ui2ujhwzm7a6trwy; logs available.
- Fix 4 (R8) APPLIED + check_fix4.mjs PASSED + live tab navigation proved.
- Fix 5 (R9) APPLIED: datasets-browser invokes real descriptor ops; canned
  refs grep = 0 across web/js/; live drive fv-15 (real envelopes).
- Fix 6 (R10) APPLIED: accelerate-panel invokes real descriptor ops; fake
  WebGPU claim gone; Cancel typed; live drive fv-16.
- Step 7 DONE: trace-table.json + TRACE_TABLE.md (census 1,401 controls
  computed from inventory-raw.json; 38 tool-backed; 21 fixed; caps 9/1/6).
- Step 8 DONE: probes live_probe{,2,3}.mjs + results JSONs; screenshots
  fv-14..fv-17. Settled console error set = exactly the 4 typed B8 caps.
- Step 9 DONE: BROKEN_CONTRACT_MAP.md (P16, R6-R10, B8-B10, §4, §5 A3
  table, §6 pending suite line), FEATURE_MATRIX.md (F-14 + screenshots),
  SWISSKNIFE_FIX_NOTES.md (audit3 section).
- Step 10 DONE: vitest batch 1 = 17/17 passed. Batch 2 = 40/41 (1 failure
  = SVD-098 stale expectation, pre-existing, B9). Integration suite =
  528 passed / 29 skipped / 0 failed (677.19 s) — baseline held.
- All changes UNCOMMITTED. No git run in external/ipfs_accelerate or
  external/ipfs_datasets. Preserved czechia normalize.py untouched.
