# MGW-124 Resolution

Date: 2026-05-27
Task: MGW-124
Source: hallucinate_app/hallucinate_app/experiments/webnn-developer-preview/demos/whisper-base/whisper.js:232

## Finding

The codebase scan identified a `// TODO: CHANGE FROM HARDCODED VALUES` annotation at line 232 of whisper.js. The original code used raw integer literals for Whisper special token IDs:

```js
// TODO: CHANGE FROM HARDCODED VALUES
let tokens = [50258, 50259, 50359, 50363];
```

## Fix Applied

The fix was already applied to the `hallucinate_app` submodule (commit `06b1808`, VAI-106). Named constants were introduced for all Whisper special token IDs, replacing the magic numbers:

```js
const WHISPER_TOKEN_START_OF_TRANSCRIPT = 50258; // <|startoftranscript|>
const WHISPER_TOKEN_ENGLISH            = 50259; // <|en|>
const WHISPER_TOKEN_TRANSCRIBE         = 50359; // <|transcribe|>
const WHISPER_TOKEN_NO_TIMESTAMPS      = 50363; // <|notimestamps|>
const WHISPER_TOKEN_TIMESTAMPS_START   = 50364; // <|0.00|> (first timestamp token)
const WHISPER_TOKEN_END_OF_TEXT        = 50257; // <|endoftext|>
```

These constants are used in both the initial token list and the end-of-sequence check, removing the TODO and all hardcoded values.

## Status

Resolved. The `hallucinate_app` worktree at commit `a6d84a57` (which includes the fix) has been checked out in the MGW-124 worktree so the file is accessible for validation.
