"""Seal actual retention and canonical recovery evidence, without Git mutation."""
from pathlib import Path
import gzip,hashlib,io,json,os,subprocess,tarfile
R=Path(__file__).resolve().parent;W=R.parents[1];P=W/'external/ipfs_datasets';A=W/'artifacts/autoencoder-progress-reconcile-20261006';RUN=P/'workspace/test-logs/decoder-normative-wording-retention-20261006'
def sha(b):return hashlib.sha256(b).hexdigest()
def record(path):
 assert path.is_file() and not path.is_symlink();b=path.read_bytes();return {'sha256':sha(b),'bytes':len(b)}
def save(path,d):
 with path.open('x') as f:json.dump(d,f,sort_keys=True,indent=2);f.write('\n')
def git(repo,*args):return subprocess.check_output(['git','-C',str(repo),*args],stderr=subprocess.PIPE)
members={}
def add(path,name):
 assert path.is_file() and not path.is_symlink();assert name not in members
 assert not any(x in {'..','.git','__pycache__','.pytest_cache'} for x in Path(name).parts)
 assert path.suffix in {'.py','.md','.json','.xml','.jsonl','.log','.diff'}
 assert not any(x in path.name for x in ['state.json','.pt','.safetensors','.npy','.npz'])
 b=path.read_bytes();assert len(b)<4_000_000;members[name]=(path,b)
for path in sorted((RUN/'retention-r1').rglob('*')):
 if path.is_file():add(path,'actual-run/'+str(path.relative_to(RUN/'retention-r1')))
for name in ['retention-r1-guardian-exit.json','retention-r1-guardian.log','retention-r1-lease-observations.jsonl','retention-r1-scheduler-adoption.json','evaluation-manifest.json','evaluation-plan.json','run_guardian.py','run_reserved.py','owned_lease_watchdog.py','adopt_shared_scheduler.py','lazy_scheduler_adoption.py','experiment-source/scripts/ops/autoencoder/evaluate_normative_wording_retention.py']:
 add(RUN/name,'owned-guardian/'+name)
for name in ['retention/actual-result-independent-review.json','retention/audit_actual_retention.py','retention/resource-execution-independent-review.json','retention/review_resource_execution.py','retention/execution-readiness.json','retention/combine_execution_readiness.py','retention/combiner-review.json','retention/guardian-readiness.json','retention/independent-runner-readiness.json','retention/guardian-input-hash-review.json','datasets-publication.json','workspace-publication.json','branches/latest-pr1271-review.json','branches/latest-pr1271-review.md']:
 path=A/name
 if path.exists():add(path,'prior-integration/'+name)
for path in sorted((A/'branches/pr1271-canonical-proposal').rglob('*')):
 if path.is_file():add(path,'prior-integration/branches/pr1271-canonical-proposal/'+str(path.relative_to(A/'branches/pr1271-canonical-proposal')))
for path in sorted((R/'registry-recovery').rglob('*')):
 if path.is_file():add(path,'registry-recovery/'+str(path.relative_to(R/'registry-recovery')))
for name in ['README.md','build_publication_scope.py','publish_integration.py','publisher_review_tests.py']:add(R/name,name)
# Preserve the historical documentation bound by pre-execution readiness, rather
# than claiming that later follow-up documentation was its input.
previous=json.loads((A/'datasets-publication.json').read_bytes())['commit']
old=git(P,'show',previous+':docs/autoencoders/progress_reconciliation_20261006.md')
members['pre-execution-publication/progress_reconciliation_20261006.md']=(None,old)
assert sum(len(b) for _,b in members.values())<30_000_000
archive=R/'retention-evidence.tar.gz';assert not archive.exists()
with archive.open('xb') as raw:
 with gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0) as zipped:
  with tarfile.open(fileobj=zipped,mode='w') as tf:
   for name,(_,b) in sorted(members.items()):
    t=tarfile.TarInfo(name);t.size=len(b);t.mtime=0;t.mode=0o644;tf.addfile(t,io.BytesIO(b))
manifest={'schema':'bounded-retention-evidence-archive/v1','archive':record(archive),'member_count':len(members),'uncompressed_bytes':sum(len(b) for _,b in members.values()),'members':{name:{'sha256':sha(b),'bytes':len(b),'source_path':None if p is None else str(p)} for name,(p,b) in members.items()},'model_weights_included':False,'native_embedding_cache_values_included':False,'source_tree_mirrors_included':False,'historical_publication_commit':previous}
save(R/'retention-evidence-manifest.json',manifest)
folder=P/'docs/autoencoders/evidence/normative-wording-retention-20261006';folder.mkdir(exist_ok=False)
for source,name in [(RUN/'retention-r1/results/summary.json','summary.json'),(A/'retention/actual-result-independent-review.json','independent-result-review.json'),(A/'retention/resource-execution-independent-review.json','independent-resource-review.json'),(A/'branches/latest-pr1271-review.json','latest-pr1271-review.json'),(R/'registry-recovery/restoration-receipt.json','canonical-runtime-restoration.json')]:
 with (folder/name).open('xb') as f:f.write(source.read_bytes())
package_manifest={'schema':'normative-wording-retention-published-evidence/v1','summary_source_path':str(RUN/'retention-r1/results/summary.json'),'assets':{p.name:record(p) for p in sorted(folder.iterdir())},'workspace_archive_path':str(archive.relative_to(W)),'workspace_archive':record(archive),'complete_archive_manifest_path':str((R/'retention-evidence-manifest.json').relative_to(W)),'qualification_granted':False,'checkpoint_promoted':False,'training_executed':False}
save(folder/'manifest.json',package_manifest)
pfiles=['docs/autoencoders/normative_wording_retention.md','docs/autoencoders/progress_reconciliation_20261006.md']+[str(p.relative_to(P)) for p in sorted(folder.iterdir())]
wfiles=['README.md','publish_integration.py','publisher_review_tests.py','build_publication_scope.py','retention-evidence.tar.gz','retention-evidence-manifest.json','pipeline/publisher-synthetic-validation.json','pipeline/retention-documentation-numeric-review.json','pipeline/retention-documentation-resource-review.json','registry-recovery/restoration-receipt.json','registry-recovery/api-controls-r2.xml','registry-recovery/test-invocations.json']
wfiles=[str(R.relative_to(W)/x) for x in wfiles]
scope={'schema':'retention-exact-main-publication-scope/v1','passed':True,'reviewed':True,'required_reviews':['pipeline/publisher-synthetic-validation.json','pipeline/retention-documentation-numeric-review.json','pipeline/retention-documentation-resource-review.json','pipeline/publication-scope-independent-review.json'],'qualification_granted':False,'checkpoint_promoted':False,'source_behavior_delta_in_this_publication':False}
for name,repo,files in [('datasets',P,pfiles),('workspace',W,wfiles)]:
 parent=git(repo,'rev-parse','origin/main').decode().strip();items={}
 for rel in files:
  p=repo/rel;item=record(p);item['mode']='100755' if p.stat().st_mode&0o111 else '100644';old=git(repo,'--literal-pathspecs','ls-tree','-z',parent,'--',rel)
  item['parent_sha256']=None if not old else sha(git(repo,'show',parent+':'+rel));items[rel]=item
 scope[name]={'parent':parent,'files':items}
save(R/'publication-scope.json',scope)
print(json.dumps({'archive_bytes':archive.stat().st_size,'members':len(members),'package_paths':len(pfiles),'workspace_paths':len(wfiles)}))
