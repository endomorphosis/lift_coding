# LA-009 source-to-IR failure and scope review

This review accounts for every frozen selected case. It does not assign
expert legal fidelity, human agreement, or semantic accuracy scores.

## Frozen cohort

- Families: 30; cases: 60.
- Splits SHA-256: `f40b60ce73acbbbb7e9da39159b7dc5706f250cb5b85ac407c4b10140cb5c5a6`.
- Sources SHA-256: `55c69799805ce8466c7935f41c43a6656fbb2dce867496fb771ae07c4395feb6`.
- Original protocol SHA-256: `ba03394cd66f51999d1b177a29558b6130429eb9fc3faebea5e57c780857940f`.
- Cohorts were not changed after outcomes.

## Case accounting

- Records: 60/60.
- Predictions: 50.
- Failed: 4.
- Unavailable: 0.
- Unsupported: 6.
- Missing: 0.

## Machine-contract metrics

- Source-span linkage: 60/60.
- Parse/schema validity: 50/60.
- Scoped machine-contract coverage: 60/60.
- Implementation agreement is not semantic accuracy.

## CVE source-supported behavior

- Source-difference observations: 24/24.
- Polarity unknown: 24.
- Polarity supported by contract: 0.
- Untrusted source executed: 0.
- Transfer to export_json unsupported: 24.
- Independent producer: `la-006-scoped-behavior-contract-compiler` (distinct from the CVEfixes adapter).

## Failed, unavailable, and unsupported records

| case_id | population | split | status | code |
| --- | --- | --- | --- | --- |
| `family:02b8daf26d6786a78c5c17ddb8bf3380e0d37a26cbbb67e06a8118c09d03dc85:case-0` | cve | calibration | failed | `cve_adapter_error` |
| `family:02b8daf26d6786a78c5c17ddb8bf3380e0d37a26cbbb67e06a8118c09d03dc85:case-1` | cve | calibration | failed | `cve_adapter_error` |
| `family:f3e06f4eae288395b755b9240a5d9376cdd20289f9c7aa9b3b1b5025f05de479:case-0` | cve | final | failed | `cve_adapter_error` |
| `family:f3e06f4eae288395b755b9240a5d9376cdd20289f9c7aa9b3b1b5025f05de479:case-1` | cve | final | failed | `cve_adapter_error` |
| `family:aad9fb3792cc37134651428c8410b4912ee1568bb3f5ba93f0afbb625e65f914:case-1` | skill | development | unsupported | `skill_policy_blocked` |
| `family:4095a8192ffd393fa8298a444fdcde2f06130ca88eae32c4e10bfaf5361a67f3:case-1` | skill | calibration | unsupported | `skill_policy_blocked` |
| `family:b947bde75c0695ef7224e81ee81699aa8a1c7d9eab2ab546f8bb3843a36d7a10:case-1` | skill | final | unsupported | `skill_policy_blocked` |
| `family:bdb094f619eded6d259e518640d5b5b469bf25ef06103b60891529ffe079e228:case-1` | skill | final | unsupported | `skill_policy_blocked` |
| `family:b7d9f67c75ce5c3d3612efbddf3ec32c8dec1469ecdc8a4e31d2dbb0b2757b30:case-1` | skill | final | unsupported | `skill_policy_blocked` |
| `family:7fb5e91eebb23de8362cd6d577e98b102f7e5b0bd11e0c4886be3db4b79ad02c:case-1` | skill | final | unsupported | `skill_policy_blocked` |

### `family:02b8daf26d6786a78c5c17ddb8bf3380e0d37a26cbbb67e06a8118c09d03dc85:case-0`

- Status: `failed`.
- Population/split: cve/calibration.
- Mutation: `source_faithful_vulnerable_positive`.
- Message: CVEfixesAdapterError: candidate scope must contain complete, exact CVEfixes policy attributes.

