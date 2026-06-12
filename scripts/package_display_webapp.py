#!/usr/bin/env python3
"""Package the Meta Ray-Ban Display Web App for static HTTPS hosting."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import shutil
import zipfile
from pathlib import Path
from typing import Any

from handsfree.display_webapp_compat import evaluate_display_webapp_readiness


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_DIR = REPO_ROOT / "dev" / "meta-rayban-display-simulator" / "webapp"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "build" / "meta-rayban-display-webapp"
PACKAGE_MANIFEST = "package-manifest.json"


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Required JSON file does not exist: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _ensure_relative_file(source_dir: Path, relative_path: str) -> Path:
    if not relative_path or Path(relative_path).is_absolute():
        raise ValueError(f"Static file path must be relative: {relative_path!r}")

    source_root = source_dir.resolve()
    file_path = (source_root / relative_path).resolve()
    if source_root != file_path and source_root not in file_path.parents:
        raise ValueError(f"Static file path escapes package root: {relative_path}")
    if not file_path.is_file():
        raise FileNotFoundError(f"Declared static file does not exist: {relative_path}")
    return file_path


def _rewrite_deployment_url(
    readiness: dict[str, Any],
    deployment_url: str | None,
) -> dict[str, Any]:
    if not deployment_url:
        return readiness

    updated = copy.deepcopy(readiness)
    updated["deployment_url"] = deployment_url
    for widget in updated.get("widgets", []):
        if isinstance(widget, dict) and widget.get("webapp_target") is True:
            widget["deployment_url"] = deployment_url
    return updated


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _copy_static_files(
    source_dir: Path,
    output_dir: Path,
    static_files: list[str],
    readiness: dict[str, Any],
) -> list[dict[str, Any]]:
    copied: list[dict[str, Any]] = []
    for relative_path in static_files:
        source_path = _ensure_relative_file(source_dir, relative_path)
        target_path = output_dir / relative_path
        target_path.parent.mkdir(parents=True, exist_ok=True)
        if relative_path == "readiness.json":
            _write_json(target_path, readiness)
        else:
            shutil.copy2(source_path, target_path)
        copied.append(
            {
                "path": relative_path,
                "bytes": target_path.stat().st_size,
                "sha256": _sha256(target_path),
            }
        )
    return copied


def _build_package_manifest(
    readiness: dict[str, Any],
    files: list[dict[str, Any]],
    source_dir: Path,
) -> dict[str, Any]:
    return {
        "schema": "handsfree.meta-rayban-display/webapp-package",
        "schema_version": "0.1.0",
        "package_id": readiness.get("package_id"),
        "entrypoint": "index.html",
        "deployment_url": readiness.get("deployment_url"),
        "source_dir": str(source_dir),
        "readiness_file": "readiness.json",
        "manifest_file": readiness.get("manifest", {}).get("path", "manifest.webmanifest"),
        "hosting": readiness.get("hosting", {}),
        "files": files,
    }


def _write_zip(output_dir: Path, zip_path: Path) -> None:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file_path in sorted(path for path in output_dir.rglob("*") if path.is_file()):
            archive.write(file_path, file_path.relative_to(output_dir).as_posix())


def package_webapp(
    source_dir: Path,
    output_dir: Path,
    deployment_url: str | None = None,
    zip_path: Path | None = None,
) -> dict[str, Any]:
    source_dir = source_dir.resolve()
    output_dir = output_dir.resolve()
    readiness = _rewrite_deployment_url(_load_json(source_dir / "readiness.json"), deployment_url)
    lint_result = evaluate_display_webapp_readiness(readiness)
    if not lint_result.get("ready"):
        failures = ", ".join(lint_result.get("failure_ids", []))
        raise ValueError(f"Display Web App readiness failed: {failures}")

    static_files = readiness.get("static_files")
    if not isinstance(static_files, list) or not all(
        isinstance(path, str) for path in static_files
    ):
        raise ValueError("readiness.json must declare static_files as a list of relative paths.")
    for required_path in ("index.html", "manifest.webmanifest", "readiness.json"):
        if required_path not in static_files:
            raise ValueError(f"readiness.json static_files must include {required_path}.")

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)
    files = _copy_static_files(source_dir, output_dir, static_files, readiness)
    manifest = _build_package_manifest(readiness, files, source_dir)
    _write_json(output_dir / PACKAGE_MANIFEST, manifest)

    if zip_path is not None:
        _write_zip(output_dir, zip_path.resolve())

    return {
        "ok": True,
        "output_dir": str(output_dir),
        "zip_path": str(zip_path.resolve()) if zip_path is not None else None,
        "package_manifest": str(output_dir / PACKAGE_MANIFEST),
        "readiness": lint_result,
        "files": files,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Package the Meta Ray-Ban Display Web App for HTTPS glasses loading."
    )
    parser.add_argument(
        "--source-dir",
        default=str(DEFAULT_SOURCE_DIR),
        help="Source Web App directory containing readiness.json.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Output directory for the hostable static package.",
    )
    parser.add_argument(
        "--deployment-url",
        help="Final public HTTPS URL to write into readiness.json before packaging.",
    )
    parser.add_argument(
        "--zip",
        dest="zip_path",
        help="Optional zip archive path to create from the packaged output directory.",
    )
    args = parser.parse_args()

    result = package_webapp(
        Path(args.source_dir),
        Path(args.output_dir),
        deployment_url=args.deployment_url,
        zip_path=Path(args.zip_path) if args.zip_path else None,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
