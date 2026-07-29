# SwissKnife Symbolic Contract Baseline

Snapshot `sca-repository-snapshot:sha256:1bfd265e8f77ee187b9b9095ec863e1e8b91a97e46044d9633cc733cd4a0a10f` was materialised by the complete symbolic contract assurance baseline pipeline. The deterministic shadow scan made `0` LLM calls and mutated no tracked source or backlog state.

- Snapshot ID: `sca-repository-snapshot:sha256:1bfd265e8f77ee187b9b9095ec863e1e8b91a97e46044d9633cc733cd4a0a10f`
- Repository index ID: `sca-repository-index:sha256:ffc1d858e3b3a9093315ac585640b180ebfdc8cf344f2bfecad06df19c849d37`
- Graph root: `baguqeerauzkvyy3kplluuziywof3u57xq2yztsqvgiwcexdq2lrwskzmhh3q`
- Extraction / catalog roots: `baguqeera4exjfpvtqa7l23x4zqfsgiduqpwvv3plbzvri2r3a25ozp2hyeuq` / `baguqeera4zkbcpgvmdnvvorsumdqm6n244wjdz4f6wzuzm43rop4vpynuf5q`
- Analyzer health: `partial` (index `unhealthy`)
- Safe for completion reasoning: `false`
- Tracked path dispositions: `unknown` (tracked `unknown`)
- Contract terminals: `3182` total (0 proved, 0 refuted, 3181 unknown, 1 unsupported, 0 stale)
- Claims: exhaustive=`false`, no_drift=`false`, no_findings=`false`
- Findings: `1` (root `sha256:e85f474a190c8d76ef73a77a13980323f3a12dd37b9fb2a6a3ac69e77d657c46`)
- Model calls: `0`

## Pipeline stages

- Stage `repository_index`: `partial` (repository_index_not_provided)
- Stage `extraction`: `complete`
- Stage `catalog`: `complete`
- Stage `graph`: `complete`
- Stage `invocation_trace`: `withheld` (analyzer_unhealthy)
- Stage `proof_cache`: `withheld` (observed_contracts_unavailable, partial_analyzer_health_proof_not_started)
- Stage `mismatch`: `withheld` (mismatch_withheld_until_analyzer_healthy, no_parity_claims_to_classify)
- Stage `vulnerability`: `withheld` (no_mismatch_findings)
- Stage `publish`: `complete`

Unhealthy or incomplete stages withhold exhaustive, no-drift, and no-findings claims. An empty findings list is not evidence of contract parity while measurement is incomplete.

Reproduce with:

```sh
python3 external/ipfs_accelerate/scripts/index_repository_contracts.py --repo-root . --scope-config config/swissknife_symbolic_contract_scope.json --output-root data/agent_supervisor/swissknife_contract_assurance/baseline --shadow
```
Prior SCA-120 repository index root `sca-repository-index:sha256:ffc1d858e3b3a9093315ac585640b180ebfdc8cf344f2bfecad06df19c849d37` remains the coverage authority for this snapshot; SCA-200 re-ran extraction, catalog, graph, and typed terminal assignment without LLM calls.
