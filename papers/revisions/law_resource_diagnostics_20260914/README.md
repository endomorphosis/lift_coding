The diagnostic reader now records the exact failing operation, controller-file
path, operating-system error number, and both held and current directory
identities. It rejects directory replacement and preserves every failed read.
Parent checks require stable identity, nondecreasing CPU and memory-peak
counters, zero processes and an unpopulated cgroup. These checks do not by
themselves admit a failed leaf observation.

Two actual short-lived containers used the existing pinned image and explicit
Docker daemon, with one CPU, 2 GiB memory/no extra swap, 16 processes, no network
and a read-only root. Each held a real `cpu.stat` descriptor across container
exit. Both returned **ENODEV (errno 19)** when that descriptor was read after
exit; the current leaf path was absent while the open directory identity was
unchanged. Each ordinary polling sequence completed 67 observations without
an error. This deliberately forced terminal-read condition demonstrates a
kernel failure mechanism; it does **not** establish the exact cause of the
historical LA-030 v2 `OSError`, whose receipt lacks errno/path details.

The first diagnostic run completed its container and removed it, then failed a
case-sensitive cleanup assertion because Docker emitted lowercase `error: no
such object`. Its original failed report and source remain intact. A separate
read-only reconciliation verified exact-container absence and stable empty
parent accounting. The second version accepts only recognized, exact-target
Docker absence diagnostics regardless of case and passed the full lifecycle.
All failed, successful and reconciliation artifacts remain in the inventory.

Nine unit tests cover four errno classes, failed opens, directory replacement
before and during sampling, symlink/path rejection, changed parent identity,
regressing counters, populated groups, descriptor leaks, and exact Docker
absence classification. A separate read-only verifier checks 30 artifact
hashes, actual container/resource identities, termination, cleanup, parent
counters and source snapshots:

```bash
python3 -B -m unittest discover -s papers/revisions/law_resource_diagnostics_20260914 -p test_cgroup_observation.py -v
python3 -B papers/revisions/law_resource_diagnostics_20260914/verify_diagnostics.py
```

This is development diagnostic evidence: two constructed container executions,
zero model calls and zero scientific cases. The historical LA-030 package and
receipts were not changed. The new scientific runner still needs to integrate
this reader, qualify any narrowly justified terminal-disappearance handling,
and enforce the complete 120-second attempt boundary including cleanup.

The added `terminal_reconciliation.py` consumes only trusted host evidence for
the specifically reproduced ENODEV controller-read condition. It requires the
same sampled/held leaf identity, exact Docker container and parent, confirmed
successful termination, missing leaf path, fresh stable empty parent counters
covering the sampled leaf costs, and no resource-limit events. It retains the
failed read and returns permission to use final parent accounting; it never
admits a candidate. Other errno values, replacement/access errors, running or
failed containers and stale/incomplete accounting remain failures. Four added
tests use the actual retained kernel probe and altered controls. This helper
still needs integration and qualification in the full attempt runner.
