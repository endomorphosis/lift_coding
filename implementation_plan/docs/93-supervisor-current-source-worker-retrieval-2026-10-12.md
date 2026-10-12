# Exact source retrieval from coding workers — 2026-10-12

The native exact-source reader previously supported an authenticated host child,
but coding-worker shell descendants could not reuse its grant. A new explicit
session bridge keeps one source-only grant in the original native state-owner
process. The public descriptor and protected `source-lookup` helper let successive
shell processes retrieve admitted byte ranges using that same native grant.

This continues the [whole-source inventory](87-supervisor-retained-source-inventory-2026-10-12.md),
[reversible read-only views](88-supervisor-reversible-source-views-2026-10-12.md)
and [native current-source reader](90-supervisor-current-source-lookup-2026-10-12.md).
The parallel [numerical worker channel](91-supervisor-numerical-worker-retrieval-2026-10-12.md)
and [semantic source-view worker](92-supervisor-worker-source-views-2026-10-12.md)
are retained with their independent admission and pending-proof status.

The bridge takes an existing ready `QuackStateServer`, retained source CAS,
canonical repository, actual allocated Git worktree and exact implementation
prompt. The native source gateway must already be bound to that allocation.
It creates no additional database, CAS owner, embedding or model checkpoint.
Its descriptor publishes all admitted regular-file path/CID references, with
at most 32 files and 8 KiB of metadata; overflow refuses rather than truncating.

Socket peers must have the isolated worker UID and descend from the actual
launched child process birth. A matching UID or descriptor is insufficient.
Before returning source, the bridge checks the original native task revision,
body, owner, grant and retained inventory, then both canonical and allocated
working source. The first profile requires clean committed regular files and
refuses reads after edits. The model-facing result strips native owner/store
records and credentials. It grants no proof, edit, omission or completion
authority. Filesystem checks remain sequential observations without a writer
lease.

The deployed helper uses isolated Python and protected deployment imports.
The router checks the descriptor against the original prompt, workspace and
container boundary, verifies the helper, adds exact invocation guidance and
rechecks admission before provider dispatch. Public environment selection exists
only during that invocation and is restored on success or failure. Ordinary
tasks without explicit source flags retain their previous prompt and route.

Requests have an 8 KiB complete envelope limit. Responses have a 32 KiB complete
JSON-plus-LF limit, with a separate four-byte-prefix wire count. Each session
allows 64 connections and 524,288 prepared response bytes. Native backend success
envelope bytes are recorded separately, including responses later refused by a
freshness check. Native errors and handshake traffic remain outside that ledger;
missing provider token usage is unknown. Byte counts are not token savings.

## Qualification

All **537 distinct merged host regression cases passed**, with no failures, errors or
skips, normal pytest plugins/AST sealing and unchanged source hashes. These
include 21 new channel/router controls, actual native 512-byte and 4,096-byte
pagination, numerical retrieval and worker-deployment regressions, plus the imported semantic
source-view and shared numerical-broker controls. The disjoint 247-case and
290-case inventories are explicitly joined. Earlier
dependency/fixture failures remain separately recorded and are not added to the
passing count.

A fresh container exercise after merging the parallel source-view publication
used an authored provider response, real UID1000
owner and UID1001 worker, unchanged owner entry, actual router and protected
helper subprocesses. Three inert fixture files (UTF-8/CRLF text, binary and empty)
reconstructed exactly: 5,716 source bytes across eight primary pages, delivering
17,322 complete JSON-plus-LF bytes. Eleven distinct helper processes shared one
native grant. The full exercise recorded 13 requests, nine successes and four
refusals, with 20,904 prepared worker response bytes. Backend validated-success
envelopes recorded 33,421 bytes, or 33,448 with their frame prefixes; native
handshake/error traffic remains unknown.

Owner-UID and unrelated worker-UID peers were refused. Canonical and allocated
edits invalidated reads; exact restoration admitted a fresh read. Private owner
paths were unreadable to the worker. The original grant was revoked, the service
stopped, its descriptor/socket removed and all three owned test containers removed.
Source and qualification-runner hashes were unchanged during the successful run.

This source-only exercise used the existing legacy reply arm. The modern
`ordinary-completion@1` route requires the separate sealed semantic-repository
context and remains unqualified by this fixture. No model/provider/solver was
called, no source was executed, and no official verifier/reward, live model tool
choice, full automatic supervisor binding or total token improvement is claimed.

## Remaining integration and measurement

1. Connect the trusted opt-in factory to the normal admitted-task allocation
   lifecycle, preserving the original task/body/context and allocated source
   binding. The current native gateway has one binding per lifetime; multi-task
   use needs an explicit reviewed lifecycle rather than silent rebinding.
2. Admit changed working overlays under fresh inventory/task evidence. The
   current clean-source profile deliberately refuses old-context reads after
   coding edits. Restart and cancellation must preserve incomplete accounting.
3. Reuse the concurrently published semantic source-view worker channel for
   compact navigation and exact-original expansion. It has its own semantic
   source admission, 64-file/1 MiB population bounds and 8 KiB response budget;
   those identities do not substitute for native task-revision custody. Add
   capsule operations separately. Reuse the published numerical-obligation
   reader; retrieved pending obligations remain pending until checked.
4. Qualify accepted edits of compact views back into exact public source, then
   test execution equivalence. Unchanged inverse reconstruction, source lookup,
   mapped edits and execution equivalence are distinct outcomes.
5. Rebuild the actual coding archive and observe a live model invoking the
   helper. Keep required facts inline until coverage and access are established.
6. Compare controlled full supervisor sessions with planning enabled. Count all
   native planning, coding, lookup, retry, continuation and repair input/output
   tokens, official rewards, failures and unavailable usage. Avoid counting
   cache/reasoning subsets twice; byte reduction alone is insufficient.

LegalIR, SecurityIR, CodebaseIR and IntentIR assets remain separate by family,
schema/version, decoder task and 8D/384D/768D profile. Existing embeddings,
inventories and decoder weights are preserved. This retrieval stage neither
replaces semantic reconstruction evaluation nor starts new distillation.

The combined accelerator publication is `514d1d21102284b6787b6ff6752ee1a60660411b`. The
[integration guide](https://github.com/endomorphosis/ipfs_accelerate_py/blob/514d1d21102284b6787b6ff6752ee1a60660411b/docs/agent_supervisor/source_lookup_worker.md)
and [qualification evidence](https://github.com/endomorphosis/ipfs_accelerate_py/tree/514d1d21102284b6787b6ff6752ee1a60660411b/docs/agent_supervisor/evidence/source-lookup-worker-20261012)
retain exact commands, disjoint test identities, source/artifact hashes, failed
attempts and scoped container results. The merge includes parallel source-view
publication `21457b554254b48b51930fa1a5d39cd563fe1bef` and preserves datasets
`f47161b757190380e9898aff155067c1ad609217`. Its software_contracts subtree equals
the earlier sealed c18390b3 source inventory checkout; both are retained.

All four exact local documentation workflow blocks and changed-guide links
passed after the merge. The exact-commit
[hosted documentation job](https://github.com/endomorphosis/ipfs_accelerate_py/actions/runs/38287993694/job/114940875083)
did not execute any steps: GitHub reports an account billing lock. The
[retained CI observation](../../artifacts/source-lookup-worker-publication-20261012/hosted-ci.json)
records that infrastructure result separately from the passing local checks.
