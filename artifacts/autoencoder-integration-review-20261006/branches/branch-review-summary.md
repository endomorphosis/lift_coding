# Autoencoder branch and worktree integration review

Reviewed origin/main `5171a632c6b9f0ecb2939d29d2ad74992cbfeb11` against the initial 410 refs and 16 worktrees, with focused commit-to-tree byte checks. The root review fetched all remote heads before these findings.

The prior paraphrase experiment commit `60f5c295` has all ten changed paths byte-identical on current main. Saved source-v2 continuation `d1643c2c` and the LegalIR/original-text reconstruction scorer `92600cbf` are also present exactly. Generated-scalar/alignment work is retained, with later opt-in additions in the shared trainer. These branches require no repeated cherry-pick.

Ancestry was insufficient for the cached IR interfaces and bounded Git source acquisition. Canonical snapshots removed modules and APIs after merging their history. The active Git batch consumer imported a missing profile; the profile and tests required omitted streaming source modules and the removed streaming CID function. The minimal closure restores existing sources and adds only the missing CID function to the current content implementation. Its existing caches remain intact.

Six optional cached IR/format/profile modules and their tests were restored, with four functions appended to the current Hub loader. All existing Hub source is a byte-identical prefix, including Legal optimizations and checkpoint selection. Producer pins remain exact. This restores an explicit callable cached/original-corpus interface; it does not add a general text encoder or qualify a model.

The canonical validation passed 129 Git/CID tests, 774 cached IR tests and 25 existing Hub loader tests: 928 tests, no skips. An initial source-closure collection failure and one memory-threshold fluctuation are retained in logs; the unchanged memory test and complete closure later passed. The final isolated IR closure uses only main’s three existing test package markers, with no synthetic namespace additions.

The dirty numerical-replay worktree contains a worker-budget change already present on main and an older lossy UI codec. Neither should replace current source. Other reviewed named decoder worktrees are clean.

The combined publication scope contains 31 paths and 511074 bytes, pinned by SHA256 and preimage in `combined-owned-source-scope.json`. The audit leaves normal Git indexes, HEADs and refs untouched. Root publishes the reviewed source scope.

Only a real `lake build <Lib>` grants Lean admission. This review performs no model training, numerical model forwards, checkpoint downloads, semantic promotion or Constitution formalization.
