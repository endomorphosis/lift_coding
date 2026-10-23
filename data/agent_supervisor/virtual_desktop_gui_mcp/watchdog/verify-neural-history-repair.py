"""Read-only R20 repair validation; acquisition is not GUI acceptance.

Staged fail-closed: after reviewing the eventual CANONICAL browser recording
and preservation receipt, the operator must pin their preflight SHA below.
No candidate-build browser recording can satisfy this validator.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import struct
import subprocess

ROOT = Path(__file__).resolve().parents[4]
SWISS = ROOT / "swissknife"
ARCHIVE = Path(__file__).resolve().parent / "smoke-receipts/neural-history"
# Intentionally unset until the actual canonical proof exists and is reviewed.
REVIEWED_PREFLIGHT_SHA256 = '425d9c0156e39ac7bcdc9e239869a6bb3a7cacc9f60c7cedfdc177f4df26ee2b'
SOURCES = {
    "swissknife/web/js/apps/neural-photoshop.js": "45f5b9a94cc1ca48282019fbe6c55d08a4ef4cbd57a1b46fe7efab1c568abfca",
    "swissknife/test/scripts/vdg-neural-photoshop-history-state.test.mjs": "5232e0a37f96c74a7fb22e9b7fb38639d6b729dcf93b4313c3d083a492489c36",
    "swissknife/test/e2e/smoke/vdg-neural-photoshop-history-smoke.mjs": "79652c1ff35ff4f9b428275f6d92ee605adeecd90e47034b8028a9ae874b5b33",
    "swissknife/test/scripts/vdg-neural-photoshop-truth.test.mjs": "42464bf1896d3cb0a95a0c87a11bd5e232e6877df468257ceb032db1ea4be7cc",
    "swissknife/scripts/rendered-control-rows.mjs": "fed110237552be81dcc46656b9210c60720a6b2e5bcd3482207368a8cb7305b7",
    "swissknife/web/js/main-simple.js": "b46037cf2eb8b3746db45e13ec07ffbedefa439fc6b0d15f0e16c85277c2c3ef",
    "swissknife/web/js/live-tool-gateway.js": "34d24769fde50cb0d526c843a0ee07ff5607f129e915037fc5054a783aab80d7",
    "swissknife/src/services/apps/all-app-executable-backend-contract.ts": "309b61af599d5e8aef812880d07ba201a32ccf852f355b49be1d19856f0941b2",
    "swissknife/src/services/apps/virtual-desktop-app-manifest.ts": "f679decd2f3a410de449632f90283c91ddaa90be0f4effefeb8457c7169f33f1",
    "swissknife/scripts/check-vdg-capture.cjs": "7ece23e30e3603185264c30699d3a7454bb4212bf0178234c00681e5f5786002",
    "swissknife/scripts/vdg-capture-fingerprint.cjs": "e120b7c7041d1b1b9bc0b9593f09861b537685bb1bb369956878f3ef73c44167",
    "swissknife/scripts/vdg-inventory-contract.cjs": "38ecb26d169c36de5893ce6526da9c848c1f5c02940b58aea04c218da15a9f94",
    "swissknife/scripts/vdg-connector-artifacts.cjs": "fc3564319f8a3b6151549ec28d76258aa8aa7524371de984a91276b201b30b15",
    "swissknife/scripts/mcpplusplus-profile-a.cjs": "df6d8b7cb651e9628c485405e891ced013622ff248145c6b34c6a1de6682d15b",
    "swissknife/scripts/vdg-capture-checkpoint.cjs": "ae8119786173e03de61076670cc65bf7c57e2e35d77903e84b74ed797821414a"
}
APP = "swissknife/web/js/apps/neural-photoshop.js"
OLD_APP_SHA256 = "6a8b1d79b86938981a8880aa653c6767eaf3d3d0635142b112b73fb35dae3125"
FAILURES = {
    "http": ("e025f5d56ed342a3eb5d41ea91be7776fdd831c82e64ffd123d126f71edd18e4", "0235-before-5ff3056b18.png", "db48e79c43f379c53bbbfca4e836fcda4796bc2c2415c8f53c9ed43bcf31db79"),
    "libp2p": ("ae0d3e6b4f5d35363b806f0e10cae917c3ce5e3a231b2069337abc9d34637873", "0235-before-5ff3056b18.png", "db48e79c43f379c53bbbfca4e836fcda4796bc2c2415c8f53c9ed43bcf31db79"),
}
SELECTOR = "#neural-history-panel-toggle"
FAMILIES = ("vdg-storage", "vdg-datasets", "vdg-accelerate", "vdg-network", "vdg-control", "vdg-local")
TRANSPORTS = ("http", "libp2p")
CELLS = {f"{family}/{transport}" for family in FAMILIES for transport in TRANSPORTS}
UNAFFECTED = {cell for cell in CELLS if not cell.startswith(("vdg-accelerate/", "vdg-local/"))}
COMPLETED_CELLS = set(UNAFFECTED)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def regular(path):
    require(path.is_file() and not path.is_symlink(), f"Expected regular proof file: {path}")
    return path


def exact(value, fields, label):
    require(type(value) is dict and set(value) == set(fields), f"Wrong {label} schema")


def integer(value, field, expected):
    require(type(value.get(field)) is int and value[field] == expected, f"Invalid {field}")


def no_authority(value):
    for field in ("gui_acceptance", "work_complete", "completion_authority"):
        require(value.get(field) is False, f"Repair proof cannot grant {field}")


def bound_json(path, digest):
    require(type(digest) is str and re.fullmatch(r"[a-f0-9]{64}", digest), "Reviewed proof digest is not pinned")
    require(sha(regular(path)) == digest, f"Reviewed proof bytes changed: {path}")
    return json.loads(path.read_text())


def png(path, digest):
    require(type(digest) is str and re.fullmatch(r"[a-f0-9]{64}", digest), "Invalid PNG digest")
    require(sha(regular(path)) == digest, f"PNG bytes changed: {path}")
    header = path.read_bytes()[:24]
    require(len(header) == 24 and header[:8] == b"\x89PNG\r\n\x1a\n" and header[12:16] == b"IHDR"
            and all(value > 0 for value in struct.unpack(">II", header[16:24])), f"Invalid actual PNG: {path}")


def tap(text, count):
    for key, expected in (("tests", count), ("pass", count), ("fail", 0), ("cancelled", 0), ("skipped", 0), ("todo", 0)):
        require(re.findall(rf"^# {key} (\d+)$", text, re.M) == [str(expected)], f"Wrong fresh TAP {key}")
    require(re.findall(r"^1\.\.(\d+)$", text, re.M) == [str(count)], "Wrong fresh TAP plan")
    require(len(re.findall(r"^ok \d+ - ", text, re.M)) == count and not re.search(r"^not ok\b", text, re.M),
            "Missing or failed actual test outcomes")


def verify_report(report, archive=ARCHIVE, root=ROOT):
    exact(report, ("schema", "source_sha256", "source_path", "project_root", "candidate_module_override", "route_interception",
                  "canonical_source_sha256", "passed", "viewport", "results", "gui_acceptance", "work_complete",
                  "completion_authority", "owned_resources", "owned_resources_closed", "screenshot_sha256"), "canonical browser report")
    no_authority(report)
    require(report["schema"] == "swissknife.vdg-neural-photoshop-history-smoke.v1" and report["passed"] is True,
            "Wrong or failed canonical browser proof")
    require(report["candidate_module_override"] is False and report["route_interception"] is False,
            "Candidate or intercepted browser proof cannot validate canonical repair")
    require(report["source_sha256"] == report["canonical_source_sha256"] == SOURCES[APP]
            and report["source_path"] == str(root / APP) and report["project_root"] == str(root / "swissknife"),
            "Browser proof is not bound to the actual canonical app")
    require(report["viewport"] == {"width": 720, "height": 540}, "Wrong actual capture geometry")
    resources = report["owned_resources"]
    exact(resources, ("server_pid", "browser_pid", "server_alive_after_cleanup", "browser_alive_after_cleanup"), "owned resources")
    require(all(type(resources[field]) is int and resources[field] > 0 for field in ("server_pid", "browser_pid"))
            and resources["server_pid"] != resources["browser_pid"], "Missing actual owned process identities")
    require(report["owned_resources_closed"] is True and resources["server_alive_after_cleanup"] is False
            and resources["browser_alive_after_cleanup"] is False, "Owned resources were not closed")
    profiles = report["results"]
    require(type(profiles) is list and len(profiles) == 2
            and [profile.get("transport_profile") for profile in profiles] == list(TRANSPORTS), "Both actual profiles are required")
    observations = []
    for profile, transport in zip(profiles, TRANSPORTS):
        exact(profile, ("transport_profile", "source_transport", "generation_transport", "actual_post_count", "trusted_confirmations",
                        "source_cid_verified", "generation_preview_only", "local_panel_collapse_reopen", "local_style_dismissal",
                        "pending_style_close_reopen", "later_generic_confirmation", "history_states", "page_errors", "observations"), "actual browser profile")
        # The reviewed smoke follows each source binding's declared transport
        # policy. A restricted read may use HTTP in the requested libp2p
        # profile; the inference preview must use the actual requested profile.
        require(profile["source_transport"] in TRANSPORTS and profile["generation_transport"] == transport,
                "Native requested/declared transport policy was not respected")
        integer(profile, "actual_post_count", 3); integer(profile, "trusted_confirmations", 3)
        for field in ("source_cid_verified", "generation_preview_only", "local_panel_collapse_reopen", "pending_style_close_reopen", "later_generic_confirmation"):
            require(profile[field] is True, f"Missing real native/browser behavior: {field}")
        require(profile["page_errors"] == [] and profile["local_style_dismissal"] == ["Escape", "backdrop", "Cancel"], "Browser errors or local modal regression")
        states = profile["history_states"]
        require(type(states) is list and len(states) == 5, "Missing actual history transitions")
        for state, label, expanded in zip(states, ("initial", "bound", "expanded", "collapsed", "reopened"), (False, False, True, False, False)):
            exact(state, ("label", "selector", "expanded", "accessible_name", "content_visible", "actual_control_count"), "actual history state")
            require(state["label"] == label and state["selector"] == SELECTOR
                    and state["expanded"] == str(expanded).lower()
                    and state["accessible_name"] == f"{'Collapse' if expanded else 'Expand'} history panel"
                    and state["content_visible"] is expanded, f"Wrong actual history state: {label}")
            integer(state, "actual_control_count", 1)
        rows = profile["observations"]
        require(type(rows) is list and len(rows) == 3, "Missing actual native owner calls")
        for observation, tool, owner, binding in zip(rows, ("ipfs_cat", "run_inference_job", "ipfs_cat"),
                ("ipfs_kit_py", "ipfs_accelerate_py", "ipfs_kit_py"), ("retrieve_content", "run_inference_job", "retrieve_content")):
            exact(observation, ("method", "route", "app_id", "binding_id", "owner", "tool_id", "transport", "correlation_id",
                                "policy_outcome", "dry_run", "outcome", "receipt_id", "event_dag_cid"), "actual native observation")
            require(observation["method"] == "POST" and observation["route"] == "/mcp/tools/call"
                    and observation["app_id"] == "neural-photoshop" and observation["tool_id"] == tool
                    and observation["owner"] == owner
                    and observation["transport"] == (transport if tool == "run_inference_job" else profile["source_transport"])
                    and observation["binding_id"] == f"neural-photoshop.{owner}.{binding}", "Native exact call identity mismatch")
            require(observation["outcome"] == "executed" and observation["policy_outcome"] == "require_confirmation"
                    and observation["dry_run"] is True, "Native preview/confirmation policy mismatch")
            require(type(observation["correlation_id"]) is str and observation["correlation_id"].startswith("desktop:neural-photoshop."), "Missing actual correlation")
            require(all(type(observation[field]) is str and re.fullmatch(r"b[a-z2-7]{58}", observation[field])
                        for field in ("receipt_id", "event_dag_cid")), "Missing actual receipt/event CIDs")
        observations.extend(rows)
    for field in ("correlation_id", "receipt_id", "event_dag_cid"):
        require(len({row[field] for row in observations}) == 6, f"Reused native {field}")
    expected_pngs = {f"{transport}-{name}.png" for transport in TRANSPORTS for name in
                    ("history-initial", "history-bound", "history-expanded", "history-collapsed", "history-reopened",
                     "style-before-close", "gateway-confirmation", "layout")}
    hashes = report["screenshot_sha256"]
    require(type(hashes) is dict and set(hashes) == expected_pngs, "Missing or unsafe actual screenshot set")
    directory = archive / "canonical"
    require({path.name for path in directory.glob("*.png")} == expected_pngs, "Actual screenshot directory differs")
    for name, digest in hashes.items():
        png(directory / name, digest)
    return observations


def verify_failure(archive=ARCHIVE):
    for transport, (digest, image, image_digest) in FAILURES.items():
        directory = archive / "actual-failure" / transport
        failure = bound_json(directory / "row.json", digest)
        row = failure["row"]
        require(f"accelerate-{transport}-" in failure["checkpoint"] and failure["row_index"] == 235
                and row["app_id"] == row["launch_id"] == "neural-photoshop"
                and row["selector"] == 'button[aria-label="Collapse history panel"]' and row["visibility"] == "not-visible"
                and row["clicked"] is False and row["failure_reasons"] == ["not-visible"]
                and row["pageerrors"] == [] and row["mcp_call_count"] == 0, "Original real failure provenance differs")
        require(failure["screenshot_sha256"] == image_digest, "Wrong actual failed screenshot binding")
        png(directory / image, image_digest)


def verify_preservation(record, live):
    exact(record, ("schema", "before_app_sha256", "after_app_sha256", "cells",
                   "gui_acceptance", "work_complete", "completion_authority"), "preservation receipt")
    no_authority(record)
    require(record["schema"] == "swissknife.vdg-neural-history-preservation.v2"
            and record["before_app_sha256"] == OLD_APP_SHA256 and record["after_app_sha256"] == SOURCES[APP], "Wrong preservation source boundary")
    require(type(record["cells"]) is dict and set(record["cells"]) == UNAFFECTED, "Exactly eight unaffected cells must be preserved")
    for cell, row in record["cells"].items():
        exact(row, ("before_input_fingerprint", "after_input_fingerprint", "run_id", "report_sha256"), "preserved cell")
        require(row["before_input_fingerprint"] == row["after_input_fingerprint"] == live["fingerprints"][cell],
                f"Unaffected source fingerprint changed: {cell}")
        actual = live["acquisitions"][cell]
        require(row["run_id"] == actual["run_id"] and row["report_sha256"] == actual["report_sha256"],
                f"Completed unaffected capture changed: {cell}")


def node_json(code, *arguments):
    process = subprocess.run(["node", "--input-type=commonjs", "-e", code, *map(str, arguments)], cwd=SWISS,
                             capture_output=True, text=True, timeout=120)
    require(process.returncode == 0, f"Read-only evidence check failed: {process.stderr[-4000:]}")
    return json.loads(process.stdout)



def live_evidence():
    return node_json('''
const fs=require('node:fs'),path=require('node:path');
const {inspectInventory}=require('./scripts/vdg-inventory-contract.cjs');
const {checkCapture}=require('./scripts/check-vdg-capture.cjs');
const {FAMILIES}=require('./scripts/vdg-evidence.cjs');
const {captureInputFingerprint}=require('./scripts/vdg-capture-fingerprint.cjs');
const root=process.cwd(),evidence=path.join(root,'test-results/virtual-desktop-ipfs-mcp-orb');
const inventory=inspectInventory({sourceRoot:root,evidenceRoot:evidence});
if(inventory.current!==true)throw Error('Current actual inventory is required: '+inventory.reason);
const acquisitions={},fingerprints={};
for(const family of Object.keys(FAMILIES))for(const transport of ['http','libp2p']){
 if(['vdg-accelerate','vdg-local'].includes(family))continue;
 fingerprints[family+'/'+transport]=captureInputFingerprint(family,transport,{sourceRoot:root,evidenceRoot:evidence,definition:FAMILIES[family]});
 const proof=checkCapture(family,transport,{sourceRoot:root,evidenceRoot:evidence});
 acquisitions[family+'/'+transport]=proof;
}
console.log(JSON.stringify({inventory,fingerprints,acquisitions}));
''')


def verify_receipts(observations):
    result = node_json('''
const fs=require('node:fs'),path=require('node:path'),os=require('node:os');
const {loadConnectorArtifacts}=require('./scripts/vdg-connector-artifacts.cjs');
const {cidForBytes}=require('./scripts/mcpplusplus-profile-a.cjs');
const rows=JSON.parse(process.argv[1]);
const root=path.join(os.homedir(),'.cache/swissknife/mcpplusplus-artifacts');
const proof=loadConnectorArtifacts(rows.map(row=>({app_id:row.app_id,binding_id:row.binding_id,owner:row.owner,observations:[row]})),{artifactRoot:root});
if(proof.problems.length||proof.observations.length!==6)throw Error('Actual six receipt/event blocks failed verification: '+JSON.stringify(proof.problems));
function records(value){const todo=[value],seen=new Set(),out=[];while(todo.length&&out.length<256){const item=todo.shift();if(!item||typeof item!=='object'||seen.has(item))continue;seen.add(item);out.push(item);if(Array.isArray(item))todo.push(...item);else{todo.push(...Object.values(item));if(item.type==='text'&&typeof item.text==='string'){try{todo.push(JSON.parse(item.text));}catch{}}}}return out;}
for(const row of rows){const receipt=JSON.parse(fs.readFileSync(path.join(root,'blocks',row.receipt_id),'utf8'));const found=records(receipt.result);
 if(row.tool_id==='ipfs_cat'){
  const cid=receipt.call.input?.payload?.cid;
  if(!cid||!found.some(value=>typeof value.bytes_base64==='string'&&cidForBytes(Buffer.from(value.bytes_base64,'base64'))===cid))throw Error('Actual source bytes/CID proof missing');
 }else if(!found.some(value=>value.body_executed===false&&value.mutation_performed===false)
    ||found.some(value=>value.task_id||value.job_id))throw Error('Inference preview did not prove no generated job/body execution');
}
console.log(JSON.stringify({receipt_event_pairs:6,source_reads:4,inference_previews:2}));
''', json.dumps(observations, separators=(",", ":")))
    require(result == {"receipt_event_pairs": 6, "source_reads": 4, "inference_previews": 2}, "Wrong actual native artifact counts")
    return result


def verify_ready_proof():
    receipt = bound_json(ARCHIVE / "canonical-preflight.json", REVIEWED_PREFLIGHT_SHA256)
    exact(receipt, ("schema", "source_sha256", "canonical_report_sha256", "preservation_sha256", "gui_acceptance", "work_complete", "completion_authority"), "reviewed canonical preflight")
    no_authority(receipt)
    require(receipt["schema"] == "swissknife.vdg-neural-history-canonical-preflight.v1" and receipt["source_sha256"] == SOURCES,
            "Wrong reviewed canonical source scope")
    for name, digest in SOURCES.items():
        require(sha(regular(ROOT / name)) == digest, f"Reviewed canonical source changed: {name}")
    verify_failure()
    report = bound_json(ARCHIVE / "canonical/result.json", receipt["canonical_report_sha256"])
    observations = verify_report(report)
    artifact_counts = verify_receipts(observations)
    preservation = bound_json(ARCHIVE / "preservation.json", receipt["preservation_sha256"])
    live = live_evidence()
    require(set(live["fingerprints"]) == UNAFFECTED and set(live["acquisitions"]) == COMPLETED_CELLS,
            "Eight unaffected fingerprints and completed acquisitions are required; Accelerate and Local need fresh captures")
    verify_preservation(preservation, live)
    command = ["node", "--test", "--test-reporter=tap", "test/scripts/vdg-neural-photoshop-history-state.test.mjs",
               "test/scripts/vdg-neural-photoshop-truth.test.mjs"]
    process = subprocess.run(command, cwd=SWISS, capture_output=True, text=True, timeout=120)
    print(process.stdout, end="")
    require(process.returncode == 0, f"Fresh27 app tests failed: {process.stderr}")
    tap(process.stdout, 27)
    for name, digest in SOURCES.items():
        require(sha(regular(ROOT / name)) == digest, f"Source changed during read-only verification: {name}")
    bound_json(ARCHIVE / "canonical-preflight.json", REVIEWED_PREFLIGHT_SHA256)
    final_report = bound_json(ARCHIVE / "canonical/result.json", receipt["canonical_report_sha256"])
    require(verify_report(final_report) == observations, "Browser observations changed during fresh tests")
    require(verify_receipts(observations) == artifact_counts, "Actual receipt artifacts changed during fresh tests")
    verify_failure()
    bound_json(ARCHIVE / "preservation.json", receipt["preservation_sha256"])
    require(live_evidence() == live, "Current inventory/acquisitions changed during fresh tests")
    return {"repair_validated": True, "canonical_product_preflight_validated": True,
            "fresh_tests": 27, "actual_profiles": 2, "actual_history_states": 10,
            "png_hashes_verified": 18, "acquisition_cells": len(live["acquisitions"]), "unaffected_cells_preserved": 8,
            "actual_native_transport_counts": {transport: sum(row["transport"] == transport for row in observations) for transport in TRANSPORTS},
            **artifact_counts, "all_12_acquisitions_and_six_strict_go_gates_still_required": True,
            "gui_acceptance": False, "work_complete": False, "completion_authority": False}


def main():
    print(json.dumps(verify_ready_proof(), sort_keys=True))


if __name__ == "__main__":
    main()
