"""Cold-read a retained public AST-lowering experiment; never invoke Lean.

The native cold validator checks current source and retained native artifacts.
Its success does not independently authenticate the original proving call.
"""
from contextlib import redirect_stdout
import json
from pathlib import Path
import sys


def main():
    if len(sys.argv) != 2:
        raise ValueError("one retained public experiment directory required")
    actual = Path(sys.argv[1]).absolute()
    if actual.resolve(strict=True) != actual or not actual.is_dir():
        raise ValueError("canonical existing experiment directory required")

    from ipfs_accelerate_py.agent_supervisor.runtime.supervisor_meta_index import (
        public_replay_without_metadata,
    )
    with public_replay_without_metadata(), redirect_stdout(sys.stderr):
        from benchmarks.agent_supervisor.container_coding import (
            codebase_ir_metadata as storage,
            terminal_revision_proof_cache as revisions,
        )
        from benchmarks.agent_supervisor.container_coding.terminal_codebase_finite_service_experiment import (
            _open, _scheduler,
        )
        from benchmarks.agent_supervisor.container_coding.terminal_source_ir_lowering import (
            join_source_ir_lowering,
        )
        from ipfs_datasets_py.duckdb_control.codebase_catalog import CodebaseHead
        from ipfs_datasets_py.logic.software_contracts.codebase_integer_lowering_lean import (
            IntegerOffsetLoweringProof, validate_current_integer_offset_lowering,
        )
        from ipfs_datasets_py.logic.software_contracts.codebase_integer_profile import (
            IntegerOffsetContract,
        )
        from ipfs_datasets_py.logic.software_contracts.content import cid_for_structured

        guards = []

        def need(value, message):
            if not value:
                raise ValueError(message)

        def read(path, expected=None):
            pin, raw, guard = revisions._file(path, maximum=4_000_000)
            if expected is not None:
                need(storage._json(pin) == storage._json(expected), "published JSON pin differs")
            value = json.loads(raw)
            need(type(value) is dict, "retained JSON object required")
            guards.append(guard)
            return value

        repository = actual / "repository"
        qualified = actual / "qualified"
        result = read(qualified / "result.json")
        need(result.get("qualified") is True, "retained experiment is not qualified")
        need(result.get("output") == str(qualified), "retained output directory differs")
        need(result.get("result_cid") == cid_for_structured({
            key: value for key, value in result.items() if key != "result_cid"
        }), "retained result identity differs")
        head = CodebaseHead.from_dict(read(actual / "head.json"))
        need(storage._json(head.to_dict()) == storage._json(result["head"]), "retained owner head differs")
        policy = read(actual / "tool-policy.json")
        proof_body = read(qualified / "native-proof.json", expected=result["native_proof"])
        projection = read(qualified / "projection.json", expected=result["projection"])
        dimensions = read(qualified / "cache-dimensions.json")
        proof = IntegerOffsetLoweringProof.from_dict(proof_body)
        contract = IntegerOffsetContract.from_dict(proof_body["contract"])
        paths = ["callee.py", "caller.py"]
        snapshot, source_guard = revisions._capture(repository, paths, head.repository_id)
        need(snapshot["revision_id"] == result["revision_id"], "retained source revision differs")
        state_path = actual / "cold-resources.json"
        need(not state_path.exists() and not state_path.with_name(state_path.name + ".lock").exists(),
             "fresh cold scheduler namespace required")
        scheduler = _scheduler(state_path)
        connection, index = _open(actual)
        try:
            checked = validate_current_integer_offset_lowering(
                proof, index, repository, expected_head=head, contract=contract,
                tool_policy=policy, scheduler=scheduler, timeout_seconds=90, memory_mb=1024,
            )
            need(storage._json(checked.to_dict()) == storage._json(proof_body),
                 "native cold validation changed the retained record")
            storage.validate_codebase_ir_metadata(output=qualified / "metadata", expected=result["metadata"])
            hit = revisions.lookup_revision_candidate(
                output=qualified / "candidate-cache", expected=result["advisory_cache"],
                root=repository, paths=paths, repository_id=head.repository_id, dimensions=dimensions,
            )
            need(hit["status"] == "hit", "current advisory candidate did not replay")
            joined = join_source_ir_lowering(projection=projection, proof=proof_body)
            need(storage._json(joined) == storage._json(result["join"]), "cold data join differs")
            need(joined["caller_record_origin_verified"] is False
                 and joined["formal_proof_independently_validated"] is False,
                 "pure data join must preserve its origin limit")
            index.observe_current(repository, expected_head=head, scheduler=scheduler)
            for guard in guards:
                guard()
            source_guard.verify_originals()
        finally:
            connection.close()
        telemetry = scheduler.snapshot()
        need(telemetry["active_lease_count"] == 0 and telemetry["waiting_request_count"] == 0,
             "cold scheduler resources were not released")
        for key in ("proof_authority", "source_semantics_verified", "cpython_equivalence_proved",
                    "training_convergence_proved"):
            need(result.get(key) is False and joined.get(key) is False,
                 "cold readback cannot promote proof or runtime authority")
        safe = {
            "qualified": True, "native_result_cid": proof_body["result_cid"], "head": head.to_dict(),
            "cache_status": hit["status"], "metadata_verified": True,
            "native_cold_validation_passed": True, "new_prover_invocations": 0,
            "active_lease_count": telemetry["active_lease_count"],
            "waiting_request_count": telemetry["waiting_request_count"],
            "proof_authority": False, "source_semantics_verified": False,
            "cpython_equivalence_proved": False, "training_convergence_proved": False,
        }
        raw = json.dumps(safe, sort_keys=True, separators=(",", ":"))
        need(len(raw.encode("utf-8")) <= 4096, "safe report byte bound exceeded")
    print(raw)


if __name__ == "__main__":
    main()
