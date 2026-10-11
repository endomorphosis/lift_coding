# Supervisor complete-prompt token measurement

The opt-in common-bindings selector can now use an existing token-counting
callable with a declared provider/model/tokenizer/revision profile. The runner
checks the pinned provider and model before invoking that callable. Compact
input requires fewer bytes and fewer counted tokens; an unavailable or invalid
counter keeps the original input. Default byte-proxy selection and historical
`@1` receipts remain unchanged.

The complete measured strings include the literal workspace, public instruction,
Doctor and reply instructions. Provider-added system/tool/schema messages,
output tokens and billing remain outside this preflight scope. A declared
`provider_tokenizer` qualification is not authenticated simply by hashing it.
Census counts both inputs once, hashes textual profile identities and stops
before provider discovery. Benchmark comparison retains representation
observations beside native usage without charging them to the token ledger.

Historical `@2` audits reconstruct recorded delivery even without the matching
callable, but leave counter and selection verification false. With the same
independently supplied counter, replay checks exact identities, counts and
selection. A foreign provider/model counter never receives the retained prompt.

The implementation preserves the parallel task-bound formalization delivery
work published in accelerator revision `dedf13a42c2b2c32131b4b10f659dd51830a6083`.
It reuses the existing codec, context estimator, receipt and accounting owners.
No new model, embedding, decoder checkpoint or database owner is created.
LegalIR, SecurityIR, CodebaseIR and IntentIR keep distinct family, schema/version,
decoder-task, dimension and token-profile namespaces. The retained 8D, 384D and
768D paths remain available independently of the coding provider tokenizer.

## Remaining qualifications

1. Inventory actual accepted formal receipts and repeated status material through
   the existing proof-cache owner. Recheck source/dependency bindings and keep
   native verdicts and unresolved obligations explicit before replacing status
   material with a capsule.
2. Qualify a reviewed provider/model/tokenizer/revision factory and deterministic
   replay. The coding CLI still uses its named byte proxy; programmatic counter
   injection alone is not a qualified live benchmark profile.
3. Qualify read-only `capsule.get` and `source.get` against the existing current
   owner before progressive disclosure. Current verified capsule readers, sealed
   source materialization and bounded symbol queries are reusable; the coding
   route lacks a qualified expansion tool and Quack lacks these admitted
   operations. Require scoped host grants, task/source/root/context bindings,
   owner generation/fence, current workspace checks after edits, exact bounded
   response populations, unresolved frontier and bound continuation.
4. Build a new qualified runtime archive before a trial. Keep the original
   planning session, task inputs, reply schema and route controls; vary one
   qualified treatment and retain failed/unknown attempts.
5. Decide success from complete native input/output totals, including lookup,
   continuation and repair attempts, plus verifier reward and completion. Keep
   provider-specific cache and cumulative-session accounting intact. No live
   savings have been established by this implementation.

The maintained accelerator
[token-reduction plan](https://github.com/endomorphosis/ipfs_accelerate_py/blob/575227d831fd6c4bd53948cab75b63a5b486dda7/docs/agent_supervisor/terminal_token_metadata_plan.md)
contains the detailed measurement and lookup boundaries.

The [qualification record](../../artifacts/supervisor-token-counter-20261011/qualification.json)
retains **307 distinct passing checks** against current datasets revision
`cdae06198a229760ca139d48f9e311e80d0df8c6`, normal pytest AST sealing, the exact
source digests and test logs. The initial run passed 301 checks and stopped at
one missing Harbor dependency; the six remaining controls then passed using the
existing Harbor 0.23.0 installation. No tests were skipped. Local documentation
workflow checks passed, including all 46 maintained relative-link surfaces.
GitHub's documentation job could not start because the account is locked due
to a billing issue; the record preserves that remote limitation separately.
