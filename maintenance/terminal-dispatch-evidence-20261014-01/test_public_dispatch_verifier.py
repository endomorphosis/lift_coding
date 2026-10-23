"""Independent verifier adversarial tests using authored data, never native jobs."""
import ast
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import pytest

AB = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


v = load("independent_public_dispatch_verifier_test", AB / "verify_public_dispatch_evidence.py")
fixture = load("dispatch_authored_fixture_for_independent_verifier",
               AB / "checkout/test/api/test_checked_dispatch_evidence.py")


@pytest.fixture
def original(tmp_path, monkeypatch):
    owner = fixture.owner.__wrapped__(tmp_path, monkeypatch)
    material = fixture.materials.__wrapped__(owner)
    manifest = material["manifest"]
    scope = manifest["checked_observer_budget_scope"]
    context = v.structured_cid(scope)
    material["preparation"]["context_cid"] = context
    broker = material["broker_identity"]
    manifest["environment"] = [
        ["IPFS_ACCELERATE_CHECKED_CONTEXT_DISPATCH_CID", context],
        ["IPFS_ACCELERATE_CHECKED_CONTEXT_OWNER_BIRTH", v.canonical(
            {key: broker[key] for key in ("pid", "process_birth_id")}).decode()],
    ]
    material["manifest_signature"] = owner[1](manifest)

    def signed(changed=None, phase="prepared", nonce="1" * 32):
        chosen = material if changed is None else changed
        return fixture.e.build_dispatch_evidence(phase=phase, handoff_id=nonce,
            context_cid=chosen["preparation"]["context_cid"],
            manifest_id="sha256:" + v.digest(v.canonical(chosen["manifest"], signing=True)),
            materials=chosen, signer=owner[1])

    return material, signed, owner[1]


def verify(material, record):
    return v.verify_record(record, material, launch=material["manifest"],
                           launch_signature=material["manifest_signature"])


def test_independent_existing_profile_signature_and_exact_originals(original):
    material, sign, _ = original
    result = verify(material, sign())
    assert result["kernel"]["broker_dispatch_emitter"] == result["kernel"]["broker"]
    assert result["kernel"]["receipt_emitter"] is None
    assert result["outcome"]["receipt_emitter_origin_verified"] is False
    assert all(result[key] is False for key in v.AUTHORITY_NAMES)


@pytest.mark.parametrize("target", ["claim", "attempt_lease", "run_lease", "native_stdin", "allocation", "broker_identity"])
def test_changed_independent_original_refuses_even_with_unchanged_public_signature(original, target):
    material, sign, _ = original
    record = sign()
    changed = deepcopy(material)
    if target == "native_stdin":
        changed[target] += " extra"
    elif target == "allocation":
        changed[target]["lifecycle"]["workspace_path"] = "/worktrees/foreign"
    elif target == "broker_identity":
        changed[target]["start_time_ticks"] += 1
    else:
        changed[target]["fencing_token"] += 1
    with pytest.raises(v.VerificationError, match="material digest"):
        verify(changed, record)


def test_rehashed_tampered_signed_payload_still_refuses_signature(original):
    material, sign, _ = original
    record = sign()
    record["payload"]["handoff_id"] = "2" * 32
    record["record_id"] = "sha256:" + v.digest(v.canonical(record["payload"]))
    with pytest.raises(v.VerificationError, match="signature"):
        verify(material, record)


def test_rehashed_resigned_payload_cannot_invent_changed_attempt_fence(original):
    material, sign, profile_sign = original
    record = sign()
    record["payload"]["attempt_lease"]["fencing_token"] += 1
    record["record_id"] = "sha256:" + v.digest(v.canonical(record["payload"]))
    record["binding"] = profile_sign(record["payload"])
    with pytest.raises(v.VerificationError, match="reconstruct"):
        verify(material, record)


def test_rehashed_resigned_payload_cannot_turn_public_data_into_authority(original):
    material, sign, profile_sign = original
    record = sign()
    record["payload"]["serialized_live_authority"] = True
    record["record_id"] = "sha256:" + v.digest(v.canonical(record["payload"]))
    record["binding"] = profile_sign(record["payload"])
    with pytest.raises(v.VerificationError, match="authority"):
        verify(material, record)


