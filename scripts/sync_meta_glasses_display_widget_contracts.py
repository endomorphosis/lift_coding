#!/usr/bin/env python3
"""Sync or verify Meta glasses display widget bridge contract modules.

This script treats spec/meta_glasses_display_widget_orb_interface.json as the
source artifact for the ordered ORB method list and mobile action ids, then
renders the repo-local Python and JS contract modules from that descriptor.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
IPFS_ACCELERATE_ROOT = REPO_ROOT / "external" / "ipfs_accelerate"
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
CONTRACT = "handsfree.meta-glasses/display-widget-action@0.1.0"

os.environ.setdefault("IPFS_ACCEL_SKIP_CORE", "1")
if str(IPFS_ACCELERATE_ROOT) not in sys.path:
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))

from ipfs_accelerate_py.agent_supervisor.interface_contract_codegen import (  # noqa: E402
    ActionContractSyncTarget,
    JavaScriptActionContractConfig,
    PythonActionContractConfig,
    load_action_definitions_from_descriptor,
    operation_action_mapper,
    render_js_action_contract,
    render_python_action_contract,
    sync_contract_targets,
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


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Sync or verify Meta glasses display widget contract modules.",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Overwrite the Python and JS contract modules with generated content.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail if the generated content differs from the checked-in modules.",
    )
    return parser


def _load_definitions() -> list[dict[str, str]]:
    return load_action_definitions_from_descriptor(
        SPEC_PATH,
        operation_to_action=operation_action_mapper(
            OPERATION_TO_ACTION,
            label="display widget operation",
        ),
        action_metadata=ACTION_METADATA,
    )


def _render_python_module(definitions: list[dict[str, str]]) -> str:
    return render_python_action_contract(
        definitions,
        contract=CONTRACT,
        config=PYTHON_CONTRACT_CONFIG,
    )


def _render_js_module(definitions: list[dict[str, str]]) -> str:
    return render_js_action_contract(
        definitions,
        contract=CONTRACT,
        config=JS_CONTRACT_CONFIG,
    )


def _write_if_needed(path: Path, content: str, *, check: bool, write: bool) -> bool:
    return sync_contract_targets(
        (ActionContractSyncTarget(path, content),),
        check=check,
        write=write,
        repo_root=REPO_ROOT,
    )


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if not args.check and not args.write:
        args.check = True

    definitions = _load_definitions()
    python_content = _render_python_module(definitions)
    js_content = _render_js_module(definitions)

    changed = sync_contract_targets(
        (
            ActionContractSyncTarget(PYTHON_CONTRACT_PATH, python_content),
            ActionContractSyncTarget(JS_CONTRACT_PATH, js_content),
        ),
        check=bool(args.check),
        write=bool(args.write),
        repo_root=REPO_ROOT,
    )

    return 1 if args.check and changed else 0


if __name__ == "__main__":
    raise SystemExit(main())
