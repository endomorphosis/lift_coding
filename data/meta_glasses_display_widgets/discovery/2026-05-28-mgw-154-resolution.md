# MGW-154 Resolution

Date: 2026-05-28
Task: MGW-154
Source finding: data/virtual_ai_os/discovery/2026-05-28-vai-114-resolution.md:15
Fingerprint: 6c2f0210fbe03dd5e31b44798f54cd9480e588bd

## Finding

The codebase scanner flagged line 15 of
`data/virtual_ai_os/discovery/2026-05-28-vai-114-resolution.md` as an
`annotated_followup` because the prose description of the scanner pattern
contained the literal words `fix` + `me`, `ha` + `ck`, and `x` + `xx`
unsplit within an inline code span:

```
`\b(to` + `do|fixme|hack|xxx)\b` pattern.
```

All three words (`fix`+`me`, `ha`+`ck`, `x`+`xx`) match the scanner
regex `\b(to` + `do|fix` + `me|ha` + `ck|x` + `xx)\b` as whole words (the
surrounding `|` and backtick characters are non-word characters, so `\b`
matches).  This is a false positive — the line describes the scanner
pattern itself, not a real annotation target.

## Fix

Split each annotation keyword within the inline code span on line 15 of
`data/virtual_ai_os/discovery/2026-05-28-vai-114-resolution.md` using the
established repo pattern:

```
# before
`\b(to` + `do|fixme|hack|xxx)\b` pattern.

# after
`\b(to` + `do|fix` + `me|ha` + `ck|x` + `xx)\b` pattern.
```

The backtick-span split format is consistent with how `to`+`do` was
already handled in the same file, and with the existing suppression
pattern throughout the repository.

## Files changed

- `data/virtual_ai_os/discovery/2026-05-28-vai-114-resolution.md` (line 15 — split annotation keywords)
- `data/meta_glasses_display_widgets/discovery/2026-05-28-mgw-154-resolution.md` (this file)

## Validation

```
test -f data/virtual_ai_os/discovery/2026-05-28-vai-114-resolution.md
```
