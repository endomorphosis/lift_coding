# Meta Glasses Display Widget ORB Mapping

This file anchors the current bridge mapping between:

- the Swissknife-style ORB operation name
- the existing HandsFree mobile action id
- the DAT bridge method invoked locally on the phone

It is derived from the currently tested backend/mobile contract in `tests/test_meta_glasses_display_widget_harness.py` and `mobile/src/utils/agentActions.js`.

| ORB operation | Mobile action id | DAT bridge method | Primary payload field |
| --- | --- | --- | --- |
| `render_widget` | `mobile_render_display_widget` | `renderDisplayWidget` | `manifest` |
| `update_widget` | `mobile_update_display_widget` | `updateDisplayWidget` | `patch` |
| `clear_widget` | `mobile_clear_display_widget` | `clearDisplayWidget` | `widget_id` |
| `focus_next` | `mobile_focus_display_widget` | `focusDisplayWidget` | `focus.direction` |
| `activate` | `mobile_activate_display_widget_action` | `activateDisplayWidgetAction` | `activated_action_id` |
| `reset_session` | `mobile_reset_display_widget_session` | `resetDisplayWidgetSession` | full payload |
| `play_video` | `mobile_play_display_widget_video` | `playDisplayWidgetVideo` | `video` |
| `subscribe_updates` | `mobile_subscribe_display_widget_updates` | `subscribeDisplayWidgetUpdates` | `subscription` |

## Notes

- `focus_next` is retained as the current ORB-visible operation name because that is what the backend harness emits today. Direction is still carried in the payload so `previous` and `next` can share the same operation.
- The mobile payload is the phone-edge transport object. It should continue to carry `descriptor_cid` or `interface_cid`, `orb_receipt_cid`, `policy_decision`, and `correlation_id` so the phone can behave as an ORB edge node rather than a standalone RPC client.
- Native DAT-unavailable cases should continue to return a structured fallback instead of failing silently. That fallback is part of the bridge contract, not an implementation detail.