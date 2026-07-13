#!/usr/bin/env python3
"""Validate XPH-114 documentation, examples, screenshots, and task accounting."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data/mcplusplus_profile_h/closeout-manifest.json"
BOARD = ROOT / "implementation_plan/docs/41-mcpplusplus-profile-h-x402-payments-plan-2026-07-12.todo.md"
TASK_RE = re.compile(r"^## (XPH-\d{3}) (.+?)\n(.*?)(?=^## XPH-|\Z)", re.MULTILINE | re.DOTALL)
STATUS_RE = re.compile(r"^- Status: (\S+)", re.MULTILINE)
VALIDATION_RE = re.compile(r"^- Validation: (.+)$", re.MULTILINE)
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


class Errors:
    def __init__(self) -> None:
        self.items: list[str] = []

    def require(self, condition: bool, message: str) -> None:
        if not condition:
            self.items.append(message)


def load_json(path: Path, errors: Errors) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.items.append(f"cannot load {path.relative_to(ROOT)}: {exc}")
        return {}
    if not isinstance(value, dict):
        errors.items.append(f"{path.relative_to(ROOT)} must contain a JSON object")
        return {}
    return value


def board_tasks(errors: Errors) -> dict[str, dict[str, str]]:
    text = BOARD.read_text(encoding="utf-8")
    tasks: dict[str, dict[str, str]] = {}
    for task_id, title, body in TASK_RE.findall(text):
        status = STATUS_RE.search(body)
        validation = VALIDATION_RE.search(body)
        errors.require(status is not None, f"{task_id} has no Status")
        errors.require(validation is not None, f"{task_id} has no Validation")
        tasks[task_id] = {
            "title": title,
            "status": status.group(1) if status else "",
            "validation": validation.group(1).strip() if validation else "",
        }
    errors.require(bool(tasks), "no XPH tasks were parsed from the taskboard")
    return tasks


def validate_docs(manifest: dict[str, Any], errors: Errors) -> None:
    required = {
        "docs/mcplusplus-profile-h-buyer-guide.md",
        "docs/mcplusplus-profile-h-seller-guide.md",
        "docs/mcplusplus-profile-h-operator-guide.md",
        "docs/mcplusplus-profile-h-migration-rollback.md",
    }
    declared = set(manifest.get("documentation", []))
    errors.require(required <= declared, f"documentation list is missing {sorted(required - declared)}")
    combined = ""
    for name in sorted(declared):
        path = ROOT / name
        errors.require(path.is_file(), f"documentation path does not exist: {name}")
        if path.is_file():
            text = path.read_text(encoding="utf-8")
            errors.require(len(text) >= 500, f"documentation is not substantive: {name}")
            combined += "\n" + text.lower()
    for phrase in (
        "exact", "upto", "batch", "testnet", "mainnet", "x402 v2",
        "wallet-provider", "reconciliation", "rollback", "raw key",
    ):
        errors.require(phrase in combined, f"documentation does not explain {phrase!r}")
    index = (ROOT / "docs/DOCUMENTATION_INDEX.md").read_text(encoding="utf-8")
    protocol_index = (ROOT / "Mcp-Plus-Plus/docs/index.md").read_text(encoding="utf-8")
    for name in required:
        errors.require(Path(name).name in index, f"documentation index does not link {name}")
        errors.require(Path(name).name in protocol_index, f"MCP++ documentation index does not link {name}")
    errors.require("closeout-manifest.json" in index and "closeout-manifest.json" in protocol_index,
                   "documentation indexes do not link the closeout manifest")


def validate_examples(manifest: dict[str, Any], errors: Errors) -> None:
    examples = manifest.get("configurationExamples", [])
    errors.require(len(examples) == 3, "exactly three seller, buyer, and pricing examples are required")
    values: dict[str, dict[str, Any]] = {}
    forbidden_keys = re.compile(r"(?i)(private.?key|mnemonic|seed.?phrase|secret.?key|wallet.?key)")
    for name in examples:
        path = ROOT / name
        errors.require(path.is_file(), f"configuration example does not exist: {name}")
        if not path.is_file():
            continue
        value = load_json(path, errors)
        values[name] = value
        raw = path.read_text(encoding="utf-8")
        errors.require(not forbidden_keys.search(raw), f"raw-key field is forbidden in {name}")
        errors.require(value.get("mode", "testnet") == "testnet", f"{name} must be testnet-only")
        errors.require(value.get("mainnetEnabled", False) is False, f"{name} enables mainnet")
        batch = value.get("batchSettlement")
        if batch is not None:
            errors.require(batch.get("enabled") is False, f"{name} enables batch settlement")
    seller = next((v for k, v in values.items() if "seller.testnet" in k), {})
    buyer = next((v for k, v in values.items() if "swissknife-buyer" in k), {})
    pricing = next((v for k, v in values.items() if "pricing.testnet" in k), {})
    errors.require(seller.get("x402Version") == 2 and seller.get("mode") == "testnet",
                   "seller example must select x402 v2 testnet")
    errors.require(str(seller.get("facilitator", {}).get("url", "")).startswith("https://"),
                   "seller facilitator must use HTTPS")
    provider = buyer.get("walletProvider", {})
    errors.require(bool(provider.get("type") and provider.get("accountAlias")),
                   "buyer must select a wallet provider by account alias")
    modes = {item.get("pricingMode"): item for item in pricing.get("capabilities", [])}
    errors.require({"exact", "upto", "batch"} <= set(modes), "pricing example must label exact, upto, and batch")
    errors.require(modes.get("batch", {}).get("enabled") is False, "batch pricing must be disabled")


def validate_screenshots(manifest: dict[str, Any], errors: Errors) -> None:
    screenshots = manifest.get("screenshots", [])
    kinds = {item.get("kind") for item in screenshots if isinstance(item, dict)}
    errors.require({"api-catalog-quote", "wallet-policy"} <= kinds,
                   "API catalog/quote and wallet screenshots are required")
    for item in screenshots:
        if not isinstance(item, dict):
            errors.items.append("screenshot entry must be an object")
            continue
        source = ROOT / str(item.get("source", ""))
        target = ROOT / str(item.get("path", ""))
        errors.require(source.is_file(), f"screenshot source does not exist: {item.get('source')}")
        if source.is_file():
            source_text = source.read_text(encoding="utf-8")
            declared_path = str(item.get("path"))
            capture_path = declared_path.removeprefix("swissknife/")
            errors.require(capture_path in source_text,
                           f"screenshot is not reproducibly captured: {item.get('path')}")
        errors.require(item.get("fixture") == "deterministic-not-live",
                       f"screenshot fixture disclosure is missing: {item.get('kind')}")
        # Screenshot artifacts are generated and restored by the supervisor.
        # When present, reject empty, renamed, or non-PNG evidence.
        if target.exists():
            errors.require(target.is_file() and target.stat().st_size > 1_000,
                           f"screenshot is empty: {item.get('path')}")
            if target.is_file():
                errors.require(target.read_bytes()[:8] == PNG_SIGNATURE,
                               f"screenshot is not PNG: {item.get('path')}")


def validate_tasks(manifest: dict[str, Any], tasks: dict[str, dict[str, str]], errors: Errors) -> None:
    rows = manifest.get("tasks", [])
    by_id = {row.get("id"): row for row in rows if isinstance(row, dict)}
    errors.require(len(by_id) == len(rows), "manifest has duplicate or malformed task entries")
    errors.require(set(by_id) == set(tasks),
                   f"task accounting differs: missing={sorted(set(tasks)-set(by_id))}, extra={sorted(set(by_id)-set(tasks))}")
    for task_id, parsed in tasks.items():
        row = by_id.get(task_id, {})
        expected_status = "active-closeout" if task_id == "XPH-114" else "completed"
        errors.require(row.get("status") == expected_status, f"{task_id} manifest status is not {expected_status}")
        errors.require(row.get("validation") == parsed["validation"], f"{task_id} validation command drifted")
        evidence = row.get("evidence", [])
        errors.require(bool(evidence), f"{task_id} has no linked validation evidence")
        for name in evidence:
            errors.require((ROOT / name).exists(), f"{task_id} evidence does not exist: {name}")
        if task_id != "XPH-114":
            errors.require(parsed["status"] == "completed", f"{task_id} is still {parsed['status']} on the board")
    closeout = manifest.get("supervisorCloseout", {})
    errors.require(closeout.get("requiredTaskCount") == len(tasks), "supervisor task count is stale")
    errors.require(closeout.get("completedBeforeCloseout") == len(tasks) - 1, "completed count is stale")
    errors.require(closeout.get("activeCloseoutTask") == "XPH-114", "active closeout task is wrong")
    for field in ("pendingRequiredTasksExcludingCloseout", "blockedRequiredTasks", "silentlySkippedRequiredTasks"):
        errors.require(closeout.get(field) == 0, f"supervisor closeout has nonzero {field}")
    errors.require(closeout.get("completionMetadataOwner") == "supervisor",
                   "closeout must leave final task metadata to the supervisor")


def main() -> int:
    errors = Errors()
    manifest = load_json(MANIFEST, errors)
    tasks = board_tasks(errors)
    errors.require(manifest.get("schema") == "mcp++/profile-h/closeout-manifest@1.0", "manifest schema is wrong")
    errors.require(manifest.get("profileVersion") == "1.0" and manifest.get("x402Version") == 2,
                   "manifest version selection is wrong")
    errors.require(manifest.get("releaseScope") == "testnet" and manifest.get("releaseDecision") == "GO",
                   "closeout is not a testnet GO")
    errors.require(manifest.get("mainnetEnabled") is False, "manifest enables mainnet")
    errors.require(manifest.get("pricingStatus") == {
        "exact": "testnet-ready", "upto": "testnet-ready", "batch": "disabled"
    }, "pricing rollout status is unsafe or ambiguous")
    validate_docs(manifest, errors)
    validate_examples(manifest, errors)
    validate_screenshots(manifest, errors)
    validate_tasks(manifest, tasks, errors)
    if errors.items:
        for item in errors.items:
            print(f"FAIL: {item}", file=sys.stderr)
        print(f"FAIL: {len(errors.items)} Profile H closeout error(s)", file=sys.stderr)
        return 1
    print(f"PASS: Profile H closeout accounts for {len(tasks)} tasks, testnet seller/buyer setup, docs, examples, and reproducible API/wallet evidence")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
