# Root work recovery

This archive preserves exact versions of untracked source, test drivers, configurations, and documentation found during the November 27 worktree reconciliation. The preserved inputs can be inspected without activating an older implementation. The manifest records the input inventories, the published commits used for exact content matching, and the original relative paths of each byte-identical payload.

Payload filenames use their SHA-256 digest. Verify the length and SHA-256 against `manifest.json` before restoring a copy in a disposable checkout. A payload can map to multiple original paths. Treat an authored-looking path as a recovery lead when it appears inside an older experiment directory.

The scan excluded dependencies, nested Git copies, generated runtime or test outputs, and source copies whose provenance could not be narrowed. Entries with unresolved credential markers are listed by path and digest. Their original bytes remain in local custody. This packet lists its scope and the counts for each omission category.
