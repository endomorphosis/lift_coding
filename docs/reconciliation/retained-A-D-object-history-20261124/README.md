# Retained worktree object histories

These are historical archives, not adopted source code, launch controls, statutory
review, or proof/model qualification. Existing product files and repository history
were not replaced. The archive preserves all exact objects missing from the two
specified published base commits and needed by287 retained tips. Six historical
large data blobs are included. Chunking bounds individual archive files; it does
not remove or rewrite any original Git object.

`manifest.json` pins ordered chunks, complete pack hashes, exact object inventories,
retained tips, prerequisites, and actual private restore evidence. The original
source-ref and object-difference observations are retained as inert `.DATA` files;
their local paths and clocks are historical, not current authority.

## Restore without checking out or running archived code

Use an existing clone of the corresponding published base repository, with its
base commit and objects available locally. No network is necessary for the steps
below. Work in a new destination. Replace FAMILY with `accelerate` or `datasets`.
The shell variables are examples and confer no execution or admission permission.

```sh
archive_dir=/absolute/path/to/this/archive
family=accelerate
base_repo=/absolute/path/to/existing/base/clone
restore_dir=/absolute/path/to/NEW-empty-destination.git
test ! -e "$restore_dir" || exit 1
git init --bare "$restore_dir"
base_objects="$(git -C "$base_repo" rev-parse --path-format=absolute --git-common-dir)/objects"
```

First verify every chunk's size/SHA256 and their ordered concatenation against the
manifest. Filenames are zero padded; concatenate only that family's listed chunks:

```sh
cat "$archive_dir/$family/"*.pack.part-*.DATA > "$restore_dir/objects/pack/archive.pack"
sha256sum "$restore_dir/objects/pack/archive.pack"
GIT_NO_LAZY_FETCH=1 GIT_ALTERNATE_OBJECT_DIRECTORIES="$base_objects"   git -C "$restore_dir" index-pack --strict "$restore_dir/objects/pack/archive.pack"
git -C "$restore_dir" verify-pack -v "$restore_dir/objects/pack/archive.idx"
```

The reported SHA256 must equal `pack_sha256`; `verify-pack` object IDs must equal
the complete `exact-object-IDs.DATA` inventory, not merely contain one expected
tip. Our private qualification performed these checks, plus a local-only
`cat-file --batch-check` before setting alternates, for every archived object.

For complete graph connectivity, supply only the corresponding published base
object store, then check all retained tips. The base is an explicit prerequisite;
this archive does not contain unrelated objects already available from that base.

```sh
printf '%s\n' "$base_objects" > "$restore_dir/objects/info/alternates"
GIT_NO_LAZY_FETCH=1 git -C "$restore_dir" fsck --connectivity-only --no-dangling   $(cat "$archive_dir/$family/retained-tip-IDs.DATA")
```

Do not automatically checkout, execute, merge, replay, or treat these old failed,
superseded, or unselected branches as approved work. A recovery ref can be created
explicitly with `git update-ref` only after selecting the desired historical tip.
The original current branches, worktrees, and failure evidence remain intact.
