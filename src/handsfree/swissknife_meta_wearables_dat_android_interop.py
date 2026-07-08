"""Interop contract between SwissKnife and ``external/meta-wearables-dat-android``.

HAO-735 repairs the VAIOS-G705 objective validation gap that requires
`swissknife` to interoperate with `external/meta-wearables-dat-android`
through importable contracts, interface descriptors, runtime handoff
behavior, and integration tests. This is part of the shared
`goal_packet/interoperability/swissknife/06921590135c` packet covering
VAIOS-G700, VAIOS-G701, VAIOS-G702, VAIOS-G703, VAIOS-G704, VAIOS-G705, and
VAIOS-G706.

`external/meta-wearables-dat-android` is the Meta Wearables Device Access
Toolkit (DAT) for Android. It ships agent-facing skill documentation
describing the on-device Display capability
(``.cursor/rules/display-access.mdc``), the ``DeviceSession``/``Display``
state machine (``.cursor/rules/session-lifecycle.mdc``), and the
registration/permission flow (``.cursor/rules/permissions-registration.mdc``),
plus a real ``DisplayAccess`` sample app whose manifest
(``samples/DisplayAccess/app/src/main/AndroidManifest.xml``) declares the
``com.meta.wearable.mwdat.APPLICATION_ID``/``CLIENT_TOKEN`` metadata keys and
``BLUETOOTH``/``BLUETOOTH_CONNECT``/``INTERNET`` permissions, and whose
``DisplayViewModel.kt`` exercises concrete ``IconName`` and ``ButtonStyle``
values when building glasses-side UI. This module statically discovers those
five descriptors (without compiling any Kotlin/Android code) and builds a
deterministic ``SwissKnifeMetaWearablesDATAndroidHandoff`` receipt that
mirrors the
``swissknife/src/services/mcp/meta-wearables-dat-android-display-interop-descriptor.ts``
runtime handoff descriptor on the SwissKnife side.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

INTERFACE_CONTRACT = "interface contract swissknife external/meta-wearables-dat-android"
GOAL_ID = "VAIOS-G705"
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

#: Agent-facing skill docs `external/meta-wearables-dat-android` ships that
#: describe the Display capability, session/stream lifecycle, and the
#: registration/permission flow.
REQUIRED_DISPLAY_ACCESS_DOC_PATH = ".cursor/rules/display-access.mdc"
REQUIRED_SESSION_LIFECYCLE_DOC_PATH = ".cursor/rules/session-lifecycle.mdc"
REQUIRED_PERMISSIONS_REGISTRATION_DOC_PATH = ".cursor/rules/permissions-registration.mdc"

#: The real DisplayAccess sample app manifest and view model that exercise
#: the Display capability end to end.
REQUIRED_DISPLAY_MANIFEST_PATH = "samples/DisplayAccess/app/src/main/AndroidManifest.xml"
REQUIRED_DISPLAY_VIEW_MODEL_PATH = (
    "samples/DisplayAccess/app/src/main/java/com/meta/wearable/dat/"
    "externalsampleapps/displayaccess/display/DisplayViewModel.kt"
)

#: ``DeviceSession``/``Display`` lifecycle states documented in the session
#: state table of ``session-lifecycle.mdc``.
REQUIRED_DEVICE_SESSION_STATES = (
    "IDLE",
    "STARTING",
    "STARTED",
    "PAUSED",
    "STOPPING",
    "STOPPED",
)

#: ``com.meta.wearable.mwdat.*`` manifest metadata keys the DAT SDK reads.
REQUIRED_MANIFEST_METADATA_KEYS = (
    "com.meta.wearable.mwdat.APPLICATION_ID",
    "com.meta.wearable.mwdat.CLIENT_TOKEN",
)

#: Android permissions the Display sample app declares.
REQUIRED_MANIFEST_PERMISSIONS = (
    "android.permission.BLUETOOTH",
    "android.permission.BLUETOOTH_CONNECT",
    "android.permission.INTERNET",
)

#: Built-in ``IconName`` values the DisplayAccess sample exercises when
#: sending glasses-side UI content.
REQUIRED_DISPLAY_ICON_NAMES = (
    "CHECKMARK",
    "TRIANGLE_LEFT_VERTICAL_LINE",
    "TRIANGLE_RIGHT_VERTICAL_LINE",
    "VIDEO_CAMERA",
)

#: Built-in ``ButtonStyle`` values the DisplayAccess sample exercises.
REQUIRED_DISPLAY_BUTTON_STYLES = ("PRIMARY", "SECONDARY")

#: SwissKnife-side MCP-IDL operations the handoff must support; kept in sync
#: with ``META_WEARABLES_DAT_ANDROID_DISPLAY_INTEROP_OPERATIONS`` in
#: ``swissknife/src/services/mcp/meta-wearables-dat-android-display-interop-descriptor.ts``.
REQUIRED_SWISSKNIFE_META_WEARABLES_DAT_ANDROID_OPERATIONS = (
    "meta_wearables_dat_android.registration.start",
    "meta_wearables_dat_android.registration.check_permission_status",
    "meta_wearables_dat_android.session.create",
    "meta_wearables_dat_android.session.start",
    "meta_wearables_dat_android.display.attach",
    "meta_wearables_dat_android.display.send_content",
)


class SwissKnifeMetaWearablesDATAndroidInteropError(RuntimeError):
    """Raised when either side of the swissknife/meta-wearables-dat-android contract is missing."""


@dataclass(frozen=True)
class MetaWearablesDATAndroidDisplayContract:
    """Static Display-capability/session-lifecycle contract discovered from the submodule."""

    root: str
    display_access_doc_path: str
    session_lifecycle_doc_path: str
    permissions_registration_doc_path: str
    display_manifest_path: str
    display_view_model_path: str
    device_session_states: tuple[str, ...]
    manifest_metadata_keys: tuple[str, ...]
    manifest_permissions: tuple[str, ...]
    display_icon_names: tuple[str, ...]
    display_button_styles: tuple[str, ...]


@dataclass(frozen=True)
class SwissKnifeMetaWearablesDATAndroidHandoff:
    """Deterministic receipt for one Display-capability handoff routed to SwissKnife."""

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
    display_icon_names: tuple[str, ...]
    display_button_styles: tuple[str, ...]
    required_swissknife_operations: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable receipt."""
        return asdict(self)


