"""Create a fresh signed LOCAL fixture at /app without dispatching it."""
import json
import os

from aa_harness_10 import (AA, CONTAINER, CONTAINER_PYTHON, EvidenceRun, RuntimeFreeze,
                        parse_args, pin)


def main():
    os.umask(0o077)
    freeze = RuntimeFreeze(parse_args().freeze_sha256)
    evidence = EvidenceRun("native-fixture-10", freeze)
    result = {"schema": "admitted-budget-native-fixture-preparation@1", "qualified": False,
              "runtime_freeze": freeze.to_dict(), "provider_calls": 0,
              "source_body_executed": False, "START_called": False,
              "worker_dispatched": False, "manual_native_prompt_is_fixture_only": True}
    try:
        setup = "import pathlib,os;p=pathlib.Path('/opt/ipfs-supervisor/public-fixture-aa10');assert not p.exists();p.mkdir(mode=0o755);os.chown(p,1000,1000)"
        evidence.command("public-directory", ["docker", "exec", "--user", "root", CONTAINER,
                                             CONTAINER_PYTHON, "-B", "-I", "-c", setup])
        program = AA / "container_prepare_signed_fixture_10.py"
        destination = "/opt/ipfs-supervisor/container-prepare-signed-aa10.py"
        result["authored_program"] = pin(program)
        evidence.upload_program(program, destination)
        answer = evidence.command("native-prepare", evidence.owner_argv(destination,
                                  state_namespace="aa-fixture-10"), timeout=300)
        result["native_summary"] = json.loads(answer.stdout.splitlines()[-1])
        public = evidence.output / "public"
        public.mkdir(mode=0o700)
        names = ["source.gitbundle", "manifest.json", "graph.json", "admission.json", "materialization.json",
                 "context-preparation.json", "task-readback.json", "native-prompt.txt", "native-capsule.json",
                 "compilation-receipt.json", "instruction-descriptor.json", "context-bundle.json", "owner-receipt.json"]
        for index, name in enumerate(names):
            evidence.command("public-export-%02d" % index, ["docker", "cp",
                CONTAINER + ":/opt/ipfs-supervisor/public-fixture-aa10/" + name, str(public / name)])
        result["public_exports"] = [pin(public / name) for name in names]
        result["qualified"] = result["native_summary"]["qualified"] is True
    except BaseException as error:
        result["failure"] = {"type": type(error).__name__, "message": str(error)[:2048]}
    finally:
        evidence.save("result.json", result)
        freeze.close()
        print(json.dumps({"qualified": result["qualified"], "output": str(evidence.output), "failure": result.get("failure")}))
    return 0 if result["qualified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
