# MGW-274 Launch Readiness Gate

Task: MGW-274
Companion task: VAI-340
Goal id: VAIOS-G697
Track: launch
Missing evidence closed: launch Playwright validation gate

MGW-274 keeps the Meta glasses display-widget backlog aligned with the VAIOS-G697
production launch objective. The gate is deliberately explicit: scanner hits for
Playwright, generic readiness text, or a stale receipt are not enough. The
supervisor may treat the phone-hosted Swissknife virtual desktop, desktop-peer
offload, Hallucinate App mediation, and Meta glasses terminal path as launch
ready only when this MGW packet, the VAI-340 `launch_readiness_receipt_v1`, the
readiness document, and both Playwright commands name the same product slice.

## LaunchReadinessGate

```json
{
  "schema": "launch_readiness_receipt_v1",
  "task_id": "MGW-274",
  "companion_task_id": "VAI-340",
  "goal_id": "VAIOS-G697",
  "receipt_id": "launch-readiness-mgw-274-phone-desktop-glasses",
  "vai_receipt": "data/virtual_ai_os/discovery/2026-06-23-vai-340-launch-readiness-gate.md",
  "readiness_doc": "docs/launch/phone_desktop_glasses_readiness.md",
  "objective_heap": "implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md",
  "python_gate": {
    "path": "tests/test_virtual_ai_os_launch_readiness_gate.py",
    "command": "PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_virtual_ai_os_launch_readiness_gate.py -q"
  },
  "playwright_gates": [
    {
      "surface": "swissknife",
      "command": "npm --prefix swissknife run test:e2e:meta-glasses",
      "spec": "swissknife/test/e2e/meta-glasses-virtual-os.spec.ts",
      "covers": [
        "phone-hosted Swissknife virtual desktop",
        "desktop-peer offload",
        "Meta glasses terminal"
      ]
    },
    {
      "surface": "hallucinate_app",
      "command": "npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts",
      "spec": "hallucinate_app/test/e2e/multimodal-control-surface.spec.ts",
      "covers": [
        "Hallucinate App mediation",
        "remote Meta glasses control-surface receipt"
      ]
    }
  ],
  "blocking_rule": "VAIOS-G697 remains active until the Python LaunchReadinessGate and both launch Playwright validation gate commands pass for this receipt lineage.",
  "split_policy": "No child split is required unless physical phone, desktop peer, or physical Meta glasses evidence capture fails independently after the deterministic Playwright gate is green."
}
```

## Supervisor Alignment

- `implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md` keeps
  VAIOS-G697 active and names the MGW-274 launch readiness gate alongside the
  VAI-340 launch readiness gate.
- `docs/launch/phone_desktop_glasses_readiness.md` is the operator-facing
  LaunchReadinessGate contract for the launch Playwright validation gate.
- `tests/test_virtual_ai_os_launch_readiness_gate.py` is the fast static guard
  that rejects weak scanner-only matches before browser tests run.

## Validation

```bash
PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_virtual_ai_os_launch_readiness_gate.py -q
npm --prefix swissknife run test:e2e:meta-glasses
npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts
```
