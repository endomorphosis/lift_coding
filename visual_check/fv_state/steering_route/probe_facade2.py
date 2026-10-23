"""Empirical probe 2: open the production Supervisor from the ipfs_accelerate
repository root (which carries the activated scheduler config), create a run,
steer it on the same instance, then try a fresh instance for cross-session
behavior. Prints JSON evidence."""
import importlib.util  # noqa: F401
import json
import os
import sys

ACCEL = "/home/hatch/workspace/lift_coding/external/ipfs_accelerate"
os.chdir(ACCEL)

from ipfs_accelerate_py.agent_supervisor.entrypoints.facade import Supervisor


def main() -> None:
    out: dict = {}
    sup = Supervisor.open(repository=ACCEL)
    out["composition_cid"] = sup.composition_cid
    out["manifest_activation"] = sup.composition_manifest.activation_task_id
    run = sup.run(
        "Steering-route verification: keep the supervisor verification backlog moving."
    )
    out["run"] = {
        "run_id": run.run_id,
        "state": run.state,
        "health": run.health,
        "event_cursor": run.event_cursor,
        "run_revision": run.run_revision,
        "identities": dict(run.identities),
        "effect_receipt_cids": list(run.effect_receipt_cids),
    }
    obs = sup.steer(
        run.run_id,
        "Prioritize the steering verification task; keep all other scope unchanged.",
    )
    out["steer_same_instance"] = obs.to_dict()
    out["status_after_steer"] = sup.status(run.run_id).to_dict()
    # Fresh instance: does the run survive?
    sup2 = Supervisor.open(repository=ACCEL)
    try:
        obs2 = sup2.status(run.run_id)
        out["fresh_instance_status"] = obs2.to_dict()
    except Exception as exc:  # noqa: BLE001
        out["fresh_instance_status"] = {
            "error": type(exc).__name__,
            "message": str(exc),
            "candidates": list(getattr(exc, "candidates", ())),
        }
    try:
        obs3 = sup2.steer(run.run_id, "cross-instance steer attempt")
        out["fresh_instance_steer"] = obs3.to_dict()
    except Exception as exc:  # noqa: BLE001
        out["fresh_instance_steer"] = {
            "error": type(exc).__name__,
            "message": str(exc),
            "candidates": list(getattr(exc, "candidates", ())),
        }
    print(json.dumps(out, indent=2, default=str))


if __name__ == "__main__":
    main()
