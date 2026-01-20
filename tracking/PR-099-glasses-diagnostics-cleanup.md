# PR-099: Glasses diagnostics cleanup (remove commented legacy blob)

## Why
`mobile/src/screens/GlassesDiagnosticsScreen.js` contains a very large commented-out “legacy implementation” block.

This bloats the file, makes it harder to review/maintain, and duplicates the existing backup file `GlassesDiagnosticsScreen.original.js`.

## Scope
- Remove the large commented-out legacy block from `mobile/src/screens/GlassesDiagnosticsScreen.js`.
- Keep a short note pointing to `GlassesDiagnosticsScreen.original.js`.
- No runtime behavior changes.

## Acceptance Criteria
- The commented legacy block is removed from `mobile/src/screens/GlassesDiagnosticsScreen.js`.
- The active exported component behavior is unchanged.
- Repo still passes tests.
