# Prospective bounded proof-assistance evaluation

This experiment measures proof acceptance for 64 constructed declarations whose
validity is known from elementary logic, arithmetic, and explicit countermodels.
It does not supply human semantic-fidelity labels for natural legal text.
The eight families contain four paired valid/invalid variants each. Renaming and
numeric variants within a family are correlated; bootstrap intervals resample
the eight families, not 64 supposedly independent natural examples. The five
previously constructed recovery declarations qualify serving and are excluded
from the new evaluation denominators.

The fixed declarations preserve all explicit premises, predicate identities,
types, and function interpretations. The temporal family concerns an explicit
single successor state, with an invalid two-step transfer control; it does not
measure arbitrary temporal-logic reasoning. Native Lean checks establish the
positive control proofs, Z3 and CVC5 separately check the negated first-order
claims, and invalid controls retain stated countermodels. Dependent and
higher-order claims are outside the bounded SMT translation fragment. Two
additional Lean theorems prove the negations of those invalid universal claims
using explicit Boolean/function countermodels, without any axioms; the typed
negative labels therefore also have native evidence.

## Compared arms

1. A deterministic Lean baseline uses the same six guarded core tactics as the
   repository Hammer reconstructor: `rfl`, `trivial`, `decide`, `omega`,
   `simp_all`, `assumption`. The final `done` in each branch forces backtracking
   when a tactic leaves a goal open. This is a direct bounded reconstruction
   baseline, not an execution of the full project Hammer service.
2. Bounded SMT-guided reconstruction first requires both Z3 and CVC5 to return
   `unsat` for the negated claim, then sends the same fixed reconstruction
   candidate to Lean. `sat`, unsupported fragments, and native reconstruction
   failures remain distinct outcomes. Solver agreement alone never counts as a
   Lean proof. This controlled implementation instantiates the Hammer pattern;
   it does not claim learned premise retrieval or certificate translation.
3. The locally cached Leanstral 1.5 NVFP4 model proposes one proof for the exact
   same declaration. A fixed prompt requests a proof body or `ABSTAIN`, with
   temperature 0, seed 20260914, and at most 1,024 tokens/60 seconds. There is no
   model-selected theorem rewriting, added premise, proof editing, tool use,
   candidate retry, or extraction of code from incomplete reasoning. A single
   enclosing Lean fence may be removed from a complete stop-terminated answer.
   The entire remaining body passes a syntax/identifier policy and Lean.

All model proof acceptances require successful elaboration of the fixed theorem
and its `#print axioms` report. Only Lean's standard `propext`, `Classical.choice`,
and `Quot.sound` axioms are permitted; `sorry`, `admit`, new axioms,
`native_decide`, executable metaprogramming, and theorem replacement are rejected.
Raw requests, responses, extracted proof bodies, Lean source, stdout/stderr,
return codes, and timing are saved. Rates use every declared goal. Truncation,
request errors, parser failures, and unrun goals never become proof successes.

## Serving correction

The local GGUF header has a Tekken tokenizer with BOS `<s>` and EOS `</s>`, but
contains no chat template. The earlier recovery responses emitted literal
ChatML turn delimiters. Inspection therefore identified a template mismatch,
in addition to the earlier 128-token truncation. The new template follows the
exact pinned upstream model's v15 tokenizer metadata and the official v15
encoder, with explicit `reasoning_effort: none` settings before `[INST]` and
`[/INST]` delimiters. The live `/apply-template` response must match the frozen
expected bytes before any qualification or evaluation request is sent.

Sources accessed 14 September 2026:

- [Exact upstream model revision](https://huggingface.co/mistralai/Leanstral-1.5-119B-A6B/tree/3fe4e64d70e6873420fe19108a3a61ec6a9f1460)
- [Pinned v15 tokenizer](https://huggingface.co/mistralai/Leanstral-1.5-119B-A6B/resolve/3fe4e64d70e6873420fe19108a3a61ec6a9f1460/tekken.json)
- [Official v15 encoder, mistral-common 1.11.5](https://github.com/mistralai/mistral-common/blob/v1.11.5/src/mistral_common/tokens/tokenizers/instruct.py)
- [Quantized model provenance](https://huggingface.co/Frosty40/Leanstral-1.5-119B-A6B-GGUF-NVFP4)

The upstream model card recommends temperature 1.0; this controlled comparison
instead fixes temperature 0 and explicitly reports that deviation. The local
quantization and short, single-request experiment do not estimate the vendor's
long-horizon agentic benchmark performance.

## Resource lifecycle

Only the existing bounded temporary runner may load the model. The permanent
service remains masked. Each job has a 900-second total deadline, a 360-second
startup limit, 90 GiB memory, four CPU cores, one model instance, and no swap.
The client stops starting requests after 490 seconds so completion and cleanup
fit within the total bound. A later bounded shard can resume untouched requests;
completed responses are never repeated or replaced. All actual attempts and
startup costs are retained. The runner removes the model process and transient
unit on completion, failure, timeout, or interrupt.
