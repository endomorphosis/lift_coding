# VAI-006 Swissknife Virtual UI And ORB Binding

Task: Bind Swissknife into the virtual UI and ORB plane.

Evidence added:
- `src/handsfree/swissknife_virtual_ui.py` records the Swissknife virtual
  desktop surface, MCP Control app launch command, ORB router module,
  descriptor-pack module, transport kinds, control contracts, and fallback
  surfaces.
- The runtime router now resolves Swissknife ORB handlers through that binding,
  preserving the existing `swissknife.orb::<capability_id>` handler contract.
- The top-level capability routing catalog includes the binding metadata
  alongside the existing mobile/glasses ORB dispatch metadata.
- `tests/test_virtual_ai_os_swissknife_integration.py` validates the binding
  sources, registered capabilities, handler refs, and dispatch-plan metadata.

Validation:
- `PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_virtual_ai_os_swissknife_integration.py`
