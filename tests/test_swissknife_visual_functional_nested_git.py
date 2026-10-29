"""Real isolated Git links/index/conflicts; never modifies a live checkout."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,tempfile,unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import swissknife_visual_functional_supervisor as supervisor
import swissknife_visual_functional_worker as worker
TARGET='external/ipfs_kit/ipfs_kit_py/assurance/pinned_pubsub.py'
class NestedGit(unittest.TestCase):
 def git(self,repo,*argv,check=True):
  return subprocess.run(['git','-c','user.name=SVF fixture','-c','user.email=fixture@example.invalid',*argv],cwd=repo,check=check,capture_output=True,text=True,env={**os.environ,'GIT_CONFIG_NOSYSTEM':'1','GIT_CONFIG_GLOBAL':'/dev/null','GIT_TERMINAL_PROMPT':'0'})
 def commit(self,repo,*names):self.git(repo,'add','--',*names);self.git(repo,'commit','-qm','isolated fixture')
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(prefix='svf-nested-git-');self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name);self.swiss=self.root/'swissknife';self.kit=self.root/'external/ipfs_kit';self.target=self.root/TARGET
  for repo in [self.root,self.swiss,self.kit]:
   repo.mkdir(parents=True,exist_ok=True);self.git(repo,'init','-q');(repo/'base.txt').write_text('baseline\n');self.commit(repo,'base.txt')
  self.target.parent.mkdir(parents=True);(self.target.parent/'pinned_ipfs.py').write_text('baseline SDK\n');self.commit(self.kit,'ipfs_kit_py/assurance/pinned_ipfs.py');self.commit(self.root,'swissknife','external/ipfs_kit')
  board=self.root/supervisor.BOARD;board.parent.mkdir(parents=True);board.write_text('## SVF-001 SDK\n- Status: ready\n- Depends on:\n- Goal id: SVF-G001\n- Deterministic command: python3 '+supervisor.WORKER+' --task-id SVF-001\n- Validation: python3 '+supervisor.WORKER+' --validate --task-id SVF-001\n- Predicted files: '+TARGET+'\n- Acceptance: Must use real SDK bytes.\n')
  (self.root/supervisor.OBJECTIVES).write_text('## SVF-G000 Root\n- Status: active\n- Parent:\n\n## SVF-G001 SDK\n- Status: active\n- Parent: SVF-G000\n')
  self.profile={'runtimeRoot':supervisor.RUNTIME}
  for p in [patch.object(worker,'ROOT',self.root),patch.object(supervisor,'active_registered_writers',return_value=[])]:p.start();self.addCleanup(p.stop)
 def preflight(self):return supervisor.preflight(self.root,{})
 def own(self):
  p=self.root/supervisor.RUNTIME/'owned-source-hashes.json';p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps({TARGET:hashlib.sha256(self.target.read_bytes()).hexdigest()}))
 def both_refuse(self):
  with self.assertRaises(supervisor.PreflightError):self.preflight()
  with self.assertRaises((supervisor.PreflightError,RuntimeError)):worker.check_owned_sources(self.profile,[TARGET])
 def checkpoint_target(self):
  self.target.write_text('tracked SDK\n');self.commit(self.kit,'ipfs_kit_py/assurance/pinned_pubsub.py');self.commit(self.root,'external/ipfs_kit')
 def test_absent_new_target_with_dirty_sdk_siblings_allows_both(self):
  (self.target.parent/'pinned_ipfs.py').write_text('reviewed sibling change\n');(self.kit/'untracked-test.py').write_text('foreign sibling\n')
  dirty=set(supervisor.dirty_paths(self.root));self.assertNotIn('external/ipfs_kit',dirty);self.assertIn('external/ipfs_kit/ipfs_kit_py/assurance/pinned_ipfs.py',dirty);self.assertEqual(self.preflight()['ready_task_ids'],['SVF-001']);worker.check_owned_sources(self.profile,[TARGET]);self.assertFalse(self.target.exists())
 def test_untracked_foreign_exact_sdk_target_refuses(self):self.target.write_text('foreign\n');self.both_refuse()
 def test_staged_foreign_exact_sdk_target_refuses(self):self.target.write_text('foreign staged\n');self.git(self.kit,'add','--','ipfs_kit_py/assurance/pinned_pubsub.py');self.both_refuse()
 def test_unstaged_tracked_exact_sdk_target_refuses(self):self.checkpoint_target();self.target.write_text('foreign changed\n');self.both_refuse()
 def test_exact_owned_dirty_checkpoint_allows_both_until_changed(self):
  self.target.write_text('scoped checkpoint\n');self.own();self.assertEqual(self.preflight()['ready_task_ids'],['SVF-001']);worker.check_owned_sources(self.profile,[TARGET]);self.target.write_text('concurrent foreign change\n');self.both_refuse()
 def test_child_head_drift_blocks_even_owned_descendant(self):
  self.target.write_text('scoped checkpoint\n');self.own();(self.kit/'base.txt').write_text('different commit\n');self.commit(self.kit,'base.txt');self.assertIn('external/ipfs_kit',supervisor.dirty_paths(self.root));self.both_refuse()
 def test_parent_index_gitlink_drift_retained_when_worktree_head_returns_to_pin(self):
  pin=self.git(self.kit,'rev-parse','HEAD').stdout.strip();(self.kit/'base.txt').write_text('different commit\n');self.commit(self.kit,'base.txt');self.git(self.root,'add','--','external/ipfs_kit');self.git(self.kit,'checkout','-q',pin);self.target.write_text('owned child\n');self.own();self.assertIn('external/ipfs_kit',supervisor.dirty_paths(self.root));self.both_refuse()
 def test_sdk_staged_worktree_cancellation_is_not_clean_or_owned(self):
  self.checkpoint_target();self.target.write_text('staged different SDK\n');self.git(self.kit,'add','--','ipfs_kit_py/assurance/pinned_pubsub.py');self.target.write_text('tracked SDK\n');self.assertEqual(self.git(self.kit,'diff','--name-only','HEAD').stdout.strip(),'');self.assertIn(TARGET,supervisor.dirty_paths(self.root));self.both_refuse()
 def test_root_and_swiss_staged_worktree_cancellation_remains_foreign(self):
  for repo,name in [(self.root,'base.txt'),(self.swiss,'swissknife/base.txt')]:
   path=self.root/name;path.write_text('staged foreign version\n');self.git(repo,'add','--','base.txt');path.write_text('baseline\n');self.assertEqual(self.git(repo,'diff','--name-only','HEAD','--','base.txt').stdout.strip(),'');self.assertIn(name,supervisor.dirty_paths(self.root))
   board=self.root/supervisor.BOARD;original=board.read_text();board.write_text(original.replace(TARGET,name))
   with self.subTest(repo=repo):
    with self.assertRaises(supervisor.PreflightError):self.preflight()
    with self.assertRaises(RuntimeError):worker.check_owned_sources(self.profile,[name])
   board.write_text(original)
 def test_sdk_rename_preserves_both_original_and_destination(self):
  self.checkpoint_target();self.git(self.kit,'mv','ipfs_kit_py/assurance/pinned_pubsub.py','ipfs_kit_py/assurance/renamed.py');dirty=set(supervisor.dirty_paths(self.root));self.assertIn(TARGET,dirty);self.assertIn('external/ipfs_kit/ipfs_kit_py/assurance/renamed.py',dirty);self.both_refuse()
 def test_sdk_conflict_or_interrupted_merge_refuses(self):
  original=self.git(self.kit,'rev-parse','HEAD').stdout.strip();self.git(self.kit,'checkout','-qb','left');(self.kit/'base.txt').write_text('left\n');self.commit(self.kit,'base.txt');self.git(self.kit,'checkout','-qb','right',original);(self.kit/'base.txt').write_text('right\n');self.commit(self.kit,'base.txt');result=self.git(self.kit,'merge','left',check=False);self.assertNotEqual(result.returncode,0);self.both_refuse()
 def test_sdk_rebase_marker_refuses(self):
  marker=self.git(self.kit,'rev-parse','--git-path','rebase-merge').stdout.strip();p=Path(marker);p=p if p.is_absolute()else self.kit/p;p.mkdir();self.both_refuse()
 def test_missing_nested_repository_not_treated_as_root_repo(self):
  import shutil
  shutil.rmtree(self.kit/'.git');self.both_refuse()
 def test_swiss_head_drift_preserved_for_owned_sw_child(self):
  target='swissknife/new.js';p=self.root/target;p.write_text('owned checkpoint\n');(self.swiss/'base.txt').write_text('different Swiss commit\n');self.commit(self.swiss,'base.txt');ledger=self.root/supervisor.RUNTIME/'owned-source-hashes.json';ledger.parent.mkdir(parents=True);ledger.write_text(json.dumps({target:hashlib.sha256(p.read_bytes()).hexdigest()}));self.assertIn('swissknife',supervisor.dirty_paths(self.root))
  with self.assertRaises(RuntimeError):worker.check_owned_sources(self.profile,[target])
 def test_unrelated_parent_gitlink_dirt_is_preserved_not_blanket_ignored(self):
  other=self.root/'foreign';other.mkdir();self.git(other,'init','-q');(other/'file').write_text('old\n');self.commit(other,'file');self.commit(self.root,'foreign');(other/'file').write_text('foreign\n');self.assertIn('foreign',supervisor.dirty_paths(self.root));self.assertEqual(self.preflight()['ready_task_ids'],['SVF-001'])
if __name__=='__main__':unittest.main()
