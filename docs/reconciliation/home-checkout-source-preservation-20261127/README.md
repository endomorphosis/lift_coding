# Home checkout source preservation

These six files preserve exact uncommitted authoring from direct home Accelerate and Datasets checkouts. The manifest records checkout and live main commits, original paths, byte counts, SHA-256 and Git blob IDs, plus all observed status dispositions.

The Accelerate files preserve historical DuckDB cleanup and pytest temporary-file retention changes. The current DuckDB implementation has moved into the task sources package and has evolved. The Datasets file preserves the July 2026 knowledge graphs hardening plan. Duplicate published and archived source, generated boards, locks and runtime state were excluded. Mixed authored and generated objective execution state was also excluded.

## Recover a source version

Verify the payload byte count and SHA-256 against the manifest. Copy it without its `.DATA` suffix into a separate directory. For a tracked change, recover its recorded checkout preimage with `git cat-file blob CHECKOUT_HEAD_BLOB` in a complete local clone. Compare the recovered file against both that preimage and the recorded current main path before adapting it. Untracked content has no checkout preimage.

The captured files were read back byte-for-byte. A bounded credential-marker scan and Python syntax check ran on the retained inputs. No project code or tests were run.
