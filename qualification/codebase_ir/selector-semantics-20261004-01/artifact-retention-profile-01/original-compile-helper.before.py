def _compile_lean(*, executable, filename, source, output, expected_success):
    from ipfs_datasets_py.logic.backends.process import BoundedToolRunner, ToolRunRequest, ToolRunLimits

    pin = _write(output / filename, source)
    object_file = str(PurePosixPath(filename).with_suffix(".olean"))
    command = ((str(executable), "-o", object_file, filename) if expected_success
               else (str(executable), filename))
    run = BoundedToolRunner().run(ToolRunRequest(argv=command,
        input_files={filename: source}, output_paths=(object_file,) if expected_success else (),
        limits=ToolRunLimits(timeout_seconds=20,
            cpu_seconds=20, max_input_bytes=262144, max_output_bytes=65536,
            max_workspace_bytes=16 * 1024 * 1024)))
    passed = run.ok and not run.output_truncated and not run.workspace_limit_exceeded
    expected_failure = (run.returncode is not None and run.returncode != 0
        and not any((run.timed_out, run.cancelled, run.unavailable, run.resource_exhausted,
                     run.output_truncated, run.workspace_limit_exceeded))
        and "Tactic `decide` proved that the proposition" in run.stdout and "is false" in run.stdout)
    compiled_artifacts = []
    for name, raw in run.output_files.items():
        with (output / name).open("xb") as stream:
            stream.write(raw)
        compiled_artifacts.append({"path": str(output / name), "sha256": _sha(raw), "bytes": len(raw)})
    if expected_success and not compiled_artifacts:
        passed = False
    return {"schema": "terminal-codebase-lean-check@1", "file": filename, "artifact": pin,
        "status": "passed" if passed else "rejected" if expected_failure else "inconclusive",
        "expected_success": expected_success,
        "matches_expectation": passed if expected_success else expected_failure,
        "compiled_artifacts": compiled_artifacts,
        "backend_executed": True, "executable": str(executable),
        "executable_sha256": _sha(executable.read_bytes()), "command": list(run.command),
        "returncode": run.returncode, "stdout": run.stdout, "stderr": run.stderr,
        "timed_out": run.timed_out, "output_truncated": run.output_truncated,
        "workspace_limit_exceeded": run.workspace_limit_exceeded,
        "resource_exhausted": run.resource_exhausted, "workspace_cleaned": run.workspace_cleaned,
        "elapsed_seconds": run.elapsed_seconds,
        "proof_scope": "kernel_checked_generated_model_statement_only", **AUTHORITY}
