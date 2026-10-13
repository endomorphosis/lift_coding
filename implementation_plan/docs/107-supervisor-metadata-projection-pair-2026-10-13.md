# Supervisor metadata projection: complete native comparison — 2026-10-13

Accelerator `49b01d2515f338af73f8c14a96bbf235e339e4bd` adds a strict comparison helper and tests for
the existing lossless metadata projection, plus a completed native Docker pilot.
The projected view **did not reduce total tokens**: 313,980 versus 313,979. It
passed Terminal Bench; the baseline failed one speed requirement. This is one
independently planned pair, not evidence that compression caused better success.

| Full supervisor, GPT-6.1-sol through `llm_router` | Legacy | Common bindings |
| --- | ---: | ---: |
| Official `largest-eigenval` reward | 0 | 1 |
| Input tokens, including cached input | 307,795 | 307,597 |
| Cached input tokens, subset of input | 250,112 | 250,112 |
| Uncached input tokens | 57,683 | 57,485 |
| Output tokens | 6,184 | 6,383 |
| Total native tokens | **313,979** | **313,980** |
| Agent setup seconds | 256.70 | 734.25 |
| Agent execution seconds, including planning/indexing | 291.14 | 345.89 |

Each arm made one planning and one coding invocation. Cumulative usage is
counted once per invocation; billing dollars remain unverified. The treatment
used 198 fewer input tokens and 199 more output tokens. Its within-invocation
coding projection reduced the complete prompt from 68,006 to 67,124 bytes.
Independent planning prevents treating cross-arm prompt lengths as a controlled
byte difference. No retry incorporated official verifier feedback into the
frozen treatment inputs. Retained declared-output observations lack final-file
hashes, so cross-arm output equality remains unverified; future generic-task
runs should export authorized output hashes before removing the container.

- [Implementation, interpretation and next reductions](https://github.com/endomorphosis/ipfs_accelerate_py/blob/49b01d2515f338af73f8c14a96bbf235e339e4bd/docs/agent_supervisor/context_projection_pair.md)
- [Public evidence and native usage scope](https://github.com/endomorphosis/ipfs_accelerate_py/blob/49b01d2515f338af73f8c14a96bbf235e339e4bd/docs/agent_supervisor/evidence/context-projection-pair-20261013/README.md)
- [Previous source-view experiment](104-supervisor-source-view-read-edit-pair-2026-10-13.md)

Both arms used Codex CLI 0.160.0, high reasoning, exact source profile
`identity@1`, the same Source384 checkpoint, task inputs and extended
formalization budget. Their full configurations differ only in metadata mode
and output directory. Runtime archive
`6426e1a06dbea6182c245bd8f96ec367103e25d674fdf578432a7a5832ed0918`
and immutable host adapter `2c220ae4b7c79ad9980122c3329ebdf9ef4131a3`
were fixed before execution. The archived offline helper predates its final
tested version; it is not invoked by the live supervisor, whose production
source closure is independently verified.

The baseline passed correctness checks and failed one performance check.
The treatment passed official verification. Both supervisors reported internal
completion, which must remain separate from benchmark success. Both consumed
Source384 and decoded four unsupported/unverified candidates, with zero
target-training steps. IntentIR failed open without a checkpoint, and both
models made zero optional source-reader requests. This profile therefore does
not establish verified source proofs or the benefit of the complete trained
multi-IR system.

An earlier Grok baseline stopped at isolated credential readiness, with zero
generation calls and no reward. Pinned CLI 1.0.46 and installed 1.0.52 both
rejected fresh copied credentials; host authentication was unchanged. The
prepared Grok treatment was not executed. The separate Codex pair retains both
outcomes and complete native usage. Its treatment setup was longer because an
ARM64 CLI package download succeeded after 466.976 seconds. No installer
timeout or intervention occurred. A verified local copy was identified for a
future matched offline setup.

The provider-free Docker pair separately fixes the entire authored workload:
same prompt, source reader, 11 logical operations and 12 CLI calls. Lossless
metadata factoring reduced one-pass prompt plus displayed CLI text from
79,362 to 78,477 UTF-8 bytes, **885 bytes (1.12%)**. Both program bodies were
already deferred; three support files remained inline. No additional
source-omission profile was implemented. The retained codec round trip and
source/edit replay establish this text measurement, not model-token savings.

Validation: **289 regression tests passed**, including 52 new comparator cases.
Local documentation and explicit link/anchor checks are retained with the
evidence. Raw model prompts, source-bearing full traces, private state,
credentials, databases and runtime binaries remain excluded. The next
controlled changes are exact policy/pack-field factoring with all overhead
charged, trained IntentIR wiring and wider verified numerical source coverage.
Their estimated byte reductions are not additive or established token savings.

This publication preserves datasets `5723a541c5d575b88f01532e4d241dc95a1f3e99`
and kit `8ac00bb1974b1378e12091d546d8425af34049e0`; it updates the accelerator
pin, this report and the earlier report's source-admission correction.
Qualification used datasets `f47161b757190380e9898aff155067c1ad609217`, not
every later change in the preserved parent pin. Exact-commit hosted CI and
parent checks are recorded in the publication artifacts.

The [hosted CI observation](../../artifacts/context-projection-pair-publication-20261013/hosted-ci.json)
and [parent checks](../../artifacts/context-projection-pair-publication-20261013/parent-checks.json)
retain the exact publication bindings.

Hosted documentation CI for this exact accelerator commit was blocked by an
account billing lock before a runner was assigned or any steps executed. Local
checks passed; hosted checks did not execute.
