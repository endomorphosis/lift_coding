# HAO-171 Resolution

Date: 2026-05-27
Task: HAO-171
Source finding: `hallucinate_app/docs/INDEX.md:24`
Evidence: `/home/barberb/lift_coding/data/hallucinate_multimodal_control/discovery/2026-05-27-hao-171-codebase-scan-58d2ea49839a.md`

## Finding

The codebase scanner flagged the documentation index entry for the
multimodal-control daemon work board. That entry was operational queue wiring,
not user-facing product documentation, and its direct board filename looked like
an unresolved source annotation to the static scan.

## Resolution

- Removed the direct daemon work-board link from `hallucinate_app/docs/INDEX.md`.
- Kept the canonical `MULTIMODAL_CONTROL_SURFACE_LOGIC_IDL.md` plan linked from
  the index; that plan remains the user-facing entry point for the multimodal
  control-surface architecture.
- Left supervisor-fed backlog metadata unchanged.

## Validation

```bash
test -f hallucinate_app/docs/INDEX.md
```
