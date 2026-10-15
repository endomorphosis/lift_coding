"""Cold-read retained public caller composition; never invoke a checker.

This validates native source/artifact consistency. It does not authenticate
the origin of the retained caller process record or grant runtime authority.
"""
from contextlib import redirect_stdout
import json
import os
from pathlib import Path
import stat
import sys


def need(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    need(len(sys.argv) == 2, "one retained public call experiment directory required")
    actual = Path(sys.argv[1]).absolute()
    need(actual.resolve(strict=True) == actual and actual.is_dir(),
         "canonical existing experiment directory required")
    directory_fields = ("st_dev", "st_ino", "st_mode", "st_uid", "st_gid")

    def directory(path):
        value = path.lstat()
        need(stat.S_ISDIR(value.st_mode) and value.st_uid == os.geteuid()
             and not stat.S_IMODE(value.st_mode) & 0o022,
             "protected owner experiment directory required")
        return tuple(getattr(value, field) for field in directory_fields)

    actual_identity = directory(actual)
    from ipfs_accelerate_py.agent_supervisor.runtime.supervisor_meta_index import (
        public_replay_without_metadata,
    )
    with public_replay_without_metadata(), redirect_stdout(sys.stderr):
        from benchmarks.agent_supervisor.container_coding import (
            codebase_ir_metadata as storage,
            terminal_call_ir_composition as composition,
            terminal_revision_proof_cache as revisions,
        )
        from benchmarks.agent_supervisor.container_coding.terminal_codebase_finite_service_experiment import (
            _open, _scheduler,
        )
        from ipfs_datasets_py.duckdb_control.codebase_catalog import CodebaseHead

        guards = []

        def read(path):
            _, raw, guard = revisions._file(path, maximum=4_000_000)
            value = json.loads(raw.decode("utf-8"))
            need(type(value) is dict, "bounded retained JSON object required")
            storage._json(value)  # Reject non-finite or non-UTF8 JSON values.
            guards.append(guard)
            return value

        qualified = actual / "qualified"
        result = read(qualified / "result.json")
        need(result.get("qualified") is True and result.get("output") == str(qualified),
             "retained qualified caller output differs")
        head_body = read(actual / "head.json")
        head = CodebaseHead.from_dict(head_body)
        need(storage._json(head.to_dict()) == storage._json(head_body)
             == storage._json(result["head"]), "retained typed native head differs")
        policy = read(actual / "tool-policy.json")
        need(type(result.get("paths")) is list and len(result["paths"]) == 3
             and len(set(result["paths"])) == 3, "complete authored three-source scope required")
        repository = actual / "repository"
        need(repository.resolve(strict=True) == repository and repository.is_dir(),
             "canonical retained source repository required")
        # Refuse creation of an absent native owner. No database or CAS body is
        # traversed here; the existing native owner performs its own readback.
        database, cas = actual / "codebase.duckdb", actual / "cas"
        need(database.resolve(strict=True) == database and stat.S_ISREG(database.lstat().st_mode),
             "existing regular native database required")
        need(cas.resolve(strict=True) == cas and stat.S_ISDIR(cas.lstat().st_mode),
             "existing native content owner required")
        state_path = actual / "cold-resources.json"
        for path in (state_path, state_path.with_name(state_path.name + ".lock")):
            need(not path.exists() and not path.is_symlink(), "fresh cold scheduler namespace required")
        need(directory(actual) == actual_identity, "experiment directory custody changed")
        scheduler = _scheduler(state_path)
        connection, index = _open(actual)
        try:
            checked = composition.validate_current_call_composition(
                expected=result, index=index, repository=repository, expected_head=head,
                tool_policy=policy, scheduler=scheduler,
            )
            need(checked.get("data_validated") is True and checked.get("cache_status") == "hit"
                 and checked.get("native_callee_cold_validation_passed") is True
                 and checked.get("caller_record_origin_verified") is False
                 and checked.get("checker_reinvoked") is False,
                 "cold caller data or origin-limit verdict differs")
            need(storage._json(checked["head"]) == storage._json(head.to_dict()),
                 "cold caller owner head differs")
            need(all(result.get(key) is False and checked.get(key) is False
                     for key in composition.AUTHORITY), "cold readback cannot promote authority")
            index.observe_current(repository, expected_head=head, scheduler=scheduler)
            for guard in guards:
                guard()
            need(directory(actual) == actual_identity, "experiment directory custody changed")
        finally:
            connection.close()
        telemetry = scheduler.snapshot()
        need(telemetry["active_lease_count"] == 0 and telemetry["waiting_request_count"] == 0,
             "cold scheduler resources were not released")
        safe = {"schema": "terminal-call-ir-cold-public-readback@1", "data_validated": True,
            "head": head.to_dict(), "cache_status": "hit", "native_callee_cold_validation_passed": True,
            "caller_record_origin_verified": False, "checker_reinvoked": False,
            "active_lease_count": 0, "waiting_request_count": 0, "new_prover_invocations": 0,
            "proof_authority": False, "source_semantics_verified": False,
            "python_import_resolution_proved": False, "training_convergence_proved": False}
        raw = storage._json(safe)
        need(len(raw) <= 4096, "safe cold report byte bound exceeded")
        for guard in guards:
            guard()
        need(directory(actual) == actual_identity, "experiment directory custody changed")
    print(raw.decode("utf-8"))


if __name__ == "__main__":
    main()
