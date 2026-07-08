"""Interop contract between Meta Wearables DAT Android and IPFS Kit.

The external Android repository cannot be imported by Python, so this module
normalizes its Gradle and Android manifest descriptors into a small runtime
contract that can be routed through the existing IPFS descriptor pack.
"""

from __future__ import annotations

import hashlib
import json
import re
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from handsfree.ipfs_descriptor_pack import get_ipfs_descriptor_pack_as_dicts

ANDROID_NS = "{http://schemas.android.com/apk/res/android}"


class MetaWearablesIPFSKitInteropError(RuntimeError):
    """Raised when either external contract cannot be discovered."""


@dataclass(frozen=True)
class MetaWearablesDATAndroidSample:
    """Static Android DAT sample contract derived from checked-in descriptors."""

    name: str
    namespace: str
    application_id: str
    min_sdk: int
    target_sdk: int
    permissions: tuple[str, ...]
    dependencies: tuple[str, ...]
    manifest_placeholders: tuple[str, ...]
    capabilities: tuple[str, ...]
    manifest_path: str
    gradle_path: str


@dataclass(frozen=True)
class IPFSKitExternalContract:
    """Static IPFS Kit descriptor contract needed by the Android handoff."""

    root: str
    deprecations_schema_path: str
    mcp_schema_repair_scripts: tuple[str, ...]
    bucket_vfs_descriptors: tuple[str, ...]
    mcp_tool_descriptors: tuple[str, ...]
    required_deprecation_report_keys: tuple[str, ...]
    ipfs_descriptor_ids: tuple[str, ...]


