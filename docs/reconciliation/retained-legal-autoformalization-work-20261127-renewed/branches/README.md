# Historical branch restoration

Each bundle is incremental over its recorded public main base. Initialize a bare Git store with those base objects, run git bundle verify, then fetch the retained refs from the bundle. The publisher repeated restoration in new private stores and verified every expected tip and complete incremental object traversal against the recorded base without network. Some local base stores are partial clones, so a complete clone of the recorded public base is required when restoring elsewhere. The additional Accelerator raw commit has an exact source tree already on public main. Restore its published bases and the A34 bundle before importing that commit with git hash-object -t commit -w --stdin.

The restored branches remain historical alternatives. This archive does not install them as active application code. Marker-review records are retained and no new copy of the previously archived 2GiB dataset is included.
