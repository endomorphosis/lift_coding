# HAO-050 Resolution

Date: 2026-05-25
Source finding: `docs/CONFIGURATION.md:334`

The scan excerpt pointed at the Virtual AI OS bootstrap section. Reviewing the
nearby documentation showed that the OpenAI API-key checklist had leaked two
numbered steps into the Virtual AI OS bootstrap flow, directly after the
bootstrap command block.

Resolution:

- Moved "Create a new API key" and "Add to `.env`" back under the OpenAI API-key
  setup checklist.
- Left the Virtual AI OS bootstrap section focused on submodule initialization,
  backlog validation, and supervisor worktree setup.

Validation:

- `test -f docs/CONFIGURATION.md`