### `family:02b8daf26d6786a78c5c17ddb8bf3380e0d37a26cbbb67e06a8118c09d03dc85:case-1`

- Status: `failed`.
- Population/split: cve/calibration.
- Mutation: `fixed_negative_control`.
- Message: CVEfixesAdapterError: candidate scope must contain complete, exact CVEfixes policy attributes.

### `family:f3e06f4eae288395b755b9240a5d9376cdd20289f9c7aa9b3b1b5025f05de479:case-0`

- Status: `failed`.
- Population/split: cve/final.
- Mutation: `source_faithful_vulnerable_positive`.
- Message: CVEfixesAdapterError: candidate scope must contain complete, exact CVEfixes policy attributes.

### `family:f3e06f4eae288395b755b9240a5d9376cdd20289f9c7aa9b3b1b5025f05de479:case-1`

- Status: `failed`.
- Population/split: cve/final.
- Mutation: `fixed_negative_control`.
- Message: CVEfixesAdapterError: candidate scope must contain complete, exact CVEfixes policy attributes.

### `family:aad9fb3792cc37134651428c8410b4912ee1568bb3f5ba93f0afbb625e65f914:case-1`

- Status: `unsupported`.
- Population/split: skill/development.
- Mutation: `malicious_markdown`.
- Message: SkillNormalizationPolicyError: SkillCenter record is not eligible for content normalization: excluded.

### `family:4095a8192ffd393fa8298a444fdcde2f06130ca88eae32c4e10bfaf5361a67f3:case-1`

- Status: `unsupported`.
- Population/split: skill/calibration.
- Mutation: `malicious_markdown`.
- Message: SkillNormalizationPolicyError: SkillCenter record is not eligible for content normalization: excluded.

### `family:b947bde75c0695ef7224e81ee81699aa8a1c7d9eab2ab546f8bb3843a36d7a10:case-1`

- Status: `unsupported`.
- Population/split: skill/final.
- Mutation: `malicious_markdown`.
- Message: SkillNormalizationPolicyError: SkillCenter record is not eligible for content normalization: excluded.

### `family:bdb094f619eded6d259e518640d5b5b469bf25ef06103b60891529ffe079e228:case-1`

- Status: `unsupported`.
- Population/split: skill/final.
- Mutation: `malicious_markdown`.
- Message: SkillNormalizationPolicyError: SkillCenter record is not eligible for content normalization: excluded.

### `family:b7d9f67c75ce5c3d3612efbddf3ec32c8dec1469ecdc8a4e31d2dbb0b2757b30:case-1`

- Status: `unsupported`.
- Population/split: skill/final.
- Mutation: `malicious_markdown`.
- Message: SkillNormalizationPolicyError: SkillCenter record is not eligible for content normalization: excluded.

### `family:7fb5e91eebb23de8362cd6d577e98b102f7e5b0bd11e0c4886be3db4b79ad02c:case-1`

- Status: `unsupported`.
- Population/split: skill/final.
- Mutation: `malicious_markdown`.
- Message: SkillNormalizationPolicyError: SkillCenter record is not eligible for content normalization: excluded.

## Shared-producer dependence

- Legal parser vs DeonticConverter agreement is same-package implementation consistency, not expert legal fidelity.
- Skill decoder/schema checks are independent of the SkillCenter normalizer.
- CVE behavior observations come from LA-006/LA-026 contracts, not from the CVEfixes adapter under evaluation.
- Packet-preparer atoms and intent nodes were not used as independent gold.

## Synthetic qualification controls excluded from the frozen denominator

- Count: 24.
- These `skill_claims_authorization` and `command_execution_bait` rows are not planned case identities.
- LA-008 fixture smokes are also outside this empirical cohort.

