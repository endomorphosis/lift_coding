# VAI-010 Hardware-Free End-to-End Harness

Task: Build a hardware-free end-to-end integration harness.

Evidence added:
- `tests/test_virtual_ai_os_end_to_end_harness.py` creates an in-process
  virtual AI OS flow with deterministic phone, desktop peer, SwissKnife UI,
  Hallucinate App command plane, and Meta glasses terminal surfaces.
- The harness routes a glasses audio command through the public capability
  routing kernel into the SwissKnife ORB surface while keeping the Hallucinate
  App operator console in the dispatch plan.
- The mobile ORB API registers a simulated phone edge, publishes the terminal
  command event, binds the SwissKnife service descriptor, invokes the command,
  dispatches streamed display/audio/mobile-card actions, then exercises a
  recoverable desktop-peer disconnect.
- The runtime binding is monkeypatched only inside the test, so validation does
  not require Meta hardware, a real desktop peer, network services, submodule
  daemons, or MCP credentials.

Coverage handoff:
- VAI-003 capability routing is covered through
  `CapabilityRoutingKernel.dispatch_task`.
- VAI-006 SwissKnife UI/ORB binding is covered through the bound service
  descriptor and `swissknife.orb` runtime surface.
- VAI-007 Hallucinate App command plane is covered as the operator-console
  source surface and command-plane metadata.
- VAI-008 Meta glasses terminal behavior is covered through the
  `handsfree.meta-glasses/remote-terminal@0.1.0` route and mobile-card fallback.
- VAI-004 compute placement behavior is covered by simulated desktop-peer
  offload and fallback to phone-local recovery.

Validation:
- `PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_virtual_ai_os_end_to_end_harness.py`
