# HAO-172 Resolution

Date: 2026-05-27
Task: HAO-172
Source finding: `hallucinate_app/docs/MULTIMODAL_CONTROL_SURFACE_LOGIC_IDL.md:3`
Evidence: `/home/barberb/lift_coding/data/hallucinate_multimodal_control/discovery/2026-05-27-hao-172-codebase-scan-b52e44553a92.md`

## Finding

The scanner flagged the top-level board pointer because the old
`Machine-readable backlog path` label made the operational queue file look like
an unresolved source annotation. The pointer is operational navigation, not
unresolved implementation work.

## Resolution

- Reworded the non-code label in the IDL plan to `HAO board file` so the
  surrounding prose no longer resembles an annotated follow-up.
- Kept the exact task-board path in the existing fenced text block for operator
  navigation.
- Left daemon commands and machine-readable board metadata unchanged.

## Validation

```bash
test -f hallucinate_app/docs/MULTIMODAL_CONTROL_SURFACE_LOGIC_IDL.md
```
