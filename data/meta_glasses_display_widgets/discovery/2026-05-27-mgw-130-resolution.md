# MGW-130 Merge Retry-Budget Resolution

Date: 2026-05-27
Task: MGW-130
Source task: MGW-125
Evidence: `/home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-27-mgw-130-mgw-125-merge-retry-budget.md`

## Merge Blocker

MGW-125 exhausted its retry budget due to `main_checkout_dirty_conflict` on
`implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md`.
The intended implementation (principal deletion in `auth_dashboard.js`) was
not committed.

Additionally, an unresolved merge conflict existed in the `hallucinate_app`
submodule at:
`hallucinate_app/experiments/webnn-developer-preview/demos/whisper-base/static/js/audioMotion-analyzer.js`

## Resolution

1. **Resolved merge conflict** in `audioMotion-analyzer.js` (line 1256–1267):
   took the incoming `2fe8f0d` version that adds `&& ! isLeds` guard to
   `channelGap` so LED channels stay flush.

2. **Implemented principal deletion** in
   `hallucinate_app/hallucinate_app/node/dashboard/auth_dashboard.js`:
   - Replaced stub `showMessage('info', 'Principal deletion is not implemented yet')`
     and `// TODO: Implement principal deletion` with actual call to
     `this.auth.deletePrincipal(principalId)`.
   - On success: shows a success message, reloads principal list, refreshes
     summary counts.
   - On failure: logs the error and surfaces it via `showError`.

3. **Committed** both changes in the `hallucinate_app` submodule.

## Validation

```bash
test -f /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-27-mgw-130-mgw-125-merge-retry-budget.md
```

Result: passed.
