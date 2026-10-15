"""Retain the first fresh installed fixture setup failure without replacing history."""
import hashlib
import json
from pathlib import Path
stage = Path(__file__).resolve().parent
def pin(name):
    raw = (stage / name).read_bytes()
    return {"path": name, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
old = pin("retained-public-harness-failures-final.json")
assert old["bytes"] == 3856 and old["sha256"] == "cc90e02d71d1e47336f516256de5c5b274fe813594baaea18442632d6e002ede"
result = json.loads((stage / old["path"]).read_bytes())
name = "installed-audit-qualification-01/qualification.json"
report = json.loads((stage / name).read_bytes())
assert report["qualified"] is False and report["fresh_qualification_container_removed"] is True
result["cases"].append({"report": name, "report_pin": pin(name),
    "driver": "qualify-installed-audit-attempt-01.py", "driver_pin": pin("qualify-installed-audit-attempt-01.py"),
    "stage": "record public original source baseline in fresh minimal Python container",
    "cause": "Minimal fixture image did not include Git before deployment; the first qualification container was removed. Controller now installs Git before recording the original public baseline, then uses production deployment and detaches external networking before context/audit.",
    "qualified": False, "superseded_attempt_counted_as_pass": False,
    "private_key_or_provider_transcript_body_read": False})
result["previous_receipt_pin"] = old
output = stage / "retained-public-harness-failures-installed.json"
assert not output.exists()
output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
print(json.dumps(pin(output.name)))
