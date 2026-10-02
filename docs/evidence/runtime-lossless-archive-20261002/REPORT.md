# Reversible runtime archive compaction — 2026-10-02

Fifteen task-owned historical runtime bundles were converted into a sealed shared content store and replaced by durable `runtime.tar.gz.cas.json` restoration references. Every original compressed archive was reconstructed byte for byte before replacement. All original manifests remain at their original paths.

The replacement unlinked **18,089,218,048 allocated bytes**. The store occupies **2,086,400,000 allocated bytes**, giving **16,002,818,048 bytes (14.90 GiB) net saving** relative to the original archive population. The immediate observed free-space increase was **18,084,880,384 bytes** because the store had already been created. Disk usage excluding reserved filesystem blocks fell from **94.7086% to 94.2360%**, displayed by psutil as **94.2%**. Host admission policies and thresholds were unchanged.

## Qualification and scope

- All **15** archive digests and byte lengths matched exact reconstruction with the retained static codec.
- **19** synthetic restorer controls, **7** durable-seal controls and **4** replacement-transaction controls passed. Repeated suite executions are not additional tests.
- The final seal freshly verified **27,925** referenced bodies and bound **27,966** retained files, including exact recipes, original manifests, restore source, codec, source/licensing provenance and archive index. File and directory durability barriers completed before original unlink.
- A fresh process executed the restorer preserved inside the sealed store, materialized a complete 1,205,822,463-byte archive without reading its original, and an independent reread matched the original SHA256. Only that generated verification output was removed.
- Final native seal/replay took **164.96 s** under a 3 CPU / 1 GiB / 3 child-process reservation; replacement took **12.78 s** under a 1 CPU / 512 MiB / 1 child-process reservation. Both released their leases; the seal controller reaped its children. Staging stayed within the declared 5 GiB envelope.
- Immediately before unlink, the transaction refreshed visible process/Docker references and checked each original through an opened descriptor against its recorded device, inode, size, time, ownership, mode, link count and full hash. It published/fsynced a no-overwrite sidecar first. A post-replacement audit checked all 15 sidecars, original absence, retained original manifests, recipes and unchanged seal.

The accessible activity checks found no matching process references or Docker mounts. Permission-limited process and link visibility remains incomplete. Some archived historical runs were only prepared or superseded; these receipts qualify byte preservation and space recovery, not their benchmark scores.

## Restore

`restore-manifest.json` records all original paths, exact archive hashes, sidecars, recipes, store location and the independently retained seal/source/codec hashes. `restore/RESTORE.md` gives the command. Keep the **entire local store**; this compact Git evidence package intentionally excludes content blobs, large recipes, binaries and the full seal inventory.

Verify the external seal, archive-index, recipe, retained restorer and codec hashes. Create a fresh canonical owned output directory with mode `0700`; the output must not exist. Execute the retained restorer with the pinned codec and expected hashes, then independently hash the restored archive. Restore recorded file ownership/mode/timestamps separately if needed. The content store is required; the sidecar alone is not an archive copy.

The preserved codec is a statically linked **Linux ARM64 zlib 1.3** executable without a dynamic loader dependency. Standard Python zlib decoding reads content blobs; output compression uses the pinned helper. The Python-only compressor fallback requires its declared zlib version and still requires exact original-hash agreement. C/Python source, build inputs and licenses are retained, but rebuilding on another platform/toolchain requires fresh exact-output qualification; portability is not claimed.

The seal SHA256 is `1b22f575bb8c05929b77f6f17d6ed333b20eff0f42beee5f45235b22ada84c26`.

## Evidence

`evidence/` retains measured native attempts, refused admissions, failed preliminary controls, final passing controls, historical producer snapshots, independent activity reviews and final replacement receipts. Early gzip-stream delta compression was ineffective (3.2% saving); its exact-verified generated patch was removed while originals were still retained. The member-content store supplies the actual recovery reported here.

`package-manifest.json` binds every packaged file by SHA256. The earlier experiment manifest remains historical and is not presented as the final manifest. No source checkout, checkpoint, unrelated cache or benchmark result was deleted by this archival task.
