# Supervisor token-efficiency controls — 2026-10-12

The supervisor now has an opt-in representation that removes the duplicated
instruction text from semantic metadata while keeping its full admitted
verbatim requirements block inline. It also supports source-verified retrieval
ranking for capsules and reports all-attempt native tokens/cost per official
pass. Planning and the `llm_router` route remain in place.

Implementation: `ipfs_accelerate_py` commit `7a00a0875b3d887183f77d2db5b819e7db7fd96d`. This parent integration
preserves the concurrent scoped header-proof changes. Dataset and Kit pins
remain `fd4be4da2a3976a8e40f47d7337cebb6332c95f3` and
`8ac00bb1974b1378e12091d546d8425af34049e0`; no model checkpoint changed.

## Input reduction measured offline

| Authored signed instruction | Complete native bytes | Candidate bytes | Selected bytes |
| --- | ---: | ---: | ---: |
| Large | 31,807 | 27,574 | 27,574 |
| Tiny | 18,713 | 18,847 | 18,713 |

The large fixture reduced complete input bytes by 4,233 (13.31%). The tiny
fixture retained native input because the candidate was larger. These inputs
include workspace mapping and the full signed public instruction. The signed
admission, indexing, router preparation and audit are real local paths; the
coding provider reply is authored. This is not a live provider token saving or
new Terminal Bench score.

## Implemented behavior

- Prepare a full experiment with
  `--semantic-metadata-view common-bindings-instruction@1` and original semantic
  transport `@1`. Current archive and signed instruction bindings are required.
  Exact restoration, complete-input comparison, token-counter failure fallback,
  no-provider census and historical audit are retained. Legacy is the default.
- Programmatic `prepare_initial_context(retrieval_ranked_capsules=True)` replays
  the exact indexed source/query and maps hits to native symbol/span identities
  before selecting capsules. Required raw source, admission and budgets remain
  enforced. Historical replay uses retained sources/AST/query and never claims
  they are current.
- Observed efficiency divides all supplied retained attempts, including
  failures, by official reward-1 passes. Unknown rewards, incomplete usage/cost
  and zero passes leave the affected ratio unavailable. Reported cost is not
  treated as verified billing.

## Qualification

**786 distinct host tests passed with no skips**, with tracked source hashes
unchanged. A fresh archive verified all 12,266 actual members against its
manifest and current source. Both metadata modes passed the 38-helper policy
closure. All **10 signed instruction tests also passed in offline Docker**
against the extracted production archive, in the cached r2 image with network
disabled, 5 CPUs/12 GiB, read-only root/sources, and no credentials, downloads or
live providers. Those Docker tests repeat host cases. The owned container was
removed and all 12,287 tracked source/test/control files remained unchanged.

The generated script for Docker attempt 01 had an escaping error and failed
before imports; the corrected script compiled and passed attempt 02. Both
receipts are retained. Actual module origins, commands, logs, JUnit, source
hashes and numerical observations are in the
[qualification bundle](https://github.com/endomorphosis/ipfs_accelerate_py/tree/7a00a0875b3d887183f77d2db5b819e7db7fd96d/docs/agent_supervisor/evidence/terminal-token-efficiency-20261012).
Archive/model/database bytes are not committed. Local supervisor documentation,
relative links, packaging pins and diff checks passed. GitHub checks are a
separate status and are not represented as green by these local results.

Exact-commit GitHub Documentation Gates and Serving Contract Gates concluded
failure before execution: "The job was not started because your account is
locked due to a billing issue." Ten failed checks with annotations reported the
same billing issue; one cached-workflow example was still queued at observation.
[Retained CI observations](../../artifacts/supervisor-token-efficiency-20261012/github-p/qualification.json)
identify the exact commit and checks. No workflow retry was requested.

## Remaining experimental boundary

Ranked successors explicitly refuse before partial preparation until fresh
retrieval is generated before successor capsules. This profile has no new
benchmark CLI flag. The ordinary full-supervisor path supports the instruction
treatment. Retained historical artifacts must remain available for replay.
Similarity, byte reduction and syntactic replay do not prove program correctness
or token savings.

The next matched benchmark should change only instruction deduplication while
holding tasks, provider/model, planning, reply contract and budgets fixed. Keep
all attempts, official verifier rewards, total native tokens, wall time and
reported cost. Evaluate ranked capsules separately after successor refresh is
integrated; proof-cache reuse and progressive Quack disclosure remain distinct
experiments. No full new deployment or live Terminal Bench qualification is
claimed by the offline Docker smoke.
