# HAO-439 Meta Glasses Terminal Receipt

Task: HAO-439
Goal id: VAIOS-G697
Track: launch
Missing evidence closed: Meta glasses terminal receipt capture

This is the HAO-439 Meta glasses terminal receipt for the VAIOS-G697 launch
readiness split.

The receipt proves that Meta glasses `display_action` events and confirmations
enter Hallucinate App through the existing HAO-431 bridge, become normalized
Hallucinate App intents, preserve `meta_glasses:terminal` participant identity,
render the selected peer and recovery state, and fail closed when pairing or
display evidence is stale.

## Meta Glasses Terminal Receipt Fixture

```json
{
  "task_id": "HAO-439",
  "artifact_id": "meta_glasses_terminal_receipt",
  "goal_id": "VAIOS-G697",
  "requires_physical_devices": false,
  "bridge_contract": {
    "source_task": "HAO-431",
    "bridge_ref": "meta_glasses_display_widget_intent_bridge",
    "single_command_contract": true,
    "display_action_field": "raw_payload.display_action",
    "normalized_intent_authority": "hallucinate_app:mediator"
  },
  "determinism": {
    "clock": "fixed",
    "timestamp": "2026-06-23T00:03:00Z",
    "network": "simulated",
    "random_seed": "hao-439-meta-glasses-terminal"
  },
  "stable_ids": {
    "session_id": "vdsk_hao439_meta_glasses_terminal",
    "pairing_receipt_id": "rcpt_pair_hao439_glasses_terminal",
    "display_action_receipt_id": "rcpt_display_action_hao439_activate",
    "confirmation_receipt_id": "rcpt_confirm_hao439_activate",
    "interaction_id": "evt_hao439_activate_monitor",
    "event_receipt_id": "rcpt_evt_hao439_activate_monitor",
    "policy_receipt_id": "rcpt_policy_hao439_activate_monitor",
    "command_intent_id": "cmd_hao439_activate_monitor",
    "command_receipt_id": "rcpt_cmd_hao439_activate_monitor",
    "placement_id": "place_hao439_terminal_model_monitor",
    "peer_offload_policy_receipt_id": "rcpt_offload_hao439_activate_monitor",
    "stale_evidence_receipt_id": "rcpt_stale_hao439_glasses_terminal"
  },
  "participants": {
    "meta_glasses:terminal": "simulated_meta_glasses_display_action_source",
    "hallucinate_app:mediator": "hao431_bridge_policy_and_receipt_authority",
    "desktop:peer": "selected_peer_render_target",
    "phone_local": "fail_closed_runtime_blocked"
  },
  "receipt_chain": [
    "pairing_receipt",
    "display_action_receipt",
    "confirmation_receipt",
    "interaction_envelope",
    "mediation_receipt",
    "virtual_desktop_command_intent",
    "peer_offload_policy_receipt",
    "terminal_render_receipt",
    "stale_evidence_recovery_receipt"
  ],
  "replay_steps": [
    {
      "phase": "pairing_receipt",
      "timestamp": "2026-06-23T00:03:00Z",
      "pairing_receipt": {
        "receipt_id": "rcpt_pair_hao439_glasses_terminal",
        "participant_id": "meta_glasses:terminal",
        "session_id": "vdsk_hao439_meta_glasses_terminal",
        "adapter_ref": "meta_glasses_terminal_adapter:simulated",
        "pairing_state": "active",
        "display_evidence_state": "fresh",
        "expires_at": "2026-06-23T00:08:00Z",
        "authenticated_transport": true
      }
    },
    {
      "phase": "display_action",
      "timestamp": "2026-06-23T00:03:01Z",
      "display_action_receipt": {
        "receipt_id": "rcpt_display_action_hao439_activate",
        "participant_id": "meta_glasses:terminal",
        "session_id": "vdsk_hao439_meta_glasses_terminal",
        "event_type": "display_action",
        "bridge_ref": "meta_glasses_display_widget_intent_bridge",
        "pairing_receipt_id": "rcpt_pair_hao439_glasses_terminal",
        "display_evidence_receipt_id": "rcpt_render_hao432_glasses",
        "raw_payload": {
          "display_action": {
            "widget_id": "widget:model-monitor",
            "card_id": "card:model-monitor-summary",
            "action_id": "activate-open-monitor",
            "action_type": "activateDisplayWidgetAction",
            "selected_peer": "desktop:peer",
            "orb_receipt_cid": "rcpt_render_hao432_glasses"
          }
        }
      }
    },
    {
      "phase": "terminal_confirmation",
      "timestamp": "2026-06-23T00:03:02Z",
      "confirmation_receipt": {
        "receipt_id": "rcpt_confirm_hao439_activate",
        "participant_id": "meta_glasses:terminal",
        "session_id": "vdsk_hao439_meta_glasses_terminal",
        "surface": "gesture",
        "surface_event": "tap",
        "confirmation": "confirm",
        "display_action_receipt_id": "rcpt_display_action_hao439_activate",
        "pairing_receipt_id": "rcpt_pair_hao439_glasses_terminal"
      }
    },
    {
      "phase": "interaction_envelope",
      "timestamp": "2026-06-23T00:03:03Z",
      "interaction_envelope": {
        "interaction_id": "evt_hao439_activate_monitor",
        "session_id": "vdsk_hao439_meta_glasses_terminal",
        "participant_id": "meta_glasses:terminal",
        "surface": "gesture",
        "surface_event": "tap",
        "source_event_class": "meta_glasses_display_action",
        "bridge_ref": "meta_glasses_display_widget_intent_bridge",
        "raw_payload": {
          "display_action": {
            "widget_id": "widget:model-monitor",
            "card_id": "card:model-monitor-summary",
            "action_id": "activate-open-monitor",
            "action_type": "activateDisplayWidgetAction",
            "selected_peer": "desktop:peer",
            "orb_receipt_cid": "rcpt_render_hao432_glasses"
          },
          "display_action_receipt_id": "rcpt_display_action_hao439_activate",
          "confirmation_receipt_id": "rcpt_confirm_hao439_activate",
          "pairing_receipt_id": "rcpt_pair_hao439_glasses_terminal"
        },
        "normalized_intent": {
          "intent": "terminal.activate_action",
          "method": "activate_action",
          "target_ref": "widget:model-monitor#activate-open-monitor",
          "arguments": {
            "selected_peer": "desktop:peer",
            "display_action_receipt_id": "rcpt_display_action_hao439_activate",
            "confirmation_receipt_id": "rcpt_confirm_hao439_activate",
            "bridge_ref": "meta_glasses_display_widget_intent_bridge"
          },
          "confidence": 1.0
        }
      }
    },
    {
      "phase": "mediation",
      "timestamp": "2026-06-23T00:03:04Z",
      "receipt": {
        "receipt_id": "rcpt_policy_hao439_activate_monitor",
        "receipt_contract_ref": "mediation_receipt@0.1.0",
        "interaction_id": "evt_hao439_activate_monitor",
        "session_id": "vdsk_hao439_meta_glasses_terminal",
        "source_participant_id": "meta_glasses:terminal",
        "policy_decision": "allow",
        "policy_reason": "fresh_pairing_and_display_evidence",
        "normalized_intent": "terminal.activate_action",
        "display_action_receipt_id": "rcpt_display_action_hao439_activate",
        "confirmation_receipt_id": "rcpt_confirm_hao439_activate",
        "render_targets": [
          "meta_glasses:terminal",
          "phone:operator"
        ]
      }
    },
    {
      "phase": "command_intent",
      "timestamp": "2026-06-23T00:03:05Z",
      "command": {
        "command_intent_id": "cmd_hao439_activate_monitor",
        "interaction_id": "evt_hao439_activate_monitor",
        "session_id": "vdsk_hao439_meta_glasses_terminal",
        "intent": "terminal.activate_action",
        "method": "activate_action",
        "target_ref": "widget:model-monitor#activate-open-monitor",
        "issued_to": "meta_glasses:terminal",
        "mapped_desktop_intent": "desktop.open_widget",
        "placement_hint": {
          "placement_id": "place_hao439_terminal_model_monitor",
          "selected_peer": "desktop:peer",
          "preferred_surface": "desktop:peer",
          "fallback_runtime": "phone_local",
          "display_region": "right_panel",
          "attention": "foreground"
        },
        "receipt_ids": {
          "event_receipt_id": "rcpt_evt_hao439_activate_monitor",
          "policy_receipt_id": "rcpt_policy_hao439_activate_monitor",
          "command_receipt_id": "rcpt_cmd_hao439_activate_monitor",
          "display_action_receipt_id": "rcpt_display_action_hao439_activate"
        }
      }
    },
    {
      "phase": "peer_offload_selection",
      "timestamp": "2026-06-23T00:03:06Z",
      "receipt": {
        "receipt_id": "rcpt_offload_hao439_activate_monitor",
        "receipt_contract_ref": "peer_offload_policy_receipt@0.1.0",
        "session_id": "vdsk_hao439_meta_glasses_terminal",
        "interaction_id": "evt_hao439_activate_monitor",
        "command_intent_id": "cmd_hao439_activate_monitor",
        "policy_receipt_id": "rcpt_policy_hao439_activate_monitor",
        "command_receipt_id": "rcpt_cmd_hao439_activate_monitor",
        "placement_id": "place_hao439_terminal_model_monitor",
        "display_action_receipt_id": "rcpt_display_action_hao439_activate",
        "selected_peer": {
          "participant_id": "desktop:peer",
          "runtime_ref": "peer_orb:simulated-desktop-primary",
          "selection_reason": "display action requested desktop peer and policy allowed"
        },
        "recovery_state": "running_on_peer",
        "render_targets": [
          "meta_glasses:terminal",
          "phone:operator"
        ]
      }
    },
    {
      "phase": "terminal_render",
      "timestamp": "2026-06-23T00:03:07Z",
      "render_receipts": [
        {
          "receipt_id": "rcpt_render_hao439_glasses_selected_peer",
          "participant_id": "meta_glasses:terminal",
          "source_policy_receipt_id": "rcpt_policy_hao439_activate_monitor",
          "source_offload_receipt_id": "rcpt_offload_hao439_activate_monitor",
          "selected_peer": "desktop:peer",
          "state": "running_on_peer",
          "summary": "Model monitor opened on desktop:peer."
        },
        {
          "receipt_id": "rcpt_render_hao439_phone_selected_peer",
          "participant_id": "phone:operator",
          "source_policy_receipt_id": "rcpt_policy_hao439_activate_monitor",
          "source_offload_receipt_id": "rcpt_offload_hao439_activate_monitor",
          "selected_peer": "desktop:peer",
          "state": "running_on_peer",
          "summary": "Meta glasses action selected desktop:peer."
        }
      ]
    },
    {
      "phase": "stale_evidence_recovery",
      "timestamp": "2026-06-23T00:09:01Z",
      "receipt": {
        "receipt_id": "rcpt_stale_hao439_glasses_terminal",
        "receipt_contract_ref": "terminal_display_evidence_recovery_receipt@0.1.0",
        "participant_id": "meta_glasses:terminal",
        "session_id": "vdsk_hao439_meta_glasses_terminal",
        "pairing_receipt_id": "rcpt_pair_hao439_glasses_terminal",
        "display_action_receipt_id": "rcpt_display_action_hao439_activate",
        "stale_pairing": true,
        "stale_display_evidence": true,
        "policy_decision": "deny",
        "policy_receipt_id": null,
        "dispatch_allowed": false,
        "blocked_intents": [
          "terminal.activate_action",
          "desktop.request_handoff",
          "desktop.open_widget"
        ],
        "recovery_state": "fail_closed",
        "selected_peer": null,
        "render_receipt": {
          "receipt_id": "rcpt_render_hao439_glasses_fail_closed",
          "participant_id": "meta_glasses:terminal",
          "state": "fail_closed",
          "selected_peer": null,
          "summary": "Pairing and display evidence are stale; no display action was dispatched."
        }
      }
    }
  ],
  "assertions": [
    "display_action and confirmation enter through the HAO-431 bridge",
    "raw_payload.display_action is preserved before normalized_intent is emitted",
    "normalized Hallucinate App intent is terminal.activate_action",
    "meta_glasses:terminal participant identity is preserved across pairing, action, confirmation, mediation, and render receipts",
    "terminal render receipts show selected_peer and recovery_state",
    "stale pairing or display evidence fails closed with no policy_receipt_id and no runtime dispatch"
  ]
}
```

## Review Notes

- This packet reuses HAO-431 as the only display-action bridge. The glasses
  terminal contributes `display_action` evidence and confirmation receipts, but
  Hallucinate App remains the normalized intent and policy authority.
- The allowed path renders `selected_peer: "desktop:peer"` and
  `state: "running_on_peer"` back to `meta_glasses:terminal`.
- The stale-evidence path is fail-closed: it denies the action, keeps
  `policy_receipt_id` null, sets `dispatch_allowed: false`, blocks
  `terminal.activate_action`, `desktop.request_handoff`, and
  `desktop.open_widget`, and renders the recovery state on the terminal.
