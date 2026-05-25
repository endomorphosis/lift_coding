# HAO-022 Policy Corpus Discovery

Date: 2026-05-25

## Scope

HAO-022 is a regression asset task, not a runtime mediation change. The existing
Hallucinate App control-surface modules already provide:

- strict template compilation in `control_surface_policy.py`,
- optional `ipfs_datasets_py.logic.api` fallback compilation,
- normalization adapters for voice, gesture, pointer/mouse, and agent events,
- deny-over-permit mediation in `control_surface_mediator.py`.

## Corpus Shape

The corpus fixture at
`hallucinate_app/python/hallucinate_app/test/fixtures/control_surface_policy_corpus.json`
keeps source rules, raw multimodal events, expected normalized intents, and
expected decisions in one reviewable file.

The harness intentionally uses the existing adapter entrypoints instead of
hand-building envelopes for the voice, gesture, pointer, and agent cases. That
makes the corpus catch drift in resolver behavior while staying independent of
browser, mobile, or daemon runtime setup.

## Upstream Logic Fallback

The NL compiler fallback cases use a fake object with the required public
`ipfs_datasets_py.logic.api` symbols. This keeps the unit regression deterministic
while still proving that unsupported strict-template rules route through the
general compiler lane, preserve upstream artifacts, and request clarification
when confidence falls below the configured threshold.

## Coverage

The corpus currently covers:

- strict compilation for quiet-hours wrist gesture suppression,
- strict compilation for confirmation before display activation and message send,
- general NL fallback for `Never let agents ...`,
- low-confidence clarification fallback,
- equivalent `display.activate` normalization across voice, gesture, mouse, and agent inputs,
- equivalent `display.focus_next` normalization across the same surfaces,
- quiet-hours deny mediation,
- deny-over-permit conflict precedence and explanation text.
