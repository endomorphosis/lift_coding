# UIR-085 recovery receipt — 2026-08-04

Status: **completed**

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

## Findings closed

1. **incomplete-reference-closure** — cross-ref validation now covers modality bindings, localization variables, accessibility relationships, adaptive predicates, expression/constraint refs, local state transitions, and program binding preconditions/effects/verifications.
2. **mutable-mapping-fields** — `UIConfiguration.settings` and `UINamespacedExtension.payload` are deep-frozen to `MappingProxyType` trees in `__post_init__`.
3. **set-semantics-not-enforced** — set-like fields (including capability_ids) reject duplicates via `_require_unique` before serialization.
4. **executable-payload-bypass** — rejects callable class objects and walks set/frozenset containers; forbidden `on_`/`handle_` keys remain blocked.
5. **modality-direction-mismatch** — `input_modality_requirements` must be `direction=input`; `output_modality_requirements` must be `direction=output`.

## Evidence

- Datasets commit: `f4e4df61527378e967662a5aa6dc945c0bb9f145`
- Validation: `cd external/ipfs_datasets && python -m pytest tests/unit/logic/ui_ux_ir/test_schema.py -q` → **25 passed**
- Accelerator pin for submodule production context: `8cfb572d962f8aae4aa0d68c03a4b460f47ea1eb`

## Operator note

Production typed-packet routing previously rejected submodule effect paths
(`nested_repository_escape`). The accelerator pin allows registered
`worktree_submodule_paths` as gitlink-backed nested roots so later UIR-010
correction attempts can package exact schema source.
