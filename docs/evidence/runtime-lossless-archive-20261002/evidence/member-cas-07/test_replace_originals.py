import hashlib,json,os,pathlib,tempfile,unittest
from replace_originals import archive_one

class ReplaceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.tmp.name);self.folder=self.root/'bundle';self.folder.mkdir();self.folder.chmod(0o775)
        self.original=self.folder/'runtime.tar.gz';self.original.write_bytes(b'original fixture bytes');st=self.original.stat()
        self.record=dict(original_archive=str(self.original),sha256=hashlib.sha256(self.original.read_bytes()).hexdigest(),bytes=st.st_size,
            device=st.st_dev,inode=st.st_ino,mtime_ns=st.st_mtime_ns,uid=st.st_uid,gid=st.st_gid,mode=oct(st.st_mode&0o777))
        self.reference={'schema':'synthetic-reference-for-transaction-test','sha256':self.record['sha256']}
    def tearDown(self):self.tmp.cleanup()
    def test_exact_owned_original_replaced_only_after_reference_durable(self):
        sentinel=self.folder/'manifest.json';sentinel.write_bytes(b'unchanged manifest')
        result=archive_one(self.record,self.reference,lambda:None)
        self.assertTrue(result['reference_durable_before_original_unlink']);self.assertFalse(self.original.exists())
        self.assertEqual(json.loads((self.folder/'runtime.tar.gz.cas.json').read_bytes()),self.reference)
        self.assertEqual(sentinel.read_bytes(),b'unchanged manifest');self.assertEqual(self.folder.stat().st_mode&0o777,0o775)
    def test_same_length_wrong_hash_keeps_original(self):
        self.original.write_bytes(b'x'*self.record['bytes']);os.utime(self.original,ns=(self.record['mtime_ns'],self.record['mtime_ns']))
        with self.assertRaisesRegex(ValueError,'exact hash'):archive_one(self.record,self.reference,lambda:None)
        self.assertTrue(self.original.exists());self.assertFalse((self.folder/'runtime.tar.gz.cas.json').exists())
    def test_existing_sidecar_refuses_without_overwrite_or_unlink(self):
        sidecar=self.folder/'runtime.tar.gz.cas.json';sidecar.write_bytes(b'prior reference')
        with self.assertRaises(FileExistsError):archive_one(self.record,self.reference,lambda:None)
        self.assertTrue(self.original.exists());self.assertEqual(sidecar.read_bytes(),b'prior reference');self.assertFalse(list(self.folder.glob('*.pending')))
    def test_cancellation_before_commit_retains_original_and_modes(self):
        def cancelled():raise TimeoutError('cancelled fixture')
        with self.assertRaises(TimeoutError):archive_one(self.record,self.reference,cancelled)
        self.assertTrue(self.original.exists());self.assertEqual(self.folder.stat().st_mode&0o777,0o775)

if __name__=='__main__':unittest.main(verbosity=2)
