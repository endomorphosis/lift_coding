# Full-depth worktree and branch recovery

The audit checked /tmp, /home/barberb, registered worktrees and nested project submodules. The eight primary repository families contribute 10,087 observed repository/commit pairs, all accounted for: 2,104 in compared published main ancestry, 206 in prior verified archives, 7,693 in the newly restored Portland archive and 84 in the other newly restored bundles. Original failed-validation labels remain unchanged.

This publication preserves additional working-copy variants as inert .DATA records. The additional-worktree packet has 123 unique payloads and 523 restore mappings. The root-authoring packet has 2,045 unique plaintext payloads and 12,832 source mappings. Its 365 marker-held mappings are retained in an encrypted archive covering 20 distinct source files. The manifests record exact byte hashes, historical aliases, explicit copied/generated exclusions and uncertain provenance.

One historical Accelerate commit includes a large dataset with unresolved credential-like text. Its exact verified Git bundle is encrypted. All plaintext recovery bundles passed restore checks; both encrypted archives were decrypted locally and matched their original SHA-256 hashes. The passphrase is stored only in the protected local file named in FINAL-REPORT.json and encrypted-recovery.json. It must be retained to recover those archives.

For a plain Git bundle, start from its recorded published base, run git bundle verify, and fetch the advertised refs into recovery branches. For encrypted records, concatenate parts in manifest order, decrypt with GnuPG using the local passphrase file, and check the original archive hash before restoring. These archives preserve historical or superseded work; they do not install it as maintained runtime code.

Original working files, staged contents and branch references were preserved. Publication uses normal fast-forward pushes with [skip ci]. No hosted CI, model execution, database query or new scientific qualification is part of this recovery. Scan exclusions include dependency caches, virtualenvs, symlinks and 176 permission-denied paths (including 105 under project artifacts), plus the explicitly recorded synthetic/generated classes.

The permission-denied paths remain unverified. Their exact paths are in full-depth-discovery-metadata.json. The current account cannot use unattended privileged reads. This is an observed-work recovery report, not a claim that inaccessible filesystem contents were inspected.

The nine additional owned nested repositories passed fresh GitHub main-ancestry checks for all 73 observed commits and fresh status checks in all 41 initialized copies. Only untracked coordination lockfiles were present. This brings accounted-for owned repository/commit pairs to 10,160. Exact refs and receipts are in nested-owned-final-proof.json. No dependency pin upgrade was needed to preserve that work.
