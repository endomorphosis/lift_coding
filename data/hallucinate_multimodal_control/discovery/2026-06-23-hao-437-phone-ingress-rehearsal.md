# HAO-437 Physical Phone Ingress Rehearsal Receipt

Task: HAO-437
Goal id: VAIOS-G697
Track: launch
Missing evidence closed: physical phone ingress rehearsal receipt

This is the HAO-437 real phone ingress rehearsal packet for the VAIOS-G697
launch readiness split.

The packet proves that a real phone-originated UI event enters Hallucinate App
as an `interaction_envelope`, preserves the phone session and correlation IDs,
and cannot dispatch to `phone_local` or `desktop:peer` before Hallucinate App
emits both `mediation_receipt` and `policy_receipt_id`. It also records the
fail-closed recovery receipt used when the physical phone adapter is absent.

## Real Phone Ingress Rehearsal Fixture

```json
{
  "task_id": "HAO-437",
  "artifact_id": "real_phone_ingress_rehearsal_receipt",
  "goal_id": "VAIOS-G697",
  "requires_physical_devices": true,
  "physical_device": {
    "participant_id": "phone:operator",
    "adapter_ref": "physical_phone_adapter:primary",
    "transport": "usb_or_lan_pairing",
    "event_source": "real_phone_ui",
    "adapter_absent_recovery": "fail_closed"
  },
  "determinism": {
    "clock": "fixed",
    "timestamp": "2026-06-23T00:01:00Z",
    "network": "operator_lan",
    "random_seed": "hao-437-phone-ingress"
  },
  "stable_ids": {
    "session_id": "vdsk_hao437_real_phone_ingress",
    "correlation_id": "corr_hao437_phone_open_monitor",
    "request_id": "req_hao437_phone_open_monitor",
    "interaction_id": "evt_hao437_phone_open_monitor",
    "event_receipt_id": "rcpt_evt_hao437_phone_open_monitor",
    "policy_receipt_id": "rcpt_policy_hao437_phone_open_monitor",
    "command_intent_id": "cmd_hao437_phone_open_monitor",
    "command_receipt_id": "rcpt_cmd_hao437_phone_open_monitor",
    "placement_id": "place_hao437_phone_model_monitor",
    "adapter_absent_receipt_id": "rcpt_absent_hao437_phone_adapter"
  },
  "participants": {
    "phone:operator": "physical_phone_operator_input",
    "hallucinate_app:mediator": "policy_and_receipt_authority",
    "desktop:peer": "runtime_target_blocked_until_policy",
    "phone_local": "runtime_target_blocked_until_policy"
  },
  "receipt_chain": [
    "physical_phone_adapter_receipt",
    "interaction_envelope",
    "mediation_receipt",
    "virtual_desktop_command_intent",
    "dispatch_gate_receipt",
    "adapter_absent_recovery_receipt"
  ],
  "replay_steps": [
    {
      "phase": "physical_phone_event",
      "timestamp": "2026-06-23T00:01:00Z",
      "adapter_receipt": {
        "receipt_id": "rcpt_adapter_hao437_phone_event",
        "participant_id": "phone:operator",
        "adapter_ref": "physical_phone_adapter:primary",
        "adapter_status": "attached",
        "session_id": "vdsk_hao437_real_phone_ingress",
        "correlation_id": "corr_hao437_phone_open_monitor",
        "request_id": "req_hao437_phone_open_monitor",
        "transport_authenticated": true,
        "raw_event_class": "phone_ui_event"
      }
    },
    {
      "phase": "interaction_envelope",
      "timestamp": "2026-06-23T00:01:01Z",
      "interaction_envelope": {
        "interaction_id": "evt_hao437_phone_open_monitor",
        "session_id": "vdsk_hao437_real_phone_ingress",
        "correlation_id": "corr_hao437_phone_open_monitor",
        "request_id": "req_hao437_phone_open_monitor",
        "surface": "phone",
        "surface_event": "tap",
        "source_event_class": "phone_ui_event",
        "participant_id": "phone:operator",
        "raw_payload": {
          "control_id": "open-model-monitor",
          "physical_adapter_receipt_id": "rcpt_adapter_hao437_phone_event"
        },
        "normalized_intent": {
          "intent": "desktop.open_widget",
          "method": "open_widget",
          "target_ref": "widget:model-monitor",
          "arguments": {
            "source": "real_phone_ingress"
          },
          "confidence": 1.0
        }
      }
    },
    {
      "phase": "mediation",
      "timestamp": "2026-06-23T00:01:02Z",
      "receipt": {
        "receipt_id": "rcpt_policy_hao437_phone_open_monitor",
        "receipt_contract_ref": "mediation_receipt@0.1.0",
        "interaction_id": "evt_hao437_phone_open_monitor",
        "session_id": "vdsk_hao437_real_phone_ingress",
        "correlation_id": "corr_hao437_phone_open_monitor",
        "request_id": "req_hao437_phone_open_monitor",
        "policy_receipt_id": "rcpt_policy_hao437_phone_open_monitor",
        "policy_decision": "allow",
        "source_participant_id": "phone:operator",
        "interaction_envelope_ref": "evt_hao437_phone_open_monitor"
      }
    },
    {
      "phase": "command_intent",
      "timestamp": "2026-06-23T00:01:03Z",
      "command": {
        "command_intent_id": "cmd_hao437_phone_open_monitor",
        "interaction_id": "evt_hao437_phone_open_monitor",
        "session_id": "vdsk_hao437_real_phone_ingress",
        "correlation_id": "corr_hao437_phone_open_monitor",
        "request_id": "req_hao437_phone_open_monitor",
        "intent": "desktop.open_widget",
        "method": "open_widget",
        "target_ref": "widget:model-monitor",
        "eligible_runtimes": [
          "desktop:peer",
          "phone_local"
        ],
        "receipt_ids": {
          "event_receipt_id": "rcpt_evt_hao437_phone_open_monitor",
          "mediation_receipt_id": "rcpt_policy_hao437_phone_open_monitor",
          "policy_receipt_id": "rcpt_policy_hao437_phone_open_monitor",
          "command_receipt_id": "rcpt_cmd_hao437_phone_open_monitor"
        },
        "placement_hint": {
          "placement_id": "place_hao437_phone_model_monitor",
          "preferred_surface": "desktop:peer",
          "fallback_runtime": "phone_local"
        }
      }
    },
    {
      "phase": "dispatch_gate",
      "timestamp": "2026-06-23T00:01:04Z",
      "receipt": {
        "receipt_id": "rcpt_dispatch_gate_hao437",
        "session_id": "vdsk_hao437_real_phone_ingress",
        "correlation_id": "corr_hao437_phone_open_monitor",
        "request_id": "req_hao437_phone_open_monitor",
        "command_intent_id": "cmd_hao437_phone_open_monitor",
        "policy_receipt_id": "rcpt_policy_hao437_phone_open_monitor",
        "mediation_receipt_id": "rcpt_policy_hao437_phone_open_monitor",
        "runtime_dispatch_blocked_before_policy": true,
        "blocked_runtimes_before_policy": [
          "desktop:peer",
          "phone_local"
        ],
        "dispatch_allowed_after_receipts": [
          "mediation_receipt",
          "policy_receipt_id"
        ]
      }
    },
    {
      "phase": "adapter_absent_recovery",
      "timestamp": "2026-06-23T00:01:05Z",
      "receipt": {
        "receipt_id": "rcpt_absent_hao437_phone_adapter",
        "receipt_contract_ref": "physical_adapter_recovery_receipt@0.1.0",
        "participant_id": "phone:operator",
        "adapter_ref": "physical_phone_adapter:primary",
        "adapter_status": "absent",
        "session_id": "vdsk_hao437_real_phone_ingress",
        "correlation_id": "corr_hao437_phone_open_monitor",
        "request_id": "req_hao437_phone_open_monitor",
        "recovery_state": "fail_closed",
        "policy_decision": "deny",
        "policy_receipt_id": null,
        "dispatch_allowed": false,
        "blocked_runtimes": [
          "desktop:peer",
          "phone_local"
        ],
        "operator_message": "Physical phone adapter absent; no runtime dispatch occurred."
      }
    }
  ],
  "assertions": [
    "real phone ingress enters Hallucinate App as interaction_envelope",
    "phone:operator session_id, correlation_id, and request_id are preserved across mediation and command intent",
    "desktop:peer and phone_local dispatch are blocked until mediation_receipt and policy_receipt_id exist",
    "physical adapter absence records fail-closed recovery with no local or desktop runtime dispatch"
  ]
}
```

## Review Notes

- The attached-adapter path is a physical-device rehearsal receipt, so
  `requires_physical_devices` is true.
- `phone:operator` supplies input only. Hallucinate App remains the policy and
  receipt authority for `mediation_receipt`, `policy_receipt_id`, command
  intent, placement, and dispatch gating.
- The absent-adapter path is intentionally fail-closed: it has no
  `policy_receipt_id`, marks `dispatch_allowed: false`, and blocks both
  `desktop:peer` and `phone_local`.
