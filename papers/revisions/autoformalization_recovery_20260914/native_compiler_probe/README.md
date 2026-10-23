# Native compiler and legacy autoencoder qualification

The existing `lift_coding/.venv/bin/python` can import `multiformats` and run the actual `TypedDeonticCanonicalCompiler` from `external/ipfs_datasets`. No dependency installation or implementation replica was required.

## Constructed compiler inputs

Six newly constructed examples were sent through the public `CompilerRequest` API with one fixed caller-supplied vocabulary. The compiler used its native `DeonticConverter`, with `use_ml=False`, cache/IPFS/monitoring disabled, and no fallback.

| Constructed input | Native result | Observed output |
| --- | --- | --- |
| Company A shall submit backup report. | success | O(company_a, submit, backup_report) |
| Company A may submit backup report. | success | P(company_a, submit, backup_report) |
| Company A must not submit backup report. | success | F(company_a, submit, backup_report) |
| The agency shall not file notice. | abstained | Unrepresented procedure facet |
| The agency is not required to file notice. | abstained | Unmapped actor and unrepresented procedure facet |
| Company A shall submit backup report within 10 days unless emergency. | success | O with emergency exception and within_10_days temporal field |

Four successful compilations and two typed abstentions are retained in `native_compiler_result.json`, including all source maps, receipts, diagnostics, and module origins/hashes. The negated-obligation probe did not assert an obligation, but its abstention is not counted as successful semantic interpretation. These constructed checks establish callable native behavior and its limitations, not an empirical paper result.

Completed in 6.274 seconds, with 37.78 MiB peak RSS. No network, service binding, or subprocess attempts occurred. The process exited.

An initial attempt on CPUs 0–1 reached the external timeout and was killed (exit 137); no result receipt was produced. A subsequent attempt using CPUs 18–19 completed. The cause of the first timeout was not established. `root_venv_bounded.json` preserves an intermediate probe receipt whose *summary* read the wrong output dictionary key (`ir` instead of `canonical_ir`); its full native payloads were correct. The final receipt comes from a rerun after fixing that probe-only key. No external implementation changed.

## Actual legacy checkpoint load

`legacy_autoencoder_result.json` records a successful load through the unmodified `load_frozen_autoencoder_guidance` API in the Portland repository. It verified the exact SHA-256/CID and exported **64 stable learned features**, with zero sample examples and no sample memory or target-embedding selection. Checkpoint bytes were unchanged after loading.

Completed in 2.673 seconds, with 367.89 MiB peak RSS. This confirms usability of the recovered 25.9 MB checkpoint. It does not establish autoformalization efficacy or implement the missing causal IR adapter.

Both scripts impose a 60-second outer timeout, 55-second internal alarm/CPU soft limit, two-CPU affinity, and 8 GiB address-space ceiling. Environment variables disable GPU, ML downloads, and autoinstall; Python audit hooks reject network connections, listening sockets, and child-process execution. These probes started no model service and both probe processes exited. No AF029 multi-gigabyte checkpoint or final-test example was opened.

## Reproduce

```sh
timeout --signal=TERM --kill-after=2s 60s /home/barberb/lift_coding/.venv/bin/python -B probe.py --repo /home/barberb/lift_coding/external/ipfs_datasets --output native_compiler_result.json

timeout --signal=TERM --kill-after=2s 60s /home/barberb/lift_coding/.venv/bin/python -B probe_legacy_autoencoder.py --repo /home/barberb/portland-laws.github.io/ipfs_datasets_py --checkpoint /home/barberb/portland-laws.github.io/ipfs_datasets_py/archive/workspace/todo-queues/legal-ir-daemon-restart12-20260608T075001Z-best-8h-autoencoder.state.json --output legacy_autoencoder_result.json
```

Run from this directory. The compiler caller example can be reused for development qualification without touching frozen experiment inputs. Any final evaluation still requires its own frozen source-only consumer and results protocol.
