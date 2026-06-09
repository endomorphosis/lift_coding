# MGW-184 Hallucinate App Submodule Pin Repair

Date: 2026-06-09
Task: MGW-184

## Finding

MGW-183 had been released from the prior retry-budget loop by moving
`hallucinate_app` to published remote commit
`2062957f2bc319d3e879fa127f68e1d4bb88b4ae`, but this worktree still pointed at
`160d66a93ee2b3675f48296f7231ed164175a8c5`.

Clean initialization failed before agents could inspect or validate
`hallucinate_app/hallucinate_app/python/hallucinate_app/ipfs_model_manager.py`:

```text
fatal: remote error: upload-pack: not our ref 160d66a93ee2b3675f48296f7231ed164175a8c5
fatal: Fetched in submodule path 'hallucinate_app', but it did not contain 160d66a93ee2b3675f48296f7231ed164175a8c5. Direct fetching of that commit failed.
```

The direct remote query advertises `2062957f2bc319d3e879fa127f68e1d4bb88b4ae`
on `refs/heads/main`, but not the previous `160d66a...` gitlink.

## Repair

The `hallucinate_app` gitlink was moved to published remote descendant commit
`943252d76e198e8a9cc900f9787b2e183f107cdd`. That commit contains the
MGW-184 repair target commit `2062957f2bc319d3e879fa127f68e1d4bb88b4ae`, keeps
the newer main-side HAO-222 work, initializes successfully, and contains the
expected
`hallucinate_app/hallucinate_app/python/hallucinate_app/ipfs_model_manager.py`
path for the MGW-183 repair chain.
