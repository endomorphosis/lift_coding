# MGW-270 Launch-Session Widget Replay Evidence

The hardware-free phone/glasses terminal fixture now carries MGW-270 launch replay evidence in:

`data/meta_glasses_display_widgets/discovery/2026-06-23-mgw-267-phone-glasses-terminal-fixture.json`

Evidence summary:

- `schema_version` is `1.1.0`.
- `launch_replay_evidence.replay_id` is `launch-session-widget-replay-mgw-270`.
- The single replay remains deterministic and requires no Meta credentials, paired hardware, or live transport.
- The three replay events cover phone-hosted virtual desktop status, confirmation UI, and desktop-peer offload transfer state.
- `regions.status_region`, `regions.diagnostics_region`, `regions.action_region.actions[*]`, `confirmation_prompt.actions[*]`, and `peer_offload.receipts` expose Hallucinate App mediation receipt IDs through the Meta glasses widget contract.
- The confirmation event renders `confirm`, `cancel`, and `retry` action kinds with backend-approved `terminal.*` action IDs and stable focus order.
- The offload event renders `desktop_peer` compute placement, transfer progress, cancel/retry/fallback actions, and the `ha-mgw270-offload-receipt` Hallucinate App receipt ID.

Validation target:

```bash
PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_meta_glasses_display_todo_queue.py::test_hardware_free_phone_glasses_terminal_fixture_is_deterministic tests/test_meta_glasses_display_todo_queue.py -q
```
