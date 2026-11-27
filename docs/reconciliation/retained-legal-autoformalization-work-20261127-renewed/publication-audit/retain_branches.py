from pathlib import Path
import hashlib,json,os,subprocess
from support import WORK as W,ENV
S=Path('/tmp/git-final-branch-retention-20261127-lmljw4GB')
selections=['accelerate_scanned_subset/ipfs_accelerate_py','ipfs_kit_py','recovery/ipfs_datasets_py','nonthin_recovery/swissknife','nonthin_recovery/lift_coding','recovery/ipfs_accelerate_py_detached']
restore=W/'fresh-branch-restores';restore.mkdir(mode=0o700,exist_ok=True)
out=W/'retained/branches';out.mkdir(parents=True,exist_ok=True)
def g(d,*args,raw=None,timeout=120):
 r=subprocess.run(['git','--git-dir',str(d),'-c','pack.threads=1','-c','index.threads=1',*args],input=raw,env=ENV,capture_output=True,timeout=timeout)
 if r.returncode:raise RuntimeError((str(d),args[0],r.returncode,r.stderr.decode(errors='replace')[-1200:]))
 return r.stdout
def pin(p):
 raw=p.read_bytes();return {'path':str(p),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
def copy(p,name,expected=None):
 before=pin(p)
 if expected:assert (before['bytes'],before['sha256'])==(expected['bytes'],expected['sha256'])
 dest=out/name;dest.parent.mkdir(parents=True,exist_ok=True)
 if not dest.exists():
  with dest.open('xb') as f:f.write(p.read_bytes())
 assert pin(dest)['sha256']==before['sha256']
 return {**before,'archive':'branches/'+name}
report=[]
for i,rel in enumerate(selections):
 folder=S/rel;r=json.loads((folder/'restore-receipt.json').read_bytes())
 assert r['status']=='RESTORE_VERIFIED'
 label=rel.replace('/','-');db=restore/(label+'.git')
 subprocess.run(['git','init','--bare','--quiet',str(db)],env=ENV,check=True)
 base=Path(r['published_base_object_db'])
 (db/'objects/info/alternates').write_text(str((base/'objects').resolve())+'\n')
 g(db,'cat-file','-e',r['published_base']+'^{commit}')
 g(db,'update-ref','refs/heads/published-base',r['published_base'])
 bundle=Path(r['bundle']['path']);assert pin(bundle)==r['bundle']
 verify=g(db,'bundle','verify',str(bundle))
 listed=g(db,'bundle','list-heads',str(bundle)).decode().splitlines()
 named={line.split()[1]:line.split()[0] for line in listed}
 assert set(named.values())==set(r['tips']) and len(named)==r['tip_count']
 g(db,'fetch','--no-write-fetch-head',str(bundle),'+refs/heads/retained/*:refs/heads/retained/*',timeout=240)
 actual=g(db,'for-each-ref','--format=%(objectname)','refs/heads/retained').decode().splitlines()
 assert set(actual)==set(r['tips']) and len(actual)==r['tip_count']
 # No promisor network. Every reference must traverse its complete commit/tree closure.
 check=g(db,'rev-list','--objects','--missing=print',*r['tips'])
 missing=[line.decode() for line in check.splitlines() if line.startswith(b'?')]
 base_walk=g(db,'rev-list','--objects','--missing=print',r['published_base'])
 base_missing={line.decode() for line in base_walk.splitlines() if line.startswith(b'?')}
 assert set(missing)<=base_missing,(label,'new_missing_objects',sorted(set(missing)-base_missing)[:5])
 row={'family':r['family'],'tip_count':r['tip_count'],'tips':r['tips'],'published_base':r['published_base'],'base_store':str(base),'bundle':copy(bundle,label+'/'+bundle.name,r['bundle']),'source_receipt':copy(folder/'restore-receipt.json',label+'/restore-receipt.json.DATA'),'fresh_private_restore':str(db),'incremental_closure_complete_against_published_base':True,'uncached_published_base_objects':len(base_missing),'no_missing_new_branch_objects':True,'no_live_code_adoption':True}
 scan=folder/'credential-marker-scan.json'
 if not scan.exists() and i==0:scan=S/'ipfs_accelerate_py/credential-marker-scan.json'
 if scan.exists():row['marker_scan']=copy(scan,label+'/credential-marker-scan.json.DATA')
 report.append(row)
 print(json.dumps({'family':row['family'],'tips':row['tip_count'],'fresh_restore':'closed'}),flush=True)
# Preserve the remaining exact A identity without re-copying its already-public 2GiB historical blob.
a='1c16fb1773a03a202523a7ff62d191717b7d8173'
source=Path('/home/barberb/lift_coding/artifacts/autoformalization-publication-20261004/canonical_git/hf-history-conversion-02/isolated.git')
raw=g(source,'cat-file','commit',a)
assert hashlib.sha1(f'commit {len(raw)}\0'.encode()+raw).hexdigest()==a
p=out/'accelerate-identical-public-tree/commit.DATA';p.parent.mkdir(exist_ok=True);p.write_bytes(raw)
rootdb=restore/(selections[0].replace('/','-')+'.git')
assert g(rootdb,'hash-object','-t','commit','-w','--stdin',raw=raw).decode().strip()==a
public='d6163a6cb844617f35f8f56d0b6ccd521fa677b7'
assert g(rootdb,'rev-parse',a+'^{tree}')==g(rootdb,'rev-parse',public+'^{tree}')
g(rootdb,'merge-base','--is-ancestor',public,report[0]['published_base'])
parents=[x.split()[1] for x in raw.decode().splitlines() if x.startswith('parent ')]
for parent in parents:g(rootdb,'cat-file','-e',parent+'^{commit}')
identity={'tip':a,'tree':g(rootdb,'rev-parse',a+'^{tree}').decode().strip(),'public_same_tree_ancestor':public,'parents':parents,'raw_commit':pin(p),'archive':'branches/accelerate-identical-public-tree/commit.DATA','public_tree_complete':True,'large_blob_previously_published':'9b6ded832adffea56cd1402bb08d1dca484eb3c8','new_large_blob_transfer':False}
summary={'schema':'renewed-historical-branch-preservation/v1','bundles':report,'restored_tip_count':sum(x['tip_count'] for x in report),'additional_public_tree_commit_identity':identity,'all_original_refs_untouched':True,'credential_marker_review':'Named small marker hits are static rejection fixtures, placeholders or examples. No 2GiB blob transferred. Prior scans retained.','code_adoption':False}
(W/'branch-retention.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n')
(out/'README.md').write_text('# Historical branch restoration\n\nEach bundle is incremental over its recorded public main base. Initialize a bare Git store with those base objects, run git bundle verify, then fetch the retained refs from the bundle. The publisher repeated restoration in new private stores and verified every expected tip and complete incremental object traversal against the recorded base without network. Some local base stores are partial clones, so a complete clone of the recorded public base is required when restoring elsewhere. The additional Accelerator raw commit has an exact source tree already on public main. Restore its published bases and the A34 bundle before importing that commit with git hash-object -t commit -w --stdin.\n\nThe restored branches remain historical alternatives. This archive does not install them as active application code. Marker-review records are retained and no new copy of the previously archived 2GiB dataset is included.\n')
print(json.dumps({'restored':summary['restored_tip_count'],'identity':a}))
