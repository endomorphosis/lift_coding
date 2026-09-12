# NS-013 Complete state-to-repair-to-certificate-to-publication witness

Generated at 2026-09-12T03:31:05+00:00. This is a sealed-profile qualification record of one integrated guard-before-write cycle. It is not a live A–D experiment, not a Groth16 proof of pytest execution, and not a live historical upstream repair.

## Task

A frozen genuine store operation wrote `write_record` before `authorize`. The authorized obligation is that a denied request leaves `persistent_state` unchanged for the declared observation profile `persistent_records_and_audit`. Schematic Table 6 labels R0/P0/T0 are replaced by the identifiers below.

- Task CID: `baguqeerayjn2552ymrf3qtqjbvfe43q5yequcbhmowkmaazqaabyo5xuntxq`
- Source tree: `cf4d4b77d0dc05c5983b62370b75330f84cbe7e8` / `ec8d7bceec58cd539744e94adcf6dd2c782408db`
- Policy CID: `sha256:f711f00ed99912349c04196f2348905f2c299cb72fccdef83b03154cc0339f39`
- Environment CID: `sha256:e4bc636d22e14b8fd6cc116b3cd5f288481df814cb5a9b5efb1cb5d2542f8580`
- Obligation ID: `baguqeera3w3hf2wk2sdlkm5jxw2m5ms3uy4xyrbxuyeadkwejyudiuyecj7q`
- Plan CID: `baguqeera3z3xeu3uo77qorfix7vbjr2vyvysrtmg6wryhhtmpckg5egqsjsq`
- Counterexample ID: `baguqeeralbumk3xpbnoqtrrejcfw4b3ulfwtcmire4u6t2dtpk5ib6zkre7q`

## Route change from symbolic/context evidence

Before the obligation was bound to exact source and a covering integrity unit, routing scored a model class. After the current source CID, obligation CID, and available proof were attached, `route_model` admitted `deterministic_only`. That change is the control decision; membership of a capsule is not.

- Route without bound evidence: `medium_model` reasons `['confidence_heuristic', 'context_within_small', 'dependency_cone_within_small', 'medium_model', 'proofs_absent', 'risk_medium', 'score_medium', 'unresolved_obligations_present']`
- Route with bound evidence: `deterministic_only` reasons `['confidence_exact', 'deterministic_only', 'proofs_cover_or_absent_obligations', 'risk_low']`
- Kernel disposition after unique analytical candidate: `analytical_unique_mapping`
- Residual without typed receipts: `missing_typed_resolvable_authority_receipts` (cannot dispatch)

## Valid permitted action and denied-effect repair

IsolatedPatchWorktree applied the guard-before-write patch in a fenced worktree (`lease_id=f8f1fb7930d000c5fd697a9b952b340f3f48ff37`). The caller root stayed on `ec8d7bceec58cd539744e94adcf6dd2c782408db`. Independent pytest on the worktree exited `0`. After repair, a permitted `alice/records.write` write still persisted, while a denied `mallory` request left records and audit unchanged. Exception paths still called `finalize`. The public `authorize`/`write_record` API was unchanged.

- Post tree: `9486efc2ed65852610a139a37e592e6d32c24dba`
- Patch digest: `sha256:96d5010b1879eff37c69e754c3687a88988be3518bc6296b48fa928d16077a53`
- Permitted write works: `True`
- Denied write persisted: `False`

## Rejected and incomplete paths cannot complete

The minimally altered invalid patch (write-before-check retained as a comment-only edit) did not repair the denied effect (`denied_write_persisted=True`). An empty requirement manifest while the obligation remained required returned `incomplete_manifest` and `sealed=false`. A simulated required unit returned `simulated_only` and was not published. None of those paths set operational completion.

- Invalid patch applied as success: `False`
- Empty/incomplete completion reported: `False`

## Publication

The complete requirement manifest (source integrity, denied-no-write, permitted-write, exception-finalization, API-scope) was parent-bound and CAS-published. The accepted post-root matches the repaired tree commitment.

- Parent seal: `ips.forest.genesis@1`
- Published seal: `sha256:1776714283057d562d41664641edbdaf36dd1fccae7b77d872368a630a5c7b73`
- Generation: `0`
- Manifest root: `sha256:eae100b04db3b4969f33a6e9ce91f43c2e825ffa7941dc15220895a3ab608964`
- Published: `True`

## Limitations

- Qualification, not a live A–D outcome and not a production LLM identity.
- Native Groth16 verification of pytest execution is not claimed; units are integrity-verified local receipts.
- Kit `proof_seal_store` and datasets incremental-sealing evidence remain shimmed as in NS-012.
- Public `semantic_state` package import loaded=`True`; anyio=`True`. Worktree/routing modules were still loaded as explicit files so the composition does not depend on package `__init__` side effects.
- Federation, libp2p/MCP transport, and external exactly-once side effects are not claimed.
