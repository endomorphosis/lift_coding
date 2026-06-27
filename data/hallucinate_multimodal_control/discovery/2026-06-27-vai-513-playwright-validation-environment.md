# VAI-513 Playwright Validation Environment Gate

Task: VAI-513
Goal id: VAIOS-G723
Merge key: vaios-g723-playwright-validation-environment

VAI-513 keeps the Hallucinate App Electron Playwright launch gate from being
satisfied by skipped UI coverage on headless supervisor hosts. The runner must
use `xvfb-run` when it is available and must otherwise fail with the explicit
`missing_xvfb_for_electron_playwright` environment diagnostic.

The MCP dashboard and Swissknife interoperability path remains blocked on
validation environment repair until Electron Playwright coverage runs under a
display or virtual display.

## Validation Environment Gate

```json
{
  "schema": "playwright_validation_environment_gate_v1",
  "task_id": "VAI-513",
  "goal_id": "VAIOS-G723",
  "merge_key": "vaios-g723-playwright-validation-environment",
  "missing_evidence": "non-skipped Hallucinate Electron Playwright launch gate on headless supervisor hosts",
  "runner": "hallucinate_app/scripts/run_playwright_test.mjs",
  "missing_display_diagnostic": "missing_xvfb_for_electron_playwright",
  "missing_display_exit_code": 78,
  "runner_requirements": {
    "uses_xvfb_run_when_present": true,
    "reports_missing_xvfb_when_absent": true,
    "allows_no_display_electron_skip_to_satisfy_gate": false
  },
  "supervisor_focus": "fix_validation_environment_before_production_ready",
  "validation_commands": [
    "PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_virtual_ai_os_launch_readiness_gate.py tests/test_virtual_ai_os_todo_queue.py -q",
    "cd hallucinate_app && (env -u DISPLAY -u WAYLAND_DISPLAY HALLUCINATE_APP_E2E_NO_BOOTSTRAP=true node scripts/run_playwright_test.mjs --help || test $? -eq 78)"
  ],
  "blocked_readiness_claims": [
    "MCP dashboard production-ready",
    "Swissknife interoperability production-ready"
  ]
}
```

## Supervisor Routing

- `missing_xvfb_for_electron_playwright` is a validation environment repair
  signal for retry-budget tasks.
- A no-display Electron skip cannot close `VAIOS-G723` Playwright evidence.
- The objective heap keeps `fix_validation_environment_before_production_ready`
  visible until the launch gate runs with real Electron coverage.
