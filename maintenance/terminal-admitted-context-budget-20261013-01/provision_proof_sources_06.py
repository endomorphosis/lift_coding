"""Provision three legacy proof adapters without changing any source bytes.

This deliberately trusts the original owner for their shared parent directory;
it does not claim root-owned ancestors for runtime files in that directory.
"""
import hashlib
import json
import os
from pathlib import Path

from aa_harness_06 import (AA, CHECKOUT, CONTAINER, CONTAINER_PYTHON, EvidenceRun,
                           RuntimeFreeze, parse_args, pin, public_bytes, wire)

PROOF = ["benchmarks/agent_supervisor/container_coding/" + name for name in (
    "terminal_source_ir_lowering.py", "terminal_source_ir_projection.py", "terminal_revision_proof_cache.py")]
RUNTIME = [
    "ipfs_accelerate_py/agent_supervisor/runtime/checked_observer_budget.py",
    "ipfs_accelerate_py/agent_supervisor/runtime/checked_context_dispatch.py",
    "ipfs_accelerate_py/agent_supervisor/entrypoints/admitted_benchmark_runtime.py",
    "ipfs_accelerate_py/agent_supervisor/runtime/router_implementation_runner.py",
    "ipfs_accelerate_py/agent_supervisor/runtime/model_input_observation_receipt.py",
    "benchmarks/agent_supervisor/container_coding/container_worker_deployment.py",
    "ipfs_accelerate_py/agent_supervisor/todo_daemon/supervisor_runtime.py",
    "ipfs_accelerate_py/agent_supervisor/todo_daemon/implementation_daemon.py",
    "benchmarks/agent_supervisor/container_coding/terminal_checked_worker_budget.py",
]
PROGRAM = r'''import hashlib,json,os,pathlib,stat,sys
request=json.load(sys.stdin);root=pathlib.Path('/opt/ipfs-supervisor/source')
assert os.getuid()==os.geteuid()==0
assert not pathlib.Path('/opt/ipfs-supervisor/state/aa-model-06').exists()
assert not pathlib.Path('/opt/ipfs-supervisor/state/aa-start-06').exists()
proof=request['proof'];runtime=request['runtime']
assert len(proof)==3 and len(runtime)==9 and not set(proof)&set(runtime)
parent=root/'benchmarks/agent_supervisor/container_coding'
assert parent.resolve(strict=True)==parent and parent.is_dir()
assert parent.stat().st_uid==0 and stat.S_IMODE(parent.stat().st_mode)==0o755
def row(path):
 assert path.resolve(strict=True)==path
 fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW);before=os.fstat(fd)
 try:
  assert stat.S_ISREG(before.st_mode) and before.st_nlink==1 and 0<before.st_size<=8*1024*1024
  with os.fdopen(fd,'rb',closefd=False)as stream:raw=stream.read(8*1024*1024+1)
  witness=lambda s:(s.st_dev,s.st_ino,s.st_mode,s.st_uid,s.st_gid,s.st_nlink,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
  assert len(raw)==before.st_size and witness(before)==witness(os.fstat(fd))==witness(path.lstat())
 finally:os.close(fd)
 return {'path':str(path),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'uid':before.st_uid,'gid':before.st_gid,'mode':oct(stat.S_IMODE(before.st_mode)),'inode':before.st_ino,'device':before.st_dev}
before={}
for relative,expected in {**proof,**runtime}.items():
 path=root/relative;actual=row(path)
 assert actual['uid']==0 and actual['mode']=='0o444'
 assert actual['bytes']==expected['bytes'] and actual['sha256']==expected['sha256']
 before[relative]=actual
parent_before={'path':str(parent),'uid':parent.stat().st_uid,'gid':parent.stat().st_gid,'mode':oct(stat.S_IMODE(parent.stat().st_mode))}
# Ownership provisioning occurs before the next proof operation captures any FD.
os.chown(parent,1000,1000);parent.chmod(0o555)
for relative in proof:
 path=root/relative;assert path.parent==parent
 os.chown(path,1000,1000);path.chmod(0o444)
after={relative:row(root/relative)for relative in before}
for relative,previous in before.items():
 current=after[relative]
 assert all(current[key]==previous[key]for key in ('path','bytes','sha256','inode','device'))
 assert current['mode']=='0o444' and current['uid']==(1000 if relative in proof else 0)
assert parent.stat().st_uid==1000 and stat.S_IMODE(parent.stat().st_mode)==0o555
print(json.dumps({'schema':'admitted-budget-public-proof-producer-provision@1','qualified':True,
 'proof_files':list(proof),'runtime_files':list(runtime),'before':before,'after':after,
 'parent_before':parent_before,'parent_after':{'path':str(parent),'uid':parent.stat().st_uid,'gid':parent.stat().st_gid,'mode':oct(stat.S_IMODE(parent.stat().st_mode))},
 'source_bytes_unchanged':True,'runtime_nine_files_root_owned':True,'recursive_chown_used':False,
 'root_owned_source_ancestor_attestation':False,'trusted_original_owner_parent':True,
 'scope':'Only three legacy proof-adapter source files and their one exact shared directory changed ownership. The owner can change its directory permissions; original producer FD/stat/hash guards govern later operations. Root bin/profile ancestors and runtime file bytes/UIDs remain unchanged.',
 'provider_calls':0,'START_called':False,'source_body_executed':False,'training_steps':0}))
'''


def main():
    os.umask(0o077)
    freeze = RuntimeFreeze(parse_args().freeze_sha256)
    evidence = EvidenceRun("proof-source-provision-06", freeze)
    result = {"schema": "admitted-budget-public-proof-source-provision-execution@1", "qualified": False,
              "runtime_freeze": freeze.to_dict(), "container": CONTAINER,
              "provider_calls": 0, "START_called": False, "source_body_executed": False,
              "training_steps": 0, "production_code_bytes_modified": False}
    try:
        expected = {relative: pin(CHECKOUT / relative) for relative in PROOF + RUNTIME}
        freeze_body = json.loads(public_bytes(AA / "runtime-source-pins-06.json"))
        assert {row["relative_path"] for row in freeze_body["files"]} <= set(RUNTIME)
        request = {"proof": {name: expected[name] for name in PROOF}, "runtime": {name: expected[name] for name in RUNTIME}}
        answer = evidence.command("ownership-provision", ["docker", "exec", "-i", "--user", "root", CONTAINER,
            CONTAINER_PYTHON, "-B", "-I", "-c", PROGRAM], input_bytes=wire(request), timeout=30)
        result["provision"] = json.loads(answer.stdout)
        assert all(pin(CHECKOUT / relative) == expected[relative] for relative in PROOF + RUNTIME)
        result["original_host_source_bytes_unchanged"] = True
        result["qualified"] = result["provision"]["qualified"] is True
    except BaseException as error:
        result["failure"] = {"type": type(error).__name__, "message": str(error)[:2048]}
    finally:
        evidence.save("result.json", result)
        freeze.close()
        print(json.dumps({"qualified": result["qualified"], "output": str(evidence.output), "failure": result.get("failure")}))
    return 0 if result["qualified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
