# SwissKnife symbolic contract baseline

Snapshot `sca-repository-snapshot:sha256:1bfd265e8f77ee187b9b9095ec863e1e8b91a97e46044d9633cc733cd4a0a10f` has complete tracked-path coverage but only partial analyzer health. The deterministic shadow scan made zero LLM calls and mutated no tracked source or backlog state.

- Scope policy root: `sca-scope-policy:sha256:642af3ddb46fd9a18aaec135e1153525359afadf85b1a102613d5ce02c8eefbd`
- Capability root: `sha256:4bb4aab44dcd8fc6c2a93023c04cc8fef47bf51f7a7c7fbeefa5c5ac382088c3`
- Repository index / graph roots: `sca-repository-index:sha256:ffc1d858e3b3a9093315ac585640b180ebfdc8cf344f2bfecad06df19c849d37` / `analysis-ast-index:sha256:1da20ec35f1c44036ab4b7304cdb59f0183cd70a7d4f1a692aa6b817c0294dc3`
- Contract extraction / catalog roots: `baguqeera672apquwndxpdkt6bkhholcqq7gx6yu2czaeurkfrbx52kutrtqq` / `baguqeeratqitoq5dblj53rtkad5bvbkx7k7shntbb5lev5e43qs7bemdfbgq`
- Parent commit / tree: `4204af6566d35631eab27ea8a5acde7d0f648ece` / `0a64563cc013fe7f29f29609ceeaad2e9a3d7068`
- Parent snapshot root: `sca-parent-snapshot:sha256:11bd222fc8ed1ab413835d759e9253c72cdd0aee39eb6adf86fd4ba202d60265`
- SwissKnife commit / tree: `b34fadb6edb66e834ea3dff9a463fb2b175feef5` / `378b87bd963ada1e81443c5ee07ba599c607570c`
- Recursive submodule inventory root: `sha256:b76b9f3691b6d8bfbb08a75eed1b2823aa3ee40a14e289c85ca65f2adb8c2e98` (60 entries)
- Tracked paths disposed: 5,771 of 5,771 (100%)
- Allowlisted overlay dispositions: 1 (excluded `node_modules` dependency directory)
- Contract terminals: 2,676 total (2,675 `unknown`, 1 `unsupported`)
- Finding: `unsupported` analyzer health due to `parser_failure_budget_exceeded`
- Proof / cache outcome: not started / published but unhealthy
- LLM calls: 0

Repository indexing completed, but its health is `unhealthy`: 2,830 parser attempts failed, including 2,701 because the local TypeScript compiler API was unavailable. Static extraction still found 2,675 reviewed contracts and all three canonical packages, but observed-contract matching and proof remain unmeasured.

Overall analyzer health is therefore `partial` and unsafe for completion reasoning. This baseline makes no exhaustive, no-drift, or no-findings claim and promotes no optional-provider result to authority.

Reproduce with:

```sh
python3 external/ipfs_accelerate/scripts/index_repository_contracts.py --repo-root . --scope-config config/swissknife_symbolic_contract_scope.json --output-root data/agent_supervisor/swissknife_contract_assurance/baseline --shadow
```

The expected result for this exact initialized snapshot is exit code 0 with `health_status` equal to `unhealthy`, snapshot root `sca-repository-snapshot:sha256:1bfd265e8f77ee187b9b9095ec863e1e8b91a97e46044d9633cc733cd4a0a10f`, and index root `sca-repository-index:sha256:ffc1d858e3b3a9093315ac585640b180ebfdc8cf344f2bfecad06df19c849d37`. Partial health is a typed blocker, never permission to claim exhaustiveness.
