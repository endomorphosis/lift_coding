# HAO-715 Daemon Launch Validation Retry-Budget Repair

Date: 2026-06-27
Task: HAO-715
Source task: HAO-713

This repair receipt closes the validation retry-budget follow-up for HAO-713
without weakening the daemon launch Playwright validation gate. The original
blocked validation was caused by a no-display Electron host reporting the stable
`missing_xvfb_for_electron_playwright` diagnostic. Backend/static launch specs
remain runnable in headless supervisor lanes, while full Electron UI coverage
still requires `DISPLAY`, `WAYLAND_DISPLAY`, or `xvfb-run`.

## Repair Fixture

```json
{
  "schema": "hao_validation_retry_budget_repair_v1",
  "task_id": "HAO-715",
  "source_task_id": "HAO-713",
  "retry_budget_finding": "data/hallucinate_multimodal_control/discovery/2026-06-27-hao-715-hao-713-retry-budget.md",
  "blocked_validation_diagnostic": "missing_xvfb_for_electron_playwright",
  "blocked_validation_exit_code": 78,
  "preserves_launch_playwright_validation_gate": true,
  "headless_safe_specs": [
    "hallucinate_app/test/e2e/multimodal-control-surface.spec.ts",
    "hallucinate_app/test/e2e/daemon-launch-health.spec.ts"
  ],
  "electron_display_required_specs": [
    "hallucinate_app/test/e2e/mcp-feature-exposure.spec.ts",
    "hallucinate_app/test/e2e/mcp-dashboard-interoperability.spec.ts"
  ],
  "validation_commands": [
    "npm --prefix hallucinate_app run test:e2e -- daemon-launch-health.spec.ts",
    "npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts"
  ],
  "keeps_supervisor_fed_backlog_aligned": true
}
```

## Evidence

- `hallucinate_app/test/e2e/daemon-launch-health.spec.ts` reads this repair
  fixture and verifies that HAO-713 still has headless-safe launch coverage.
- `data/hallucinate_multimodal_control/discovery/2026-06-27-hao-715-hao-713-retry-budget.md`
  remains the original retry-budget finding that created this follow-up.
