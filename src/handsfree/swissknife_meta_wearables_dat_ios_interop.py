"""Interop contract between SwissKnife and ``external/meta-wearables-dat-ios``.

VAI-667 repairs the VAIOS-G706 objective validation gap that requires
``swissknife`` to interoperate with ``external/meta-wearables-dat-ios`` through
importable contracts, interface descriptors, runtime handoff behavior, and
integration tests. This is part of the shared
``goal_packet/interoperability/swissknife/06921590135c`` packet covering
VAIOS-G700, VAIOS-G701, VAIOS-G702, VAIOS-G703, VAIOS-G704, VAIOS-G705, and
VAIOS-G706.

The iOS DAT submodule ships agent-facing Display, session lifecycle, and
registration/permission rules plus a real ``samples/DisplayAccess`` Swift app.
This module statically discovers those source descriptors without compiling
Swift or importing the SDK, then emits a deterministic
``SwissKnifeMetaWearablesDATIOSHandoff`` receipt that mirrors the SwissKnife
MCP++ descriptor.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

INTERFACE_CONTRACT = "interface contract swissknife external/meta-wearables-dat-ios"
GOAL_ID = "VAIOS-G706"
GOAL_PACKET = "goal_packet/interoperability/swissknife/06921590135c"
GOAL_PACKET_GOALS = (
    "VAIOS-G700",
    "VAIOS-G701",
    "VAIOS-G702",
    "VAIOS-G703",
    "VAIOS-G704",
    "VAIOS-G705",
    "VAIOS-G706",
)

REQUIRED_DISPLAY_ACCESS_DOC_PATH = ".cursor/rules/display-access.mdc"
REQUIRED_SESSION_LIFECYCLE_DOC_PATH = ".cursor/rules/session-lifecycle.mdc"
REQUIRED_PERMISSIONS_REGISTRATION_DOC_PATH = ".cursor/rules/permissions-registration.mdc"
REQUIRED_DISPLAY_INFO_PLIST_PATH = "samples/DisplayAccess/DisplayAccess/Info.plist"
REQUIRED_DISPLAY_VIEW_MODEL_PATH = (
    "samples/DisplayAccess/DisplayAccess/ViewModels/DisplayViewModel.swift"
)
REQUIRED_CAR_MAINTENANCE_DISPLAY_PATH = (
    "samples/DisplayAccess/DisplayAccess/Samples/CarMaintenanceDisplay.swift"
)

REQUIRED_DEVICE_SESSION_STATES = (
    "idle",
    "starting",
    "started",
    "paused",
    "stopping",
    "stopped",
)

REQUIRED_INFO_PLIST_KEYS = (
    "CFBundleURLTypes",
    "MWDAT",
    "AppLinkURLScheme",
    "MetaAppID",
    "ClientToken",
    "TeamID",
    "UIBackgroundModes",
    "NSBluetoothAlwaysUsageDescription",
    "NSLocalNetworkUsageDescription",
    "NSBonjourServices",
)

REQUIRED_BACKGROUND_MODES = (
    "processing",
    "bluetooth-central",
    "bluetooth-peripheral",
)

REQUIRED_DISPLAY_ICON_NAMES = (
    "checkmark",
    "triangleLeftVerticalLine",
    "triangleRightVerticalLine",
    "videoCamera",
)

REQUIRED_DISPLAY_BUTTON_STYLES = ("primary", "secondary")

REQUIRED_DISPLAY_VIEW_TYPES = (
    "FlexBox",
    "Text",
    "Button",
    "Image",
    "VideoPlayer",
)

REQUIRED_SWISSKNIFE_META_WEARABLES_DAT_IOS_OPERATIONS = (
    "meta_wearables_dat_ios.registration.start",
    "meta_wearables_dat_ios.registration.handle_url",
    "meta_wearables_dat_ios.registration.check_permission_status",
    "meta_wearables_dat_ios.session.create",
    "meta_wearables_dat_ios.session.start",
    "meta_wearables_dat_ios.display.attach",
    "meta_wearables_dat_ios.display.send",
    "meta_wearables_dat_ios.display.stop",
)


class SwissKnifeMetaWearablesDATIOSInteropError(RuntimeError):
    """Raised when either side of the swissknife/meta-wearables-dat-ios contract is missing."""


@dataclass(frozen=True)
class MetaWearablesDATIOSDisplayContract:
    """Static Display/session contract discovered from the iOS DAT submodule."""

    root: str
    display_access_doc_path: str
    session_lifecycle_doc_path: str
    permissions_registration_doc_path: str
    display_info_plist_path: str
    display_view_model_path: str
    car_maintenance_display_path: str
    device_session_states: tuple[str, ...]
    info_plist_keys: tuple[str, ...]
    background_modes: tuple[str, ...]
    display_icon_names: tuple[str, ...]
    display_button_styles: tuple[str, ...]
    display_view_types: tuple[str, ...]


@dataclass(frozen=True)
class SwissKnifeMetaWearablesDATIOSHandoff:
    """Deterministic receipt for one iOS Display handoff routed to SwissKnife."""

    contract_id: str
    source_repository: str
    target_repository: str
    interface_contract: str
    goal_id: str
    goal_packet: str
    capability: str
    route: str
    content_cid: str
    payload_sha256: str
    payload_size_bytes: int
    device_session_states: tuple[str, ...]
    info_plist_keys: tuple[str, ...]
    background_modes: tuple[str, ...]
    display_icon_names: tuple[str, ...]
    display_button_styles: tuple[str, ...]
    display_view_types: tuple[str, ...]
    required_swissknife_operations: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable receipt."""
        return asdict(self)


