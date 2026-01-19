# PR-085 work log

## Checklist
- [ ] Add iOS interruption observer and handlers.
- [ ] Ensure audio session re-activation after interruptions.
- [ ] Add lifecycle re-apply logic (if needed).
- [ ] Add dev logging/diagnostics hooks.
- [ ] Update docs with manual test steps.

## Notes
- Prefer conservative defaults; don’t enable background audio unless required.
- Keep changes scoped to iOS audio session stability.
