# MGW-179 Codebase Scan Finding

Date: 2026-05-30
Fingerprint: fbd7ce184cdf61e6ed3f7ef380122d02117c6232
Kind: annotated_followup
Source: scripts/hallucinate_multimodal_control_todo_supervisor.py:303
Priority: P3
Track: runtime

## Evidence

```text
args = _with_default(args, "--objective-surplus-min-terms-per-todo", str(OBJECTIVE_SURPLUS_MIN_TERMS_PER_TODO))
```

## Suggested Handling

Review the finding in context, decide whether it represents a bug, missing test,
maintenance risk, or false positive, and land a small fix with validation. If the
finding is a false positive, document why in the changed code or discovery notes
so the supervisor does not keep re-adding the same work.

## Resolution (MGW-179)

**False positive.** The word "todo" in `--objective-surplus-min-terms-per-todo` is part
of the CLI flag identifier — it refers to backlog task entries — and is not a code
annotation. A clarifying comment was added immediately before the flagged line in
`scripts/hallucinate_multimodal_control_todo_supervisor.py` (alongside the existing
comment on the `--objective-todo-vector-index-path` argument). The script continues
to compile and function correctly. The supervisor should not refile this finding.
