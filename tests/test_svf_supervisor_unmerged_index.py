"""Actual isolated Git index conflicts; no live checkout, network or service use."""
from pathlib import Path
import os,subprocess,sys,tempfile,unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import swissknife_visual_functional_supervisor as supervisor

class UnmergedIndexTests(unittest.TestCase):
 def git(self,repo,*args,input=None):
  return subprocess.run(['git','-c','core.hooksPath=/dev/null','-c','core.fsmonitor=false','-c','user.name=RAM fixture','-c','user.email=fixture@example.invalid',*args],cwd=repo,input=input,text=True,capture_output=True,check=True,timeout=10,env={**os.environ,'GIT_CONFIG_NOSYSTEM':'1','GIT_CONFIG_GLOBAL':'/dev/null','GIT_TERMINAL_PROMPT':'0','GIT_OPTIONAL_LOCKS':'0'}).stdout
 def setUp(self):
  temporary=tempfile.TemporaryDirectory(prefix='svf-unmerged-index-',dir=os.environ.get('TMPDIR'));self.addCleanup(temporary.cleanup);self.root=Path(temporary.name)
  for repo in [self.root,self.root/'swissknife',self.root/'external/ipfs_kit']:
   repo.mkdir(parents=True,exist_ok=True);self.git(repo,'init','-q');(repo/'baseline.txt').write_text('baseline\n');self.git(repo,'add','--','baseline.txt');self.git(repo,'commit','-qm','RAM baseline')
  self.git(self.root,'add','--','swissknife','external/ipfs_kit');self.git(self.root,'commit','-qm','RAM registered gitlinks')
 def query(self,repo):return supervisor._git(repo,'ls-files','--unmerged','-z')
 def conflicting_index(self,repo,name,mode,oids):
  records='0 '+'0'*40+'\t'+name+'\n'+''.join(f'{mode} {oid} {stage}\t{name}\n'for stage,oid in enumerate(oids,1))
  self.git(repo,'update-index','--index-info',input=records)
 def test_clean_index_and_all_registered_nested_checks_still_run(self):
  original=supervisor._git;queries=[]
  def traced(repo,*args):
   if args==('ls-files','--unmerged','-z'):queries.append(repo)
   return original(repo,*args)
  with patch.object(supervisor,'_git',side_effect=traced):self.assertEqual(supervisor.dirty_paths(self.root),[])
  self.assertEqual(queries,[self.root,self.root/'swissknife',self.root/'external/ipfs_kit'])
 def test_real_file_merge_stages_are_refused_before_worktree_diffs(self):
  blobs=[self.git(self.root,'hash-object','-w','--stdin',input=value).strip()for value in ['base\n','left\n','right\n']]
  self.conflicting_index(self.root,'baseline.txt','100644',blobs);raw=self.query(self.root)
  self.assertEqual(raw.count('\0'),3);self.assertIn('100644 '+blobs[2]+' 3\tbaseline.txt\0',raw)
  with self.assertRaisesRegex(supervisor.PreflightError,'unresolved index'):supervisor.dirty_paths(self.root)
 def test_real_gitlink_merge_stages_are_refused(self):
  repo=self.root/'swissknife';oids=[self.git(repo,'rev-parse','HEAD').strip()]
  for value in ['left\n','right\n']:
   (repo/'baseline.txt').write_text(value);self.git(repo,'add','--','baseline.txt');self.git(repo,'commit','-qm','RAM gitlink version');oids.append(self.git(repo,'rev-parse','HEAD').strip())
  self.conflicting_index(self.root,'swissknife','160000',oids);raw=self.query(self.root)
  self.assertEqual(raw.count('\0'),3);self.assertIn('160000 '+oids[2]+' 3\tswissknife\0',raw)
  with self.assertRaisesRegex(supervisor.PreflightError,'unresolved index'):supervisor.dirty_paths(self.root)
 def test_conflict_query_uses_index_even_when_worktree_is_absent(self):
  # Index inspection needs no working-tree traversal or nested repository scan.
  missing=self.root/'absent-worktree';self.assertFalse(missing.exists())
  original=supervisor._git;observed=[]
  class StopAfterIndex(Exception):pass
  def inspect(repo,*args):
   if args==('ls-files','--unmerged','-z'):
    with patch.dict(os.environ,{'GIT_WORK_TREE':str(missing)}):observed.append(original(repo,*args))
    raise StopAfterIndex
   return original(repo,*args)
  with patch.object(supervisor,'_git',side_effect=inspect),self.assertRaises(StopAfterIndex):supervisor.dirty_paths(self.root)
  self.assertEqual(observed,['']);self.assertFalse(missing.exists())
 def test_nested_staged_unstaged_untracked_and_head_drift_remain_visible(self):
  swiss=self.root/'swissknife';kit=self.root/'external/ipfs_kit'
  (swiss/'baseline.txt').write_text('staged\n');self.git(swiss,'add','--','baseline.txt');(swiss/'baseline.txt').write_text('baseline\n');(kit/'foreign.txt').write_text('untracked\n')
  dirty=set(supervisor.dirty_paths(self.root));self.assertIn('swissknife/baseline.txt',dirty);self.assertIn('external/ipfs_kit/foreign.txt',dirty)
  (swiss/'baseline.txt').write_text('new commit\n');self.git(swiss,'add','--','baseline.txt');self.git(swiss,'commit','-qm','RAM nested head drift');self.assertIn('swissknife',supervisor.dirty_paths(self.root))
if __name__=='__main__':unittest.main()
