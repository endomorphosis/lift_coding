# PGIR-119 Reconciliation Guardrail

Date: 2026-08-18
Fingerprint: fe270214fc72a4ca0eca4b0e8e1bbfaa72705443
Kind: dirty_backlogged_worktree
Reason: unsupported_status
Candidate count: 1
Priority: P1
Track: ops

## Main Checkout Status

- none

## Main Checkout Evidence

- none

## Sample Branches Or Worktrees

- `rescue/worktree/rescue-worktree-rescue-worktree-rescue-worktree-rescue-worktree-rescue-worktree-rescue-worktree--8995e6acf55f` at `/home/barberb/lift_coding/.pgir_campaign/runtime/worktrees/workspace-cea216f7b677-c216268df90c` status: ` D .asyncio_allowlist;  D .gitignore;  D .gitmodules;  D MANIFEST.in;  D bin/.gitkeep;  D docker-compose.yml;  D ipfs_accelerate_js/.gitignore;  D ipfs_accelerate_js/MIGRATION_REPORT_20250311_040828.md;  D ipfs_accelerate_js/MIGRATION_SUMMARY_20250311_034331.md;  D ipfs_accelerate_js/MIGRATION_SUMMARY_20250311_034647.md;  D ipfs_accelerate_js/PUBLISHING_CHECKLIST.md;  D ipfs_accelerate_js/README.md;  D ipfs_accelerate_js/docs/API_DOCUMENTATION.md;  D ipfs_accelerate_js/docs/DEVELOPER_GUIDE.md;  D ipfs_accelerate_js/docs/GENERATOR_IMPROVEMENT_GUIDE.md;  D ipfs_accelerate_js/docs/IMPLEMENTATION_STATUS.md;  D ipfs_accelerate_js/docs/JAVASCRIPT_SDK_DOCUMENTATION.md;  D ipfs_accelerate_js/docs/MIGRATION_PLAN.md;  D ipfs_accelerate_js/docs/MIGRATION_PROGRESS.md;  D ipfs_accelerate_js/docs/TYPESCRIPT_IMPLEMENTATION_SUMMARY.md`
  - Name status:
    - `del_integration.py`
    - `D	test/verify_test_environment.py`
    - `D	test/verify_web_resource_pool.py`
    - `D	test/vision_template.py`
    - `D	test/vision_template2.py`
    - `D	test/vision_template_fixed.py`
    - `D	test/vision_text_duckdb_integration.py`
    - `D	test/vision_text_visualization.py`
    - `D	test/visualizations/cache_performance_forecast_class.png`
    - `D	test/visualizations/cache_performance_forecast_manual.png`
    - `D	test/visualizations/compression_ratio_forecast_class.png`
    - `D	test/visualizations/compression_ratio_forecast_manual.png`
  - Diff stat:
    - `askqueue_e2e.py    |   169 -`
    - ` scripts/validation/validate_docker_cache_setup.sh  |   357 -`
    - ` scripts/validation/validate_installer_alignment.py |   316 -`
    - ` scripts/validation/validate_setup.py               |   360 -`
    - ` scripts/validation/verify_p2p_cache.py             |   217 -`
    - ` scripts/verify_dashboard_integration.py            |   199 -`
    - ` scripts/vscode_mcp_server.py                       |    58 -`
    - ` scripts/zero_touch_install.sh                      |  1097 -`
    - ` setup.py                                           |   261 -`
    - ` state/p2p_gpt2_2peer/peer1_queue.duckdb.wal        |   Bin 236841 -> 0 bytes`
    - ` state/p2p_gpt2_2peer/peer2_queue.duckdb.wal        |   Bin 234378 -> 0 bytes`
    - ` state/smoketest_logs/driver.out                    |    22 -`
  - Untracked paths:
    - `ipfs_accelerate_py/__pycache__`
    - `ipfs_accelerate_py/agent_supervisor/__pycache__`
    - `ipfs_accelerate_py/agent_supervisor/analysis/__pycache__`
    - `ipfs_accelerate_py/agent_supervisor/context/__pycache__`
    - `ipfs_accelerate_py/agent_supervisor/control/__pycache__`
    - `ipfs_accelerate_py/agent_supervisor/core/__pycache__`
    - `ipfs_accelerate_py/agent_supervisor/merge/__pycache__`
    - `ipfs_accelerate_py/agent_supervisor/objectives/__pycache__`
    - `ipfs_accelerate_py/agent_supervisor/planning/__pycache__`
    - `ipfs_accelerate_py/agent_supervisor/proof/__pycache__`
    - `ipfs_accelerate_py/agent_supervisor/rescue/__pycache__`
    - `ipfs_accelerate_py/agent_supervisor/runtime/__pycache__`

## Why This Blocks Progress

The implementation supervisor can only merge clean inactive implementation
worktrees when the main checkout is safe to mutate. Dirty main checkouts and
dirty backlogged worktrees are preserved until a deliberate reconciliation task
decides whether to commit, merge, discard generated duplicates, or split
unresolved work into follow-up tasks.

## Suggested Repair

Inspect the dirty paths and sampled worktrees, resolve any real work into
reviewable commits or follow-up tasks, rerun the supervisor reconciliation pass,
and verify that either the candidate merge count decreases or the dirty
worktree cleanup skip count decreases.

## Reconciliation Plan

Work surface: `1` candidates, `1` sampled records.

### Suggested Actions

