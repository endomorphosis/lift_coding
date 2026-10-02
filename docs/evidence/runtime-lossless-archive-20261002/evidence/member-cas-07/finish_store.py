"""Join all native qualifications, preserve recipes/tools, and seal private store."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys,time
import archive_cas as cas
from seal_store import seal_store

root=Path(__file__).resolve().parent;store_root=root/'store';started=time.monotonic()
report={'schema':'complete-runtime-archive-store-qualification@1','qualified':False,'original_archives_removed':False}
try:
    selected=json.loads((root.parent/'manifest-overlap.json').read_text())['bundles']+json.loads((root.parent/'additional-candidates.json').read_text())['candidates']
    accepted=[];raw_total=allocated_total=0;rows=[];codec=store_root/'codec/deflate1';codec_sha=cas.digest_file(codec)
    producers={cas.digest_file(path):str(path) for path in (root/'archive_cas.py',root/'archive_cas_static01.py')}
    for item in selected:
        original=Path(item['path']);slug=original.name
        attempt='static01' if slug=='terminal-native-runtime-full-v4' else 'static03' if slug in ('runtime-01','runtime-02','runtime-03','runtime-04') else 'static02'
        run=root/('runs-'+attempt)/slug;envelope=json.loads((run/'envelope.json').read_bytes());worker=json.loads((run/'worker-result.json').read_bytes())
        cas.require(envelope['qualified'] and envelope['reaped'] and envelope['native_admission']['released'] and worker['qualified'],'complete released native qualification required')
        cas.require(envelope['implementation_sha256'] in producers,'exact retained tested producer required')
        replay=worker['reconstruction'];cas.require(replay['exact'] and not replay['original_archive_read_during_replay'] and replay['codec_sha256']==codec_sha,'standalone independent exact replay required')
        cas.require(replay['archive_sha256']==item['archive_sha256_recorded'] and replay['archive_bytes']==item['archive_bytes'],'independent inventory/replay join')
        manifest=original/'manifest.json';archive=original/'runtime.tar.gz';cas.regular(archive)
        cas.require(cas.digest_file(manifest)==item['manifest_sha256'] and cas.digest_file(archive)==item['archive_sha256_recorded'],'original bytes changed after qualification')
        recipe=store_root/'recipes'/(slug+'.jsonl');cas.require(cas.digest_file(recipe)==replay['recipe_sha256'],'qualified recipe changed')
        st=archive.stat();raw_total+=st.st_size;allocated_total+=st.st_blocks*512
        accepted.append(dict(slug=slug,archive_sha256=replay['archive_sha256'],archive_bytes=replay['archive_bytes'],recipe_sha256=replay['recipe_sha256'],
            manifest_sha256=item['manifest_sha256'],codec_sha256=codec_sha,source_archive=str(archive),source_manifest=str(manifest)))
        rows.append(dict(slug=slug,original_archive=str(archive),sha256=replay['archive_sha256'],bytes=st.st_size,allocated_bytes=st.st_blocks*512,
            inode=st.st_ino,device=st.st_dev,mtime_ns=st.st_mtime_ns,mode=oct(st.st_mode&0o777),uid=st.st_uid,gid=st.st_gid,
            qualification=str(run),envelope_sha256=cas.digest_file(run/'envelope.json'),worker_result_sha256=cas.digest_file(run/'worker-result.json'),
            historical_tested_producer=producers[envelope['implementation_sha256']]))
    store=cas.Store(store_root)
    try:
        manifests=store_root/'manifests';manifests.mkdir(mode=0o700)
        restore=store_root/'restore';restore.mkdir(mode=0o700)
        for row in accepted:
            source=Path(row['source_manifest']);target=manifests/(row['slug']+'.json');shutil.copyfile(source,target);target.chmod(0o600)
            cas.require(cas.digest_file(target)==row['manifest_sha256'],'preserved manifest copy mismatch')
        for source in (root/'archive_cas.py',root/'seal_store.py',root/'store/codec/deflate1.c'):
            target=restore/source.name;shutil.copyfile(source,target);target.chmod(0o600)
        index=store_root/'archive-index.json';index.write_text(json.dumps(accepted,indent=2,sort_keys=True)+'\n');index.chmod(0o600)
        instructions=store_root/'RESTORE.md'
        instructions.write_text('''# Restore an archived runtime bundle

This store preserves exact raw tar headers/PAX/link records, contents, padding and end records, plus original gzip headers/trailers. The retained ARM64 codec statically links zlib1.3 and libc and has no dynamic loader dependency. Standard zlib decoding is used only to read content blobs; compressed output uses the pinned helper. Qualification does not assert cross-platform portability.

Keep this entire store and the external SHA256 of SEALED.json. Verify that seal, the chosen entry in archive-index.json, the recipe, restorer source and codec hashes before executing. Original per-bundle manifests are retained under manifests/. Create a fresh destination directory owned by you with mode0700. Rehydrate using the preserved Python script, supplying the expected values from the reviewed index and seal:

    python3 STORE/restore/archive_cas.py --store STORE --recipe STORE/recipes/SLUG.jsonl --codec STORE/codec/deflate1 --codec-sha256 CODEC_SHA256 --expected-recipe-sha256 RECIPE_SHA256 --expected-archive-sha256 ORIGINAL_SHA256 --restore-output PRIVATE_DEST/runtime.tar.gz --result PRIVATE_DEST/receipt.json

The output path must not exist. The program verifies every referenced content blob, reconstructs and hashes the full compressed archive, fsyncs an exclusive temporary file, and publishes it without overwriting another file. The original archive is never consulted. Check the resulting receipt and independently hash the resulting file. Restore the recorded filesystem metadata separately when desired; those metadata are recorded in the external qualification summary and do not alter archive bytes.

SEALED.json is the durability barrier. All referenced bodies were freshly verified, all retained files fsynced, and every directory including ancestors fsynced. Store directories are read-only; only the empty advisory lock file stays writable. Original archive removal and current activity authorization are separate decisions, not performed by this store or script.
''');instructions.chmod(0o600)
        report['prepared_staging']=cas.inventory(store_root)
    finally:store.close()
    (root/'accepted-archives.json').write_text(json.dumps(accepted,indent=2,sort_keys=True)+'\n')
    expected_files={
        'restore/archive_cas.py':cas.digest_file(root/'archive_cas.py'),
        'restore/seal_store.py':cas.digest_file(root/'seal_store.py'),
        'restore/deflate1.c':cas.digest_file(store_root/'codec/deflate1.c'),
        'archive-index.json':cas.digest_file(store_root/'archive-index.json'),
    }
    report['seal']=seal_store(store_root,accepted,expected_files)
    # Execute the retained program in a fresh process and materialize one archive.
    chosen=next(row for row in accepted if row['slug']=='terminal-native-runtime-full-v4')
    cas.require(cas.inventory(store_root)['allocated_bytes']+chosen['archive_bytes']+16*cas.BLOCK<cas.MAX_STAGE,'store plus restore exceeds complete experiment staging bound')
    post=root/'post-seal';post.mkdir(mode=0o700);restored=post/'runtime.tar.gz'
    command=[sys.executable,str(store_root/'restore/archive_cas.py'),'--store',str(store_root),
        '--recipe',str(store_root/'recipes'/(chosen['slug']+'.jsonl')),'--codec',str(codec),'--codec-sha256',codec_sha,
        '--expected-recipe-sha256',chosen['recipe_sha256'],'--expected-archive-sha256',chosen['archive_sha256'],
        '--restore-output',str(restored),'--result',str(post/'receipt.json')]
    with (post/'run.log').open('xb') as log:completed=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=120)
    cas.require(completed.returncode==0,'retained post-seal program failed')
    report['post_seal_replay']=json.loads((post/'receipt.json').read_bytes());cas.require(report['post_seal_replay']['qualified'],'post-seal replay unqualified')
    before=cas.regular(restored);digest=cas.digest_file(restored);cas.require(cas.regular(restored)==before and digest==chosen['archive_sha256'] and before[2]==chosen['archive_bytes'],'independent materialized output differs')
    report['post_seal_independent_output_check']=dict(sha256=digest,bytes=before[2],retained_program=str(store_root/'restore/archive_cas.py'),
        retained_program_sha256=cas.digest_file(store_root/'restore/archive_cas.py'),command=command,
        removed_only_generated_restore=str(restored))
    restored.unlink()
    report.update(qualified=True,archives=rows,archive_count=len(rows),original_apparent_bytes=raw_total,original_allocated_bytes=allocated_total,
        sealed_store=cas.inventory(store_root),potential_net_allocated_saving=allocated_total-cas.inventory(store_root)['allocated_bytes'])
except BaseException as error:report['error']=dict(type=type(error).__name__,message=str(error))
finally:
    report['seconds']=time.monotonic()-started
    (root/'complete-qualification.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    print(json.dumps({k:report.get(k) for k in ('qualified','archive_count','seconds','potential_net_allocated_saving','error')}),flush=True)
