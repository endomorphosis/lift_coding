# VAI-008 Meta Glasses Remote Terminal

Task: Route Meta glasses audio and display as remote terminal endpoints.

Evidence added:
- `src/handsfree/meta_glasses_remote_terminal.py` defines the
  `handsfree.meta-glasses/remote-terminal@0.1.0` route contract for
  mobile-hosted sessions.
- The route exposes audio command input, audio response output, and display
  widget status endpoints with phone, Web App, and mobile-card fallbacks.
- The session contract records pairing state, disconnection handling, and
  desktop-offload visibility so the glasses path is constrained to terminal
  behavior instead of acting as a free-form display surface.
- The VAI-008 section in
  `implementation_plan/docs/19-virtual-ai-os-submodule-integration.md` records
  the required route shape and fallback semantics.
- `tests/test_meta_glasses_display_todo_queue.py` validates the route manifest
  used by the device-plane backlog validation command.

Dependency handoff:
- VAI-003 provides the shared capability routing registry and mobile/glasses
  surface labels.
- VAI-004 provides runtime placement semantics for phone-local and desktop-peer
  compute fallback.
- VAI-006 provides the Swissknife ORB/display-widget binding referenced by the
  visual status endpoint.
- VAI-007 provides the Hallucinate App operator-console path that keeps
  desktop-offload status visible when glasses rendering falls back.

Validation:
- `PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_meta_glasses_display_todo_queue.py`
