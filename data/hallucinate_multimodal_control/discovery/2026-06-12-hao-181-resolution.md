# HAO-181 Resolution

Date: 2026-06-12
Task: HAO-181
Source finding: `hallucinate_app/hallucinate_app/experiments/webnn-developer-preview/demos/whisper-base/whisper.js:232`
Evidence: `/home/barberb/lift_coding/data/hallucinate_multimodal_control/discovery/2026-05-27-hao-181-codebase-scan-249bb3d996f7.md`

## Finding

The scanner found an unresolved annotation:

```js
// TODO: CHANGE FROM HARDCODED VALUES
```

The current file no longer contained that exact annotation, but the decoder
setup still had hardcoded initial prompt length, attention-mask dimensions, and
logits shapes in the same generation path.

## Resolution

The decoder setup now derives those values from local model state:

1. Initial decoder prompt length comes from `WHISPER_INITIAL_PROMPT.length`.
2. The first decoder attention mask is generated from the prompt length instead
   of a fixed 4x4 literal.
3. Greedy token selection uses each logits tensor's `dims` rather than fixed
   `[1, 4, 51865]` and `[1, 1, 51865]` shapes.
4. The generated-token count and cached decoding loop use `this.num_init_tokens`.
5. Special token IDs are resolved through the loaded tokenizer with documented
   whisper-base fallbacks for compatibility.

## Validation

```bash
test -f hallucinate_app/hallucinate_app/experiments/webnn-developer-preview/demos/whisper-base/whisper.js
```

Result: passed.
