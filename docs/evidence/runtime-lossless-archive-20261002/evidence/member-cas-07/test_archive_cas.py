import contextlib,gzip,hashlib,io,json,pathlib,tarfile,tempfile,unittest
from unittest.mock import patch
import archive_cas as cas

class ArchiveTests(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.tmp.name)
    def tearDown(self):self.tmp.cleanup()
    def archive(self,name='one',change=b'first',mtime=123):
        p=self.root/name;p.mkdir();archive=p/'runtime.tar.gz';records=[]
        shared=b'common immutable content\x00'*200
        entries=[('shared.txt',shared),('other.txt',change),('long/'+('directory/'*25)+'leaf.py',b'long name contents'),('../../never-extracted.txt',b'inert archive path')]
        with archive.open('wb') as raw,gzip.GzipFile(fileobj=raw,filename='runtime.tar',mode='wb',mtime=mtime,compresslevel=1) as gz,tarfile.open(fileobj=gz,mode='w',format=tarfile.PAX_FORMAT) as tar:
            for path,data in entries:
                info=tarfile.TarInfo(path);info.size=len(data);info.uid=info.gid=0;info.uname=info.gname='root';info.mtime=0
                tar.addfile(info,io.BytesIO(data));records.append(dict(path=path,bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),mode=info.mode))
            info=tarfile.TarInfo('hardlink.txt');info.type=tarfile.LNKTYPE;info.linkname='shared.txt';tar.addfile(info)
            records.append(dict(path='hardlink.txt',bytes=len(shared),sha256=hashlib.sha256(shared).hexdigest(),mode=info.mode))
        manifest=p/'manifest.json';manifest.write_text(json.dumps(dict(archive_sha256=cas.digest_file(archive),files=records)))
        return archive,manifest
    @contextlib.contextmanager
    def store(self):
        value=cas.Store(self.root/'store')
        try:yield value
        finally:value.close()
    def captured(self,store):
        archive,manifest=self.archive();row=cas.capture(archive=archive,manifest=manifest,store=store,slug='one')
        return archive,manifest,pathlib.Path(row['recipe']),row
    def test_exact_raw_tar_pax_hardlink_and_gzip_metadata(self):
        with self.store() as store:
            a,m,recipe,row=self.captured(store);result=cas.reconstruct(recipe=recipe,store=store)
            self.assertEqual(result['archive_sha256'],cas.digest_file(a));self.assertTrue(result['exact']);self.assertGreater(result['members'],5)
            header=json.loads(recipe.read_text().splitlines()[0]);self.assertEqual(int.from_bytes(bytes.fromhex(header['gzip_header_hex'])[4:8],'little'),123)
            self.assertFalse((self.root.parent/'never-extracted.txt').exists())
    def test_replay_needs_only_recipe_and_cas(self):
        with self.store() as store:
            a,m,recipe,row=self.captured(store);a.rename(a.with_suffix('.saved'));m.rename(m.with_suffix('.saved'))
            self.assertTrue(cas.reconstruct(recipe=recipe,store=store)['exact'])
    def test_reuses_shared_bytes_and_preserves_distinct_gzip_timestamps(self):
        with self.store() as store:
            a,m,recipe,row=self.captured(store);second,manifest=self.archive('two',b'second',mtime=456)
            nextrow=cas.capture(archive=second,manifest=manifest,store=store,slug='two')
            self.assertEqual(nextrow['new_blobs'],1);other=cas.reconstruct(recipe=pathlib.Path(nextrow['recipe']),store=store)
            self.assertNotEqual(other['archive_sha256'],row['archive_sha256']);self.assertTrue(other['exact'])
    def test_missing_blob_refused(self):
        with self.store() as store:
            a,m,recipe,row=self.captured(store);next(store.blobs.iterdir()).unlink()
            with self.assertRaises(ValueError):cas.reconstruct(recipe=recipe,store=store)
    def test_tampered_blob_refused(self):
        with self.store() as store:
            a,m,recipe,row=self.captured(store);next(store.blobs.iterdir()).write_bytes(b'not zlib')
            with self.assertRaises((ValueError,cas.zlib.error)):cas.reconstruct(recipe=recipe,store=store)
    def test_changed_recipe_body_size_refused(self):
        with self.store() as store:
            a,m,recipe,row=self.captured(store);rows=[json.loads(v) for v in recipe.read_text().splitlines()];rows[1]['body_bytes']+=1
            recipe.write_text(''.join(json.dumps(v)+'\n' for v in rows))
            with self.assertRaisesRegex(ValueError,'size join'):cas.reconstruct(recipe=recipe,store=store)
    def test_gzip_timestamp_tamper_refused_by_original_digest(self):
        with self.store() as store:
            a,m,recipe,row=self.captured(store);rows=[json.loads(v) for v in recipe.read_text().splitlines()]
            header=bytearray.fromhex(rows[0]['gzip_header_hex']);header[4]^=1;rows[0]['gzip_header_hex']=header.hex();recipe.write_text(''.join(json.dumps(v)+'\n' for v in rows))
            with self.assertRaisesRegex(ValueError,'original gzip'):cas.reconstruct(recipe=recipe,store=store)
    def test_zlib_profile_mismatch_refused(self):
        with self.store() as store:
            a,m,recipe,row=self.captured(store);recipe.write_text(recipe.read_text().replace('"deflate_level":1','"deflate_level":9'))
            with self.assertRaisesRegex(ValueError,'pinned deflate'):cas.reconstruct(recipe=recipe,store=store)
    def test_wrong_archive_manifest_refused(self):
        with self.store() as store:
            a,m=self.archive();r=json.loads(m.read_text());r['archive_sha256']='0'*64;m.write_text(json.dumps(r))
            with self.assertRaisesRegex(ValueError,'archive/manifest'):cas.capture(archive=a,manifest=m,store=store,slug='one')
    def test_staging_write_ceiling_refused(self):
        with self.store() as store:
            a,m=self.archive()
            with patch.object(cas,'MAX_APPARENT',20),self.assertRaisesRegex(ValueError,'write ceiling'):cas.capture(archive=a,manifest=m,store=store,slug='one')
    def test_store_exclusive_lock(self):
        with self.store() as store:
            with self.assertRaises(BlockingIOError):cas.Store(store.root)
    def test_symbolic_blob_refused(self):
        with self.store() as store:
            a,m,recipe,row=self.captured(store);blob=next(store.blobs.iterdir());target=self.root/'independent';blob.rename(target);blob.symlink_to(target)
            with self.assertRaisesRegex(ValueError,'nonsymlink'):cas.reconstruct(recipe=recipe,store=store)
    def test_statically_pinned_codec_exact_materialization(self):
        codec=pathlib.Path(__file__).parent/'store/codec/deflate1'
        with self.store() as store:
            a,m,recipe,row=self.captured(store);out=self.root/'restored.tar.gz'
            result=cas.reconstruct(recipe=recipe,store=store,codec=codec,expected_codec_sha256=cas.digest_file(codec),
                expected_recipe_sha256=cas.digest_file(recipe),expected_archive_sha256=cas.digest_file(a),restore_output=out)
            self.assertTrue(result['exclusive_verified_publication']);self.assertEqual(out.read_bytes(),a.read_bytes())
            with self.assertRaisesRegex(ValueError,'fresh canonical'):cas.reconstruct(recipe=recipe,store=store,codec=codec,
                expected_codec_sha256=cas.digest_file(codec),expected_recipe_sha256=cas.digest_file(recipe),
                expected_archive_sha256=cas.digest_file(a),restore_output=out)
    def test_wrong_external_original_refuses_materialization(self):
        codec=pathlib.Path(__file__).parent/'store/codec/deflate1'
        with self.store() as store:
            a,m,recipe,row=self.captured(store);out=self.root/'restored.tar.gz'
            with self.assertRaisesRegex(ValueError,'external original'):cas.reconstruct(recipe=recipe,store=store,codec=codec,
                expected_codec_sha256=cas.digest_file(codec),expected_recipe_sha256=cas.digest_file(recipe),
                expected_archive_sha256='0'*64,restore_output=out)
            self.assertFalse(out.exists());self.assertFalse(list(self.root.glob('.archive-restore-*')))
    def test_wrong_codec_hash_refused(self):
        codec=pathlib.Path(__file__).parent/'store/codec/deflate1'
        with self.store() as store:
            a,m,recipe,row=self.captured(store)
            with self.assertRaisesRegex(ValueError,'codec binary hash'):cas.reconstruct(recipe=recipe,store=store,codec=codec,expected_codec_sha256='0'*64)
    def test_nonprivate_store_parent_refused(self):
        self.root.chmod(0o775)
        with self.assertRaisesRegex(ValueError,'non-writable-by-others'):cas.Store(self.root/'store')
    def test_static_codec_cleanup_preserves_primary_corruption_error(self):
        codec=pathlib.Path(__file__).parent/'store/codec/deflate1'
        with self.store() as store:
            a,m,recipe,row=self.captured(store);next(store.blobs.iterdir()).write_bytes(b'corrupt')
            with self.assertRaises(cas.zlib.error):cas.reconstruct(recipe=recipe,store=store,codec=codec,expected_codec_sha256=cas.digest_file(codec))
    def test_static_replay_independent_of_current_python_zlib_version(self):
        codec=pathlib.Path(__file__).parent/'store/codec/deflate1'
        with self.store() as store:
            a,m,recipe,row=self.captured(store)
            with patch.object(cas.zlib,'ZLIB_RUNTIME_VERSION','future-version'):
                self.assertTrue(cas.reconstruct(recipe=recipe,store=store,codec=codec,expected_codec_sha256=cas.digest_file(codec))['exact'])
    def test_shared_output_directory_refused_before_publication(self):
        codec=pathlib.Path(__file__).parent/'store/codec/deflate1'
        with self.store() as store:
            a,m,recipe,row=self.captured(store);shared=self.root/'shared';shared.mkdir();shared.chmod(0o775)
            with self.assertRaisesRegex(ValueError,'non-writable-by-others'):cas.reconstruct(recipe=recipe,store=store,codec=codec,
                expected_codec_sha256=cas.digest_file(codec),expected_recipe_sha256=cas.digest_file(recipe),
                expected_archive_sha256=cas.digest_file(a),restore_output=shared/'output.gz')
            self.assertEqual(list(shared.iterdir()),[])

if __name__=='__main__':unittest.main(verbosity=2)
