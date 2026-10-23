"""Provision only cached public DuckDB extension binaries into the owner HOME."""
import json,subprocess,os
from pathlib import Path
Z=Path(__file__).resolve().parent;os.umask(0o077)
program='''import hashlib,json,pathlib,shutil,os,stat,duckdb,platform
assert duckdb.__version__=='1.5.5' and platform.machine()=='aarch64'
source=pathlib.Path('/home/supervisor/.duckdb/extensions/v1.5.5/linux_arm64')
target=pathlib.Path('/opt/ipfs-supervisor/home/.duckdb/extensions/v1.5.5/linux_arm64');target.mkdir(parents=True,exist_ok=True)
rows=[]
for name in ['ducklake.duckdb_extension','httpfs.duckdb_extension','quack.duckdb_extension']:
 p=source/name;assert p.is_file() and not p.is_symlink();q=target/name
 if not q.exists():shutil.copyfile(p,q)
 assert not q.is_symlink();raw=p.read_bytes();assert q.read_bytes()==raw
 os.chown(q,1000,1000);q.chmod(0o444)
 rows.append({'source':str(p),'target':str(q),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'target_uid':q.stat().st_uid,'mode':oct(stat.S_IMODE(q.stat().st_mode))})
for p in [target,*target.parents]:
 if p==pathlib.Path('/opt/ipfs-supervisor/home'):break
 os.chown(p,1000,1000);p.chmod(0o755)
print(json.dumps({'schema':'checked-worker-offline-duckdb-extension-prerequisite@1','files':rows,'network_used':False,'cached_image_public_extensions_used':True,'database_bodies_copied':False,'extension_bodies_exported':False}))'''
r=subprocess.run(['docker','exec','--user','root','ipfs-checked-worker-context-z02','/opt/ipfs-supervisor/venv/bin/python','-B','-I','-c',program],capture_output=True,timeout=30)
(Z/'offline-duckdb-prerequisite.stdout').write_bytes(r.stdout);(Z/'offline-duckdb-prerequisite.stderr').write_bytes(r.stderr)
assert r.returncode==0,r.stderr.decode()
value=json.loads(r.stdout)
check=subprocess.run(['docker','exec','--user','supervisor','--env','HOME=/opt/ipfs-supervisor/home','ipfs-checked-worker-context-z02','/opt/ipfs-supervisor/venv/bin/python','-B','-I','-c',"import duckdb,json;c=duckdb.connect(':memory:');c.execute('SET autoinstall_known_extensions=false');c.execute('SET autoload_known_extensions=false');c.execute('LOAD ducklake');print(json.dumps({'duckdb_version':duckdb.__version__,'native_offline_ducklake_load_passed':True,'network_used':False}))"],capture_output=True,timeout=30)
assert check.returncode==0,check.stderr.decode();value['native_load']=json.loads(check.stdout)
with (Z/'offline-duckdb-prerequisite.json').open('x') as f:json.dump(value,f,sort_keys=True,indent=2);f.write('\n')
print(json.dumps({'public_extension_files':len(value['files']),'native_offline_ducklake_load_passed':True}))
