# Dependency worktree preservation — 2026-11-23

Status: **NOT_ADOPTED**. Eight Git bundles preserve exact retained local branch histories from foreign dependency copies. They do not apply changes to dependencies, update gitlinks, or establish runtime, model, legal, or release qualification. No third-party repository was pushed.

`manifest.json` records origins, fresh default-branch commits, exact original refs/tips, prerequisites, retained blob IDs/sizes, bundle SHA256/size and actual verification results. Each listed prerequisite was verified reachable from that origin’s recorded fresh default. An entry whose header lists no prerequisites is explicitly recorded as `NO_COMMIT_PREREQUISITES_IN_BUNDLE_HEADER`; no missing-prerequisite assumption is imposed on an orphaned snapshot.

## Restore into a separate local copy

For an entry with prerequisites, clone the origin with normal complete history and fetch its default branch before verifying and importing the bundle:

```sh
git clone --no-checkout ORIGIN_URL recovery-copy
git -C recovery-copy fetch --no-tags origin DEFAULT_BRANCH
git -C recovery-copy bundle verify /absolute/path/ORIGIN.bundle
git -C recovery-copy fetch /absolute/path/ORIGIN.bundle \
  'refs/heads/*:refs/heads/recovered/*'
```

Use the actual values from the manifest. If verification reports missing prerequisites, fetch those recorded commits from the origin first; do not bypass verification. A bundle with no prerequisites can instead be verified/imported into an empty local Git repository. `git bundle list-heads ORIGIN.bundle` lists the exact preserved refs. Importing into `recovered/` does not replace main or check out the retained changes.

All bundles passed `git bundle verify`, exact `list-heads`, and unbundle/pack integrity checks. The recorded basic secret-marker scan ran before staging and never logged values. `BUILD-FAILED.json` preserves an initial local pack-size inspection failure; the inspection was corrected to use reconstructed blob sizes and every final bundle was verified. No runtime tests or adoption are claimed.
