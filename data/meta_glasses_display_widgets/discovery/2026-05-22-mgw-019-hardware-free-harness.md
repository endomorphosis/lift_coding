# MGW-019 Hardware-Free Harness Expansion

Date: 2026-05-22
Task: MGW-019 Broaden the hardware-free display widget harness for discovered lifecycle gaps

## Outcome

The backend, mobile, and Swissknife hardware-free harnesses now cover the display widget paths called out by MGW-013:

- render, update, clear, focus, activate, reset, `play_video`, and `subscribe_updates`
- policy denial before mobile dispatch
- native-display-unavailable fallback
- firmware update required and DAT glasses app update required fixture states
- lifecycle error diagnostics and stream event metadata

The fixtures use only local mock bridge state and do not require Meta credentials, DAT package access, or paired glasses.

## Validation

Planned validation commands for this task:

```bash
PYTHONPATH=./src pytest tests/test_meta_glasses_display_widget_harness.py
cd mobile && npm test -- --runInBand src/utils/__tests__/displayWidgetHarness.test.js
cd swissknife && npx jest test/mcp-plus-plus/meta-glasses-display-harness.test.ts --config=config/jest/jest.config.cjs --runInBand
```
