# PR-118: Dev docs port + dev-audio payload alignment

## Summary
Fix docs drift around backend port and dev audio upload payload so device bring-up and demos match the real backend defaults.

## Changes
- Normalize runbooks/docs from port `8000` -> `8080` for backend API examples.
- Update dev audio upload examples to use `data_base64`.
- Make backend `/v1/dev/audio` accept `audio_base64` as an alias (backwards compatible).

## Test plan
- Manual doc sanity check: follow the runbook curl examples against a locally running backend on `http://localhost:8080`.
- (Optional) Run `pytest` once deps include optional secret-manager packages.
