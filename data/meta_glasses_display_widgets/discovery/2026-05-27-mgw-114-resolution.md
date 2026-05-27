# MGW-114 Code Annotation Resolution

Date: 2026-05-27
Task: MGW-114
Source finding: `work/REMAINING_GAPS_AND_PR_INSTRUCTIONS.md:180`
Evidence: `/home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-27-mgw-114-codebase-scan-4b6fa8e6e4e8.md`

## Finding

The scan matched the "Expected PR URLs" section because it committed URL-shaped
placeholders for future GitHub PR numbers. Those values were not actionable links
and could be mistaken for unresolved implementation annotations.

## Resolution

`work/REMAINING_GAPS_AND_PR_INSTRUCTIONS.md` now tells operators to record the
actual GitHub URL returned after each draft PR is created. The manual UI link was
also made concrete for `endomorphosis/lift_coding`, while the shell examples keep
their local `REPO` variable inside executable command snippets.

## Validation

```bash
test -f work/REMAINING_GAPS_AND_PR_INSTRUCTIONS.md
```