- `synthetic:family:10df17dbfee02e86d083e2784e7aaec79a4691d1441d1ceff4ef944f2695b949:command_execution_bait`
- `synthetic:family:10df17dbfee02e86d083e2784e7aaec79a4691d1441d1ceff4ef944f2695b949:malicious_markdown`
- `synthetic:family:4095a8192ffd393fa8298a444fdcde2f06130ca88eae32c4e10bfaf5361a67f3:command_execution_bait`
- `synthetic:family:4095a8192ffd393fa8298a444fdcde2f06130ca88eae32c4e10bfaf5361a67f3:skill_claims_authorization`
- `synthetic:family:564de790672a8ff721a37da968ab57f51cfa0f46f489aa5e77130c8487f9dee8:command_execution_bait`
- `synthetic:family:564de790672a8ff721a37da968ab57f51cfa0f46f489aa5e77130c8487f9dee8:malicious_markdown`
- `synthetic:family:7fb5e91eebb23de8362cd6d577e98b102f7e5b0bd11e0c4886be3db4b79ad02c:command_execution_bait`
- `synthetic:family:7fb5e91eebb23de8362cd6d577e98b102f7e5b0bd11e0c4886be3db4b79ad02c:skill_claims_authorization`
- `synthetic:family:aad9fb3792cc37134651428c8410b4912ee1568bb3f5ba93f0afbb625e65f914:command_execution_bait`
- `synthetic:family:aad9fb3792cc37134651428c8410b4912ee1568bb3f5ba93f0afbb625e65f914:skill_claims_authorization`
- `synthetic:family:af2d220ac03bb25626bc2481a068dd98abb4c0907fb89decdd50028f7814ddad:command_execution_bait`
- `synthetic:family:af2d220ac03bb25626bc2481a068dd98abb4c0907fb89decdd50028f7814ddad:malicious_markdown`
- `synthetic:family:b7d9f67c75ce5c3d3612efbddf3ec32c8dec1469ecdc8a4e31d2dbb0b2757b30:command_execution_bait`
- `synthetic:family:b7d9f67c75ce5c3d3612efbddf3ec32c8dec1469ecdc8a4e31d2dbb0b2757b30:skill_claims_authorization`
- `synthetic:family:b947bde75c0695ef7224e81ee81699aa8a1c7d9eab2ab546f8bb3843a36d7a10:command_execution_bait`
- `synthetic:family:b947bde75c0695ef7224e81ee81699aa8a1c7d9eab2ab546f8bb3843a36d7a10:skill_claims_authorization`
- `synthetic:family:bdb094f619eded6d259e518640d5b5b469bf25ef06103b60891529ffe079e228:command_execution_bait`
- `synthetic:family:bdb094f619eded6d259e518640d5b5b469bf25ef06103b60891529ffe079e228:skill_claims_authorization`
- `synthetic:family:c8c0d8e29a596f792708eb72a5815e752b90c081c7ebda19bf315989e9e288db:command_execution_bait`
- `synthetic:family:c8c0d8e29a596f792708eb72a5815e752b90c081c7ebda19bf315989e9e288db:malicious_markdown`
- `synthetic:family:e8a49438d9f648468887e8c9429cfa975620d996f6dd7b4a8c04933544a311ac:command_execution_bait`
- `synthetic:family:e8a49438d9f648468887e8c9429cfa975620d996f6dd7b4a8c04933544a311ac:malicious_markdown`
- `synthetic:family:f761769c88e7c2240ae3440d8be2102ac5be2b311463fe806297f7e134fe651d:command_execution_bait`
- `synthetic:family:f761769c88e7c2240ae3440d8be2102ac5be2b311463fe806297f7e134fe651d:malicious_markdown`

## Withdrawn unmeasured claims

- Expert legal applicability/exception fidelity: unmeasured; no numeric score.
- Inter-annotator agreement and independent human validation: unmeasured; no numeric score.
- Legal applicability or validity in the world: unmeasured; no numeric score.
- Semantic accuracy inferred from implementation agreement: not assigned.
- Human/author review was not a run dependency.