- `classify_dirty_worktree_group`: inspect sampled dirty statuses and compare against the target ref
- `resolve_unsupported_statuses`: handle deletes, renames, unmerged paths, or unusual index states with an explicit resolver pass
- `preserve_or_merge_backlogged_work`: merge valuable branch work, commit preserved changes, or file follow-up tasks for unresolved work
- `rerun_cleanup_pass`: rerun cleanup_backlogged_worktrees after preserving or merging dirty worktree content

### Safety Constraints

- Do not discard dirty or untracked content unless it is proven redundant with the target ref.
- Prefer commits, merges, or explicit follow-up tasks over destructive cleanup.
- Keep todo, objective, discovery, and strategy files parseable after reconciliation.

### Success Signals

- `candidate_count_decreases`
- `dirty_worktree_group_count_decreases`
- `main_checkout_dirty_becomes_false`
- `cleanup_or_reconciliation_pass_processes_candidates`

## Machine Readable Manifest

```json
{
  "actions": [
    {
      "action": "classify_dirty_worktree_group",
      "automation": "inspect sampled dirty statuses and compare against the target ref",
      "scope": "sampled_worktrees"
    },
    {
      "action": "resolve_unsupported_statuses",
      "automation": "handle deletes, renames, unmerged paths, or unusual index states with an explicit resolver pass",
      "scope": "dirty_worktrees"
    },
    {
      "action": "preserve_or_merge_backlogged_work",
      "automation": "merge valuable branch work, commit preserved changes, or file follow-up tasks for unresolved work",
      "scope": "dirty_worktrees"
    },
    {
      "action": "rerun_cleanup_pass",
      "automation": "rerun cleanup_backlogged_worktrees after preserving or merging dirty worktree content",
      "scope": "worktree_root"
    }
  ],
  "candidate_count": 1,
  "conflict_path_counts": {},
  "dedupe_key": "reconciliation_guardrail:dirty_backlogged_worktree:unsupported_status",
  "fingerprint": "fe270214fc72a4ca0eca4b0e8e1bbfaa72705443",
  "kind": "dirty_backlogged_worktree",
  "main_dirty_evidence": {},
  "reason": "unsupported_status",
  "safety_constraints": [
    "Do not discard dirty or untracked content unless it is proven redundant with the target ref.",
    "Prefer commits, merges, or explicit follow-up tasks over destructive cleanup.",
    "Keep todo, objective, discovery, and strategy files parseable after reconciliation."
  ],
  "sample_branches": [
    "rescue/worktree/rescue-worktree-rescue-worktree-rescue-worktree-rescue-worktree-rescue-worktree-rescue-worktree--8995e6acf55f"
  ],
  "sample_count": 1,
  "sample_status_paths": [
    ".asyncio_allowlist",
    ".gitignore",
    ".gitmodules",
    "MANIFEST.in",
    "bin/.gitkeep",
    "docker-compose.yml",
    "ipfs_accelerate_js/.gitignore",
    "ipfs_accelerate_js/MIGRATION_REPORT_20250311_040828.md",
    "ipfs_accelerate_js/MIGRATION_SUMMARY_20250311_034331.md",
    "ipfs_accelerate_js/MIGRATION_SUMMARY_20250311_034647.md",
    "ipfs_accelerate_js/PUBLISHING_CHECKLIST.md",
    "ipfs_accelerate_js/README.md",
    "ipfs_accelerate_js/docs/API_DOCUMENTATION.md",
    "ipfs_accelerate_js/docs/DEVELOPER_GUIDE.md",
    "ipfs_accelerate_js/docs/GENERATOR_IMPROVEMENT_GUIDE.md",
    "ipfs_accelerate_js/docs/IMPLEMENTATION_STATUS.md",
    "ipfs_accelerate_js/docs/JAVASCRIPT_SDK_DOCUMENTATION.md",
    "ipfs_accelerate_js/docs/MIGRATION_PLAN.md",
    "ipfs_accelerate_js/docs/MIGRATION_PROGRESS.md",
    "ipfs_accelerate_js/docs/TYPESCRIPT_IMPLEMENTATION_SUMMARY.md",
    "del_integration.py",
    "test/verify_test_environment.py",
    "test/verify_web_resource_pool.py",
    "test/vision_template.py",
    "test/vision_template2.py",
    "test/vision_template_fixed.py",
    "test/vision_text_duckdb_integration.py",
    "test/vision_text_visualization.py",
    "test/visualizations/cache_performance_forecast_class.png",
    "test/visualizations/cache_performance_forecast_manual.png",
    "test/visualizations/compression_ratio_forecast_class.png",
    "test/visualizations/compression_ratio_forecast_manual.png",
    "test/visualizations/index_efficiency_forecast_class.png",
    "test/visualizations/index_efficiency_forecast_manual.png",
    "test/visualizations/query_time_forecast_class.png",
    "test/visualizations/query_time_forecast_manual.png",
    "test/visualizations/read_efficiency_forecast_class.png",
    "test/visualizations/read_efficiency_forecast_manual.png",
    "test/visualizations/storage_size_forecast_class.png",
    "test/visualizations/storage_size_forecast_manual.png"
  ],
  "sample_worktrees": [
    "/home/barberb/lift_coding/.pgir_campaign/runtime/worktrees/workspace-cea216f7b677-c216268df90c"
  ],
  "success_signals": [
    "candidate_count_decreases",
    "dirty_worktree_group_count_decreases",
    "main_checkout_dirty_becomes_false",
    "cleanup_or_reconciliation_pass_processes_candidates"
  ],
  "top_conflict_paths": []
}
```
