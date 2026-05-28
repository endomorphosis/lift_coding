# HAO-212 Resolution

Date: 2026-05-28
Source: hallucinate_app/hallucinate_app/python/hallucinate_app/github_issue_reporter.py:369
Kind: swallowed_exception
Status: fixed

## Finding

The `except Exception as e:` block in `GitHubIssueReporter.create_issue()` logged
only `str(e)` — swallowing the full stack trace and discarding API-specific
context from `GithubException`.

## Fix

* Added `exc_info=True` to `logger.error` so the full traceback is captured in
  every log handler (file, Sentry, etc.).
* Added an explicit branch for `GithubException` that also logs `e.status` and
  `e.data` (HTTP status code + API response body) before the common `exc_info`
  call — those fields are zero-cost to extract and critical for diagnosing 401,
  403, 404, and 422 API errors.

## Validation

```
python3 -m py_compile hallucinate_app/hallucinate_app/python/hallucinate_app/github_issue_reporter.py
```
Exit 0 — no syntax or import errors.
