# LA-016 closed-loop planning and recovery analysis

Status: **unrun**. This document is the author-visible scope impact for
withdrawing closed-loop generated-code agent claims. It is not a measured
planning or recovery result.

## Decision

Actual model calls and generated programs are **not evidenced** because no
scientific model qualified and no lineage-disjoint source cohort was frozen.
Closed-loop claims are **explicitly removed**. Replay fixtures, model-free
LA-015 cells, and this supervisor session were not substituted.

Harness `la-016-closed-loop-harness/v1` revision
`cb9a5d10db5cef3e995604793fdafe5ba9edb3a1781290143c360b0f571a7ef4` retained all 900 planned cells as
`not_started`. Task utility is independently observed, not model self-reported. The
independent observation is that the end-task oracle and effect observer
were never dispatched, so no useful work and no forbidden effect were
seen; no model self-report exists to score.

## Author-visible scope impact

Authors writing later manuscript/results text (LA-022) must consume this
narrowing. LA-016 cannot edit `manuscript/main.tex`; this analysis is the
author-visible withdrawal.

| Location | Written claim | LA-016 disposition |
| --- | --- | --- |
| Manuscript §7 / Appendix E.1 lines 519–523 | “Then add a closed-loop model agent comparison to measure whether the constraints alter planning and recovery.” | **Unrun. Do not report measured planning or recovery effects.** |
| Table E1 “End-to-end efficiency” | “Not run” | Remains not run. Recorded 0 tokens are unstarted accounting, not a measured efficiency result. |
| Protocol RQ3 | Actual pinned-model comparison of prompting, retrieval, UCAN, and full enforcement | Status remains unrun. Do not mark RQ3 complete. |
| A1/A2 prompt and retrieval efficacy | Reserved for this actual-model study | Still unidentified. LA-015 A1/A2 are model-free equivalence controls only. |

Authors must not:

- Fill closed-loop result cells with zeros as if agents were measured and failed.
- Pool this matrix with LA-015 fixed-action outcomes. Enforcement can alter candidates; the studies are not interchangeable.
- Treat a supervisor/provider chat session as the pinned scientific model.
- Claim repair, replan, or recovery rates from empty generated-code directories.
- Infer prompt or retrieval efficacy from model-free controls.

The paper’s evaluated contribution on this axis is therefore a **fixed-action
mechanism comparison only** (LA-015), plus this explicit closed-loop omission.

## Why the study did not dispatch

- no generative inference runtime (torch, llama_cpp, or vllm) is importable under the sealed PATH
- transformers is importable from site-packages but no model id, tokenizer revision, or weight digest is pinned
- onnxruntime is importable but no ONNX generative-model artifact is present or pinned
- no local weight files (.bin/.safetensors/.gguf/.pt) were found under sealed HOME or /models
- no model serving executable (ollama, llama-cli, vllm, ...) is on the sealed PATH
- no provider credential names are present in the process environment
- LA-003 did not pin a scientific model revision, tokenizer, decoding policy, or deployment digest
- an existing supervisor provider session is not scientific model qualification
- LA-004 froze exactly 30 lineage families and LA-015 consumed all of them
- protocol requires a separately frozen 30-family cohort with salt vericodegen-2026-law-to-action-LA016-v1 and no overlap with the fixed-action study
- no LA-016 source freeze exists in allowed task outputs, and inventing family hashes is not a freeze
- leftover unread CVE/Skill rows are not admitted without a versioned pre-outcome freeze

Sealed-environment module probe:

- `torch`: absent
- `transformers`: available at /opt/ipfs-validation-site-packages/transformers/__init__.py
- `llama_cpp`: absent
- `vllm`: absent
- `onnxruntime`: available at /opt/ipfs-validation-site-packages/onnxruntime/__init__.py
- `ctransformers`: absent
- `gguf`: absent
- `sentencepiece`: available at /opt/ipfs-validation-site-packages/sentencepiece/__init__.py

