# HAO-179 Resolution

Date: 2026-05-27
Task: HAO-179
Source finding: `hallucinate_app/hallucinate_app/experiments/webnn-developer-preview/demos/whisper-base/generation_utils.js:52`
Evidence: `/home/barberb/lift_coding/data/hallucinate_multimodal_control/discovery/2026-05-27-hao-179-codebase-scan-af1c8f84f823.md`

## Finding

The scanner found an unresolved TODO at line 52 of `generation_utils.js`:

```js
// TODO, remove hardcode
if (dims[1] == 4) {
    for (let i = 0; i < dims[2]; i++) {
        scores.push(logits[dims[2] * (dims[1] - 1) + i]);
    }
} else {
    for (let i = 0; i < dims[2]; i++) {
        scores.push(logits[i]);
    }
}
```

The hardcoded check `dims[1] == 4` assumed the logits tensor was always shaped
`[batch, 4, vocab_size]`, which fails for variable-length sequences and is not
robust to other batch configurations.

## Resolution

The hardcoded branch was replaced with a general implementation that:

1. Validates that `dims` has at least 2 dimensions.
2. Derives `vocab_size`, `sequence_length`, and `batch_size` from the trailing
   dimensions of the `dims` array, supporting tensors of any rank ≥ 2.
3. Validates the derived dimensions before indexing the buffer.
4. Uses `Array.from(logits.slice(...))` with a computed offset to extract the
   scores for the last sequence position, which is the correct token to predict.

The fixed implementation handles any `[..., sequence_length, vocab_size]` shaped
logits tensor without hardcoding the sequence length axis.

## Validation

```bash
test -f hallucinate_app/hallucinate_app/experiments/webnn-developer-preview/demos/whisper-base/generation_utils.js
```

Result: passed.