def test_self_reported_log_emitter_refuses(original):
    material, sign, profile_sign = original
    record = sign()
    record["payload"]["kernel"]["receipt_emitter"] = record["payload"]["kernel"]["broker"]
    record["payload"]["outcome"]["receipt_emitter_origin_verified"] = True
    record["record_id"] = "sha256:" + v.digest(v.canonical(record["payload"]))
    record["binding"] = profile_sign(record["payload"])
    with pytest.raises(v.VerificationError, match="reconstruct"):
        verify(material, record)


@pytest.mark.parametrize("target", ["event_sequence", "release_bool"])
def test_resigned_bool_integer_confusion_refused(original, target):
    material, sign, profile_sign = original
    record = sign()
    if target == "event_sequence":
        record["payload"]["input"]["event_sequence"] = True
    else:
        record["payload"]["outcome"]["wrapper_release_confirmed"] = 0
    record["record_id"] = "sha256:" + v.digest(v.canonical(record["payload"]))
    record["binding"] = profile_sign(record["payload"])
    with pytest.raises(v.VerificationError, match="reconstruct"):
        verify(material, record)


def test_pid_reuse_breaks_kernel_birth_identity(original):
    material, _, _ = original
    changed = deepcopy(material["daemon_identity"])
    changed["start_time_ticks"] += 1
    with pytest.raises(v.VerificationError, match="birth hash"):
        v.birth(changed)


def test_real_profile_ascii_signature_differs_from_utf8_evidence_hash(original):
    material, sign, _ = original
    record = sign()
    assert b"\\u03bb" in v.canonical(material["manifest"], signing=True)
    assert "λ".encode() in v.canonical(material["manifest"])
    verify(material, record)


@pytest.mark.parametrize("raw", [b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":Infinity}', b'{"a":-Infinity}'])
def test_duplicate_and_nonfinite_json_refused(raw):
    with pytest.raises(v.VerificationError):
        v.strict_json(raw)


def test_public_input_symlink_refused(tmp_path):
    original = tmp_path / "data.json"
    original.write_bytes(b"{}")
    linked = tmp_path / "linked.json"
    linked.symlink_to(original)
    with pytest.raises(OSError):
        v.read_bytes(linked)


def test_oversized_public_input_refused(tmp_path):
    path = tmp_path / "data.json"
    path.write_bytes(b"{}")
    with pytest.raises(v.VerificationError, match="bound"):
        v.read_bytes(path, bound=1)


def test_verifier_has_no_runtime_import_or_launch_path():
    tree = ast.parse((AB / "verify_public_dispatch_evidence.py").read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert all(not item.name.startswith(("ipfs_", "subprocess", "socket")) for item in node.names)
        if isinstance(node, ast.ImportFrom):
            assert not (node.module or "").startswith(("ipfs_", "subprocess", "socket"))


def test_exact_sealed_AA18_public_signature_CID_and_artifact_domains():
    """Real public shapes, with no dependency downloads or original modifications."""
    public = AB.parent / "terminal-admitted-context-budget-20261013-01/actual-start-18/public"
    manifest = v.read_json(public / "native-launch-manifest.json")
    signature = v.read_json(public / "native-launch-signature.json")
    v.verify_signature(manifest, signature)
    admission = manifest["local_admission"]
    v.verify_signature(admission["manifest"]["payload"], admission["manifest"]["binding"],
                       expected_identity=signature["identity"], expected_profile=signature["profile_id"])
    assert v.structured_cid(admission) == manifest["checked_observer_budget_scope"]["admission_cid"]
    assert v.structured_cid(manifest["checked_observer_budget_scope"]) == dict(
        manifest["environment"])["IPFS_ACCELERATE_CHECKED_CONTEXT_DISPATCH_CID"]
    prepared = v.read_json(public / "native-dispatch-prepared-record.json")
    v.verify_cid(prepared["preparation"], "preparation_cid")
    v.verify_cid(prepared["preparation"]["event"], "event_cid")
    v.verify_sources(prepared["preflight"], admission)
    v.verify_public_artifacts(public, {"manifest": manifest, "admission": admission, "snapshot": prepared["preflight"]})
