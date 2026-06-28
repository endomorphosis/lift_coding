# HAO-715 Validation Retry-Budget Repair

Date: 2026-06-27
Task: HAO-715
Source task: HAO-713
Goal id: VAIOS-G728
Goal packet: goal_packet/launch/hallucinate_app/44dceea6bc53

HAO-715 repairs the retry-budget finding in
`data/hallucinate_multimodal_control/discovery/2026-06-27-hao-715-hao-713-retry-budget.md`
without weakening the launch Playwright validation gate. Electron UI coverage
still requires a display-capable host or `xvfb-run`, but backend/static launch
gate specs remain executable on headless supervisor hosts.

## Repair Fixture

```json
{
  "schema": "hallucinate_app.validation_retry_budget_repair.v1",
  "task_id": "HAO-715",
  "source_task_id": "HAO-713",
  "goal_id": "VAIOS-G728",
  "goal_packet": "goal_packet/launch/hallucinate_app/44dceea6bc53",
  "evidence_term": "launch Playwright validation gate",
  "blocked_validation_diagnostic": "missing_xvfb_for_electron_playwright",
  "blocked_validation_exit_code": 78,
  "preserves_launch_playwright_validation_gate": true,
  "headless_safe_specs": [
    "hallucinate_app/test/e2e/mcp-feature-exposure.spec.ts",
    "hallucinate_app/test/e2e/mcp-dashboard-interoperability.spec.ts",
    "hallucinate_app/test/e2e/multimodal-control-surface.spec.ts",
    "hallucinate_app/test/e2e/daemon-launch-health.spec.ts"
  ],
  "electron_required_specs": [
    "hallucinate_app/test/e2e/menu-system.spec.ts",
    "hallucinate_app/test/e2e/mcp-daemon-manager.spec.ts"
  ]
}
```
