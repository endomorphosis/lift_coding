# Temporary Leanstral jobs

`run_leanstral_ephemeral.py` starts Leanstral only for one client command, waits
for its own server to become healthy, runs the client, and removes its server
and child processes on completion, failure, deadline, SIGINT, or SIGTERM.
It never changes the existing masked `ipfs-accelerate-leanstral.service`.

The completed autoformalization natural-source evaluation used an effective
**10,000-second total wall limit** and a **360-second startup-readiness limit**.
All 100 attempts finished with the same model kept warm across client batches.
It was stopped at **09:04:49 UTC on 14 September 2026**; its server and
controllers exited, port 8080 closed, and the temporary override was removed.
Future natural workloads explicitly pass the same limits and keep one model
loaded until their client workload finishes:

```bash
python3 -B papers/revisions/autoformalization_empirical_20260914/assistance/launch_natural_warm.py --dry-run
```

Remove `--dry-run` to launch when no owned evaluation model is already active.
The launcher prints both limits explicitly and exits without loading a model
when all 100 planned attempts are complete. The completed September 14 run was
extended without restarting its model. Its retained original launch argument
records a 900-second wall; the superseding 10,000-second runtime override and
final cleanup are in
`papers/revisions/autoformalization_empirical_20260914/assistance/LIVE_RUNTIME_STATUS.md`.
The shorter command below is the historical recovery-probe example.

Run a read-only preflight before loading weights:

```bash
python3 -B scripts/run_leanstral_ephemeral.py \
  --preflight-only --wall-seconds 600 --startup-seconds 360 \
  --memory-gib 90 --reserve-gib 12 --cpus 4 --context 4096 \
  -- python3 -B scripts/autoformalization_recovery_probe.py --max-tokens 512 --output /tmp/leanstral-probe
```

Remove `--preflight-only` to run the bounded job. Give each real run a distinct
`--server-log /path/to/server.log` and client output path. Arguments following
`--` are executed directly, without a shell. Client stdin is closed, so the
client must be noninteractive. Exit 124 means a startup or job deadline; 125
means a preflight, server, or resource failure; otherwise the client's exit
status is preserved. A systemd-enforced deadline can instead return the
systemd-run failure status; the server log and stderr identify the cause.

For a GGUF without its own chat template, pass `--chat-template-file PATH`.
The runner validates the file, records its SHA256, and passes the explicit
Jinja argument to the server under both execution backends. The locally cached
Leanstral 1.5 GGUF needs its Tekken v15 template; the evaluation
template is in
`papers/revisions/autoformalization_empirical_20260914/assistance/leanstral_v15.jinja`.
Relying on generic ChatML framing caused malformed turns in the earlier pilot.
The corrected evaluation verifies the server's `/apply-template` result before
requesting proofs. Set an explicit template appropriate to the actual model;
an arbitrary model's chat framing is not interchangeable.

The client receives `LEANSTRAL_BASE_URL`, `LEANSTRAL_ENDPOINT`,
`OPENAI_BASE_URL`, and `IPFS_ACCELERATE_LLAMA_CPP_BASE_URL`, all ending in `/v1`.
`LEANSTRAL_MODEL=leanstral_local`. The IPFS Accelerate llama.cpp autostart
switches are explicitly disabled. Existing adapters with frozen endpoint
identities need the default port 8080. A port conflict is an error; the runner
does not kill or reuse the other listener. Readiness also checks that the
listening socket belongs to its own server tree. `--bind` defaults to
`127.0.0.1`. Pass `--bind docker0` (or the docker0 gateway IPv4) so a
bridge-network worker can reach the owner without a wildcard host bind. `0.0.0.0`
and `localhost` are refused.

## Limits and cleanup

The default `--backend auto` tests a transient user systemd unit with
`/usr/bin/true`. If supported, it runs both server and client in a unique,
automatically collected service with `RuntimeMaxSec`, `MemoryMax`,
`MemorySwapMax=0`, `CPUQuota`, `TasksMax`, `OOMPolicy=kill`, and
`KillMode=control-group`. No service is installed or enabled. A stopped or
killed invoking terminal cannot leave that service running beyond its hard
deadline. The worker also cleans up promptly when the client finishes.

If transient units are unavailable, the Linux process backend uses a separate
watchdog worker with a parent-death signal, a verified child subreaper, private
process sessions, inherited CPU/address-space/file limits and CPU affinity.
Every 100 ms it checks aggregate descendant RSS, task count, and host available
RAM. It adopts and kills double-forked or detached descendants and escalates
TERM to KILL after two seconds. This fallback is for trusted experiment
programs: polling limits can overshoot between checks, and its RAM/task limits
are not the kernel-enforced aggregate limits of a cgroup. Use `--backend
systemd` to fail closed when those stronger limits are required. No user-space
cleanup can immediately reap a process stuck in uninterruptible kernel I/O.

An exclusive per-GPU lock spans the whole job; CPU-only jobs share a separate
lock. The lock is inherited by the fallback worker or acquired inside the
transient service before the model is started. A second job fails rather than
loading another copy. Processes receive only the requested NVIDIA device in
`CUDA_VISIBLE_DEVICES`; `--gpu none` selects CPU execution explicitly.

## Sizing on this workstation

The September 14 inspection found 20 CPUs, approximately 121.7 GiB unified RAM,
an NVIDIA GB10, and a 62.52 GiB Leanstral NVFP4 GGUF. NVIDIA reports separate
VRAM capacity as unavailable on this machine, so preflight checks host unified
RAM and the selected GPU's presence. The estimate requires model bytes times
1.10 plus up to 4 GiB runtime headroom, as well as the requested host reserve.
This is an admission estimate, not a guarantee that a particular CUDA build
will fit; allocation errors remain failures and trigger cleanup.

Conservative defaults are 90 GiB memory, a 12 GiB host reserve, four CPU cores,
128 tasks, one GPU, 36 offloaded layers, context 4096, one parallel slot,
batch/ubatch 128/64, and no warmup. The generic CLI defaults are
`--wall-seconds 10000 --startup-seconds 360` when those arguments are omitted.
`--startup-seconds` is a readiness timeout, not the job wall bound; it is
counted inside `--wall-seconds`. The natural-evaluation launcher passes the
same pair explicitly. The historical recovery probe above uses 600 seconds
total and 360 seconds startup. An earlier live job was launched with a
900-second wall; that original argv is a frozen record and is not the current
default. Termination may take an additional three seconds for cleanup.

## Validation

```bash
python3 -B -m unittest discover -s tests -p test_leanstral_ephemeral.py -v
```

Tests use a tiny HTTP server and a dummy model file. They cover successful
inference-client lifecycle (without inference), client/server failures,
startup and client timeouts, interrupts, killed outer wrappers, detached
descendant cleanup, lock and port collisions, aggregate resource guards, and
read-only preflight. When available, a fake job additionally checks actual
kernel cgroup memory/CPU/task limits. No test loads Leanstral weights.

## Observed paper-recovery run

The first 180-second startup limit expired while loading the real model and
cleaned up correctly. One retry with 600 seconds total and 360 seconds startup
became ready after 251.469 seconds and completed five local requests. Both
temporary units and server processes were removed; the permanent service stayed
masked. The actual pilot used 128 output tokens and four responses hit that
limit. Its strict parser rejected all five; a separate post-hoc extraction of
the first assistant turn allowed Lean to verify two unedited proof bodies.
These are constructed runtime diagnostics, not a held-out efficacy result.
Use a deliberately frozen chat/termination and output-budget contract for the
full evaluation. Records are in
`papers/revisions/autoformalization_recovery_20260914/`.
