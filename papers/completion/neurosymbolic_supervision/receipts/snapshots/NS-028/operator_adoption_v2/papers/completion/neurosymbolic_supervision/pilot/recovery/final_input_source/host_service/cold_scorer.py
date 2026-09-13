"""Fixed isolated scorer. Private tests/logs are never echoed to the caller."""
from pathlib import Path,PurePosixPath
import hashlib,json,os,shutil,stat,subprocess,sys,time

DEADLINE=time.monotonic()+115

def canon(x):return json.dumps(x,sort_keys=True,separators=(',',':')).encode()
def digest(x):return hashlib.sha256(canon(x)).hexdigest()
def require(ok):
 if not ok:raise ValueError('bound scorer input mismatch')
def file_sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def rel(v):
 require(type(v)is str and v and not v.startswith('/') and '\\'not in v and '\0'not in v);p=PurePosixPath(v);require(str(p)==v and not any(x in('.','..','.git')for x in p.parts));return v

def observe(name,nodes):
 path=Path('/results')/(name+'.observation.json');require(not path.exists())
 code="import sys;sys.path[:0]=['/work/src','/work','/capture','/railroad.whl'];import pytest;raise SystemExit(pytest.main(sys.argv[1:]))"
 argv=[sys.executable,'-I','-B','-c',code,'-q','-p','no:cacheprovider','-p','baseline_capture',*nodes]
 env={'HOME':'/tmp','PATH':'/usr/local/bin:/usr/bin:/bin','PYTHONDONTWRITEBYTECODE':'1','PYTEST_DISABLE_PLUGIN_AUTOLOAD':'1','BASELINE_OBSERVATION':str(path)}
 with (Path('/results')/(name+'.stdout.private.log')).open('xb')as out,(Path('/results')/(name+'.stderr.private.log')).open('xb')as err:
  try:r=subprocess.run(argv,cwd='/work',env=env,stdout=out,stderr=err,timeout=max(0.001,min(115,DEADLINE-time.monotonic())));rc=r.returncode
  except subprocess.TimeoutExpired:rc=124
 if not path.exists():return {'rc':rc,'collected':[],'passed':0,'skipped':0,'valid':False,'observation_sha256':None}
 require(path.is_file()and not path.is_symlink()and path.stat().st_size<=8*1024*1024);data=json.loads(path.read_text());collected=data.get('collected',[]);reports=data.get('reports',[])
 require(type(collected)is list and all(type(x)is str for x in collected)and type(reports)is list)
 passed=sum(r.get('when')=='call'and r.get('outcome')=='passed'for r in reports);skipped=sum(r.get('outcome')=='skipped'for r in reports)
 valid=rc==0 and data.get('exitstatus')==0 and not data.get('collection_errors')and bool(collected)and passed>0 and not any(r.get('outcome')=='failed'for r in reports)
 return {'rc':rc,'collected':collected,'passed':passed,'skipped':skipped,'valid':valid,'observation_sha256':file_sha(path)}

def main():
 recipe=json.loads(Path('/runner/recipe.json').read_text());require(recipe['schema']=='ns-historical-cold-recipe/v1')
 work=Path('/work');require(not any(work.iterdir()))
 for path,spec in recipe['source_files'].items():
  p=Path('/preimage')/rel(path);out=work/path;out.parent.mkdir(parents=True,exist_ok=True)
  if spec.get('kind')=='symlink':
   require(p.is_symlink() and os.readlink(p)==spec['target']);out.symlink_to(spec['target'])
  else:
   require(p.is_file()and not p.is_symlink()and file_sha(p)==spec['sha256']);shutil.copyfile(p,out);out.chmod(spec['mode'])
 for path,spec in recipe['candidate']['files'].items():
  p=Path('/candidate')/rel(path)
  if spec.get('kind')=='symlink':require(p.is_symlink()and os.readlink(p)==spec['target']);continue
  require(p.is_file()and not p.is_symlink()and file_sha(p)==spec['sha256'])
  if path in recipe['allowed_edit_paths']:shutil.copyfile(p,work/path);(work/path).chmod(spec['mode'])
 def unchanged_candidate():
  return all((os.readlink(work/path)==spec['target']) if spec.get('kind')=='symlink' else (file_sha(work/path)==spec['sha256']) for path,spec in recipe['candidate']['files'].items())
 require(unchanged_candidate())
 visible=observe('visible',recipe['visible_nodes']);require(unchanged_candidate())
 # Only now, after proposal sealing and ordinary unchanged tests, load oracle.
 raw=Path('/custody')/recipe['oracle_metadata_sha256'];require(file_sha(raw)==recipe['oracle_metadata_sha256']);oracle=json.loads(raw.read_text())
 require(oracle['task_id']==recipe['unit_id']and oracle['proposal_sandbox_may_read']is False)
 require(digest(oracle['fail_to_pass'])==recipe['expected_hidden_nodes_sha256']and len(oracle['fail_to_pass'])==recipe['expected_hidden_count'])
 hidden_paths=set()
 for spec in oracle['hidden_files']:
  path=rel(spec['path']);hidden_paths.add(path);key=recipe['custody_files'][path];payload=Path('/custody')/key
  require(key==spec['sha256']and file_sha(payload)==key and payload.stat().st_size==spec['byte_length'])
  dest=work/path;dest.parent.mkdir(parents=True,exist_ok=True);require(not dest.is_symlink());shutil.copyfile(payload,dest);dest.chmod(0o444)
 require(len(hidden_paths)>0)
 for node in oracle['fail_to_pass']:require(rel(node.split('::',1)[0])in hidden_paths)
 hidden=observe('hidden',oracle['fail_to_pass'])
 # Public test source may intentionally be replaced by its hidden later version;
 # proposal implementation files must still be the exact sealed candidate.
 require(all(file_sha(work/path)==recipe['candidate']['files'][path]['sha256']for path in recipe['allowed_edit_paths']))
 visible_ok=visible['valid']and len(visible['collected'])==recipe['expected_visible_collected_count']
 hidden_ok=hidden['valid']and set(hidden['collected'])==set(oracle['fail_to_pass'])and hidden['passed']==recipe['expected_hidden_count']
 success=visible_ok and hidden_ok
 result={'schema':'ns-historical-cold-result/v1','success':success,'classification':'passed'if success else'visible_regression_failed'if not visible_ok else'hidden_acceptance_failed','visible_collected':len(visible['collected']),'visible_passed':visible['passed'],'visible_skipped':visible['skipped'],'hidden_collected':len(hidden['collected']),'hidden_passed':hidden['passed'],'hidden_skipped':hidden['skipped'],'baseline_exit':visible['rc'],'hidden_exit':hidden['rc'],'observation_hashes':{k:v['observation_sha256']for k,v in [('visible',visible),('hidden',hidden)]}}
 Path('/results/result.json').write_bytes(canon(result));return 0
if __name__=='__main__':
 try:raise SystemExit(main())
 except Exception as exc:
  # Do not echo exception messages, test source, assertion payloads or node IDs.
  Path('/results/result.json').write_bytes(canon({'schema':'ns-historical-cold-result/v1','success':False,'classification':'scorer_input_or_execution_error'}));raise SystemExit(2)
