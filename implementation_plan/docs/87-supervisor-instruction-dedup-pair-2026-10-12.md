# Full-supervisor token comparison and numerical projection — 2026-10-12

Both fresh `largest-eigenval` trials passed Terminal Bench's official verifier.
The full supervisor with instruction deduplication used **309,813 native
tokens versus 311,776** for the full baseline, **0.63% fewer** in this pair.

| Observation | Full baseline | Instruction dedup |
| --- | ---: | ---: |
| Official passes | 1/1 | 1/1 |
| Planning tokens | 25,461 | 25,612 |
| Coding tokens | 286,315 | 284,201 |
| Total tokens | **311,776** | **309,813** |
| Cached input, included above | 236,800 | 234,624 |
| Uncached input | 69,141 | 69,109 |
| Output, including reasoning | 5,835 | 6,080 |
| Agent execution | 249.83 s | 283.82 s |
| Outer execution including setup and cleanup | 619.59 s | 1,310.29 s |

Most of the reduction was cached input. Uncached input fell by only 32 tokens,
while output increased by 245; provider cost is unknown. The second deployment
took substantially longer, and agent execution was also slower. Independent
plans and cache history differ, so this single pair does not establish causal
or repeatable savings.

Deduplication actually selected, with no fallback. Its complete coding input
shrunk from 66,818 to 65,850 bytes, a 968-byte reduction (1.449%). The separately
planned baseline input was 66,486 bytes. Both native input reconstruction
audits passed. All four planning/coding CLI sessions are counted: **621,589
tokens** across the two retained runs. Provider-free preparation failures are
retained separately. Both native tasks and shutdowns completed, and owned
containers were observed absent twice.

The experiment used `llm_router`, the qualified GPT-6.1 Sol/high Codex fallback,
CLI 0.160.0, lexical capsules, ordinary completion, identical checkpoint and
archive, 5 CPUs/20 GiB, and zero retries. It compares two full-supervisor
variants; native Codex-harness and no-index trials were not rerun. The setup
cache now supports the existing formalization profile, preserving independent
preparation/planning/coding budgets and unchanged admission thresholds. The
fix passed 138 tests; preparation passed 27 independent checks, runtime reviews
21 and 23, final pair review 20, and current reporter regression fixtures 23.
A qualified task-name mismatch in the first offline reporter was corrected
with the existing exact task-name/path matcher; the failed report is retained.

The live runs exposed two formalization gaps. Source384 consumed its pinned
checkpoint, but all four sampled functions were unsupported and none were
source-aligned. IntentIR failed open without a checkpoint and supplied no
learned advice. The selected SecurityIR and IntentIR validators have narrow
scalar grammars; additional weights alone cannot support these numerical
functions or the free-form benchmark instruction. The current setup-cache
layout also excludes additional learned Intent/numerical assets.

After both timed runs closed, the existing deterministic numerical path was
tested on only the permitted public `eigen.py` and `eval.py` files. In **8.06
seconds without models or target-code execution**, it linked all four functions
to IR and structurally translated two. It emitted 45 pending obligations, two
eigenpair contracts and four assertion requirements, then reopened and replayed
the metadata/world DuckLakes in a fresh process. Both generated Lean modules
compiled; a missing-premise negative correctly failed. Six abstract SMT checks
returned SAT. **Zero source correctness obligations were discharged.** The
independent probe review passed 17 checks, including unchanged benchmark inputs.

The next integration work is an opt-in numerical structural profile with
bounded retrieval of the unresolved obligations, broader validated IntentIR
grammar, and qualified packaging for additional checkpoints. The current
8,192-byte summary retains source links, compound contracts, and assertions,
but omits individual obligation rows and three per-function summaries with
explicit omission counts. Those omissions must not be treated as proof.

Measured source pins are accelerator `c3d4f873acdb62fd5b124328b3e3f28accd8dbdb`
and datasets `c1b1f65f254f5f3ee8f307cdddf923c62450f78e`. The verified archive is
`96aa70a6e10667ee9ca6d54a8baaae2a18378cdab22414c3bb32cc9fd65ed607`.
Later publication preserves concurrent repository work; it does not relabel
the immutable runs as newer code. This publication pins accelerator
`d86f3c3724949ca630656d525288f87e9db0fdb5` and preserves the concurrent
datasets pin `c18390b350c7ab40f5bd342578204a03dc34fe05`.

The [detailed evidence](https://github.com/endomorphosis/ipfs_accelerate_py/tree/d86f3c3724949ca630656d525288f87e9db0fdb5/docs/agent_supervisor/evidence/terminal-instruction-dedup-pair-20261012)
contains bounded observations, independent reviews, exact generated logic,
solver results, retained failures, and a hash manifest. Raw provider transcripts,
credentials, owner databases and model/runtime payloads are excluded.

Local documentation gates passed after the concurrent merge. The hosted
[documentation-gates job](https://github.com/endomorphosis/ipfs_accelerate_py/actions/runs/38208558857/job/114677389912)
could not start because GitHub reports an account billing lock; this is not
a successful hosted check or a code-test failure.
