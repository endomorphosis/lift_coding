# HAO-126 Resolution

Date: 2026-05-26
Source finding: 2026-05-26-hao-126-codebase-scan-a70cd0bd27d0.md

## Finding

The codebase scan flagged `src/handsfree/ai/capabilities.py` because the final
registered-capability dispatcher branch raised `NotImplementedError`.

## Resolution

All currently registered AI capabilities have concrete dispatcher branches. The
remaining branch is therefore a registry/dispatcher consistency guard, not a
planned implementation placeholder. It now raises `RuntimeError` with a message
that identifies registry drift if a future capability is registered without an
executor.

## Validation

Passed from the HAO-126 worktree:

```bash
python3 -m py_compile src/handsfree/ai/capabilities.py
```
