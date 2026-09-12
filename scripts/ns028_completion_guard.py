"""Protected NS028 evidence gate. Verifies retained bytes; never runs experiments.

The root authority file is a separately protected baseline input. It admits exact
host offers/public keys and independently reviewed native execution evidence.
Worker-authored profiles, receipt judgments and verifier keys are not authority.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import re

PAPER = "papers/completion/neurosymbolic_supervision/"
SERVICE = PAPER + "qualification/production_provider/pilot_service/"
# Exact independently reviewed current verifier; no import from a receipt path.
CLIENT_SHA = "81e8758031abe1102992987e5bee8830039c68c9599fc0d2665012515fa544a9"
AUTHORITY = "scripts/ns028_completion_authority.json"
UNITS = ("ns-hist-05-dnspython", "ns-hist-06-bottle", "ns-hist-07-idna", "ns-hist-08-protego")
HARNESSES = ("native_import", "admit_final_attempt", "missing_freeze_refused",
             "stale_freeze_refused", "current_source_profile", "consumed_replay_refused")


def require(ok, message):
    if not ok:
        raise ValueError("NS028 evidence gate: " + message)


def canon(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def cell_id(unit, arm, repetition):
    return sha(canon(dict(unit=unit, arm=arm, repetition=repetition,
                          cache="local_cold", record_kind="pilot")))


def verify(root, receipt):
    root = Path(root).resolve()
    outputs, artifacts = receipt.get("outputs", {}), receipt.get("artifacts", {})

    def raw_file(name, maximum=4 * 1024 * 1024):
        require(isinstance(name, str), "file name is not text")
        rel = Path(name)
        require(not rel.is_absolute() and ".." not in rel.parts, "unsafe file path")
        path = root / rel
        require(path.resolve() == path and path.is_file() and path.stat().st_size <= maximum,
                "missing, redirected or oversized file: " + name)
        return path.read_bytes()

    def evidence(name):
        snapshot = outputs.get(name)
        require(isinstance(snapshot, str) and snapshot in artifacts,
                "required evidence lacks a task snapshot: " + name)
        raw = raw_file(snapshot)
        require(sha(raw) == artifacts[snapshot], "evidence snapshot changed: " + name)
        return raw

    def data(name):
        return json.loads(evidence(name))

    rows = [json.loads(line) for line in evidence(PAPER + "pilot/results.jsonl").splitlines() if line]
    expected = {cell_id(u, a, r): (u, a, r) for u in UNITS for a in ("A", "B") for r in (0, 1, 2)}
    require(len(rows) == 24 and len({r.get("cell_id") for r in rows}) == 24
            and {r.get("cell_id") for r in rows} == set(expected), "exact 24 unique pilot cells required")
    for row in rows:
        unit, arm, repetition = expected[row["cell_id"]]
        require((row.get("task_id"), row.get("arm"), row.get("repetition")) == (unit, arm, repetition)
                and type(row.get("repetition")) is int and row.get("record_kind") == "pilot"
                and row.get("cache") == "local_cold" and row.get("split") == "pilot",
                "row identity differs from fixed pilot population")
        require(row.get("terminal") is True and row.get("status") in
                ("completed", "passed", "failed", "unavailable", "terminal_failed"),
                "pending or nonterminal pilot row cannot complete NS028")

    freeze_raw = evidence(PAPER + "artifacts/final_experiment_freeze.json")
    freeze = json.loads(freeze_raw)
    arms = freeze.get("retained_executable_arms")
    require(arms == ["A", "B"],
            "nonempty exact pre-outcome retained arms ['A', 'B'] required; no post-outcome arm removal")
    require(freeze.get("freeze_sha256") == sha(canon({k: v for k, v in freeze.items() if k != "freeze_sha256"})),
            "final freeze self-hash differs")
    require(freeze.get("first_final_attempt_started") is False, "pilot gate cannot retrospectively freeze final outcomes")

    authority = json.loads(raw_file(AUTHORITY))
    require(authority.get("schema") == "ns028-root-completion-authority/v1"
            and authority.get("task_id") == "NS-028" and authority.get("approved") is True,
            "root completion authority has not admitted actual evidence")
    require(authority.get("client_sha256") == CLIENT_SHA and authority.get("retained_arms") == arms,
            "root verifier/retained-arm authority differs")
    require(authority.get("freeze_file_sha256") == sha(freeze_raw), "final freeze lacks exact root admission")
    final_raw = evidence(PAPER + "protocol/final_run_manifest.json")
    final = json.loads(final_raw)
    require(authority.get("final_manifest_file_sha256") == sha(final_raw)
            and final.get("freeze_sha256") == freeze["freeze_sha256"]
            and final.get("first_final_attempt_started") is False,
            "final manifest does not bind the reviewed pre-final freeze")

    pins = freeze.get("immutable_pins")
    require(isinstance(pins, dict) and pins and pins == authority.get("source_pins"),
            "freeze source pins differ from protected root authority")
    for name, digest in pins.items():
        require(isinstance(digest, str) and re.fullmatch("[0-9a-f]{64}", digest), "invalid source pin")
        raw = evidence(name) if name in outputs else raw_file(name, 64 * 1024 * 1024)
        require(sha(raw) == digest, "frozen source bytes changed: " + name)

    harness = authority.get("native_harness")
    require(isinstance(harness, dict), "actual native harness admission missing")
    proof_raw = evidence(harness["evidence_path"])
    require(sha(proof_raw) == harness.get("evidence_sha256"), "native harness evidence differs from root admission")
    proof = json.loads(proof_raw)
    require(proof.get("schema") == "ns028-root-native-harness-execution/v1"
            and proof.get("executed") is True and proof.get("fixture") is False
            and proof.get("execution_kind") == "actual_native_python_import_and_call"
            and all(proof.get("checks", {}).get(k) is True for k in HARNESSES),
            "actual native import and required execution controls are absent")
    require(proof.get("source_path") == harness.get("source_path")
            and proof.get("source_sha256") == harness.get("source_sha256") == pins.get(harness.get("source_path")),
            "native harness source identity differs")
    command = proof.get("command", {})
    require(type(command.get("exit_code")) is int and command["exit_code"] == 0
            and isinstance(command.get("argv"), list) and command["argv"]
            and command.get("log") == harness.get("log_path")
            and sha(evidence(harness["log_path"])) == harness.get("log_sha256"),
            "actual native harness command/log binding missing")

    client_path = root / SERVICE / "pilot_client.py"
    require(sha(raw_file(SERVICE + "pilot_client.py")) == CLIENT_SHA, "reviewed signature verifier source changed")
    spec = importlib.util.spec_from_file_location("ns028_protected_pilot_verifier", client_path)
    client = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(client)
    cells = authority.get("cells")
    require(isinstance(cells, dict) and set(cells) == set(expected), "all 24 root-issued host authorities required")
    for unit in UNITS:
        mechanism = {}
        for arm in ("A", "B"):
            profiles = [cells[cell_id(unit, arm, r)]["binding"]["profile"] for r in (0, 1, 2)]
            profile = profiles[0]
            require(all(p == profile for p in profiles) and profile.get("implemented_arm") == arm
                    and profile.get("implemented_cache") == "local_cold",
                    "pre-outcome arm mechanism changes across matched repetitions")
            mechanism[arm] = profile.get("mechanism_profile_sha256")
            require(isinstance(mechanism[arm], str) and re.fullmatch("[0-9a-f]{64}", mechanism[arm]),
                    "actual arm mechanism commitment is absent")
        require(mechanism["A"] != mechanism["B"], "labels on the same mechanism cannot instantiate A/B")
    useful = {arm: 0 for arm in arms}
    verified_cells = []
    for row in rows:
        cid = row["cell_id"]
        entry = cells[cid]
        binding = entry["binding"]
        require(binding.get("cell_id") == cid and binding.get("batch_sha256") == authority.get("batch_sha256"),
                "root cell/batch binding differs")
        prefix = PAPER + "pilot/host_receipts/" + cid + "/"
        offer_raw = evidence(prefix + "offer.json")
        require(sha(offer_raw) == entry.get("offer_sha256") == binding.get("offer_sha256"),
                "offer not admitted by the protected root authority")
        offer = json.loads(offer_raw)
        require(offer.get("public_key_sha256") == entry.get("public_key_sha256"), "untrusted host verifier key")
        request = offer["request"]
        unit, arm, repetition = expected[cid]
        require((request.get("unit"), request.get("arm"), request.get("repetition"), request.get("cell_id"))
                == (unit, arm, repetition, cid), "offered cell identity differs")
        for key in client.REQUEST_KEYS - {"schema", "request_id"}:
            require(request.get(key) == binding.get(key), "root request binding differs: " + key)
        require(offer.get("profile") == binding.get("profile") and offer.get("source_sha256") == binding.get("source_sha256"),
                "root source/profile binding differs")
        terminal_name = entry.get("terminal_filename")
        require(terminal_name in ("response.json", "disposition.json"), "unadmitted terminal evidence name")
        raw = evidence(prefix + terminal_name)
        require(sha(raw) == entry.get("terminal_sha256"), "signed terminal bytes differ from root admission")
        signed = json.loads(raw)
        if terminal_name == "disposition.json":
            d = signed.get("receipt", {})
            original_name = "proposal.json" if d.get("original_filename") == "proposal_result.json" else "response.json"
            original, disposition = client.verify_disposition(offer, signed, evidence(prefix + original_name), binding)
            require(row.get("counts_as_live_repair") is False and row.get("live_repair_admitted") is False,
                    "failed disposition cannot receive repair credit")
            verified_cells.append({"cell_id": cid, "terminal_failed": True, "useful": False})
            continue
        body = client.verify_signature(offer, signed)
        client.receipt_scope(body, offer, binding)
        require(body.get("status") == "completed" and body.get("error") is None
                and body.get("provider_invoked") is True and body.get("served_profile_admitted") is True
                and body.get("historical_pilot_unit_admitted") is True
                and body.get("provider_termination", {}).get("termination_proven") is True,
                "actual terminated, admitted proposal is absent")
        require(body.get("operator_review_kind") == "ai_operator"
                and body.get("trust_scope") == "specific_reviewed_pilot_candidate_only"
                and body.get("automatic_adversarial_scorer_integrity_qualified") is False,
                "candidate review scope is absent or overclaims integrity")
        review_raw = evidence(prefix + "operator_review.json")
        review = json.loads(review_raw)
        require(sha(review_raw) == body.get("operator_review_sha256") and review.get("approved") is True
                and review.get("binding") == body.get("operator_review_binding"), "actual bound candidate review absent")
        rb = review["binding"]
        require(all(rb.get(k) == body.get(k) for k in ("grant_sha256", "candidate_sha256", "source_sha256", "batch_sha256", "cell_id")),
                "review names a different candidate/cell")
        score = body.get("scorer", {})
        require(score.get("schema") == "ns-historical-cold-host-result/v1" and score.get("split") == "pilot"
                and score.get("unit_id") == unit and score.get("candidate_sha256") == body.get("candidate_sha256")
                and score.get("manifest_sha256") == body.get("manifest_sha256"), "independent cold score identity differs")
        details = score.get("scorer", {})
        nonempty = all(type(details.get(k)) is int and details[k] > 0 for k in ("visible_collected", "hidden_collected"))
        passed = (nonempty and score.get("success") is True and details.get("success") is True
                  and type(score.get("container_exit_code")) is int and score["container_exit_code"] == 0
                  and score.get("timed_out") is False
                  and all(type(details.get(k + "_passed")) is int and details[k + "_passed"] == details[k + "_collected"] for k in ("visible", "hidden")))
        require(row.get("counts_as_live_repair") is passed and row.get("live_repair_admitted") is passed,
                "row repair credit differs from actual independently signed cold result")
        if passed and arm in useful:
            useful[arm] += 1
        verified_cells.append({"cell_id": cid, "terminal_failed": False, "useful": passed})
    require(all(useful[arm] > 0 for arm in arms), "every retained arm needs an actual useful independently cold-scored witness")
    return {"schema": "ns028-protected-completion-check/v1", "terminal_cells": 24,
            "useful_witnesses": useful, "root_authority_sha256": sha(raw_file(AUTHORITY)),
            "client_sha256": CLIENT_SHA, "verified_cells": verified_cells,
            "new_provider_calls": 0, "new_scorer_calls": 0,
            "scope": "Exact reviewed pilot candidates only; no final or adversarial scorer admission."}
