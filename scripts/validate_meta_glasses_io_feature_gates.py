#!/usr/bin/env python3
"""Validate MGW-423 native DAT feature-gate documentation."""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Requirement:
    label: str
    needles: tuple[str, ...]


DOC_REQUIREMENTS: dict[str, tuple[Requirement, ...]] = {
    "docs/meta-glasses-expanded-io-physical-validation-checklist.md": (
        Requirement("Android DAT v0.7", ("android dat v0.7", "0.7.0")),
        Requirement("iOS DAT v0.7", ("ios dat v0.7", "0.7.0")),
        Requirement("display-capable device selection", ("display-capable", "selected display target")),
        Requirement("native optional gates", ("native dat camera", "native dat display", "optional")),
        Requirement("package credentials", ("package credentials", "sdk linkage")),
        Requirement("Developer Mode or release channel", ("developer mode", "release channel")),
        Requirement("app registration", ("app registration", "dam")),
        Requirement("firmware/app update state", ("firmware", "app update")),
        Requirement("paired hardware", ("paired hardware", "paired to")),
        Requirement("capability checks", ("capability checks", "runtime diagnostics")),
        Requirement("camera stream/photo capture", ("photo capture", "video stream")),
        Requirement("Bluetooth route diagnostics", ("bluetooth route", "microphone", "speaker", "headphone")),
        Requirement("Web Apps HTTPS deployment", ("web app", "https", "meta ai app")),
        Requirement("Neural Band input validation", ("neural band", "input")),
        Requirement("captouch input validation", ("captouch", "arrow", "enter")),
        Requirement("motion/GPS", ("motion", "gps")),
        Requirement("fallback evidence", ("fallback evidence", "reason")),
        Requirement("privacy review", ("privacy review", "redaction")),
        Requirement("rollback", ("rollback", "release channel")),
    ),
    "docs/meta-wearables-dat-display-physical-validation-checklist.md": (
        Requirement("display native optional gates", ("native dat display remains optional", "disabled by default")),
        Requirement("package credentials", ("package credentials", "dat_sdk_unlinked")),
        Requirement("Developer Mode or release channel", ("developer mode", "release channel")),
        Requirement("app registration", ("app registration", "dam")),
        Requirement("firmware/app update state", ("firmware_update_required", "dat_app_update_required")),
        Requirement("paired display-capable hardware", ("paired display-capable hardware", "target_required")),
        Requirement("capability checks", ("capability checks", "displaySdkLinked")),
        Requirement("DAT v0.7", ("dat v0.7", "0.7.0")),
        Requirement("Web Apps HTTPS fallback", ("web apps https", "fallback")),
        Requirement("privacy review", ("privacy review", "rollback")),
    ),
}


def _normalize(text: str) -> str:
    lowered = text.lower()
    return re.sub(r"\s+", " ", lowered)


def _check_docs() -> list[str]:
    failures: list[str] = []
    for relative_path, requirements in DOC_REQUIREMENTS.items():
        path = REPO_ROOT / relative_path
        if not path.exists():
            failures.append(f"missing required doc: {relative_path}")
            continue
        text = _normalize(path.read_text(encoding="utf-8"))
        for requirement in requirements:
            missing = [needle for needle in requirement.needles if needle.lower() not in text]
            if missing:
                failures.append(
                    f"{relative_path}: missing {requirement.label} evidence terms: {', '.join(missing)}"
                )
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate MGW-423 Meta glasses expanded I/O feature-gate docs."
    )
    parser.add_argument(
        "--check-docs",
        action="store_true",
        help="Check required feature-gate and physical-validation documentation.",
    )
    args = parser.parse_args()

    if not args.check_docs:
        parser.error("nothing to do; pass --check-docs")

    failures = _check_docs()
    if failures:
        for failure in failures:
            print(f"ERROR: {failure}")
        return 1

    print("MGW-423 feature-gate documentation checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
