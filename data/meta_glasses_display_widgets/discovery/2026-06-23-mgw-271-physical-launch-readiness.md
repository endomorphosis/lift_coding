# MGW-271 Physical Meta Glasses Launch-Readiness Checklist

Scope: define the physical-readiness checklist for using physical Meta glasses as the phone interface to the phone-hosted virtual desktop while keeping the MGW-265 through MGW-270 widget, action, and receipt contracts intact.

Readiness gates:

- Pairing: confirm the phone host can discover and pair the physical Meta glasses, transition `pairing.status` from `discovering` or `pairing_requested` to `paired` and `display_ready`, and persist the paired device reference in `render_context.paired_device_id`.
- Pairing recovery: force disconnect, stale session, display unavailable, and update-required paths; each must render a bounded recovery state with `retry_pairing`, `reset_display_session`, `open_phone_preview`, or `open_mobile_card`.
- Phone-hosted authority: verify the phone remains authoritative for `session_identity`, command routing, policy decisions, and receipt storage. The glasses are only the launch terminal for the virtual desktop and must submit render/update/confirm/cancel through the shared VAI capability envelope.
- Display fallback: unplug, disconnect, or disable the glasses display and verify equivalent state renders through `mobile-card`, `display_webapp`, or `simulator`, including pairing badge, active tool, confirmation prompt, offload state, and receipt identifiers.
- Offload-state visibility: run the desktop peer path through `phone_local`, `desktop_peer`, `hybrid`, and `fallback_phone` placements. The physical glasses view must show the selected desktop peer label, transfer phase/progress when present, placement receipt, and bounded cancel/retry/fallback actions.
- Policy receipt inspection: inspect `descriptor_refs.policy_receipt_cid`, Hallucinate App `mediation_receipt_id`, VAI `capability_receipt_cid`, `peer_offload.receipts`, and any `placement_receipt_cid`, `transfer_receipt_cid`, or `fallback_receipt_cid` for every physical render/update/confirm/cancel path. A missing receipt must render `recovery.code: receipt_missing` instead of silently continuing.
- Input parity: confirm captouch, voice, Neural Band, phone relay, simulator, and mobile-card actions all normalize to Hallucinate App `interaction_envelope.surface: "meta_glasses"` and preserve the same focus order and backend-approved `terminal.*` action IDs.
- Receipt audit: capture the correlation ID, policy outcome, capability receipt, ORB receipt, bridge receipt, and Hallucinate App mediation receipt for the final launch run so the physical session can be compared to the deterministic MGW-270 replay.

Simulator-only gaps to keep visible before signoff:

- Optical brightness, field-of-view comfort, eye-box tolerance, and real wearer legibility cannot be proven by the simulator-only fixture.
- Real Bluetooth/Wi-Fi pairing latency, reconnect behavior, and packet loss are not covered by the deterministic replay.
- Captouch, voice, Neural Band, and phone relay input latency need physical-device timing evidence.
- Battery drain, thermal throttling, firmware update prompts, and DAT native-display firmware failure modes require physical Meta glasses coverage.
- Privacy LED, display dimming, notification interruption, and phone OS backgrounding behavior remain physical launch checks.

Launch-readiness signoff rule:

Physical Meta glasses are launch-ready only when pairing, display fallback, desktop peer offload-state visibility, policy receipt inspection, and the simulator-only gap log are all reviewed against the phone-hosted virtual desktop replay evidence. The deterministic fixture remains the contract baseline; physical validation adds hardware evidence without creating a second command or receipt model.
