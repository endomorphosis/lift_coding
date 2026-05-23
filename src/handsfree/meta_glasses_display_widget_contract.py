"""Shared Meta glasses display widget bridge contract for backend emitters.

Keeps the Python-side mobile action ids and ORB operation names aligned with the
spec artifacts and mobile bridge contract.
"""

from __future__ import annotations

from typing import Final


DISPLAY_WIDGET_ACTION_CONTRACT: Final = "handsfree.meta-glasses/display-widget-action@0.1.0"

DISPLAY_WIDGET_ACTION_DEFINITIONS: Final[tuple[dict[str, str], ...]] = (
    {
        "action": "render",
        "operation": "render_widget",
        "id": "mobile_render_display_widget",
        "label": "Render Widget",
        "phrase": "render the display widget",
    },
    {
        "action": "update",
        "operation": "update_widget",
        "id": "mobile_update_display_widget",
        "label": "Update Widget",
        "phrase": "update the display widget",
    },
    {
        "action": "clear",
        "operation": "clear_widget",
        "id": "mobile_clear_display_widget",
        "label": "Clear Widget",
        "phrase": "clear the display widget",
    },
    {
        "action": "focus",
        "operation": "focus_next",
        "id": "mobile_focus_display_widget",
        "label": "Focus Widget",
        "phrase": "focus the display widget",
    },
    {
        "action": "activate",
        "operation": "activate",
        "id": "mobile_activate_display_widget_action",
        "label": "Activate Widget",
        "phrase": "activate the selected display widget action",
    },
    {
        "action": "reset",
        "operation": "reset_session",
        "id": "mobile_reset_display_widget_session",
        "label": "Reset Widget",
        "phrase": "reset the display widget session",
    },
    {
        "action": "play_video",
        "operation": "play_video",
        "id": "mobile_play_display_widget_video",
        "label": "Play Widget Video",
        "phrase": "play display widget video",
    },
    {
        "action": "subscribe_updates",
        "operation": "subscribe_updates",
        "id": "mobile_subscribe_display_widget_updates",
        "label": "Subscribe Widget Updates",
        "phrase": "subscribe to display widget updates",
    },
)

DISPLAY_WIDGET_ACTION_IDS: Final[tuple[str, ...]] = tuple(
    definition["id"] for definition in DISPLAY_WIDGET_ACTION_DEFINITIONS
)

DISPLAY_WIDGET_ORB_OPERATIONS: Final[tuple[str, ...]] = tuple(
    definition["operation"] for definition in DISPLAY_WIDGET_ACTION_DEFINITIONS
)
