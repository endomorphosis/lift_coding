# SwissKnife symbolic contract baseline

Snapshot `sca-repository-snapshot:sha256:7607147c58f1d036683b10de53f5efee61bee2af9ccd8b805788fd9095fdd3d4` has complete tracked-path coverage but only partial cold-scan analyzer health. The scan made zero LLM calls and mutated no tracked source or backlog state.

- Scope policy root: `sca-scope-policy:sha256:642af3ddb46fd9a18aaec135e1153525359afadf85b1a102613d5ce02c8eefbd`
- Capability root: `sha256:45c7498e697f1de5cc099877d7924b7f7ca5abe23e4620b849df5bda439a7409`
- Coverage ID: `sha256:84294eb74bfc53fe2b88ce255290e72aeff0d765900212ed8c01427722adc286`
- Findings root: `sha256:cb6e36d2f437138c51907981fd1a416a3078ad7b4401b8ae6573d08af11ba392`
- Contract extraction/catalog roots: `baguqeera672apquwndxpdkt6bkhholcqq7gx6yu2czaeurkfrbx52kutrtqq` / `baguqeeratqitoq5dblj53rtkad5bvbkx7k7shntbb5lev5e43qs7bemdfbgq`
- Parent commit/tree: `b0d76a7266377665a8999a3f7ec294f64495e7b2` / `741c2d821054182109af2572a4b61c12254f8af8`
- SwissKnife commit/tree: `b34fadb6edb66e834ea3dff9a463fb2b175feef5` / `378b87bd963ada1e81443c5ee07ba599c607570c`
- Recursive submodule inventory root: `sha256:85b777b9dec4468ab996372d7bfb864a474bbad49a35a470da6783de3b6c5541` (60 entries)
- Tracked paths disposed: 5,771 of 5,771 (100%)
- Contract terminals: 2,676 total (2,675 `unknown`, 1 `unsupported`)
- Terminal status domain: `proved`, `refuted`, `unknown`, `unsupported`, `stale`
- Finding: `unsupported` at the uninitialized `swissknife` primary gitlink
- Proof/cache outcome: not started/not finalized
- LLM calls: 0

Analyzer health is `partial` and is not safe for completion reasoning. This baseline therefore makes no exhaustive, no-drift, or no-findings claim and promotes no optional-provider result to authority.

The independently reproducible clean primary inventory confirms one exact disposition for all 5,771 tracked paths. Static extraction found 2,675 reviewed contracts and all three canonical packages. Observed-contract matching and proof remain unmeasured in the admitted cold-scan evidence because that scan did not publish an index; the later unhealthy validation index is cache evidence only and is not promoted to contract authority.

Validate the compact baseline with:

```sh
PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets:external/ipfs_kit python3 external/ipfs_accelerate/scripts/index_repository_contracts.py --repo-root . --scope-config config/swissknife_symbolic_contract_scope.json --output-root data/agent_supervisor/swissknife_contract_assurance/baseline --shadow
```

The exact command exits 0 after the pinned `swissknife` checkout and its verified incremental CAS are present. On the clean tracked snapshot it publishes index `sca-repository-index:sha256:578c812adc6b7054831d4c7aba4ca74951f5978a7742f4e0c232cce3d114a712` with all 5,771 rows and a 100% cache-hit ratio. Analyzer health remains `unhealthy`: 2,830 of 3,070 eligible paths are typed parse failures (`parser_failure_budget_exceeded`), so the successful process exit does not authorize exhaustive, no-drift, or completion claims.

The compact admitted files retain the cold-scan blockers that required the incremental bootstrap: an uninitialized primary gitlink, tracked-symlink identity mismatch, and a 21,537,678-byte structured source beyond the 16 MiB parser bound. The raw 3.8 MiB snapshot emitted by the validator is deliberately not retained because the same 5,771 canonical disposition identities are committed here below the single-file admission limit.
