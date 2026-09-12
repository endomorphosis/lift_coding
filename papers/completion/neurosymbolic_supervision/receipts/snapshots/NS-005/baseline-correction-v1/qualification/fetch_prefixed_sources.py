from pathlib import Path
import json,hashlib,urllib.request,tarfile,shutil,concurrent.futures,datetime,subprocess
ROOT=Path('/home/barberb/lift_coding');HERE=Path(__file__).resolve().parent;LANE=ROOT/'.worktrees/vericodegen-neurosymbolic_supervision-2026';PAPER=LANE/'papers/completion/neurosymbolic_supervision'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 original=HERE/'original';original.mkdir(exist_ok=True)
 refs={}
 for rel in ['benchmark/tasks.jsonl','benchmark/splits.json','benchmark/oracle_manifest.json','receipts/NS-005.json','protocol/preregistered_protocol.md']:
  src=PAPER/rel;dst=original/rel;dst.parent.mkdir(parents=True,exist_ok=True)
  if not dst.exists():shutil.copyfile(src,dst)
  assert sha(src)==sha(dst);refs[rel]=sha(dst)
 rows=[json.loads(l) for l in (original/'benchmark/tasks.jsonl').read_text().splitlines() if l.strip()];targets=[r for r in rows if r.get('live_repair_admitted') and r['baseline']['visible_preexisting_node_count']==0];assert len(targets)==4
 def fetch(row):
  snap=row['source_snapshot'];slug=row['provenance']['upstream_slug'];commit=snap['pre_fix_commit'];dest=HERE/'source_cache'/row['task_id'];dest.mkdir(parents=True,exist_ok=True);arc=dest/'prefix.tar.gz';url=f'https://codeload.github.com/{slug}/tar.gz/{commit}'
  if not arc.exists():
   with urllib.request.urlopen(url,timeout=90) as response,arc.open('xb') as out:shutil.copyfileobj(response,out)
  tree=dest/'tree';tree.mkdir(exist_ok=True)
  links=[]
  with tarfile.open(arc) as tar:
   for member in tar.getmembers():
    path=Path(member.name);parts=path.parts[1:]
    if not parts:continue
    if path.is_absolute() or '..' in parts or member.islnk():raise RuntimeError('unsafe tar member')
    dst=tree.joinpath(*parts)
    if member.issym():
     target=(dst.parent/member.linkname).resolve()
     if Path(member.linkname).is_absolute() or not target.is_relative_to(tree.resolve()):raise RuntimeError('escaping symlink')
     links.append((dst,member.linkname))
    elif member.isdir():dst.mkdir(parents=True,exist_ok=True)
    elif member.isfile():
     dst.parent.mkdir(parents=True,exist_ok=True)
     with tar.extractfile(member) as source,dst.open('wb') as out:shutil.copyfileobj(source,out)
     dst.chmod(member.mode & 0o777)
  for dst,target in links:
   dst.parent.mkdir(parents=True,exist_ok=True)
   if not dst.is_symlink():dst.symlink_to(target)
  for item in snap['files']:assert sha(tree/item['path'])==item['sha256']
  return {'task_id':row['task_id'],'upstream':slug,'pre_fix_commit':commit,'url':url,'archive_sha256':sha(arc),'archive_bytes':arc.stat().st_size,'tree':str(tree),'admitted_source_hashes_verified':len(snap['files']),'downloaded_only_pre_fix':True}
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(fetch,targets))
 out={'schema':'ns005-unchanged-baseline-source-recovery/v1','at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'lane_head':subprocess.check_output(['git','-C',str(LANE),'rev-parse','HEAD'],text=True).strip(),'original_files':refs,'sources':results,'hidden_oracle_bodies_read':False,'population_unchanged':True}
 p=HERE/'source_recovery.json'
 with p.open('x') as f:json.dump(out,f,indent=2);f.write('\n')
 print(json.dumps({'report':str(p),'sha256':sha(p),'sources':[{k:r[k] for k in ['task_id','archive_bytes','admitted_source_hashes_verified']} for r in results]}))
if __name__=='__main__':main()