def discover_meta_wearables_dat_android_display_contract(
    root: str | Path,
) -> MetaWearablesDATAndroidDisplayContract:
    """Discover the Display-capability/session-lifecycle contract.

    Reads (without compiling) the descriptors that
    `external/meta-wearables-dat-android` ships so SwissKnife can rely on a
    stable, statically-verifiable contract:

    - ``.cursor/rules/display-access.mdc``
    - ``.cursor/rules/session-lifecycle.mdc``
    - ``.cursor/rules/permissions-registration.mdc``
    - ``samples/DisplayAccess/app/src/main/AndroidManifest.xml``
    - ``samples/DisplayAccess/app/src/main/java/com/meta/wearable/dat/
      externalsampleapps/displayaccess/display/DisplayViewModel.kt``
    """
    root_path = Path(root)
    if not root_path.exists():
        raise SwissKnifeMetaWearablesDATAndroidInteropError(
            f"meta-wearables-dat-android root not found: {root_path}"
        )

    display_access_doc_path = root_path / REQUIRED_DISPLAY_ACCESS_DOC_PATH
    session_lifecycle_doc_path = root_path / REQUIRED_SESSION_LIFECYCLE_DOC_PATH
    permissions_registration_doc_path = root_path / REQUIRED_PERMISSIONS_REGISTRATION_DOC_PATH
    display_manifest_path = root_path / REQUIRED_DISPLAY_MANIFEST_PATH
    display_view_model_path = root_path / REQUIRED_DISPLAY_VIEW_MODEL_PATH

    missing = [
        str(path)
        for path in (
            display_access_doc_path,
            session_lifecycle_doc_path,
            permissions_registration_doc_path,
            display_manifest_path,
            display_view_model_path,
        )
        if not path.exists()
    ]
    if missing:
        raise SwissKnifeMetaWearablesDATAndroidInteropError(
            f"meta-wearables-dat-android Display descriptors missing: {missing}"
        )

    display_access_source = display_access_doc_path.read_text(encoding="utf-8")
    for required_symbol in (
        "Wearables.createSession",
        "addDisplay",
        "sendContent",
        "flexBox",
        "DisplayState.STARTED",
    ):
        if required_symbol not in display_access_source:
            raise SwissKnifeMetaWearablesDATAndroidInteropError(
                f"meta-wearables-dat-android display-access.mdc is missing symbol: "
                f"{required_symbol}"
            )

    permissions_registration_source = permissions_registration_doc_path.read_text(
        encoding="utf-8"
    )
    for required_symbol in (
        "Wearables.startRegistration",
        "checkPermissionStatus",
        "RequestPermissionContract",
        "PermissionStatus.Granted",
    ):
        if required_symbol not in permissions_registration_source:
            raise SwissKnifeMetaWearablesDATAndroidInteropError(
                f"meta-wearables-dat-android permissions-registration.mdc is missing symbol: "
                f"{required_symbol}"
            )

    session_lifecycle_source = session_lifecycle_doc_path.read_text(encoding="utf-8")
    discovered_session_states = tuple(
        sorted(set(re.findall(r"`([A-Z]+)`\s*\|", session_lifecycle_source)))
    )
    missing_session_states = set(REQUIRED_DEVICE_SESSION_STATES) - set(discovered_session_states)
    if missing_session_states:
        raise SwissKnifeMetaWearablesDATAndroidInteropError(
            f"meta-wearables-dat-android session-lifecycle.mdc is missing states: "
            f"{sorted(missing_session_states)}"
        )

    manifest_source = display_manifest_path.read_text(encoding="utf-8")
    discovered_metadata_keys = tuple(
        sorted(
            set(
                name
                for name in re.findall(r'android:name="([^"]+)"', manifest_source)
                if name.startswith("com.meta.wearable.mwdat.")
            )
        )
    )
    missing_metadata_keys = set(REQUIRED_MANIFEST_METADATA_KEYS) - set(discovered_metadata_keys)
    if missing_metadata_keys:
        raise SwissKnifeMetaWearablesDATAndroidInteropError(
            f"meta-wearables-dat-android AndroidManifest.xml is missing metadata keys: "
            f"{sorted(missing_metadata_keys)}"
        )

    discovered_permissions = tuple(
        sorted(set(re.findall(r'uses-permission android:name="([^"]+)"', manifest_source)))
    )
    missing_permissions = set(REQUIRED_MANIFEST_PERMISSIONS) - set(discovered_permissions)
    if missing_permissions:
        raise SwissKnifeMetaWearablesDATAndroidInteropError(
            f"meta-wearables-dat-android AndroidManifest.xml is missing permissions: "
            f"{sorted(missing_permissions)}"
        )

    view_model_source = display_view_model_path.read_text(encoding="utf-8")
    discovered_icon_names = tuple(
        sorted(set(re.findall(r"IconName\.([A-Z_]+)", view_model_source)))
    )
    missing_icon_names = set(REQUIRED_DISPLAY_ICON_NAMES) - set(discovered_icon_names)
    if missing_icon_names:
        raise SwissKnifeMetaWearablesDATAndroidInteropError(
            f"meta-wearables-dat-android DisplayViewModel.kt is missing icon names: "
            f"{sorted(missing_icon_names)}"
        )

    discovered_button_styles = tuple(
        sorted(set(re.findall(r"ButtonStyle\.([A-Z_]+)", view_model_source)))
    )
    missing_button_styles = set(REQUIRED_DISPLAY_BUTTON_STYLES) - set(discovered_button_styles)
    if missing_button_styles:
        raise SwissKnifeMetaWearablesDATAndroidInteropError(
            f"meta-wearables-dat-android DisplayViewModel.kt is missing button styles: "
            f"{sorted(missing_button_styles)}"
        )

    return MetaWearablesDATAndroidDisplayContract(
        root=str(root_path),
        display_access_doc_path=str(display_access_doc_path),
        session_lifecycle_doc_path=str(session_lifecycle_doc_path),
        permissions_registration_doc_path=str(permissions_registration_doc_path),
        display_manifest_path=str(display_manifest_path),
        display_view_model_path=str(display_view_model_path),
        device_session_states=discovered_session_states,
        manifest_metadata_keys=discovered_metadata_keys,
        manifest_permissions=discovered_permissions,
        display_icon_names=discovered_icon_names,
        display_button_styles=discovered_button_styles,
    )