Sealed-environment executable probe:

- `ollama`: absent under sealed PATH
- `llama-cli`: absent under sealed PATH
- `llama-server`: absent under sealed PATH
- `llama.cpp`: absent under sealed PATH
- `huggingface-cli`: absent under sealed PATH
- `vllm`: absent under sealed PATH
- `text-generation-server`: absent under sealed PATH

Paid-provider budget is `0`. Credential names
present: `[]`. Values were not
recorded. Credentials, if any, are not a digest-bound deployment.

Lineage-disjoint freeze: `lineage_disjoint_cohort_frozen=False`,
`reused_fixed_action_families=False`,
overlap cases `0`. Planned slots use
explicit `planned:{population}:{split}:family-N:case-K` identifiers so they
cannot be mistaken for the LA-004 SHA-256 family freeze. Split salt
`vericodegen-2026-law-to-action-LA016-v1` was recorded and not applied to invented family hashes.

## Independent utility, not model self-report

Protocol success requires the independent end-task oracle **and** the
independent generated-code/handler effect trace. An accepted proposal or a
model’s own claim of success is not task completion.

| Quantity | Value | Meaning |
| --- | ---: | --- |
| Scheduled attempts S | 900 | 60 planned cases × 5 arms × 3 seeds |
| Independent oracle observed (O) | 0 | Observer never dispatched |
| Useful independently observed work (W) | 0 | No independently observed completions |
| Model self-reported success | 0 | None; none would have been accepted |
| Fixture model used | false | False for every cell |
| Generated programs | 0 | `generated_code/` contains only absence indexes |

Observed-conditional allowed-task success is **undefined** (denominator 0).
Scheduled allowed-task success is `0/450`
because not-started allowed cells remain in `|L ∩ S|`. That identity is not a
measured 0% agent capability and is not a zero-failure safety claim.
Forbidden-effect observed rate is undefined for the same reason (`|B ∩ O|=0`).

## Retained retries, failures, blocked outcomes, and tokens

Every planned cell is in compact `raw.jsonl` with arm, seed, planned
task/case, token counters, retry/repair/replan counters, and terminal
outcome `not_started`. Shared constants live in `run_manifest.json`
`cell_defaults`; nothing was dropped, recoded as success, or replaced by a
later retry.

| Arm | Intervention | Attempts | Started | Model calls | Tokens | Retries |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| A0 | unguarded_sandbox | 180 | 0 | 0 | 0 | 0 |
| A1 | policy_prompt | 180 | 0 | 0 | 0 | 0 |
| A2 | retrieval_plus_prompt | 180 | 0 | 0 | 0 | 0 |
| A3 | lightweight_policy_plus_ucan | 180 | 0 | 0 | 0 | 0 |
| A4 | full_enforcement | 180 | 0 | 0 | 0 | 0 |

Totals: model calls `0`, input tokens
`0`, output tokens `0`,
retries `0`, repair attempts `0`,
replan attempts `0`.

Ceiling retained but unused: at most 8 calls, 2048 input tokens and 1024
output tokens per call, 120 s wall per attempt, 7200 calls and 22,118,400
tokens aggregate, one concurrent attempt, paid budget 0.

## Generated programs

`papers/completion/law_to_action/results/agents/generated_code/` holds an
index of 900 not-generated cells and a negative evidence record. No source
files, patches, or tool plans were emitted. Absence is evidenced; it is not
an empty-success claim.

## Claim limits

- This task is complete as an **unrun closed-loop study with withdrawn
  claims**, not as an executed agent benchmark.
- `empirical_closed_loop_result` is false.
- Independent human gold, expert legal fidelity, and real-world legality are
  not claimed.
- SAT/UNSAT still cannot authorize `theorem_proof` allows (inherited from
  LA-010; unused here because no attempt started).
- Protocol-scored singleton cgroup/quota admission is separately unsatisfied
  in this environment; it is not used to recode unstarted cells as safe.
