#!/usr/bin/env python3
"""Validate retained NS-026 production-provider evidence. Does not re-dispatch a paid call."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path.cwd()
PAPER = ROOT / "papers/completion/neurosymbolic_supervision"
EXP = PAPER / "experiments"
PROTO = PAPER / "protocol"
QUAL = PAPER / "qualification" / "production_provider"
AUDIT = PAPER / "audit"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def require(cond, message):
    if not cond:
        raise AssertionError(message)


def validate_retained_legacy_draft() -> int:
    for path in (
        EXP / "run_comparison.py",
        EXP / "score_runs.py",
        EXP / "production_gateway.py",
        EXP / "production_profile.json",
        PROTO / "development_provider_amendment.json",
        EXP / "README.md",
        QUAL / "qualification_report.json",
        AUDIT / "production_readiness.json",
    ):
        require(path.is_file(), f"missing {path}")
        if path.suffix == ".py":
            compile(path.read_bytes(), str(path), "exec")
    compile((QUAL / "run_qualification.py").read_bytes(), str(QUAL / "run_qualification.py"), "exec")
    compile((QUAL / "validate_production_provider.py").read_bytes(), str(QUAL / "validate_production_provider.py"), "exec")

    amendment = load(PROTO / "development_provider_amendment.json")
    profile = load(EXP / "production_profile.json")
    manifest = load(PROTO / "experiment_manifest.json")
    require(amendment["schema"] == "paper-ns-development-provider-amendment/v1", "amendment schema")
    require(amendment["overwrites_original_protocol"] is False, "must not overwrite ns-core-v1")
    require(amendment["ns004_protocol_bundle_sha256"] == manifest["protocol_bundle_sha256"], "amendment protocol pin")
    require(amendment["permitted_development_profile"]["admitted_production"] is False, "dev cannot admit production")
    require(amendment["permitted_development_profile"]["requested_model"] == "grok-4.6", "grok primary")
    require(amendment["permitted_development_profile"]["transport"].startswith("https://api.x.ai/"), "https transport")
    require(profile["ns004_proposed_available"] is False, "terra high still unavailable")
    require(profile["production_admission"]["admitted"] is False, "production not admitted")
    require("usage_reset" in json.dumps(amendment["deviation_from_preserved_ns004"]), "usage reset disclosure")

    readme = (EXP / "README.md").read_text(encoding="utf-8")
    for token in ("one-task", "one-arm", "paired", "score_runs.py", "--admitted-provider", "production_gateway.py", "NS-016"):
        require(token in readme, f"README missing {token}")

    report = load(QUAL / "qualification_report.json")
    require(report.get("ok") is True, f"qualification report not ok: {json.dumps(report.get('checks'), indent=2)[:2000]}")
    by = {row["name"]: row for row in report["checks"]}
    require(by["actual_development_provider_not_stub"]["ok"] is True, "actual provider missing")
    require(by["actual_development_provider_not_stub"]["served_model"] != "ns-006-deterministic-dev-stub", "stub labeled as actual")
    require(by["actual_development_provider_not_stub"]["served_provider"] == "xai", "served provider")
    require(by["actual_development_provider_not_stub"]["served_model"], "served model")
    require(by["independent_score_after_seal"]["ok"] is True, "independent score")
    require(by["resume_no_duplicate_dispatch"]["ok"] is True, "duplicate dispatch")
    require(by["pinned_pre_fix_proposal_export"]["ok"] is True, "historical materialization")
    require(by["boundary_canary_rejects_scorer_payload"]["ok"] is True, "canary")
    require(by["nonempty_unchanged_baseline"]["ok"] is True, "baseline")
    require(by["historical_scorer_no_blanket_refusal"]["ok"] is True, "historical scorer")
    require(by["stub_interrupt_no_duplicate_dispatch"]["ok"] is True, "interrupt")
    require(by["production_unknown_or_unavailable_not_solved"]["ok"] is True, "unknown/unavailable")

    attempt = load(QUAL / "development_invocation" / "attempt.json")
    require(attempt["schema"] == "paper-ns-runner-attempt/v1", "attempt schema")
    require(attempt["path_class"] == "development", "path_class")
    require(attempt["provider_receipt"]["simulated"] is False, "actual call is not simulated")
    require(attempt["provider_receipt"]["admitted_production"] is False, "dev production")
    require(attempt["provider_receipt"]["dispatched"] is True, "dispatched")
    require(attempt["provider_receipt"]["dispatch_confirmed"] is True, "confirmed")
    require(attempt["bindings"]["source_preimage_id"], "source preimage")
    require(attempt["measurement"]["measurements"]["active_elapsed_seconds"]["status"] == "actual", "timing")
    require(attempt["measurement"]["measurements"]["input_tokens"]["status"] in {"actual", "unavailable"}, "tokens")
    stages = [row["stage"] for row in attempt["measurement"]["stages"]]
    require("provider" in stages, "provider stage")
    require("cold_scoring" in stages or attempt["measurement"]["terminal_state"] in {"abstained", "unavailable", "unsolved", "solved"}, "stage presence")

    scan = load(QUAL / "historical" / "proposal_export_scan.json")
    require(scan["files"] == ["xmltodict.py"], scan["files"])
    require(scan["git_present"] is False, "git leaked")
    require(scan["xmltodict_sha256"] == scan["expected_xmltodict_sha256"], "pre-fix pin")
    require(scan["archive_sha256"] == scan["expected_archive_sha256"], "archive pin")

    readiness = load(AUDIT / "production_readiness.json")
    require(readiness["production_admitted"] is False, "readiness production")
    require(readiness["ns016_freeze_ready"]["provider_source_pin"], "provider pin")
    require(readiness["ns016_freeze_ready"]["scorer_source_pin"], "scorer pin")
    require(readiness["ns016_freeze_ready"]["run_instructions"], "run instructions")

    source = (EXP / "run_comparison.py").read_text(encoding="utf-8")
    require("git show" not in source or "pinned upstream" in source.lower() or "materialize_pinned_snapshot" in source, "caller git still used")
    require("load_gateway" in source and "admitted-provider" in source, "gateway not wired")
    scorer = (EXP / "score_runs.py").read_text(encoding="utf-8")
    require("Live hidden FAIL_TO_PASS payloads are scorer-principal reconstruction recipes and are not materialized in this NS-006 environment" not in scorer, "blanket refusal remains")
    require("ns-026-independent-historical-scorer" in scorer, "scorer id")
    print(json.dumps({"ok": True, "amendment_id": amendment["amendment_id"], "served_model": attempt["provider_receipt"]["served_model"]}, indent=2))
    return 0


def main() -> int:
    import importlib.util
    spec = importlib.util.spec_from_file_location("ns_host_validation_gateway", EXP / "production_gateway.py")
    gateway = importlib.util.module_from_spec(spec); spec.loader.exec_module(gateway)
    source_manifest = load(QUAL / "host_service/source_manifest.json")
    for relative, expected in source_manifest["files"].items():
        require(sha(QUAL / "host_service" / relative) == expected, "durable service source changed: " + relative)
    for relative, expected in source_manifest["qualifications"].items():
        require(sha(QUAL / "host_service" / relative) == expected, "retained source qualification changed: " + relative)
    attempts = [load(QUAL / "historical_development" / name) for name in ("attempt.json", "resume.json", "rescored.json")]
    first = attempts[0]; previous = first["provider_receipt"]["host_verified"]
    verified = gateway.verify_host_response(ROOT, previous["binding"])
    require(verified == previous, "current signed host evidence differs")
    body = verified["receipt"]; oracle = gateway.host_oracle(verified)
    require(body["inert_qualification"] is False and body["provider_invoked"] is True and body["served_profile_admitted"] is True and body["historical_development_unit_admitted"] is True, "actual admitted historical development call absent")
    require(body["provider_stream_metadata"]["served_models"] == ["grok-4.6"], "served model differs")
    require(body["operator_review_kind"] == "ai_operator" and body["automatic_adversarial_scorer_integrity_qualified"] is False and body["production_final_admitted"] is False, "specific candidate trust limit lost")
    require(body["new_provider_calls_during_score"] == 0 and body["provider_termination"]["termination_proven"] is True, "proposal/score phase boundary incomplete")
    require(oracle["cold_full_validation"] is True, "nonempty independent cold score incomplete")
    for attempt in attempts:
        require(attempt["provider_receipt"]["host_verified"] == verified, "attempts do not reuse the same exact signed result")
        require(attempt["measurement"]["record_kind"] == "development", "final outcome improperly admitted")
        require(attempt["measurement"]["identity"]["source_preimage_id"] == body["source_sha256"] and attempt["bindings"]["source_preimage_id"] == body["source_sha256"], "source binding differs")
        require(attempt["runner"]["candidate"]["host_candidate_sha256"] == body["candidate_sha256"], "candidate binding differs")
        require(attempt["provider_receipt"]["admitted_production"] is False, "development became native/final production admission")
        for key in ("host_cpu_seconds", "peak_aggregate_memory_bytes", "human_wait_seconds"):
            require(attempt["measurement"]["measurements"][key]["status"] == "unavailable", "client counter incorrectly used as remote aggregate")
    require(attempts[1]["runner"]["interruption"]["duplicate_dispatch_prevented"] is True, "same-grant resume unverified")
    replay = attempts[2]["runner"]["host_rescore"]
    require(replay["new_provider_calls"] == replay["new_scorer_calls"] == 0 and replay["hidden_oracle_loaded"] is False, "rescore must only reverify signed evidence")
    require(oracle["status"] in ("passed", "failed"), "actual test outcome absent")
    print(json.dumps({"ok": True, "scope": "specific_reviewed_historical_development_candidate", "historical_outcome": oracle["status"], "grant_sha256": body["grant_sha256"], "signed_response_sha256": verified["response_sha256"], "new_provider_calls": 0, "new_scorer_calls": 0, "pilot_final_admitted": False, "automatic_adversarial_scorer_integrity_qualified": False}, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"validate_production_provider: {exc}", file=sys.stderr)
        raise SystemExit(1)
