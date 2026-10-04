from pathlib import Path
import hashlib,json,os,stat,subprocess,time
ROOT=Path('/home/barberb/lift_coding');OUT=Path(__file__).resolve().parent
source=json.loads((OUT/'selection.json').read_bytes());start=time.monotonic()
source_files=[];evidence=[]
for row in source['selected']:
    p=row['path']
    if p.startswith(('papers/revisions/','papers/completion/','artifacts/','.pgir_campaign/runtime/')):
        evidence.append(row);continue
    source_files.append(row)
index=OUT/'private-index-02';assert not index.exists();env={**os.environ,'GIT_INDEX_FILE':str(index),'GIT_TERMINAL_PROMPT':'0'}
def git(args,stdin=None):
    p=subprocess.run(['git','-c','gc.auto=0','-c','maintenance.auto=false',*args],cwd=ROOT,env=env,input=stdin,capture_output=True,timeout=180)
    assert p.returncode==0,(args[:2],p.returncode,p.stderr[:300]);return p.stdout
assert git(['rev-parse','HEAD']).decode().strip()==source['head']
git(['read-tree',source['head']]);entries=[];objects={};checks=[]
for row in source_files:
    name=row['path'];path=ROOT/name
    if row['type']=='deleted':entries.append(b'0 '+b'0'*40+b'\t'+os.fsencode(name)+b'\0');continue
    before=path.lstat()
    if row['type']=='link':raw=os.fsencode(os.readlink(path))
    else:
        fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
        with os.fdopen(fd,'rb') as stream:
            raw=stream.read();after=os.fstat(stream.fileno())
        assert (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns)==(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns)
    assert hashlib.sha256(raw).hexdigest()==row['sha256'] and len(raw)==row['bytes'],name
    key=(row['sha256'],row['bytes'])
    if key not in objects:objects[key]=git(['hash-object','-w','--stdin'],raw).strip()
    oid=objects[key];entries.append(row['mode'].encode()+b' '+oid+b'\t'+os.fsencode(name)+b'\0')
    # Audit the actual stored blob, independent of working-tree bytes/filters.
    blob=git(['cat-file','blob',oid.decode()]);assert blob==raw
    checks.append({'path':name,'mode':row['mode'],'git_blob':oid.decode(),'bytes':len(blob),'sha256':hashlib.sha256(blob).hexdigest()})
git(['update-index','--add','-z','--index-info'],b''.join(entries))
tree=git(['write-tree']).decode().strip()
original=source['original_index'];assert hashlib.sha256(Path(original['path']).read_bytes()).hexdigest()==original['sha256']
receipt={'schema':'terminal-ir-root-source-tree@2','tree':tree,'parent':source['head'],'private_index':str(index),'source_files':source_files,'stored_blob_checks':checks,'source_bytes':sum(r.get('bytes',0) for r in source_files),'evidence_files_huggingface':len(evidence),'evidence_bytes_huggingface':sum(r.get('bytes',0) for r in evidence),'evidence_paths':'selection.json:selected plus inventory.json paths','policy':'Source/docs/tests and final manuscripts in GitHub; generated evaluation/revision/runtime records and evidence caches in Hugging Face with content-addressed manifest. Originals unchanged.','original_index_unchanged':True,'elapsed_seconds':time.monotonic()-start,'published':False}
(OUT/'source-tree-02.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({k:receipt[k] for k in ('tree','source_bytes','evidence_files_huggingface','evidence_bytes_huggingface','elapsed_seconds')}))
