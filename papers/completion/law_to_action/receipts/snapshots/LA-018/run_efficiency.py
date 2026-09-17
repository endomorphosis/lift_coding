#!/usr/bin/python3.12
"""LA-018 full cost and latency for cold and reused evidence.

Instruments exclusive wall time for retrieval, compilation, solver/checker,
clock/root checks, capability verification, DuckDB consumption, artifact
storage, and handler effects. Cold/warm cache and stale-root/stale-clock
invalidation are executed against frozen development cases. Model tokens,
network bytes, and prices that were not observed are left unset.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import platform
import resource
import shutil
import sys
import tempfile
import time
import traceback
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Mapping
from uuid import uuid4

HERE = Path(__file__).resolve()
ROOT = HERE.parents[6]
SNAPSHOT = HERE.parent
LIVE = ROOT / "papers" / "completion" / "law_to_action"
BENCHMARK = LIVE / "benchmark"
PYTHON = "/usr/bin/python3.12"
VALIDATION_SITE_PACKAGES = Path("/opt/ipfs-validation-site-packages")
SEALED_PATH = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin"
HARNESS_VERSION = "la-018-efficiency-harness/v1"
SCHEMA_RAW = "law-to-action-efficiency-run/v1"
SCHEMA_ENV = "law-to-action-efficiency-environment/v1"
SCHEMA_SUMMARY = "law-to-action-efficiency-summary/v1"
SEED = 104729
CONDITIONS = ("cold", "warm", "stale_root", "stale_clock")
EXCLUSIVE_PHASES = (
    "retrieval",
    "compilation",
    "solver",
    "checker",
    "clock_root_check",
    "capability_verification",
    "database_transaction",
    "artifact_storage",
    "handler_effect",
)
THREAD_ENV = {
    "OMP_NUM_THREADS": "1",
    "OPENBLAS_NUM_THREADS": "1",
    "MKL_NUM_THREADS": "1",
    "NUMEXPR_NUM_THREADS": "1",
    "VECLIB_MAXIMUM_THREADS": "1",
    "RAYON_NUM_THREADS": "1",
}
CURRENT_ROOT = "policy:root-v1"
STALE_ROOT = "policy:root-v2"
CURRENT_CLOCK = "2026-07-28T12:02:00Z"
STALE_CLOCK = "2026-07-28T12:11:00Z"

for path in (
    VALIDATION_SITE_PACKAGES,
    ROOT / "external" / "ipfs_accelerate",
    ROOT / "external" / "ipfs_datasets",
    ROOT / "external" / "ipfs_kit",
    BENCHMARK,
):
    text = str(path)
    if path.is_dir() and text not in sys.path:
        sys.path.insert(0, text)


class RunError(RuntimeError):
    """Efficiency run cannot proceed."""


def sha256_file(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp-" + uuid4().hex)
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def write_jsonl(path: Path, rows: list[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp-" + uuid4().hex)
    with temporary.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n")
    os.replace(temporary, path)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RunError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def pin(path: Path) -> dict[str, Any]:
    return {
        "path": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
        "present": path.is_file(),
        "sha256": sha256_file(path) if path.is_file() else None,
        "size_bytes": path.stat().st_size if path.is_file() else None,
    }


def implementation_pins() -> dict[str, Any]:
    files = {
        "protocol.json": BENCHMARK / "protocol.json",
        "arms.json": BENCHMARK / "arms.json",
        "splits.json": BENCHMARK / "manifests" / "splits.json",
        "sources.json": BENCHMARK / "manifests" / "sources.json",
        "baselines.py": BENCHMARK / "baselines.py",
        "effects.py": BENCHMARK / "handlers" / "effects.py",
        "durable_consumption.py": BENCHMARK / "durable_consumption.py",
        "run_fixed_actions.py": ROOT / "papers/completion/law_to_action/receipts/snapshots/LA-015/run_fixed_actions.py",
        "run_closed_loop.py": ROOT / "papers/completion/law_to_action/receipts/snapshots/LA-016/run_closed_loop.py",
        "run_efficiency.py": HERE,
        "admissibility_enforcement.py": ROOT
        / "external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/admissibility_enforcement.py",
        "authorization.py": ROOT / "external/ipfs_kit/ipfs_kit_py/mcp_server/authorization.py",
        "ucan.py": ROOT / "external/ipfs_kit/ipfs_kit_py/mcp_server/mcplusplus/ucan.py",
        "sat_provider.py": ROOT / "papers/completion/law_to_action/receipts/snapshots/LA-010/sat_provider.py",
        "sat_checker.py": ROOT / "papers/completion/law_to_action/receipts/snapshots/LA-010/sat_checker.py",
        "closed_loop_manifest": LIVE / "results" / "agents" / "run_manifest.json",
    }
    pins = {name: pin(path) for name, path in files.items()}
    return {
        "files": pins,
        "revision": digest({name: row["sha256"] for name, row in pins.items()}),
        "harness_version": HARNESS_VERSION,
        "protocol_revision": "LA-003/v3",
    }


@contextmanager
def phase_timer() -> Iterator[dict[str, float]]:
    box = {"wall_seconds": 0.0}
    started = time.perf_counter()
    try:
        yield box
    finally:
        box["wall_seconds"] = time.perf_counter() - started


class EvidenceCache:
    """Process-local reuse of retrieval, compilation, and solver evidence."""

    def __init__(self) -> None:
        self.retrieval: dict[str, dict[str, Any]] = {}
        self.compilation: dict[str, dict[str, Any]] = {}
        self.solver: dict[str, dict[str, Any]] = {}
        self.checker: dict[str, dict[str, Any]] = {}

    def clear(self) -> None:
        self.retrieval.clear()
        self.compilation.clear()
        self.solver.clear()
        self.checker.clear()

    def invalidate_root(self, policy_root: str) -> list[str]:
        dropped = []
        for store_name, store in (
            ("compilation", self.compilation),
            ("solver", self.solver),
            ("checker", self.checker),
        ):
            for key in [key for key in store if f"|root={policy_root}|" in key]:
                store.pop(key, None)
                dropped.append(f"{store_name}:{key}")
        return dropped

    def invalidate_clock(self, clock: str) -> list[str]:
        dropped = []
        for store_name, store in (("solver", self.solver), ("checker", self.checker)):
            for key in [key for key in store if f"|clock={clock}|" in key]:
                store.pop(key, None)
                dropped.append(f"{store_name}:{key}")
        return dropped


class TimingStore:
    """Wrap durable consumption so database transactions are timed exclusively."""

    def __init__(self, inner: Any) -> None:
        self.inner = inner
        self.elapsed = 0.0
        self.transactions = 0
        self.last_consumed: bool | None = None

    def try_consume(self, token_key: str, *, meta: Mapping[str, Any] | None = None) -> bool:
        started = time.perf_counter()
        try:
            result = self.inner.try_consume(token_key, meta=meta)
            self.last_consumed = bool(result)
            return result
        finally:
            self.elapsed += time.perf_counter() - started
            self.transactions += 1

    def consume_command(self, *args: Any, **kwargs: Any) -> Any:
        started = time.perf_counter()
        try:
            return self.inner.consume_command(*args, **kwargs)
        finally:
            self.elapsed += time.perf_counter() - started
            self.transactions += 1

    def __getattr__(self, name: str) -> Any:
        return getattr(self.inner, name)


def read_meminfo() -> dict[str, int]:
    values: dict[str, int] = {}
    path = Path("/proc/meminfo")
    if not path.is_file():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[0].endswith(":"):
            key = parts[0][:-1]
            try:
                kib = int(parts[1])
            except ValueError:
                continue
            values[key] = kib * 1024
    return values


def probe_hardware() -> dict[str, Any]:
    affinity = sorted(os.sched_getaffinity(0))
    mem = read_meminfo()
    uname = os.uname()
    loadavg = None
    load_path = Path("/proc/loadavg")
    if load_path.is_file():
        loadavg = load_path.read_text(encoding="utf-8").strip().split()[:3]
    cpu_model = None
    cpuinfo = Path("/proc/cpuinfo")
    cpuinfo_identity: dict[str, str] = {}
    if cpuinfo.is_file():
        for line in cpuinfo.read_text(encoding="utf-8").splitlines():
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()
            if key in {"model name", "Hardware", "CPU part", "CPU implementer", "CPU architecture"} and key not in cpuinfo_identity:
                cpuinfo_identity[key] = value
        cpu_model = cpuinfo_identity.get("model name") or cpuinfo_identity.get("Hardware")
        if cpu_model is None and cpuinfo_identity:
            cpu_model = " ".join(f"{key}={value}" for key, value in cpuinfo_identity.items())
    cgroup = None
    cgroup_file = Path("/proc/self/cgroup")
    if cgroup_file.is_file():
        cgroup = cgroup_file.read_text(encoding="utf-8").strip()
    return {
        "sysname": uname.sysname,
        "release": uname.release,
        "machine": uname.machine,
        "python_implementation": platform.python_implementation(),
        "cpu_model": cpu_model,
        "cpuinfo_identity": cpuinfo_identity,
        "logical_cpus_allowed": affinity,
        "logical_cpu_count_allowed": len(affinity),
        "memory_total_bytes": mem.get("MemTotal"),
        "memory_available_bytes_at_probe": mem.get("MemAvailable"),
        "loadavg_1_5_15": loadavg,
        "cgroup": cgroup,
        "concurrency": {
            "maximum_parallel_attempts": 1,
            "observed_parallel_attempts": 1,
            "rule": "One attempt at a time; thread libraries pinned to 1.",
        },
        "thread_environment": dict(THREAD_ENV),
    }


def usage_snapshot() -> dict[str, Any]:
    ru = resource.getrusage(resource.RUSAGE_SELF)
    children = resource.getrusage(resource.RUSAGE_CHILDREN)
    return {
        "self_user_seconds": ru.ru_utime,
        "self_system_seconds": ru.ru_stime,
        "self_max_rss_bytes": ru.ru_maxrss * 1024,
        "children_user_seconds": children.ru_utime,
        "children_system_seconds": children.ru_stime,
        "children_max_rss_bytes": children.ru_maxrss * 1024,
    }


def development_families(la015: Any) -> list[dict[str, Any]]:
    families = [row for row in la015.frozen_families() if row["split"] == "development"]
    counts = {"legal": 0, "cve": 0, "skill": 0}
    for row in families:
        counts[row["population"]] += 1
    if counts != {"legal": 2, "cve": 2, "skill": 2} or len(families) != 6:
        raise RunError(f"expected 6 development families, found {counts}")
    return families


def source_record_for(sources: Mapping[str, Any], family_id: str) -> dict[str, Any]:
    for row in sources["source_records"]:
        if row["lineage_family_id"] == family_id:
            return row
    raise RunError(f"no source record for {family_id}")


def artifact_for(sources: Mapping[str, Any], artifact_id: str) -> dict[str, Any]:
    for row in sources["source_artifacts"]:
        if row["artifact_id"] == artifact_id:
            return row
    raise RunError(f"no source artifact {artifact_id}")


def jsonl_row_for(path: Path, case_id: str) -> tuple[bytes, dict[str, Any] | None]:
    if not path.is_file():
        return b"", None
    raw = path.read_bytes()
    for line in raw.splitlines():
        if not line.strip():
            continue
        row = json.loads(line.decode("utf-8"))
        if row.get("case_id") == case_id:
            return line + b"\n", row
    return raw, None


def retrieval_plan(
    candidate: Mapping[str, Any],
    sources: Mapping[str, Any],
) -> list[dict[str, Any]]:
    record = source_record_for(sources, candidate["lineage_family_id"])
    artifact = artifact_for(sources, record["artifact_id"])
    population = candidate["population"]
    case_id = candidate["candidate_id"]
    local: list[dict[str, Any]] = []
    if population == "legal":
        local.append(
            {
                "kind": "quoted_spans_annotation",
                "path": BENCHMARK / "annotations" / "legal.jsonl",
                "select": case_id,
            }
        )
    elif population == "cve":
        cve_id = record.get("source_locator", {}).get("cve_id")
        if cve_id:
            local.append(
                {
                    "kind": "cve_pair_reproduction",
                    "path": BENCHMARK / "cve_reproduction" / "pairs" / f"{cve_id}.json",
                    "select": None,
                }
            )
        local.append(
            {
                "kind": "cve_pair_case",
                "path": BENCHMARK / "cases" / "cve_pairs.jsonl",
                "select": case_id,
            }
        )
    elif population == "skill":
        local.append(
            {
                "kind": "skill_annotation",
                "path": BENCHMARK / "annotations" / "skills.jsonl",
                "select": case_id,
            }
        )
    local.append(
        {
            "kind": "source_ir_row",
            "path": LIVE / "results" / "source_ir" / "raw.jsonl",
            "select": case_id,
        }
    )
    remote_body = {
        "kind": "upstream_source_body",
        "artifact_id": artifact["artifact_id"],
        "cache_relative_path": artifact.get("cache_relative_path"),
        "source_uri": artifact.get("source_uri"),
        "sha256": artifact.get("sha256"),
        "size_bytes_declared": artifact.get("size_bytes"),
        "redistribution": artifact.get("redistribution", {}).get("status"),
        "present": False,
        "observed": True,
        "bytes_transferred": None,
        "reason": (
            "Upstream body is retrieval_only and is not in the paper artifact; "
            "no network fetch was executed under the sealed validation PATH."
        ),
    }
    return [{"local": local, "unavailable_body": remote_body}]


def retrieve_local(
    cache: EvidenceCache,
    plan: list[dict[str, Any]],
    *,
    allow_cache: bool,
) -> dict[str, Any]:
    transferred = 0
    cached_bytes = 0
    hits = 0
    misses = 0
    files: list[dict[str, Any]] = []
    payload = plan[0]
    for item in payload["local"]:
        path: Path = item["path"]
        key = f"retrieval|{path}|{item.get('select')}|{item['kind']}"
        if allow_cache and key in cache.retrieval:
            entry = cache.retrieval[key]
            hits += 1
            cached_bytes += int(entry["size_bytes"])
            files.append({**entry, "cache": "hit", "bytes_transferred": 0})
            continue
        misses += 1
        if not path.is_file():
            files.append(
                {
                    "kind": item["kind"],
                    "path": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
                    "present": False,
                    "observed": True,
                    "bytes_transferred": None,
                    "size_bytes": None,
                    "sha256": None,
                    "cache": "miss_absent",
                    "reason": "local derived artifact missing",
                }
            )
            continue
        if item.get("select"):
            raw, _row = jsonl_row_for(path, str(item["select"]))
        else:
            raw = path.read_bytes()
        entry = {
            "kind": item["kind"],
            "path": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
            "present": True,
            "observed": True,
            "size_bytes": len(raw),
            "sha256": sha256_bytes(raw),
        }
        cache.retrieval[key] = entry
        transferred += len(raw)
        files.append({**entry, "cache": "miss", "bytes_transferred": len(raw)})
    unavailable = dict(payload["unavailable_body"])
    return {
        "files": files,
        "unavailable_upstream_body": unavailable,
        "bytes_transferred": transferred,
        "bytes_from_cache": cached_bytes,
        "cache_hits": hits,
        "cache_misses": misses,
        "cache_hit": hits > 0 and misses == 0 and transferred == 0,
        "observed": True,
        "network_fetch": False,
    }


def unobserved_model() -> dict[str, Any]:
    return {
        "observed": False,
        "scientific_model_pinned": False,
        "input_tokens": None,
        "output_tokens": None,
        "retry_tokens": None,
        "total_tokens": None,
        "model_calls": None,
        "price_usd": None,
        "price_assumption_used": False,
        "silently_filled": False,
        "reason": (
            "LA-016 closed-loop model study is unrun: no scientific model, tokenizer, "
            "or provider revision is pinned. Token counts are unobserved and are not filled."
        ),
    }


def unobserved_network() -> dict[str, Any]:
    return {
        "observed": False,
        "bytes_transferred": None,
        "round_trips": None,
        "price_usd": None,
        "silently_filled": False,
        "reason": (
            "Validation attempts run with network disabled. No live retrieval, model, "
            "or solver RPC was executed. Local disk reads are recorded under retrieval."
        ),
    }


def observed_retries(count: int, wall_seconds: float) -> dict[str, Any]:
    return {
        "observed": True,
        "retry_count": count,
        "wall_seconds": wall_seconds,
        "retry_tokens": None,
        "silently_filled": False,
        "note": "Retry count is the number of extra solver/handler attempts actually issued in this run.",
    }


def classify_terminal(decision: str, calls: int, effects: int, failure: str | None) -> str:
    if failure:
        return "execution_failure"
    if decision == "abstain":
        return "abstention"
    if decision == "allow" and effects == 1 and calls == 1:
        return "success"
    if decision == "deny" and effects == 0 and calls == 0:
        return "denial"
    if decision == "allow" and effects == 0:
        return "execution_failure"
    if decision == "deny" and effects > 0:
        return "success"
    return "execution_failure"


def round_seconds(value: float) -> float:
    return round(float(value), 9)


def empty_phase(name: str) -> dict[str, Any]:
    return {
        "name": name,
        "wall_seconds": 0.0,
        "exclusive": True,
        "observed": True,
        "cache": None,
    }


def run_attempt(
    *,
    la015: Any,
    baselines: Any,
    config: Mapping[str, Any],
    sources: Mapping[str, Any],
    candidate: Mapping[str, Any],
    condition: str,
    cache: EvidenceCache,
    shared: Mapping[str, Any],
    store: TimingStore,
    revision: str,
) -> dict[str, Any]:
    from ipfs_accelerate_py.agent_supervisor.proof.admissibility_enforcement import (
        SupervisorPreInvocationEnforcement,
    )
    from ipfs_datasets_py.logic.admissibility.receipt import BoundRoots

    attempt_id = f"{SEED}:A4:{condition}:{candidate['candidate_id']}"
    tmp = Path(tempfile.mkdtemp(prefix="la018-"))
    state_dir = Path(tempfile.mkdtemp(prefix="la018-state-"))
    run_id = f"la018-{condition}-{uuid4().hex[:10]}"
    nonce = f"n-{sha256_text(attempt_id)[:24]}"
    policy_root = STALE_ROOT if condition == "stale_root" else CURRENT_ROOT
    clock = STALE_CLOCK if condition == "stale_clock" else CURRENT_CLOCK
    allow_cache = condition != "cold"
    invalidated: list[str] = []
    if condition == "stale_root":
        invalidated = cache.invalidate_root(CURRENT_ROOT)
    elif condition == "stale_clock":
        invalidated = cache.invalidate_clock(CURRENT_CLOCK)

    plan = la015.mutation_plan("none" if condition.startswith("stale") else candidate["mutation"])
    if condition == "stale_root":
        plan.wrong_roots = True
    if condition == "stale_clock":
        plan.expired_clock = True

    phases: dict[str, dict[str, Any]] = {name: empty_phase(name) for name in EXCLUSIVE_PHASES}
    nested: dict[str, Any] = {}
    calls = 0
    failure = None
    decision = "deny"
    store.elapsed = 0.0
    store.transactions = 0
    store.last_consumed = None
    ru_before = usage_snapshot()
    e2e_started = time.perf_counter()
    try:
        with phase_timer() as box:
            retrieval = retrieve_local(cache, retrieval_plan(candidate, sources), allow_cache=allow_cache)
        phases["retrieval"] = {
            "name": "retrieval",
            "wall_seconds": round_seconds(box["wall_seconds"]),
            "exclusive": True,
            "observed": True,
            "cache": "hit" if retrieval["cache_hit"] else "miss",
            "bytes_transferred": retrieval["bytes_transferred"],
            "bytes_from_cache": retrieval["bytes_from_cache"],
            "cache_hits": retrieval["cache_hits"],
            "cache_misses": retrieval["cache_misses"],
            "files": retrieval["files"],
            "unavailable_upstream_body": retrieval["unavailable_upstream_body"],
            "network_fetch": False,
        }

        formula_text = baselines.obligation_formula(candidate)
        formula_digest = sha256_text(formula_text)
        compilation_key = f"compilation|{formula_digest}|root={policy_root}|"
        with phase_timer() as box:
            if allow_cache and compilation_key in cache.compilation:
                compiled = cache.compilation[compilation_key]
                compilation_cache = "hit"
            else:
                nvars, clauses = baselines.parse_dimacs(formula_text)
                compiled = {"nvars": nvars, "clauses": clauses, "formula_digest": formula_digest}
                cache.compilation[compilation_key] = compiled
                compilation_cache = "miss"
        phases["compilation"] = {
            "name": "compilation",
            "wall_seconds": round_seconds(box["wall_seconds"]),
            "exclusive": True,
            "observed": True,
            "cache": compilation_cache,
            "formula_digest": formula_digest,
            "nvars": compiled["nvars"],
            "nclauses": len(compiled["clauses"]),
            "identity_includes": ["formula_digest", "policy_root"],
        }

        solver_key = f"solver|{formula_digest}|root={policy_root}|clock={clock}|"
        with phase_timer() as box:
            if allow_cache and solver_key in cache.solver:
                provider = cache.solver[solver_key]
                solver_cache = "hit"
                provider_elapsed = provider.get("elapsed_seconds")
            else:
                provider = baselines.sat_provider(compiled["nvars"], compiled["clauses"])
                cache.solver[solver_key] = provider
                solver_cache = "miss"
                provider_elapsed = provider.get("elapsed_seconds")
        phases["solver"] = {
            "name": "solver",
            "wall_seconds": round_seconds(box["wall_seconds"]),
            "exclusive": True,
            "observed": True,
            "cache": solver_cache,
            "status": provider.get("status"),
            "authority_kind": "satisfiability",
            "theorem_proof": False,
            "provider": provider.get("provider"),
            "algorithm": provider.get("algorithm"),
            "identity_includes": ["formula_digest", "policy_root", "clock"],
        }
        nested["solver_provider_elapsed_seconds"] = {
            "seconds": provider_elapsed,
            "nested_inside": "solver",
            "added_to_exclusive_sum": False,
            "explanation": (
                "SymPy DPLL elapsed_seconds is a nested observation inside the exclusive "
                "solver wall and is not added again."
            ),
        }

        checker_key = f"checker|{formula_digest}|root={policy_root}|clock={clock}|"
        with phase_timer() as box:
            if allow_cache and checker_key in cache.checker:
                checker = cache.checker[checker_key]
                checker_cache = "hit"
            else:
                checker = baselines.sat_checker(compiled["nvars"], compiled["clauses"], provider)
                cache.checker[checker_key] = checker
                checker_cache = "miss"
        phases["checker"] = {
            "name": "checker",
            "wall_seconds": round_seconds(box["wall_seconds"]),
            "exclusive": True,
            "observed": True,
            "cache": checker_cache,
            "status": checker.get("status"),
            "agrees_with_provider": checker.get("agrees_with_provider"),
            "checker": checker.get("checker"),
            "authority_kind": "satisfiability",
            "theorem_proof": False,
            "identity_includes": ["formula_digest", "policy_root", "clock"],
        }
        obligation_allowed = provider.get("status") == "unsat" and checker.get("agrees_with_provider") is True

        expected_roots = baselines.bound_roots()
        if plan.wrong_roots:
            expected_roots = BoundRoots(
                policy_root=STALE_ROOT,
                corpus_roots=("corpus:legal-v1", "corpus:security-v1"),
                revocation_root="revocation:root-v1",
                circuit_roots=("circuit:auth-v1",),
                vk_roots=("vk:auth-v1",),
            )
        current_roots = baselines.bound_roots()
        with phase_timer() as box:
            roots_match = expected_roots.policy_root == current_roots.policy_root and clock == CURRENT_CLOCK
            clock_ok = clock == CURRENT_CLOCK
            stale_evidence = (not roots_match) or (not clock_ok) or bool(invalidated)
        phases["clock_root_check"] = {
            "name": "clock_root_check",
            "wall_seconds": round_seconds(box["wall_seconds"]),
            "exclusive": True,
            "observed": True,
            "cache": None,
            "expected_policy_root": expected_roots.policy_root,
            "current_policy_root": current_roots.policy_root,
            "expected_clock": CURRENT_CLOCK,
            "observed_clock": clock,
            "roots_match": expected_roots.policy_root == current_roots.policy_root,
            "clock_ok": clock_ok,
            "stale_evidence": stale_evidence,
            "invalidated_keys": invalidated,
        }

        with phase_timer() as box:
            gate = la015.run_ucan(
                baselines,
                config=config,
                candidate=candidate,
                plan=plan,
                nonce=f"u-{sha256_text(attempt_id)[:24]}",
                tmp=tmp,
                shared=shared,
            )
        phases["capability_verification"] = {
            "name": "capability_verification",
            "wall_seconds": round_seconds(box["wall_seconds"]),
            "exclusive": True,
            "observed": True,
            "cache": "uncached_one_shot",
            "decision": gate.get("decision"),
            "reason": gate.get("reason"),
            "crypto": gate.get("crypto"),
            "note": (
                "UCAN tokens are one-shot and are not reused across attempts; warm reuse "
                "applies to retrieval/compilation/solver/checker evidence, not consumed capabilities."
            ),
        }

        pre_allow = bool(obligation_allowed and gate.get("decision") == "allow" and clock_ok and expected_roots.policy_root == CURRENT_ROOT)
        receipt_audience = "audience:supervisor-dispatcher" if pre_allow and not plan.forged_receipt else "audience:wrong"
        receipt = None
        capability = None
        if not plan.missing_receipt and not plan.forged_receipt:
            receipt = la015.attempt_receipt(
                baselines,
                candidate,
                audience_id=receipt_audience,
                nonce=nonce,
                receipt_id=f"receipt:{sha256_text(attempt_id)[:24]}",
            )
            if pre_allow:
                capability = la015.attempt_capability(
                    receipt, capability_id=f"capability:la-018-{sha256_text(attempt_id)[:20]}"
                )
        if plan.forged_receipt:
            receipt = "forged"
            capability = None
        context = la015.attempt_supervisor_context(
            baselines,
            candidate,
            nonce=nonce,
            extra_effects=plan.extra_effect_ids,
            wrong_environment=plan.wrong_environment,
        )
        clock_fn = (lambda: STALE_CLOCK) if plan.expired_clock else (lambda: CURRENT_CLOCK)
        handler_box = {"wall_seconds": 0.0}

        def dispatch() -> Any:
            with phase_timer() as inner:
                result = la015.dispatch_handler(baselines, candidate, state_dir, run_id)
            handler_box["wall_seconds"] += inner["wall_seconds"]
            return result

        delegate = la015.CountingDelegate(dispatch)
        enforcer = SupervisorPreInvocationEnforcement(
            mode="enforce",
            store=store,
            expected_roots=expected_roots,
            clock=clock_fn,
        )
        with phase_timer() as enforce_box:
            if plan.replay and pre_allow and capability is not None and receipt not in (None, "forged"):
                warmup = la015.CountingDelegate(lambda: None)
                enforcer.authorize_and_delegate(context, warmup, receipt=receipt, capability=capability)
            outcome = enforcer.authorize_and_delegate(context, delegate, receipt=receipt, capability=capability)
        nested["enforcement_dispatch_wall_seconds"] = {
            "seconds": round_seconds(enforce_box["wall_seconds"]),
            "nested_inside": ["database_transaction", "handler_effect", "internal_root_clock"],
            "added_to_exclusive_sum": False,
            "explanation": (
                "authorize_and_delegate wall contains database consumption and the handler "
                "delegate. Exclusive sums use the timed store wrapper and handler wrapper, "
                "not this outer envelope."
            ),
        }
        enforce_decision = la015.map_enforce_decision(outcome)
        allowed = pre_allow and enforce_decision == "allow" and delegate.calls == 1
        if enforce_decision == "abstain":
            decision = "abstain"
        else:
            decision = "allow" if allowed else "deny"
        calls = delegate.calls
        phases["database_transaction"] = {
            "name": "database_transaction",
            "wall_seconds": round_seconds(store.elapsed),
            "exclusive": True,
            "observed": True,
            "cache": None,
            "transactions": store.transactions,
            "consumed": store.last_consumed,
            "store_kind": getattr(store.inner, "store_kind", type(store.inner).__name__),
            "in_memory_store": bool(getattr(store.inner, "in_memory", False)),
        }
        phases["handler_effect"] = {
            "name": "handler_effect",
            "wall_seconds": round_seconds(handler_box["wall_seconds"]),
            "exclusive": True,
            "observed": True,
            "cache": None,
            "handler_calls": calls,
            "delegate_called": bool(outcome.delegate_called),
        }
        with phase_timer() as box:
            observation = la015.observe(baselines, state_dir, run_id)
            receipt_path = tmp / "attempt-receipt.json"
            receipt_path.write_bytes(
                canonical_json(
                    {
                        "attempt_id": attempt_id,
                        "run_id": run_id,
                        "decision": decision,
                        "formula_digest": formula_digest,
                        "policy_root": policy_root,
                        "clock": clock,
                    }
                )
            )
            stored_bytes = receipt_path.stat().st_size
        phases["artifact_storage"] = {
            "name": "artifact_storage",
            "wall_seconds": round_seconds(box["wall_seconds"]),
            "exclusive": True,
            "observed": True,
            "cache": None,
            "bytes_written": stored_bytes,
            "journal_event_count": int(observation.get("journal_event_count") or 0),
        }
        if decision == "deny" and calls > 0:
            failure = "A4 decision deny but handler was invoked; effect counters retained"
        denial_reason = outcome.observation.denial_reason
        mechanism = {
            "obligation_allowed": obligation_allowed,
            "sat_status": provider.get("status"),
            "checker_status": checker.get("status"),
            "ucan_decision": gate.get("decision"),
            "enforce_decision": enforce_decision,
            "enforce_mode": "enforce",
            "denial_reason": denial_reason,
            "crypto": "real-ed25519",
            "store_kind": getattr(store.inner, "store_kind", type(store.inner).__name__),
        }
    except Exception as exc:
        failure = f"{type(exc).__name__}: {exc}"
        decision = "abstain"
        observation = {"observed_effect_count": 0, "journal_event_count": 0}
        mechanism = {"error": failure}
        denial_reason = failure
        if phases["retrieval"].get("files") is None:
            phases["retrieval"]["observed"] = False
    e2e_wall = time.perf_counter() - e2e_started
    ru_after = usage_snapshot()
    shutil.rmtree(tmp, ignore_errors=True)
    shutil.rmtree(state_dir, ignore_errors=True)

    exclusive_sum = sum(float(phases[name]["wall_seconds"]) for name in EXCLUSIVE_PHASES)
    overhead = e2e_wall - exclusive_sum
    effects = int(observation.get("observed_effect_count") or 0)
    journal = int(observation.get("journal_event_count") or 0)
    terminal = classify_terminal(decision, calls, effects, failure)
    oracle = candidate["oracle_label"]
    forbidden_effect = (oracle == "forbidden" and effects > 0) or (oracle == "allowed" and effects > 1)
    useful = oracle == "allowed" and terminal == "success" and effects == 1 and not forbidden_effect
    model = unobserved_model()
    network = unobserved_network()
    retries = observed_retries(0, 0.0)
    return {
        "schema": SCHEMA_RAW,
        "task": "LA-018",
        "attempt_id": attempt_id,
        "run_id": run_id,
        "seed": SEED,
        "arm_id": "A4",
        "condition": condition,
        "case_id": candidate["candidate_id"],
        "lineage_family_id": candidate["lineage_family_id"],
        "source_id": candidate["source_id"],
        "population": candidate["population"],
        "split": candidate["split"],
        "oracle_label": oracle,
        "mutation": candidate["mutation"] if not condition.startswith("stale") else f"stale:{condition}",
        "frozen_mutation": candidate["mutation"],
        "decision": decision,
        "terminal_outcome": terminal,
        "handler_calls": calls,
        "observed_effect_count": effects,
        "journal_event_count": journal,
        "observed_forbidden_effect": forbidden_effect,
        "useful_work": useful,
        "sandbox": True,
        "identity_digest": candidate["candidate_digest"],
        "implementation_revision": revision,
        "independent_human_gold": False,
        "empirical_efficiency_result": True,
        "crypto": "real-ed25519",
        "enforce_mode": "enforce",
        "store_kind": mechanism.get("store_kind"),
        "sat_status": mechanism.get("sat_status"),
        "denial_reason": mechanism.get("denial_reason") or denial_reason,
        "failure": failure,
        "cache": {
            "condition": condition,
            "allow_reuse": allow_cache,
            "invalidated_keys": invalidated,
            "stale_evidence": bool(invalidated) or condition.startswith("stale"),
            "policy_root": policy_root,
            "clock": clock,
        },
        "phases": phases,
        "exclusive_phase_sum_seconds": round_seconds(exclusive_sum),
        "end_to_end_wall_seconds": round_seconds(e2e_wall),
        "overhead_seconds": round_seconds(overhead),
        "overhead_explanation": (
            "end_to_end_wall_seconds starts before the first exclusive phase and ends after "
            "the last. overhead_seconds is e2e minus the exclusive phase sum and covers "
            "tempdir setup/teardown, object construction, and control flow between phases. "
            "Nested solver provider elapsed and the outer enforcement-dispatch envelope are "
            "not added to the exclusive sum."
        ),
        "nested_observations": nested,
        "model": model,
        "network": network,
        "retries": retries,
        "price_conversion": {
            "applied": False,
            "price_usd": None,
            "token_saving_treated_as_money": False,
            "graph_size_treated_as_money": False,
            "reason": "Measured usage only. No provider price table was applied.",
        },
        "cpu_user_delta_seconds": round_seconds(ru_after["self_user_seconds"] - ru_before["self_user_seconds"]),
        "cpu_system_delta_seconds": round_seconds(ru_after["self_system_seconds"] - ru_before["self_system_seconds"]),
        "max_rss_bytes_after": ru_after["self_max_rss_bytes"],
        "concurrency": 1,
        "harness_version": HARNESS_VERSION,
    }


def mean(values: list[float]) -> float | None:
    if not values:
        return None
    return round_seconds(sum(values) / len(values))


def summarize(records: list[dict[str, Any]], pins: Mapping[str, Any], environment: Mapping[str, Any], setup: Mapping[str, Any]) -> dict[str, Any]:
    by_condition: dict[str, list[dict[str, Any]]] = {name: [] for name in CONDITIONS}
    for row in records:
        by_condition[row["condition"]].append(row)

    def condition_stats(name: str) -> dict[str, Any]:
        rows = by_condition[name]
        return {
            "condition": name,
            "n": len(rows),
            "end_to_end_wall_mean_seconds": mean([row["end_to_end_wall_seconds"] for row in rows]),
            "exclusive_phase_sum_mean_seconds": mean([row["exclusive_phase_sum_seconds"] for row in rows]),
            "overhead_mean_seconds": mean([row["overhead_seconds"] for row in rows]),
            "retrieval_wall_mean_seconds": mean([row["phases"]["retrieval"]["wall_seconds"] for row in rows]),
            "compilation_wall_mean_seconds": mean([row["phases"]["compilation"]["wall_seconds"] for row in rows]),
            "solver_wall_mean_seconds": mean([row["phases"]["solver"]["wall_seconds"] for row in rows]),
            "checker_wall_mean_seconds": mean([row["phases"]["checker"]["wall_seconds"] for row in rows]),
            "clock_root_check_wall_mean_seconds": mean([row["phases"]["clock_root_check"]["wall_seconds"] for row in rows]),
            "capability_verification_wall_mean_seconds": mean(
                [row["phases"]["capability_verification"]["wall_seconds"] for row in rows]
            ),
            "database_transaction_wall_mean_seconds": mean(
                [row["phases"]["database_transaction"]["wall_seconds"] for row in rows]
            ),
            "artifact_storage_wall_mean_seconds": mean([row["phases"]["artifact_storage"]["wall_seconds"] for row in rows]),
            "handler_effect_wall_mean_seconds": mean([row["phases"]["handler_effect"]["wall_seconds"] for row in rows]),
            "retrieval_bytes_transferred_sum": sum(row["phases"]["retrieval"]["bytes_transferred"] or 0 for row in rows),
            "retrieval_cache_hits": sum(row["phases"]["retrieval"]["cache_hits"] for row in rows),
            "retrieval_cache_misses": sum(row["phases"]["retrieval"]["cache_misses"] for row in rows),
            "useful_work": sum(bool(row["useful_work"]) for row in rows),
            "stale_evidence": sum(bool(row["cache"]["stale_evidence"]) for row in rows),
        }

    paired = []
    by_case: dict[str, dict[str, dict[str, Any]]] = {}
    for row in records:
        by_case.setdefault(row["case_id"], {})[row["condition"]] = row
    for case_id, group in sorted(by_case.items()):
        cold = group["cold"]
        warm = group["warm"]
        stale_root = group["stale_root"]
        stale_clock = group["stale_clock"]
        paired.append(
            {
                "case_id": case_id,
                "oracle_label": cold["oracle_label"],
                "population": cold["population"],
                "cold_e2e_seconds": cold["end_to_end_wall_seconds"],
                "warm_e2e_seconds": warm["end_to_end_wall_seconds"],
                "stale_root_e2e_seconds": stale_root["end_to_end_wall_seconds"],
                "stale_clock_e2e_seconds": stale_clock["end_to_end_wall_seconds"],
                "cold_retrieval_cache": cold["phases"]["retrieval"]["cache"],
                "warm_retrieval_cache": warm["phases"]["retrieval"]["cache"],
                "cold_solver_cache": cold["phases"]["solver"]["cache"],
                "warm_solver_cache": warm["phases"]["solver"]["cache"],
                "stale_root_invalidated": bool(stale_root["cache"]["invalidated_keys"]),
                "stale_clock_invalidated": bool(stale_clock["cache"]["invalidated_keys"]),
                "cold_useful_work": cold["useful_work"],
                "warm_useful_work": warm["useful_work"],
                "stale_root_useful_work": stale_root["useful_work"],
                "stale_clock_useful_work": stale_clock["useful_work"],
                "utility_preserved_on_reuse": cold["useful_work"] == warm["useful_work"],
            }
        )

    reconcilable = []
    for row in records:
        delta = abs(row["end_to_end_wall_seconds"] - row["exclusive_phase_sum_seconds"] - row["overhead_seconds"])
        reconcilable.append(delta < 1e-6)
    allowed_pairs = [row for row in paired if row["oracle_label"] == "allowed"]
    model_filled = any(
        row["model"]["input_tokens"] is not None
        or row["model"]["output_tokens"] is not None
        or row["model"]["retry_tokens"] is not None
        or row["model"]["silently_filled"]
        for row in records
    )
    price_applied = any(row["price_conversion"]["applied"] for row in records)

    total_e2e = sum(row["end_to_end_wall_seconds"] for row in records)
    total_exclusive = sum(row["exclusive_phase_sum_seconds"] for row in records)
    total_overhead = sum(row["overhead_seconds"] for row in records)
    setup_wall = float(setup["wall_seconds"])
    full_paper_cost_wall = setup_wall + total_e2e

    return {
        "schema": SCHEMA_SUMMARY,
        "task": "LA-018",
        "harness_version": HARNESS_VERSION,
        "implementation_revision": pins["revision"],
        "protocol_revision": "LA-003/v3",
        "arm_id": "A4",
        "split": "development",
        "scheduled": len(records),
        "executed": len(records),
        "conditions": list(CONDITIONS),
        "exclusive_phases": list(EXCLUSIVE_PHASES),
        "condition_definitions": {
            "cold": "Empty process-local retrieval/compilation/solver/checker caches. Every phase is a miss.",
            "warm": "Same case identity immediately after cold. Retrieval/compilation/solver/checker reuse cached evidence.",
            "stale_root": "Cached evidence bound to policy:root-v1 is invalidated; expected roots become policy:root-v2.",
            "stale_clock": "Cached solver/checker evidence bound to the current clock is invalidated; clock is expired.",
        },
        "by_condition": {name: condition_stats(name) for name in CONDITIONS},
        "paired_case_comparisons": paired,
        "reconciliation": {
            "identity": "end_to_end_wall_seconds = exclusive_phase_sum_seconds + overhead_seconds",
            "all_rows_reconcile": all(reconcilable),
            "rows": len(records),
            "total_end_to_end_wall_seconds": round_seconds(total_e2e),
            "total_exclusive_phase_sum_seconds": round_seconds(total_exclusive),
            "total_overhead_seconds": round_seconds(total_overhead),
            "setup_qualification_wall_seconds": round_seconds(setup_wall),
            "full_paper_cost_wall_seconds": round_seconds(full_paper_cost_wall),
            "full_paper_cost_rule": (
                "setup_qualification_wall_seconds + sum(end_to_end_wall_seconds). "
                "Do not add exclusive phase sums on top of end-to-end walls."
            ),
            "double_counting_avoided": [
                "SymPy provider elapsed_seconds is nested inside solver wall and is not summed again.",
                "authorize_and_delegate envelope is nested; exclusive database and handler wrappers are used instead.",
                "Setup/qualification wall is reported separately and is included once in full paper cost.",
            ],
            "overhead_covers": [
                "temporary directory create/remove",
                "receipt/capability object construction",
                "control flow between exclusive phases",
            ],
        },
        "cold_warm": {
            "warm_retrieval_always_hit": all(row["warm_retrieval_cache"] == "hit" for row in paired),
            "cold_retrieval_always_miss": all(row["cold_retrieval_cache"] == "miss" for row in paired),
            "warm_solver_always_hit": all(row["warm_solver_cache"] == "hit" for row in paired),
            "cold_solver_always_miss": all(row["cold_solver_cache"] == "miss" for row in paired),
            "utility_preserved_on_reuse": all(row["utility_preserved_on_reuse"] for row in paired),
            "note": (
                "Graph size and token saving are not treated as monetary savings. "
                "Warm reuse preserves the same useful_work flag as the paired cold run."
            ),
        },
        "stale_invalidation": {
            "stale_root_invalidated_every_case": all(row["stale_root_invalidated"] for row in paired),
            "stale_clock_invalidated_every_case": all(row["stale_clock_invalidated"] for row in paired),
            "allowed_stale_root_useful_work": sum(row["stale_root_useful_work"] for row in allowed_pairs),
            "allowed_stale_clock_useful_work": sum(row["stale_clock_useful_work"] for row in allowed_pairs),
            "allowed_cold_useful_work": sum(row["cold_useful_work"] for row in allowed_pairs),
            "allowed_warm_useful_work": sum(row["warm_useful_work"] for row in allowed_pairs),
            "note": (
                "Stale root or clock invalidates reused solver/compilation evidence and the A4 "
                "enforcer denies. Useful work on allowed cases is preserved under cold/warm reuse "
                "and is not preserved under stale evidence."
            ),
        },
        "unobserved_not_filled": {
            "model_tokens_observed": False,
            "model_tokens_silently_filled": model_filled,
            "network_bytes_observed": False,
            "price_conversion_applied": price_applied,
            "retries_observed": True,
            "retry_count_total": sum(row["retries"]["retry_count"] for row in records),
        },
        "hardware": environment["hardware"],
        "environment_ref": "papers/completion/law_to_action/results/efficiency/environment.json",
        "claim_limits": [
            "This is a development-split A4 cost/latency study, not a rescored 900-cell safety result.",
            "Closed-loop model tokens remain unobserved; LA-016 did not pin a scientific model.",
            "SAT/UNSAT cannot authorize theorem_proof allows.",
            "No external price table, token-to-dollar conversion, or graph-size saving is claimed as money.",
            "Upstream PDF/Parquet/SQLite bodies are retrieval_only and were not fetched.",
            "Independent human gold, expert legal fidelity, and real-world legality remain unclaimed.",
            "Network bytes are unobserved under the sealed no-network validation environment.",
        ],
        "independent_human_gold": False,
        "sandbox_only": True,
        "empirical_efficiency_result": True,
    }


def probe_environment(baselines: Any, pins: Mapping[str, Any], hardware: Mapping[str, Any], setup: Mapping[str, Any]) -> dict[str, Any]:
    env = baselines.probe_environment()
    closed = load_json(LIVE / "results" / "agents" / "run_manifest.json")
    return {
        "schema": SCHEMA_ENV,
        "task": "LA-018",
        "observed_at": utc_now(),
        "harness_version": HARNESS_VERSION,
        "implementation_revision": pins["revision"],
        "python": env.get("python"),
        "python_executable": env.get("python_executable"),
        "python_sha256": env.get("python_sha256"),
        "python_version": env.get("python_version"),
        "path": SEALED_PATH,
        "authoritative_path": SEALED_PATH,
        "path_is_sealed": True,
        "path_enforced_in_harness": os.environ.get("PATH") == SEALED_PATH,
        "path_reported_by_late_probe": env.get("path"),
        "path_late_probe_note": (
            "Some imported libraries prepend package bin directories. The harness records the "
            "authoritative sealed PATH separately from that late observation."
        ),
        "home": env.get("home"),
        "home_is_validation_prefix": env.get("home_is_validation_prefix"),
        "cryptography_version": env.get("cryptography_version"),
        "HAVE_CRYPTO_ED25519": env.get("HAVE_CRYPTO_ED25519"),
        "duckdb_available": env.get("duckdb_available"),
        "duckdb_origin": env.get("duckdb_origin"),
        "duckdb_version": env.get("duckdb_version"),
        "sympy_available": env.get("sympy_available"),
        "sympy_origin": env.get("sympy_origin"),
        "source_pins": env.get("source_pins"),
        "hardware": hardware,
        "concurrency": hardware["concurrency"],
        "thread_environment": dict(THREAD_ENV),
        "setup": setup,
        "closed_loop_model_status": {
            "scientific_model_pinned": bool(closed.get("scientific_model_pinned")),
            "dispatchable": bool(closed.get("dispatchable")),
            "status": closed.get("status"),
            "input_tokens_in_la016_ledger": closed.get("input_tokens"),
            "interpretation": (
                "LA-016 recorded 0 tokens as unstarted accounting. LA-018 does not adopt those "
                "zeros as measured model usage."
            ),
        },
        "network": {
            "attempt_network": "disabled",
            "observed": False,
        },
        "pins": pins,
    }


def run(out_dir: Path, snapshot_dir: Path) -> dict[str, Any]:
    os.environ["PATH"] = SEALED_PATH
    for key, value in THREAD_ENV.items():
        os.environ[key] = value
    setup_started = time.perf_counter()
    started = utc_now()
    la015 = load_module(
        "la015_fixed_actions",
        ROOT / "papers/completion/law_to_action/receipts/snapshots/LA-015/run_fixed_actions.py",
    )
    baselines = la015.load_baselines()
    config = baselines.load_arms()
    sources = load_json(BENCHMARK / "manifests" / "sources.json")
    pins = implementation_pins()
    families = development_families(la015)
    mutations = la015.assign_mutations(la015.frozen_families())
    candidates = [
        row
        for row in la015.build_candidates(baselines, la015.frozen_families(), mutations)
        if row["split"] == "development"
    ]
    if len(candidates) != 12:
        raise RunError(f"expected 12 development cases, found {len(candidates)}")
    hardware = probe_hardware()
    env_probe = baselines.probe_environment()
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    durable = baselines.load_durable()
    work = Path(tempfile.mkdtemp(prefix="la018-run-"))
    root_key = Ed25519PrivateKey.generate()
    shared = {"root_key": root_key}
    database = work / "control.duckdb"
    inner_store = durable.DuckDBCapabilityConsumptionStore(database, owner_id="owner:la-018")
    store = TimingStore(inner_store)
    cache = EvidenceCache()
    records: list[dict[str, Any]] = []
    setup = {
        "wall_seconds": round_seconds(time.perf_counter() - setup_started),
        "started_at": started,
        "includes": [
            "module import",
            "pin hashing",
            "development family freeze",
            "DuckDB store attach",
        ],
        "included_in_per_run_rows": False,
        "included_in_full_paper_cost": True,
    }
    try:
        inner_store.attach()
        for candidate in candidates:
            cache.clear()
            for condition in CONDITIONS:
                records.append(
                    run_attempt(
                        la015=la015,
                        baselines=baselines,
                        config=config,
                        sources=sources,
                        candidate=candidate,
                        condition=condition,
                        cache=cache,
                        shared=shared,
                        store=store,
                        revision=pins["revision"],
                    )
                )
    finally:
        inner_store.close()
        shutil.rmtree(work, ignore_errors=True)
    completed = utc_now()
    if len(records) != 48:
        raise RunError(f"expected 48 efficiency attempts, found {len(records)}")
    environment = probe_environment(baselines, pins, hardware, setup)
    environment["run"] = {
        "started_at": started,
        "completed_at": completed,
        "python_environment": env_probe,
    }
    summary = summarize(records, pins, environment, setup)
    live_dir = out_dir
    snap_out = snapshot_dir / "outputs" / "results" / "efficiency"
    for directory in (live_dir, snap_out, snapshot_dir / "probe", snapshot_dir / "traces"):
        directory.mkdir(parents=True, exist_ok=True)
    write_jsonl(live_dir / "raw.jsonl", records)
    write_json(live_dir / "environment.json", environment)
    write_json(live_dir / "summary.json", summary)
    shutil.copy2(live_dir / "raw.jsonl", snap_out / "raw.jsonl")
    shutil.copy2(live_dir / "environment.json", snap_out / "environment.json")
    shutil.copy2(live_dir / "summary.json", snap_out / "summary.json")
    write_json(snapshot_dir / "probe" / "environment.json", environment)
    write_json(
        snapshot_dir / "traces" / "schedule.json",
        {
            "seed": SEED,
            "arm_id": "A4",
            "split": "development",
            "families": [row["lineage_family_id"] for row in families],
            "cases": [row["candidate_id"] for row in candidates],
            "conditions": list(CONDITIONS),
            "scheduled": 48,
            "rule": "For each of 12 development cases, run cold, warm, stale_root, stale_clock in that order with a per-case cache.",
        },
    )
    write_json(
        snapshot_dir / "traces" / "run_head.json",
        {
            "started_at": started,
            "completed_at": completed,
            "records": len(records),
            "implementation_revision": pins["revision"],
            "all_rows_reconcile": summary["reconciliation"]["all_rows_reconcile"],
        },
    )
    return {
        "ok": True,
        "records": len(records),
        "implementation_revision": pins["revision"],
        "started_at": started,
        "completed_at": completed,
        "all_rows_reconcile": summary["reconciliation"]["all_rows_reconcile"],
        "model_tokens_silently_filled": summary["unobserved_not_filled"]["model_tokens_silently_filled"],
        "price_conversion_applied": summary["unobserved_not_filled"]["price_conversion_applied"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("run",))
    parser.add_argument("--out", type=Path, default=LIVE / "results" / "efficiency")
    parser.add_argument("--snapshot", type=Path, default=SNAPSHOT)
    args = parser.parse_args(argv)
    result = run(args.out, args.snapshot)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
