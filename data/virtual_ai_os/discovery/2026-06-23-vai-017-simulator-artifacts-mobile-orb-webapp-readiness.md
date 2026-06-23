# VAI-017 Simulator Artifacts to Mobile ORB and Web App Readiness

Date: 2026-06-23
Task: VAI-017
Track: mobile

## Scope

VAI-017 defines the pre-hardware proof bundle that connects simulator artifacts
from the browser Meta Ray-Ban shell to the mobile ORB and Web App readiness
flows. The goal is to validate a glasses-terminal session before physical
hardware is attached.

## Simulator artifacts

Use these artifacts as the shared evidence source:

| Artifact | Source | Readiness use |
| --- | --- | --- |
| Browser command session export | `dev/meta-rayban-display-simulator/simulator.js` | Proves `handsfree.virtual-desktop-session`, `handsfree.command-session@0.1.0`, mobile-hosted mode, hardware-free terminal constraints, display/audio endpoints, widget refs, and queued command envelopes. |
| Web App readiness metadata | `dev/meta-rayban-display-simulator/webapp/readiness.json` | Proves 600x600 viewport, static package inventory, deployment URL, public HTTPS hosting requirement, focus order, contrast metadata, and native DAT migration gate. |
| Web App ORB event receipts | `dev/meta-rayban-display-simulator/webapp/app.js` session storage keys | Proves registration, event publication, service binding, subscription, invocation, and dispatch receipts against the mobile ORB API. |
| Hardware-free ORB harness | `tests/test_virtual_ai_os_end_to_end_harness.py` | Proves the same mobile ORB route can register a simulated phone edge, publish a terminal event, bind a SwissKnife service, invoke it, and dispatch display Web App, display widget, audio, and mobile-card render targets. |
| Simulator shell test | `tests/test_meta_glasses_display_todo_queue.py` | Proves the VAI-016 browser simulator exports the command/session model and endpoint IDs required by the mobile-hosted virtual desktop. |

## Mobile ORB readiness flow

The mobile ORB readiness check must ingest simulator artifacts in this order:

1. Register a simulated edge session with `platform: simulator`,
   `dat_capabilities.webAppDisplay: true`, and local interface CIDs for the
   mobile ORB bridge, display widget bridge, and simulator descriptor.
2. Publish the simulator display or audio event with the exported
   `correlation_id`, `orb_receipt_cid`, and source endpoint.
3. Bind the task or SwissKnife service descriptor using the same
   `widget_id`, `widget_cid`, and descriptor CID carried by the simulator.
4. Invoke the bound service with the simulator display widget action, focused
   action ID, viewport, focus order, and parent receipt CIDs.
5. Dispatch the response to `display_webapp`, `display_widget`, `audio`, and
   `mobile_card` so unpaired hardware still validates the glasses-terminal
   fallback path.
6. Persist or export the resulting ORB receipts beside the simulator session
   export so the physical DAT handoff can compare receipt lineage rather than
   replaying an untracked browser action.

Required match keys:

- `widget_id`
- `widget_cid`
- `descriptor_cid` or `interface_cid`
- `correlation_id`
- `focus_order`
- `render_targets`
- parent receipt CIDs

## Web App readiness flow

The Web App readiness check must consume the same simulator proof bundle:

1. Load `dev/meta-rayban-display-simulator/webapp/readiness.json`.
2. Confirm the package lists `index.html`, `styles.css`, `app.js`,
   `manifest.webmanifest`, `readiness.json`, and both PNG icons.
3. Confirm the viewport is 600x600 and the widget entry uses
   `render_path: display-webapp`.
4. Confirm `focus_order` matches the simulator manifest and currently remains
   `pause -> dismiss`.
5. Confirm `hosting.requires_publicly_available_https` is true and
   `deployment_url` is the target URL to register in Meta AI app Web Apps.
6. Confirm the Web App can emit ORB proof receipts through
   `register_edge_capabilities`, `publish_glasses_event`, `bind_service`,
   `invoke_service`, and `dispatch_glasses_response`.

## Acceptance mapping

VAI-017 acceptance is satisfied when the same simulator artifacts feed both:

- mobile ORB readiness: simulated edge registration, event publication,
  service binding, invocation, dispatch, and diagnostics receipt lineage;
- Web App readiness: static package validation, public HTTPS deployment gate,
  focus/navigation metadata, and fixture parity with the simulator manifest.

This creates a pre-hardware gate for a glasses-terminal session. If the mobile
ORB receipt lineage and Web App readiness metadata disagree on widget identity,
descriptor identity, correlation ID, focus order, or fallback render targets,
the session must stay in simulator remediation instead of advancing to physical
DAT hardware.

## Validation

Backlog validation command:

```bash
rg -n "VAI-017|mobile ORB|Web App readiness|simulator artifacts" implementation_plan/docs/19-virtual-ai-os-submodule-integration.md data/virtual_ai_os/discovery
```
