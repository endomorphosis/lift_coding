#!/usr/bin/env python3
"""XPH-102 schema and Python/TypeScript conformance gate."""
from __future__ import annotations
import base64, copy, json, subprocess, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; MCP=ROOT/"Mcp-Plus-Plus"; VECTORS=MCP/"conformance/vectors"; PYTHON=MCP/"tests-py"; TYPESCRIPT=MCP/"tests-ts"; SCHEMAS=MCP/"schemas/profile-h/1.0"
sys.path.insert(0,str(PYTHON))
from validators.profile_h import ProfileHValidationError,canonical_profile_h_bytes,decode_x402_header,encode_x402_header,validate_profile_h_artifact,validate_replay,validate_request_binding  # noqa:E402
def load(name): return json.loads((VECTORS/name).read_text(encoding="utf-8"))
def invoke(case,by_id):
 if case["operation"]=="decode": decode_x402_header(case["kind"],case["encoded"]); return
 if case["operation"]=="replay": validate_replay({case["commitment"]},case["commitment"]); return
 source=copy.deepcopy(by_id[case["source"]]); payload=source["payload"]
 if case["operation"]=="artifact-mutate": payload[case["mutation"]["path"]]=case["mutation"]["value"]
 if case["operation"]=="artifact-redaction": payload["requirements"][0]["extra"]["walletAddress"]="0xsecret"
 if case.get("append_requirement"): payload["requirements"].append(copy.deepcopy(payload["requirements"][0]))
 if case["operation"] in ("artifact","artifact-mutate","artifact-redaction"): validate_profile_h_artifact(source["kind"],payload,case.get("limits"),now_ms=case.get("now_ms"))
 elif case["operation"]=="binding": validate_request_binding(case["expected_request_cid"],payload)
def python_report(valid,transport,invalid):
 by_id={x["id"]:x for x in valid["cases"]}; report={"artifacts":{},"transport":{},"invalid":{}}
 for x in valid["cases"]: report["artifacts"][x["id"]]={"canonical":base64.b64encode(canonical_profile_h_bytes(x["payload"])).decode(),"cid":validate_profile_h_artifact(x["kind"],x["payload"],now_ms=x.get("now_ms"))}
 for x in transport["cases"]:
  header=encode_x402_header(x["kind"],x["payload"]); report["transport"][x["id"]]={"canonical":base64.b64encode(canonical_profile_h_bytes(x["payload"])).decode(),"header":header,"decoded":decode_x402_header(x["kind"],header)}
 for x in invalid["cases"]:
  try: invoke(x,by_id); report["invalid"][x["id"]]={"accepted":True}
  except ProfileHValidationError as error: report["invalid"][x["id"]]={"code":error.code,"path":error.path}
 return report
def typescript_report():
 with tempfile.TemporaryDirectory(prefix="profile-h-ts-") as directory:
  command=["npx","tsc","src/profileH.ts","profile-h-vector-runner.ts","--outDir",directory,"--module","nodenext","--moduleResolution","nodenext","--target","es2022","--strict","--skipLibCheck","--types","node"]
  subprocess.run(command,cwd=TYPESCRIPT,check=True,capture_output=True,text=True)
  result=subprocess.run(["node",str(Path(directory)/"profile-h-vector-runner.js"),str(VECTORS)],cwd=TYPESCRIPT,check=True,capture_output=True,text=True)
  return json.loads(result.stdout)
def validate_schemas(valid,transport):
 import jsonschema
 artifacts=json.loads((SCHEMAS/"artifacts.schema.json").read_text()); x402=json.loads((SCHEMAS/"x402-v2.schema.json").read_text())
 jsonschema.Draft202012Validator.check_schema(artifacts); jsonschema.Draft202012Validator.check_schema(x402)
 av=jsonschema.Draft202012Validator(artifacts); xv=jsonschema.Draft202012Validator(x402)
 for x in valid["cases"]: av.validate(x["payload"])
 for x in transport["cases"]: xv.validate(x["payload"])
def main():
 valid,transport,invalid=(load(x) for x in ("profile_h_artifacts_valid.json","profile_h_transport_valid.json","profile_h_invalid.json")); validate_schemas(valid,transport); python=python_report(valid,transport,invalid)
 expected_invalid={x["id"]:{"code":x["expected_error"],"path":x["expected_path"]} for x in invalid["cases"]}
 if python["invalid"]!=expected_invalid: raise AssertionError(f"Python invalid-vector drift: {python['invalid']!r}")
 if {k:v["cid"] for k,v in python["artifacts"].items()}!=valid["expected_cids"]: raise AssertionError("published Profile H CIDs drifted")
 for x in transport["cases"]:
  extra=transport.get("expected_outputs",{}).get(x["id"],{}); canonical=x["expected_canonical"] or extra["canonical"]; header=x["expected_header"] or extra["header"]
  if base64.b64decode(python["transport"][x["id"]]["canonical"]).decode()!=canonical or python["transport"][x["id"]]["header"]!=header: raise AssertionError(f"published transport vector drifted: {x['id']}")
 typescript=typescript_report()
 if python!=typescript: raise AssertionError("Python and TypeScript reports differ byte-for-byte or CID-for-CID")
 required={"invalid-base64","invalid-amount","invalid-network","expired-quote","request-substitution","invalid-signature","replay","redaction-wallet-address","requirement-bound","artifact-size-bound"}
 if not required<={x["id"] for x in invalid["cases"]}: raise AssertionError("required negative vector category missing")
 docs=(MCP/"docs/generated/profile-h-schemas-1.0.md").read_text()
 if any(x not in docs for x in ("PaidCapability","PaymentQuote","PaymentAuthorization","PaymentVerification","SettlementReceipt","PaidEntitlement","UsageRecord","RefundRecord","AccessReceipt")): raise AssertionError("generated schema reference incomplete")
 print(f"PASS: Profile H 1.0 schemas and {len(valid['cases'])+len(transport['cases'])} valid/{len(invalid['cases'])} invalid vectors agree byte-for-byte and CID-for-CID in Python and TypeScript")
 return 0
if __name__=="__main__": raise SystemExit(main())
