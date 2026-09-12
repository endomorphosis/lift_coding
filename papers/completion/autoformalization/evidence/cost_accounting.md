# AF-020 cost accounting

This note accounts for retained autoformalization preparation, annotation, target construction,
features, indexing, updates/selection, model calls, failed attempts, proof reconstruction,
validation, review, and setup costs.  Values come from frozen run/usage records and command
logs.  Dry-run synthetic throughput is not used as CUDA or residency evidence.

## Cost units and observation kinds

| Quantity | Unit | Measured meaning | Unmeasured / other |
| --- | --- | --- | --- |
| elapsed_seconds | seconds | Wall time from a retained command or per-record timer | Null if no timer was kept |
| cpu_seconds | cpu_seconds | Independently observed process CPU time | Never inferred from elapsed wall time |
| gpu_seconds | gpu_seconds | Seconds on actually running CUDA/GPU | Null when CUDA is unavailable; not a measured 0.0 |
| provider_units | provider_units | Executed provider/model-call units | Estimated/provider rates stay labeled; unused calls may be a measured 0 |
| memory_gib | gibibytes | Billed or independently metered GiB | RSS snapshots are not converted into billed GiB |
| human_review_seconds | seconds | Independently timed review | Pending review is unmeasured, not 0.0 |

Observation kinds are `measured`, `estimated`, `provider`, and `unmeasured`.
Estimated and provider figures are never relabeled as measured wall-clock costs.

## Hardware, precision, and cache

- Sealed PATH: `/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin`
- Interpreter: `/usr/bin/python3.12` (3.12.3)
- Machine: `aarch64`
- CUDA_VISIBLE_DEVICES: `None`
- nvidia-smi usable: `False`
- nvidia-smi reason: NVIDIA-SMI has failed because it couldn't communicate with the NVIDIA driver. Make sure that the latest NVIDIA driver is installed and running.
- torch import: `{"error": "ModuleNotFoundError: No module named 'torch'", "ok": false}`
- CUDA available in this process: `False`
- Hardware record: `{"cache_state":"unused","cuda_available":false,"device":"cpu","gpu_telemetry_available":false,"hardware":"cpu","notes":"Sealed-PATH probe; operator ~/.local torch/CUDA is out of scope.","precision":"unmeasured"}`

AF-009 selected `packed_cpu` with float32 parameters/losses on the operator host and recorded
CUDA status `unavailable` (skipped tests, `CUDA_VISIBLE_DEVICES` empty).  AF-011 sealed T0–T2
ran the python autoencoder backend because torch/NumPy were absent from the private HOME.
Those are distinct hardware/precision conditions and are not a matched CPU/CUDA pair.

Cache state is explicit per usage row: `unused`, `hit`, `miss`, `sample_memory`, or `unmeasured`.
T1 sample-memory updates are labeled `sample_memory` and are not treated as a CUDA residency win.

## Phase totals

| Phase | Records | Measured elapsed (s) | Failures | Setup rows | Present |
| --- | ---: | ---: | ---: | ---: | --- |
| setup | 7 | 64.169610 | 0 | 7 | True |
| preparation | 3 | 0.003000 | 0 | 0 | True |
| annotation | 1 | unmeasured | 0 | 0 | True |
| target_construction | 3 | 23.560000 | 0 | 0 | True |
| features | 1 | unmeasured | 0 | 0 | True |
| indexing | 5 | unmeasured | 0 | 0 | True |
| updates_selection | 8 | 150.934000 | 0 | 0 | True |
| model_calls | 1 | unmeasured | 0 | 0 | True |
| failed_attempts | 3 | unmeasured | 3 | 0 | True |
| proof_reconstruction | 2 | 0.000084 | 2 | 0 | True |
| validation | 14 | 242.921914 | 5 | 0 | True |
| review | 1 | unmeasured | 0 | 0 | True |

Measured elapsed summed across phases: 481.588608018 s.
Measured elapsed summed across retained records: 481.588608018 s.
Independent usage sum: 481.588608018 s.
Reconciliation ok: `True`. Setup included: `True`. Failures included: `True`.
Phase totals reconcile with retained run/usage records, including setup and failures.

## Retained sources

Usage rows keep the source path and SHA-256 of the frozen record they were reduced from.
Item-level training rows are not re-emitted; AF-011 arm/replay wall times come from the
checkpoint manifest.  Planning and assistance elapsed values are sums of retained
`cost.elapsed_seconds` cells.  Retrieval/premise rows without timers contribute setup from
the sealed command log and leave per-query latency unmeasured.

Source usage rows: 49.

## Throughput and speedup

- `AF-020:throughput:cpu_t0_replays`: status `measured` value `1.021181001` — T0 codec replays are matched CPU actual runs of the same identity; this is not a CUDA speedup.
- `AF-020:throughput:cuda_unmeasured`: status `unmeasured` value `None` — No matched cold/warm CPU/CUDA/precision actual runs. Unavailable CUDA is not a 0.0s or 1.0x result.

Any CUDA or residency benefit remains unmeasured.  Unavailable hardware is not a zero-cost result,
and it is not reported as 0.0 seconds or a 1.0x speedup.

## Limitations

- Sealed validation PATH has no usable NVIDIA driver (`nvidia-smi` cannot query devices).
- CPU seconds, billed memory-GiB, MiniLM/FAISS embedding cost, Leanstral GPU time, and human review are unmeasured.
- Annotation cost is unmeasured while AF-005 independent gold is pending.
- AF-011 `elapsed_seconds: 0.0` on some aggregate jsonl rows is ignored; wall times are taken from the checkpoint manifest.
- Planning/assistance records that stored `gpu_seconds: 0.0` without CUDA are reclassified as unmeasured GPU cost.
- Packed-CPU qualification (AF-009) is CPU float32 evidence, not a CUDA matched run.
- This accounting is provenance over retained records, not independent scientific replication.

## Versions

- Generated at: 2026-09-12T07:22:36.412961+00:00
- aggregate_costs.py sha256: `ab4c62f23c813a7e94ced9da5922c89156b9aac1fbdb3bb7c2901342a43227f6`
- runtime_telemetry.py sha256: `229e88ee03102e85aac0d1101561338309c5570bd1acee3ea2d1226022e7aa6e`
- environment_manifest sha256: `06d1ff983d6879cfbe13e700267f4d2f2d21dbc2136c5d062276a4a7dfced1d5`
- experiment_plan sha256: `b58ca30cca5c80b37df6875fe8534118fad3a4552b726304c926aa88640d058c`
