"""Copy only public cached extension binaries and the named offline BPE file."""
import hashlib
import json
import os
from pathlib import Path

from aa_harness_16 import (CONTAINER, CONTAINER_PYTHON, EvidenceRun, RuntimeFreeze,
                        parse_args, pin)

BPE_URL = b"https://openaipublic.blob.core.windows.net/encodings/o200k_base.tiktoken"
BPE = Path("/tmp/data-gym-cache") / hashlib.sha1(BPE_URL).hexdigest()

PROGRAM = r'''import hashlib,json,os,pathlib,platform,shutil,stat
import duckdb
assert duckdb.__version__=='1.5.5' and platform.machine()=='aarch64'
source=pathlib.Path('/home/supervisor/.duckdb/extensions/v1.5.5/linux_arm64')
target=pathlib.Path('/opt/ipfs-supervisor/home/.duckdb/extensions/v1.5.5/linux_arm64')
target.mkdir(parents=True,exist_ok=True)
rows=[]
for name in ('ducklake.duckdb_extension','httpfs.duckdb_extension','quack.duckdb_extension'):
 p=source/name;q=target/name
 assert p.is_file() and not p.is_symlink() and not q.exists()
 raw=p.read_bytes();shutil.copyfile(p,q);assert q.read_bytes()==raw
 os.chown(q,1000,1000);q.chmod(0o444)
 rows.append({'source':str(p),'target':str(q),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'target_uid':q.stat().st_uid,'mode':oct(stat.S_IMODE(q.stat().st_mode))})
for p in (target,*target.parents):
 if p==pathlib.Path('/opt/ipfs-supervisor/home'):break
 os.chown(p,1000,1000);p.chmod(0o755)
cache=pathlib.Path('/opt/ipfs-supervisor/home/tokenizer-cache');assert not cache.exists()
cache.mkdir(mode=0o700);os.chown(cache,1000,1000)
print(json.dumps({'schema':'admitted-budget-offline-public-cache@1','files':rows,'network_used':False,'cached_image_public_extensions_used':True,'database_bodies_copied':False,'extension_bodies_exported':False}))
'''


def main():
    os.umask(0o077)
    freeze = RuntimeFreeze(parse_args().freeze_sha256)
    evidence = EvidenceRun("offline-cache-16", freeze)
    result = {"schema": "admitted-budget-offline-cache-provisioning@1", "qualified": False,
              "runtime_freeze": freeze.to_dict(), "provider_calls": 0, "network_used": False,
              "credentials_transferred": False, "database_bodies_copied": False}
    try:
        result["bpe_source"] = pin(BPE)
        copied = evidence.command("extensions", ["docker", "exec", "--user", "root", CONTAINER,
            CONTAINER_PYTHON, "-B", "-I", "-c", PROGRAM], timeout=30)
        result["extensions"] = json.loads(copied.stdout)
        destination = "/opt/ipfs-supervisor/home/tokenizer-cache/" + BPE.name
        evidence.command("bpe-copy", ["docker", "cp", str(BPE), CONTAINER + ":" + destination])
        protect = "import pathlib,os,hashlib,json;p=pathlib.Path(" + repr(destination) + ");assert not p.is_symlink();b=p.read_bytes();assert len(b)==" + str(result["bpe_source"]["bytes"]) + ";assert hashlib.sha256(b).hexdigest()==" + repr(result["bpe_source"]["sha256"]) + ";os.chown(p,1000,1000);p.chmod(0o444);print(json.dumps({'public_bpe_exact':True,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}))"
        result["bpe_target"] = json.loads(evidence.command("bpe-protect", ["docker", "exec", "--user", "root", CONTAINER,
            CONTAINER_PYTHON, "-B", "-I", "-c", protect], timeout=30).stdout)
        check = r'''import sys,duckdb,json,pathlib
sys.path.insert(0,'/opt/ipfs-supervisor/tokenizer')
import tiktoken
assert tiktoken.__version__=='0.13.0'
c=duckdb.connect(':memory:');c.execute('SET autoinstall_known_extensions=false');c.execute('SET autoload_known_extensions=false')
for name in ('ducklake','httpfs','quack'):c.execute('LOAD '+name)
assert tiktoken.get_encoding('o200k_base').encode('Stage AA offline token check')
print(json.dumps({'duckdb_version':duckdb.__version__,'tokenizer_version':tiktoken.__version__,'native_offline_extension_loads':['ducklake','httpfs','quack'],'offline_BPE_loaded':True,'network_used':False}))
'''
        argv = ["docker", "exec", "--user", "supervisor", "--env", "HOME=/opt/ipfs-supervisor/home",
                "--env", "TIKTOKEN_CACHE_DIR=/opt/ipfs-supervisor/home/tokenizer-cache",
                CONTAINER, CONTAINER_PYTHON, "-B", "-I", "-c", check]
        result["native_load"] = json.loads(evidence.command("offline-native-load", argv, timeout=30).stdout)
        if pin(BPE) != result["bpe_source"]:
            raise ValueError("original public BPE file changed")
        result["qualified"] = True
    except BaseException as error:
        result["failure"] = {"type": type(error).__name__, "message": str(error)[:2048]}
    finally:
        evidence.save("result.json", result)
        freeze.close()
        print(json.dumps({"qualified": result["qualified"], "output": str(evidence.output), "failure": result.get("failure")}))
    return 0 if result["qualified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
