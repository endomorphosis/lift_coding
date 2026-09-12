# NS-026 production provider qualification

Retained evidence for an actual development Grok invocation, pinned historical
materialization, independent scoring, and resume/unknown-effect checks.

This directory does not store scorer-only payloads, original Git objects,
fixed-commit trees, or provider credentials.

Executable entry:

```
python3 papers/completion/neurosymbolic_supervision/qualification/production_provider/run_qualification.py
python3 papers/completion/neurosymbolic_supervision/qualification/production_provider/validate_production_provider.py
```

`run_qualification.py` performs the bounded real development call. The
validator checks retained receipts and does not re-dispatch.
