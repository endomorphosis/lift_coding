# PR-076 work log

## Checklist
- [ ] Identify existing confirmation screen and API call.
- [ ] Reuse existing audio capture/upload pipeline (avoid duplicating).
- [ ] Implement yes/no transcript mapping and retry UX.
- [ ] Ensure cancel path does not confirm.
- [ ] Add minimal test for mapping logic.
- [ ] Manual test on device with Bluetooth audio.

## Transcript mapping
- confirm: `yes`, `confirm`, `do it`, `ok`
- cancel: `no`, `cancel`, `stop`, `don't`

(Keep mapping conservative; default to “did not understand”.)