def build_swissknife_meta_wearables_dat_android_handoff(
    meta_wearables_dat_android_root: str | Path,
    *,
    capability: str = "meta_wearables_dat_android.display.session_handoff",
    payload: bytes | str | dict[str, Any] | None = None,
) -> SwissKnifeMetaWearablesDATAndroidHandoff:
    """Build a deterministic ``external/meta-wearables-dat-android`` to SwissKnife handoff receipt."""
    contract = discover_meta_wearables_dat_android_display_contract(
        meta_wearables_dat_android_root
    )

    payload_bytes = _payload_to_bytes(
        payload
        if payload is not None
        else {
            "source": "swissknife",
            "target": "external/meta-wearables-dat-android",
            "capability": capability,
            "route": "swissknife-meta-wearables-dat-android-display-session",
            "device_session_states": list(contract.device_session_states),
            "display_icon_names": list(contract.display_icon_names),
            "display_button_styles": list(contract.display_button_styles),
        }
    )
    digest = hashlib.sha256(payload_bytes).hexdigest()
    return SwissKnifeMetaWearablesDATAndroidHandoff(
        contract_id="swissknife.meta-wearables-dat-android-display-interop@1",
        source_repository="swissknife",
        target_repository="external/meta-wearables-dat-android",
        interface_contract=INTERFACE_CONTRACT,
        goal_id=GOAL_ID,
        goal_packet=GOAL_PACKET,
        capability=capability,
        route="swissknife-meta-wearables-dat-android-display-session",
        content_cid=f"sha256:{digest}",
        payload_sha256=digest,
        payload_size_bytes=len(payload_bytes),
        device_session_states=contract.device_session_states,
        display_icon_names=contract.display_icon_names,
        display_button_styles=contract.display_button_styles,
        required_swissknife_operations=REQUIRED_SWISSKNIFE_META_WEARABLES_DAT_ANDROID_OPERATIONS,
    )


def _payload_to_bytes(payload: bytes | str | dict[str, Any]) -> bytes:
    if isinstance(payload, bytes):
        return payload
    if isinstance(payload, str):
        return payload.encode("utf-8")
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
