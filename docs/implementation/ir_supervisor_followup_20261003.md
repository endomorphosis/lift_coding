# Supervisor initialization and replay followup

This release fixes three remaining component gaps: benchmark initialization now
receives the selected formula decoder, checkpoint replay has bounded verified
reads, and the shared scheduler can gradually resume admissions after pressure.
It preserves the existing default admission policy and model/proof authorities.

The [benchmark wrapper fix](../../external/ipfs_accelerate/docs/agent_supervisor/evidence/benchmark-initial-context-20261003/README.md)
forwards the frozen formula decoder and reviewed header protocol to the native
initial-context builder. Previously both arguments caused a `TypeError` before
inference. The new boundary and neighboring tests passed 39 cases, including
authored frozen inference, DuckLake hydration and persisted replay. The three
original failures remain in the evidence.

The [artifact replay qualification](../../external/ipfs_datasets/docs/software_contracts/evidence/registry-bounded-replay-20261003/README.md)
has 148 final passing checks. Source384 generations, prior heads and projections,
model-generation corpus attachments and resident inference read exact verified
bytes through the existing registry. Oversized files, FIFOs, symlinks, corruption
and concurrent growth refuse before decoding. This bounds artifact input bytes;
it does not promise a total peak-RSS limit or migrate old producer generations.
The controls include actual CPU inference, source-generation training, pinned
Lake checks and cold replay. An initial run without explicit Lake configuration
skipped 12 cases; the configured rerun executed and passed all 12.

[Shared pressure recovery](../../external/ipfs_datasets/docs/autoencoders/SHARED_PROOF_PRESSURE_RECOVERY.md)
uses the existing host scheduler and durable state lock. With
`IPFS_DATASETS_PROOF_RESOURCE_RECOVERY=1` in every cooperating process, admissions
require spaced healthy samples after cooldown, then resume at a bounded rate.
Validation and cleanup retain their reserved lane and original pressure checks.
The default remains disabled; active clients must agree on the shared policy.
The host readiness probe left its current configuration intact and recorded
the policy mismatch. Controlled pressure tests are distinct from an actual
external-load stress campaign. The recovery suite passed 87 controls, including
four actual subprocess and restart controls with injected pressure and time.

The full learned methodology still needs integration into the Harbor container
route. The earlier finite checkpoint fixture uses three CPU/process slots and
a 6 GiB parent, while the original benchmark task allows one CPU and 2 GiB.
A fair comparison needs a qualified common resource profile, exact model/index
binding and proof/planning consumption in that route. These component fixes
produce no new official benchmark score, token advantage or promoted weights.

The frozen backlog remains 18 of 32 closed, with 26 qualified for their declared
scope and 14 production criteria open. GPU device admission, aggregate resource
enforcement, the joined acceptance matrix and matched benchmark campaign remain
among the outstanding work. Concurrent upstream decoder work is preserved in
the pinned datasets revision.
