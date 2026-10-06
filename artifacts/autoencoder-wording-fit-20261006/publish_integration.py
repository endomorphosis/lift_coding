"""Publish a reviewed exact whitelist through a private Git index.

Fetch/commit/push are explicit execution only. Other working changes and the
ordinary indexes and HEADs are preserved; no source or model code is executed.
"""
import argparse,hashlib,json,os,subprocess
from pathlib import Path, PurePosixPath
R=Path(__file__).resolve().parent
W=R.parents[1]
P=W/'external/ipfs_datasets'

def require(ok,message):
 if not ok:raise ValueError(message)
def git(repo,*args,data=None,env=None):
 return subprocess.check_output(['git','-c','core.hooksPath=/dev/null','-C',str(repo),*args],input=data,env=env,stderr=subprocess.PIPE)
def sha(data):return hashlib.sha256(data).hexdigest()
def unique_object(pairs):
 result={}
 for key,value in pairs:
  require(key not in result,'duplicate JSON key: '+key);result[key]=value
 return result
def read(path):return json.loads(Path(path).read_bytes(),object_pairs_hook=unique_object)
def relative_path(value):
 require(type(value) is str and value and str(PurePosixPath(value))==value
         and not PurePosixPath(value).is_absolute()
         and not any(x in ('..','.git') for x in PurePosixPath(value).parts)
         and value!='.','closed normalized repository-relative path required')
 return value
def save(path,data):
 with path.open('x') as f:json.dump(data,f,sort_keys=True,indent=2);f.write('\n')
def capture(repo):
 index=Path(git(repo,'rev-parse','--git-path','index').decode().strip())
 if not index.is_absolute():index=repo/index
 return dict(head=git(repo,'rev-parse','HEAD').decode().strip(),index_sha256=sha(index.read_bytes()))
def normal():return dict(workspace=capture(W),datasets=capture(P))
def entry(repo,parent,rel):
 record=git(repo,'--literal-pathspecs','ls-tree','-z',parent,'--',rel)
 if not record:return None
 header,name=record.rstrip(b'\0').split(b'\t',1)
 mode,kind,oid=header.decode().split()
 require(name.decode()==rel and kind=='blob' and mode in ('100644','100755'),'exact regular upstream file required')
 return dict(mode=mode,oid=oid,sha256=sha(git(repo,'cat-file','blob',oid)))
def verify_review(path):
 result=read(path);require(result.get('passed') is True and not result.get('findings'),'review failed: '+str(path))
 for name,wanted in result.get('artifacts',{}).items():
  actual=Path(name).read_bytes()
  if isinstance(wanted,str):require(sha(actual)==wanted,'reviewed artifact changed: '+name)
  else:
   require(sha(actual)==wanted['sha256'],'reviewed hash changed: '+name)
   if 'bytes' in wanted:require(len(actual)==wanted['bytes'],'reviewed size changed: '+name)
 return result

