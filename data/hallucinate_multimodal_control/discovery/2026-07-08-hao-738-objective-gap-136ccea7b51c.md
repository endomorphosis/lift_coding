# HAO-738 Objective Goal Gap

Date: 2026-07-08
Fingerprint: 136ccea7b51cd3def2e6ed2bb0e61328ff556aa2
Goal id: VAIOS-G710
Goal title: Interoperate external/meta-wearables-dat-android with external/ipfs_datasets
Objective heap: implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md
Priority: P1
Track: interoperability
Parent goals: VAIOS-G000
Graph depth: 1
Bundle: objective/interoperability/external_meta_wearables_dat_android-external_ipfs_datasets
Parallel lane: objective/interoperability/external_meta_wearables_dat_android-external_ipfs_datasets
Bundle strategy: explicit
Goal packet: goal_packet/interoperability/external/6595cbbfadb9
Goal packet role: packet_member
Goal packet goals: VAIOS-G709, VAIOS-G710, VAIOS-G711
Goal packet task count: 3
Goal packet work item count: 3
Evidence methods: ast, embedding, path
Embedding query: external/meta-wearables-dat-android external/ipfs_datasets interoperability integration test interface descriptor __future__ _jsonnet abc anyio argparse ast asyncio atexit base64 boto3 bs4 cProfile
AST query: external/meta-wearables-dat-android, external/ipfs_datasets, interface contract, integration test, __future__, _jsonnet, abc, anyio, argparse, ast, asyncio, atexit, base64, boto3, bs4, cProfile
Conflict policy: keep pair-specific integration edits isolated; use the LLM merge resolver for conflicts

## Goal

Prove `external/meta-wearables-dat-android` interoperates with `external/ipfs_datasets` through importable contracts, interface descriptors, runtime handoff behavior, and integration tests.

## Missing Evidence

- objective validation repair

## Present Evidence

- tests/integration/test_external_meta_wearables_dat_android_external_ipfs_datasets_interop.py: .github/workflows/ci.yml (embedding:0.55), CONTRIBUTING.md (ast), dev/meta-rayban-display-simulator/fixtures/task-progress.json (ast)
- docs/integration/external_meta_wearables_dat_android-external_ipfs_datasets.md: ARCHITECTURE.md (embedding:0.36), dev/meta-rayban-display-simulator/fixtures/task-progress.json (ast), docs/DOCUMENTATION_INDEX.md (embedding:0.43)
- interface contract external/meta-wearables-dat-android external/ipfs_datasets: dev/meta-rayban-display-simulator/fixtures/task-progress.json (ast), docs/GETTING_STARTED.md (embedding:0.34), docs/launch/phone_desktop_glasses_readiness.md (embedding:0.35)
- external/ipfs_datasets/.tools/ipfs_kit_py/data/deprecations_report.schema.json: external/ipfs_datasets/.tools/ipfs_kit_py/data/deprecations_report.schema.json (path), agent-runner/apply_instruction.py (ast), agent-runner/runner.py (ast)
- external/ipfs_datasets/.tools/ipfs_kit_py/docs/implementation/BUCKET_VFS_INTERFACES_COMPLETE.md: external/ipfs_datasets/.tools/ipfs_kit_py/docs/implementation/BUCKET_VFS_INTERFACES_COMPLETE.md (path), config/display_webapp_readiness.meta_glasses_widget.example.json (ast), dev/meta-rayban-display-simulator/fixtures/task-progress.json (ast)
- external/ipfs_datasets/.tools/ipfs_kit_py/examples/demo_bucket_vfs_interfaces.py: external/ipfs_datasets/.tools/ipfs_kit_py/examples/demo_bucket_vfs_interfaces.py (path), dev/meta-rayban-display-simulator/fixtures/task-progress.json (ast), docs/integration/ipfs-backend-integration.md (embedding:0.69)
- external/ipfs_datasets/.tools/ipfs_kit_py/examples/demo_unified_bucket_interface.py: external/ipfs_datasets/.tools/ipfs_kit_py/examples/demo_unified_bucket_interface.py (path), dev/meta-rayban-display-simulator/fixtures/task-progress.json (ast), docs/integration/ipfs-backend-integration.md (embedding:0.65)
- external/ipfs_datasets/.tools/ipfs_kit_py/examples/demos/demo_bucket_vfs_interfaces.py: external/ipfs_datasets/.tools/ipfs_kit_py/examples/demos/demo_bucket_vfs_interfaces.py (path), agent-runner/apply_instruction.py (ast), agent-runner/runner.py (ast)
- external/ipfs_datasets/.tools/ipfs_kit_py/examples/schema_column_optimization_example.py: external/ipfs_datasets/.tools/ipfs_kit_py/examples/schema_column_optimization_example.py (path), config/display_webapp_readiness.meta_glasses_widget.example.json (ast), dev/meta-rayban-display-simulator/fixtures/task-progress.json (ast)

## Suggested Handling

Run and repair the objective validation command until it passes, then record the evidence.

## Repair Evidence

- HAO-738 objective validation repair is covered by `src/handsfree/meta_wearables_dat_android_ipfs_datasets_interop.py`, which exposes the importable `MetaWearablesDATAndroidIPFSDatasetsHandoff` contract and `build_meta_wearables_dat_android_ipfs_datasets_handoff()` runtime handoff builder.
- `tests/integration/test_external_meta_wearables_dat_android_external_ipfs_datasets_interop.py` validates `interface contract external/meta-wearables-dat-android external/ipfs_datasets`, descriptor discovery, Bucket VFS schema/docs/demos, deterministic content addressing, and objective heap alignment.
- `docs/integration/external_meta_wearables_dat_android-external_ipfs_datasets.md` records the pair contract, handoff route, expected Bucket VFS operations, and validation command.
- External evidence paths are now concrete for `external/meta-wearables-dat-android`, `external/ipfs_datasets`, `external/ipfs_datasets/.tools/ipfs_kit_py/data/deprecations_report.schema.json`, `external/ipfs_datasets/.tools/ipfs_kit_py/docs/implementation/BUCKET_VFS_INTERFACES_COMPLETE.md`, `external/ipfs_datasets/.tools/ipfs_kit_py/examples/demo_bucket_vfs_interfaces.py`, and `external/ipfs_datasets/.tools/ipfs_kit_py/examples/demo_unified_bucket_interface.py`.
