# Deterministic Contract Repair Operations

- Release id: `release:7bffac45912b7c09`
- Interface: `DeterministicRepairRelease@1`
- Auto-safe boundary: `auto_safe`
- Operator policy root: `sha256:75f8736d78f8ea7366f71a0d07a05e37df1e1e0bf723cce414494089835769ba`
- Runtime model calls: `0`

## Pins

- **Mcp-Plus-Plus**: `6965f89f066769f3b3ac7b5f753b1a0044562570`
- **bootstrap_seal**: `config/deterministic_contract_repair_bootstrap_seal.json`
- **bootstrap_seal_sha256**: `sha256:2d855d7db8e2e399624c353db40246e79c821b93e7805f55f1b2baa4182ae4e1`
- **fixed_point_epoch**: `sha256:2a9cfc8a07b1cb90ca6d100d3b28eded65e7beff5407df7bf7f27cfeec231a3e`
- **ipfs_accelerate**: `5458255b9d0123c24848ca286b2cf549e26e0b87`
- **ipfs_datasets**: `c330a601364e3fb760db34f98195b506a63f1f26`
- **ipfs_kit**: `ea3b47b72090354c27a9826d14a260d76b5e6914`
- **monorepo_head**: `2e422fa97423c118627956b31116352edd12e042`
- **policy**: `config/deterministic_contract_repair_policy.json`
- **policy_sha256**: `sha256:75f8736d78f8ea7366f71a0d07a05e37df1e1e0bf723cce414494089835769ba`
- **scheduler**: `config/deterministic_swissknife_mcplusplus_repair_scheduler.json`
- **scheduler_sha256**: `sha256:44a475f019df8ea8205de2c0a9e4350db59215bdb512edaa1047a952a184134f`
- **services_manifest**: `config/deterministic_contract_repair_services.json`
- **services_manifest_sha256**: `sha256:ee7d4c843aad60af87895ac962623b249eb0b844f0cf15656973eb83a8ae9f2e`
- **swissknife**: `1e2021cae2eafcb1d546be3b99fbdb4bc5a36256`

## Evidence CIDs

- **adversarial**: `sha256:8bdddab2dd92fcc90fd98f0b1b063d719ffa0dae6728f332137fc0d0cd9dd373`
- **benchmark**: `sha256:128b7c6614ab8a8124cec61214bd18426803c9b560bb56b9e68f844fc5032775`
- **canary**: `sha256:b2c0d6464adc3de2fcd6f5e84f2fd9471ae4947b78023fa7e501d752a6021677`
- **desktop_e2e**: `sha256:2b83eaa1a01f9ba9019649818f8a5566f3181181ad8e06c83b763356d4c04c13`
- **fixed_point**: `sha256:151fc53e9876ea2b1d59ba43956aaaa79a8f579798a442b86cb2dd7efb477645`
- **hermetic_conformance**: `sha256:e8d69f0142aeb4777ccd8b149bf0cabcdf8f82fbf004e3a59b0ba57f4928c619`
- **live_conformance**: `sha256:dbd6b14479cf6531c8d15c1b973786897ccc1671216fb91cb7f990fc7c7a7c3f`
- **policy**: `sha256:75f8736d78f8ea7366f71a0d07a05e37df1e1e0bf723cce414494089835769ba`
- **shadow**: `sha256:2fe712da3c80383c80794cb0765d204d33a6db8b6d4e2278e58d75d37de6a793`

## Unresolved typed gaps

- `finding:residual-review-authority-pin` [review_required] residual/review-required-authority-pin: Authority pin rotation requires human review
- `finding:residual-unsupported-profile-g` [unsupported] residual/unsupported-profile-g: MCP++ profile G remains typed unsupported

## Rollback procedure

1. Set policy mode to report_only and apply_enabled=false.
2. Restore config/deterministic_contract_repair_policy.json from release policy_sha256.
3. Re-run fixed-point, benchmark, shadow, and canary verifiers.
4. Re-admit auto_safe only after safety floors hold for a full review window.

## Compatibility claims

- Claims are limited to live/reconstructed evidence only.
- exceeds_live_evidence: `False`
- live_three_service: `True`
- desktop_e2e: `True`
- adversarial_kill_score: `True`

## Review decisions

- **review:auto-safe-boundary**: Auto-safe boundary pinned at auto_safe (authority=`reviewed`)
- **review:unresolved-residuals**: Unsupported/review-required residuals remain open (not repaired) (authority=`reviewed`)
- **review:zero-llm**: Release verification enforces zero model/provider calls (authority=`reviewed`)

