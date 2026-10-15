"""Retain explicit provider-free qualification failure history, never upgrading it."""
import hashlib
import json
from pathlib import Path

stage = Path(__file__).resolve().parent
cases = [
    {"report": "host-model-audit-01/qualification.json", "driver": "qualify-catalog-audit-attempt-01.py",
     "stage": "first genuine current expanded whole-model replay",
     "cause": "Auditor bundle witness closure late-bound its artifact variable to the retrieval file; final guard refused with VerifiedCodeRetrievalError. Production callback now binds original bundle inputs at definition.",
     "driver_capture": "Exact executed driver body reconstructed by removing the two later observation-retention assignments; executed report remains unchanged."},
    {"report": "host-model-audit-02/qualification.json", "driver": "qualify-catalog-audit-observation-retention-02.py",
     "stage": "instruction preparation on reused fresh signed fixture",
     "cause": "Immutable public-instruction artifact already existed; exclusive publication correctly refused. New qualification uses a separate fresh signed fixture, without deleting or replacing the retained artifact.",
     "driver_capture": "Executed driver retained before later unique-residual identity assertions were added."},
]
def pin(name):
    raw = (stage / name).read_bytes()
    return {"path": name, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
for case in cases:
    receipt = json.loads((stage / case["report"]).read_bytes())
    assert receipt["qualified"] is False and "failure" in receipt
    case.update(report_pin=pin(case["report"]), driver_pin=pin(case["driver"]),
        qualified=False, superseded_attempt_counted_as_pass=False, private_key_or_provider_transcript_body_read=False)
result = {"schema": "catalog-audit-retained-public-qualification-failures@1", "cases": cases,
    "failed_attempts_retained_and_not_upgraded": True, "scope": "Explicit fresh public fixture reports and evidence scripts only; no private owner database or credential bodies included."}
output = stage / "retained-public-harness-failures.json"
assert not output.exists()
output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
print(json.dumps(pin(output.name)))
