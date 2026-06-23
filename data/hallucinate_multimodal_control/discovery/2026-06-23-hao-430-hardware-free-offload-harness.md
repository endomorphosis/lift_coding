# HAO-430 Hardware-Free Multimodal Offload Harness

This discovery artifact defines a deterministic hardware-free multimodal
offload harness for the Hallucinate App virtual desktop session. No physical
phone, desktop, Swissknife browser, or Meta glasses device is required. The
fixture simulates phone input, desktop peer offload, Swissknife operator UI, and
Meta glasses terminal output using stable participant IDs, a fixed clock, a
scripted peer timeout, and receipt IDs copied from one phase to the next.

The harness proves routing, mediation, receipts, and recovery by replaying this
chain:

`phone_event -> mediation_receipt -> virtual_desktop_command_intent -> peer_offload_policy_receipt -> runtime_receipt -> peer_offload_recovery_receipt -> render_receipt`.

The replay is intentionally narrow: one phone-originated command asks to open
the model monitor on the virtual desktop, the mediator allows it, the preferred
desktop peer times out, Hallucinate App selects the Swissknife UI fallback, and
the phone UI, Swissknife operator UI, and Meta glasses terminal all render the
same receipt-backed recovery state.

## Deterministic Harness Fixture

```json
{
  "task_id": "HAO-430",
  "harness_id": "hardware_free_multimodal_offload_harness",
  "requires_physical_devices": false,
  "determinism": {
    "clock": "fixed",
    "timestamp": "2026-06-23T00:00:00Z",
    "network": "simulated",
    "random_seed": "hao-430-fixed-replay"
  },
  "participants": {
    "phone:operator": "simulated_phone_input",
    "desktop:peer": "simulated_desktop_peer_offload",
    "swissknife:ui": "simulated_operator_ui",
    "meta_glasses:terminal": "simulated_terminal_output"
  },
  "replay_steps": [
    {
      "phase": "phone_event",
      "event": {
        "interaction_id": "evt_hao430_open_monitor",
        "surface": "voice",
        "surface_event": "utterance",
        "raw_payload": {
          "transcript": "open the model monitor on my desktop",
          "transport_correlation_id": "hao430-mobile-001"
        },
        "normalized_intent": {
          "intent": "desktop.open_widget",
          "method": "open_widget",
          "target_ref": "widget:model-monitor",
          "arguments": {
            "source": "phone"
          },
          "confidence": 0.93
        },
        "actor": {
          "type": "user",
          "id": "operator",
          "delegation_chain": []
        },
        "context": {
          "platform": "mobile",
          "device_context": {
            "remote_surface": "mobile-shell"
          }
        },
        "session": {
          "session_id": "vdsk_hao430_fixture",
          "participant_id": "phone:operator",
          "desktop_ref": "swissknife:desktop:primary",
          "sequence": 1,
          "parent_receipt_ids": [
            "rcpt_session_hao430_join"
          ]
        }
      }
    },
    {
      "phase": "mediation",
      "receipt": {
        "receipt_id": "rcpt_policy_hao430_open_monitor",
        "receipt_contract_ref": "mediation_receipt@0.1.0",
        "interaction_id": "evt_hao430_open_monitor",
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
      "command": {
        "command_intent_id": "cmd_hao430_open_monitor",
        "interaction_id": "evt_hao430_open_monitor",
        "session_id": "vdsk_hao430_fixture",
        "intent": "desktop.open_widget",
        "method": "open_widget",
        "target_ref": "widget:model-monitor",
        "issued_to": "desktop:peer",
        "placement_hint": {
          "placement_id": "place_hao430_model_monitor",
          "preferred_surface": "desktop:peer",
          "fallback_surfaces": [
            "swissknife:ui",
            "phone:operator",
            "meta_glasses:terminal"
          ],
          "display_region": "right_panel",
          "attention": "foreground",
          "privacy": "operator_visible",
          "constraints": [
            "avoid_glasses_full_text",
            "desktop_peer_if_available"
          ]
        },
        "receipt_ids": {
          "event_receipt_id": "rcpt_evt_hao430_open_monitor",
          "policy_receipt_id": "rcpt_policy_hao430_open_monitor",
          "command_receipt_id": "rcpt_cmd_hao430_open_monitor"
        }
      }
    },
    {
      "phase": "peer_offload_selection",
      "receipt": {
        "receipt_id": "rcpt_offload_hao430_open_monitor",
        "receipt_contract_ref": "peer_offload_policy_receipt@0.1.0",
        "session_id": "vdsk_hao430_fixture",
        "interaction_id": "evt_hao430_open_monitor",
        "policy_receipt_id": "rcpt_policy_hao430_open_monitor",
        "command_receipt_id": "rcpt_cmd_hao430_open_monitor",
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
          "max_attempts": 1,
          "attempt": 1,
          "remaining_attempts": 0
        },
        "render_targets": [
          "phone:operator",
          "swissknife:ui",
          "meta_glasses:terminal"
        ]
      }
    },
    {
      "phase": "desktop_peer_timeout",
      "runtime_receipt": {
        "receipt_id": "rcpt_runtime_hao430_peer_timeout",
        "peer_offload_policy_receipt_id": "rcpt_offload_hao430_open_monitor",
        "runtime_status": "timeout",
        "failed_peer_id": "desktop:peer",
        "timeout_ms": 2500
      }
    },
    {
      "phase": "recovery",
      "receipt": {
        "receipt_id": "rcpt_recovery_hao430_fallback",
        "receipt_contract_ref": "peer_offload_recovery_receipt@0.1.0",
        "session_id": "vdsk_hao430_fixture",
        "interaction_id": "evt_hao430_open_monitor",
        "policy_receipt_id": "rcpt_policy_hao430_open_monitor",
        "command_receipt_id": "rcpt_cmd_hao430_open_monitor",
        "peer_offload_policy_receipt_id": "rcpt_offload_hao430_open_monitor",
        "runtime_receipt_id": "rcpt_runtime_hao430_peer_timeout",
        "recovery_outcome": "timeout",
        "recovery_state": "fallback_selected",
        "last_good_receipt_id": "rcpt_offload_hao430_open_monitor",
        "selected_peer": {
          "participant_id": "swissknife:ui",
          "runtime_ref": "local_orb:simulated-swissknife",
          "selection_reason": "desktop peer timed out and retry budget exhausted"
        }
      }
    },
    {
      "phase": "surface_render",
      "render_receipts": [
        {
          "receipt_id": "rcpt_render_hao430_phone",
          "participant_id": "phone:operator",
          "source_recovery_receipt_id": "rcpt_recovery_hao430_fallback",
          "state": "fallback_selected",
          "summary": "Desktop peer timed out; opened model monitor in Swissknife UI."
        },
        {
          "receipt_id": "rcpt_render_hao430_swissknife",
          "participant_id": "swissknife:ui",
          "source_recovery_receipt_id": "rcpt_recovery_hao430_fallback",
          "state": "fallback_selected",
          "summary": "Model monitor opened from mediated fallback."
        },
        {
          "receipt_id": "rcpt_render_hao430_glasses",
          "participant_id": "meta_glasses:terminal",
          "source_recovery_receipt_id": "rcpt_recovery_hao430_fallback",
          "state": "fallback_selected",
          "summary": "Fallback selected; monitor available in Swissknife."
        }
      ]
    }
  ],
  "assertions": [
    "all ingress events enter mediation before dispatch",
    "desktop peer execution never starts without policy_receipt_id",
    "all user-visible surfaces render the same recovery_state",
    "receipt chain is stable across retry or fallback"
  ]
}
```

## Replay Notes

- The phone simulator owns only the raw event and participant context. It cannot
  select a peer or execute the command.
- The mediator is the first component allowed to emit policy and command
  receipts.
- The desktop peer simulator reports transport/runtime failure only; it does not
  choose the fallback state.
- The Swissknife UI and Meta glasses terminal simulators render from the same
  `peer_offload_recovery_receipt`, so labels may differ but receipt IDs and
  recovery semantics remain identical.
