"""Use actual deployment/worker APIs in one fresh public fixture container."""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from pathlib import Path
import re
import shlex
from types import SimpleNamespace
import time


async def shell(argv, *, timeout=600):
    process = await asyncio.create_subprocess_exec(*argv, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout)
    except BaseException:
        process.kill()
        await process.wait()
        raise
    return SimpleNamespace(return_code=process.returncode, stdout=stdout.decode(), stderr=stderr.decode())


class LocalDockerFixture:
    default_user = "root"
    def __init__(self, name):
        assert re.fullmatch(r"ipfs-nomination-audit-qualification-20261012-[0-9]{2}", name)
        self.name = name
    async def exec(self, *, command, cwd="/app", user=None, env=None, timeout_sec=600):
        argv = ["docker", "exec", "--user", user or self.default_user, "--workdir", cwd]
        for name, value in (env or {}).items():
            argv += ["--env", name + "=" + value]
        return await shell(argv + [self.name, "/bin/sh", "-c", command], timeout=timeout_sec)
    async def upload_file(self, source, destination):
        result = await shell(["docker", "cp", str(source), self.name + ":" + destination])
        assert result.return_code == 0, result.stderr


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


async def main(args):
    from benchmarks.agent_supervisor.container_coding.terminal_deployment import deploy_supervisor, runtime_environment, PYTHON, ROOT, INPUT_SNAPSHOT
    from benchmarks.agent_supervisor.container_coding.container_worker_deployment import install_worker_boundary, qualify_worker_boundary
    output = args.output.absolute()
    output.mkdir(exist_ok=False)
    started = time.monotonic()
    environment = LocalDockerFixture(args.container)
    manifest = json.loads((args.archive / "manifest.json").read_bytes())
    receipt = {"schema": "reviewed-source-installed-public-audit-qualification@1", "qualified": False,
        "controller_sha256": digest(Path(__file__).resolve()), "archive_sha256": manifest["archive_sha256"],
        "context_probe_sha256": digest(args.context_probe), "audit_probe_sha256": digest(args.audit_probe),
        "runtime_manifest_sha256": digest(args.archive / "manifest.json"),
        "provider_calls": 0, "training_steps": 0, "prover_invocations": 0,
        "target_module_imports": 0, "official_task_verifier_invocations": 0,
        "scope": "Fresh Python container, public Bottle and literal Terminal Bench instruction, genuine production deployment/signed admission/context/native prompt and historical complete-model-input audit. Not an original Harbor task image, benchmark execution or full task satisfaction.",
        "real_auth_transferred": False}
    async def execute(label, command, *, user="root", env=None, timeout=600, cwd="/app"):
        result = await environment.exec(command=command, cwd=cwd, user=user, env=env, timeout_sec=timeout)
        (output / (label + ".stdout")).write_text(result.stdout)
        (output / (label + ".stderr")).write_text(result.stderr)
        assert result.return_code == 0, (label, result.return_code, result.stderr[:1024])
        print(json.dumps({"stage": label, "seconds": round(time.monotonic() - started, 3)}), flush=True)
        return result
    try:
        await execute("create-original-public-fixture", "install -d -m 0755 /app", cwd="/")
        await environment.upload_file(args.source, "/app/bottle.py")
        await execute("record-original-public-baseline", "git init -q && git add bottle.py && git -c user.name='Public fixture' -c user.email=fixture@localhost commit -qm 'Original public Bottle fixture'")
        deployed = await deploy_supervisor(environment, archive_dir=args.archive, output=output / "deployment", auth_json=None, install_codex=True)
        assert deployed["qualified"] and deployed["imports"]["python"] == manifest["runtime_python_version"]
        # The existing worker API needs an auth file to copy; use only our own empty fixture.
        synthetic_auth = output / "synthetic-auth.json"
        synthetic_auth.write_text("{}\n")
        await environment.upload_file(synthetic_auth, ROOT + "/codex-auth/auth.json")
        await execute("protect-synthetic-auth", "chown 1000:1000 " + ROOT + "/codex-auth/auth.json && chmod 0600 " + ROOT + "/codex-auth/auth.json")
        installed = await install_worker_boundary(environment, container_name=args.container,
            output=output / "worker-boundary/installation")
        qualified = await qualify_worker_boundary(environment, output=output / "worker-boundary/qualification")
        boundary = {**installed, "qualified": qualified["qualified"], "qualification": qualified}
        assert boundary["qualified"]
        disconnected = await shell(["docker", "network", "disconnect", "bridge", args.container])
        assert disconnected.return_code == 0, disconnected.stderr
        receipt["external_network_detached_before_context_and_audit"] = True
        for source, name in ((args.context_probe, "qualify-admitted-public-context.py"),
                (args.audit_probe, "qualify-catalog-audit.py"), (args.source, "public-bottle.py"),
                (args.instruction, "public-instruction.txt"), (args.archive / "manifest.json", "qualification-runtime-manifest.json")):
            await environment.upload_file(source, ROOT + "/" + name)
            await execute("protect-" + name, "chown root:root " + shlex.quote(ROOT + "/" + name) + " && chmod 0444 " + shlex.quote(ROOT + "/" + name))
        context_output = "/app/.nomination-admitted-qualification"
        runtime_env = runtime_environment()
        context = await execute("actual-signed-context", shlex.join([PYTHON, "-P", ROOT + "/qualify-admitted-public-context.py",
            "--output", context_output, "--source", ROOT + "/public-bottle.py", "--instruction", ROOT + "/public-instruction.txt"]),
            user="supervisor", env=runtime_env, timeout=600)
        context_receipt = await execute("export-public-context-receipt", shlex.join([PYTHON, "-I", "-c",
            "from pathlib import Path; print(Path(" + repr(context_output + "/qualification.json") + ").read_text())"]), user="supervisor", env=runtime_env)
        context_data = json.loads(context_receipt.stdout)
        assert context_data["qualified"] and not context_data["admission_or_hydration_stubs"]
        audit_output = "/app/.nomination-model-audit-qualification"
        await execute("actual-historical-model-audit", shlex.join([PYTHON, "-P", ROOT + "/qualify-catalog-audit.py",
            "--fixture", context_output, "--output", audit_output,
            "--runtime-manifest", ROOT + "/qualification-runtime-manifest.json",
            "--runtime-manifest-sha256", receipt["runtime_manifest_sha256"]]), user="supervisor", env=runtime_env, timeout=600)
        audit_receipt = await execute("export-public-audit-receipt", shlex.join([PYTHON, "-I", "-c",
            "from pathlib import Path; print(Path(" + repr(audit_output + "/qualification.json") + ").read_text())"]), user="supervisor", env=runtime_env)
        audit_data = json.loads(audit_receipt.stdout)
        assert audit_data["qualified"] and len(audit_data["observations"]) == 12 and len(audit_data["negatives"]) == 4
        provenance = audit_data["imported_producer_provenance"]
        assert provenance["installed_archive_join_performed"] is True
        assert provenance["runtime_manifest_sha256"] == receipt["runtime_manifest_sha256"]
        assert provenance["archive_sha256"] == manifest["archive_sha256"]
        assert len(provenance["actual_imported_producers"]) == 10
        fixtures = output / "public-model-input-fixtures"
        fixtures.mkdir()
        for mode in ("expanded", "compact_v2", "legacy_v1", "identifiers"):
            for suffix in ("-receipt.json", "-model-input.txt"):
                exported = await shell(["docker", "cp", args.container + ":" + audit_output + "/" + mode + suffix,
                    str(fixtures / (mode + suffix))])
                assert exported.return_code == 0, exported.stderr
        after = json.loads((await execute("preserve-original-tracked-source", "python3 -I -c " + shlex.quote(INPUT_SNAPSHOT), user="supervisor", env=runtime_env)).stdout)
        assert after["files"] == deployed["original_inputs"]["files"]
        assert after["head"] == deployed["original_inputs"]["head"]
        assert after["report_exists"] == deployed["original_inputs"]["report_exists"]
        assert digest(args.context_probe) == receipt["context_probe_sha256"]
        assert digest(args.audit_probe) == receipt["audit_probe_sha256"]
        receipt.update(qualified=True, deployment_qualified=True, worker_boundary_qualified=True,
            context=context_data, audit=audit_data, original_tracked_source_and_HEAD_preserved=True,
            original_Harbor_task_image_used=False, benchmark_reward_measured=False,
            full_driver_prepare_review_resume_qualified=False,
            provider_total_session_token_savings_established=False,
            source_equivalence_or_model_convergence_proved=False)
    except Exception as exc:
        receipt["failure"] = {"type": type(exc).__name__, "message": str(exc)[:2048]}
        raise
    finally:
        cleanup = await shell(["docker", "rm", "--force", args.container], timeout=60)
        receipt["fresh_qualification_container_removed"] = cleanup.return_code == 0
        receipt["seconds"] = time.monotonic() - started
        (output / "qualification.json").write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for name in ("archive", "output", "context-probe", "audit-probe", "source", "instruction"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--container", required=True)
    asyncio.run(main(parser.parse_args()))
