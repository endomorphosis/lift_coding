# Portland legal work history

This packet preserves ten distinct checked-out commit lines from the Portland law `workspace/codex-work` directory. Three checkout tips are already ancestors of the corresponding GitHub `origin/main`. Two proposal-validation checkouts share one commit tip and one retained ref. `restore.json` records both main commits, bundle checksums, exact branch tips, and original checkout labels.

The bundles carry objects reachable from the retained tips outside the corresponding published main. Both were restored into empty Git object stores using only the respective main histories for prerequisites. Verification checked each recovered tip, the exact new object set, and the origin of any delta bases Git added during unpacking.

The recovery refs preserve historical source and test identities for review. Integration of a functional change uses a separately tested commit on current submodule main. The manifest records the qualifying Accelerate objective output-ownership candidate and the proposal-validation behavior already present in current source.

## Restore a branch

In a full clone of the appropriate submodule with current `origin/main` fetched, set `bundle_file` to the absolute path of the relevant bundle from this directory. Check its checksum against `restore.json`, then run the following commands in that submodule clone.

```sh
sha256sum "$bundle_file"
git bundle verify "$bundle_file"
git bundle list-heads "$bundle_file"
git fetch "$bundle_file" 'refs/heads/portland-legal/*:refs/heads/recovered/portland-legal/*'
```

Compare the recovered branch tip with the matching `tip` in the manifest before inspecting or applying changes. The restore commands create recovery refs in the receiving clone.
