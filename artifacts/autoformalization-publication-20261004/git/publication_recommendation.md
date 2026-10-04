# Git publication inventory and integration order

This is a read-only inventory taken on 2026-10-04. No index, checkout, configuration, branch, stash, commit, fetch, push or merge was changed by the inventory agent. Git optional locks were disabled. Parent-agent fetches may have refreshed remote-tracking refs during collection; this is not a globally atomic snapshot.

The commit-sized inventory is [publication_compact.json](publication_compact.json) (725,178 bytes, SHA256 `a5b0ae2bf3d6839b323b19e144dc38970f0af13065ec0de81cacdd4ca85df906`). The full local inventory and compressed copy retain all detailed registrations and bindings. Keep the 49.9 MB raw inventory, the intermediate 8.6 MB scope file, generated archive copies and runtime caches outside the Git source publication.

## Observed scope

- 179 distinct Git common directories map to 40 normalized origin repositories. URL credentials and query parameters were removed from the inventory.
- 31,144 registered worktree paths include 3,170 available worktrees belonging to the expected repository and 27,974 unavailable historical registrations. Leave missing and locked recovery registrations intact; do not materialize or repair them.
- 319 available worktrees have tracked changes or untracked files in the sampled source roots. Of these, 265 belong to endomorphosis-owned origins. Detailed source sampling excludes large generated artifact/runtime trees.
- No indexed conflict, active merge/rebase operation, or index-byte change was observed during inventory. This is an initial state observation, not a guarantee that future integrations will be conflict-free.
- 24 applicable AGENTS files, representing eight distinct contents, were read and bound. They belong to third-party SDK/framework repositories. None was found in the seven canonical publication repositories or their ancestor directories. Pristine third-party repositories need no write; their contribution and testing rules apply to any separate modification/publication there.

| Canonical origin | Unique branch/detached heads | Already ancestors of observed origin/main | Remaining known objects | Remaining heads to import |
| --- | ---: | ---: | ---: | ---: |
| lift_coding | 28 | 28 | 0 | 0 |
| ipfs_datasets_py | 393 | 352 | 2 | 39 |
| ipfs_accelerate_py | 632 | 549 | 3 | 80 |
| ipfs_kit_py | 108 | 107 | 0 | 1 |
| swissknife | 29 | 24 | 0 | 5 |
| Mcp-Plus-Plus | 10 | 10 | 0 | 0 |
| hallucinate_app | 1 | 1 | 0 | 0 |

These counts deduplicate commit SHAs across cloned common directories and do not include new snapshot commits made after inventory. Additional initialized owned origins, including CEC/prover/converter/model-manager helpers, remain separately listed with exact source locations in the compact inventory. Their ancestry was not compared with a designated canonical checkout by this agent.

## Non-destructive publication sequence

1. Freeze and record each available owned worktree's relevant tracked and untracked source changes. Snapshot meaningful source, documentation, tests and bounded reproducibility receipts. Exclude credentials, ignored data, generated clones, runtime archives and build caches. Keep large checkpoint bytes in the separately reviewed Hugging Face publication, with exact hashes and lineage recorded in Git. Preserve existing frozen artifact bytes and original worktrees.
2. Process owned leaf repositories before their parent gitlinks. For each normalized origin, retain an exact ledger of all original branch heads, detached heads and new source snapshot commits. Import missing commits from the selected local common directories into a fresh namespaced publication area; do not rewrite original refs or stale `core.worktree` settings.
3. Create a fresh integration worktree from the captured current origin/main. Merge each unique head that is not already an ancestor. Resolve conflicts against both branches' actual changes, preserving newer implementations and branch-only features. Record exact resolutions when an old change has already been superseded. Do not use a blanket tree replacement as evidence that branch-only work was preserved.
4. Verify that every selected original and snapshot head is an ancestor of the integration commit. Check the resulting source diff, gitlink commits, large-file policy and frozen-file hashes. Run the relevant existing validation commands for changes that remain in the final tree; preserve known unrelated test limitations accurately.
5. Push the integration branch to origin/main with an ordinary non-force push. If origin/main advances, refresh it, integrate its new commits and retry. Never force-push, delete existing branches/worktrees, or reset active recovery checkouts. Publish updated parent gitlinks only after the referenced subrepository commits are available remotely.

GitHub authentication was available; write access to every discovered origin was not verified by this inventory. No credential values or secret file contents were read or saved. Source availability, committed lineage and remote reachability remain separate checks.
