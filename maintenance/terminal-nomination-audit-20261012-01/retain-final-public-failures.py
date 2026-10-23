"""Extend retained public failure history without replacing its earlier receipt."""
import hashlib
import json
from pathlib import Path
stage = Path(__file__).resolve().parent
def pin(name):
    body = (stage / name).read_bytes()
    return {"path": name, "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()}
old = pin("retained-public-harness-failures.json")
assert old["bytes"] == 2483 and old["sha256"] == "e6d7c99d6483e577a7a2bb0be333baac2c9a97f800abaa5eda112fc99bffbf42"
result = json.loads((stage / old["path"]).read_bytes())
report_name = "host-model-audit-03/qualification.json"
report = json.loads((stage / report_name).read_bytes())
assert report["qualified"] is False and report["observations"][0]["audit"]["status"] == "verified_all_observed_model_inputs"
assert report["observations"][1]["audit"]["reason"] == "audit_timeout"
result["cases"].append({"report": report_name, "report_pin": pin(report_name),
    "driver": "qualify-catalog-audit-attempt-03.py", "driver_pin": pin("qualify-catalog-audit-attempt-03.py"),
    "stage": "first compact-v2 current whole-model replay after verified expanded replay",
    "cause": "The collector's legacy hard ten-second limit silently capped the explicitly requested thirty seconds. The opt-in catalog collector and driver now permit up to thirty seconds within the caller budget and unchanged deadline reserve; legacy/default budgets remain unchanged.",
    "driver_capture": "Exact executed driver retained before adding pinned immutable instruction-artifact reuse and the tenth imported producer.",
    "qualified": False, "superseded_attempt_counted_as_pass": False,
    "private_key_or_provider_transcript_body_read": False})
result["previous_receipt_pin"] = old
output = stage / "retained-public-harness-failures-final.json"
assert not output.exists()
output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
print(json.dumps(pin(output.name)))