def discover_meta_wearables_dat_ios_display_contract(
    root: str | Path,
) -> MetaWearablesDATIOSDisplayContract:
    """Discover the iOS DAT Display/session contract from static source files."""
    root_path = Path(root)
    if not root_path.exists():
        raise SwissKnifeMetaWearablesDATIOSInteropError(
            f"meta-wearables-dat-ios root not found: {root_path}"
        )

    display_access_doc_path = root_path / REQUIRED_DISPLAY_ACCESS_DOC_PATH
    session_lifecycle_doc_path = root_path / REQUIRED_SESSION_LIFECYCLE_DOC_PATH
    permissions_registration_doc_path = root_path / REQUIRED_PERMISSIONS_REGISTRATION_DOC_PATH
    display_info_plist_path = root_path / REQUIRED_DISPLAY_INFO_PLIST_PATH
    display_view_model_path = root_path / REQUIRED_DISPLAY_VIEW_MODEL_PATH
    car_maintenance_display_path = root_path / REQUIRED_CAR_MAINTENANCE_DISPLAY_PATH

    required_paths = (
        display_access_doc_path,
        session_lifecycle_doc_path,
        permissions_registration_doc_path,
        display_info_plist_path,
        display_view_model_path,
        car_maintenance_display_path,
    )
    missing = [str(path) for path in required_paths if not path.exists()]
    if missing:
        raise SwissKnifeMetaWearablesDATIOSInteropError(
            f"meta-wearables-dat-ios Display descriptors missing: {missing}"
        )

    display_access_source = display_access_doc_path.read_text(encoding="utf-8")
    for required_symbol in (
        "Wearables.configure",
        "createSession(deviceSelector:)",
        "supportsDisplay()",
        "addDisplay",
        "DisplayState.started",
        "display?.send",
        "VideoPlayer",
    ):
        if required_symbol not in display_access_source:
            raise SwissKnifeMetaWearablesDATIOSInteropError(
                f"meta-wearables-dat-ios display-access.mdc is missing symbol: "
                f"{required_symbol}"
            )

    permissions_source = permissions_registration_doc_path.read_text(encoding="utf-8")
    for required_symbol in (
        "Wearables.shared.startRegistration",
        "Wearables.shared.handleUrl",
        "registrationStateStream",
        "checkPermissionStatus",
        "requestPermission",
    ):
        if required_symbol not in permissions_source:
            raise SwissKnifeMetaWearablesDATIOSInteropError(
                f"meta-wearables-dat-ios permissions-registration.mdc is missing symbol: "
                f"{required_symbol}"
            )

    session_source = session_lifecycle_doc_path.read_text(encoding="utf-8")
    discovered_session_states = tuple(
        sorted(set(re.findall(r"`([a-z]+)`\s*\|", session_source)))
    )
    missing_session_states = set(REQUIRED_DEVICE_SESSION_STATES) - set(
        discovered_session_states
    )
    if missing_session_states:
        raise SwissKnifeMetaWearablesDATIOSInteropError(
            f"meta-wearables-dat-ios session-lifecycle.mdc is missing states: "
            f"{sorted(missing_session_states)}"
        )

    plist_source = display_info_plist_path.read_text(encoding="utf-8")
    discovered_info_plist_keys = tuple(sorted(set(re.findall(r"<key>([^<]+)</key>", plist_source))))
    missing_info_plist_keys = set(REQUIRED_INFO_PLIST_KEYS) - set(discovered_info_plist_keys)
    if missing_info_plist_keys:
        raise SwissKnifeMetaWearablesDATIOSInteropError(
            f"meta-wearables-dat-ios DisplayAccess Info.plist is missing keys: "
            f"{sorted(missing_info_plist_keys)}"
        )

    discovered_background_modes = tuple(
        sorted(mode for mode in REQUIRED_BACKGROUND_MODES if f"<string>{mode}</string>" in plist_source)
    )
    missing_background_modes = set(REQUIRED_BACKGROUND_MODES) - set(
        discovered_background_modes
    )
    if missing_background_modes:
        raise SwissKnifeMetaWearablesDATIOSInteropError(
            f"meta-wearables-dat-ios DisplayAccess Info.plist is missing background modes: "
            f"{sorted(missing_background_modes)}"
        )

    display_source = display_view_model_path.read_text(encoding="utf-8")
    car_display_source = car_maintenance_display_path.read_text(encoding="utf-8")
    combined_display_source = f"{display_source}\n{car_display_source}"

    discovered_icon_names = tuple(
        sorted(
            icon_name
            for icon_name in REQUIRED_DISPLAY_ICON_NAMES
            if f".{icon_name}" in combined_display_source
        )
    )
    missing_icon_names = set(REQUIRED_DISPLAY_ICON_NAMES) - set(discovered_icon_names)
    if missing_icon_names:
        raise SwissKnifeMetaWearablesDATIOSInteropError(
            f"meta-wearables-dat-ios DisplayAccess Swift source is missing icon names: "
            f"{sorted(missing_icon_names)}"
        )

    discovered_button_styles = tuple(
        sorted(set(re.findall(r"style:\s*\.([A-Za-z0-9_]+)", combined_display_source)))
    )
    missing_button_styles = set(REQUIRED_DISPLAY_BUTTON_STYLES) - set(
        discovered_button_styles
    )
    if missing_button_styles:
        raise SwissKnifeMetaWearablesDATIOSInteropError(
            f"meta-wearables-dat-ios DisplayAccess Swift source is missing button styles: "
            f"{sorted(missing_button_styles)}"
        )

    discovered_display_view_types = tuple(
        sorted(view_type for view_type in REQUIRED_DISPLAY_VIEW_TYPES if view_type in combined_display_source)
    )
    missing_display_view_types = set(REQUIRED_DISPLAY_VIEW_TYPES) - set(
        discovered_display_view_types
    )
    if missing_display_view_types:
        raise SwissKnifeMetaWearablesDATIOSInteropError(
            f"meta-wearables-dat-ios DisplayAccess Swift source is missing view types: "
            f"{sorted(missing_display_view_types)}"
        )

    return MetaWearablesDATIOSDisplayContract(
        root=str(root_path),
        display_access_doc_path=str(display_access_doc_path),
        session_lifecycle_doc_path=str(session_lifecycle_doc_path),
        permissions_registration_doc_path=str(permissions_registration_doc_path),
        display_info_plist_path=str(display_info_plist_path),
        display_view_model_path=str(display_view_model_path),
        car_maintenance_display_path=str(car_maintenance_display_path),
        device_session_states=discovered_session_states,
        info_plist_keys=discovered_info_plist_keys,
        background_modes=discovered_background_modes,
        display_icon_names=discovered_icon_names,
        display_button_styles=discovered_button_styles,
        display_view_types=discovered_display_view_types,
    )


