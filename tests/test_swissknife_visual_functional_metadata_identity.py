"""Portable metadata identity bounds; no providers, live journals or services."""
import hashlib,json,os
from pathlib import Path
import sys,tempfile,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import swissknife_visual_functional_recovery as recovery
import swissknife_visual_functional_llm as adapter

class MetadataIdentityTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.name=recovery.CANONICAL_TASK_SPEC;self.path=self.root/self.name;self.path.parent.mkdir()
    def large(self,size=1061834):
        value={'schema':'swissknife.visual-functional-taskboard.v1','tasks':[],'padding':''}
        base=json.dumps(value,separators=(',',':')).encode();value['padding']='x'*(size-len(base));data=json.dumps(value,separators=(',',':')).encode();self.assertEqual(len(data),size);self.path.write_bytes(data);return data
    def test_full_r13_size_metadata_hash_is_exact_sha_only(self):
        data=self.large();before=self.path.read_bytes();result=recovery.current_hashes(self.root,[self.name])
        self.assertEqual(result,{self.name:hashlib.sha256(data).hexdigest()});self.assertEqual(self.path.read_bytes(),before)
        self.assertEqual(len(result[self.name]),64);self.assertNotIn('padding',str(result))
    def test_exact_four_mib_bound_allowed(self):
        data=self.large(recovery.MAX_TASK_SPEC_IDENTITY_BYTES)
        self.assertEqual(recovery.current_hashes(self.root,[self.name])[self.name],hashlib.sha256(data).hexdigest())
    def test_over_four_mib_metadata_refused(self):
        self.large(recovery.MAX_TASK_SPEC_IDENTITY_BYTES+1)
        with self.assertRaises(adapter.ModelAdapterError):recovery.current_hashes(self.root,[self.name])
    def test_large_ordinary_and_other_config_paths_still_refused(self):
        data=self.large()
        for name in ('app.py','config/other.json','config/swissknife_visual_functional_tasks-copy.json','docs/plan.json'):
            path=self.root/name;path.parent.mkdir(exist_ok=True);path.write_bytes(data)
            with self.subTest(name=name),self.assertRaises(adapter.ModelAdapterError):recovery.current_hashes(self.root,[name])
    def test_generic_snapshot_and_read_do_not_gain_metadata_exception(self):
        self.large()
        with self.assertRaises(adapter.ModelAdapterError):adapter._snapshot(self.root,self.name)
        with self.assertRaises(adapter.ModelAdapterError):adapter._read(self.root,self.name)
        self.assertEqual(adapter.MAX_FILE_BYTES,1048576)
    def test_missing_path_stays_none(self):
        self.assertEqual(recovery.current_hashes(self.root,[self.name,'new.py']),{self.name:None,'new.py':None})
    def test_missing_parent_file_does_not_become_none(self):
        self.path.parent.rmdir();self.path.parent.write_text('not a directory')
        with self.assertRaises(adapter.ModelAdapterError):recovery.current_hashes(self.root,[self.name])
    def test_symlink_and_dangling_symlink_refused(self):
        target=self.root/'target.json';target.write_bytes(b'{}')
        self.path.symlink_to(target)
        with self.assertRaises(adapter.ModelAdapterError):recovery.current_hashes(self.root,[self.name])
        self.path.unlink();self.path.symlink_to(self.root/'missing')
        with self.assertRaises(adapter.ModelAdapterError):recovery.current_hashes(self.root,[self.name])
    def test_parent_symlink_refused(self):
        self.path.parent.rmdir();outside=self.root/'other';outside.mkdir();(outside/self.path.name).write_bytes(b'{}');self.path.parent.symlink_to(outside,target_is_directory=True)
        with self.assertRaises(adapter.ModelAdapterError):recovery.current_hashes(self.root,[self.name])
    def test_nonregular_directory_and_fifo_refused_without_block(self):
        self.path.mkdir()
        with self.assertRaises(adapter.ModelAdapterError):recovery.current_hashes(self.root,[self.name])
        self.path.rmdir();os.mkfifo(self.path)
        with self.assertRaises(adapter.ModelAdapterError):recovery.current_hashes(self.root,[self.name])
    def test_changed_metadata_bytes_fail_fence_without_mutating_journal(self):
        self.large();expected=recovery.current_hashes(self.root,[self.name]);journal=self.root/'admission.json';journal.write_bytes(b'{"spent":2,"history":["retained"]}\n');before=journal.read_bytes()
        self.path.write_bytes(self.path.read_bytes().replace(b'padding',b'changed',1))
        with self.assertRaisesRegex(recovery.RecoveryError,'changed since admission'):recovery.unchanged(self.root,expected)
        self.assertEqual(journal.read_bytes(),before)
    def test_new_present_metadata_does_not_match_missing_admission(self):
        expected={self.name:None};self.path.write_bytes(b'{}')
        with self.assertRaises(recovery.RecoveryError):recovery.unchanged(self.root,expected)

if __name__=='__main__':unittest.main()
