# Proof-assistance results — 14 September 2026

All 64 prospective constructed requests completed, after five separate historical
qualification requests. The unchanged frozen comparison contains 32 valid and 32
invalid declarations in eight semantic families. Each family contributes four
paired variants; these are family clusters, not 64 independent natural examples.

| Method | Valid proofs accepted by Lean | Invalid proofs accepted | Other scope |
|---|---:|---:|---|
| Fixed Lean core tactics | 32/32 (100%) | 0/32 | All 64 attempted |
| Bounded SMT-guided reconstruction | 24/32 (75%) | 0/32 | 16 dependent/higher-order instances unsupported; 24 counterexamples |
| Leanstral 1.5 NVFP4, frozen admission policy | 12/32 (37.5%) | 0/32 | All 64 model responses retained |

The model produced 12 accepted proofs, 30 abstentions, 15 policy rejections, five
native rejections, and two token-limit truncations. The paired difference from
the deterministic baseline on valid goals is −62.5 percentage points; a 2,000-draw
bootstrap over eight semantic families gives a 95% percentile interval of
[−90.625, −28.125] points. This describes the small constructed suite and protocol;
it is not evidence about general legal source fidelity or the model's published
agentic benchmark performance.

The model proposed directly against each fixed declaration without additional
premises, theorem changes, proof editing, tool calls, or candidate retries. Raw
requests/responses and all checker outcomes remain available. Positive labels
have native Lean control proofs. The first-order negative labels have matching
Z3/CVC5 counterexample dispositions; separate Lean countermodel theorems verify
the two negative typed families outside that solver fragment.

The result includes admission-policy friction. Two rejected responses used the
valid core tactic `rw`, and four used an unlisted local binder name. A clearly
separate posthoc diagnostic admitted only `rw` and `safe_x` and checked the six
original proof bodies without edits or model calls. Three additional valid
proofs passed the kernel, and no invalid proof did. The diagnostic combined
coverage is 15/32; the prospective primary result remains 12/32.

The 64 new model requests used 9,470 prompt tokens and 6,056 completion tokens,
with 259.897 seconds total request wall time. Five qualification requests are
excluded from those denominators. The successful job loaded for 281.246 seconds.
An earlier corrected-template startup stopped before inference because the
server applies BOS during tokenization rather than exposing it as template text;
its full load/cleanup cost is preserved separately. Token-level qualification
then verified BOS/settings/instruction token IDs before any proof request.

The bounded service has exited, port 8080 is closed, and the permanent service
remains masked. Cgroup accounting is retained in resource_observations*.jsonl;
its memory.peak describes charged cgroup memory and must not be described as
total unified GPU/model memory. All jobs had 900 second wall and 90 GiB cgroup limits.
