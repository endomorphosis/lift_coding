#!/usr/bin/env python3
"""Validate resolved Expo config for DAT display mode lanes."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate DAT display lane in resolved Expo config.")
    parser.add_argument("--mode", choices=("disabled", "enabled"), required=True)
    parser.add_argument("--config-path", required=True)
    return parser.parse_args()


def _load_plugin_options(config_path: Path) -> dict | None:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    for entry in config.get("plugins", []):
        if isinstance(entry, list) and "expo-meta-wearables-dat/app.plugin.js" in str(entry[0]):
            if len(entry) > 1 and isinstance(entry[1], dict):
                return entry[1]
            return {}
    return None


def main() -> int:
    args = _parse_args()
    plugin_options = _load_plugin_options(Path(args.config_path))
    if plugin_options is None:
        print("expo-meta-wearables-dat plugin configuration was not found in resolved expo config")
        return 1

    expected_enabled = args.mode == "enabled"
    actual_enabled = bool(plugin_options.get("enableDisplay"))
    if actual_enabled != expected_enabled:
        print(
            f"MWDAT_DISPLAY_MODE={args.mode} expected enableDisplay={expected_enabled}, got {actual_enabled}"
        )
        return 1

    print(f"Validated DAT lane {args.mode}: enableDisplay={actual_enabled}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

