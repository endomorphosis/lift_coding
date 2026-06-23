# VAI-016 Meta Ray-Ban browser simulator shell

Date: 2026-06-23

## Scope

VAI-016 extends the browser-first Meta Ray-Ban display simulator with a shared
command/session shell for the mobile-hosted virtual desktop model.

## Evidence

- `dev/meta-rayban-display-simulator/simulator.js` exports a
  `handsfree.virtual-desktop-session` browser session model and
  `handsfree.command-session@0.1.0` command envelopes.
- The shell models one display surface and one audio surface using the same
  stable endpoint IDs expected by the Meta glasses remote terminal route:
  `meta_glasses_display_widget`, `meta_glasses_audio_input`, and
  `meta_glasses_audio_output`.
- Commands are queued with session identity, phone host identity, widget refs,
  and a `handsfree.meta-glasses/remote-terminal@0.1.0` route so display and
  audio commands can be replayed through the same mobile-hosted virtual desktop
  session contract.
- `dev/meta-rayban-display-simulator/index.html` now exposes dispatch and export
  controls for the browser simulator session.

## Validation

Command:

```bash
PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_meta_glasses_display_todo_queue.py
```

Expected coverage:

- the Meta Ray-Ban browser simulator shell exports the mobile-hosted virtual
  desktop session model;
- display surface commands route to the display widget endpoint;
- audio surface commands route to audio input and output endpoints;
- the shell exposes command dispatch, session export, and session inspection
  controls.
