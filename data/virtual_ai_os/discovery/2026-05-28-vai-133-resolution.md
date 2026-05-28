# VAI-133 Resolution

Date: 2026-05-28
Task: VAI-133
Source finding: hallucinate_app/hallucinate_app/python/hallucinate_app/github_issue_reporter.py:369
Fingerprint: b701b80bf41c6cc95fc8720fa5a0f3f57ffcb6c3

## Finding

Bare `except Exception as e:` at line 369 of `github_issue_reporter.py` (inside
`report_issue`) swallowed the full traceback — only the string representation of
the exception was logged, not the stack frame chain.

## Fix

Changed `logger.error(f"Failed to create GitHub issue: {e}")` to
`logger.exception(...)` so the exception is captured with its full traceback.

A concurrent HAO-212 implementation added structured `GithubException` handling
with separate status/data fields and `exc_info=True`.  The two changes conflicted
in the hallucinate_app submodule.

## Merge Conflict Resolution

The submodule conflict (`UU hallucinate_app`) was resolved by merging:

- VAI-133 side: `f515e6fefcf1e1de8a49639a657ad07680bf2615` — `logger.exception`
- HAO-212 side: `3b989f6ae7f1ab9672f1cd5239ef088c2c3ca048` — structured API error detail

Resolution commit in submodule: `1e5f563ce03c8a9829cbaa38cb1d342f26f9bd2b`

HAO-212's richer `GithubException` branch was kept as the resolution because it
already includes `exc_info=True` for full tracebacks, and additionally captures
the HTTP status code and API error payload for easier triage.

## Validation

```
python3 -m py_compile hallucinate_app/hallucinate_app/python/hallucinate_app/github_issue_reporter.py
```
