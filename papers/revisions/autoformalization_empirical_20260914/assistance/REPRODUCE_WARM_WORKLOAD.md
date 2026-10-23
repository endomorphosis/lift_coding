# Finite inference with one warm model

For a fresh replication with frozen inputs and empty result directories, use the
whole finite client workload inside one bounded runner. All client batches reuse
the same server; it is removed after the final request, a failure, or the deadline.
The permanent service remains masked.

The configured natural-evaluation entry point is
`python3 -B papers/revisions/autoformalization_empirical_20260914/assistance/launch_natural_warm.py`.
It explicitly supplies the 10000-second total wall bound and 360-second readiness
timeout, acquires the resource lock, and refuses to reload an active endpoint.
Use `--dry-run` to inspect its exact command without launching a model.
The underlying equivalent command is:

```bash
python3 -B scripts/run_leanstral_ephemeral.py \
  --wall-seconds 10000 --startup-seconds 360 \
  --memory-gib 90 --reserve-gib 12 --cpus 4 --context 4096 \
  --chat-template-file papers/revisions/autoformalization_empirical_20260914/assistance/leanstral_v15.jinja \
  --server-log /path/to/fresh-server.log \
  -- /usr/bin/python3 -B papers/revisions/autoformalization_empirical_20260914/assistance/run_natural_workload.py
```

The workload checks retained attempts and runs only missing records; do not rerun
it against a completed result directory merely to load a model. Real inference
requires the separately pinned weight artifact. The current live handoff used a
runtime-only extension of the already loaded instance, because the user changed
the active-work resource envelope after the original shorter job started. That
handoff is documented in LIVE_RUNTIME_STATUS.json and warm_lifecycle.jsonl.
The process-specific `continue_natural_warm.py` is an operational recovery record,
not the portable replication entry point.
