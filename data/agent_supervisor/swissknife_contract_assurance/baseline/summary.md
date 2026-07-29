# SwissKnife symbolic contract baseline

Snapshot `sca-repository-snapshot:sha256:7607147c58f1d036683b10de53f5efee61bee2af9ccd8b805788fd9095fdd3d4` has complete tracked-path coverage but only partial analyzer health. The scan made zero LLM calls and mutated no tracked source or backlog state.

- Scope policy root: `sca-scope-policy:sha256:642af3ddb46fd9a18aaec135e1153525359afadf85b1a102613d5ce02c8eefbd`
- Capability root: `sha256:45c7498e697f1de5cc099877d7924b7f7ca5abe23e4620b849df5bda439a7409`
- Contract extraction/catalog roots: `baguqeera672apquwndxpdkt6bkhholcqq7gx6yu2czaeurkfrbx52kutrtqq` / `baguqeeratqitoq5dblj53rtkad5bvbkx7k7shntbb5lev5e43qs7bemdfbgq`
- Parent commit/tree: `b0d76a7266377665a8999a3f7ec294f64495e7b2` / `741c2d821054182109af2572a4b61c12254f8af8`
- SwissKnife commit/tree: `b34fadb6edb66e834ea3dff9a463fb2b175feef5` / `378b87bd963ada1e81443c5ee07ba599c607570c`
- Recursive submodule inventory root: `sha256:85b777b9dec4468ab996372d7bfb864a474bbad49a35a470da6783de3b6c5541` (60 entries)
- Tracked paths disposed: 5,771 of 5,771 (100%)
- Contract terminals: 2,676 total (2,675 `unknown`, 1 `unsupported`)
- Finding: `unsupported` at the uninitialized `swissknife` primary gitlink
- Proof/cache outcome: not started/not finalized
- LLM calls: 0

Analyzer health is `partial` and is not safe for completion reasoning. This baseline therefore makes no exhaustive, no-drift, or no-findings claim and promotes no optional-provider result to authority.

The independently reproducible clean primary inventory confirms one exact disposition for all 5,771 tracked paths. Static extraction found 2,675 reviewed contracts and all three canonical packages; observed-contract matching and proof remain unmeasured because the repository index was not published.

Reproduce with:

```sh
python3 external/ipfs_accelerate/scripts/index_repository_contracts.py --repo-root . --scope-config config/swissknife_symbolic_contract_scope.json --output-root data/agent_supervisor/swissknife_contract_assurance/baseline --shadow
```

The expected fail-closed result in this leased worktree is exit code 2 with `RepositoryPathEscapeError`. Against an initialized checkout at the same primary commit, the stock loader additionally exposes a tracked-symlink identity mismatch and a 21,537,678-byte structured source beyond the 16 MiB parser bound; these remain typed health blockers rather than permission to claim exhaustiveness.

## Retry validation

The SCA-120 retry at parent `4204af6566d35631eab27ea8a5acde7d0f648ece` reran the command above and reproduced exit code 2 with `RepositoryPathEscapeError` before any output write. Independent validation of the admitted artifacts confirmed:

- all 5,771 tracked SwissKnife paths have one unique, clean disposition;
- the snapshot, scope-policy, capability, coverage, contract, and finding commitments recompute exactly;
- all 2,676 contracts use a declared terminal status;
- partial health keeps exhaustive, no-drift, and no-findings claims false;
- proof and cache work remain unstarted and unfinalized; and
- LLM, optional-provider promotion, source mutation, and backlog mutation counts remain zero.

The retry does not rewrite the baseline JSON merely to bind a later supervisor merge: those artifacts intentionally remain committed to the captured parent/primary snapshot above.

## Final repair validation

Repair round 3 initialized the pinned `swissknife` gitlink and established a
durable, identity-matched cache entry for the tracked symlink and the
over-bound structured source. The exact validation command then completed
with exit code 0 and published repository index
`sca-repository-index:sha256:967c42e7987d8c0bbeac0173628c90c65426316893bd043ee29512bd27a6bcb0`
for snapshot
`sca-repository-snapshot:sha256:1bfd265e8f77ee187b9b9095ec863e1e8b91a97e46044d9633cc733cd4a0a10f`.

That run disposed all 5,771 tracked paths and emitted 5,772 rows including one
allowlisted overlay. All 3,070 parser-eligible paths received a terminal
index outcome, but 2,830 were typed parse failures. The resulting parser
failure ratio was 0.9218241042345277 against the reviewed maximum of 0.01;
canaries passed, Git-root discovery was complete, and the analyzer health
therefore remained `unhealthy` and unsafe for completion reasoning. The run
made zero LLM calls and changed no tracked source or backlog state.

The stock command's expanded repository-snapshot serialization is 3,822,303
bytes, above both the 1,000,000-byte single-file admission limit and the
2,000,000-byte patch limit. It is therefore retained only in the ignored
durable index and does not replace this baseline's admitted 575,496-byte
compact coverage commitment. No exhaustive, no-drift, or no-findings claim is
made.
