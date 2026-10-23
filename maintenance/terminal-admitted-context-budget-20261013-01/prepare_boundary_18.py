"""Prepare only the fresh offline AA container and real worker boundary."""
import asyncio
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tarfile
from types import SimpleNamespace

from aa_harness_18 import (AA, CHECKOUT, CONTAINER, CONTAINER_PYTHON, IMAGE, LEAN, PINNED, TOKENIZER,
                        EvidenceRun, RuntimeFreeze, parse_args, pin, public_bytes)


class DockerEnvironment:
    def __init__(self, evidence):
        self.evidence = evidence
        self.sequence = 0

    async def exec(self, *, command, cwd, user, env=None, timeout_sec=180):
        self.sequence += 1
        argv = ["docker", "exec", "--user", user, "--workdir", cwd]
        for key, value in sorted((env or {}).items()):
            argv += ["--env", key + "=" + value]
        result = await asyncio.to_thread(self.evidence.command, "exec-%03d" % self.sequence,
                   argv + [CONTAINER, "/bin/sh", "-c", command], timeout=timeout_sec,
                   allow_failure=True)
        return SimpleNamespace(stdout=result.stdout.decode(), stderr=result.stderr.decode(),
                               return_code=result.returncode)

    async def upload_file(self, source, destination):
        self.sequence += 1
        await asyncio.to_thread(self.evidence.command, "upload-%03d" % self.sequence,
                               ["docker", "cp", str(source), CONTAINER + ":" + destination])


