# MGW-272 Shared VAI Capability Receipt Binding

The launch replay evidence now binds the Meta glasses terminal actions to the
shared VAI capability registry receipts used by the phone-hosted virtual desktop
session.

Evidence artifact:

- `data/meta_glasses_display_widgets/discovery/2026-06-23-mgw-267-phone-glasses-terminal-fixture.json`
- `schema_version: "1.2.0"`
- `launch_replay_evidence.replay_id: "launch-session-widget-replay-mgw-272"`
- `launch_replay_evidence.extends_replay_id: "launch-session-widget-replay-mgw-270"`
- `launch_replay_evidence.command_contract: "vai.shared_capability_envelope@0.1.0"`
- `launch_replay_evidence.no_second_widget_command_contract: true`

Shared VAI capability receipts:

- `bafy-mgw272-vai-render-receipt`
- `bafy-mgw272-vai-update-receipt`
- `bafy-mgw272-vai-confirm-receipt`
- `bafy-mgw272-vai-cancel-receipt`

Placement and recovery receipts reused by the replay:

- `bafy-mgw267-placement-phone`
- `bafy-mgw267-placement-peer`
- `bafy-mgw272-recovery-preview`

Binding rules captured in the fixture:

- `shared_vai_receipts` appears on every replayed widget state and links the
  active `vai.glasses_widget.*` capability to the Hallucinate App mediation
  receipt, policy receipt, ORB receipt, placement receipt, recovery receipt, and
  render result.
- Every `regions.action_region.actions[*]` entry and every
  `confirmation_prompt.actions[*]` entry carries `vai_capability_id`,
  `capability_receipt_cid`, `mediation_receipt_id`, `placement_receipt_cid`,
  `recovery_receipt_cid`, and the shared command contract.
- Existing `terminal.*` backend action IDs are unchanged, so the replay extends
  the MGW-270 launch evidence without creating a second widget command contract.
- `peer_offload.receipts` repeats the same shared receipt chain for the active
  compute placement, including the desktop-peer transfer state.

Validation:

```bash
PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_meta_glasses_display_todo_queue.py tests/test_virtual_ai_os_capability_registry.py -q
```
