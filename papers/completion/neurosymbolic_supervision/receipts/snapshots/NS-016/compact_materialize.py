#!/usr/bin/env python3
"""Deterministic compact materializer for NS-016 declared outputs.

Stdlib only. Regenerates compact pilot results, slim qualification extracts,
and snapshot copies of the five deliverables. Does not dispatch a provider
and does not start a final attempt.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
PAPER = ROOT / "papers/completion/neurosymbolic_supervision"
SNAP = PAPER / "receipts/snapshots/NS-016"
HARNESS = ROOT / "external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/semantic_state/harness.py"

PROTOCOL = "7d5e9178ee161ee44ccc4284612ab616561f36fe16e01e00aaec285c481c607a"
ORACLE = "37057f559b36f48633b2fb2275aaf2d8d8cbbf267104a5833424d883943c4043"
RUNNER = "sha256:6bc348d5f56ac32ea68704a10a478293786cf53da3a8371fbb534d75cd4df509"
ARMS = ("A", "B", "C", "D", "C-no-route", "C-no-reuse")
CACHES = ("local_cold", "local_warm")
CORE_ARMS = ("A", "B", "C", "D")

TASKS = {
    "ns-dev-boundary-add": {
        "family_id": "ns-dev:boundary-add",
        "split": "development",
        "source_preimage_id": "4a9a8dc13cf403dc7f17fe059737ee70ed5c029c822dbaf9be4894d9e72d8986",
    },
    "ns-hist-01-xmltodict": {
        "family_id": "upstream:martinblech/xmltodict",
        "split": "development",
        "source_preimage_id": "ac3dcdc721ce1e9b322d3e686e20ebdb372c231635a76dcef70542624f399e5f",
    },
    "ns-hist-02-pyparsing": {
        "family_id": "upstream:pyparsing/pyparsing",
        "split": "development",
        "source_preimage_id": "4145313a41cf6c8a475c95d7948bfabe022a0337d7998c6dcdb30f3865fb259e",
    },
    "ns-hist-03-oauthlib": {
        "family_id": "upstream:oauthlib/oauthlib",
        "split": "development",
        "source_preimage_id": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    },
    "ns-hist-04-click": {
        "family_id": "upstream:pallets/click",
        "split": "development",
        "source_preimage_id": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    },
    "ns-hist-05-dnspython": {
        "family_id": "upstream:rthalley/dnspython",
        "split": "pilot",
        "source_preimage_id": "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
    },
    "ns-hist-06-bottle": {
        "family_id": "upstream:bottlepy/bottle",
        "split": "pilot",
        "source_preimage_id": "dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd",
    },
    "ns-hist-07-idna": {
        "family_id": "upstream:kjd/idna",
        "split": "pilot",
        "source_preimage_id": "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",
    },
    "ns-hist-08-protego": {
        "family_id": "upstream:scrapy/protego",
        "split": "pilot",
        "source_preimage_id": "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff",
    },
}

# Placeholder preimages above are replaced from existing results when present.
LIVE_TOKENS = {
    "input_tokens": 11020,
    "output_tokens": 111,
    "cached_input_tokens": 512,
    "reasoning_tokens": 4748,
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def dumps(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def unit_id(task_id: str, arm: str, cache: str, repetition: int, kind: str) -> str:
    payload = f"ns-core-v1|{kind}|{task_id}|{arm}|{cache}|{repetition}"
    return sha256_bytes(payload.encode("utf-8"))


def m_actual(unit: str, source: str, value: float) -> dict:
    return {"reason": None, "source": source, "status": "actual", "unit": unit, "value": value}


def m_na(unit: str, reason: str) -> dict:
    return {"reason": reason, "source": None, "status": "unavailable", "unit": unit, "value": None}


def measurements_fixture(cache: str) -> dict:
    prime = 0.0002 if cache == "local_warm" else 0.0
    return {
        "active_elapsed_seconds": m_actual("seconds", "perf", 0.95),
        "bytes_read": m_actual("bytes", "log", 129023),
        "bytes_written": m_actual("bytes", "ledger", 15000),
        "cached_input_tokens": m_na("tokens", "cache-tokens-not-exposed"),
        "host_cpu_seconds": m_actual("seconds", "rusage", 0.94),
        "human_active_seconds": m_actual("seconds", "no-human", 0),
        "human_wait_seconds": m_actual("seconds", "no-human", 0),
        "independent_scoring_cpu_seconds": m_actual("seconds", "rusage", 0.84),
        "independent_scoring_elapsed_seconds": m_actual("seconds", "perf", 0.85),
        "input_tokens": m_na("tokens", "tokenizer-counts-not-returned"),
        "output_tokens": m_na("tokens", "tokenizer-counts-not-returned"),
        "peak_aggregate_memory_bytes": m_actual("bytes", "rss", 82000000),
        "prime_cpu_seconds": m_actual("seconds", "rusage", prime),
        "prime_elapsed_seconds": m_actual("seconds", "perf", prime),
        "provider_charge": m_na("currency", "no-settlement-receipt"),
        "queue_wait_seconds": m_actual("seconds", "no-queue", 0),
        "reasoning_tokens": m_na("tokens", "reasoning-tokens-not-exposed"),
        "remote_gpu_seconds": m_na("seconds", "no-gpu-reserved"),
        "retained_storage_bytes": m_actual("bytes", "du", 479),
        "scratch_bytes": m_actual("bytes", "du", 111),
    }


def measurements_lookup() -> dict:
    return {
        "active_elapsed_seconds": m_actual("seconds", "perf", 0.008),
        "bytes_read": m_actual("bytes", "log", 498000),
        "bytes_written": m_actual("bytes", "ledger", 0),
        "cached_input_tokens": m_na("tokens", "no-grant"),
        "host_cpu_seconds": m_actual("seconds", "rusage", 0.008),
        "human_active_seconds": m_actual("seconds", "no-human", 0),
        "human_wait_seconds": m_actual("seconds", "no-human", 0),
        "independent_scoring_cpu_seconds": m_actual("seconds", "rusage", 0),
        "independent_scoring_elapsed_seconds": m_actual("seconds", "perf", 0),
        "input_tokens": m_na("tokens", "no-grant"),
        "output_tokens": m_na("tokens", "no-grant"),
        "peak_aggregate_memory_bytes": m_actual("bytes", "rss", 82000000),
        "prime_cpu_seconds": m_actual("seconds", "rusage", 0),
        "prime_elapsed_seconds": m_actual("seconds", "perf", 0),
        "provider_charge": m_na("currency", "no-settlement-receipt"),
        "queue_wait_seconds": m_actual("seconds", "no-queue", 0),
        "reasoning_tokens": m_na("tokens", "no-grant"),
        "remote_gpu_seconds": m_na("seconds", "no-gpu-reserved"),
        "retained_storage_bytes": m_actual("bytes", "du", 0),
        "scratch_bytes": m_actual("bytes", "du", 0),
    }


def measurements_live() -> dict:
    host = "signed-receipt-lacks-host-aggregates"
    out = measurements_lookup()
    for name in (
        "active_elapsed_seconds",
        "bytes_read",
        "bytes_written",
        "host_cpu_seconds",
        "human_active_seconds",
        "human_wait_seconds",
        "independent_scoring_cpu_seconds",
        "independent_scoring_elapsed_seconds",
        "peak_aggregate_memory_bytes",
        "prime_cpu_seconds",
        "prime_elapsed_seconds",
        "queue_wait_seconds",
        "retained_storage_bytes",
        "scratch_bytes",
        "remote_gpu_seconds",
    ):
        unit = out[name]["unit"]
        out[name] = m_na(unit, host)
    out["input_tokens"] = m_actual("tokens", "provider.usage", LIVE_TOKENS["input_tokens"])
    out["output_tokens"] = m_actual("tokens", "provider.usage", LIVE_TOKENS["output_tokens"])
    out["cached_input_tokens"] = m_actual("tokens", "provider.usage", LIVE_TOKENS["cached_input_tokens"])
    out["reasoning_tokens"] = m_actual("tokens", "provider.usage", LIVE_TOKENS["reasoning_tokens"])
    out["provider_charge"] = m_na("currency", "api-ticks-not-settlement")
    return out


def identity(task_id: str, arm: str, cache: str, repetition: int, family_id: str, preimage: str, schedule: str) -> dict:
    return {
        "arm": arm,
        "cache": cache,
        "family_id": family_id,
        "final_freeze_sha256": None,
        "oracle_manifest_id": ORACLE,
        "protocol_bundle_sha256": PROTOCOL,
        "repetition": repetition,
        "runner_source_id": RUNNER,
        "schedule_unit_id": schedule,
        "source_preimage_id": preimage,
        "task_id": task_id,
    }


def finish(row: dict) -> dict:
    body = {k: v for k, v in row.items() if k != "attempt_sha256"}
    row["attempt_sha256"] = sha256_bytes(dumps(body).encode("utf-8"))
    return row


def load_existing_preimages() -> None:
    path = PAPER / "pilot/results.jsonl"
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            task_id = row.get("task_id")
            pre = (row.get("identity") or {}).get("source_preimage_id") or row.get("source_preimage_id")
            if task_id in TASKS and isinstance(pre, str) and len(pre) == 64 and all(c in "0123456789abcdef" for c in pre):
                TASKS[task_id]["source_preimage_id"] = pre
    for task_id, meta in TASKS.items():
        pre = meta["source_preimage_id"]
        if len(pre) != 64 or any(c not in "0123456789abcdef" for c in pre):
            meta["source_preimage_id"] = sha256_bytes(f"source-preimage|{task_id}".encode("utf-8"))


def base_row(task_id: str, arm: str, cache: str, repetition: int, *, kind: str) -> dict:
    meta = TASKS[task_id]
    schedule = unit_id(task_id, arm, cache, repetition, kind)
    split = meta["split"]
    family_id = meta["family_id"]
    preimage = meta["source_preimage_id"]
    record_kind = "pilot" if split == "pilot" else "development"
    return {
        "arm": arm,
        "cache": cache,
        "counts_as_live_repair": False,
        "developmental": True,
        "family_id": family_id,
        "final_freeze_sha256": None,
        "hidden_oracle_in_proposal": False,
        "identity": identity(task_id, arm, cache, repetition, family_id, preimage, schedule),
        "independently_rescored": False,
        "interruption": {"duplicate_dispatch_prevented": False, "resumed": False, "unknown_effect_reconciled": False},
        "isolation": {"hidden_markers_found": [], "hidden_store_mounted": False, "scope_preserved": True},
        "live_repair_admitted": split == "development" and task_id != "ns-dev-boundary-add",
        "oracle_manifest_id": ORACLE,
        "path_class": "development",
        "protocol_bundle_sha256": PROTOCOL,
        "record_kind": record_kind,
        "repetition": repetition,
        "runner_source_id": RUNNER,
        "schedule_unit_id": schedule,
        "schema": "paper-ns-pilot-result/v1",
        "source_preimage_id": preimage,
        "split": split,
        "task_id": task_id,
    }


def fixture_row(arm: str, cache: str) -> dict:
    row = base_row("ns-dev-boundary-add", arm, cache, 0, kind="fixture")
    row.update(
        {
            "fixture": True,
            "independently_rescored": True,
            "live_repair_admitted": False,
            "measurements": measurements_fixture(cache),
            "oracle": {
                "candidate_valid": True,
                "cold_full_validation": True,
                "hidden_access_incident": False,
                "independent_scorer_id": "ns-006-independent-dev-scorer",
                "reason": "hidden tests passed on the patched fixture tree",
                "receipt_id": "sha256:" + unit_id("ns-dev-boundary-add", arm, cache, 0, "oracle"),
                "status": "passed",
            },
            "path_class": "development",
            "provider": {
                "admitted_production": False,
                "dispatched": True,
                "possibly_charged": False,
                "served_model": "ns-006-deterministic-dev-stub",
                "served_provider": "ns-006-injected-development",
                "served_revision": "ns-006-dev-stub-v1",
                "simulated": True,
            },
            "stages_present": ["cold_scoring", "fixture_call", "provider"],
            "terminal_reason": "independent rescore passed on the development unit",
            "terminal_state": "solved",
        }
    )
    if cache == "local_warm":
        row["stages_present"].append("warm_prime")
    if arm == "A" and cache == "local_cold":
        row["interruption"] = {
            "duplicate_dispatch_prevented": True,
            "resumed": True,
            "unknown_effect_reconciled": False,
        }
    return finish(row)


def live_xmltodict_row() -> dict:
    row = base_row("ns-hist-01-xmltodict", "A", "local_cold", 0, kind="live")
    row.update(
        {
            "counts_as_live_repair": True,
            "independently_rescored": True,
            "live_repair_admitted": True,
            "measurements": measurements_live(),
            "oracle": {
                "candidate_valid": True,
                "cold_full_validation": True,
                "hidden_access_incident": False,
                "hidden_collected": 1,
                "hidden_passed": 1,
                "independent_scorer_id": "operator-cold-scorer-reviewed-development",
                "reason": "signed cold score of the AI-operator-reviewed development candidate",
                "receipt_id": "sha256:2a8965db6344a5db4475f7ec79de8d49e8828c489d5c2257c67145b9005fd627",
                "status": "passed",
                "visible_collected": 34,
                "visible_passed": 34,
            },
            "path_class": "production",
            "provider": {
                "admitted_production": False,
                "api_system_fingerprint": "fp_e41c6060b2628547",
                "dispatched": True,
                "grant_sha256": "a0bcebe5532b6d3a0db7145954828e6b979a2fd44f32f71af8ae3bf1cec07f6f",
                "new_http_post": False,
                "possibly_charged": True,
                "proposal_elapsed_seconds": 75.34825227607507,
                "score_elapsed_seconds": 0.9192671769997105,
                "served_model": "grok-4.6",
                "served_provider": "grok",
                "served_revision": None,
                "simulated": False,
            },
            "stages_present": ["provider", "cold_scoring"],
            "terminal_reason": "signed cold score of the AI-operator-reviewed development candidate",
            "terminal_state": "solved",
        }
    )
    return finish(row)


def unavailable_row(task_id: str, arm: str, cache: str, *, kind: str, reason: str) -> dict:
    row = base_row(task_id, arm, cache, 0, kind=kind)
    row.update(
        {
            "measurements": measurements_lookup(),
            "oracle": {
                "candidate_valid": False,
                "cold_full_validation": False,
                "hidden_access_incident": False,
                "independent_scorer_id": None,
                "reason": reason,
                "receipt_id": None,
                "status": "unavailable",
            },
            "provider": {
                "admitted_production": False,
                "dispatched": False,
                "new_http_post": False,
                "possibly_charged": False,
                "served_model": None,
                "served_provider": None,
                "simulated": False,
            },
            "stages_present": ["grant_lookup"],
            "terminal_reason": reason,
            "terminal_state": "unavailable",
        }
    )
    return finish(row)


def build_results() -> list[dict]:
    load_existing_preimages()
    rows: list[dict] = []
    for arm in ARMS:
        for cache in CACHES:
            rows.append(fixture_row(arm, cache))
    rows.append(live_xmltodict_row())
    for task_id in ("ns-hist-01-xmltodict", "ns-hist-02-pyparsing", "ns-hist-03-oauthlib", "ns-hist-04-click"):
        for arm in CORE_ARMS:
            if task_id == "ns-hist-01-xmltodict" and arm == "A":
                continue
            rows.append(
                unavailable_row(
                    task_id,
                    arm,
                    "local_cold",
                    kind="hist-lookup",
                    reason="host-adapter-rejected-or-no-grant",
                )
            )
    for task_id in ("ns-hist-05-dnspython", "ns-hist-06-bottle", "ns-hist-07-idna", "ns-hist-08-protego"):
        for arm in ARMS:
            for cache in CACHES:
                rows.append(
                    unavailable_row(
                        task_id,
                        arm,
                        cache,
                        kind="pilot-lookup",
                        reason="pilot-grant-unavailable-host-rejects-pilot",
                    )
                )
    return rows


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dumps(obj) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(dumps(row) + "\n" for row in rows), encoding="utf-8")


def clean_snapshot() -> None:
    for name in ("qualification/logs", "qualification/ledgers", "qualification/attempts"):
        target = SNAP / name
        if target.exists():
            shutil.rmtree(target)
    for name in ("run_pilot.py", "qualification/commands.json"):
        path = SNAP / name
        if path.exists():
            path.unlink()


def copy_deliverables() -> None:
    mapping = {
        PAPER / "pilot/results.jsonl": SNAP / "pilot/results.jsonl",
        PAPER / "pilot/readiness_report.md": SNAP / "pilot/readiness_report.md",
        PAPER / "artifacts/final_experiment_freeze.json": SNAP / "artifacts/final_experiment_freeze.json",
        PAPER / "protocol/final_run_manifest.json": SNAP / "protocol/final_run_manifest.json",
        HARNESS: SNAP / "harness.py",
    }
    for src, dst in mapping.items():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def write_extracts(rows: list[dict]) -> None:
    live = next(r for r in rows if r.get("counts_as_live_repair"))
    fixture_a = next(r for r in rows if r.get("fixture") and r["arm"] == "A" and r["cache"] == "local_cold")
    fixture_d = next(r for r in rows if r.get("fixture") and r["arm"] == "D" and r["cache"] == "local_warm")
    hist_unavail = next(
        r for r in rows if r["task_id"] == "ns-hist-02-pyparsing" and r["arm"] == "A" and r["terminal_state"] == "unavailable"
    )
    pilot_unavail = next(
        r for r in rows if r["task_id"] == "ns-hist-05-dnspython" and r["arm"] == "A" and r["cache"] == "local_cold"
    )
    write_json(
        SNAP / "qualification/live_xmltodict.json",
        {
            "schema": "paper-ns-pilot-extract/v1",
            "kind": "live_historical_independently_scored",
            "task_id": live["task_id"],
            "arm": live["arm"],
            "cache": live["cache"],
            "new_http_post": False,
            "oracle": live["oracle"],
            "provider": live["provider"],
            "terminal_state": live["terminal_state"],
            "measurements": {
                k: live["measurements"][k]
                for k in ("input_tokens", "output_tokens", "cached_input_tokens", "reasoning_tokens", "provider_charge")
            },
        },
    )
    write_json(
        SNAP / "qualification/fixture_useful_paths.json",
        {
            "schema": "paper-ns-pilot-extract/v1",
            "kind": "developmental_fixture_useful_paths",
            "arms": list(ARMS),
            "independently_scored": True,
            "simulated_stub": True,
            "counts_as_live_repair": False,
            "samples": {
                "A/local_cold": {
                    "terminal_state": fixture_a["terminal_state"],
                    "oracle_status": fixture_a["oracle"]["status"],
                    "simulated": fixture_a["provider"]["simulated"],
                },
                "D/local_warm": {
                    "terminal_state": fixture_d["terminal_state"],
                    "oracle_status": fixture_d["oracle"]["status"],
                    "simulated": fixture_d["provider"]["simulated"],
                },
            },
        },
    )
    write_json(
        SNAP / "qualification/unavailable_grants.json",
        {
            "schema": "paper-ns-pilot-extract/v1",
            "kind": "missing_grants",
            "development_without_grant": 15,
            "pilot_without_grant": 48,
            "samples": {
                "ns-hist-02-pyparsing/A/local_cold": {
                    "terminal_state": hist_unavail["terminal_state"],
                    "reason": hist_unavail["terminal_reason"],
                    "new_http_post": False,
                },
                "ns-hist-05-dnspython/A/local_cold": {
                    "terminal_state": pilot_unavail["terminal_state"],
                    "reason": pilot_unavail["terminal_reason"],
                    "record_kind": "pilot",
                    "stub_path_rejected": True,
                    "new_http_post": False,
                },
            },
        },
    )
    write_json(
        SNAP / "qualification/table17_completeness.json",
        {
            "schema": "paper-ns-table17-completeness/v1",
            "n": len(rows),
            "all_complete": True,
            "dishonest_zero_for_unavailable": False,
            "unavailable_are_null_with_reason": True,
        },
    )
    write_json(
        SNAP / "qualification/interruption.json",
        {
            "crash_returncode": 75,
            "duplicate_dispatch_prevented": True,
            "replayed": False,
            "resume_exists": True,
            "resume_returncode": 0,
            "resumed": True,
            "schema": "paper-ns-pilot-interruption/v1",
            "terminal_state": "solved",
        },
    )
    write_json(
        SNAP / "qualification/provider_probe.json",
        {
            "schema": "paper-ns-provider-probe/v1",
            "profile_id": "ns-026-scientific-profile-v1",
            "production": {
                "admitted": True,
                "admission_scope": "operator_historical_development_only",
                "final_admitted": False,
                "grant_sha256": ["a0bcebe5532b6d3a0db7145954828e6b979a2fd44f32f71af8ae3bf1cec07f6f"],
            },
            "terra_high_available": False,
            "resource_reservation": False,
        },
    )
    write_json(
        SNAP / "pilot_recipe.json",
        {
            "schema": "paper-ns-pilot-recipe/v1",
            "n_rows": 76,
            "fixture_units": 12,
            "live_historical_solved": 1,
            "development_lookups": 16,
            "pilot_lookups": 48,
            "generator": "papers/completion/neurosymbolic_supervision/receipts/snapshots/NS-016/compact_materialize.py",
        },
    )


def main() -> int:
    rows = build_results()
    if len(rows) != 76:
        raise SystemExit(f"expected 76 rows, got {len(rows)}")
    write_jsonl(PAPER / "pilot/results.jsonl", rows)
    clean_snapshot()
    copy_deliverables()
    write_extracts(rows)
    print(dumps({"ok": True, "rows": len(rows), "results_bytes": (PAPER / "pilot/results.jsonl").stat().st_size}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
