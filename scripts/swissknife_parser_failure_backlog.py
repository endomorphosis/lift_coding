#!/usr/bin/env python3
"""Materialize and verify the exact SwissKnife parser-failure backlog.

The retained repository index is the source of failure-row authority.  This
tool converts that authority into a compact content-addressed manifest and a
marker-delimited supervisor taskboard section without consulting a model.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping


SCHEMA = "ipfs_accelerate_py/agent-supervisor/parser-failure-backlog@1"
RECEIPT_SCHEMA = (
    "ipfs_accelerate_py/agent-supervisor/parser-failure-resolution-receipt@1"
)
BEGIN_MARKER = "<!-- BEGIN GENERATED SCA PARSER FAILURE BACKLOG V1 -->"
END_MARKER = "<!-- END GENERATED SCA PARSER FAILURE BACKLOG V1 -->"
BOARD_NAMESPACE = "swissknife-symbolic-contract-assurance-v1"
GOAL_ID = "SCA-G022"
EXPECTED_FAILURE_COUNT = 258
INDEX_FILE_SHA256 = (
    "0f1282f349c0026b5b9037b185932cfdb13f52ffe9b29a325858a8debc0032cb"
)
INDEX_ID = (
    "sca-repository-index:sha256:"
    "bd7cd357b5bb0cac78d746b3e6f1ba6dd9f9f9451763ba28ea3015825a6491a7"
)
SNAPSHOT_ID = (
    "sca-repository-snapshot:sha256:"
    "d092867b88fc3f921d98c235298c4fdf1e928b29e564de68f619db258bdfbfcb"
)
AST_INDEX_ID = (
    "analysis-ast-index:sha256:"
    "907cc301da1ef80df8a43fce30d76ac083585ca0317db5c8e152281032f775d7"
)
PARSER_ID = (
    "sca-repository-parser:sha256:"
    "5004a038a1761125ab16ce2510262a3b18f687213d25fab342e89cac6439c284"
)
HEALTH_CID = "baguqeerawrhoccwxhu6fd53adibcpkv26lqrj5e6hvd2ro3ntqwt5ji5pn3q"
HEALTH_DIGEST = (
    "sha256:b44ee10ad73d3c51f7601a0227aabaf2e114f49e3d47a8bb6d9c2d3ea51d7b77"
)
MANIFEST_DEFAULT = Path(
    "implementation_plan/conformance/swissknife-parser-failure-backlog-v1.json"
)
INDEX_DEFAULT = Path(
    "data/agent_supervisor/swissknife_contract_assurance/"
    "audit/current-index-20260729/repository-index.json"
)
HEALTH_DEFAULT = Path(
    "data/agent_supervisor/swissknife_contract_assurance/"
    "audit/unsafe-publication-20260729T171543Z/analyzer_health/report.json"
)
TODO_DEFAULT = Path(
    "implementation_plan/docs/"
    "44-swissknife-symbolic-contract-assurance.todo.md"
)
RECEIPT_ROOT = (
    "data/agent_supervisor/swissknife_contract_assurance/parser-failures"
)


class BacklogError(RuntimeError):
    """Raised when retained evidence or generated backlog data is inconsistent."""


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_text(value: str) -> str:
    return _sha256_bytes(value.encode("utf-8"))


def _cid_for_bytes(value: bytes) -> str:
    try:
        from multiformats import CID, multihash
    except ImportError as exc:  # pragma: no cover - environment gate
        raise BacklogError(
            "multiformats is required to mint the strict DAG-JSON CID"
        ) from exc
    return str(CID("base32", 1, "dag-json", multihash.digest(value, "sha2-256")))


def _identity(value: Any) -> dict[str, Any]:
    canonical = _canonical_bytes(value)
    return {
        "canonical_subject": "payload",
        "profile": "strict-dag-json-v1",
        "canonicalization": "json-sort-keys-compact-utf8",
        "byte_length": len(canonical),
        "digest": "sha256:" + _sha256_bytes(canonical),
        "cid": _cid_for_bytes(canonical),
        "cid_version": 1,
        "multibase": "base32",
        "multicodec": "dag-json",
        "multihash": "sha2-256",
    }


def _envelope(payload: dict[str, Any], *, schema: str = SCHEMA) -> dict[str, Any]:
    return {
        "schema": schema,
        "content_identity": _identity(payload),
        "payload": payload,
    }


def _read_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BacklogError(f"cannot read JSON object {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise BacklogError(f"{path} must contain a JSON object")
    return value


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _digest_part(value: str) -> str:
    digest = value.rsplit(":", 1)[-1].lower()
    if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
        raise BacklogError(f"expected a full SHA-256 identity, got {value!r}")
    return digest


def _family(path: str) -> str:
    active_js = {
        "ipfs_accelerate_js/src/utils/run_web_platform_integration_tests.js",
        "test/mocks/stubs/chai-stub.js",
        "test/unit/cli/chat-command.test.js",
        "test/utils/mockMCPClient.js",
    }
    python_paths = {
        "ipfs_accelerate_js/test/performance/webgpu_optimizer/run_benchmarks.py",
        "test/fixed_web_platform/cross_browser_model_sharding.py",
        "test/web_platform_test_output/test_hf_bert.py",
    }
    structured = {
        "benchmark-results/sample-baseline.json",
        "docs/ast_exports/full_asts/python/swissknife_old/"
        "ipfs_transformers.py.ast.json",
    }
    if path.startswith("ipfs_accelerate_js/test/unit/"):
        return "UNIT"
    if path.startswith("ipfs_accelerate_js/test/browser/"):
        return "BROWSER"
    if path in active_js:
        return "ACTIVEJS"
    if path in python_paths:
        return "PYTHON"
    if path in structured:
        return "STRUCTURED"
    if path.startswith("web/legacy-archive/"):
        return "LEGACY"
    raise BacklogError(f"unclassified parser failure path: {path}")


CLUSTERS: tuple[dict[str, Any], ...] = (
    {
        "family": "UNIT",
        "task_id": "SCA-232",
        "title": "Repair converted unit-test parser failures without exclusions",
        "lane": "sca-parser-failure-unit",
        "source_scopes": ["swissknife/ipfs_accelerate_js/test/unit"],
        "acceptance": (
            "Repair or deterministically regenerate every retained unit-test "
            "path. Prefix exclusions are forbidden because these tests include "
            "scheduler and expected-behavior contract evidence."
        ),
    },
    {
        "family": "BROWSER",
        "task_id": "SCA-233",
        "title": "Repair converted browser-test parser failures",
        "lane": "sca-parser-failure-browser",
        "source_scopes": ["swissknife/ipfs_accelerate_js/test/browser"],
        "acceptance": (
            "Repair or deterministically regenerate all nine browser tests and "
            "retain their behavior assertions as indexed contract evidence."
        ),
    },
    {
        "family": "ACTIVEJS",
        "task_id": "SCA-234",
        "title": "Repair active JavaScript and content-routing parser failures",
        "lane": "sca-parser-failure-active-js",
        "source_scopes": [
            "swissknife/ipfs_accelerate_js/src/utils/"
            "run_web_platform_integration_tests.js",
            "swissknife/test/mocks/stubs/chai-stub.js",
            "swissknife/test/unit/cli/chat-command.test.js",
            "swissknife/test/utils/mockMCPClient.js",
            "external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/"
            "analysis/polyglot_ast_provider.py",
            "external/ipfs_accelerate/test/api/"
            "test_agent_supervisor_polyglot_ast_provider.py",
        ],
        "acceptance": (
            "Use content/shebang-aware routing for the shell program and real "
            "parser success for the three JavaScript tests; the MCP client mock "
            "may not be excluded or treated as non-contract evidence."
        ),
    },
    {
        "family": "PYTHON",
        "task_id": "SCA-235",
        "title": "Repair Python failures and classify semantic-looking symlinks",
        "lane": "sca-parser-failure-python",
        "source_scopes": [
            "swissknife/ipfs_accelerate_js/test/performance/webgpu_optimizer/"
            "run_benchmarks.py",
            "swissknife/test/fixed_web_platform/"
            "cross_browser_model_sharding.py",
            "swissknife/test/web_platform_test_output/test_hf_bert.py",
            "external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/"
            "analysis/repository_snapshot.py",
            "external/ipfs_accelerate/test/api/"
            "test_agent_supervisor_repository_snapshot.py",
        ],
        "acceptance": (
            "Classify EntryKind.SYMLINK before suffix routing and add positive "
            "and negative fixtures for all ten semantic-looking symlinks; fix "
            "the two real indentation defects."
        ),
    },
    {
        "family": "STRUCTURED",
        "task_id": "SCA-236",
        "title": "Repair or explicitly type structured-data parser failures",
        "lane": "sca-parser-failure-structured",
        "source_scopes": [
            "swissknife/benchmark-results/sample-baseline.json",
            "swissknife/docs/ast_exports/full_asts/python/swissknife_old/"
            "ipfs_transformers.py.ast.json",
        ],
        "acceptance": (
            "Make the empty JSON valid and give the oversized generated AST a "
            "reviewed non-excluded typed disposition or a bounded parse path."
        ),
    },
    {
        "family": "LEGACY",
        "task_id": "SCA-237",
        "title": "Repair legacy-archive JavaScript parser failures",
        "lane": "sca-parser-failure-legacy",
        "source_scopes": ["swissknife/web/legacy-archive"],
        "acceptance": (
            "Repair all eight retained legacy files or record a reviewed "
            "per-path non-excluded disposition; no directory-wide exclusion."
        ),
    },
)
CLUSTER_BY_FAMILY = {item["family"]: item for item in CLUSTERS}


def _official_cluster_map(health: Mapping[str, Any]) -> dict[tuple[str, str], str]:
    result: dict[tuple[str, str], str] = {}
    for raw in health.get("clusters", []):
        if not isinstance(raw, Mapping):
            continue
        key = (str(raw.get("language") or ""), str(raw.get("reason_code") or ""))
        cluster_id = str(raw.get("cluster_id") or "")
        if not all(key) or not cluster_id or key in result:
            raise BacklogError("health report contains malformed/duplicate clusters")
        result[key] = cluster_id
    if len(result) != 6:
        raise BacklogError(f"expected 6 official health clusters, found {len(result)}")
    return result


def build_payload(index_path: Path, health_path: Path) -> dict[str, Any]:
    index_bytes = index_path.read_bytes()
    if _sha256_bytes(index_bytes) != INDEX_FILE_SHA256:
        raise BacklogError("repository index bytes do not match pinned SHA-256")
    index = _read_object(index_path)
    health = _read_object(health_path)
    if index.get("index_id") != INDEX_ID:
        raise BacklogError("repository index identity does not match pinned index")
    snapshot = index.get("snapshot")
    if not isinstance(snapshot, Mapping) or snapshot.get("snapshot_id") != SNAPSHOT_ID:
        raise BacklogError("repository snapshot identity does not match pinned snapshot")
    if index.get("ast_index_id") != AST_INDEX_ID:
        raise BacklogError("AST index identity does not match pinned AST index")
    health_identity = health.get("content_identity")
    if (
        not isinstance(health_identity, Mapping)
        or health_identity.get("cid") != HEALTH_CID
        or health_identity.get("digest") != HEALTH_DIGEST
    ):
        raise BacklogError("analyzer-health identity does not match pinned evidence")

    failure_rows = [
        row
        for row in index.get("rows", [])
        if isinstance(row, Mapping) and row.get("parser_status") == "parse_failure"
    ]
    health_failures = [
        item
        for item in health.get("dispositions", [])
        if isinstance(item, Mapping)
        and item.get("parser_status") == "parse_failure"
    ]
    if len(failure_rows) != EXPECTED_FAILURE_COUNT:
        raise BacklogError(
            f"expected {EXPECTED_FAILURE_COUNT} failure rows, found {len(failure_rows)}"
        )
    if len(health_failures) != EXPECTED_FAILURE_COUNT:
        raise BacklogError(
            "analyzer-health report does not contain exactly 258 failures"
        )

    by_health_path = {str(item["path"]): item for item in health_failures}
    if len(by_health_path) != EXPECTED_FAILURE_COUNT:
        raise BacklogError("analyzer-health failure paths are not unique")
    official_clusters = _official_cluster_map(health)
    sorted_rows = sorted(failure_rows, key=lambda row: _digest_part(str(row["row_id"])))
    seen: dict[str, set[str]] = {
        "path": set(),
        "row_id": set(),
        "content_digest": set(),
        "ast_record_id": set(),
        "source_digest": set(),
        "ast_digest": set(),
    }
    rows: list[dict[str, Any]] = []
    family_counts: Counter[str] = Counter()
    official_counts: Counter[str] = Counter()
    for offset, row in enumerate(sorted_rows):
        path = str(row.get("path") or "")
        disposition = by_health_path.get(path)
        if disposition is None:
            raise BacklogError(f"failure row has no health disposition: {path}")
        if row.get("parser_identity") != PARSER_ID:
            raise BacklogError(f"failure row has unexpected parser identity: {path}")
        source_ref = row.get("source_ref")
        ast_ref = row.get("ast_ref")
        if not isinstance(source_ref, Mapping) or not isinstance(ast_ref, Mapping):
            raise BacklogError(f"failure row lacks bounded CAS references: {path}")
        family = _family(path)
        health_key = (
            str(disposition.get("language") or ""),
            str(disposition.get("reason_code") or ""),
        )
        official_cluster_id = official_clusters.get(health_key)
        if not official_cluster_id:
            raise BacklogError(
                f"failure disposition has no official cluster: {path} {health_key}"
            )
        row_id = str(row.get("row_id") or "")
        row_digest = _digest_part(row_id)
        task_id = f"SCA-{238 + offset:03d}"
        item = {
            "task_id": task_id,
            "dedupe_key": f"parser-failure/v1/{row_id}",
            "row_id": row_id,
            "row_digest": row_digest,
            "path": path,
            "repository_path": f"swissknife/{path}",
            "path_disposition_id": str(disposition.get("disposition_id") or ""),
            "actionable_family": family,
            "cluster_task_id": str(CLUSTER_BY_FAMILY[family]["task_id"]),
            "official_cluster_id": official_cluster_id,
            "source_index_id": INDEX_ID,
            "snapshot_id": SNAPSHOT_ID,
            "ast_index_id": AST_INDEX_ID,
            "parser_identity": PARSER_ID,
            "parser_language": str(disposition.get("language") or ""),
            "parser_reason_code": str(disposition.get("reason_code") or ""),
            "parser_reason_sha256": "sha256:"
            + _sha256_text(str(row.get("parser_reason") or "")),
            "content_digest": str(row.get("content_digest") or ""),
            "ast_record_id": str(row.get("ast_record_id") or ""),
            "source_ref": dict(source_ref),
            "ast_ref": dict(ast_ref),
            "tracked": row.get("tracked") is True,
            "overlay": row.get("overlay") is True,
            "git_status": str(row.get("git_status") or ""),
            "policy_rule": str(row.get("policy_rule") or ""),
            "receipt_path": f"{RECEIPT_ROOT}/rows/{row_digest}.json",
            "fan_in_nibble": row_digest[0],
        }
        uniqueness = {
            "path": path,
            "row_id": row_id,
            "content_digest": item["content_digest"],
            "ast_record_id": item["ast_record_id"],
            "source_digest": str(source_ref.get("digest") or ""),
            "ast_digest": str(ast_ref.get("digest") or ""),
        }
        for name, value in uniqueness.items():
            if not value or value in seen[name]:
                raise BacklogError(f"failure {name} is missing or duplicated: {value}")
            seen[name].add(value)
        rows.append(item)
        family_counts[family] += 1
        official_counts[official_cluster_id] += 1

    expected_family_counts = {
        "UNIT": 232,
        "BROWSER": 9,
        "ACTIVEJS": 4,
        "PYTHON": 3,
        "STRUCTURED": 2,
        "LEGACY": 8,
    }
    if dict(family_counts) != expected_family_counts:
        raise BacklogError(
            f"actionable family counts drifted: {dict(family_counts)}"
        )
    reported_official_counts = {
        str(item["cluster_id"]): int(item["count"])
        for item in health["clusters"]
    }
    if dict(official_counts) != reported_official_counts:
        raise BacklogError("official cluster membership does not match health counts")

    clusters: list[dict[str, Any]] = []
    for definition in CLUSTERS:
        family = str(definition["family"])
        members = [row["task_id"] for row in rows if row["actionable_family"] == family]
        clusters.append(
            {
                **definition,
                "failure_count": len(members),
                "row_task_ids": members,
                "receipt_path": f"{RECEIPT_ROOT}/clusters/{family.lower()}.json",
                "fresh_index_path": (
                    f"{RECEIPT_ROOT}/fresh/{family.lower()}/repository-index.json"
                ),
            }
        )

    gates: list[dict[str, Any]] = []
    for offset, nibble in enumerate("0123456789abcdef"):
        members = [row["task_id"] for row in rows if row["fan_in_nibble"] == nibble]
        gates.append(
            {
                "task_id": f"SCA-{496 + offset:03d}",
                "nibble": nibble,
                "failure_count": len(members),
                "row_task_ids": members,
                "receipt_path": f"{RECEIPT_ROOT}/gates/{nibble}.json",
            }
        )
    expected_gate_counts = [19, 18, 24, 15, 10, 16, 16, 11, 12, 14, 18, 15, 18, 14, 20, 18]
    if [gate["failure_count"] for gate in gates] != expected_gate_counts:
        raise BacklogError("row-ID nibble fan-in counts drifted")

    return {
        "schema_version": 1,
        "board_namespace": BOARD_NAMESPACE,
        "goal_id": GOAL_ID,
        "source_index": {
            "path": index_path.as_posix(),
            "file_sha256": "sha256:" + INDEX_FILE_SHA256,
            "index_id": INDEX_ID,
            "snapshot_id": SNAPSHOT_ID,
            "snapshot_commit": str(snapshot.get("head_commit_id") or ""),
            "ast_index_id": AST_INDEX_ID,
            "parser_identity": PARSER_ID,
        },
        "analyzer_health": {
            "path": health_path.as_posix(),
            "cid": HEALTH_CID,
            "digest": HEALTH_DIGEST,
            "healthy": health.get("healthy") is True,
            "bounded_failure_count": EXPECTED_FAILURE_COUNT,
        },
        "counts": {
            "failure_rows": len(rows),
            "actionable_clusters": len(clusters),
            "row_tasks": len(rows),
            "fan_in_gates": len(gates),
            "aggregate_gates": 1,
            "generated_tasks": len(clusters) + len(rows) + len(gates) + 1,
        },
        "family_counts": dict(sorted(family_counts.items())),
        "official_cluster_counts": dict(sorted(official_counts.items())),
        "clusters": clusters,
        "rows": rows,
        "gates": gates,
        "aggregate": {
            "task_id": "SCA-512",
            "depends_on": [gate["task_id"] for gate in gates],
            "receipt_path": f"{RECEIPT_ROOT}/aggregate.json",
            "fresh_index_path": f"{RECEIPT_ROOT}/fresh/aggregate/repository-index.json",
        },
    }


def _csv(values: Iterable[str]) -> str:
    return ", ".join(str(value) for value in values)


def _task_block(
    *,
    task_id: str,
    title: str,
    track: str,
    depends_on: Iterable[str],
    outputs: Iterable[str],
    validation: str,
    bundle: str,
    lane: str,
    resource_class: str,
    resource_stage: str,
    timeout: int,
    predicted_files: Iterable[str],
    interfaces: str,
    context_tokens: int,
    provider_role: str,
    conflict_policy: str,
    preconditions: str,
    effects: str,
    evidence_subset: str,
    acceptance: str,
    extra: Iterable[tuple[str, str]] = (),
) -> str:
    lines = [
        f"## {task_id} {title}",
        "",
        "- Status: todo",
        "- Priority: P0",
        f"- Track: {track}",
        f"- Depends on: {_csv(depends_on)}",
        f"- Goal id: {GOAL_ID}",
        f"- Outputs: {_csv(outputs)}",
        f"- Validation: {validation}",
        f"- Board namespace: {BOARD_NAMESPACE}",
        f"- Bundle: {bundle}",
        f"- Parallel lane: {lane}",
        f"- Resource class: {resource_class}",
        f"- Resource stage: {resource_stage}",
        f"- Implementation timeout seconds: {timeout}",
        f"- Predicted files: {_csv(predicted_files)}",
        f"- Interfaces: {interfaces}",
        f"- Context budget tokens: {context_tokens}",
        f"- Provider role: {provider_role}",
    ]
    for key, value in extra:
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            f"- Conflict policy: {conflict_policy}",
            f"- Preconditions: {preconditions}",
            f"- Effects: {effects}",
            f"- Evidence subset: {evidence_subset}",
            f"- Acceptance: {acceptance}",
        ]
    )
    return "\n".join(lines)


def render_tasks(payload: Mapping[str, Any], manifest_path: Path) -> str:
    manifest = manifest_path.as_posix()
    blocks: list[str] = [BEGIN_MARKER]
    for cluster in payload["clusters"]:
        family = str(cluster["family"])
        receipt = str(cluster["receipt_path"])
        fresh = str(cluster["fresh_index_path"])
        predicted = [*cluster["source_scopes"], receipt, fresh]
        validation = (
            f"python3 scripts/swissknife_parser_failure_backlog.py verify-cluster "
            f"--manifest {manifest} --cluster {family} --fresh-index {fresh} "
            f"--receipt-out {receipt}"
        )
        blocks.append(
            _task_block(
                task_id=str(cluster["task_id"]),
                title=str(cluster["title"]),
                track="parser-failure-cluster-repair",
                depends_on=("SCA-231", "SCA-229"),
                outputs=predicted,
                validation=validation,
                bundle=f"swissknife/contract-assurance/parser-failure/{family.lower()}",
                lane=str(cluster["lane"]),
                resource_class="cpu-large",
                resource_stage="repair",
                timeout=21600,
                predicted_files=predicted,
                interfaces="ParserFailureBacklog@1, RepositoryIndexer@1",
                context_tokens=2048,
                provider_role="grok-implement, codex-review",
                extra=(
                    ("LLM context budget bytes", "12288"),
                    ("Runtime model call maximum", "1"),
                    ("Failure family", family),
                    ("Failure count", str(cluster["failure_count"])),
                ),
                conflict_policy=(
                    "Edit only the declared family/analyzer scope and its unique "
                    "receipts; never weaken health thresholds or introduce a "
                    "blanket exclusion."
                ),
                preconditions=(
                    "SCA-231 retains exact triage and SCA-229 enforces bounded "
                    "provider/completion receipts."
                ),
                effects=(
                    "Produces targeted source/analyzer repairs plus a deterministic "
                    "fresh-index resolution receipt for this family."
                ),
                evidence_subset=(
                    f"{INDEX_ID}, {SNAPSHOT_ID}, family {family}, "
                    f"{cluster['failure_count']} exact row handles"
                ),
                acceptance=str(cluster["acceptance"]),
            )
        )

    cluster_receipts = {
        str(cluster["family"]): str(cluster["receipt_path"])
        for cluster in payload["clusters"]
    }
    for row in payload["rows"]:
        task_id = str(row["task_id"])
        receipt = str(row["receipt_path"])
        family = str(row["actionable_family"])
        validation = (
            "python3 scripts/swissknife_parser_failure_backlog.py verify-row "
            f"--manifest {manifest} --task-id {task_id} "
            f"--cluster-receipt {cluster_receipts[family]} --receipt-out {receipt}"
        )
        blocks.append(
            _task_block(
                task_id=task_id,
                title=f"Verify parser-failure row {_digest_part(str(row['row_id']))[:12]}",
                track="parser-failure-row-verification",
                depends_on=(str(row["cluster_task_id"]),),
                outputs=(receipt,),
                validation=validation,
                bundle="swissknife/contract-assurance/parser-failure/row",
                lane="sca-parser-failure-row",
                resource_class="cpu-small",
                resource_stage="verification",
                timeout=900,
                predicted_files=(receipt,),
                interfaces="ParserFailureRowReceipt@1",
                context_tokens=0,
                provider_role="deterministic-only",
                extra=(
                    ("Runtime model calls", "0"),
                    ("Dedupe key", str(row["dedupe_key"])),
                    ("Failure row id", str(row["row_id"])),
                    ("Path disposition id", str(row["path_disposition_id"])),
                    ("Source index id", str(row["source_index_id"])),
                    ("Snapshot id", str(row["snapshot_id"])),
                    ("Failure path", str(row["repository_path"])),
                    ("Content digest", str(row["content_digest"])),
                    ("AST record id", str(row["ast_record_id"])),
                    ("Parser identity", str(row["parser_identity"])),
                    ("Parser reason digest", str(row["parser_reason_sha256"])),
                    ("Official cluster id", str(row["official_cluster_id"])),
                ),
                conflict_policy=(
                    "Write only this row's unique receipt; never edit source, "
                    "reclassify another row, or invoke a model."
                ),
                preconditions=(
                    "The family receipt binds a fresh index and an explicit "
                    "non-failure transition for this exact row/path."
                ),
                effects=(
                    "Projects one content-addressed family resolution into one "
                    "small independently checkable row receipt."
                ),
                evidence_subset=(
                    "Pinned row/path/content/AST/parser identities and family "
                    "resolution handle"
                ),
                acceptance=(
                    "The exact retained failure is assigned once, its fresh "
                    "resolution is explicit, and the receipt contains zero model calls."
                ),
            )
        )

    for gate in payload["gates"]:
        receipt = str(gate["receipt_path"])
        nibble = str(gate["nibble"])
        validation = (
            "python3 scripts/swissknife_parser_failure_backlog.py verify-gate "
            f"--manifest {manifest} --nibble {nibble} "
            f"--receipt-dir {RECEIPT_ROOT}/rows --receipt-out {receipt}"
        )
        blocks.append(
            _task_block(
                task_id=str(gate["task_id"]),
                title=f"Fan in parser-failure row receipts for nibble {nibble.upper()}",
                track="parser-failure-fan-in",
                depends_on=gate["row_task_ids"],
                outputs=(receipt,),
                validation=validation,
                bundle="swissknife/contract-assurance/parser-failure/fan-in",
                lane="sca-parser-failure-fan-in",
                resource_class="cpu-small",
                resource_stage="verification",
                timeout=900,
                predicted_files=(receipt,),
                interfaces="ParserFailureFanInReceipt@1",
                context_tokens=0,
                provider_role="deterministic-only",
                extra=(
                    ("Runtime model calls", "0"),
                    ("Failure row-id nibble", nibble),
                    ("Failure count", str(gate["failure_count"])),
                ),
                conflict_policy=(
                    "Read only the exact nibble's row receipts and write one unique "
                    "fan-in receipt; never invoke a model."
                ),
                preconditions="Every assigned row task for this nibble is complete.",
                effects="Proves exact membership, uniqueness, and receipt validity.",
                evidence_subset=_csv(gate["row_task_ids"]),
                acceptance=(
                    f"Exactly {gate['failure_count']} unique row receipts cover "
                    f"every and only retained row IDs beginning with {nibble}."
                ),
            )
        )

    aggregate = payload["aggregate"]
    aggregate_receipt = str(aggregate["receipt_path"])
    aggregate_fresh = str(aggregate["fresh_index_path"])
    validation = (
        "python3 scripts/swissknife_parser_failure_backlog.py verify-all "
        f"--manifest {manifest} --gate-dir {RECEIPT_ROOT}/gates "
        f"--fresh-index {aggregate_fresh} --receipt-out {aggregate_receipt}"
    )
    blocks.append(
        _task_block(
            task_id="SCA-512",
            title="Prove exact parser-failure reconciliation and fresh health",
            track="parser-failure-aggregate",
            depends_on=aggregate["depends_on"],
            outputs=(aggregate_receipt, aggregate_fresh),
            validation=validation,
            bundle="swissknife/contract-assurance/parser-failure/aggregate",
            lane="sca-parser-failure-aggregate",
            resource_class="cpu-large",
            resource_stage="verification",
            timeout=28800,
            predicted_files=(aggregate_receipt, aggregate_fresh),
            interfaces="ParserFailureAggregateReceipt@1, AnalyzerHealth",
            context_tokens=0,
            provider_role="deterministic-only",
            extra=(
                ("Runtime model calls", "0"),
                ("Expected retained failure count", "258"),
                ("Reviewed maximum parser failures", "10"),
                ("Reviewed maximum parser failure ratio", "0.01"),
            ),
            conflict_policy=(
                "Run one full fresh deterministic scan; never consume copied "
                "authority, weaken thresholds, omit providers, or invoke a model."
            ),
            preconditions="All sixteen exact fan-in receipts are complete.",
            effects=(
                "Binds the complete old failure set to current dispositions and "
                "gates authoritative publication on fresh analyzer health."
            ),
            evidence_subset=(
                "258 row receipts, 16 fan-in receipts, fresh snapshot/index/AST/"
                "parser/health identities"
            ),
            acceptance=(
                "Old row assignments are exact with no duplicate or unassigned "
                "failure; the fresh full index has complete dispositions, no "
                "unexpected new failure, at most 10 failures and ratio at most "
                "0.01; execution records zero model/provider/LLM calls."
            ),
        )
    )
    blocks.append(END_MARKER)
    return "\n\n".join(blocks) + "\n"


def _replace_generated_section(board: str, section: str) -> str:
    has_begin = BEGIN_MARKER in board
    has_end = END_MARKER in board
    if has_begin != has_end:
        raise BacklogError("taskboard contains only one generated-section marker")
    if has_begin:
        prefix, tail = board.split(BEGIN_MARKER, 1)
        _, suffix = tail.split(END_MARKER, 1)
        return prefix.rstrip() + "\n\n" + section.rstrip() + suffix
    return board.rstrip() + "\n\n" + section


def _replace_publication_dependency(board: str) -> str:
    heading = "## SCA-225 Publish one healthy deterministic authoritative index generation"
    if heading not in board:
        raise BacklogError("taskboard lacks the SCA-225 publication task")
    before, after = board.split(heading, 1)
    section, separator, tail = after.partition("\n## SCA-")
    old = "- Depends on: SCA-120, SCA-215, SCA-216, SCA-229, SCA-231"
    new = "- Depends on: SCA-120, SCA-215, SCA-216, SCA-229, SCA-512"
    if old in section:
        section = section.replace(old, new, 1)
    elif new not in section:
        raise BacklogError("SCA-225 dependency line has unexpected content")
    return before + heading + section + (separator + tail if separator else "")


def materialize(
    *,
    index_path: Path,
    health_path: Path,
    todo_path: Path,
    manifest_path: Path,
) -> dict[str, Any]:
    payload = build_payload(index_path, health_path)
    manifest = _envelope(payload)
    section = render_tasks(payload, manifest_path)
    board = todo_path.read_text(encoding="utf-8")
    board = _replace_generated_section(board, section)
    board = _replace_publication_dependency(board)
    _write_json(manifest_path, manifest)
    todo_path.write_text(board, encoding="utf-8")
    return manifest


def check(
    *,
    index_path: Path,
    health_path: Path,
    todo_path: Path,
    manifest_path: Path,
) -> dict[str, Any]:
    expected = _envelope(build_payload(index_path, health_path))
    actual = _read_object(manifest_path)
    if actual != expected:
        raise BacklogError("stored parser-failure manifest differs from regeneration")
    board = todo_path.read_text(encoding="utf-8")
    expected_section = render_tasks(expected["payload"], manifest_path).strip()
    if BEGIN_MARKER not in board or END_MARKER not in board:
        raise BacklogError("taskboard lacks generated parser-failure markers")
    observed = (
        BEGIN_MARKER
        + board.split(BEGIN_MARKER, 1)[1].split(END_MARKER, 1)[0]
        + END_MARKER
    ).strip()
    if observed != expected_section:
        raise BacklogError("generated taskboard section differs from regeneration")
    publication = board.split(
        "## SCA-225 Publish one healthy deterministic authoritative index generation",
        1,
    )[1].split("\n## SCA-", 1)[0]
    expected_dependency = (
        "- Depends on: SCA-120, SCA-215, SCA-216, SCA-229, SCA-512"
    )
    if expected_dependency not in publication or "SCA-231" in publication.splitlines()[4]:
        raise BacklogError("SCA-225 is not gated by SCA-512")
    task_ids = [
        item["task_id"]
        for item in expected["payload"]["clusters"]
        + expected["payload"]["rows"]
        + expected["payload"]["gates"]
        + [expected["payload"]["aggregate"]]
    ]
    if task_ids != [f"SCA-{value:03d}" for value in range(232, 513)]:
        raise BacklogError("generated task IDs are not the exact SCA-232..SCA-512 range")
    return {
        "ok": True,
        "manifest_digest": expected["content_identity"]["digest"],
        "manifest_cid": expected["content_identity"]["cid"],
        "failure_count": 258,
        "generated_task_count": 281,
        "task_id_first": "SCA-232",
        "task_id_last": "SCA-512",
    }


def _manifest_payload(path: Path) -> dict[str, Any]:
    envelope = _read_object(path)
    payload = envelope.get("payload")
    identity = envelope.get("content_identity")
    if not isinstance(payload, dict) or not isinstance(identity, Mapping):
        raise BacklogError("manifest envelope is malformed")
    if dict(identity) != _identity(payload):
        raise BacklogError("manifest content identity does not verify")
    return payload


def _fresh_rows(path: Path) -> tuple[dict[str, Any], dict[str, Mapping[str, Any]]]:
    fresh = _read_object(path)
    rows = fresh.get("rows")
    if not isinstance(rows, list):
        raise BacklogError("fresh repository index has no rows")
    by_path = {
        str(row.get("path") or ""): row
        for row in rows
        if isinstance(row, Mapping)
    }
    if len(by_path) != len(rows):
        raise BacklogError("fresh repository index paths are missing or duplicated")
    return fresh, by_path


def verify_cluster(
    manifest_path: Path,
    family: str,
    fresh_index_path: Path,
    receipt_out: Path,
) -> dict[str, Any]:
    payload = _manifest_payload(manifest_path)
    family = family.upper()
    cluster = next(
        (item for item in payload["clusters"] if item["family"] == family),
        None,
    )
    if cluster is None:
        raise BacklogError(f"unknown actionable family {family}")
    fresh, by_path = _fresh_rows(fresh_index_path)
    resolution_rows: list[dict[str, Any]] = []
    for old in payload["rows"]:
        if old["actionable_family"] != family:
            continue
        current = by_path.get(str(old["path"]))
        if current is None:
            raise BacklogError(
                f"{old['path']} disappeared without a typed rename/deletion receipt"
            )
        status = str(current.get("parser_status") or "")
        kind = str(current.get("disposition_kind") or "")
        policy = str(current.get("policy_rule") or "")
        if status == "parse_failure":
            raise BacklogError(f"parser failure remains unresolved: {old['path']}")
        if kind == "excluded" or "skip_" in policy:
            raise BacklogError(f"failure was hidden by exclusion: {old['path']}")
        if status != "success" and family in {"UNIT", "BROWSER"}:
            raise BacklogError(
                f"contract-bearing test requires parser success: {old['path']}"
            )
        resolution_rows.append(
            {
                "task_id": old["task_id"],
                "row_id": old["row_id"],
                "path": old["path"],
                "old_content_digest": old["content_digest"],
                "fresh_row_id": str(current.get("row_id") or ""),
                "fresh_content_digest": str(current.get("content_digest") or ""),
                "fresh_parser_status": status,
                "fresh_disposition_kind": kind,
                "fresh_policy_rule": policy,
            }
        )
    fresh_bytes = fresh_index_path.read_bytes()
    receipt_payload = {
        "kind": "cluster",
        "family": family,
        "cluster_task_id": cluster["task_id"],
        "source_manifest_digest": _identity(payload)["digest"],
        "source_index_id": payload["source_index"]["index_id"],
        "fresh_index_id": str(fresh.get("index_id") or ""),
        "fresh_index_file_digest": "sha256:" + _sha256_bytes(fresh_bytes),
        "fresh_snapshot_id": str((fresh.get("snapshot") or {}).get("snapshot_id") or ""),
        "failure_count": len(resolution_rows),
        "resolutions": resolution_rows,
        "runtime_model_calls": 0,
    }
    receipt = _envelope(receipt_payload, schema=RECEIPT_SCHEMA)
    _write_json(receipt_out, receipt)
    return receipt


def verify_row(
    manifest_path: Path,
    task_id: str,
    cluster_receipt_path: Path,
    receipt_out: Path,
) -> dict[str, Any]:
    payload = _manifest_payload(manifest_path)
    row = next((item for item in payload["rows"] if item["task_id"] == task_id), None)
    if row is None:
        raise BacklogError(f"manifest has no row task {task_id}")
    cluster_receipt = _read_object(cluster_receipt_path)
    cluster_payload = cluster_receipt.get("payload")
    if not isinstance(cluster_payload, Mapping):
        raise BacklogError("cluster receipt is malformed")
    if cluster_receipt.get("content_identity") != _identity(dict(cluster_payload)):
        raise BacklogError("cluster receipt content identity does not verify")
    resolution = next(
        (
            item
            for item in cluster_payload.get("resolutions", [])
            if isinstance(item, Mapping) and item.get("task_id") == task_id
        ),
        None,
    )
    if resolution is None or resolution.get("row_id") != row["row_id"]:
        raise BacklogError(f"cluster receipt does not resolve exact row {task_id}")
    receipt_payload = {
        "kind": "row",
        "task_id": task_id,
        "row_id": row["row_id"],
        "path": row["path"],
        "source_manifest_digest": _identity(payload)["digest"],
        "cluster_receipt_digest": cluster_receipt["content_identity"]["digest"],
        "resolution": dict(resolution),
        "runtime_model_calls": 0,
    }
    receipt = _envelope(receipt_payload, schema=RECEIPT_SCHEMA)
    _write_json(receipt_out, receipt)
    return receipt


def verify_gate(
    manifest_path: Path,
    nibble: str,
    receipt_dir: Path,
    receipt_out: Path,
) -> dict[str, Any]:
    payload = _manifest_payload(manifest_path)
    nibble = nibble.lower()
    gate = next((item for item in payload["gates"] if item["nibble"] == nibble), None)
    if gate is None:
        raise BacklogError(f"invalid fan-in nibble {nibble}")
    receipts: list[dict[str, str]] = []
    for row in payload["rows"]:
        if row["fan_in_nibble"] != nibble:
            continue
        path = receipt_dir / f"{row['row_digest']}.json"
        envelope = _read_object(path)
        row_payload = envelope.get("payload")
        if (
            not isinstance(row_payload, Mapping)
            or row_payload.get("task_id") != row["task_id"]
            or row_payload.get("row_id") != row["row_id"]
            or envelope.get("content_identity") != _identity(dict(row_payload))
        ):
            raise BacklogError(f"invalid row receipt for {row['task_id']}")
        receipts.append(
            {
                "task_id": row["task_id"],
                "row_id": row["row_id"],
                "receipt_digest": envelope["content_identity"]["digest"],
            }
        )
    if len(receipts) != gate["failure_count"]:
        raise BacklogError("fan-in receipt count does not match manifest")
    receipt_payload = {
        "kind": "fan_in",
        "task_id": gate["task_id"],
        "nibble": nibble,
        "failure_count": len(receipts),
        "rows": receipts,
        "runtime_model_calls": 0,
    }
    receipt = _envelope(receipt_payload, schema=RECEIPT_SCHEMA)
    _write_json(receipt_out, receipt)
    return receipt


def verify_all(
    manifest_path: Path,
    gate_dir: Path,
    fresh_index_path: Path,
    receipt_out: Path,
) -> dict[str, Any]:
    payload = _manifest_payload(manifest_path)
    gate_receipts: list[dict[str, Any]] = []
    assigned: list[str] = []
    for gate in payload["gates"]:
        envelope = _read_object(gate_dir / f"{gate['nibble']}.json")
        gate_payload = envelope.get("payload")
        if (
            not isinstance(gate_payload, Mapping)
            or gate_payload.get("task_id") != gate["task_id"]
            or envelope.get("content_identity") != _identity(dict(gate_payload))
        ):
            raise BacklogError(f"invalid fan-in receipt for nibble {gate['nibble']}")
        rows = gate_payload.get("rows")
        if not isinstance(rows, list):
            raise BacklogError("fan-in receipt lacks rows")
        assigned.extend(str(item.get("row_id") or "") for item in rows)
        gate_receipts.append(
            {
                "task_id": gate["task_id"],
                "nibble": gate["nibble"],
                "receipt_digest": envelope["content_identity"]["digest"],
            }
        )
    expected = [str(item["row_id"]) for item in payload["rows"]]
    if len(assigned) != 258 or len(set(assigned)) != 258 or set(assigned) != set(expected):
        raise BacklogError("fan-in gates do not cover every retained row exactly once")
    fresh, _ = _fresh_rows(fresh_index_path)
    health = fresh.get("health")
    if not isinstance(health, Mapping):
        raise BacklogError("fresh index lacks analyzer health")
    metrics = health.get("metrics")
    thresholds = health.get("thresholds")
    if not isinstance(metrics, Mapping) or not isinstance(thresholds, Mapping):
        raise BacklogError("fresh analyzer health lacks metrics/thresholds")
    if (
        health.get("healthy") is not True
        or health.get("safe_for_completion_reasoning") is not True
        or int(thresholds.get("max_parser_failures", 999999)) > 10
        or float(thresholds.get("max_parser_failure_ratio", 1.0)) > 0.01
        or float(metrics.get("parser_failure_ratio", 1.0)) > 0.01
    ):
        raise BacklogError("fresh index does not meet the reviewed health gate")
    fresh_failure_count = sum(
        1
        for row in fresh["rows"]
        if isinstance(row, Mapping) and row.get("parser_status") == "parse_failure"
    )
    if fresh_failure_count > 10:
        raise BacklogError("fresh index exceeds the reviewed absolute failure budget")
    receipt_payload = {
        "kind": "aggregate",
        "task_id": "SCA-512",
        "source_index_id": payload["source_index"]["index_id"],
        "source_failure_count": 258,
        "assigned_failure_count": len(assigned),
        "unique_assigned_failure_count": len(set(assigned)),
        "fan_in_receipts": gate_receipts,
        "fresh_index_id": str(fresh.get("index_id") or ""),
        "fresh_index_file_digest": "sha256:"
        + _sha256_bytes(fresh_index_path.read_bytes()),
        "fresh_snapshot_id": str((fresh.get("snapshot") or {}).get("snapshot_id") or ""),
        "fresh_failure_count": fresh_failure_count,
        "fresh_failure_ratio": metrics.get("parser_failure_ratio"),
        "health_status": health.get("status"),
        "runtime_model_calls": 0,
    }
    receipt = _envelope(receipt_payload, schema=RECEIPT_SCHEMA)
    _write_json(receipt_out, receipt)
    return receipt


def _common_paths(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--index", type=Path, default=INDEX_DEFAULT)
    parser.add_argument("--health-report", type=Path, default=HEALTH_DEFAULT)
    parser.add_argument("--todo", type=Path, default=TODO_DEFAULT)
    parser.add_argument("--manifest", type=Path, default=MANIFEST_DEFAULT)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    materialize_parser = subparsers.add_parser("materialize")
    _common_paths(materialize_parser)
    check_parser = subparsers.add_parser("check")
    _common_paths(check_parser)

    cluster_parser = subparsers.add_parser("verify-cluster")
    cluster_parser.add_argument("--manifest", type=Path, default=MANIFEST_DEFAULT)
    cluster_parser.add_argument("--cluster", required=True)
    cluster_parser.add_argument("--fresh-index", type=Path, required=True)
    cluster_parser.add_argument("--receipt-out", type=Path, required=True)

    row_parser = subparsers.add_parser("verify-row")
    row_parser.add_argument("--manifest", type=Path, default=MANIFEST_DEFAULT)
    row_parser.add_argument("--task-id", required=True)
    row_parser.add_argument("--cluster-receipt", type=Path, required=True)
    row_parser.add_argument("--receipt-out", type=Path, required=True)

    gate_parser = subparsers.add_parser("verify-gate")
    gate_parser.add_argument("--manifest", type=Path, default=MANIFEST_DEFAULT)
    gate_parser.add_argument("--nibble", required=True)
    gate_parser.add_argument("--receipt-dir", type=Path, required=True)
    gate_parser.add_argument("--receipt-out", type=Path, required=True)

    all_parser = subparsers.add_parser("verify-all")
    all_parser.add_argument("--manifest", type=Path, default=MANIFEST_DEFAULT)
    all_parser.add_argument("--gate-dir", type=Path, required=True)
    all_parser.add_argument("--fresh-index", type=Path, required=True)
    all_parser.add_argument("--receipt-out", type=Path, required=True)

    args = parser.parse_args(argv)
    try:
        if args.command == "materialize":
            result = materialize(
                index_path=args.index,
                health_path=args.health_report,
                todo_path=args.todo,
                manifest_path=args.manifest,
            )
            output: Any = {
                "ok": True,
                "manifest_digest": result["content_identity"]["digest"],
                "manifest_cid": result["content_identity"]["cid"],
                "failure_count": 258,
                "generated_task_count": 281,
            }
        elif args.command == "check":
            output = check(
                index_path=args.index,
                health_path=args.health_report,
                todo_path=args.todo,
                manifest_path=args.manifest,
            )
        elif args.command == "verify-cluster":
            output = verify_cluster(
                args.manifest, args.cluster, args.fresh_index, args.receipt_out
            )
        elif args.command == "verify-row":
            output = verify_row(
                args.manifest,
                args.task_id,
                args.cluster_receipt,
                args.receipt_out,
            )
        elif args.command == "verify-gate":
            output = verify_gate(
                args.manifest, args.nibble, args.receipt_dir, args.receipt_out
            )
        else:
            output = verify_all(
                args.manifest, args.gate_dir, args.fresh_index, args.receipt_out
            )
    except (BacklogError, OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
