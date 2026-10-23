"""Export an already qualified original model; never rerun its model checker."""
import hashlib
import io
import json
import os
from pathlib import Path
import tarfile

from aa_harness_05 import (AA, CONTAINER, CONTAINER_PYTHON, PREVIOUS, EvidenceRun,
                        RuntimeFreeze, parse_args, pin, public_bytes, wire, write_exclusive)


def public_pattern():
    path = PREVIOUS / "actual-public-inventory.json"
    value = json.loads(public_bytes(path))
    root = PREVIOUS / "actual-public-checked-01"
    names = []
    for row in value["files"]:
        relative = Path(row["path"]).relative_to(root)
        name = relative.as_posix()
        if relative.is_absolute() or ".." in relative.parts or set(relative.parts) & {"cas", "lake", ".git"}:
            raise ValueError("only named predecessor public path patterns may be reused")
        if relative.suffix not in {".json", ".jsonl", ".py", ".lean", ".olean"} and name not in {"model/candidate-cache/artifact.bin", "model/callee/candidate-cache/artifact.bin"}:
            raise ValueError("private storage or unknown file excluded")
        names.append(name)
    if len(names) != len(set(names)) or len(names) != 113:
        raise ValueError("exact113 public relative path pattern required")
    return sorted(names), pin(path)


