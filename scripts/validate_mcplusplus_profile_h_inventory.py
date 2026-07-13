#!/usr/bin/env python3
"""Validate the XPH-100 x402 integration-seam inventory.

The validator deliberately checks both report structure and repository evidence.
That makes the discovery artifact useful as a gate for later Profile H tasks
instead of allowing a syntactically valid but stale checklist to pass.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT = ROOT / "data/mcplusplus_profile_h/x402-inventory.json"
EXPECTED_COMPONENTS = {
    "Mcp-Plus-Plus",
    "ipfs_kit_py",
    "ipfs_accelerate_py",
    "ipfs_datasets_py",
    "swissknife",
}
SELLERS = {"ipfs_kit_py", "ipfs_accelerate_py", "ipfs_datasets_py"}
EXPECTED_HEADERS = {
    "requirements": "PAYMENT-REQUIRED",
    "authorization": "PAYMENT-SIGNATURE",
    "settlement": "PAYMENT-RESPONSE",
}
REQUIRED_GAP_CODES = {f"XPH-GAP-{number:03d}" for number in range(1, 9)}
REQUIRED_DISPATCHER_IDS = {
    "kit-jsonrpc-core", "kit-fastmcp-tools", "kit-libp2p-stream", "kit-profile-g",
    "accelerate-fastmcp-core", "accelerate-fastapi-mount", "accelerate-libp2p-facade",
    "accelerate-libp2p-canonical", "accelerate-profile-g",
    "accelerate-trio-http", "accelerate-trio-libp2p",
    "datasets-fastapi-jsonrpc", "datasets-fastapi-envelope", "datasets-libp2p-dispatch",
    "datasets-libp2p-framing", "datasets-profile-g", "datasets-rest-tool-execute",
    "datasets-mcplusplus-rest",
    "swissknife-http-jsonrpc", "swissknife-libp2p-jsonrpc", "swissknife-libp2p-session",
    "swissknife-local-orb", "swissknife-sdk-client", "swissknife-generic-http",
    "swissknife-generic-libp2p", "swissknife-host-sdk-client",
    "swissknife-versioned-sdk-client",
}
REQUIRED_CAPABILITY_PATHS = {
    "external/ipfs_accelerate/ipfs_accelerate_py/mcplusplus_module/trio/server.py",
    "external/ipfs_accelerate/ipfs_accelerate_py/p2p_tasks/mcp_p2p.py",
    "external/ipfs_datasets/ipfs_datasets_py/mcp_server/p2p_libp2p_transport.py",
}
REQUIRED_WALLET_CLIENT_KINDS = {
    "buyer transport",
    "primary CLI MCP SDK buyer transport",
    "version-aware buyer router",
    "alternate MCP SDK buyer transport",
    "generic buyer transport",
    "signing isolation precedent",
    "receipt/CID precedent",
    "wallet provider",
}
REQUIRED_MANIFESTS = {
    "ipfs_kit_py": {
        "external/ipfs_kit/pyproject.toml",
        "external/ipfs_kit/requirements.txt",
        "external/ipfs_kit/setup.py",
        "external/ipfs_kit/package.json",
    },
    "ipfs_accelerate_py": {
        "external/ipfs_accelerate/pyproject.toml",
        "external/ipfs_accelerate/requirements.txt",
        "external/ipfs_accelerate/ipfs_accelerate_py/requirements.txt",
        "external/ipfs_accelerate/setup.py",
    },
    "ipfs_datasets_py": {
        "external/ipfs_datasets/pyproject.toml",
        "external/ipfs_datasets/requirements.txt",
        "external/ipfs_datasets/setup.py",
    },
    "swissknife": {
        "swissknife/package.json",
        "swissknife/package-lock.json",
        "swissknife/pnpm-lock.yaml",
        "swissknife/yarn.lock",
        "swissknife/web/package.json",
        "swissknife/web/package-lock.json",
    },
}
REQUIRED_BYPASS_SURFACE_IDS = {
    "accelerate-legacy-fastapi-rollback",
    "datasets-deprecated-flask-tools",
    "datasets-direct-product-rest",
}


class InventoryErrors:
    def __init__(self) -> None:
        self.items: list[str] = []

    def require(self, condition: bool, message: str) -> None:
        if not condition:
            self.items.append(message)

    def unique(self, values: Iterable[Any], label: str) -> None:
        materialized = list(values)
        self.require(len(materialized) == len(set(materialized)), f"{label} must be unique")


def _objects(report: dict[str, Any], key: str, errors: InventoryErrors) -> list[dict[str, Any]]:
    value = report.get(key)
    errors.require(isinstance(value, list) and bool(value), f"{key} must be a non-empty array")
    if not isinstance(value, list):
        return []
    objects = [item for item in value if isinstance(item, dict)]
    errors.require(len(objects) == len(value), f"every {key} entry must be an object")
    return objects


def _validate_source(entry: dict[str, Any], label: str, errors: InventoryErrors) -> None:
    relative = entry.get("path")
    if relative is None:
        return
    errors.require(isinstance(relative, str) and relative and not relative.startswith("/"), f"{label}.path must be repository-relative")
    if not isinstance(relative, str) or not relative:
        return
    source = ROOT / relative
    errors.require(source.is_file(), f"{label}.path does not exist: {relative}")
    if not source.is_file():
        return
    symbols = entry.get("symbols", [])
    errors.require(isinstance(symbols, list), f"{label}.symbols must be an array")
    text = source.read_text(encoding="utf-8", errors="replace")
    for symbol in symbols if isinstance(symbols, list) else []:
        errors.require(isinstance(symbol, str) and bool(symbol), f"{label} contains an invalid symbol")
        if not isinstance(symbol, str) or not symbol:
            continue
        # Dotted inventory labels may include a class qualifier while source
        # contains only the final function/class name. Descriptive initialize
        # labels intentionally check their significant final token.
        candidates = [symbol, symbol.rsplit(".", 1)[-1], symbol.split()[0]]
        errors.require(any(candidate in text for candidate in candidates), f"{label} symbol is not evidenced in {relative}: {symbol}")


def _manifest_declares_x402(path: Path) -> bool:
    """Return whether a dependency manifest declares an x402 package."""
    text = path.read_text(encoding="utf-8", errors="replace")
    return bool(re.search(
        r'''(?im)(?:["'](?:@x402/[^"']+|x402)["']\s*:|^\s*x402(?:\[[^\]]+\])?\s*(?:[<>=!~^@]|$))''',
        text,
    ))


def _git_revision(relative: str) -> str | None:
    """Return a source root's checked-out revision without mutating it."""
    try:
        result = subprocess.run(
            ["git", "-C", str(ROOT / relative), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    revision = result.stdout.strip()
    return revision if re.fullmatch(r"[0-9a-f]{40}", revision) else None


def validate(report: dict[str, Any]) -> list[str]:
    errors = InventoryErrors()
    errors.require(report.get("schema_version") == 1, "schema_version must be 1")
    errors.require(report.get("task_id") == "XPH-100", "task_id must be XPH-100")
    errors.require(report.get("behavior_change") is False, "discovery report must state behavior_change=false")

    scope = report.get("scope", {})
    components = set(scope.get("canonical_components", [])) if isinstance(scope, dict) else set()
    errors.require(components == EXPECTED_COMPONENTS, "scope.canonical_components must cover the complete Profile H component set")
    errors.require(
        isinstance(scope.get("transport_coverage_rule"), str) and bool(scope.get("transport_coverage_rule")),
        "scope.transport_coverage_rule must define the dispatcher inventory boundary",
    )
    revisions = scope.get("source_revisions", {}) if isinstance(scope, dict) else {}
    source_roots = scope.get("canonical_source_roots", {}) if isinstance(scope, dict) else {}
    for component in EXPECTED_COMPONENTS:
        revision = revisions.get(component) if isinstance(revisions, dict) else None
        errors.require(isinstance(revision, str) and bool(re.fullmatch(r"[0-9a-f]{40}", revision)), f"missing 40-character source revision for {component}")
        relative = source_roots.get(component) if isinstance(source_roots, dict) else None
        errors.require(isinstance(relative, str) and bool(relative), f"missing canonical source root for {component}")
        if isinstance(relative, str) and relative and isinstance(revision, str):
            actual_revision = _git_revision(relative)
            errors.require(actual_revision is not None, f"cannot resolve source revision for {component}")
            errors.require(actual_revision == revision, f"source revision is stale for {component}")

    upstream = report.get("upstream_x402", {})
    errors.require(upstream.get("protocol_version") == 2, "upstream_x402.protocol_version must pin v2")
    normative = upstream.get("normative_http", {}) if isinstance(upstream, dict) else {}
    errors.require(normative.get("unpaid_status") == 402, "normative unpaid status must be 402")
    errors.require(normative.get("headers") == EXPECTED_HEADERS, "normative v2 header mapping is incomplete or incorrect")
    legacy = set(normative.get("legacy_headers_forbidden", [])) if isinstance(normative, dict) else set()
    errors.require({"X-PAYMENT", "X-PAYMENT-RESPONSE"} <= legacy, "legacy v1 headers must be explicitly forbidden")
    pinned = upstream.get("pinned_specification", {}) if isinstance(upstream, dict) else {}
    commit = pinned.get("commit") if isinstance(pinned, dict) else None
    errors.require(isinstance(commit, str) and bool(re.fullmatch(r"[0-9a-f]{40}", commit)), "upstream specification must have an immutable git commit")
    references = upstream.get("primary_references", []) if isinstance(upstream, dict) else []
    reference_kinds = {item.get("kind") for item in references if isinstance(item, dict)}
    errors.require({"specification", "http-v2", "v1-to-v2-migration", "official-mcp-integration"} <= reference_kinds, "primary upstream references are incomplete")

    dependencies = _objects(report, "dependency_version_matrix", errors)
    dependency_components = {item.get("component") for item in dependencies}
    errors.require(SELLERS | {"swissknife"} == dependency_components, "dependency matrix must cover exactly all sellers and SwissKnife")
    for index, item in enumerate(dependencies):
        label = f"dependency_version_matrix[{index}]"
        component = item.get("component")
        errors.require(item.get("status") in {"absent", "present"}, f"{label}.status is invalid")
        errors.require(isinstance(item.get("manifests_scanned"), list) and bool(item.get("manifests_scanned")), f"{label} must list scanned manifests")
        manifests = set(item.get("manifests_scanned", [])) if isinstance(item.get("manifests_scanned"), list) else set()
        if component in REQUIRED_MANIFESTS:
            errors.require(REQUIRED_MANIFESTS[component] <= manifests, f"{label} does not cover every canonical dependency manifest")
        for manifest in item.get("manifests_scanned", []):
            errors.require(isinstance(manifest, str) and (ROOT / manifest).is_file(), f"{label} manifest does not exist: {manifest}")
            if isinstance(manifest, str) and (ROOT / manifest).is_file() and item.get("status") == "absent":
                errors.require(not _manifest_declares_x402(ROOT / manifest), f"{label} is stale: {manifest} now declares x402")
        errors.require(isinstance(item.get("candidate"), str) and bool(item.get("candidate")), f"{label} must pin a candidate dependency")
        errors.require(isinstance(item.get("candidate_pin"), str) and bool(item.get("candidate_pin")), f"{label} must record candidate version provenance")
        errors.require(isinstance(item.get("registry"), str) and item.get("registry", "").startswith("https://"), f"{label} must record an HTTPS registry release")
        errors.require(bool(item.get("integrity")), f"{label} must record candidate artifact integrity")

    dispatchers = _objects(report, "dispatchers", errors)
    errors.unique((item.get("id") for item in dispatchers), "dispatcher ids")
    dispatcher_ids = {item.get("id") for item in dispatchers}
    errors.require(REQUIRED_DISPATCHER_IDS <= dispatcher_ids, "known MCP++ dispatch seams are missing")
    for index, item in enumerate(dispatchers):
        label = f"dispatchers[{index}]"
        _validate_source(item, label, errors)
        errors.require(item.get("transport") in {"http", "libp2p", "shared", "local"}, f"{label}.transport is invalid")
        errors.require(isinstance(item.get("side_effect_boundary"), str) and bool(item.get("side_effect_boundary")), f"{label} lacks side-effect boundary")
        errors.require(isinstance(item.get("payment_insertion"), str) and bool(item.get("payment_insertion")), f"{label} lacks payment insertion seam")
        errors.require(item.get("current_payment_enforcement") is False, f"{label} must accurately report no current payment enforcement")
    for component in SELLERS | {"swissknife"}:
        transports = {item.get("transport") for item in dispatchers if item.get("component") == component}
        errors.require("http" in transports, f"{component} HTTP dispatcher is missing")
        errors.require("libp2p" in transports, f"{component} libp2p dispatcher is missing")

    descriptors = _objects(report, "capability_descriptors", errors)
    for index, item in enumerate(descriptors):
        _validate_source(item, f"capability_descriptors[{index}]", errors)
        errors.require(item.get("current_profile_h") is False, f"capability_descriptors[{index}] incorrectly claims Profile H")
    errors.require(EXPECTED_COMPONENTS <= {item.get("component") for item in descriptors}, "capability descriptors must cover every component")
    errors.require(
        REQUIRED_CAPABILITY_PATHS <= {item.get("path") for item in descriptors},
        "alternate HTTP/libp2p runtime capability descriptors are missing",
    )

    wallet = _objects(report, "wallet_client_seams", errors)
    for index, item in enumerate(wallet):
        _validate_source(item, f"wallet_client_seams[{index}]", errors)
    errors.require(any(item.get("kind") == "wallet provider" and item.get("path") is None for item in wallet), "missing wallet-provider gap is not recorded")
    errors.require(any(item.get("kind") == "buyer transport" for item in wallet), "SwissKnife buyer transport seam is missing")
    errors.require(
        REQUIRED_WALLET_CLIENT_KINDS <= {item.get("kind") for item in wallet},
        "SwissKnife alternate client, signer, receipt, or wallet-provider seams are missing",
    )

    seller_configs = _objects(report, "seller_configuration_paths", errors)
    errors.require(SELLERS == {item.get("component") for item in seller_configs}, "seller configuration paths must cover exactly all three sellers")
    for index, item in enumerate(seller_configs):
        errors.require(item.get("x402_configuration_present") is False, f"seller_configuration_paths[{index}] incorrectly claims x402 config")
        for relative in item.get("existing_paths", []):
            errors.require(isinstance(relative, str) and (ROOT / relative).is_file(), f"seller configuration source does not exist: {relative}")

    stores = _objects(report, "durable_stores", errors)
    errors.require(SELLERS | {"swissknife"} <= {item.get("component") for item in stores}, "durable stores must cover all sellers and SwissKnife")
    for index, item in enumerate(stores):
        _validate_source(item, f"durable_stores[{index}]", errors)
        errors.require(item.get("payment_ready") is False, f"durable_stores[{index}] incorrectly claims payment readiness")
        errors.require(isinstance(item.get("reuse"), str) and bool(item.get("reuse")), f"durable_stores[{index}] lacks reuse assessment")

    families = _objects(report, "protected_operation_families", errors)
    errors.require(SELLERS == {item.get("component") for item in families}, "protected operation families must cover exactly all sellers")
    for index, item in enumerate(families):
        errors.require(isinstance(item.get("families"), list) and len(item.get("families", [])) >= 5, f"protected_operation_families[{index}] is incomplete")
        errors.require(set(item.get("dispatch_seams", [])) <= dispatcher_ids, f"protected_operation_families[{index}] references an unknown dispatcher")
        errors.require(bool(item.get("authorization_that_payment_must_not_bypass")), f"protected_operation_families[{index}] lacks authorization composition")

    bypass_surfaces = _objects(report, "non_mcplusplus_execution_surfaces", errors)
    errors.unique((item.get("id") for item in bypass_surfaces), "non-MCP++ execution surface ids")
    errors.require(
        REQUIRED_BYPASS_SURFACE_IDS <= {item.get("id") for item in bypass_surfaces},
        "legacy or direct paid-access bypass surfaces are missing",
    )
    for index, item in enumerate(bypass_surfaces):
        _validate_source(item, f"non_mcplusplus_execution_surfaces[{index}]", errors)
        errors.require(item.get("in_mcplusplus_dispatcher_count") is False, f"non_mcplusplus_execution_surfaces[{index}] is incorrectly counted as MCP++")
        errors.require(isinstance(item.get("profile_h_disposition"), str) and bool(item.get("profile_h_disposition")), f"non_mcplusplus_execution_surfaces[{index}] lacks a Profile H disposition")

    mirrors = _objects(report, "mirrors", errors)
    errors.require(len(mirrors) >= 4, "canonical/vendored mirror accounting is incomplete")
    for index, item in enumerate(mirrors):
        errors.require((ROOT / str(item.get("canonical", ""))).exists(), f"mirrors[{index}] canonical path is missing")
        for relative in item.get("copies", []):
            errors.require((ROOT / relative).exists(), f"mirrors[{index}] copy path is missing: {relative}")

    gaps = _objects(report, "gaps", errors)
    errors.unique((item.get("code") for item in gaps), "gap codes")
    errors.require(REQUIRED_GAP_CODES <= {item.get("code") for item in gaps}, "required integration gaps are incomplete")
    errors.require(all(item.get("required_owner") for item in gaps), "every gap must have a follow-on owner")

    conclusion = report.get("conclusion", {})
    errors.require(conclusion.get("runtime_x402_present") is False, "conclusion must accurately report runtime x402 absence")
    errors.require(conclusion.get("profile_h_advertised") is False, "conclusion must accurately report Profile H absence")
    errors.require(conclusion.get("mainnet_ready") is False, "inventory must not claim mainnet readiness")
    first_points = conclusion.get("recommended_first_enforcement_points", {}) if isinstance(conclusion, dict) else {}
    errors.require(SELLERS | {"swissknife"} <= set(first_points), "recommended enforcement points are incomplete")
    return errors.items


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT, help="inventory JSON to validate")
    args = parser.parse_args(argv)
    report_path = args.report if args.report.is_absolute() else ROOT / args.report
    try:
        with report_path.open("r", encoding="utf-8") as handle:
            report = json.load(handle)
    except (OSError, json.JSONDecodeError) as error:
        print(f"FAIL: cannot read inventory {report_path}: {error}", file=sys.stderr)
        return 2
    if not isinstance(report, dict):
        print("FAIL: inventory root must be a JSON object", file=sys.stderr)
        return 2

    failures = validate(report)
    if failures:
        print(f"FAIL: {len(failures)} inventory validation error(s)", file=sys.stderr)
        for failure in failures:
            print(f" - {failure}", file=sys.stderr)
        return 1
    # Keep success diagnostics out of stdout. Supervisor taskboards historically
    # allowed Markdown code spans around validation commands; older parser
    # versions passed those backticks through to Bash, which substituted stdout
    # and then attempted to execute a line beginning with ``PASS:``. Reporting
    # on stderr makes this validator safe for an already-parsed legacy command
    # while the taskboard metadata is being repaired.
    print(
        "PASS: XPH-100 inventory covers "
        f"{len(report['dispatchers'])} dispatch seams, "
        f"{len(report['capability_descriptors'])} capability descriptors, "
        f"{len(report['durable_stores'])} durable stores, and "
        f"{len(report['gaps'])} explicit gaps",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
