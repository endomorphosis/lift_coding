# HAO-100 Codebase Scan Finding

Date: 2026-05-26
Fingerprint: 6e4fbd36e646447b55a94706454af4cf6f7859f3
Kind: annotated_followup
Source: scripts/meta_glasses_display_llm_router.py:38
Priority: P3
Track: runtime

## Evidence

```text
parser.add_argument("--todo-path", type=Path, default=TODO_PATH)
```

## Suggested Handling

Review the finding in context, decide whether it represents a bug, missing test,
maintenance risk, or false positive, and land a small fix with validation. If the
finding is a false positive, document why in the changed code or discovery notes
so the supervisor does not keep re-adding the same work.
