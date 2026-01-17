# PR-027: Profile-based summary verbosity tuning

## Goal
Implement real profile-based verbosity tuning for PR summaries and responses, moving beyond placeholder logic.

## Background
The system supports user profiles (commute, workout, kitchen, focused, relaxed) in the command processing pipeline, but the actual summary verbosity and response formatting is not yet fully tuned based on these profiles.

Current state:
- Profiles are accepted in `/v1/command` requests
- Router recognizes profiles in client_context
- Response generation doesn't yet adapt verbosity or format based on profile

## Scope
- Define verbosity levels for each profile:
  - **workout**: Ultra-brief (1-2 sentences max, key numbers only)
  - **commute**: Brief (2-3 sentences, essential info)
  - **kitchen**: Moderate (3-4 sentences, conversational)
  - **focused**: Minimal interruption (brief, actionable items only)
  - **relaxed**: Detailed (full context, all details)
  - **default**: Moderate (balanced detail)

- Update PR summary generation (`pr.summarize` intent):
  - Apply verbosity rules to summary text
  - Adjust card count and detail level based on profile
  - Keep critical information regardless of profile (e.g., security alerts)

- Update inbox listing (`inbox.list` intent):
  - Adjust item count and detail based on profile
  - Filter or prioritize items based on profile preferences

- Add tests for profile-specific response formatting

## Non-goals
- Advanced NLP-based response generation
- User-specific customization beyond profiles (that's future work)
- Complex multi-turn conversation tuning
- Audio playback speed adjustment (that's client-side)

## Acceptance criteria
- `pr.summarize` with profile="workout" returns 1-2 sentence summaries
- `pr.summarize` with profile="relaxed" returns detailed summaries
- `inbox.list` with profile="focused" prioritizes actionable items
- Profile handling is tested for each intent
- Default behavior (no profile) remains unchanged
- Tests remain green

## Implementation notes
- Add verbosity configuration in `src/handsfree/profiles.py` (new module)
- Update intent handlers in `src/handsfree/commands/router.py` to use profile config
- Update PR provider's summary generation to accept verbosity hints
- Add helper functions for text truncation and filtering based on profile
- Document profile behaviors in tracking doc or API docs

## Related PRs
- PR-004: Command router (profiles accepted but not fully used)
- PR-005: GitHub readonly inbox and summary (current PR summarization)
