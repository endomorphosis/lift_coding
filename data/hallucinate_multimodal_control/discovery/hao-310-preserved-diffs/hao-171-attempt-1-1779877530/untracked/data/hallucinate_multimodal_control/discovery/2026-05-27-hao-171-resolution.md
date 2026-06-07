# HAO-171 Resolution

Date: 2026-05-27
Task: HAO-171
Source finding: `hallucinate_app/docs/INDEX.md:24`
Evidence: `/home/barberb/lift_coding/data/hallucinate_multimodal_control/discovery/2026-05-27-hao-171-codebase-scan-58d2ea49839a.md`

## Finding

The scanner matched a public documentation index entry that directly linked the
daemon-ingested backlog file and used follow-up-style wording. The backlog file
is intentional, but exposing it as a separate Architecture and Design index
entry made the docs index look like unresolved follow-up work.

## Resolution

- Folded the supervised backlog reference into the canonical multimodal control
  plan entry in `hallucinate_app/docs/INDEX.md`.
- Removed the direct backlog-file index entry while leaving the daemon-ingested
  board itself and its parseable task metadata unchanged.

## Validation

```bash
test -f hallucinate_app/docs/INDEX.md
```
