#!/usr/bin/env python3
"""Materialize and verify the retained SwissKnife parser-failure backlog.

The generator consumes the compact repository index and its polyglot analyzer
health report.  It fails closed unless the two artifacts describe exactly the
same disposition ledger and the retained failure population is the reviewed
258-row set.  No source file is parsed or mutated here: this program only
projects immutable evidence into a content-addressed conformance manifest and
a marker-delimited Markdown task section.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import stat
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


SCHEMA = "swissknife/parser-failure-backlog@1"
MANIFEST_SCHEMA = "swissknife/parser-failure-backlog-manifest@1"
BOARD_NAMESPACE = "swissknife-symbolic-contract-assurance-v1"
GOAL_ID = "SCA-G022"
EXPECTED_FAILURE_COUNT = 258
MAX_GATE_FAN_IN = 32

DEFAULT_INDEX = Path(
    "data/agent_supervisor/swissknife_contract_assurance/"
    "audit/current-index-20260729/repository-index.json"
)
DEFAULT_HEALTH = Path(
    "data/agent_supervisor/swissknife_contract_assurance/"
    "audit/unsafe-publication-20260729T171543Z/analyzer_health/report.json"
)
DEFAULT_TODO = Path(
    "implementation_plan/docs/"
    "44-swissknife-symbolic-contract-assurance.todo.md"
)
DEFAULT_MANIFEST = Path(
    "implementation_plan/conformance/"
    "swissknife-parser-failure-backlog-v1.json"
)

LOGICAL_INDEX = DEFAULT_INDEX.as_posix()
LOGICAL_HEALTH = DEFAULT_HEALTH.as_posix()
LOGICAL_TODO = DEFAULT_TODO.as_posix()
LOGICAL_MANIFEST = DEFAULT_MANIFEST.as_posix()

SECTION_START = (
    "<!-- BEGIN GENERATED SWISSKNIFE PARSER FAILURE BACKLOG v1 -->"
)
SECTION_END = "<!-- END GENERATED SWISSKNIFE PARSER FAILURE BACKLOG v1 -->"

ROW_ID_RE = re.compile(
    r"^sca-repository-index-row:sha256:(?P<digest>[0-9a-f]{64})$"
)
SHA256_RE = re.compile(r"^sha256:(?P<digest>[0-9a-f]{64})$")
TASK_ID_RE = re.compile(r"^SCA-(?P<number>[0-9]{3})$")
HEADER_RE = re.compile(
    r"^##[ \t]+(?P<task_id>SCA-[0-9]{3})(?:[ \t]+(?P<title>[^\n]*))?$",
    re.MULTILINE,
)

ACTIVE_JS_PATHS = frozenset(
    {
        "ipfs_accelerate_js/src/utils/run_web_platform_integration_tests.js",
        "test/mocks/stubs/chai-stub.js",
        "test/unit/cli/chat-command.test.js",
        "test/utils/mockMCPClient.js",
    }
)
PYTHON_PATHS = frozenset(
    {
        "ipfs_accelerate_js/test/performance/webgpu_optimizer/run_benchmarks.py",
        "test/fixed_web_platform/cross_browser_model_sharding.py",
        "test/web_platform_test_output/test_hf_bert.py",
    }
)
STRUCTURED_PATHS = frozenset(
    {
        "benchmark-results/sample-baseline.json",
        "docs/ast_exports/full_asts/python/swissknife_old/"
        "ipfs_transformers.py.ast.json",
    }
)


class BacklogError(ValueError):
    """Input evidence or generated projection is inconsistent."""


@dataclass(frozen=True)
class FamilySpec:
    name: str
    task_id: str
    title: str
    expected_count: int
    source_scopes: tuple[str, ...]
    acceptance: str

    @property
    def receipt_path(self) -> str:
        return (
            "data/agent_supervisor/swissknife_contract_assurance/"
            f"parser-failures/clusters/{self.name.casefold()}.json"
        )


FAMILIES: tuple[FamilySpec, ...] = (
    FamilySpec(
        "UNIT",
        "SCA-232",
        "Repair TypeScript unit-test parser failures without blanket exclusion",
        232,
        ("swissknife/ipfs_accelerate_js/test/unit",),
        (
            "All 232 pinned rows receive per-path reviewed provenance and a "
            "fresh parser disposition. A directory-prefix or test-prefix "
            "blanket exclusion is forbidden because expected-behavior tests, "
            "including scheduler contracts, remain contract evidence."
        ),
    ),
    FamilySpec(
        "BROWSER",
        "SCA-233",
        "Repair browser integration TypeScript parser failures",
        9,
        ("swissknife/ipfs_accelerate_js/test/browser",),
        (
            "All 9 browser rows parse or receive a narrowly reviewed typed "
            "disposition; browser/WebGPU/WebNN contract evidence remains "
            "visible to the repository index."
        ),
    ),
    FamilySpec(
        "ACTIVEJS",
        "SCA-234",
        "Repair active JavaScript and MCP test parser failures",
        4,
        tuple(f"swissknife/{path}" for path in sorted(ACTIVE_JS_PATHS)),
        (
            "The three real JavaScript/MCP files "
            "(test/mocks/stubs/chai-stub.js, "
            "test/unit/cli/chat-command.test.js, and "
            "test/utils/mockMCPClient.js) must achieve real parser success. "
            "Only ipfs_accelerate_js/src/utils/"
            "run_web_platform_integration_tests.js may receive a reviewed "
            "nonsemantic shell-script disposition after its shebang/content "
            "identity is proved; no suffix-wide exclusion is admitted."
        ),
    ),
    FamilySpec(
        "PYTHON",
        "SCA-235",
        "Repair Python failures and symlink classification order",
        3,
        (
            *tuple(f"swissknife/{path}" for path in sorted(PYTHON_PATHS)),
            "external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/"
            "analysis/repository_snapshot.py",
            "external/ipfs_accelerate/test/api/"
            "test_agent_supervisor_repository_snapshot.py",
        ),
        (
            "The two real Python files "
            "(test/fixed_web_platform/cross_browser_model_sharding.py and "
            "test/web_platform_test_output/test_hf_bert.py) must achieve "
            "Python AST parser success. Only ipfs_accelerate_js/test/"
            "performance/webgpu_optimizer/run_benchmarks.py may receive a "
            "symlink disposition. Repository snapshot classification checks "
            "EntryKind.SYMLINK before suffix eligibility, with positive and "
            "negative regression fixtures and no false parser success."
        ),
    ),
    FamilySpec(
        "STRUCTURED",
        "SCA-236",
        "Repair invalid and oversized structured-data parser failures",
        2,
        tuple(f"swissknife/{path}" for path in sorted(STRUCTURED_PATHS)),
        (
            "The empty JSON and oversized generated AST export receive "
            "content-specific repairs or reviewed typed dispositions; JSON "
            "validity and size budgets are not weakened globally."
        ),
    ),
    FamilySpec(
        "LEGACY",
        "SCA-237",
        "Classify legacy archive parser failures explicitly",
        8,
        ("swissknife/web/legacy-archive",),
        (
            "All 8 legacy archive rows receive reviewed, content-addressed "
            "dispositions that are limited to the archive boundary and cannot "
            "hide current web, MCP, scheduler, or model-serving surfaces."
        ),
    ),
)
FAMILY_BY_NAME = {item.name: item for item in FAMILIES}
EXPECTED_FAMILY_COUNTS = {
    item.name: item.expected_count for item in FAMILIES
}
LANES = tuple(f"sca-parser-failure-lane-{index:02d}" for index in range(4))


def _fail(condition: bool, message: str) -> None:
    if not condition:
        raise BacklogError(message)


def _canonical_json_bytes(value: Any, *, ensure_ascii: bool = False) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=ensure_ascii,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, RecursionError) as exc:
        raise BacklogError("value is not canonical JSON") from exc


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    try:
        return _sha256_bytes(path.read_bytes())
    except OSError as exc:
        raise BacklogError(f"cannot read {path}: {exc}") from exc


def _unique_object(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, member in pairs:
        if key in value:
            raise BacklogError(f"JSON object repeats key {key!r}")
        value[key] = member
    return value


def _reject_json_constant(value: str) -> None:
    raise BacklogError(f"JSON contains forbidden numeric constant {value}")


def _load_json_object(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_text(encoding="utf-8")
        value = json.loads(
            raw,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_json_constant,
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BacklogError(f"cannot decode {path}: {exc}") from exc
    _fail(isinstance(value, dict), f"{path} must contain a JSON object")
    return value


def _varint(value: int) -> bytes:
    _fail(value >= 0, "varint cannot encode a negative integer")
    output = bytearray()
    while True:
        current = value & 0x7F
        value >>= 7
        output.append(current | (0x80 if value else 0))
        if not value:
            return bytes(output)


def _cid_v1_dag_json_from_digest(digest: bytes) -> str:
    _fail(len(digest) == 32, "sha2-256 digest must contain 32 bytes")
    # CIDv1 + dag-json (0x0129) + sha2-256 multihash (0x12, length 32).
    raw = (
        _varint(1)
        + _varint(0x0129)
        + _varint(0x12)
        + _varint(len(digest))
        + digest
    )
    encoded = base64.b32encode(raw).decode("ascii").rstrip("=").casefold()
    return "b" + encoded


def _cid_v1_dag_json_sha256(value: bytes) -> str:
    return _cid_v1_dag_json_from_digest(hashlib.sha256(value).digest())


def _identity(prefix: str, value: Any, *, ensure_ascii: bool = False) -> str:
    digest = _sha256_bytes(
        _canonical_json_bytes(value, ensure_ascii=ensure_ascii)
    )
    return f"{prefix}:sha256:{digest}"


def _digest_from(value: str, *, noun: str) -> str:
    match = SHA256_RE.fullmatch(str(value or ""))
    _fail(match is not None, f"{noun} must be a sha256:<64-hex> digest")
    return match.group("digest")


def _row_digest(value: str) -> str:
    match = ROW_ID_RE.fullmatch(str(value or ""))
    _fail(match is not None, "repository row ID is malformed")
    return match.group("digest")


def _normalize_language(value: Any) -> str:
    raw = str(value or "").strip().casefold()
    if raw.startswith("."):
        raw = raw[1:]
    if "@" in raw:
        raw = raw.split("@", 1)[0]
    return {
        "cjs": "javascript",
        "mjs": "javascript",
        "js": "javascript",
        "ts": "typescript",
        "py": "python",
        "json_schema": "json-schema",
        "openapi": "openapi-json",
    }.get(raw, raw)


def _language_for_row(row: Mapping[str, Any]) -> str:
    selected = _normalize_language(row.get("language"))
    if selected:
        return selected
    suffix = Path(str(row.get("path") or "")).suffix.casefold()
    return {
        ".cjs": "javascript",
        ".js": "javascript",
        ".mjs": "javascript",
        ".jsx": "jsx",
        ".py": "python",
        ".ts": "typescript",
        ".tsx": "tsx",
        ".json": "json",
    }.get(suffix, "")


def _typed_reason_code(value: Any, *, fallback: str) -> str:
    text = str(value or "").strip()
    if not text:
        return fallback
    head = text.split(":", 1)[0].strip()
    head = head.split(" at line", 1)[0].strip()
    if " " in head and head[0].isupper():
        head = head.split(" ", 1)[0].strip()
    normalized = head.casefold().replace(" ", "_")
    return (normalized or fallback)[:128]


def _expected_health_disposition(row: Mapping[str, Any]) -> dict[str, str]:
    language = _language_for_row(row)
    status = str(
        row.get("parser_status") or row.get("status") or row.get("outcome") or ""
    ).strip().casefold()
    parser_identity = str(row.get("parser_identity") or "").strip()
    parser_reason = str(
        row.get("parser_reason")
        or row.get("reason_code")
        or row.get("parse_error")
        or ""
    )
    success = {"indexed", "cache_hit", "success", "parsed"}
    failure = {
        "parse_failure",
        "failure",
        "failed",
        "error",
        "bounded_failure",
    }
    non_eligible = {
        "not_applicable",
        "unsupported",
        "deleted",
        "excluded",
        "n/a",
        "",
    }
    if status in non_eligible and status not in success | failure:
        outcome = "not_eligible"
        reason = _typed_reason_code(
            parser_reason, fallback=status or "not_eligible"
        )
        emitted_status = status or "not_applicable"
    elif status in failure or (not status and parser_reason):
        outcome = "bounded_failure"
        reason = _typed_reason_code(parser_reason, fallback="parse_failure")
        emitted_status = status or "parse_failure"
    elif status in success or (not status and not parser_reason and language):
        outcome = "success"
        reason = "indexed"
        emitted_status = status or "indexed"
    elif language:
        outcome = "bounded_failure"
        reason = _typed_reason_code(
            parser_reason or status, fallback="untyped_parser_status"
        )
        emitted_status = status or "parse_failure"
    else:
        outcome = "not_eligible"
        reason = _typed_reason_code(parser_reason, fallback="not_eligible")
        emitted_status = status or "not_applicable"
    identity_input = {
        "path": str(row.get("path") or ""),
        "language": language,
        "outcome": outcome,
        "reason_code": reason,
        "parser_identity": parser_identity,
    }
    return {
        **identity_input,
        "parser_status": emitted_status,
        "disposition_id": _identity(
            "path-disposition", identity_input, ensure_ascii=True
        ),
    }


def _validate_content_identity(report: Mapping[str, Any]) -> None:
    identity = report.get("content_identity")
    _fail(isinstance(identity, dict), "health report lacks content identity")
    payload = {key: report[key] for key in report if key != "content_identity"}
    canonical = _canonical_json_bytes(payload, ensure_ascii=True)
    digest = _sha256_bytes(canonical)
    _fail(
        identity.get("digest") == f"sha256:{digest}",
        "health report SHA-256 identity does not match its canonical payload",
    )
    _fail(
        identity.get("byte_length") == len(canonical),
        "health report content-identity byte length is incorrect",
    )
    _fail(
        identity.get("cid") == _cid_v1_dag_json_sha256(canonical),
        "health report CIDv1 dag-json identity is incorrect",
    )
    _fail(
        identity.get("cid_version") == 1
        and identity.get("multicodec") == "dag-json"
        and identity.get("multihash") == "sha2-256",
        "health report uses an unexpected multiformat identity profile",
    )


def _family_for_path(path: str) -> str:
    if path.startswith("ipfs_accelerate_js/test/unit/"):
        return "UNIT"
    if path.startswith("ipfs_accelerate_js/test/browser/"):
        return "BROWSER"
    if path in ACTIVE_JS_PATHS:
        return "ACTIVEJS"
    if path in PYTHON_PATHS:
        return "PYTHON"
    if path in STRUCTURED_PATHS:
        return "STRUCTURED"
    if path.startswith("web/legacy-archive/"):
        return "LEGACY"
    raise BacklogError(f"parse-failure path has no actionable family: {path}")


def _validate_sources(
    index_path: Path, health_path: Path
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    index = _load_json_object(index_path)
    health = _load_json_object(health_path)
    _fail(
        index.get("schema")
        == "ipfs_accelerate_py/agent-supervisor/sca-repository-index@1",
        "repository index schema is not the reviewed SCA schema",
    )
    _fail(
        health.get("schema")
        == "ipfs_accelerate_py/agent-supervisor/polyglot-ast-health@1",
        "analyzer-health schema is not the reviewed polyglot schema",
    )

    index_id = str(index.get("index_id") or "")
    index_content = {
        key: index[key] for key in index if key != "index_id"
    }
    _fail(
        index_id == _identity("sca-repository-index", index_content),
        "repository index content ID is invalid",
    )
    snapshot = index.get("snapshot")
    _fail(isinstance(snapshot, dict), "repository index lacks a snapshot")
    _fail(
        isinstance(snapshot.get("snapshot_id"), str)
        and str(snapshot["snapshot_id"]).startswith(
            "sca-repository-snapshot:sha256:"
        ),
        "repository snapshot ID is malformed",
    )
    _validate_content_identity(health)

    rows = index.get("rows")
    dispositions = health.get("dispositions")
    disposition_ids = health.get("disposition_ids")
    _fail(isinstance(rows, list), "repository index rows must be a list")
    _fail(
        isinstance(dispositions, list),
        "health dispositions must be a list",
    )
    _fail(
        isinstance(disposition_ids, list),
        "health disposition IDs must be a list",
    )
    _fail(
        len(rows) == len(dispositions) == len(disposition_ids),
        "index and health disposition ledgers differ in length",
    )
    _fail(
        all(isinstance(item, dict) for item in rows),
        "repository index contains a non-object row",
    )
    _fail(
        all(isinstance(item, dict) for item in dispositions),
        "health report contains a non-object disposition",
    )
    row_paths = [str(item.get("path") or "") for item in rows]
    health_paths = [str(item.get("path") or "") for item in dispositions]
    _fail(
        row_paths == sorted(row_paths) and len(row_paths) == len(set(row_paths)),
        "repository index paths are not unique canonical order",
    )
    _fail(
        health_paths == row_paths,
        "health disposition ledger does not exactly match index path order",
    )
    _fail(
        disposition_ids
        == [str(item.get("disposition_id") or "") for item in dispositions],
        "health disposition ID ledger differs from full dispositions",
    )
    _fail(
        len(disposition_ids) == len(set(disposition_ids)),
        "health disposition IDs are not unique",
    )

    failure_rows: list[dict[str, Any]] = []
    health_by_path: dict[str, dict[str, Any]] = {}
    for row, actual in zip(rows, dispositions, strict=True):
        row_id = str(row.get("row_id") or "")
        content = {key: row[key] for key in row if key != "row_id"}
        _fail(
            row_id == _identity("sca-repository-index-row", content),
            f"repository row content ID is invalid for {row.get('path')}",
        )
        expected = _expected_health_disposition(row)
        for field in (
            "path",
            "language",
            "outcome",
            "reason_code",
            "parser_status",
            "parser_identity",
            "disposition_id",
        ):
            _fail(
                actual.get(field) == expected[field],
                (
                    "health disposition mismatch for "
                    f"{row.get('path')} field {field}"
                ),
            )
        _fail(
            actual.get("parser_authority")
            in {
                "real_typescript_compiler",
                "python_ast",
                "stdlib_json",
                "regex_forbidden",
                "unavailable",
                "unknown",
            },
            f"health disposition has invalid authority for {row.get('path')}",
        )
        health_by_path[expected["path"]] = actual
        if row.get("parser_status") == "parse_failure":
            _fail(
                row.get("disposition_kind") == "parse_failure"
                and actual.get("outcome") == "bounded_failure",
                f"failure row is not a bounded failure: {row.get('path')}",
            )
            failure_rows.append(dict(row))

    _fail(
        len(failure_rows) == EXPECTED_FAILURE_COUNT,
        (
            f"expected {EXPECTED_FAILURE_COUNT} parse failures, "
            f"found {len(failure_rows)}"
        ),
    )
    unique_fields = (
        ("row_id", lambda row: row.get("row_id")),
        ("path", lambda row: row.get("path")),
        ("content_digest", lambda row: row.get("content_digest")),
        (
            "source_ref.digest",
            lambda row: (row.get("source_ref") or {}).get("digest"),
        ),
        ("ast_record_id", lambda row: row.get("ast_record_id")),
        (
            "ast_ref.digest",
            lambda row: (row.get("ast_ref") or {}).get("digest"),
        ),
    )
    for noun, select in unique_fields:
        values = [str(select(row) or "") for row in failure_rows]
        _fail(
            all(values) and len(values) == len(set(values)),
            f"failure rows do not have unique nonempty {noun}",
        )
    for row in failure_rows:
        _row_digest(str(row["row_id"]))
        _digest_from(str(row["content_digest"]), noun="row content digest")
        source_ref = row.get("source_ref")
        ast_ref = row.get("ast_ref")
        _fail(
            isinstance(source_ref, dict) and isinstance(ast_ref, dict),
            f"row references are malformed for {row['path']}",
        )
        _fail(
            source_ref.get("digest") == row.get("content_digest"),
            f"source reference differs from content digest for {row['path']}",
        )
        _digest_from(str(ast_ref.get("digest") or ""), noun="AST reference")
        row["health_disposition"] = health_by_path[str(row["path"])]
        row["actionable_family"] = _family_for_path(str(row["path"]))

    family_counts = Counter(
        str(item["actionable_family"]) for item in failure_rows
    )
    _fail(
        dict(sorted(family_counts.items()))
        == dict(sorted(EXPECTED_FAMILY_COUNTS.items())),
        (
            "actionable family population differs from reviewed counts: "
            f"{dict(sorted(family_counts.items()))}"
        ),
    )

    official_clusters = health.get("clusters")
    _fail(
        isinstance(official_clusters, list) and len(official_clusters) == 6,
        "health report must contain exactly 6 official failure clusters",
    )
    cluster_map: dict[tuple[str, str, str], dict[str, Any]] = {}
    for cluster in official_clusters:
        _fail(isinstance(cluster, dict), "failure cluster must be an object")
        key = (
            str(cluster.get("language") or ""),
            str(cluster.get("reason_code") or ""),
            str(cluster.get("parser_identity") or ""),
        )
        _fail(key not in cluster_map, "health report repeats a failure cluster")
        expected_id = _identity(
            "failure-cluster",
            {
                "language": key[0],
                "reason_code": key[1],
                "parser_identity": key[2],
            },
            ensure_ascii=True,
        )
        _fail(
            cluster.get("cluster_id") == expected_id,
            f"official failure cluster ID is invalid: {cluster.get('cluster_id')}",
        )
        cluster_map[key] = cluster
    derived_cluster_counts: Counter[tuple[str, str, str]] = Counter()
    for row in failure_rows:
        disposition = row["health_disposition"]
        key = (
            str(disposition["language"]),
            str(disposition["reason_code"]),
            str(disposition["parser_identity"]),
        )
        derived_cluster_counts[key] += 1
        _fail(
            key in cluster_map,
            f"failure row has no official health cluster: {row['path']}",
        )
        row["official_failure_cluster_id"] = cluster_map[key]["cluster_id"]
    _fail(
        set(derived_cluster_counts) == set(cluster_map),
        "official health clusters and failure rows differ",
    )
    for key, count in derived_cluster_counts.items():
        _fail(
            cluster_map[key].get("count") == count,
            f"official cluster count is wrong for {key}",
        )

    metrics = health.get("metrics")
    _fail(isinstance(metrics, dict), "health report metrics are missing")
    _fail(
        metrics.get("bounded_failure_count") == EXPECTED_FAILURE_COUNT
        and metrics.get("cluster_count") == 6
        and metrics.get("tracked_row_count") == len(rows)
        and metrics.get("disposition_sample_count") == len(dispositions),
        "health report population metrics differ from its ledgers",
    )
    _fail(
        index.get("health", {}).get("metrics", {}).get(
            "parser_failure_ratio"
        )
        == EXPECTED_FAILURE_COUNT
        / int(metrics.get("eligible_path_count") or 0),
        "repository index parser-failure ratio is inconsistent",
    )
    return index, health, failure_rows


def _task_number(task_id: str) -> int:
    match = TASK_ID_RE.fullmatch(task_id)
    _fail(match is not None, f"invalid generated task ID: {task_id}")
    return int(match.group("number"))


def _task_common(
    *,
    task_id: str,
    title: str,
    kind: str,
    depends_on: Sequence[str],
    outputs: Sequence[str],
    lane_index: int,
    resource_class: str,
    resource_stage: str,
    timeout_seconds: int,
    interfaces: Sequence[str],
    context_budget_tokens: int,
    provider_role: str,
    conflict_policy: str,
    preconditions: str,
    effects: str,
    evidence_subset: str,
    acceptance: str,
    extra: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    task = {
        "task_id": task_id,
        "title": title,
        "kind": kind,
        "priority": "P0",
        "track": "parser-health",
        "depends_on": list(depends_on),
        "goal_id": GOAL_ID,
        "outputs": list(outputs),
        "validation": (
            "python3 scripts/swissknife_parser_failure_backlog.py "
            f"check --task-id {task_id}"
        ),
        "board_namespace": BOARD_NAMESPACE,
        "bundle": f"swissknife/contract-assurance/parser-failures/{kind}",
        "parallel_lane": LANES[lane_index % len(LANES)],
        "resource_class": resource_class,
        "resource_stage": resource_stage,
        "implementation_timeout_seconds": timeout_seconds,
        "predicted_files": list(outputs),
        "interfaces": list(interfaces),
        "context_budget_tokens": context_budget_tokens,
        "provider_role": provider_role,
        "conflict_policy": conflict_policy,
        "preconditions": preconditions,
        "effects": effects,
        "evidence_subset": evidence_subset,
        "acceptance": acceptance,
        "extra": dict(extra or {}),
    }
    return task


def _build_tasks(
    failure_rows: Sequence[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    tasks: list[dict[str, Any]] = []
    for index, family in enumerate(FAMILIES):
        outputs = [*family.source_scopes, family.receipt_path]
        tasks.append(
            _task_common(
                task_id=family.task_id,
                title=family.title,
                kind=f"cluster-{family.name.casefold()}",
                depends_on=("SCA-231", "SCA-229"),
                outputs=outputs,
                lane_index=index,
                resource_class="cpu-medium",
                resource_stage="implementation",
                timeout_seconds=14400,
                interfaces=(
                    "ParserFailureClusterRepair@1",
                    "PolyglotASTHealthReport",
                ),
                context_budget_tokens=2048,
                provider_role="grok-implement, codex-review",
                conflict_policy=(
                    "Touch only the declared family scope and its unique "
                    "cluster receipt; preserve the reviewed health thresholds "
                    "and retain contract-bearing evidence."
                ),
                preconditions=(
                    "SCA-231 pins the retained 258-row population and SCA-229 "
                    "keeps implementation evidence separate from acceptance."
                ),
                effects=(
                    f"Repairs or explicitly disposes the {family.expected_count} "
                    f"{family.name} rows and emits {family.receipt_path}."
                ),
                evidence_subset=(
                    f"{LOGICAL_MANIFEST} family {family.name}; repository index "
                    f"{LOGICAL_INDEX}; health report {LOGICAL_HEALTH}"
                ),
                acceptance=family.acceptance,
                extra={
                    "Failure family": family.name,
                    "Failure row count": str(family.expected_count),
                    "LLM context budget bytes": "12288",
                    "Manifest": LOGICAL_MANIFEST,
                },
            )
        )

    sorted_rows = sorted(
        failure_rows, key=lambda row: _row_digest(str(row["row_id"]))
    )
    row_entries: list[dict[str, Any]] = []
    leaves_by_nibble: dict[str, list[str]] = defaultdict(list)
    for offset, row in enumerate(sorted_rows):
        task_id = f"SCA-{238 + offset:03d}"
        digest = _row_digest(str(row["row_id"]))
        family_name = str(row["actionable_family"])
        family = FAMILY_BY_NAME[family_name]
        nibble = digest[0].upper()
        gate_task_id = f"SCA-{496 + int(nibble, 16):03d}"
        receipt = (
            "data/agent_supervisor/swissknife_contract_assurance/"
            f"parser-failures/rows/{digest}.json"
        )
        parser_reason = str(row.get("parser_reason") or "")
        row_path = str(row["path"])
        if row_path == (
            "ipfs_accelerate_js/src/utils/"
            "run_web_platform_integration_tests.js"
        ):
            required_resolution = "reviewed_nonsemantic_shell_disposition"
            resolution_acceptance = (
                "The fresh row must be a reviewed nonsemantic shell-script "
                "disposition bound to its shebang/content identity; it must "
                "not be reported as JavaScript parser success."
            )
        elif row_path in ACTIVE_JS_PATHS:
            required_resolution = "real_javascript_parser_success"
            resolution_acceptance = (
                "The fresh row must be successful output from the real "
                "JavaScript/TypeScript compiler parser; exclusion or a "
                "nonsemantic disposition does not satisfy this task."
            )
        elif row_path == (
            "ipfs_accelerate_js/test/performance/"
            "webgpu_optimizer/run_benchmarks.py"
        ):
            required_resolution = "reviewed_symlink_disposition"
            resolution_acceptance = (
                "The fresh row must be a reviewed symlink disposition "
                "produced before suffix eligibility; parser success or a "
                "generic unsupported disposition does not satisfy this task."
            )
        elif row_path in PYTHON_PATHS:
            required_resolution = "python_ast_parser_success"
            resolution_acceptance = (
                "The fresh row must be successful Python AST output; "
                "exclusion, symlink routing, or another nonsemantic "
                "disposition does not satisfy this task."
            )
        else:
            required_resolution = "parser_success_or_reviewed_typed_disposition"
            resolution_acceptance = (
                "The fresh row must be parser success or the exact "
                "family-approved typed disposition."
            )
        entry = {
            "task_id": task_id,
            "cluster_task_id": family.task_id,
            "gate_task_id": gate_task_id,
            "gate_nibble": nibble,
            "actionable_family": family_name,
            "row_id": row["row_id"],
            "row_digest": digest,
            "path": row["path"],
            "repository_path": f"swissknife/{row['path']}",
            "content_digest": row["content_digest"],
            "source_ref": row["source_ref"],
            "ast_record_id": row["ast_record_id"],
            "ast_ref": row["ast_ref"],
            "language": row.get("language"),
            "parser_identity": row.get("parser_identity"),
            "parser_reason": parser_reason,
            "parser_reason_sha256": (
                "sha256:" + _sha256_bytes(parser_reason.encode("utf-8"))
            ),
            "health_disposition_id": row["health_disposition"][
                "disposition_id"
            ],
            "health_reason_code": row["health_disposition"]["reason_code"],
            "official_failure_cluster_id": row[
                "official_failure_cluster_id"
            ],
            "dedupe_key": f"parser-failure/v1/{row['row_id']}",
            "receipt_path": receipt,
            "required_resolution": required_resolution,
        }
        row_entries.append(entry)
        leaves_by_nibble[nibble].append(task_id)
        tasks.append(
            _task_common(
                task_id=task_id,
                title=f"Verify parser failure {digest[:12]} for {row['path']}",
                kind=f"row-{family_name.casefold()}",
                depends_on=(family.task_id,),
                outputs=(receipt,),
                lane_index=offset,
                resource_class="cpu-small",
                resource_stage="proof",
                timeout_seconds=1800,
                interfaces=(
                    "ParserFailureRowVerification@1",
                    "ContentAddressedReceipt",
                ),
                context_budget_tokens=0,
                provider_role="deterministic-only",
                conflict_policy=(
                    "Read only the pinned row and its cluster receipt; emit "
                    "only this row's unique receipt and never invoke a model."
                ),
                preconditions=(
                    f"{family.task_id} emitted the reviewed {family_name} "
                    "cluster repair receipt."
                ),
                effects=(
                    "Records the exact fresh disposition for one pinned "
                    "path/content/parser tuple without source mutation."
                ),
                evidence_subset=(
                    f"{LOGICAL_MANIFEST} row {row['row_id']}; "
                    f"cluster receipt {family.receipt_path}"
                ),
                acceptance=(
                    "A deterministic receipt binds the pinned row ID, path, "
                    "content digest, source/AST references, parser identity, "
                    "cluster receipt, and fresh index identity. "
                    f"{resolution_acceptance} No model or provider call occurs."
                ),
                extra={
                    "Dedupe key": entry["dedupe_key"],
                    "Failure family": family_name,
                    "Failure row id": str(row["row_id"]),
                    "Failure path": str(row["path"]),
                    "Failure content digest": str(row["content_digest"]),
                    "Official failure cluster": str(
                        row["official_failure_cluster_id"]
                    ),
                    "Required resolution": required_resolution,
                    "Runtime model calls": "0",
                    "Manifest": LOGICAL_MANIFEST,
                },
            )
        )

    gates: list[dict[str, Any]] = []
    for nibble_value in range(16):
        nibble = format(nibble_value, "X")
        task_id = f"SCA-{496 + nibble_value:03d}"
        dependencies = leaves_by_nibble[nibble]
        _fail(
            0 < len(dependencies) <= MAX_GATE_FAN_IN,
            f"nibble {nibble} gate fan-in is outside 1..{MAX_GATE_FAN_IN}",
        )
        receipt = (
            "data/agent_supervisor/swissknife_contract_assurance/"
            f"parser-failures/gates/{nibble.casefold()}.json"
        )
        gates.append(
            {
                "task_id": task_id,
                "nibble": nibble,
                "leaf_count": len(dependencies),
                "leaf_task_ids": list(dependencies),
                "receipt_path": receipt,
            }
        )
        tasks.append(
            _task_common(
                task_id=task_id,
                title=(
                    f"Fan in parser-failure row receipts for digest nibble "
                    f"{nibble}"
                ),
                kind="nibble-gate",
                depends_on=dependencies,
                outputs=(receipt,),
                lane_index=nibble_value,
                resource_class="cpu-small",
                resource_stage="proof",
                timeout_seconds=1800,
                interfaces=(
                    "ParserFailureNibbleGate@1",
                    "ContentAddressedReceipt",
                ),
                context_budget_tokens=0,
                provider_role="deterministic-only",
                conflict_policy=(
                    "Read exactly the assigned first-nibble row receipts and "
                    "emit only this gate receipt; never inspect source or call "
                    "a model."
                ),
                preconditions=(
                    f"All {len(dependencies)} row receipts assigned to "
                    f"nibble {nibble} are authoritative."
                ),
                effects=(
                    f"Proves exact set equality for the {len(dependencies)} "
                    f"row IDs whose full digest begins with {nibble}."
                ),
                evidence_subset=(
                    f"{LOGICAL_MANIFEST} nibble gate {nibble} and its exact "
                    "leaf task list"
                ),
                acceptance=(
                    "The gate receipt contains every and only the manifest "
                    "rows assigned to this first digest nibble, has no duplicate "
                    "row/content identity, and records zero model calls."
                ),
                extra={
                    "Digest nibble": nibble,
                    "Leaf count": str(len(dependencies)),
                    "Runtime model calls": "0",
                    "Manifest": LOGICAL_MANIFEST,
                },
            )
        )

    aggregate_receipt = (
        "data/agent_supervisor/swissknife_contract_assurance/"
        "parser-failures/aggregate.json"
    )
    fresh_index_root = (
        "data/agent_supervisor/swissknife_contract_assurance/"
        "parser-failures/fresh-full-index"
    )
    tasks.append(
        _task_common(
            task_id="SCA-512",
            title="Prove exact 258-row closure and fresh parser health",
            kind="aggregate-gate",
            depends_on=tuple(item["task_id"] for item in gates),
            outputs=(aggregate_receipt, fresh_index_root),
            lane_index=0,
            resource_class="cpu-large",
            resource_stage="proof",
            timeout_seconds=28800,
            interfaces=(
                "ParserFailureAggregateGate@1",
                "PolyglotASTHealthReport",
                "ContentAddressedReceipt",
            ),
            context_budget_tokens=0,
            provider_role="deterministic-only",
            conflict_policy=(
                "Materialize a fresh full repository index in the declared "
                "output root with reviewed thresholds; never assume or copy "
                "an existing output, reuse the retained audit as the result, "
                "skip extraction, weaken the 10/0.01 gate, or call a model."
            ),
            preconditions=(
                "All 16 first-nibble gates prove exact, disjoint row sets "
                "covering the manifest population."
            ),
            effects=(
                "Proves exact set equality for all 258 retained failures and "
                "materializes and binds their closure to one fresh full "
                "repository index and analyzer-health receipt."
            ),
            evidence_subset=(
                f"{LOGICAL_MANIFEST}; 16 nibble gate receipts; fresh "
                "repository index, AST index, snapshot and analyzer health"
            ),
            acceptance=(
                "The 16 gates are disjoint and union to exactly the 258 "
                "manifest row IDs; SCA-512 itself creates the declared fresh "
                "full index from source with no pre-existing-output shortcut. "
                "Every fresh parser failure must be an explicitly retained "
                "bounded-failure row named by an authoritative row receipt, "
                "the complete fresh failure set must equal that receipted set, "
                "and every new, unreceipted, or out-of-manifest parser failure "
                "fails the gate even when aggregate count and ratio remain at "
                "most 10 and 0.01. Every prior path has a current typed "
                "disposition, identities decode and rehash exactly, and the "
                "execution receipt proves zero model or provider calls."
            ),
            extra={
                "Failure row count": str(EXPECTED_FAILURE_COUNT),
                "Nibble gate count": "16",
                "Fresh full index output": fresh_index_root,
                "Runtime model calls": "0",
                "Manifest": LOGICAL_MANIFEST,
            },
        )
    )
    return tasks, row_entries


def _csv(values: Iterable[Any]) -> str:
    return ", ".join(
        " ".join(str(value).split())
        for value in values
        if " ".join(str(value).split())
    )


def _one_line(value: Any) -> str:
    return " ".join(str(value or "").split())


def _render_task(task: Mapping[str, Any], *, status: str = "todo") -> str:
    lines = [
        f"## {task['task_id']} {_one_line(task['title'])}",
        "",
        f"- Status: {status}",
        f"- Priority: {task['priority']}",
        f"- Track: {task['track']}",
        f"- Depends on: {_csv(task['depends_on'])}",
        f"- Goal id: {task['goal_id']}",
        f"- Outputs: {_csv(task['outputs'])}",
        f"- Validation: {task['validation']}",
        f"- Board namespace: {task['board_namespace']}",
        f"- Bundle: {task['bundle']}",
        f"- Parallel lane: {task['parallel_lane']}",
        f"- Resource class: {task['resource_class']}",
        f"- Resource stage: {task['resource_stage']}",
        (
            "- Implementation timeout seconds: "
            f"{task['implementation_timeout_seconds']}"
        ),
        f"- Predicted files: {_csv(task['predicted_files'])}",
        f"- Interfaces: {_csv(task['interfaces'])}",
        f"- Context budget tokens: {task['context_budget_tokens']}",
        f"- Provider role: {task['provider_role']}",
    ]
    for key, value in task.get("extra", {}).items():
        lines.append(f"- {key}: {_one_line(value)}")
    lines.extend(
        [
            f"- Conflict policy: {_one_line(task['conflict_policy'])}",
            f"- Preconditions: {_one_line(task['preconditions'])}",
            f"- Effects: {_one_line(task['effects'])}",
            f"- Evidence subset: {_one_line(task['evidence_subset'])}",
            f"- Acceptance: {_one_line(task['acceptance'])}",
        ]
    )
    return "\n".join(lines)


def _render_section(
    tasks: Sequence[Mapping[str, Any]],
    *,
    statuses: Mapping[str, str] | None = None,
) -> str:
    selected_statuses = dict(statuses or {})
    blocks = [
        SECTION_START,
        "",
        (
            "The following tasks are a deterministic projection of "
            f"`{LOGICAL_MANIFEST}`. Mutable task status is preserved on "
            "regeneration; identities, dependencies, scopes and acceptance "
            "contracts are not."
        ),
        "",
    ]
    allowed = {"todo", "in_progress", "completed", "blocked"}
    for task in tasks:
        status = selected_statuses.get(str(task["task_id"]), "todo")
        _fail(
            status in allowed,
            f"generated task {task['task_id']} has invalid status {status!r}",
        )
        blocks.extend([_render_task(task, status=status), ""])
    blocks.append(SECTION_END)
    return "\n".join(blocks)


def _split_generated_section(board: str) -> tuple[str, str]:
    starts = board.count(SECTION_START)
    ends = board.count(SECTION_END)
    _fail(
        (starts, ends) in {(0, 0), (1, 1)},
        "taskboard has malformed or duplicate generated-section markers",
    )
    if not starts:
        return board, ""
    start = board.index(SECTION_START)
    end = board.index(SECTION_END, start) + len(SECTION_END)
    return board[:start] + board[end:], board[start:end]


def _generated_statuses(section: str) -> dict[str, str]:
    if not section:
        return {}
    statuses: dict[str, str] = {}
    matches = list(HEADER_RE.finditer(section))
    for index, match in enumerate(matches):
        task_id = match.group("task_id")
        end = matches[index + 1].start() if index + 1 < len(matches) else len(
            section
        )
        block = section[match.end() : end]
        status_match = re.search(
            r"^- Status:[ \t]*(?P<status>[^\n]+)$", block, re.MULTILINE
        )
        _fail(
            status_match is not None,
            f"generated task {task_id} has no Status field",
        )
        statuses[task_id] = status_match.group("status").strip()
    return statuses


def _replace_sca225_dependency(board: str) -> str:
    match = re.search(
        r"(?ms)^## SCA-225\b.*?(?=^## SCA-[0-9]{3}\b|\Z)", board
    )
    _fail(match is not None, "taskboard does not contain SCA-225")
    block = match.group(0)
    dep_match = re.search(
        r"(?m)^- Depends on:[ \t]*(?P<deps>[^\n]*)$", block
    )
    _fail(dep_match is not None, "SCA-225 has no dependency field")
    dependencies = [
        item.strip()
        for item in dep_match.group("deps").split(",")
        if item.strip()
    ]
    has_old = "SCA-231" in dependencies
    has_new = "SCA-512" in dependencies
    _fail(
        has_old != has_new,
        "SCA-225 must depend on exactly one of SCA-231 or SCA-512",
    )
    if has_old:
        dependencies = [
            "SCA-512" if item == "SCA-231" else item for item in dependencies
        ]
    replacement = "- Depends on: " + ", ".join(dependencies)
    updated_block = (
        block[: dep_match.start()]
        + replacement
        + block[dep_match.end() :]
    )
    return board[: match.start()] + updated_block + board[match.end() :]


def _metadata_for_blocks(board: str) -> dict[str, dict[str, str]]:
    matches = list(HEADER_RE.finditer(board))
    tasks: dict[str, dict[str, str]] = {}
    for index, match in enumerate(matches):
        task_id = match.group("task_id")
        _fail(task_id not in tasks, f"taskboard repeats {task_id}")
        end = matches[index + 1].start() if index + 1 < len(matches) else len(
            board
        )
        metadata: dict[str, str] = {}
        for line in board[match.end() : end].splitlines():
            stripped = line.strip()
            if stripped.startswith("- ") and ":" in stripped:
                key, value = stripped[2:].split(":", 1)
                metadata[key.strip().casefold()] = value.strip()
        tasks[task_id] = metadata
    return tasks


def _path_overlap(left: str, right: str) -> bool:
    left_parts = Path(left).parts
    right_parts = Path(right).parts
    common = min(len(left_parts), len(right_parts))
    return left_parts[:common] == right_parts[:common]


def _validate_board_graph(
    board: str, generated_tasks: Sequence[Mapping[str, Any]]
) -> dict[str, int]:
    metadata = _metadata_for_blocks(board)
    generated_ids = {str(task["task_id"]) for task in generated_tasks}
    _fail(
        generated_ids == {f"SCA-{number:03d}" for number in range(232, 513)},
        "generated task IDs are not the contiguous SCA-232..SCA-512 range",
    )
    _fail(
        generated_ids <= set(metadata),
        "taskboard omits one or more generated tasks",
    )
    dependencies: dict[str, list[str]] = {}
    for task_id, fields in metadata.items():
        dependencies[task_id] = [
            item.strip()
            for item in fields.get("depends on", "").split(",")
            if item.strip()
        ]
    missing = sorted(
        {
            dependency
            for values in dependencies.values()
            for dependency in values
            if dependency not in metadata
        }
    )
    _fail(not missing, f"taskboard has missing dependencies: {missing}")
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(task_id: str) -> None:
        _fail(task_id not in visiting, f"dependency cycle reaches {task_id}")
        if task_id in visited:
            return
        visiting.add(task_id)
        for dependency in dependencies[task_id]:
            visit(dependency)
        visiting.remove(task_id)
        visited.add(task_id)

    for task_id in sorted(metadata):
        visit(task_id)

    ancestors: dict[str, set[str]] = {}

    def find_ancestors(task_id: str) -> set[str]:
        if task_id not in ancestors:
            result: set[str] = set()
            for dependency in dependencies[task_id]:
                result.add(dependency)
                result.update(find_ancestors(dependency))
            ancestors[task_id] = result
        return ancestors[task_id]

    active = {
        task_id
        for task_id, fields in metadata.items()
        if fields.get("status", "todo").casefold()
        not in {"completed", "blocked"}
    }
    predicted: dict[str, list[str]] = {}
    for task_id in active:
        fields = metadata[task_id]
        predicted[task_id] = [
            item.strip()
            for item in fields.get("predicted files", "").split(",")
            if item.strip()
        ]
        _fail(
            fields.get("parallel lane") and predicted[task_id],
            f"active task {task_id} lacks parallel metadata",
        )
    active_ids = sorted(active)
    overlaps: list[str] = []
    for offset, left_id in enumerate(active_ids):
        for right_id in active_ids[offset + 1 :]:
            if (
                left_id in find_ancestors(right_id)
                or right_id in find_ancestors(left_id)
            ):
                continue
            if any(
                _path_overlap(left, right)
                for left in predicted[left_id]
                for right in predicted[right_id]
            ):
                overlaps.append(f"{left_id}/{right_id}")
    _fail(
        not overlaps,
        "unordered active task write scopes overlap: " + ", ".join(overlaps),
    )
    generated_lanes = {
        metadata[task_id].get("parallel lane", "")
        for task_id in generated_ids
    }
    _fail(
        generated_lanes == set(LANES),
        "generated tasks do not use exactly four deterministic lane labels",
    )
    generated_edges = sum(
        len(dependencies[task_id]) for task_id in generated_ids
    )
    max_fan_in = max(len(dependencies[task_id]) for task_id in generated_ids)
    _fail(
        generated_edges == 544,
        f"generated dependency edge count is {generated_edges}, expected 544",
    )
    _fail(
        max_fan_in <= MAX_GATE_FAN_IN,
        f"generated max fan-in {max_fan_in} exceeds {MAX_GATE_FAN_IN}",
    )
    return {
        "task_count": len(metadata),
        "generated_task_count": len(generated_ids),
        "dependency_edge_count": sum(map(len, dependencies.values())),
        "generated_dependency_edge_count": generated_edges,
        "generated_max_fan_in": max_fan_in,
        "active_unordered_overlap_count": len(overlaps),
        "generated_lane_count": len(generated_lanes),
    }


def _build_expected_board(
    current: str,
    tasks: Sequence[Mapping[str, Any]],
) -> tuple[str, dict[str, str]]:
    base, old_section = _split_generated_section(current)
    statuses = _generated_statuses(old_section)
    generated_ids = {str(task["task_id"]) for task in tasks}
    _fail(
        set(statuses) <= generated_ids,
        "existing generated section contains an unexpected task ID",
    )
    outside_ids = {match.group("task_id") for match in HEADER_RE.finditer(base)}
    collisions = sorted(outside_ids & generated_ids)
    _fail(
        not collisions,
        f"generated task IDs already exist outside markers: {collisions}",
    )
    normalized_base = _replace_sca225_dependency(base).rstrip()
    section = _render_section(tasks, statuses=statuses)
    return normalized_base + "\n\n" + section + "\n", statuses


def _manifest_envelope(payload: Mapping[str, Any]) -> dict[str, Any]:
    canonical = _canonical_json_bytes(payload)
    digest = _sha256_bytes(canonical)
    return {
        "schema": MANIFEST_SCHEMA,
        "content_identity": {
            "subject": "payload",
            "canonicalization": "json-sort-keys-utf8-no-whitespace-v1",
            "byte_length": len(canonical),
            "digest": f"sha256:{digest}",
            "cid": _cid_v1_dag_json_from_digest(bytes.fromhex(digest)),
            "cid_version": 1,
            "multibase": "base32",
            "multicodec": "dag-json",
            "multihash": "sha2-256",
        },
        "payload": payload,
    }


def _build_projection(
    index_path: Path, health_path: Path
) -> tuple[list[dict[str, Any]], dict[str, Any], bytes]:
    index, health, failure_rows = _validate_sources(index_path, health_path)
    tasks, row_entries = _build_tasks(failure_rows)
    _fail(
        len(tasks) == 281 and len(row_entries) == EXPECTED_FAILURE_COUNT,
        "generated task or row population is incorrect",
    )
    gates = [
        {
            "task_id": task["task_id"],
            "nibble": task["extra"]["Digest nibble"],
            "leaf_count": int(task["extra"]["Leaf count"]),
            "leaf_task_ids": list(task["depends_on"]),
            "receipt_path": task["outputs"][0],
        }
        for task in tasks
        if task["kind"] == "nibble-gate"
    ]
    gate_counts = {
        item["nibble"]: item["leaf_count"] for item in gates
    }
    _fail(
        gate_counts
        == {
            "0": 19,
            "1": 18,
            "2": 24,
            "3": 15,
            "4": 10,
            "5": 16,
            "6": 16,
            "7": 11,
            "8": 12,
            "9": 14,
            "A": 18,
            "B": 15,
            "C": 18,
            "D": 14,
            "E": 20,
            "F": 18,
        },
        f"retained first-nibble population changed: {gate_counts}",
    )
    canonical_section = _render_section(tasks)
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "board_namespace": BOARD_NAMESPACE,
        "goal_id": GOAL_ID,
        "source_artifacts": {
            "repository_index": {
                "logical_path": LOGICAL_INDEX,
                "file_sha256": "sha256:" + _sha256_file(index_path),
                "schema": index["schema"],
                "index_id": index["index_id"],
                "ast_index_id": index["ast_index_id"],
                "snapshot_id": index["snapshot"]["snapshot_id"],
                "snapshot_commit": index["snapshot"]["head_commit_id"],
                "parser_identity": failure_rows[0]["parser_identity"],
            },
            "analyzer_health": {
                "logical_path": LOGICAL_HEALTH,
                "file_sha256": "sha256:" + _sha256_file(health_path),
                "schema": health["schema"],
                "content_identity": health["content_identity"],
                "status": health["status"],
                "failure_count": health["metrics"][
                    "bounded_failure_count"
                ],
                "cluster_count": health["metrics"]["cluster_count"],
            },
        },
        "projection": {
            "todo_logical_path": LOGICAL_TODO,
            "manifest_logical_path": LOGICAL_MANIFEST,
            "task_id_min": "SCA-232",
            "task_id_max": "SCA-512",
            "cluster_task_count": 6,
            "row_task_count": EXPECTED_FAILURE_COUNT,
            "nibble_gate_task_count": 16,
            "aggregate_task_count": 1,
            "generated_task_count": len(tasks),
            "generated_dependency_edge_count": sum(
                len(task["depends_on"]) for task in tasks
            ),
            "max_dependency_fan_in": max(
                len(task["depends_on"]) for task in tasks
            ),
            "parallel_lanes": list(LANES),
            "canonical_task_section_sha256": (
                "sha256:"
                + _sha256_bytes(canonical_section.encode("utf-8"))
            ),
            "sca_225_dependency_replaced": {
                "removed": "SCA-231",
                "added": "SCA-512",
            },
        },
        "families": [
            {
                "name": family.name,
                "task_id": family.task_id,
                "failure_count": family.expected_count,
                "source_scopes": list(family.source_scopes),
                "receipt_path": family.receipt_path,
            }
            for family in FAMILIES
        ],
        "rows": row_entries,
        "gates": gates,
        "tasks": tasks,
    }
    envelope = _manifest_envelope(payload)
    manifest_bytes = _canonical_json_bytes(envelope) + b"\n"
    return tasks, envelope, manifest_bytes


def _validate_manifest_envelope(value: Mapping[str, Any]) -> None:
    _fail(value.get("schema") == MANIFEST_SCHEMA, "manifest schema is invalid")
    payload = value.get("payload")
    identity = value.get("content_identity")
    _fail(
        isinstance(payload, dict) and isinstance(identity, dict),
        "manifest envelope is incomplete",
    )
    canonical = _canonical_json_bytes(payload)
    digest = _sha256_bytes(canonical)
    _fail(
        identity.get("subject") == "payload"
        and identity.get("digest") == f"sha256:{digest}"
        and identity.get("byte_length") == len(canonical)
        and identity.get("cid")
        == _cid_v1_dag_json_from_digest(bytes.fromhex(digest))
        and identity.get("cid_version") == 1
        and identity.get("multibase") == "base32"
        and identity.get("multicodec") == "dag-json"
        and identity.get("multihash") == "sha2-256",
        "manifest content identity is invalid",
    )


def _atomic_write(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = 0o644
    try:
        mode = stat.S_IMODE(path.stat().st_mode)
    except FileNotFoundError:
        pass
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    try:
        with temporary.open("wb") as stream:
            stream.write(value)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _summary(
    *,
    envelope: Mapping[str, Any],
    board_stats: Mapping[str, int],
    statuses: Mapping[str, str],
    manifest_bytes: bytes,
) -> dict[str, Any]:
    identity = envelope["content_identity"]
    return {
        "schema": SCHEMA,
        "failure_rows": EXPECTED_FAILURE_COUNT,
        "families": EXPECTED_FAMILY_COUNTS,
        "generated_tasks": 281,
        "generated_dependency_edges": 544,
        "nibble_gates": 16,
        "max_fan_in": board_stats["generated_max_fan_in"],
        "parallel_lanes": list(LANES),
        "unordered_overlap_count": board_stats[
            "active_unordered_overlap_count"
        ],
        "board_task_count": board_stats["task_count"],
        "board_dependency_edges": board_stats["dependency_edge_count"],
        "preserved_status_count": len(statuses),
        "manifest_payload_sha256": identity["digest"],
        "manifest_payload_cid": identity["cid"],
        "manifest_file_sha256": "sha256:" + _sha256_bytes(manifest_bytes),
    }


def _select_task(
    task_id: str | None, tasks: Sequence[Mapping[str, Any]]
) -> None:
    if not task_id:
        return
    _fail(
        task_id in {str(task["task_id"]) for task in tasks},
        f"{task_id} is not a generated SCA-232..SCA-512 task",
    )


def command_materialize(args: argparse.Namespace) -> dict[str, Any]:
    tasks, envelope, manifest_bytes = _build_projection(
        args.index, args.health_report
    )
    try:
        current = args.todo.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise BacklogError(f"cannot read {args.todo}: {exc}") from exc
    board, statuses = _build_expected_board(current, tasks)
    board_stats = _validate_board_graph(board, tasks)
    _validate_manifest_envelope(envelope)
    _atomic_write(args.manifest, manifest_bytes)
    _atomic_write(args.todo, board.encode("utf-8"))
    return _summary(
        envelope=envelope,
        board_stats=board_stats,
        statuses=statuses,
        manifest_bytes=manifest_bytes,
    )


def command_check(args: argparse.Namespace) -> dict[str, Any]:
    tasks, envelope, manifest_bytes = _build_projection(
        args.index, args.health_report
    )
    _select_task(args.task_id, tasks)
    try:
        current_board = args.todo.read_text(encoding="utf-8")
        current_manifest = args.manifest.read_bytes()
    except (OSError, UnicodeError) as exc:
        raise BacklogError(f"cannot read generated projection: {exc}") from exc
    expected_board, statuses = _build_expected_board(current_board, tasks)
    _fail(
        current_board.encode("utf-8") == expected_board.encode("utf-8"),
        (
            "taskboard differs from deterministic regeneration "
            f"(current sha256:{_sha256_bytes(current_board.encode('utf-8'))}, "
            f"expected sha256:{_sha256_bytes(expected_board.encode('utf-8'))})"
        ),
    )
    _fail(
        current_manifest == manifest_bytes,
        (
            "manifest differs from deterministic regeneration "
            f"(current sha256:{_sha256_bytes(current_manifest)}, "
            f"expected sha256:{_sha256_bytes(manifest_bytes)})"
        ),
    )
    parsed_manifest = _load_json_object(args.manifest)
    _validate_manifest_envelope(parsed_manifest)
    board_stats = _validate_board_graph(current_board, tasks)
    return _summary(
        envelope=envelope,
        board_stats=board_stats,
        statuses=statuses,
        manifest_bytes=manifest_bytes,
    )


def _common_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    parser.add_argument(
        "--health-report", type=Path, default=DEFAULT_HEALTH
    )
    parser.add_argument("--todo", type=Path, default=DEFAULT_TODO)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    materialize = subparsers.add_parser(
        "materialize",
        help="atomically update the manifest and generated board section",
    )
    _common_arguments(materialize)
    materialize.set_defaults(handler=command_materialize)
    check = subparsers.add_parser(
        "check",
        help="prove the manifest and board equal deterministic regeneration",
    )
    _common_arguments(check)
    check.add_argument(
        "--task-id",
        help="also assert that one SCA-232..SCA-512 task is in the projection",
    )
    check.set_defaults(handler=command_check)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = args.handler(args)
    except BacklogError as exc:
        parser.exit(2, f"error: {exc}\n")
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
