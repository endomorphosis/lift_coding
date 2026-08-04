# UIR-085 recovery receipt — 2026-08-04

Status: **open**

This receipt is the operator-facing binder for the durable UIR-010
`correction_failed` head. It is not acceptance evidence and does not mint a
repair grant by itself.

## Bound failure

| Field | Value |
|-------|-------|
| Source task | `UIR-010` |
| Denial ID | `baguqeerairqc5selrpnvxsuenklnq5oi6e2djjcptvdzpta7hmdvapbai64a` |
| Failure event | `sha256:6b2cd775ae74b67b210714157217a9af90eb2da5d2885093eebcb9d531db57fa` |
| Failure sequence | 1958 |
| Failed attempt | 2 |
| Failure kind | implementation |
| Origin stream | `event-log:sha256:5d2d9e8dec77b16b1500d5d7fd8cfff8fbf10cf37199bead391db4663ead3926` |

## Required findings to close

1. incomplete-reference-closure
2. mutable-mapping-fields
3. set-semantics-not-enforced
4. executable-payload-bypass
5. modality-direction-mismatch

## Completion rule

Only mark `UIR-085` completed after schema/tests address the five findings and
this receipt is updated with validation evidence. Completing the task then
allows the supervisor to mint the exact post-merge correction repair grant for
UIR-010.
