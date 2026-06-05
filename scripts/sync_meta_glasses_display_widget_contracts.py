#!/usr/bin/env python3
"""Sync or verify Meta glasses display widget bridge contract modules.

This script treats spec/meta_glasses_display_widget_orb_interface.json as the
source artifact for the ordered ORB method list and mobile action ids, then
renders the repo-local Python and JS contract modules from that descriptor.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


SCRIPT_REPO_ROOT = Path(__file__).resolve().parents[1]
IPFS_ACCELERATE_ROOT = SCRIPT_REPO_ROOT / "external" / "ipfs_accelerate"
CONTRACT = "handsfree.meta-glasses/display-widget-action@0.1.0"

os.environ.setdefault("IPFS_ACCEL_SKIP_CORE", "1")
if str(IPFS_ACCELERATE_ROOT) not in sys.path:
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))

from ipfs_accelerate_py.agent_supervisor.wrapper_utils import build_repo_script_bootstrap  # noqa: E402
from ipfs_accelerate_py.agent_supervisor.interface_contract_codegen import (  # noqa: E402
    JavaScriptActionContractConfig,
    PythonActionContractConfig,
    build_configured_action_contract_sync_runner,
    operation_action_mapper,
)

_SCRIPT_BOOTSTRAP = build_repo_script_bootstrap(__file__)
SCRIPT_REPO_ROOT = _SCRIPT_BOOTSTRAP.script_repo_root
IPFS_ACCELERATE_ROOT = _SCRIPT_BOOTSTRAP.package_root
REPO_ROOT = _SCRIPT_BOOTSTRAP.repo_root
SPEC_PATH = REPO_ROOT / "spec" / "meta_glasses_display_widget_orb_interface.json"
PYTHON_CONTRACT_PATH = (
    REPO_ROOT / "src" / "handsfree" / "meta_glasses_display_widget_contract.py"
)
JS_CONTRACT_PATH = (
    REPO_ROOT
    / "mobile"
    / "src"
    / "utils"
    / "metaWearablesDatDisplayWidgetContract.js"
)

OPERATION_TO_ACTION = {
    "focus_next": "focus",
    "focus_previous": "focus",
    "render_widget": "render",
    "update_widget": "update",
    "clear_widget": "clear",
    "activate": "activate",
    "reset_session": "reset",
    "play_video": "play_video",
    "subscribe_updates": "subscribe_updates",
}

ACTION_METADATA = {
    "render": {
        "label": "Render Widget",
        "phrase": "render the display widget",
        "dat_method": "renderDisplayWidget",
    },
    "update": {
        "label": "Update Widget",
        "phrase": "update the display widget",
        "dat_method": "updateDisplayWidget",
    },
    "clear": {
        "label": "Clear Widget",
        "phrase": "clear the display widget",
        "dat_method": "clearDisplayWidget",
    },
    "focus": {
        "label": "Focus Widget",
        "phrase": "focus the display widget",
        "dat_method": "focusDisplayWidget",
    },
    "activate": {
        "label": "Activate Widget",
        "phrase": "activate the selected display widget action",
        "dat_method": "activateDisplayWidgetAction",
    },
    "reset": {
        "label": "Reset Widget",
        "phrase": "reset the display widget session",
        "dat_method": "resetDisplayWidgetSession",
    },
    "play_video": {
        "label": "Play Widget Video",
        "phrase": "play display widget video",
        "dat_method": "playDisplayWidgetVideo",
    },
    "subscribe_updates": {
        "label": "Subscribe Widget Updates",
        "phrase": "subscribe to display widget updates",
        "dat_method": "subscribeDisplayWidgetUpdates",
    },
}

PYTHON_CONTRACT_CONFIG = PythonActionContractConfig(
    contract_name="DISPLAY_WIDGET_ACTION_CONTRACT",
    definitions_name="DISPLAY_WIDGET_ACTION_DEFINITIONS",
    ids_name="DISPLAY_WIDGET_ACTION_IDS",
    operations_name="DISPLAY_WIDGET_ORB_OPERATIONS",
    docstring=(
        "Shared Meta glasses display widget bridge contract for backend emitters.\n\n"
        "Keeps the Python-side mobile action ids and ORB operation names aligned with the\n"
        "spec artifacts and mobile bridge contract."
    ),
)

JS_CONTRACT_CONFIG = JavaScriptActionContractConfig(
    contract_name="DISPLAY_WIDGET_ACTION_CONTRACT",
    ids_name="DISPLAY_WIDGET_ACTION_IDS",
    ids_set_name="DISPLAY_WIDGET_ACTION_ID_SET",
    action_by_id_name="DISPLAY_WIDGET_ACTION_BY_ACTION_ID",
    operation_by_id_name="DISPLAY_WIDGET_ORB_OPERATION_BY_ACTION_ID",
    validator_function_name="isDisplayWidgetActionId",
    extra_id_maps={
        "dat_method": "DISPLAY_WIDGET_DAT_METHOD_BY_ACTION_ID",
    },
)

ACTION_CONTRACT_SYNC_RUNNER = build_configured_action_contract_sync_runner(
    descriptor_path=SPEC_PATH,
    contract=CONTRACT,
    operation_to_action=operation_action_mapper(
        OPERATION_TO_ACTION,
        label="display widget operation",
    ),
    action_metadata=ACTION_METADATA,
    python_target_path=PYTHON_CONTRACT_PATH,
    python_config=PYTHON_CONTRACT_CONFIG,
    js_target_path=JS_CONTRACT_PATH,
    js_config=JS_CONTRACT_CONFIG,
    repo_root=REPO_ROOT,
    description="Sync or verify Meta glasses display widget contract modules.",
)
SYNC_CONFIG = ACTION_CONTRACT_SYNC_RUNNER.config


def main(argv: list[str] | None = None) -> int:
    return ACTION_CONTRACT_SYNC_RUNNER.run(argv)


if __name__ == "__main__":
    raise SystemExit(main())
