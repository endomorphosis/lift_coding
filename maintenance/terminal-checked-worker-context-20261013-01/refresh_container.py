"""Refresh explicitly changed public runtime source in the owned fixture only."""
import hashlib,io,json,os,subprocess,tarfile,sys
from pathlib import Path
Z=Path(__file__).resolve().parent;C=Z/'checkout';os.umask(0o077)
rows=subprocess.check_output(['git','status','--porcelain=v1','--untracked-files=all'],cwd=C,text=True).splitlines()
paths=sorted({line[3:] for line in rows if line[3:].endswith('.py') and line[3:].startswith(('ipfs_accelerate_py/','benchmarks/')) and '/test_' not in line[3:]})
name=sys.argv[1] if len(sys.argv)>1 else 'final-runtime-update'
assert name.isidentifier() or all(c.isalnum() or c=='-' for c in name)
archive=Z/(name+'.tar');assert not archive.exists()
pins=[]
with tarfile.open(archive,'w') as t:
 for relative in paths:
  p=C/relative;raw=p.read_bytes();info=tarfile.TarInfo(relative);info.size=len(raw);info.mode=0o644;t.addfile(info,io.BytesIO(raw))
  pins.append({'relative_path':relative,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
container='ipfs-checked-worker-context-z01';target='/opt/ipfs-supervisor/'+name+'.tar'
subprocess.run(['docker','cp',str(archive),container+':'+target],check=True,capture_output=True,timeout=30)
subprocess.run(['docker','exec','--user','root',container,'tar','-xf',target,'-C','/opt/ipfs-supervisor/source'],check=True,capture_output=True,timeout=30)
program='import hashlib,json,pathlib,sys;rows=json.load(sys.stdin);out=[]\nfor r in rows:\n p=pathlib.Path("/opt/ipfs-supervisor/source")/r["relative_path"];p.chmod(0o444);b=p.read_bytes();assert len(b)==r["bytes"] and hashlib.sha256(b).hexdigest()==r["sha256"];out.append(r)\nprint(json.dumps({"verified":True,"files":out}))'
r=subprocess.run(['docker','exec','-i','--user','root',container,'/opt/ipfs-supervisor/venv/bin/python','-B','-I','-c',program],input=json.dumps(pins).encode(),capture_output=True,check=True,timeout=30)
with (Z/(name+'.json')).open('x') as f:json.dump(json.loads(r.stdout),f,sort_keys=True,indent=2);f.write('\n')
print(json.dumps({'runtime_source_files':len(pins),'all_container_copies_exact':True}))
