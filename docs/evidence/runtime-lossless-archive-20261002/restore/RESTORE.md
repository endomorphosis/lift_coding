# Restore an archived runtime bundle

This store preserves exact raw tar headers/PAX/link records, contents, padding and end records, plus original gzip headers/trailers. The retained ARM64 codec statically links zlib1.3 and libc and has no dynamic loader dependency. Standard zlib decoding is used only to read content blobs; compressed output uses the pinned helper. Qualification does not assert cross-platform portability.

Keep this entire store and the external SHA256 of SEALED.json. Verify that seal, the chosen entry in archive-index.json, the recipe, restorer source and codec hashes before executing. Original per-bundle manifests are retained under manifests/. Create a fresh destination directory owned by you with mode0700. Rehydrate using the preserved Python script, supplying the expected values from the reviewed index and seal:

    python3 STORE/restore/archive_cas.py --store STORE --recipe STORE/recipes/SLUG.jsonl --codec STORE/codec/deflate1 --codec-sha256 CODEC_SHA256 --expected-recipe-sha256 RECIPE_SHA256 --expected-archive-sha256 ORIGINAL_SHA256 --restore-output PRIVATE_DEST/runtime.tar.gz --result PRIVATE_DEST/receipt.json

The output path must not exist. The program verifies every referenced content blob, reconstructs and hashes the full compressed archive, fsyncs an exclusive temporary file, and publishes it without overwriting another file. The original archive is never consulted. Check the resulting receipt and independently hash the resulting file. Restore the recorded filesystem metadata separately when desired; those metadata are recorded in the external qualification summary and do not alter archive bytes.

SEALED.json is the durability barrier. All referenced bodies were freshly verified, all retained files fsynced, and every directory including ancestors fsynced. Store directories are read-only; only the empty advisory lock file stays writable. Original archive removal and current activity authorization are separate decisions, not performed by this store or script.
