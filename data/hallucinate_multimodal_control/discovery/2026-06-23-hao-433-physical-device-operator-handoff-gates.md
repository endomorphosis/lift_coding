# HAO-433 Physical-Device Operator Handoff Gates

This discovery artifact defines the launch handoff gates for moving the
Hallucinate App virtual desktop session from hardware-free replay to
physical-device validation with a real phone, desktop peer, and Meta glasses
operator terminal.

The handoff is intentionally narrow. Physical-device validation may start only
after the command plane proves that the HAO-432 replay receipt chain still owns
policy, routing, recovery, and rendering. The real phone, desktop peer, and Meta
glasses adapters provide transport evidence only; they do not become policy
authorities.

## Gate Fixture

```json
{
  "task_id": "HAO-433",
  "artifact_id": "physical_device_operator_handoff_gates",
  "handoff_contract_ref": "physical_device_operator_handoff_gate@0.1.0",
  "source_replay_artifact": "data/hallucinate_multimodal_control/discovery/2026-06-23-hao-432-launch-slice-replay-receipts.md",
  "promotion_state": "blocked_until_all_gates_pass",
  "session_profile": "phone-hosted virtual desktop with desktop peer offload and Meta glasses terminal",
  "required_participants": [
    "phone:operator",
    "desktop:peer",
    "swissknife:ui",
    "meta_glasses:terminal"
  ],
  "operator_handoff_receipt": {
    "receipt_id": "rcpt_gate_hao433_operator_handoff",
    "receipt_contract_ref": "physical_device_operator_handoff_gate@0.1.0",
    "parent_receipt_ids": [
      "rcpt_render_hao432_final_replay",
      "rcpt_gate_hao433_phone_ingress",
      "rcpt_gate_hao433_desktop_peer_ready",
      "rcpt_gate_hao433_meta_glasses_ready",
      "rcpt_gate_hao433_operator_ack"
    ],
    "allowed_state": "physical_validation_allowed",
    "verified_by": "hallucinate_app_command_plane"
  }
}
```

## Required Gates

| Gate | Required proof before physical-device validation | Fail-closed result |
| --- | --- | --- |
| Replay parity | HAO-432 replay succeeds with stable participant IDs, fixed parent receipt order, no desktop peer dispatch before mediation, and matching phone UI, Swissknife UI, and Meta glasses render state. | Keep the session hardware-free and emit a replay parity denial receipt. |
| Real phone ingress | The phone-hosted controller submits voice, gesture, and phone UI events as `interaction_envelope` records with `context.platform: "mobile"`, `participant_id: "phone:operator"`, active session ID, and transport correlation ID. | Reject phone input if it can bypass mediation or cannot attach the active virtual desktop session. |
| Desktop peer readiness | The desktop peer proves authenticated transport, runtime health, command capability refs, stream-region support, retry budget, and a receipt return path before peer selection. | Prevent `peer_offload_policy_receipt.selected_peer` from naming the peer and fall back through mediated recovery. |
| Meta glasses terminal | Meta glasses display-widget actions and confirmations enter through the HAO-431 bridge with display-action evidence, `context.platform: "meta_glasses"`, `participant_id: "meta_glasses:terminal"`, and command receipt aliases preserved. | Deny stale or sessionless glasses actions and render the recovery state on the terminal. |
| Operator acknowledgement | The operator sees the replay proof, selected phone, selected desktop peer, selected Meta glasses terminal, policy state, and fail-closed recovery route before hardware input can mutate state. | Leave `promotion_state` blocked and require a fresh acknowledgement receipt. |
| Recovery coverage | Timeouts, disconnects, denied policy, malformed envelopes, user cancellation, stale display actions, unavailable desktop peer runtime, and exhausted retry budgets all map to `operator_console_error_recovery`. | Stop physical-device validation for any route without a recovery receipt plan. |

## Command-Plane Promotion Rule

Hallucinate App may emit `promotion_state: "physical_validation_allowed"` only
when every gate has a receipt and those receipts are parents of
`rcpt_gate_hao433_operator_handoff`. The allowed handoff receipt must be
rendered to the phone UI, Swissknife UI, desktop peer diagnostics, and Meta
glasses terminal before the first physical-device command is accepted.

Physical-device validation must remain phone-hosted and command-plane owned.
The real phone supplies operator input, the desktop peer supplies offload
execution, and Meta glasses supply constrained display and confirmation input,
but all command intents, policy decisions, operator handoff decisions, and
recovery outcomes remain Hallucinate App receipts.

## Verification Checklist

- `HAO-433` appears in the IDL and discovery evidence.
- The physical-device handoff is blocked until replay parity, real phone
  ingress, desktop peer readiness, Meta glasses terminal readiness, operator
  acknowledgement, and recovery coverage all pass.
- The phone-hosted virtual desktop cannot accept physical input without a
  mediated `operator_handoff_receipt_id`.
- The desktop peer cannot be selected until it proves capability, health, and
  receipt return path.
- Meta glasses cannot hand off to the phone-hosted virtual desktop unless the
  display action maps through the HAO-431 command-plane bridge.
- Every denial, timeout, disconnect, cancellation, retry exhaustion, or stale
  device action fails closed through receipt-backed recovery.
