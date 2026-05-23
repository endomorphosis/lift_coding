#!/usr/bin/env python3
"""Sync or verify Meta glasses display widget bridge contract modules.

This script treats spec/meta_glasses_display_widget_orb_interface.json as the
source artifact for the ordered ORB method list and mobile action ids, then
renders the repo-local Python and JS contract modules from that descriptor.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
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

ACTION_TO_LABEL = {
    "render": "Render Widget",
    "update": "Update Widget",
    "clear": "Clear Widget",
    "focus": "Focus Widget",
    "activate": "Activate Widget",
    "reset": "Reset Widget",
    "play_video": "Play Widget Video",
    "subscribe_updates": "Subscribe Widget Updates",
}

ACTION_TO_PHRASE = {
    "render": "render the display widget",
    "update": "update the display widget",
    "clear": "clear the display widget",
    "focus": "focus the display widget",
    "activate": "activate the selected display widget action",
    "reset": "reset the display widget session",
    "play_video": "play display widget video",
    "subscribe_updates": "subscribe to display widget updates",
}

ACTION_TO_DAT_METHOD = {
    "render": "renderDisplayWidget",
    "update": "updateDisplayWidget",
    "clear": "clearDisplayWidget",
    "focus": "focusDisplayWidget",
    "activate": "activateDisplayWidgetAction",
    "reset": "resetDisplayWidgetSession",
    "play_video": "playDisplayWidgetVideo",
    "subscribe_updates": "subscribeDisplayWidgetUpdates",
}


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
    descriptor = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    definitions: list[dict[str, str]] = []
    for method in descriptor["methods"]:
        operation = str(method["name"])
        action_id = str(method["outputSchema"]["properties"]["type"]["const"])
        action = _action_from_operation(operation)
        definitions.append(
            {
                "action": action,
                "operation": operation,
                "id": action_id,
                "label": ACTION_TO_LABEL[action],
                "phrase": ACTION_TO_PHRASE[action],
                "dat_method": ACTION_TO_DAT_METHOD[action],
            }
        )
    return definitions


def _action_from_operation(operation: str) -> str:
    if operation in {"focus_next", "focus_previous"}:
        return "focus"
    if operation == "render_widget":
        return "render"
    if operation == "update_widget":
        return "update"
    if operation == "clear_widget":
        return "clear"
    if operation == "activate":
        return "activate"
    if operation == "reset_session":
        return "reset"
    if operation == "play_video":
        return "play_video"
    if operation == "subscribe_updates":
        return "subscribe_updates"
    raise ValueError(f"Unsupported display widget operation: {operation}")


def _render_python_module(definitions: list[dict[str, str]]) -> str:
    tuple_entries = "\n".join(
        [
            "    {\n"
            f'        "action": "{definition["action"]}",\n'
            f'        "operation": "{definition["operation"]}",\n'
            f'        "id": "{definition["id"]}",\n'
            f'        "label": "{definition["label"]}",\n'
            f'        "phrase": "{definition["phrase"]}",\n'
            "    },"
            for definition in definitions
        ]
    )
    return (
        '"""Shared Meta glasses display widget bridge contract for backend emitters.\n\n'
        "Keeps the Python-side mobile action ids and ORB operation names aligned with the\n"
        'spec artifacts and mobile bridge contract.\n"""\n\n'
        "from __future__ import annotations\n\n"
        "from typing import Final\n\n\n"
        f'DISPLAY_WIDGET_ACTION_CONTRACT: Final = "{CONTRACT}"\n\n'
        "DISPLAY_WIDGET_ACTION_DEFINITIONS: Final[tuple[dict[str, str], ...]] = (\n"
        f"{tuple_entries}\n"
        ")\n\n"
        "DISPLAY_WIDGET_ACTION_IDS: Final[tuple[str, ...]] = tuple(\n"
        '    definition["id"] for definition in DISPLAY_WIDGET_ACTION_DEFINITIONS\n'
        ")\n\n"
        "DISPLAY_WIDGET_ORB_OPERATIONS: Final[tuple[str, ...]] = tuple(\n"
        '    definition["operation"] for definition in DISPLAY_WIDGET_ACTION_DEFINITIONS\n'
        ")\n"
    )


def _render_js_module(definitions: list[dict[str, str]]) -> str:
    action_ids = "\n".join(f"  '{definition['id']}'," for definition in definitions)
    action_map = "\n".join(
        f"  {definition['id']}: '{definition['action']}',"
        for definition in definitions
    )
    operation_map = "\n".join(
        f"  {definition['id']}: '{definition['operation']}',"
        for definition in definitions
    )
    dat_method_map = "\n".join(
        f"  {definition['id']}: '{definition['dat_method']}',"
        for definition in definitions
    )
    return (
        f"export const DISPLAY_WIDGET_ACTION_CONTRACT =\n  '{CONTRACT}';\n\n"
        f"export const DISPLAY_WIDGET_ACTION_IDS = [\n{action_ids}\n];\n\n"
        "export const DISPLAY_WIDGET_ACTION_BY_ACTION_ID = {\n"
        f"{action_map}\n"
        "};\n\n"
        "export const DISPLAY_WIDGET_ORB_OPERATION_BY_ACTION_ID = {\n"
        f"{operation_map}\n"
        "};\n\n"
        "export const DISPLAY_WIDGET_DAT_METHOD_BY_ACTION_ID = {\n"
        f"{dat_method_map}\n"
        "};\n\n"
        "const DISPLAY_WIDGET_ACTION_ID_SET = new Set(DISPLAY_WIDGET_ACTION_IDS);\n\n"
        "export function isDisplayWidgetActionId(actionId) {\n"
        "  return DISPLAY_WIDGET_ACTION_ID_SET.has(actionId);\n"
        "}\n"
    )


def _write_if_needed(path: Path, content: str, *, check: bool, write: bool) -> bool:
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    if existing == content:
        return False
    if check:
        print(f"drift:{path.relative_to(REPO_ROOT)}")
        return True
    if write:
        path.write_text(content, encoding="utf-8")
        print(f"updated:{path.relative_to(REPO_ROOT)}")
        return True
    print(f"would-update:{path.relative_to(REPO_ROOT)}")
    return True


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if not args.check and not args.write:
        args.check = True

    definitions = _load_definitions()
    python_content = _render_python_module(definitions)
    js_content = _render_js_module(definitions)

    changed = False
    changed |= _write_if_needed(
        PYTHON_CONTRACT_PATH,
        python_content,
        check=bool(args.check),
        write=bool(args.write),
    )
    changed |= _write_if_needed(
        JS_CONTRACT_PATH,
        js_content,
        check=bool(args.check),
        write=bool(args.write),
    )

    return 1 if args.check and changed else 0


if __name__ == "__main__":
    raise SystemExit(main())