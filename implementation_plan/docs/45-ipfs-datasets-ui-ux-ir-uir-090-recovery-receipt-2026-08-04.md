# UIR-090 recovery receipt — Grok backend X-tool isolation (2026-08-04)

## Failure

UIR-010 attempt 7 used exact `grok-4.5` with a 99,673-byte typed packet and
the native CLI's `--disable-web-search`, explicit built-in tool removals, and
deny-all permission rule. Grok's backend X tools are outside those generic
surfaces: the session made eleven calls across `x_keyword_search`,
`x_semantic_search`, `x_user_search`, and `x_thread_fetch`, reached the
300-second provider bound, and returned no proposal that the supervisor could
admit.

The supervisor failed closed. It wrote no files, made no commit, queued no
merge, and recorded `fallback: false`; the generic provider failure did not
authorize Terra. Attempt 7 is durably consumed by event
`sha256:5bf145a01cfc1779e9b49f4de8020ea280215c4642063569bdfbb45137c67394`,
sequence **2285**.

## Bound evidence

- Provider receipt SHA-256:
  `e1d1dad22a8a858f6c297fe840c8f38d2b948690b964ae25db6eafbdb11ccb60`.
- Grok session summary SHA-256:
  `05dc663fe72fed8607faf21b4311f7e3ae63e005dab367369e7d7b1e76827b1b`.
- Grok session ACP updates SHA-256:
  `ed6c9e8c8c2ead4ee2737c32c37d49b95cd9f5ce0387a7c8cee14bde661a8213`.
- Grok session summary records model `grok-4.5`; the updates contain eleven
  completed search calls and no workspace-write tool.

The session artifacts remain local and may contain provider content; their
digests preserve the evidence binding without committing that content.

## Fix and release condition

- Remove `x_search`, `x_keyword_search`, `x_semantic_search`, `x_user_search`,
  and `x_thread_fetch` from the Grok proposal surface.
- Reject any streaming Grok transcript that nevertheless contains a tool-call
  event, so newly introduced backend tools cannot produce an admitted proposal.
- Cover terminal `structuredOutput`, legacy `text`, direct schema objects,
  empty terminal envelopes, and tool-bearing transcripts with regressions.
- Preserve exact `grok-4.5` primary routing and authorize exact
  `gpt-5.6-terra` with medium reasoning only after the native structured Grok
  HTTP 402 balance-exhaustion signal.

Completing this repair mints attempt **8** for UIR-010. It does not reuse or
rewrite attempt 7.
