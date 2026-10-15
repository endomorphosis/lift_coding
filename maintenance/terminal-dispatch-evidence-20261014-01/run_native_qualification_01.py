"""One exclusive complete setup/native qualification/disposal campaign.

Requires the root's exact final producer, harness and matrix freeze pin. There is
no implicit Docker work on import and no predecessor evidence is changed.
"""
import argparse
import json
import os
from pathlib import Path
import re
import sys


CASES = ("baseline", "stale-head", "swapped-allocation", "modified-artifact", "disconnect", "exceeded-budget", "replayed-nonce")
STEPS = (
    ("prepare_boundary_01.py", "docker-boundary-01", 360),
    ("provision_offline_cache_01.py", "offline-cache-01", 180),
    ("prepare_signed_fixture_01.py", "native-fixture-01", 420),
    ("provision_proof_sources_01.py", "proof-source-provision-01", 120),
    ("qualify_container_model_01.py", "model-qualification-01", 480),
    ("run_admitted_owner_01.py", "actual-start-01", 360),
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze-sha256", required=True)
    parser.add_argument("--freeze-name", default="runtime-source-pins-01.json")
    parser.add_argument("--case", choices=CASES, required=True)
    parser.add_argument("--run-number", default="01")
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9]{2,4}", args.run_number):
        raise ValueError("two to four digit exclusive run number required")
    if not re.fullmatch(r"runtime-source-pins-[0-9]{2,4}\.json", args.freeze_name):
        raise ValueError("one exact bounded AB-root freeze manifest name required")
    os.umask(0o077)
    os.environ["TERMINAL_DISPATCH_EVIDENCE_CASE"] = args.case
    os.environ["TERMINAL_DISPATCH_EVIDENCE_RUN_TAG"] = args.case + "-" + args.run_number
    os.environ["TERMINAL_DISPATCH_EVIDENCE_FREEZE_NAME"] = args.freeze_name
    from ab_harness_01 import AB, CASE, RUN_TAG, CONTAINER, CONTAINER_PYTHON, EVIDENCE_ROOT, EvidenceRun, RuntimeFreeze, pin, public_bytes
    freeze = RuntimeFreeze(args.freeze_sha256)
    if EVIDENCE_ROOT.exists():
        freeze.close()
        raise FileExistsError("exclusive qualification namespace already exists")
    EVIDENCE_ROOT.mkdir(mode=0o700)
    evidence = EvidenceRun("campaign-control", freeze)
    result = {"schema": "terminal-dispatch-native-qualification-campaign@1", "case": CASE, "run_tag": RUN_TAG,
        "qualified": False, "container": CONTAINER, "runtime_freeze": freeze.to_dict(), "steps": [],
        "provider_calls": 0, "training_steps": 0, "source_body_executed": False,
        "Terminal_Bench_harness_used": False, "full_task_satisfaction": False,
        "source_to_model_equivalence_proved": False, "convergence_proved": False,
        "worker_JSON_emitter_independently_proved": False, "proof_authority": False, "completion_authority": False}
    container_id = None
    try:
        frozen = json.loads(freeze.raw)
        scripts = {Path(row["path"]).name for row in frozen.get("scripts", [])}
        required_scripts = {name for name, _, _ in STEPS} | {"ab_harness_01.py", "run_native_qualification_01.py",
            "native_fault_controls_01.py", "container_prepare_signed_fixture_01.py", "container_qualify_model_01.py", "container_run_admitted_01.py"}
        if not required_scripts <= scripts:
            raise ValueError("all exact authored campaign/setup/owner/fault scripts must be in final freeze")
        configurations = frozen.get("configurations", [])
        if len(configurations) != 1 or configurations[0]["path"] != str(AB / "native-qualification-matrix-01.json"):
            raise ValueError("the exact native qualification matrix must be in final freeze")
        matrix = json.loads(public_bytes(AB / "native-qualification-matrix-01.json"))
        assert matrix["schema"] == "terminal-dispatch-native-qualification-matrix@1"
        assert [row["case"] for row in matrix["cases"]] == list(CASES)
        result["matrix"] = pin(AB / "native-qualification-matrix-01.json")
        if CASE == "replayed-nonce":
            result.update(native_run_attempted=False, qualification_open=True,
                reason="No existing safe seam lets the authentic native wrapper replay an issued nonce; foreign-client or mocked-authority substitution is excluded.")
        else:
            for ordinal, (script, namespace, timeout) in enumerate(STEPS):
                answer = evidence.command("step-%02d" % ordinal,
                    [sys.executable, "-B", str(AB / script), "--freeze-sha256", args.freeze_sha256,
                        "--freeze-name", args.freeze_name],
                    timeout=timeout, allow_failure=True)
                child_path = EVIDENCE_ROOT / namespace / "result.json"
                child = json.loads(public_bytes(child_path))
                result["steps"].append({"script": script, "returncode": answer.returncode,
                    "result": pin(child_path), "qualified": child["qualified"] is True})
                if ordinal == 0:
                    container_id = child.get("container_id")
                    if type(container_id) is not str or not re.fullmatch(r"[0-9a-f]{64}", container_id):
                        raise ValueError("exact Docker creation ID must be retained before followup")
                    result["container_id"] = container_id
                if answer.returncode != 0 or child["qualified"] is not True:
                    raise RuntimeError("actual campaign step did not qualify: " + script)
            native = json.loads(public_bytes(EVIDENCE_ROOT / "actual-start-01/public/summary.json"))
            assert native["case"] == CASE and native["qualified"] is True
            assert native["native_admitted_benchmark_runtime_START_used"] is True
            assert native["worker_JSON_emitter_independently_proved"] is False
            result["native_summary"] = native
            result["qualified"] = True
    except BaseException as error:
        result["failure"] = {"type": type(error).__name__, "message": str(error)[:2048]}
        result["qualified"] = False
    finally:
        # An intermediate setup failure is still disposed by exact captured ID.
        # Outer disposal never substitutes for the original owner's STOP fence.
        try:
            if container_id is None:
                launch_path = EVIDENCE_ROOT / "docker-boundary-01/launch.stdout"
                if launch_path.exists():
                    captured = public_bytes(launch_path).decode().strip()
                    if re.fullmatch(r"[0-9a-f]{64}", captured):
                        container_id = captured
            if container_id is not None:
                inspected = evidence.command("final-owned-container-identity", ["docker", "inspect", "--format", "{{.Id}}", CONTAINER], allow_failure=True, cleanup=True)
                if inspected.returncode == 0:
                    if inspected.stdout.decode().strip() != container_id:
                        raise ValueError("container name was rebound; disposal refused")
                    evidence.command("final-isolated-cleanup", ["docker", "exec", "--user", "supervisor", container_id,
                        "/usr/bin/sudo", "-n", "-u", "benchmarkworker", "--", "/opt/ipfs-supervisor/bin/worker-entry", "--cleanup"],
                        timeout=20, allow_failure=True, cleanup=True)
                    stopped = evidence.command("final-container-stop", ["docker", "stop", "--time", "10", container_id], timeout=30, allow_failure=True, cleanup=True)
                    removed = evidence.command("final-container-remove", ["docker", "rm", container_id], timeout=30, allow_failure=True, cleanup=True)
                    if removed.returncode != 0:
                        raise RuntimeError("exact owned container disposal failed")
                    result["container_disposal"] = {"stop_returncode": stopped.returncode, "remove_returncode": removed.returncode, "exact_owned_container_id": container_id}
                absence = evidence.command("final-owned-container-absence", ["docker", "ps", "-aq", "--filter", "id=" + container_id], cleanup=True)
                assert not absence.stdout.strip(), "exact owned container remains present"
                result["owned_container_absent"] = True
            freeze.check()
        except BaseException as error:
            result["cleanup_failure"] = {"type": type(error).__name__, "message": str(error)[:2048]}
            result["qualified"] = False
        evidence.save("result.json", result)
        freeze.close()
        print(json.dumps({"qualified": result["qualified"], "case": CASE, "output": str(EVIDENCE_ROOT),
            "qualification_open": result.get("qualification_open", False), "failure": result.get("failure")}))
    return 0 if result["qualified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
