# VAI-104 Resolution

Date: 2026-05-27
Task: VAI-104
Source finding: `hallucinate_app/hallucinate_app/experiments/webnn-developer-preview/demos/whisper-base/generation_utils.js:52`
Evidence: `/home/barberb/lift_coding/data/virtual_ai_os/discovery/2026-05-27-vai-104-codebase-scan-af1c8f84f823.md`

## Review

The scan evidence flagged a hardcoded branch in `get_new_tokens` that treated
the first decoder pass specially when the sequence length was exactly four. The
function already receives logits dimensions, so the token selection can be
derived from shape instead of from a Whisper-specific initial prompt length.

## Resolution

`get_new_tokens` now computes the vocabulary width and sequence length from the
provided logits shape, validates that the helper is decoding a single batch, and
slices the logits for the last sequence position. This keeps the current
`[1, 4, 51865]` and `[1, 1, 51865]` paths equivalent while supporting any
single-batch sequence length.

## Validation

```bash
test -f hallucinate_app/hallucinate_app/experiments/webnn-developer-preview/demos/whisper-base/generation_utils.js
```

Result: passed.

```bash
node --input-type=module - <<'NODE'
import { get_new_tokens } from './hallucinate_app/hallucinate_app/experiments/webnn-developer-preview/demos/whisper-base/generation_utils.js';

const tokenFromSeq2 = get_new_tokens(Float32Array.from([1, 9, 2, 3, 10, 4]), [1, 2, 3]);
if (tokenFromSeq2 !== 1) {
  throw new Error(`expected token 1 from last row of seq=2 logits, got ${tokenFromSeq2}`);
}

const tokenFromSeq1 = get_new_tokens(Float32Array.from([5, 4, 6]), [1, 1, 3]);
if (tokenFromSeq1 !== 2) {
  throw new Error(`expected token 2 from seq=1 logits, got ${tokenFromSeq1}`);
}
NODE
```

Result: passed.
