# Historical recovery commit identities — NOT ADOPTED

These four files preserve exact Git commit-object bytes from the Kit and Swiss recovery histories. They are not source-code overlays, independent repository bundles, a legal review, test results, or an adoption into either main branch. Their trees and blobs are already represented by the published histories listed in manifest.json; the retained commit identities themselves are different.

Restoration requires an already populated local repository of the correct project with the listed published-main commit and its reachable objects available. No network, checkout, merge, cherry-pick, or branch-main update is implied. This archive contains commit metadata only; its tree/blob prerequisites are intentionally not duplicated.

For each matching .commit.DATA file, first run `git hash-object -t commit --stdin < FILE` without -w and compare the printed identity to the manifest. Then run `git hash-object -t commit -w --stdin < FILE`. Restore both selected commits for that project (the later selected commit refers to the earlier one). `git cat-file commit OID` must return the exact archived bytes. Finally run `git fsck --connectivity-only --no-reflogs --no-dangling OID1 OID2`. An optional explicitly named archive ref may retain the historical tip; do not replace main or any existing ref.

Preparation proved that fresh private bare banks without alternates first restored the raw commit objects into actual loose object files and returned exact cat-file bytes. Only afterward did those banks receive a private alternate to the corresponding already populated PUB object store for connectivity checking. Those temporary restore banks and local alternates are not publication payloads or self-contained portable repositories.

The failed bundle preflight f6d67d is retained separately: rev-list --objects exclusion output was conservatively larger than the true novel object set, so it was not used as a content-difference proof. No bundle was created by that failed preflight.
