# HAO-432 Launch-Slice Replay Receipts

This launch-slice deterministic replay artifact promotes the HAO-429 peer
offload receipts, the HAO-430 hardware-free harness, and the HAO-431 Meta
glasses command-plane bridge into one replayable sequence. It records
phone-originated commands, desktop peer selection, policy decisions,
fallback/retry/cancel outcomes, and Meta glasses status updates with stable
receipt IDs.

The sequence is hardware-free. It uses a fixed clock, simulated network, stable
participant IDs, and receipt parents instead of physical phone, desktop peer,
Swissknife browser, or Meta glasses devices. Replayers process the ledger in
order and verify that every recovery and render status derives from the same
receipt chain.

## Deterministic Launch-Slice Replay Fixture

```json
{
  "task_id": "HAO-432",
  "artifact_id": "launch_slice_replay_receipts",
  "extends_harness_id": "hardware_free_multimodal_offload_harness",
  "requires_physical_devices": false,
  "determinism": {
    "clock": "fixed",
    "timestamp": "2026-06-23T00:01:00Z",
    "network": "simulated",
    "random_seed": "hao-432-launch-slice-fixed-replay"
  },
  "participants": {
    "phone:operator": "simulated_phone_input",
    "desktop:peer": "simulated_desktop_peer_offload",
    "swissknife:ui": "simulated_operator_ui",
    "meta_glasses:terminal": "simulated_terminal_output"
  },
  "receipt_chain": [
    "phone_event",
    "mediation_receipt",
    "virtual_desktop_command_intent",
    "peer_offload_policy_receipt",
    "runtime_receipt",
    "peer_offload_recovery_receipt",
    "meta_glasses_status_receipt",
    "render_receipt"
  ],
  "replay_steps": [
    {
      "phase": "phone_event",
      "timestamp": "2026-06-23T00:01:00Z",
      "event": {
        "interaction_id": "evt_hao432_open_monitor",
        "surface": "voice",
        "surface_event": "utterance",
        "source_event_class": "phone_ui_event",
        "raw_payload": {
          "transcript": "open the model monitor on my desktop",
          "transport_correlation_id": "hao432-mobile-001"
        },
        "normalized_intent": {
          "intent": "desktop.open_widget",
          "method": "open_widget",
          "target_ref": "widget:model-monitor",
          "arguments": {
            "source": "phone"
          },
          "confidence": 0.94
        },
        "session": {
          "session_id": "vdsk_hao432_launch_slice",
          "participant_id": "phone:operator",
          "desktop_ref": "swissknife:desktop:primary",
          "sequence": 1,
          "parent_receipt_ids": [
            "rcpt_session_hao432_join"
          ]
        }
      }
    },
    {
      "phase": "mediation",
      "timestamp": "2026-06-23T00:01:01Z",
      "receipt": {
        "receipt_id": "rcpt_policy_hao432_open_monitor",
        "receipt_contract_ref": "mediation_receipt@0.1.0",
        "interaction_id": "evt_hao432_open_monitor",
        "policy_decision": "allow",
        "policy_reason": "desktop_peer_if_available",
        "source_participant_id": "phone:operator",
        "render_targets": [
          "phone:operator",
          "swissknife:ui",
          "meta_glasses:terminal"
        ]
      }
    },
    {
      "phase": "command_intent",
      "timestamp": "2026-06-23T00:01:02Z",
      "command": {
        "command_intent_id": "cmd_hao432_open_monitor",
        "interaction_id": "evt_hao432_open_monitor",
        "session_id": "vdsk_hao432_launch_slice",
        "intent": "desktop.open_widget",
        "method": "open_widget",
        "target_ref": "widget:model-monitor",
        "issued_to": "desktop:peer",
        "receipt_ids": {
          "event_receipt_id": "rcpt_evt_hao432_open_monitor",
          "policy_receipt_id": "rcpt_policy_hao432_open_monitor",
          "command_receipt_id": "rcpt_cmd_hao432_open_monitor"
        }
      }
    },
    {
      "phase": "peer_offload_selection",
      "timestamp": "2026-06-23T00:01:03Z",
      "receipt": {
        "receipt_id": "rcpt_offload_hao432_open_monitor",
        "receipt_contract_ref": "peer_offload_policy_receipt@0.1.0",
        "session_id": "vdsk_hao432_launch_slice",
        "interaction_id": "evt_hao432_open_monitor",
        "policy_receipt_id": "rcpt_policy_hao432_open_monitor",
        "command_receipt_id": "rcpt_cmd_hao432_open_monitor",
        "policy_decision": "allow",
        "selected_peer": {
          "participant_id": "desktop:peer",
          "runtime_ref": "peer_orb:simulated-desktop-primary",
          "selection_reason": "preferred placement satisfied"
        },
        "fallback_plan": {
          "fallback_targets": [
            "swissknife:ui",
            "phone:operator",
            "meta_glasses:terminal"
          ],
          "fallback_reason": null,
          "requires_operator_confirmation": false
        },
        "recovery_state": "dispatching",
        "retry_budget": {
          "max_attempts": 2,
          "attempt": 1,
          "remaining_attempts": 1
        },
        "render_targets": [
          "phone:operator",
          "swissknife:ui",
          "meta_glasses:terminal"
        ]
      }
    },
    {
      "phase": "runtime_timeout",
      "timestamp": "2026-06-23T00:01:05Z",
      "runtime_receipt": {
        "receipt_id": "rcpt_runtime_hao432_peer_timeout_1",
        "peer_offload_policy_receipt_id": "rcpt_offload_hao432_open_monitor",
        "runtime_status": "timeout",
        "failed_peer_id": "desktop:peer",
        "timeout_ms": 2500
      }
    },
    {
      "phase": "retry_recovery",
      "timestamp": "2026-06-23T00:01:06Z",
      "receipt": {
        "receipt_id": "rcpt_recovery_hao432_retry",
        "receipt_contract_ref": "peer_offload_recovery_receipt@0.1.0",
        "session_id": "vdsk_hao432_launch_slice",
        "interaction_id": "evt_hao432_open_monitor",
        "policy_receipt_id": "rcpt_policy_hao432_open_monitor",
        "command_receipt_id": "rcpt_cmd_hao432_open_monitor",
        "peer_offload_policy_receipt_id": "rcpt_offload_hao432_open_monitor",
        "runtime_receipt_id": "rcpt_runtime_hao432_peer_timeout_1",
        "recovery_outcome": "retry_scheduled",
        "recovery_state": "retry_scheduled",
        "retry_attempt": 2,
        "remaining_attempts": 0,
        "next_target_participant_id": "desktop:peer",
        "last_good_receipt_id": "rcpt_offload_hao432_open_monitor"
      }
    },
    {
      "phase": "meta_glasses_status_retry",
      "timestamp": "2026-06-23T00:01:06Z",
      "meta_glasses_status_receipt": {
        "receipt_id": "rcpt_glasses_hao432_retry",
        "participant_id": "meta_glasses:terminal",
        "source_recovery_receipt_id": "rcpt_recovery_hao432_retry",
        "state": "retry_scheduled",
        "summary": "Retrying desktop peer attempt 2."
      }
    },
    {
      "phase": "runtime_timeout_after_retry",
      "timestamp": "2026-06-23T00:01:09Z",
      "runtime_receipt": {
        "receipt_id": "rcpt_runtime_hao432_peer_timeout_2",
        "peer_offload_policy_receipt_id": "rcpt_offload_hao432_open_monitor",
        "runtime_status": "timeout",
        "failed_peer_id": "desktop:peer",
        "timeout_ms": 2500
      }
    },
    {
      "phase": "fallback_recovery",
      "timestamp": "2026-06-23T00:01:10Z",
      "receipt": {
        "receipt_id": "rcpt_recovery_hao432_fallback",
        "receipt_contract_ref": "peer_offload_recovery_receipt@0.1.0",
        "session_id": "vdsk_hao432_launch_slice",
        "interaction_id": "evt_hao432_open_monitor",
        "policy_receipt_id": "rcpt_policy_hao432_open_monitor",
        "command_receipt_id": "rcpt_cmd_hao432_open_monitor",
        "peer_offload_policy_receipt_id": "rcpt_offload_hao432_open_monitor",
        "runtime_receipt_id": "rcpt_runtime_hao432_peer_timeout_2",
        "parent_receipt_ids": [
          "rcpt_recovery_hao432_retry"
        ],
        "recovery_outcome": "timeout",
        "recovery_state": "fallback_selected",
        "selected_peer": {
          "participant_id": "swissknife:ui",
          "runtime_ref": "local_orb:simulated-swissknife",
          "selection_reason": "desktop peer timed out and retry budget exhausted"
        },
        "last_good_receipt_id": "rcpt_recovery_hao432_retry"
      }
    },
    {
      "phase": "meta_glasses_status_fallback",
      "timestamp": "2026-06-23T00:01:10Z",
      "meta_glasses_status_receipt": {
        "receipt_id": "rcpt_glasses_hao432_fallback",
        "participant_id": "meta_glasses:terminal",
        "source_recovery_receipt_id": "rcpt_recovery_hao432_fallback",
        "state": "fallback_selected",
        "summary": "Desktop unavailable; monitor opened in Swissknife."
      }
    },
    {
      "phase": "phone_cancel_event",
      "timestamp": "2026-06-23T00:01:12Z",
      "event": {
        "interaction_id": "evt_hao432_cancel_monitor",
        "surface": "voice",
        "surface_event": "cancel",
        "source_event_class": "phone_ui_event",
        "raw_payload": {
          "transcript": "cancel that",
          "transport_correlation_id": "hao432-mobile-002"
        },
        "normalized_intent": {
          "intent": "desktop.cancel_command",
          "method": "cancel_command",
          "target_ref": "cmd_hao432_open_monitor",
          "arguments": {
            "source": "phone"
          },
          "confidence": 0.97
        },
        "session": {
          "session_id": "vdsk_hao432_launch_slice",
          "participant_id": "phone:operator",
          "desktop_ref": "swissknife:desktop:primary",
          "sequence": 2,
          "parent_receipt_ids": [
            "rcpt_recovery_hao432_fallback"
          ]
        }
      }
    },
    {
      "phase": "cancel_mediation",
      "timestamp": "2026-06-23T00:01:13Z",
      "receipt": {
        "receipt_id": "rcpt_policy_hao432_cancel_monitor",
        "receipt_contract_ref": "mediation_receipt@0.1.0",
        "interaction_id": "evt_hao432_cancel_monitor",
        "policy_decision": "allow",
        "policy_reason": "operator_cancel_allowed",
        "source_participant_id": "phone:operator",
        "render_targets": [
          "phone:operator",
          "swissknife:ui",
          "meta_glasses:terminal"
        ]
      }
    },
    {
      "phase": "cancel_recovery",
      "timestamp": "2026-06-23T00:01:14Z",
      "receipt": {
        "receipt_id": "rcpt_recovery_hao432_cancelled",
        "receipt_contract_ref": "peer_offload_recovery_receipt@0.1.0",
        "session_id": "vdsk_hao432_launch_slice",
        "interaction_id": "evt_hao432_cancel_monitor",
        "policy_receipt_id": "rcpt_policy_hao432_cancel_monitor",
        "command_receipt_id": "rcpt_cmd_hao432_open_monitor",
        "peer_offload_policy_receipt_id": "rcpt_offload_hao432_open_monitor",
        "cancel_source_participant_id": "phone:operator",
        "cancel_event_receipt_id": "rcpt_evt_hao432_cancel_monitor",
        "last_good_receipt_id": "rcpt_recovery_hao432_fallback",
        "recovery_outcome": "cancelled",
        "recovery_state": "cancelled"
      }
    },
    {
      "phase": "surface_render",
      "timestamp": "2026-06-23T00:01:15Z",
      "render_receipts": [
        {
          "receipt_id": "rcpt_render_hao432_phone",
          "participant_id": "phone:operator",
          "source_recovery_receipt_id": "rcpt_recovery_hao432_cancelled",
          "state": "cancelled",
          "summary": "Cancelled the model monitor command."
        },
        {
          "receipt_id": "rcpt_render_hao432_swissknife",
          "participant_id": "swissknife:ui",
          "source_recovery_receipt_id": "rcpt_recovery_hao432_cancelled",
          "state": "cancelled",
          "summary": "Cancelled command from phone receipt."
        },
        {
          "receipt_id": "rcpt_render_hao432_glasses",
          "participant_id": "meta_glasses:terminal",
          "source_recovery_receipt_id": "rcpt_recovery_hao432_cancelled",
          "state": "cancelled",
          "summary": "Command cancelled from phone."
        }
      ]
    }
  ],
  "assertions": [
    "phone-originated commands enter mediation before dispatch",
    "desktop peer selection is receipt-backed by policy_decision",
    "retry_scheduled, fallback_selected, and cancelled outcomes are replayed in one sequence",
    "Meta glasses status updates use the same recovery receipt IDs as phone and Swissknife renders",
    "receipt IDs remain stable across retry, fallback, and cancel"
  ]
}
```

## Replay Notes

- The phone simulator originates both the open command and the cancel command.
- The desktop peer simulator only reports runtime timeout receipts; it never
  selects retry, fallback, or cancellation state.
- Hallucinate App owns every policy decision and recovery receipt.
- Meta glasses status updates are first-class receipts in the launch-slice
  replay, so terminal state can be compared directly with phone and Swissknife
  render receipts.
