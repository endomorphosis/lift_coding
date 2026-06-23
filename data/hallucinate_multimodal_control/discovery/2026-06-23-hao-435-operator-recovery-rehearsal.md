# HAO-435 Operator Recovery Rehearsal

HAO-435 defines the hardware-free operator recovery rehearsal for desktop peer
offload failure before physical-device launch validation. The rehearsal extends
the HAO-434 shared evidence packet and proves that phone UI, Swissknife UI, and
Meta glasses all render the same Hallucinate App recovery state and receipt
chain for timeout, denial, retry exhaustion, user cancellation, and
fallback-to-phone outcomes.

## Rehearsal Fixture

```json
{
  "task_id": "HAO-435",
  "artifact_id": "operator_recovery_rehearsal_desktop_peer_offload_failure",
  "source_evidence_packet": "data/hallucinate_multimodal_control/discovery/2026-06-23-hao-434-vai-mgw-shared-evidence-packet.md",
  "requires_physical_devices": false,
  "participants": {
    "phone:operator": "simulated_phone_ui",
    "desktop:peer": "simulated_desktop_peer_offload",
    "swissknife:ui": "simulated_swissknife_operator_ui",
    "meta_glasses:terminal": "simulated_meta_glasses_status_terminal"
  },
  "correlation_ids": {
    "session_id": "vdsk_hao432_launch_slice",
    "command_correlation_id": "cmdcorr_hao434_open_monitor",
    "policy_correlation_id": "polcorr_hao434_open_monitor",
    "placement_correlation_id": "placecorr_hao434_desktop_peer"
  },
  "common_receipt_parents": {
    "mediation_receipt_id": "rcpt_policy_hao432_open_monitor",
    "command_intent_receipt_id": "rcpt_cmd_hao432_open_monitor",
    "peer_offload_policy_receipt_id": "rcpt_offload_hao432_open_monitor"
  },
  "receipt_chain_template": [
    "mediation_receipt_id",
    "command_intent_receipt_id",
    "peer_offload_policy_receipt_id",
    "recovery_receipt_id",
    "render_receipt_ids.phone:operator",
    "render_receipt_ids.swissknife:ui",
    "render_receipt_ids.meta_glasses:terminal"
  ],
  "drills": [
    {
      "drill_id": "desktop_peer_timeout",
      "offload_failure": "desktop peer runtime timeout before first response",
      "injected_runtime_receipt_id": "rcpt_runtime_hao435_peer_timeout",
      "operator_console_error_recovery": {
        "recovery_id": "rec_hao435_timeout_retry",
        "failure_class": "desktop_peer_timeout",
        "failed_route_id": "route_hao435_desktop_peer",
        "last_good_receipt_id": "rcpt_offload_hao432_open_monitor",
        "retry_budget": {
          "max_attempts": 2,
          "attempt": 1,
          "remaining_attempts": 1
        },
        "fallback_surface": null,
        "operator_action_required": false,
        "recovery_receipt_id": "rcpt_recovery_hao435_timeout_retry",
        "recovery_state": "retry_scheduled"
      },
      "render_receipt_ids": {
        "phone:operator": "rcpt_render_hao435_timeout_phone",
        "swissknife:ui": "rcpt_render_hao435_timeout_swissknife",
        "meta_glasses:terminal": "rcpt_render_hao435_timeout_glasses"
      }
    },
    {
      "drill_id": "desktop_peer_denial",
      "offload_failure": "desktop peer route denied by policy or stale readiness proof",
      "injected_runtime_receipt_id": null,
      "operator_console_error_recovery": {
        "recovery_id": "rec_hao435_desktop_peer_denial",
        "failure_class": "desktop_peer_denial",
        "failed_route_id": "route_hao435_desktop_peer",
        "last_good_receipt_id": "rcpt_policy_hao432_open_monitor",
        "retry_budget": {
          "max_attempts": 0,
          "attempt": 0,
          "remaining_attempts": 0
        },
        "fallback_surface": null,
        "operator_action_required": true,
        "recovery_receipt_id": "rcpt_recovery_hao435_denied",
        "recovery_state": "denied"
      },
      "render_receipt_ids": {
        "phone:operator": "rcpt_render_hao435_denied_phone",
        "swissknife:ui": "rcpt_render_hao435_denied_swissknife",
        "meta_glasses:terminal": "rcpt_render_hao435_denied_glasses"
      }
    },
    {
      "drill_id": "retry_exhaustion",
      "offload_failure": "desktop peer retry budget exhausted after final timeout",
      "injected_runtime_receipt_id": "rcpt_runtime_hao435_peer_timeout_final",
      "operator_console_error_recovery": {
        "recovery_id": "rec_hao435_retry_exhausted",
        "failure_class": "retry_exhaustion",
        "failed_route_id": "route_hao435_desktop_peer",
        "last_good_receipt_id": "rcpt_recovery_hao435_timeout_retry",
        "retry_budget": {
          "max_attempts": 2,
          "attempt": 2,
          "remaining_attempts": 0
        },
        "fallback_surface": "swissknife:ui",
        "operator_action_required": false,
        "recovery_receipt_id": "rcpt_recovery_hao435_retry_exhausted",
        "recovery_state": "fallback_selected"
      },
      "render_receipt_ids": {
        "phone:operator": "rcpt_render_hao435_retry_exhausted_phone",
        "swissknife:ui": "rcpt_render_hao435_retry_exhausted_swissknife",
        "meta_glasses:terminal": "rcpt_render_hao435_retry_exhausted_glasses"
      }
    },
    {
      "drill_id": "user_cancellation",
      "offload_failure": "operator cancellation while desktop peer recovery is pending",
      "cancel_source_participant_id": "phone:operator",
      "injected_runtime_receipt_id": null,
      "operator_console_error_recovery": {
        "recovery_id": "rec_hao435_user_cancelled",
        "failure_class": "user_cancellation",
        "failed_route_id": "route_hao435_desktop_peer",
        "last_good_receipt_id": "rcpt_recovery_hao435_retry_exhausted",
        "retry_budget": {
          "max_attempts": 2,
          "attempt": 2,
          "remaining_attempts": 0
        },
        "fallback_surface": null,
        "operator_action_required": false,
        "recovery_receipt_id": "rcpt_recovery_hao435_cancelled",
        "recovery_state": "cancelled"
      },
      "render_receipt_ids": {
        "phone:operator": "rcpt_render_hao435_cancelled_phone",
        "swissknife:ui": "rcpt_render_hao435_cancelled_swissknife",
        "meta_glasses:terminal": "rcpt_render_hao435_cancelled_glasses"
      }
    },
    {
      "drill_id": "fallback_to_phone",
      "offload_failure": "desktop peer and Swissknife fallback unavailable; phone is selected as safest local surface",
      "injected_runtime_receipt_id": "rcpt_runtime_hao435_peer_and_swissknife_unavailable",
      "operator_console_error_recovery": {
        "recovery_id": "rec_hao435_fallback_to_phone",
        "failure_class": "fallback_to_phone",
        "failed_route_id": "route_hao435_desktop_peer",
        "last_good_receipt_id": "rcpt_recovery_hao435_retry_exhausted",
        "retry_budget": {
          "max_attempts": 2,
          "attempt": 2,
          "remaining_attempts": 0
        },
        "fallback_surface": "phone:operator",
        "operator_action_required": true,
        "recovery_receipt_id": "rcpt_recovery_hao435_fallback_phone",
        "recovery_state": "fallback_to_phone"
      },
      "render_receipt_ids": {
        "phone:operator": "rcpt_render_hao435_fallback_phone_phone",
        "swissknife:ui": "rcpt_render_hao435_fallback_phone_swissknife",
        "meta_glasses:terminal": "rcpt_render_hao435_fallback_phone_glasses"
      }
    }
  ],
  "surface_parity_requirements": {
    "render_participants": [
      "phone:operator",
      "swissknife:ui",
      "meta_glasses:terminal"
    ],
    "matching_fields": [
      "session_id",
      "command_correlation_id",
      "policy_correlation_id",
      "placement_correlation_id",
      "source_recovery_receipt_id",
      "recovery_state",
      "fallback_surface",
      "last_good_receipt_id"
    ],
    "meta_glasses_limit": "Meta glasses render status and receipt aliases only; they do not retry, cancel, or dispatch the desktop peer command."
  },
  "assertions": [
    "operator recovery rehearsal covers desktop peer timeout, denial, retry exhaustion, user cancellation, and fallback-to-phone outcomes",
    "every offload failure outcome emits a Hallucinate App recovery receipt before any phone, Swissknife, or Meta glasses render receipt",
    "phone UI, Swissknife UI, and Meta glasses render the same recovery_state and source_recovery_receipt_id for each drill",
    "desktop peer, phone, Swissknife, and Meta glasses adapters cannot invent local recovery state without the shared receipt chain",
    "fallback-to-phone keeps the desktop peer uninvoked after the recovery receipt selects phone:operator"
  ]
}
```

## Rehearsal Notes

- The rehearsal uses the HAO-434 shared correlation IDs and parent receipts so
  VAI and MGW launch replay consumers see the same recovery proof chain.
- Denial stops before desktop peer dispatch; its receipt chain therefore ends
  at the last good mediation receipt plus the denied recovery receipt.
- Retry exhaustion and fallback-to-phone are separate outcomes: retry
  exhaustion may choose Swissknife, while fallback-to-phone proves the phone UI
  can become the selected recovery surface when desktop peer and Swissknife are
  unavailable.
- Meta glasses receive the same recovery receipt IDs as phone and Swissknife,
  but their role is display-only status rendering.
