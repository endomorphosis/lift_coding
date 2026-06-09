# MGW-183 Hallucinate App Submodule Pin Repair

Date: 2026-06-09
Task: MGW-183

## Finding

MGW-182 repeatedly failed before it could inspect or validate
`hallucinate_app/hallucinate_app/python/hallucinate_app/ipfs_model_manager.py`
because a clean worktree could not initialize the `hallucinate_app` submodule.

`git submodule update --init hallucinate_app` failed with:

```text
fatal: remote error: upload-pack: not our ref 556cb241909759c94c580e46a87b6ad770a8bde5
fatal: Fetched in submodule path 'hallucinate_app', but it did not contain 556cb241909759c94c580e46a87b6ad770a8bde5. Direct fetching of that commit failed.
```

The superproject gitlink pointed at `556cb241909759c94c580e46a87b6ad770a8bde5`,
which exists in a local checkout but is not advertised by
`https://github.com/endomorphosis/hallucinate_app.git`.

## Repair

The `hallucinate_app` gitlink was moved to published remote `main` commit
`2062957f2bc319d3e879fa127f68e1d4bb88b4ae`, which initializes successfully in a
fresh worktree and includes the prior IPFS model import exception cleanup
behavior needed by MGW-181/MGW-182.
