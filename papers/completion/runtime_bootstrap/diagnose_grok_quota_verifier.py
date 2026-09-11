"""Run the native isolated capacity probes and audit the real verifier outcome.

No task prompt, implementation model, live database, or fallback is dispatched.
The wrapper records where the unchanged native validator returns; it never
changes a receipt, decision, validator result, or provider command.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import secrets
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
import materialize_paper_database as M
import paper_supervisor_campaign as C


def main():
    M._native(ROOT)
    from ipfs_accelerate_py import llm_router
    from ipfs_accelerate_py.agent_supervisor.runtime import grok_cli_runner as runner
    report = {"schema": "paper-grok-native-quota-diagnosis/v1", "started_at": C.now(),
              "implementation_dispatched": False, "fallback_dispatched": False,
              "live_state_mutated": False, "probes_are_real": True}
    env = C.environment(ROOT)
    native_validate = llm_router.validate_agent_implementation_quota_evidence

    def audit_validate(**kwargs):
        observation = {"native_validator_file": native_validate.__code__.co_filename,
                       "session_id": kwargs["expected_session_id"],
                       "verifier_returncode": kwargs["verifier_returncode"]}
        home = Path(kwargs["grok_home"])
        observation["files"] = []
        for path in sorted((home / "sessions").glob("**/*")):
            if path.is_file():
                raw = path.read_bytes()
                observation["files"].append({"relative": str(path.relative_to(home)),
                    "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()})
                if path.name == "updates.jsonl":
                    updates = []
                    for line in raw.decode(errors="replace").splitlines():
                        try:
                            update = json.loads(line)
                            updates.append({"type": update.get("type"), "keys": sorted(update)})
                        except (ValueError, TypeError):
                            updates.append({"invalid_json": True})
                    observation["update_shapes"] = updates
        prior_trace = sys.gettrace()
        def trace(frame, event, arg):
            if frame.f_code is native_validate.__code__:
                if event == "return":
                    observation["validator_return_line"] = frame.f_lineno
                    observation["validator_returned_none"] = arg is None
                elif event == "exception":
                    observation.setdefault("exceptions", []).append({
                        "line": frame.f_lineno, "type": arg[0].__name__, "message": str(arg[1])})
                return trace
            return None
        try:
            sys.settrace(trace)
            value = native_validate(**kwargs)
        finally:
            sys.settrace(prior_trace)
        report["verifier_observation"] = observation
        return value

    llm_router.validate_agent_implementation_quota_evidence = audit_validate
    try:
        nonce = secrets.token_hex(32)
        code, receipt, overflow = runner._run_typed_grok_preflight(
            grok_bin=str(Path.home() / ".local/bin/grok"), base_env=env, nonce=nonce)
        report.update(preflight_returncode=code, preflight_receipt=receipt, preflight_overflow=overflow)
        if code != 0 and receipt:
            value = runner._independently_verify_grok_quota(
                grok_bin=str(Path.home() / ".local/bin/grok"), base_env=env,
                failure_receipt=receipt)
            report["independent_verifier_return_type"] = type(value).__name__
            report["independent_verifier_confirmed"] = bool(value)
            if value:
                route = llm_router.resolve_agent_implementation_route(
                    primary_provider_id="grok_cli", primary_model_id="grok-4.6",
                    fallback_provider_id="codex", fallback_model_id="gpt-5.6-terra",
                    fallback_trigger="primary_quota_exhausted", fallback_reasoning_effort="high")
                decision = llm_router.decide_agent_implementation_fallback(
                    route, repo_root=ROOT, failure_receipt=receipt,
                    expected_nonce=nonce, expected_model="grok-4.6",
                    expected_probe_returncode=code, independent_quota_evidence=value,
                    now_ms=int(time.time() * 1000), max_age_ms=60000)
                report["quota_high_decision"] = {
                    "authorized": decision.authorized, "reason_code": decision.reason_code,
                    "verifier_status": decision.verifier_status,
                    "fallback_model": decision.fallback_model_id,
                    "fallback_reasoning_effort": decision.fallback_reasoning_effort,
                    "evidence_id": value.evidence_id}
        else:
            report["independent_verifier_skipped"] = "preflight did not produce a failure candidate"
    finally:
        llm_router.validate_agent_implementation_quota_evidence = native_validate
        report["finished_at"] = C.now()
        path = Path(__file__).with_name(sys.argv[1] if len(sys.argv) > 1 else "grok_native_quota_diagnosis.json")
        path.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
    print(json.dumps(report, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
