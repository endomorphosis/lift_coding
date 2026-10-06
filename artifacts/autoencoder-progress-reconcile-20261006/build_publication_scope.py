"""Seal bounded reconciliation evidence and exact private-index publish scope.

No fetch, staging, model execution, normal Git mutation or push is performed.
"""
from pathlib import Path
import gzip, hashlib, io, json, os, subprocess, tarfile
R=Path(__file__).resolve().parent;W=R.parents[1];P=W/'external/ipfs_datasets'
def digest(b):return hashlib.sha256(b).hexdigest()
def save(path,d):
 with path.open('x') as f:json.dump(d,f,sort_keys=True,indent=2);f.write('\n')
def git(repo,*args):return subprocess.check_output(['git','-C',str(repo),*args],stderr=subprocess.PIPE)
def record(path):
 assert path.is_file() and not path.is_symlink()
 b=path.read_bytes();return {'sha256':digest(b),'bytes':len(b)}
# Evidence-only members: exclude source mirrors, synthetic fixtures, status dumps,
# private Git indexes, future receipts and the archive itself.
exclusions={'main-coordination-closure','independent-pure-tmp','pure-tmp','__pycache__','.pytest_cache','pipeline'}
members=[]
for path in sorted(R.rglob('*')):
 rel=path.relative_to(R)
 if not path.is_file() or path.is_symlink() or any(x in exclusions for x in rel.parts):continue
 if path.name in {'datasets-ref-worktree-inventory.json','workspace-ref-worktree-inventory.json'}:continue
 if len(rel.parts)==1 and path.name not in {'README.md','initial-state.json','build_publication_scope.py','publish_integration.py','publisher_review_tests.py'}:continue
 if path.suffix not in {'.py','.json','.md','.diff','.xml','.log','.txt'}:continue
 b=path.read_bytes();assert len(b)<4_000_000
 members.append((str(rel),b))
assert members and sum(len(b) for _,b in members)<15_000_000
archive=R/'review-evidence.tar.gz';assert not archive.exists()
with archive.open('xb') as raw:
 with gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0) as compressed:
  with tarfile.open(fileobj=compressed,mode='w') as tf:
   for name,b in members:
    info=tarfile.TarInfo(name);info.size=len(b);info.mode=0o644;info.mtime=0
    tf.addfile(info,io.BytesIO(b))
manifest={'schema':'bounded-reconciliation-review-archive/v1','archive':record(archive),'member_count':len(members),'uncompressed_bytes':sum(len(b) for _,b in members),'members':{name:{'sha256':digest(b),'bytes':len(b)} for name,b in members},'model_weight_values_included':False,'source_mirrors_included':False,'giant_status_dumps_included':False}
save(R/'review-evidence-manifest.json',manifest)
pfiles=['ipfs_datasets_py/logic/deontic/coordination_decoder.py','ipfs_datasets_py/logic/autoformal/legal_coordination_evaluation.py','tests/unit/logic/test_deontic_grouped_decoder.py','tests/unit/logic/test_deontic_grouped_decoder_boundaries.py','docs/autoencoders/progress_reconciliation_20261006.md']
wfiles=['scripts/review_autoencoder_progress.py','tests/test_review_autoencoder_progress.py','implementation_plan/docs/59-autoencoder-progress-reconciliation-2026-10-06.md']
for rel in ['README.md','initial-state.json','build_publication_scope.py','publish_integration.py','publisher_review_tests.py','review-evidence.tar.gz','review-evidence-manifest.json','branches/branch-worktree-review.json','branches/branch-worktree-review.md','branches/main-coordination-interface-review.json','evidence/evidence-review.json','evidence/evidence-review.md','evidence/validation-receipt.json','runtime/runtime-compatibility.json','runtime/runtime-compatibility.md','runtime/additive-closure-review.md','recovery/effective-workingcopy-after.json','recovery/canonical-logic-tree-check.json','pipeline/publisher-synthetic-validation.json','pipeline/reconciliation-documentation-review.json','pipeline/evidence-documentation-review.json','pipeline/publication-producer-review.json']:
 wfiles.append(str(R.relative_to(W)/rel))
reviews=['pipeline/publisher-synthetic-validation.json','pipeline/reconciliation-documentation-review.json','pipeline/evidence-documentation-review.json','pipeline/publication-producer-review.json','pipeline/publication-scope-independent-review.json']
scope={'schema':'autoencoder-progress-exact-publication-scope/v1','passed':True,'reviewed':True,'required_reviews':reviews,'semantic_qualification_granted':False,'checkpoint_promotion':False,'no_foreign_dirty_files':True}
for name,repo,files in [('datasets',P,pfiles),('workspace',W,wfiles)]:
 parent=git(repo,'rev-parse','origin/main').decode().strip();items={}
 for rel in files:
  item=record(repo/rel);item['mode']='100755' if os.stat(repo/rel).st_mode&0o111 else '100644'
  old=git(repo,'--literal-pathspecs','ls-tree','-z',parent,'--',rel)
  item['parent_sha256']=None if not old else digest(git(repo,'show',parent+':'+rel))
  items[rel]=item
 scope[name]={'parent':parent,'files':items}
save(R/'publication-scope.json',scope)
print(json.dumps({'archive_members':len(members),'archive_bytes':archive.stat().st_size,'datasets_paths':len(pfiles),'workspace_paths':len(wfiles)}))
