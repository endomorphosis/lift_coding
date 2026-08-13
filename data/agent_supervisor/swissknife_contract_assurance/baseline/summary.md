# SwissKnife Symbolic Contract Baseline

Snapshot `sca-repository-snapshot:sha256:8f7dfae2982620d57f256098f101d633824ac937cf85d398175a356f1c22f973` was materialised by the complete symbolic contract assurance baseline pipeline. The deterministic shadow scan made `0` LLM calls and mutated no tracked source or backlog state.

- Snapshot ID: `sca-repository-snapshot:sha256:8f7dfae2982620d57f256098f101d633824ac937cf85d398175a356f1c22f973`
- Repository index ID: `sca-repository-index:sha256:b1f5abd07f8f3e5dc3034e86d5b7e198b06d09464b57f91d196f59260bc30303`
- Graph root: `baguqeeraqgz5mgv7kjkfn3upzksm46h4mvqpcdbwjke4vu7ha2ynxa74ddva`
- Extraction / catalog roots: `baguqeerahzlmouauftmjlkwegcj6njpt7kzu3ihocehsfpm2ugnckqlrqvqa` / `baguqeeraqrg6ac7r7iu6thjwrd5l4oa62gzrr2yld5p6omzfa2p7hcdr2ikq`
- Analyzer health: `unhealthy` (index `unhealthy`)
- Safe for completion reasoning: `false`
- Tracked path dispositions: `6395` (tracked `6395`)
- Contract terminals: `3182` total (0 proved, 0 refuted, 3181 unknown, 1 unsupported, 0 stale)
- Claims: exhaustive=`false`, no_drift=`false`, no_findings=`false`
- Findings: `99` (root `sha256:4cbd72a62888ea25f057695c875cf4868860452286af9ddc8ad7ee0d976de1d5`)
- Model calls: `0`

## Pipeline stages

- Stage `repository_index`: `partial` (parser_failure_budget_exceeded, repository_index_unhealthy)
- Stage `extraction`: `complete`
- Stage `catalog`: `complete`
- Stage `graph`: `complete` (SymbolicContractGraphError, graph_projection_failed)
- Stage `invocation_trace`: `partial` (endpoint_anchors_partial, package_surfaces_omitted, typed_unknown_anchor_findings)
- Stage `proof_cache`: `withheld` (partial_analyzer_health_proof_not_started)
- Stage `mismatch`: `withheld` (mismatch_withheld_until_analyzer_healthy, no_parity_claims_to_classify)
- Stage `vulnerability`: `withheld` (no_mismatch_findings)

Unhealthy or incomplete stages withhold exhaustive, no-drift, and no-findings claims. An empty findings list is not evidence of contract parity while measurement is incomplete.

Reproduce with:

```sh
python3 external/ipfs_accelerate/scripts/index_repository_contracts.py --repo-root . --scope-config config/swissknife_symbolic_contract_scope.json --output-root data/agent_supervisor/swissknife_contract_assurance/baseline --shadow
```