async def main():
    os.umask(0o077)
    freeze = RuntimeFreeze(parse_args().freeze_sha256)
    evidence = EvidenceRun("docker-boundary-18", freeze)
    result = {"schema": "admitted-budget-container-boundary@1", "qualified": False,
              "container": CONTAINER, "provider_calls": 0, "credentials_transferred": False,
              "repository_source_executed": False, "native_START_called": False,
              "training_steps": 0, "full_supervisor_entrypoint_used": False,
              "runtime_freeze": freeze.to_dict()}
    try:
        for source in (LEAN, TOKENIZER):
            if not source.is_dir() or source.resolve(strict=True) != source:
                raise ValueError("exact public read-only mount directory required")
        image = evidence.command("image-identity", ["docker", "image", "inspect", "--format", "{{json .Id}} {{json .Architecture}} {{json .Os}} {{json .Config.User}}", IMAGE])
        result["image_public_identity"] = image.stdout.decode().strip()
        absence = evidence.command("container-name-absence", ["docker", "ps", "-a", "--filter", "name=^/" + CONTAINER + "$", "--format", "{{.Names}}"])
        if absence.stdout.strip():
            raise ValueError("exact fresh container name required")
        launched = evidence.command("launch", ["docker", "run", "--detach", "--network", "none",
            "--mount", "type=bind,src=" + str(LEAN) + ",dst=/opt/ipfs-supervisor/lean,readonly",
            "--mount", "type=bind,src=" + str(TOKENIZER) + ",dst=/opt/ipfs-supervisor/tokenizer,readonly",
            "--name", CONTAINER, "--entrypoint", "/bin/sleep", IMAGE, "infinity"])
        result["container_id"] = launched.stdout.decode().strip()
        actual_mounts = json.loads(evidence.command("mounts", ["docker", "inspect", "--format", "{{json .Mounts}}", CONTAINER]).stdout)
        expected = {(str(LEAN), "/opt/ipfs-supervisor/lean"), (str(TOKENIZER), "/opt/ipfs-supervisor/tokenizer")}
        if len(actual_mounts) != 2 or {(row["Source"], row["Destination"]) for row in actual_mounts} != expected or any(row["Type"] != "bind" or row["RW"] is not False for row in actual_mounts):
            raise ValueError("only the two declared read-only public mounts are permitted")
        result["mounts"] = [{key: row[key] for key in ("Type", "Source", "Destination", "RW")} for row in actual_mounts]
        setup = r'''import os,pathlib,pwd,subprocess
root=pathlib.Path('/opt/ipfs-supervisor');owner=pwd.getpwnam('supervisor');worker=pwd.getpwnam('benchmarkworker')
assert owner.pw_uid==1000 and worker.pw_uid==1001 and worker.pw_gid==owner.pw_gid
home=root/'worker-home';assert home.is_dir() and not any(home.iterdir())
subprocess.run(['userdel','benchmarkworker'],check=True)
for p in (root/'home',root/'home/.codex',root/'codex-auth',root/'state'):
 p.mkdir(parents=True,exist_ok=True);os.chown(p,1000,owner.pw_gid);p.chmod(0o700)
repo=pathlib.Path('/app');repo.mkdir(exist_ok=True);assert not any(repo.iterdir())
os.chown(repo,1000,owner.pw_gid)
subprocess.run(['git','init','-q',str(repo)],check=True)
subprocess.run(['git','-C',str(repo),'-c','safe.directory=/app','-c','user.name=AA boundary fixture','-c','user.email=fixture@example.invalid','commit','--allow-empty','-qm','Authored empty AA permission baseline'],check=True)
for base,dirs,files in os.walk(repo):
 os.chown(base,1000,owner.pw_gid)
 for name in files:os.chown(pathlib.Path(base)/name,1000,owner.pw_gid)
print('Fresh empty-account and Git permission setup; no repository code executed')
'''
        evidence.command("permission-setup", ["docker", "exec", "--user", "root", CONTAINER, CONTAINER_PYTHON, "-I", "-c", setup])
        archive = evidence.output / "public-source.tar.gz"
        inventory = []
        with tarfile.open(archive, "x:gz", compresslevel=1) as bundle:
            for base, roots, prefix in ((CHECKOUT, ["ipfs_accelerate_py", "benchmarks"], "source"),
                                       (PINNED / "datasets", ["ipfs_datasets_py"], "datasets"),
                                       (PINNED / "kit", ["ipfs_kit_py"], "kit")):
                names = subprocess.check_output(["rg", "--files", "-g", "*.py", *roots], cwd=base, text=True).splitlines()
                if base == CHECKOUT:
                    sql = base / "ipfs_accelerate_py/agent_supervisor/task_sources/sql"
                    sql_names = sorted(path.name for path in sql.iterdir() if path.is_file() and path.suffix == ".sql")
                    if len(sql_names) != 5:
                        raise ValueError("exactly five public migration source assets required")
                    names += [str((sql / name).relative_to(base)) for name in sql_names]
                for name in sorted(names):
                    source = base / name
                    raw = public_bytes(source)
                    target = prefix + "/" + name
                    member = tarfile.TarInfo(target)
                    member.size = len(raw); member.mode = 0o444; member.uid = member.gid = 0
                    bundle.addfile(member, io.BytesIO(raw))
                    inventory.append({"source": str(source), "target": target, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()})
        evidence.save("source-inventory.json", {"files": inventory, "archive": pin(archive, 256 * 1024 * 1024),
            "scope": "Explicit public Python packages plus five migration SQL sources; no database/model/CAS bodies; sequential file snapshot only."})
        evidence.command("upload-source", ["docker", "cp", str(archive), CONTAINER + ":/tmp/aa-public-source.tar.gz"])
        evidence.command("protect-source", ["docker", "exec", "--user", "root", CONTAINER, "/bin/sh", "-c",
            "tar -xzf /tmp/aa-public-source.tar.gz -C /opt/ipfs-supervisor && rm /tmp/aa-public-source.tar.gz && chown -R root:root /opt/ipfs-supervisor/source /opt/ipfs-supervisor/datasets /opt/ipfs-supervisor/kit && find /opt/ipfs-supervisor/source /opt/ipfs-supervisor/datasets /opt/ipfs-supervisor/kit -type d -exec chmod 0755 {} +"])
        freeze.check()
        sys.path.insert(0, str(CHECKOUT))
        from benchmarks.agent_supervisor.container_coding.container_worker_deployment import install_worker_boundary, qualify_worker_boundary
        environment = DockerEnvironment(evidence)
        result["installation"] = await install_worker_boundary(environment, container_name=CONTAINER,
            output=evidence.output / "installation", observer_only=True)
        result["qualification"] = await qualify_worker_boundary(environment, output=evidence.output / "qualification")
        freeze.check()
        result["qualified"] = result["qualification"]["qualified"] is True
        result["container_left_running_for_owned_followup"] = True
    except BaseException as error:
        result["failure"] = {"type": type(error).__name__, "message": str(error)[:2048]}
        result["partial_container_retained_for_review"] = True
    finally:
        evidence.save("result.json", result)
        freeze.close()
        print(json.dumps({"qualified": result["qualified"], "output": str(evidence.output), "failure": result.get("failure")}))
    return 0 if result["qualified"] else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
