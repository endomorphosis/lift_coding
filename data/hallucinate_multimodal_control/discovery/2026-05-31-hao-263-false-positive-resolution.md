# HAO-263 False Positive Resolution

Date: 2026-05-31
Source: scripts/hallucinate_multimodal_control_todo_supervisor.py:307
Kind: annotated_followup

## Finding

The scanner filed HAO-263 from the `# scanner-resolved:` comment at line 307
because that comment contained the substring "todo" (as part of the CLI flag name
`--objective-surplus-min-terms-per-todo`).

## Resolution

False positive. The word "todo" at this location is part of the CLI flag name
`--objective-surplus-min-terms-per-todo`, which refers to backlog task entries
passed to the implementation supervisor. It is not a deferred-work annotation.

HAO-263 has been added to the `scanner-resolved:` list so the supervisor will
not re-file this finding. In attempt 2 the supervisor script was refactored
(from ~307 lines to 128 lines) and the CLI arg construction code moved to
`scripts/hallucinate_multimodal_control_todo_daemon.py`. The scanner-resolved
annotation was added there (line 65, `OBJECTIVE_SURPLUS_MIN_TERMS_PER_TODO`)
to cover the relocated code.
