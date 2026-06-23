# HAO-438 Desktop-Peer Offload Smoke Receipt

Task: HAO-438
Goal id: VAIOS-G697
Track: launch
Missing evidence closed: desktop peer offload smoke receipt

This is the HAO-438 desktop-peer offload smoke receipt for the VAIOS-G697
launch readiness split.

This receipt-backed smoke packet proves that a phone-originated command can be
mediated by Hallucinate App, select `desktop:peer`, record the peer capability
and runtime health used for selection, emit `peer_offload_policy_receipt`, and
recover deterministically to `phone_local` when the selected peer becomes
unavailable. The desktop peer only reports capability and health. Hallucinate
App owns policy, placement, fallback, retry, and recovery receipts.

## Desktop-Peer Offload Smoke Fixture

```json
{
  "task_id": "HAO-438",
  "artifact_id": "desktop_peer_offload_smoke_receipt",
  "goal_id": "VAIOS-G697",
  "requires_physical_devices": false,
  "determinism": {
    "clock": "fixed",
    "timestamp": "2026-06-23T00:02:00Z",
    "network": "simulated",
    "random_seed": "hao-438-desktop-peer-smoke"
  },
  "stable_ids": {
    "session_id": "vdsk_hao438_desktop_peer_smoke",
    "interaction_id": "evt_hao438_open_monitor",
    "command_intent_id": "cmd_hao438_open_monitor",
    "policy_receipt_id": "rcpt_policy_hao438_open_monitor",
    "command_receipt_id": "rcpt_cmd_hao438_open_monitor",
    "placement_id": "place_hao438_desktop_peer_model_monitor",
    "peer_offload_policy_receipt_id": "rcpt_offload_hao438_open_monitor"
  },
  "participants": {
    "phone:operator": "simulated_phone_input",
    "desktop:peer": "simulated_desktop_peer_offload",
    "phone_local": "phone_local_runtime_fallback",
    "meta_glasses:terminal": "simulated_terminal_output"
  },
  "receipt_chain": [
    "phone_event",
    "mediation_receipt",
    "virtual_desktop_command_intent",
    "desktop_peer_capability_receipt",
    "desktop_peer_runtime_health_receipt",
    "peer_offload_policy_receipt",
    "runtime_receipt",
    "peer_offload_recovery_receipt",
    "render_receipt"
  ],
  "replay_steps": [
    {
      "phase": "phone_event",
      "timestamp": "2026-06-23T00:02:00Z",
      "event": {
        "interaction_id": "evt_hao438_open_monitor",
        "surface": "phone",
        "surface_event": "tap",
        "source_event_class": "phone_ui_event",
        "raw_payload": {
          "control_id": "open-model-monitor",
          "transport_correlation_id": "hao438-mobile-001"
        },
        "normalized_intent": {
          "intent": "desktop.open_widget",
          "method": "open_widget",
          "target_ref": "widget:model-monitor",
          "arguments": {
            "source": "phone"
          },
          "confidence": 1.0
        },
        "session": {
          "session_id": "vdsk_hao438_desktop_peer_smoke",
          "participant_id": "phone:operator",
          "desktop_ref": "swissknife:desktop:primary",
          "sequence": 1,
          "parent_receipt_ids": [
            "rcpt_session_hao438_join"
          ]
        }
      }
    },
    {
      "phase": "mediation",
      "timestamp": "2026-06-23T00:02:01Z",
      "receipt": {
        "receipt_id": "rcpt_policy_hao438_open_monitor",
        "receipt_contract_ref": "mediation_receipt@0.1.0",
        "interaction_id": "evt_hao438_open_monitor",
        "session_id": "vdsk_hao438_desktop_peer_smoke",
        "policy_decision": "allow",
        "policy_reason": "desktop_peer_if_available",
        "source_participant_id": "phone:operator",
        "render_targets": [
          "phone:operator",
          "meta_glasses:terminal"
        ]
      }
    },
    {
      "phase": "command_intent",
      "timestamp": "2026-06-23T00:02:02Z",
      "command": {
        "command_intent_id": "cmd_hao438_open_monitor",
        "interaction_id": "evt_hao438_open_monitor",
        "session_id": "vdsk_hao438_desktop_peer_smoke",
        "intent": "desktop.open_widget",
        "method": "open_widget",
        "target_ref": "widget:model-monitor",
        "issued_to": "desktop:peer",
        "placement_hint": {
          "placement_id": "place_hao438_desktop_peer_model_monitor",
          "preferred_surface": "desktop:peer",
          "fallback_runtime": "phone_local",
          "display_region": "right_panel",
          "attention": "foreground",
          "privacy": "operator_visible"
        },
        "receipt_ids": {
          "event_receipt_id": "rcpt_evt_hao438_open_monitor",
          "policy_receipt_id": "rcpt_policy_hao438_open_monitor",
          "command_receipt_id": "rcpt_cmd_hao438_open_monitor"
        }
      }
    },
    {
      "phase": "desktop_peer_capability",
      "timestamp": "2026-06-23T00:02:03Z",
      "capability_receipt": {
        "receipt_id": "rcpt_capability_hao438_desktop_peer",
        "participant_id": "desktop:peer",
        "session_id": "vdsk_hao438_desktop_peer_smoke",
        "capability_refs": [
          "desktop.execute_command",
          "desktop.stream_region",
          "receipt.return_path"
        ],
        "authenticated_transport": true,
        "receipt_return_path": "hallucinate_app.receipts.peer_runtime"
      }
    },
    {
      "phase": "desktop_peer_runtime_health",
      "timestamp": "2026-06-23T00:02:04Z",
      "runtime_health_receipt": {
        "receipt_id": "rcpt_health_hao438_desktop_peer",
        "participant_id": "desktop:peer",
        "session_id": "vdsk_hao438_desktop_peer_smoke",
        "runtime_status": "healthy",
        "latency_ms": 42,
        "stream_region_ready": true,
        "retry_budget_supported": true
      }
    },
    {
      "phase": "peer_offload_selection",
      "timestamp": "2026-06-23T00:02:05Z",
      "receipt": {
        "receipt_id": "rcpt_offload_hao438_open_monitor",
        "receipt_contract_ref": "peer_offload_policy_receipt@0.1.0",
        "session_id": "vdsk_hao438_desktop_peer_smoke",
        "interaction_id": "evt_hao438_open_monitor",
        "command_intent_id": "cmd_hao438_open_monitor",
        "policy_receipt_id": "rcpt_policy_hao438_open_monitor",
        "command_receipt_id": "rcpt_cmd_hao438_open_monitor",
        "placement_id": "place_hao438_desktop_peer_model_monitor",
        "policy_decision": "allow",
        "capability_receipt_id": "rcpt_capability_hao438_desktop_peer",
        "runtime_health_receipt_id": "rcpt_health_hao438_desktop_peer",
        "selected_peer": {
          "participant_id": "desktop:peer",
          "runtime_ref": "peer_orb:simulated-desktop-primary",
          "selection_reason": "preferred placement satisfied by healthy peer",
          "capability_refs": [
            "desktop.execute_command",
            "desktop.stream_region",
            "receipt.return_path"
          ]
        },
        "fallback_plan": {
          "fallback_targets": [
            "phone_local"
          ],
          "fallback_reason": null,
          "requires_operator_confirmation": false
        },
        "recovery_state": "dispatching",
        "retry_budget": {
          "max_attempts": 1,
          "attempt": 1,
          "remaining_attempts": 0
        },
        "render_targets": [
          "phone:operator",
          "meta_glasses:terminal"
        ]
      }
    },
    {
      "phase": "runtime_unavailable",
      "timestamp": "2026-06-23T00:02:07Z",
      "runtime_receipt": {
        "receipt_id": "rcpt_runtime_hao438_peer_unavailable",
        "peer_offload_policy_receipt_id": "rcpt_offload_hao438_open_monitor",
        "session_id": "vdsk_hao438_desktop_peer_smoke",
        "command_intent_id": "cmd_hao438_open_monitor",
        "policy_receipt_id": "rcpt_policy_hao438_open_monitor",
        "placement_id": "place_hao438_desktop_peer_model_monitor",
        "runtime_status": "unavailable",
        "failed_peer_id": "desktop:peer",
        "failure_reason": "peer_transport_closed_before_dispatch"
      }
    },
    {
      "phase": "phone_local_recovery",
      "timestamp": "2026-06-23T00:02:08Z",
      "receipt": {
        "receipt_id": "rcpt_recovery_hao438_phone_local",
        "receipt_contract_ref": "peer_offload_recovery_receipt@0.1.0",
        "session_id": "vdsk_hao438_desktop_peer_smoke",
        "interaction_id": "evt_hao438_open_monitor",
        "command_intent_id": "cmd_hao438_open_monitor",
        "policy_receipt_id": "rcpt_policy_hao438_open_monitor",
        "command_receipt_id": "rcpt_cmd_hao438_open_monitor",
        "placement_id": "place_hao438_desktop_peer_model_monitor",
        "peer_offload_policy_receipt_id": "rcpt_offload_hao438_open_monitor",
        "runtime_receipt_id": "rcpt_runtime_hao438_peer_unavailable",
        "recovery_outcome": "peer_unavailable",
        "recovery_state": "fallback_selected",
        "recovered_runtime": "phone_local",
        "selected_peer": {
          "participant_id": "phone_local",
          "runtime_ref": "phone_local:virtual-desktop",
          "selection_reason": "desktop peer unavailable before dispatch"
        },
        "last_good_receipt_id": "rcpt_offload_hao438_open_monitor"
      }
    },
    {
      "phase": "surface_render",
      "timestamp": "2026-06-23T00:02:09Z",
      "render_receipts": [
        {
          "receipt_id": "rcpt_render_hao438_phone",
          "participant_id": "phone:operator",
          "source_recovery_receipt_id": "rcpt_recovery_hao438_phone_local",
          "state": "fallback_selected",
          "runtime": "phone_local",
          "summary": "Desktop peer unavailable; command continued on phone_local."
        },
        {
          "receipt_id": "rcpt_render_hao438_glasses",
          "participant_id": "meta_glasses:terminal",
          "source_recovery_receipt_id": "rcpt_recovery_hao438_phone_local",
          "state": "fallback_selected",
          "runtime": "phone_local",
          "summary": "Phone-local fallback selected for the desktop command."
        }
      ]
    }
  ],
  "assertions": [
    "phone-originated command enters mediation before desktop peer dispatch",
    "desktop:peer is selected only after capability and runtime health receipts",
    "peer_offload_policy_receipt carries the selected desktop peer and placement_id",
    "desktop peer reports availability failure but does not choose fallback",
    "phone_local recovery preserves the same session_id, command_intent_id, policy_receipt_id, command_receipt_id, placement_id, and peer_offload_policy_receipt_id"
  ]
}
```

## Review Notes

- The smoke receipt is deterministic and hardware-free so it can be replayed by
  the launch gate without requiring a physical desktop peer.
- The selected `desktop:peer` announces authenticated transport, capability
  refs, runtime health, stream-region readiness, and receipt return path before
  Hallucinate App emits `peer_offload_policy_receipt`.
- The unavailable peer contributes only `runtime_status: "unavailable"` and the
  failed peer ID. The `phone_local` recovery decision is made in the
  `peer_offload_recovery_receipt` with the same session, command, policy,
  placement, and offload receipt IDs intact.