@dataclass(frozen=True)
class MetaWearablesIPFSKitHandoff:
    """Deterministic receipt for one Android DAT payload routed to IPFS Kit."""

    contract_id: str
    source_repository: str
    target_repository: str
    sample_name: str
    capability: str
    route: str
    endpoint_path: str
    method: str
    content_cid: str
    payload_sha256: str
    payload_size_bytes: int
    required_android_permissions: tuple[str, ...]
    required_ipfs_descriptors: tuple[str, ...]
    mcp_schema_repair_scripts: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable receipt."""
        return asdict(self)


def discover_meta_wearables_dat_android_contract(
    root: str | Path,
) -> tuple[MetaWearablesDATAndroidSample, ...]:
    """Discover supported Android DAT samples from Gradle and manifest files."""
    root_path = Path(root)
    if not root_path.exists():
        raise MetaWearablesIPFSKitInteropError(f"Android DAT root not found: {root_path}")

    samples: list[MetaWearablesDATAndroidSample] = []
    for sample_dir in sorted((root_path / "samples").glob("*Access")):
        gradle_path = sample_dir / "app" / "build.gradle.kts"
        manifest_path = sample_dir / "app" / "src" / "main" / "AndroidManifest.xml"
        if not gradle_path.exists() or not manifest_path.exists():
            continue

        gradle_text = gradle_path.read_text(encoding="utf-8")
        manifest = ET.parse(manifest_path).getroot()
        permissions = tuple(
            sorted(
                perm.attrib.get(f"{ANDROID_NS}name", "")
                for perm in manifest.findall("uses-permission")
                if perm.attrib.get(f"{ANDROID_NS}name")
            )
        )
        namespace = _extract_gradle_string(gradle_text, "namespace")
        application_id = _extract_gradle_string(gradle_text, "applicationId")
        dependencies = tuple(sorted(set(re.findall(r"libs\.([a-zA-Z0-9_.]+)", gradle_text))))
        placeholders = tuple(sorted(set(re.findall(r'manifestPlaceholders\["([^"]+)"\]', gradle_text))))

        samples.append(
            MetaWearablesDATAndroidSample(
                name=sample_dir.name,
                namespace=namespace,
                application_id=application_id,
                min_sdk=_extract_gradle_int(gradle_text, "minSdk"),
                target_sdk=_extract_gradle_int(gradle_text, "targetSdk"),
                permissions=permissions,
                dependencies=dependencies,
                manifest_placeholders=placeholders,
                capabilities=_capabilities_from_dependencies(dependencies),
                manifest_path=str(manifest_path),
                gradle_path=str(gradle_path),
            )
        )

    if not samples:
        raise MetaWearablesIPFSKitInteropError(
            f"No Android DAT samples with Gradle and manifest descriptors under {root_path}"
        )
    return tuple(samples)


def discover_ipfs_kit_external_contract(root: str | Path) -> IPFSKitExternalContract:
    """Discover IPFS Kit descriptors required by the Android handoff."""
    root_path = Path(root)
    if not root_path.exists():
        raise MetaWearablesIPFSKitInteropError(f"IPFS Kit root not found: {root_path}")

    schema_path = root_path / "data" / "deprecations_report.schema.json"
    if not schema_path.exists():
        raise MetaWearablesIPFSKitInteropError(
            f"IPFS Kit deprecations schema not found: {schema_path}"
        )

    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    required = tuple(schema.get("required", ()))
    missing = {"report_version", "generated_at", "deprecated", "summary", "policy", "raw"} - set(required)
    if missing:
        raise MetaWearablesIPFSKitInteropError(
            f"IPFS Kit deprecations schema is missing required keys: {sorted(missing)}"
        )

    repair_scripts = tuple(
        str(path)
        for path in (
            root_path / "archive" / "archive_clutter" / "fix_scripts" / "fix_mcp_schema.py",
            root_path / "backup" / "archive_clutter" / "fix_scripts" / "fix_mcp_schema.py",
            root_path / "backup" / "patches" / "fixes" / "fix_mcp_schema.py",
        )
    )
    missing_scripts = [path for path in repair_scripts if not Path(path).exists()]
    if missing_scripts:
        raise MetaWearablesIPFSKitInteropError(
            f"IPFS Kit MCP schema repair scripts missing: {missing_scripts}"
        )

    bucket_vfs_descriptors = tuple(
        str(path)
        for path in (
            root_path / "docs" / "implementation" / "BUCKET_VFS_INTERFACES_COMPLETE.md",
            root_path / "ipfs_kit_py" / "bucket_vfs_cli.py",
            root_path / "ipfs_kit_py" / "mcp" / "servers" / "bucket_vfs_mcp_tools.py",
        )
        if path.exists()
    )
    if len(bucket_vfs_descriptors) != 3:
        raise MetaWearablesIPFSKitInteropError("IPFS Kit bucket/VFS descriptors are incomplete")

    mcp_tool_descriptors = tuple(
        str(path)
        for path in (
            root_path / "ipfs_kit_py" / "mcp" / "servers" / "enhanced_integrated_mcp_server.py",
            root_path / "mcp" / "bucket_vfs_mcp_tools.py",
            root_path / "docs" / "py-ipld-dag-pb" / "ipld_dag_pb" / "dag-pb.proto",
        )
        if path.exists()
    )
    if len(mcp_tool_descriptors) != 3:
        raise MetaWearablesIPFSKitInteropError("IPFS Kit MCP/IPLD descriptors are incomplete")

    ipfs_descriptor_ids = tuple(
        descriptor["descriptor_id"] for descriptor in get_ipfs_descriptor_pack_as_dicts()
    )
    return IPFSKitExternalContract(
        root=str(root_path),
        deprecations_schema_path=str(schema_path),
        mcp_schema_repair_scripts=repair_scripts,
        bucket_vfs_descriptors=bucket_vfs_descriptors,
        mcp_tool_descriptors=mcp_tool_descriptors,
        required_deprecation_report_keys=required,
        ipfs_descriptor_ids=ipfs_descriptor_ids,
    )


def build_meta_wearables_ipfs_kit_handoff(
    android_root: str | Path,
    ipfs_kit_root: str | Path,
    *,
    sample_name: str = "DisplayAccess",
    capability: str = "display.output",
    payload: bytes | str | dict[str, Any] | None = None,
) -> MetaWearablesIPFSKitHandoff:
    """Build a deterministic Android DAT to IPFS Kit handoff receipt."""
    samples = discover_meta_wearables_dat_android_contract(android_root)
    sample = next((item for item in samples if item.name == sample_name), None)
    if sample is None:
        raise MetaWearablesIPFSKitInteropError(f"Android DAT sample not found: {sample_name}")
    if capability not in sample.capabilities:
        raise MetaWearablesIPFSKitInteropError(
            f"{sample_name} does not advertise capability {capability}"
        )

    ipfs_contract = discover_ipfs_kit_external_contract(ipfs_kit_root)
    descriptor = next(
        item
        for item in get_ipfs_descriptor_pack_as_dicts()
        if item["descriptor_id"] == "ipfs.add"
    )

    payload_bytes = _payload_to_bytes(
        payload
        if payload is not None
        else {
            "source": "external/meta-wearables-dat-android",
            "sample": sample.name,
            "capability": capability,
            "route": "android-dat-display-to-ipfs-kit",
        }
    )
    digest = hashlib.sha256(payload_bytes).hexdigest()
    return MetaWearablesIPFSKitHandoff(
        contract_id="handsfree.external-meta-wearables-dat-android.external-ipfs-kit@1",
        source_repository="external/meta-wearables-dat-android",
        target_repository="external/ipfs_kit",
        sample_name=sample.name,
        capability=capability,
        route="android-dat-display-to-ipfs-kit",
        endpoint_path=descriptor["endpoint_path"],
        method=descriptor["method"],
        content_cid=f"sha256:{digest}",
        payload_sha256=digest,
        payload_size_bytes=len(payload_bytes),
        required_android_permissions=sample.permissions,
        required_ipfs_descriptors=(
            ipfs_contract.deprecations_schema_path,
            *ipfs_contract.bucket_vfs_descriptors,
            *ipfs_contract.mcp_tool_descriptors,
        ),
        mcp_schema_repair_scripts=ipfs_contract.mcp_schema_repair_scripts,
    )


def _extract_gradle_string(source: str, key: str) -> str:
    match = re.search(rf"\b{re.escape(key)}\s*=\s*\"([^\"]+)\"", source)
    if not match:
        raise MetaWearablesIPFSKitInteropError(f"Gradle field missing: {key}")
    return match.group(1)


def _extract_gradle_int(source: str, key: str) -> int:
    match = re.search(rf"\b{re.escape(key)}\s*=\s*(\d+)", source)
    if not match:
        raise MetaWearablesIPFSKitInteropError(f"Gradle integer field missing: {key}")
    return int(match.group(1))


def _capabilities_from_dependencies(dependencies: tuple[str, ...]) -> tuple[str, ...]:
    capabilities = {"device.session"}
    if "mwdat.camera" in dependencies:
        capabilities.add("camera.photo_capture")
    if "mwdat.display" in dependencies:
        capabilities.add("display.output")
    if "mwdat.mockdevice" in dependencies:
        capabilities.add("mockdevice.testing")
    return tuple(sorted(capabilities))


def _payload_to_bytes(payload: bytes | str | dict[str, Any]) -> bytes:
    if isinstance(payload, bytes):
        return payload
    if isinstance(payload, str):
        return payload.encode("utf-8")
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