def main():
 parser=argparse.ArgumentParser();parser.add_argument('scope',choices=('datasets','workspace'))
 parser.add_argument('--attempt',required=True);args=parser.parse_args()
 require(args.attempt.isalnum() and len(args.attempt)<32,'short fresh attempt required')
 scope=read(R/'publication-scope.json');require(scope['passed'] and scope['reviewed'],'final sealed scope required')
 require('pipeline/publication-scope-independent-review.json' in scope['required_reviews'],
         'independent exact scope review required')
 for review in scope['required_reviews']:verify_review(R/relative_path(review))
 sealed=read(R/'pipeline/publication-scope-independent-review.json')
 require(sealed['artifacts'].get(str(R/'publication-scope.json'))==sha((R/'publication-scope.json').read_bytes()),
         'independent review does not seal the selected scope')
 repository=P if args.scope=='datasets' else W
 receipt=R/(args.scope+'-publication.json');require(not receipt.exists(),'already published')
 before=normal();git(repository,'fetch','--no-tags','origin','main')
 parent=git(repository,'rev-parse','origin/main').decode().strip()
 git(repository,'merge-base','--is-ancestor',scope[args.scope]['parent'],parent)
 index=R/(args.scope+'-'+args.attempt+'.index');require(not index.exists(),'fresh alternate index required')
 env=dict(os.environ,GIT_INDEX_FILE=str(index));git(repository,'read-tree',parent,env=env)
 expected=set(scope[args.scope]['files'])
 for rel,item in scope[args.scope]['files'].items():
  relative_path(rel);require(item.get('mode','100644') in ('100644','100755'),'regular staged mode required')
  selected=repository/rel;require(selected.is_file() and not selected.is_symlink(),'regular candidate required')
  require(selected.resolve().is_relative_to(repository.resolve()),'candidate leaves repository')
  for parent_directory in selected.parents:
   if parent_directory==repository:break
   require(not parent_directory.is_symlink(),'symbolic candidate parent refused')
  content=selected.read_bytes();require(sha(content)==item['sha256'] and len(content)==item['bytes'],'candidate changed: '+rel)
  old=entry(repository,parent,rel);oldsha=None if old is None else old['sha256']
  require(oldsha in (item['parent_sha256'],item['sha256']),'upstream preimage changed; reconcile: '+rel)
  oid=git(repository,'hash-object','-w','--stdin',data=content).decode().strip()
  mode=old['mode'] if old else item.get('mode','100644')
  git(repository,'update-index','--add','--cacheinfo',mode+','+oid+','+rel,env=env)
  require(sha(git(repository,'show',':'+rel,env=env))==item['sha256'],'staged bytes differ')
 if args.scope=='workspace':
  package=read(R/'datasets-publication.json')['commit']
  require(git(P,'ls-remote','origin','refs/heads/main').decode().split()[0]==package,'datasets remote moved; review new pointer')
  previous=git(W,'ls-tree',parent,'--','external/ipfs_datasets').decode().split()
  require(previous[0]=='160000','expected datasets gitlink')
  git(P,'merge-base','--is-ancestor',previous[2],package)
  git(W,'update-index','--add','--cacheinfo','160000,'+package+',external/ipfs_datasets',env=env)
  expected.add('external/ipfs_datasets')
 changed=set(git(repository,'diff','--cached','--name-only',parent,env=env).decode().splitlines())
 require(changed and changed<=expected,'unexpected or empty staged change')
 git(repository,'diff','--cached','--check',parent,env=env)
 require(normal()==before,'normal Git state changed')
 tree=git(repository,'write-tree',env=env).decode().strip()
 message=('Train paired decoder heads on broader normative TRAIN wording\n\nPreserve original updates and exact zero replay; evaluate sealed development wording with durable source traces and unchanged qualification boundaries.\n' if args.scope=='datasets' else 'Record verified source preparation and paired normative decoder fits\n\nRetain source provenance, full vocabulary traces, failure evidence and prospective development results without promoting checkpoints.\n')
 commit=git(repository,'commit-tree',tree,'-p',parent,data=message.encode()).decode().strip()
 require(git(repository,'ls-remote','origin','refs/heads/main').decode().split()[0]==parent,'remote main changed; retry reviewed preimages')
 save(R/(args.scope+'-'+args.attempt+'-prepared.json'),dict(parent=parent,commit=commit,tree=tree,changed=sorted(changed),normal_before=before))
 git(repository,'-c','pack.threads=1','-c','pack.windowMemory=64m','push','origin',commit+':refs/heads/main')
 require(git(repository,'ls-remote','origin','refs/heads/main').decode().split()[0]==commit,'remote verification failed')
 after=normal();require(after==before,'normal Git state changed during publication')
 save(receipt,dict(parent=parent,commit=commit,tree=tree,changed=sorted(changed),normal_before=before,normal_after=after,normal_state_preserved=True,force_push=False))
 print(json.dumps(dict(scope=args.scope,commit=commit,changed_files=len(changed))))
if __name__=='__main__':main()