def build_swissknife_meta_wearables_dat_ios_handoff(
    meta_wearables_dat_ios_root: str | Path,
    *,
    capability: str = "meta_wearables_dat_ios.display.session_handoff",
    payload: bytes | str | dict[str, Any] | None = None,
) -> SwissKnifeMetaWearablesDATIOSHandoff:
    """Build a deterministic iOS DAT Display handoff receipt."""
    contract = discover_meta_wearables_dat_ios_display_contract(meta_wearables_dat_ios_root)

    payload_bytes = _payload_to_bytes(
        payload
        if payload is not None
        else {
            "source": "swissknife",
            "target": "external/meta-wearables-dat-ios",
            "capability": capability,
            "route": "swissknife-meta-wearables-dat-ios-display-session",
            "device_session_states": list(contract.device_session_states),
            "info_plist_keys": list(contract.info_plist_keys),
            "background_modes": list(contract.background_modes),
            "display_icon_names": list(contract.display_icon_names),
            "display_button_styles": list(contract.display_button_styles),
            "display_view_types": list(contract.display_view_types),
        }
    )
    digest = hashlib.sha256(payload_bytes).hexdigest()
    return SwissKnifeMetaWearablesDATIOSHandoff(
        contract_id="swissknife.meta-wearables-dat-ios-display-interop@1",
        source_repository="swissknife",
        target_repository="external/meta-wearables-dat-ios",
        interface_contract=INTERFACE_CONTRACT,
        goal_id=GOAL_ID,
        goal_packet=GOAL_PACKET,
        capability=capability,
        route="swissknife-meta-wearables-dat-ios-display-session",
        content_cid=f"sha256:{digest}",
        payload_sha256=digest,
        payload_size_bytes=len(payload_bytes),
        device_session_states=contract.device_session_states,
        info_plist_keys=contract.info_plist_keys,
        background_modes=contract.background_modes,
        display_icon_names=contract.display_icon_names,
        display_button_styles=contract.display_button_styles,
        display_view_types=contract.display_view_types,
        required_swissknife_operations=REQUIRED_SWISSKNIFE_META_WEARABLES_DAT_IOS_OPERATIONS,
    )


def _payload_to_bytes(payload: bytes | str | dict[str, Any]) -> bytes:
    if isinstance(payload, bytes):
        return payload
    if isinstance(payload, str):
        return payload.encode("utf-8")
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
