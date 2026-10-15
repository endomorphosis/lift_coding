"""Run one fresh original in-container owner and export only its public outputs."""
import hashlib
import json
import os
from pathlib import Path

from aa_harness_08 import (AA, CONTAINER, CONTAINER_PYTHON, EvidenceRun, RuntimeFreeze,
                        parse_args, pin, public_bytes)


def main():
    os.umask(0o077)
    freeze = RuntimeFreeze(parse_args().freeze_sha256)
    evidence = EvidenceRun("actual-start-08", freeze)
    result = {"schema": "admitted-budget-actual-owner-invocation@1", "qualified": False,
              "runtime_freeze": freeze.to_dict(), "container": CONTAINER,
              "provider_calls": 0, "source_body_executed": False, "training_steps": 0,
              "private_database_cas_or_key_bodies_exported": False}
    expected_container_id = None
    try:
        boundary = json.loads(public_bytes(AA / "docker-boundary-08/result.json"))
        assert boundary["qualified"] is True and boundary["container"] == CONTAINER
        expected_container_id = boundary["container_id"]
        actual = evidence.command("container-identity", ["docker", "inspect", "--format", "{{.Id}}", CONTAINER]).stdout.decode().strip()
        if actual != expected_container_id:
            raise ValueError("only the exact fresh owned AA container may run or be disposed")
        program = AA / "container_run_admitted_08.py"
        result["authored_owner_program"] = pin(program)
        destination = "/opt/ipfs-supervisor/container-run-admitted-aa08.py"
        evidence.upload_program(program, destination)
        answer = evidence.command("native-owner", evidence.owner_argv(destination,
                                  state_namespace="aa-start-08"), timeout=240, allow_failure=True)
        if not answer.stdout.splitlines():
            raise RuntimeError("owner did not publish a bounded public execution receipt")
        execution = json.loads(answer.stdout.splitlines()[-1])
        result["owner_execution"] = execution
        names = execution["public_files"]
        if type(names) is not list or not 1 <= len(names) <= 80 or len(set(names)) != len(names):
            raise ValueError("bounded exact public output inventory required")
        for name in names:
            relative = Path(name)
            if type(name) is not str or relative.is_absolute() or relative.name != name or relative.suffix not in {".json", ".txt", ".log", ".stdout", ".stderr"}:
                raise ValueError("unknown public output path refused")
        public = evidence.output / "public"
        public.mkdir(mode=0o700)
        if execution["public_directory"] != "/opt/ipfs-supervisor/state/aa-start-08/public":
            raise ValueError("owner public output namespace differs")
        for index, name in enumerate(names):
            evidence.command("public-export-%02d" % index, ["docker", "cp",
                CONTAINER + ":" + execution["public_directory"] + "/" + name, str(public / name)])
        result["public_exports"] = [pin(public / name, 8 * 1024 * 1024) for name in names]
        summary = json.loads(public_bytes(public / "summary.json"))
        result["actual_summary"] = summary
        result["qualified"] = answer.returncode == 0 and execution["qualified"] is True and summary["qualified"] is True
        if result["qualified"]:
            assert summary["native_admitted_benchmark_runtime_START_used"] is True
            assert summary["actual_native_worker_observer_invocations"] == 1 and summary["provider_calls"] == 0
    except BaseException as error:
        result["failure"] = {"type": type(error).__name__, "message": str(error)[:2048]}
        result["qualified"] = False
    finally:
        # All native STOP/close operations occurred inside the original owner
        # while its live Quack owner remained open. Container disposal is a
        # final independent outer boundary, never a substitute for those gates.
        if expected_container_id is not None:
            try:
                current = evidence.command("cleanup-container-identity", ["docker", "inspect", "--format", "{{.Id}}", CONTAINER], allow_failure=True, cleanup=True)
                if current.returncode == 0:
                    if current.stdout.decode().strip() != expected_container_id:
                        raise ValueError("container identity changed before owned cleanup")
                    cleanup = evidence.command("outer-worker-cleanup", ["docker", "exec", "--user", "supervisor", CONTAINER,
                        "/usr/bin/sudo", "-n", "-u", "benchmarkworker", "--", "/opt/ipfs-supervisor/bin/worker-entry", "--cleanup"],
                        timeout=20, allow_failure=True, cleanup=True)
                    result["outer_worker_cleanup_returncode"] = cleanup.returncode
                    stopped = evidence.command("container-stop", ["docker", "stop", "--time", "10", CONTAINER], timeout=30, allow_failure=True, cleanup=True)
                    removed = evidence.command("container-remove", ["docker", "rm", CONTAINER], timeout=30, allow_failure=True, cleanup=True)
                    absence = evidence.command("container-absence", ["docker", "ps", "-aq", "--filter", "id=" + expected_container_id], cleanup=True)
                    result["container_disposal"] = {"stop_returncode": stopped.returncode, "remove_returncode": removed.returncode,
                        "container_absent": not bool(absence.stdout.strip()), "only_exact_owned_container_removed": True}
                    if cleanup.returncode != 0 or removed.returncode != 0 or absence.stdout.strip():
                        result["qualified"] = False
                else:
                    result["container_disposal"] = {"container_already_absent": True, "qualified_cleanup": False}
                    result["qualified"] = False
            except BaseException as error:
                result["cleanup_failure"] = {"type": type(error).__name__, "message": str(error)[:2048]}
                result["qualified"] = False
        try:
            freeze.check()
        except BaseException as error:
            result["freeze_failure"] = {"type": type(error).__name__, "message": str(error)[:2048]}
            result["qualified"] = False
        evidence.save("result.json", result)
        freeze.close()
        print(json.dumps({"qualified": result["qualified"], "output": str(evidence.output), "failure": result.get("failure")}))
    return 0 if result["qualified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
