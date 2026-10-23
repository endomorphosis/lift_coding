"""Assemble the three SVD-132 batch evidence files into one audit record.

The canonical single-run spec cannot finish inside its own 900 s budget
on this 2-core VM under co-tenant load (per-batch runs of the repo's own
runner + Playwright driver, via the runner's supported `manifest`
option, are the worklist-sanctioned alternative). This script merges
svd132-batch-{0,1,2}.json into svd132-batched-assembly.json with the
runner's evidence shape preserved per app, and reports totals. It does
NOT write svd-132-playwright.json — that filename belongs to the
canonical single run only.
"""

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
batch_files = sorted(HERE.glob("svd132-batch-*.json"))
batches = [json.loads(path.read_text()) for path in batch_files]

apps = [app for batch in batches for app in batch["apps"]]
assembly = {
    "schema": batches[0]["schema"],
    "task_id": batches[0]["task_id"],
    "driver": batches[0]["driver"],
    "assembly": (
        "gap-pass batched assembly of three runs of the repo's SVD-132 audit "
        "runner (runVirtualDesktopAppAudit + PlaywrightVirtualDesktopAppAuditDriver) "
        "over manifest batches of 15 entries, via the runner's manifest option; "
        "the canonical single-run spec exceeds its 900 s budget on this VM"
    ),
    "batches": [
        {
            "file": path.name,
            "generated_at": batch["generated_at"],
            "apps": len(batch["apps"]),
            "passed": sum(1 for a in batch["apps"] if a["status"] == "passed"),
            "screenshots": batch["summary"]["screenshot_count"],
        }
        for path, batch in zip(batch_files, batches)
    ],
    "summary": {
        "total_id_count": len(apps),
        "passed": sum(1 for a in apps if a["status"] == "passed"),
        "failed": sum(1 for a in apps if a["status"] != "passed"),
        "screenshot_count": sum(b["summary"]["screenshot_count"] for b in batches),
    },
    "apps": apps,
}
out = HERE / "svd132-batched-assembly.json"
out.write_text(json.dumps(assembly, indent=2) + "\n")
print(json.dumps(assembly["summary"], indent=2))
for app in apps:
    if app["status"] != "passed":
        print("FAILED:", app["requested_id"])
