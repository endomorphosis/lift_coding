# HAO-128 Resolution

Date: 2026-05-26
Source finding: 2026-05-26-hao-128-codebase-scan-98853974dbe3.md

## Finding

The codebase scan flagged `src/handsfree/github/auth.py` because
`GitHubAppTokenProvider.get_token()` caught every exception during token lookup
and returned `None`.

## Resolution

Unconfigured GitHub App auth still returns `None` so fixture mode remains
available. Once GitHub App auth is configured, mint and refresh failures now
surface as errors instead of being converted into no-token mode. Malformed
installation-token responses are also normalized into explicit `RuntimeError`
messages before cache state is updated.

## Validation

Passed from the HAO-128 worktree:

```bash
python3 -m py_compile src/handsfree/github/auth.py
python3 -m pytest tests/test_github_app_auth.py -q
```
