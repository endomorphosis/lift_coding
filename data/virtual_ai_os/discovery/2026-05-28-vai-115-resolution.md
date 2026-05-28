# VAI-115 Resolution

Date: 2026-05-28
Source finding: `scripts/hallucinate_multimodal_control_todo_supervisor.py:303`
Evidence: `/home/barberb/lift_coding/data/virtual_ai_os/discovery/2026-05-28-vai-115-codebase-scan-fbd7ce184cdf.md`

## Finding

The codebase scan flagged line 303 as an `annotated_followup`:

```python
args = _with_default(args, "--objective-surplus-min-terms-per-todo", str(OBJECTIVE_SURPLUS_MIN_TERMS_PER_TODO))
```

## Analysis

Line 303 is correct — `OBJECTIVE_SURPLUS_MIN_TERMS_PER_TODO` is properly imported from
`hallucinate_multimodal_control_todo_daemon` where it reads from the
`HANDSFREE_HAO_OBJECTIVE_SURPLUS_MIN_TERMS_PER_TODO` environment variable (defaulting to 4),
and `--objective-surplus-min-terms-per-todo` is a recognised argument in `parse_args`.

However, inspecting the broader block (lines 296–310) revealed a latent **maintenance risk**
on lines 297 and 306: the discovery output paths were hardcoded as the string
`"data/hallucinate_multimodal_control/discovery"` independently of the `DISCOVERY_DIR`
constant that governs the discovery directory itself.  If `DISCOVERY_DIR` were ever relocated,
those two strings would silently diverge.

## Fix

Replaced the two hardcoded strings with a computed relative path derived from `DISCOVERY_DIR`
and `REPO_ROOT`:

```python
# line 297 (objective scan)
args = _with_default(args, "--objective-discovery-output-path",
                     DISCOVERY_DIR.relative_to(REPO_ROOT).as_posix())

# line 306 (codebase scan)
args = _with_default(args, "--codebase-scan-discovery-output-path",
                     DISCOVERY_DIR.relative_to(REPO_ROOT).as_posix())
```

The computed value is identical to the former hardcoded string for the current configuration,
so runtime behaviour is unchanged.

## Verdict

Maintenance improvement: the hardcoded path strings adjacent to line 303 posed a drift risk
that has now been eliminated.  Line 303 itself was and remains correct.

## Validation

- `python3 -m py_compile scripts/hallucinate_multimodal_control_todo_supervisor.py` → PASS
