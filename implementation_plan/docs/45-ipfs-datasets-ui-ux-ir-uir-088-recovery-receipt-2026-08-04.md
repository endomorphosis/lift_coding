# UIR-088 recovery receipt — tool-free Grok proposal (2026-08-04)

## Failure

UIR-010 repair-grant attempt 5 passed correction authority, worktree, context,
and packet verification, then routed a 99,673-byte packet to the production
implementation provider. Event 2160 records a 100,616-byte / 25,154-token
request and a zero-byte `provider_failure`; event 2166 durably consumed attempt
5 as `sha256:88fbcaeabda51fb30bd2e6a46c6d8fe13aafd7bdf08fa9bca3ac1f95481c57da`.

The native Grok session proves that exact `grok-4.5` was selected. It then
called `run_terminal_command` to inspect the provider working directory. That
directory is deliberately empty because the bounded packet already contains
the entire authorized context. The command failed with “not a git repository,”
and `max_turns=1` cancelled the turn before a final structured proposal existed.

## Root cause and fix

The Grok argv used `--tools ""`. Grok interprets an empty allowlist as no
allowlist and restores its default tools. Accelerator commit
`8318799cbbbc837dc59da2883a680432269b1e00` replaces that ambiguous flag with an
explicit denylist covering all built-in proposal tools plus a deny-all
permission backstop. The provider remains proposal-only, receives no checkout,
and cannot invoke a tool.

The policy is unchanged: exact `grok-4.5` is primary; exact
`gpt-5.6-terra`/medium is reachable only after a native structured Grok HTTP
402 balance-exhaustion signal. Generic provider failure does not invoke Terra.

## Verification

- Production provider CLI suite: 53/53 passed.
- Contract packet provider router suite: 49/49 passed.
- Critical Ruff, Python compilation, and `git diff --check`: passed.
- Final supervisor daemon-port suite on accelerator commit
  `8318799cbbbc837dc59da2883a680432269b1e00`: 659/659 passed.
- An isolated copied-state pass, with networking disabled and implementation
  dispatch omitted, emitted exactly one `task_retry_budget_reset` for UIR-010,
  selected UIR-010, completed UIR-088, and left live state unchanged.

## Release

Completing this repair mints attempt 6 for UIR-010. It does not reuse attempt 5
and does not bypass the independent review gate.