def main():
    os.umask(0o077)
    freeze = RuntimeFreeze(parse_args().freeze_sha256)
    evidence = EvidenceRun("model-qualification-05", freeze)
    result = {"schema": "admitted-budget-container-model-execution@1", "qualified": False,
              "runtime_freeze": freeze.to_dict(), "provider_calls": 0, "training_steps": 0,
              "source_body_executed": False, "START_called": False,
              "database_cas_lake_bodies_exported": False,
              "native_model_executed_by_export_driver": False,
              "fresh_native_Lean_processes": 0, "original_native_Lean_processes": 3}
    try:
        names, predecessor = public_pattern()
        result["public_relative_path_pattern"] = predecessor
        original = AA / "model-qualification-04"
        command_path = original / "native-model.json"
        command_raw = freeze._retain(command_path)
        command = json.loads(command_raw)
        assert command["returncode"] == 0 and command["timed_out"] is False
        assert command["argv"][-1] == "/opt/ipfs-supervisor/container-qualify-aa-model04.py"
        stdout_path, stderr_path = original / "native-model.stdout", original / "native-model.stderr"
        assert command["stdout"]["path"] == str(stdout_path) and command["stderr"]["path"] == str(stderr_path)
        stdout_raw = freeze._retain(stdout_path, expected=command["stdout"])
        freeze._retain(stderr_path, expected=command["stderr"])
        assert len(stdout_raw.splitlines()) == 1
        result["native_summary"] = json.loads(stdout_raw.splitlines()[0])
        assert result["native_summary"]["qualified"] is True
        assert result["native_summary"]["model_status"] == "model_proved"
        assert result["native_summary"]["rows"] == 49
        assert result["native_summary"]["model_state"] == "/opt/ipfs-supervisor/state/aa-model-04"
        assert result["native_summary"]["repository"] == "/app"
        original_result = original / "result.json"
        original_raw = freeze._retain(original_result)
        original_report = json.loads(original_raw)
        assert original_report["qualified"] is False  # Export failed; preserve it.
        assert wire(original_report["native_summary"]) == wire(result["native_summary"])
        model_program = AA / "container_qualify_model_04.py"
        freeze._retain(model_program, expected=original_report["authored_program"])
        result["authored_program"] = pin(Path(__file__).resolve())
        result["original_model_execution"] = {"command_receipt": pin(command_path),
            "stdout": pin(stdout_path), "stderr": pin(stderr_path),
            "failed_export_report": pin(original_result), "model_program": pin(model_program),
            "native_model_was_run_by_original_attempt04": True,
            "native_model_reexecuted_here": False}
        # The export program opens precisely these113 paths, not a directory or store walk.
        export = r'''import hashlib,io,json,os,pathlib,stat,sys,tarfile
names=json.load(sys.stdin);base=pathlib.Path('/opt/ipfs-supervisor/state/aa-model-04');repository=pathlib.Path('/app')
output=base/'aa-public-model-05.tar';assert not output.exists()
rows=[];total=0
with tarfile.open(output,'x:')as archive:
 for name in names:
  relative=pathlib.Path(name);assert not relative.is_absolute() and '..' not in relative.parts and not set(relative.parts)&{'cas','lake','.git'}
  path=repository/pathlib.Path(*relative.parts[1:]) if relative.parts[0]=='repository' else base/relative
  assert path.resolve(strict=True)==path
  fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW);before=os.fstat(fd)
  try:
   assert stat.S_ISREG(before.st_mode) and before.st_nlink==1 and 0<=before.st_size<=8*1024*1024
   with os.fdopen(fd,'rb',closefd=False)as stream:raw=stream.read(8*1024*1024+1)
   witness=lambda s:(s.st_dev,s.st_ino,s.st_mode,s.st_uid,s.st_gid,s.st_nlink,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
   assert len(raw)==before.st_size and witness(before)==witness(os.fstat(fd))==witness(path.lstat())
  finally:os.close(fd)
  total+=len(raw);assert total<=32*1024*1024
  member=tarfile.TarInfo(name);member.size=len(raw);member.mode=0o644;archive.addfile(member,io.BytesIO(raw))
  rows.append({'container_path':str(path),'relative_path':name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
output.chmod(0o444)
print(json.dumps({'schema':'admitted-budget-explicit-model-public-export@1','files':rows,'archive':str(output),'source_repository':'/app','private_model_state':str(base),'database_cas_lake_bodies_exported':False,'directory_walk_used':False}))
'''
        argv = ["docker", "exec", "-i", "--user", "supervisor", CONTAINER,
                CONTAINER_PYTHON, "-B", "-I", "-c", export]
        exported = json.loads(evidence.command("public-export-build", argv, input_bytes=wire(names), timeout=60).stdout)
        archive = evidence.output / "public-model.tar"
        evidence.command("public-export-copy", ["docker", "cp", CONTAINER + ":" + exported["archive"], str(archive)])
        public = evidence.output / "public"
        public.mkdir(mode=0o700)
        by_name = {row["relative_path"]: row for row in exported["files"]}
        with tarfile.open(archive, "r:") as bundle:
            members = bundle.getmembers()
            if len(members) != 113 or {member.name for member in members} != set(names):
                raise ValueError("export archive differs from exact public path pattern")
            for member in members:
                if not member.isfile() or member.issym() or member.islnk() or not 0 <= member.size <= 8 * 1024 * 1024:
                    raise ValueError("only bounded public regular export members are permitted")
                raw = bundle.extractfile(member).read(8 * 1024 * 1024 + 1)
                row = by_name[member.name]
                if len(raw) != row["bytes"] or hashlib.sha256(raw).hexdigest() != row["sha256"]:
                    raise ValueError("public export pin differs")
                write_exclusive(public / member.name, raw)
        result["public_export"] = exported
        result["public_files"] = [pin(public / name) for name in names]
        result["archive"] = pin(archive, 32 * 1024 * 1024 + 1024 * 1024)
        source_summary_path = public / "qualification-summary.json"
        source_summary = json.loads(public_bytes(source_summary_path))
        assert source_summary["qualified"] is True and source_summary["result_cid"] == result["native_summary"]["result_cid"]
        assert source_summary["fresh_native_Lean_processes"] == 3 and source_summary["rows"] == 49
        assert len(source_summary["families"]) == 20 and source_summary["model_state"] == "/opt/ipfs-supervisor/state/aa-model-04"
        result["qualification_source_origin"] = {"container_path": "/opt/ipfs-supervisor/state/aa-model-04/qualification-summary.json",
            "host_pin": pin(source_summary_path), "original_native_model_result_cid": source_summary["result_cid"],
            "original_model_attempt": 4, "export_attempt": 5, "new_prover_invocations": 0}
        freeze.check()
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
