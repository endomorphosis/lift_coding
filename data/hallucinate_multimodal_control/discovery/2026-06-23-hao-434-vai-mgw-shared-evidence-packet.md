# HAO-434 VAI/MGW Shared Evidence Packet

HAO-434 connects the HAO-432 Hallucinate App launch replay receipt chain to the
shared evidence packet consumed by the VAI launch replay and the MGW
glasses-widget launch replay. The packet is intentionally hardware-free and
keeps Hallucinate App as the receipt authority: VAI and MGW consume the same
mediation, command-intent, peer-offload, recovery, and render receipt IDs
instead of minting parallel launch evidence.

## Shared Evidence Packet Fixture

```json
{
  "task_id": "HAO-434",
  "artifact_id": "vai_mgw_shared_launch_evidence_packet",
  "source_replay_artifact": "launch_slice_replay_receipts",
  "source_replay_path": "data/hallucinate_multimodal_control/discovery/2026-06-23-hao-432-launch-slice-replay-receipts.md",
  "consumed_by": [
    "virtual_ai_os.launch_replay",
    "meta_glasses_display_widgets.glasses_widget_launch_replay"
  ],
  "correlation_ids": {
    "session_id": "vdsk_hao432_launch_slice",
    "command_correlation_id": "cmdcorr_hao434_open_monitor",
    "policy_correlation_id": "polcorr_hao434_open_monitor",
    "placement_correlation_id": "placecorr_hao434_desktop_peer"
  },
  "emitted_receipt_ids": {
    "mediation_receipt_id": "rcpt_policy_hao432_open_monitor",
    "command_intent_receipt_id": "rcpt_cmd_hao432_open_monitor",
    "peer_offload_policy_receipt_id": "rcpt_offload_hao432_open_monitor",
    "recovery_receipt_ids": [
      "rcpt_recovery_hao432_retry",
      "rcpt_recovery_hao432_fallback",
      "rcpt_recovery_hao432_cancelled"
    ],
    "render_receipt_ids": {
      "phone:operator": "rcpt_render_hao432_phone",
      "swissknife:ui": "rcpt_render_hao432_swissknife",
      "meta_glasses:terminal": "rcpt_render_hao432_glasses"
    }
  },
  "hallucinate_app_emitted_receipts": [
    {
      "receipt_type": "mediation_receipt",
      "receipt_id": "rcpt_policy_hao432_open_monitor",
      "session_id": "vdsk_hao432_launch_slice",
      "command_correlation_id": "cmdcorr_hao434_open_monitor",
      "policy_correlation_id": "polcorr_hao434_open_monitor",
      "placement_correlation_id": "placecorr_hao434_desktop_peer"
    },
    {
      "receipt_type": "virtual_desktop_command_intent",
      "receipt_id": "rcpt_cmd_hao432_open_monitor",
      "session_id": "vdsk_hao432_launch_slice",
      "command_correlation_id": "cmdcorr_hao434_open_monitor",
      "policy_correlation_id": "polcorr_hao434_open_monitor",
      "placement_correlation_id": "placecorr_hao434_desktop_peer"
    },
    {
      "receipt_type": "peer_offload_policy_receipt",
      "receipt_id": "rcpt_offload_hao432_open_monitor",
      "session_id": "vdsk_hao432_launch_slice",
      "command_correlation_id": "cmdcorr_hao434_open_monitor",
      "policy_correlation_id": "polcorr_hao434_open_monitor",
      "placement_correlation_id": "placecorr_hao434_desktop_peer"
    },
    {
      "receipt_type": "peer_offload_recovery_receipt",
      "receipt_id": "rcpt_recovery_hao432_retry",
      "session_id": "vdsk_hao432_launch_slice",
      "command_correlation_id": "cmdcorr_hao434_open_monitor",
      "policy_correlation_id": "polcorr_hao434_open_monitor",
      "placement_correlation_id": "placecorr_hao434_desktop_peer"
    },
    {
      "receipt_type": "peer_offload_recovery_receipt",
      "receipt_id": "rcpt_recovery_hao432_fallback",
      "session_id": "vdsk_hao432_launch_slice",
      "command_correlation_id": "cmdcorr_hao434_open_monitor",
      "policy_correlation_id": "polcorr_hao434_open_monitor",
      "placement_correlation_id": "placecorr_hao434_desktop_peer"
    },
    {
      "receipt_type": "peer_offload_recovery_receipt",
      "receipt_id": "rcpt_recovery_hao432_cancelled",
      "session_id": "vdsk_hao432_launch_slice",
      "command_correlation_id": "cmdcorr_hao434_open_monitor",
      "policy_correlation_id": "polcorr_hao434_open_monitor",
      "placement_correlation_id": "placecorr_hao434_desktop_peer"
    },
    {
      "receipt_type": "render_receipt",
      "receipt_id": "rcpt_render_hao432_phone",
      "participant_id": "phone:operator",
      "session_id": "vdsk_hao432_launch_slice",
      "command_correlation_id": "cmdcorr_hao434_open_monitor",
      "policy_correlation_id": "polcorr_hao434_open_monitor",
      "placement_correlation_id": "placecorr_hao434_desktop_peer"
    },
    {
      "receipt_type": "render_receipt",
      "receipt_id": "rcpt_render_hao432_swissknife",
      "participant_id": "swissknife:ui",
      "session_id": "vdsk_hao432_launch_slice",
      "command_correlation_id": "cmdcorr_hao434_open_monitor",
      "policy_correlation_id": "polcorr_hao434_open_monitor",
      "placement_correlation_id": "placecorr_hao434_desktop_peer"
    },
    {
      "receipt_type": "render_receipt",
      "receipt_id": "rcpt_render_hao432_glasses",
      "participant_id": "meta_glasses:terminal",
      "session_id": "vdsk_hao432_launch_slice",
      "command_correlation_id": "cmdcorr_hao434_open_monitor",
      "policy_correlation_id": "polcorr_hao434_open_monitor",
      "placement_correlation_id": "placecorr_hao434_desktop_peer"
    }
  ],
  "vai_launch_replay": {
    "launch_replay_id": "vai-launch-replay-hao434",
    "session_id": "vdsk_hao432_launch_slice",
    "command_correlation_id": "cmdcorr_hao434_open_monitor",
    "policy_correlation_id": "polcorr_hao434_open_monitor",
    "placement_correlation_id": "placecorr_hao434_desktop_peer",
    "consumed_receipt_ids": {
      "mediation_receipt_id": "rcpt_policy_hao432_open_monitor",
      "command_intent_receipt_id": "rcpt_cmd_hao432_open_monitor",
      "peer_offload_policy_receipt_id": "rcpt_offload_hao432_open_monitor",
      "recovery_receipt_ids": [
        "rcpt_recovery_hao432_retry",
        "rcpt_recovery_hao432_fallback",
        "rcpt_recovery_hao432_cancelled"
      ],
      "render_receipt_ids": {
        "phone:operator": "rcpt_render_hao432_phone",
        "swissknife:ui": "rcpt_render_hao432_swissknife",
        "meta_glasses:terminal": "rcpt_render_hao432_glasses"
      }
    }
  },
  "mgw_glasses_widget_launch_replay": {
    "launch_replay_id": "mgw-glasses-widget-launch-replay-hao434",
    "session_id": "vdsk_hao432_launch_slice",
    "command_correlation_id": "cmdcorr_hao434_open_monitor",
    "policy_correlation_id": "polcorr_hao434_open_monitor",
    "placement_correlation_id": "placecorr_hao434_desktop_peer",
    "display_widget_action": {
      "widget_id": "virtual-desktop-session",
      "action_id": "render_cancelled_status",
      "correlation_id": "cmdcorr_hao434_open_monitor",
      "request_id": "vdsk_hao432_launch_slice",
      "orb_receipt_cid": "rcpt_render_hao432_glasses",
      "policy_receipt_cid": "rcpt_policy_hao432_open_monitor"
    },
    "consumed_receipt_ids": {
      "mediation_receipt_id": "rcpt_policy_hao432_open_monitor",
      "command_intent_receipt_id": "rcpt_cmd_hao432_open_monitor",
      "peer_offload_policy_receipt_id": "rcpt_offload_hao432_open_monitor",
      "recovery_receipt_ids": [
        "rcpt_recovery_hao432_retry",
        "rcpt_recovery_hao432_fallback",
        "rcpt_recovery_hao432_cancelled"
      ],
      "render_receipt_ids": {
        "phone:operator": "rcpt_render_hao432_phone",
        "swissknife:ui": "rcpt_render_hao432_swissknife",
        "meta_glasses:terminal": "rcpt_render_hao432_glasses"
      }
    }
  },
  "assertions": [
    "Hallucinate App emits every receipt ID consumed by VAI and MGW launch replay",
    "VAI and MGW receive identical session, command, policy, and placement correlation IDs",
    "recovery receipt IDs remain stable across retry, fallback, and cancel",
    "the Meta glasses render receipt is the MGW orb_receipt_cid alias, not a separate command authority"
  ]
}
```

## Replay Notes

- Hallucinate App emits the receipt IDs and correlation IDs; VAI and MGW only
  consume and replay them.
- `session_id`, `command_correlation_id`, `policy_correlation_id`, and
  `placement_correlation_id` are copied unchanged to every emitted receipt and
  both consumer replay blocks.
- The MGW `orb_receipt_cid` is an alias to the Hallucinate App Meta glasses
  render receipt, so the widget replay cannot become a separate command
  authority.
