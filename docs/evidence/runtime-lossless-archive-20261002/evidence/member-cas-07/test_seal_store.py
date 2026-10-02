import json,pathlib,shutil,subprocess,sys,unittest
from unittest.mock import patch
import seal_store as seal_module
import archive_cas as cas
from seal_store import seal_store
from test_archive_cas import ArchiveTests

class SealTests(unittest.TestCase):
    def setUp(self):
        self.fixture=ArchiveTests();self.fixture.setUp();self.root=self.fixture.root
        archive,manifest=self.fixture.archive();self.store_root=self.root/'store';store=cas.Store(self.store_root)
        try:self.capture=cas.capture(archive=archive,manifest=manifest,store=store,slug='one')
        finally:store.close()
        manifests=self.store_root/'manifests';manifests.mkdir(mode=0o700);shutil.copyfile(manifest,manifests/'one.json');(manifests/'one.json').chmod(0o600)
        codecs=self.store_root/'codec';codecs.mkdir(mode=0o700)
        source=pathlib.Path(__file__).parent/'store/codec/deflate1';shutil.copyfile(source,codecs/'deflate1');(codecs/'deflate1').chmod(0o500)
        self.accepted=[dict(slug='one',recipe_sha256=self.capture['recipe_sha256'],archive_sha256=cas.digest_file(archive),
            archive_bytes=archive.stat().st_size,manifest_sha256=cas.digest_file(manifest),codec_sha256=cas.digest_file(codecs/'deflate1'))]
    def tearDown(self):self.fixture.tearDown()
    def test_durable_seal_replays_in_fresh_process(self):
        result=seal_store(self.store_root,self.accepted);self.assertTrue(result['qualified'])
        self.assertEqual(self.store_root.stat().st_mode&0o777,0o500)
        recipe=self.store_root/'recipes/one.jsonl';output=self.root/'restore.gz';report=self.root/'replay.json'
        command=[sys.executable,str(pathlib.Path(cas.__file__)), '--store',str(self.store_root),'--recipe',str(recipe),
            '--codec',str(self.store_root/'codec/deflate1'),'--codec-sha256',self.accepted[0]['codec_sha256'],
            '--expected-recipe-sha256',self.accepted[0]['recipe_sha256'],'--expected-archive-sha256',self.accepted[0]['archive_sha256'],
            '--restore-output',str(output),'--result',str(report)]
        completed=subprocess.run(command,capture_output=True,text=True,timeout=10);self.assertEqual(completed.returncode,0,completed.stdout+completed.stderr)
        self.assertEqual(cas.digest_file(output),self.accepted[0]['archive_sha256'])
        self.assertTrue(json.loads(report.read_text())['qualified'])
    def test_wrong_accepted_recipe_refuses_without_seal(self):
        self.accepted[0]['recipe_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'accepted recipe'):seal_store(self.store_root,self.accepted)
        self.assertFalse((self.store_root/'SEALED.json').exists())
    def test_corrupt_referenced_payload_refuses_without_seal(self):
        next((self.store_root/'blobs').iterdir()).write_bytes(b'corrupt')
        with self.assertRaises((ValueError,cas.zlib.error)):seal_store(self.store_root,self.accepted)
        self.assertFalse((self.store_root/'SEALED.json').exists())
    def test_group_writable_payload_refused(self):
        next((self.store_root/'blobs').iterdir()).chmod(0o660)
        with self.assertRaisesRegex(ValueError,'private retained file'):seal_store(self.store_root,self.accepted)
        self.assertFalse((self.store_root/'SEALED.json').exists())
    def test_wrong_codec_binding_refused(self):
        self.accepted[0]['codec_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'standalone codec changed'):seal_store(self.store_root,self.accepted)
    def test_recipe_changed_after_verification_before_fsync_walk_refused(self):
        original=seal_module.os.fwalk;mutated=False
        def changed(*args,**kwargs):
            nonlocal mutated
            if not mutated:
                mutated=True;p=self.store_root/'recipes/one.jsonl';p.write_bytes(p.read_bytes()+b'\n')
            return original(*args,**kwargs)
        with patch.object(seal_module.os,'fwalk',changed),self.assertRaisesRegex(ValueError,'final durable file differs'):seal_store(self.store_root,self.accepted)
        self.assertFalse((self.store_root/'SEALED.json').exists())
    def test_blob_changed_after_verification_before_fsync_walk_refused(self):
        original=seal_module.os.fwalk;mutated=False
        def changed(*args,**kwargs):
            nonlocal mutated
            if not mutated:
                mutated=True;p=next((self.store_root/'blobs').iterdir());p.write_bytes(b'new stable but unverified body')
            return original(*args,**kwargs)
        with patch.object(seal_module.os,'fwalk',changed),self.assertRaisesRegex(ValueError,'final durable file differs'):seal_store(self.store_root,self.accepted)
        self.assertFalse((self.store_root/'SEALED.json').exists())

if __name__=='__main__':unittest.main(verbosity=2)
