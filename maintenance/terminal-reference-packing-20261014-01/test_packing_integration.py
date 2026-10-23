"""Actual pure codecs plus authored source restoration; no native owner runs.

Real owner entry/exit fault observations are performed only by packing_faults.py
against an explicitly selected completed owned run. These unit tests do not
claim an owner observation, read catalogs/CAS, or execute benchmark source.
"""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import tempfile

import pytest

from nested_context import CLAIMS, lift_context_strings, restore_context_strings, validate_source_complete
from test_nested_context import public_projections


def authored_variant_task(projection):
    from benchmarks.agent_supervisor.container_coding.terminal_semantic_context_transport import encode_context_packet
    from reference_codec import _envelope, canonical_packet_bytes
    rendered = projection["rendered"]
    core = json.loads(rendered)
    lifted = lift_context_strings(rendered)
    # Deterministic authored tables exercise real decoders. No optimizer,
    # tokenizer, learned nomination, provider or owner is invoked here.
    table = sorted([core["repository_id"], core["tree_id"]], key=lambda value: value.encode("utf-8"))
    return {"task_id": projection["task_id"], "projection": projection,
        "packing": {"variants": {
            "native_dictionary": {"wire": encode_context_packet(core)},
            "reference_original": {"wire": _envelope(core, canonical_packet_bytes(core), table)},
            "reference_lifted": {"wire": _envelope(lifted, canonical_packet_bytes(lifted), table)},
        }}}


@pytest.mark.parametrize("task", ["headless-terminal", "llm-inference-batching-scheduler",
                                  "feal-differential-cryptanalysis", "break-filter-js-from-html"])
def test_complete_native_lift_reference_decode_restore_integration(public_projections, task):
    from packing_run import restore_variant
    from reference_codec import decode_reference_packet
    projection = public_projections[task]["raw"]
    sample = authored_variant_task(projection)
    for name, variant in sample["packing"]["variants"].items():
        assert restore_variant(name, variant["wire"], projection["rendered"]) == projection["rendered"]
    restored_lift = decode_reference_packet(sample["packing"]["variants"]["reference_lifted"]["wire"])
    assert restore_context_strings(restored_lift) == projection["rendered"]
    instruction = json.loads(json.loads(projection["rendered"])["goal"]["instruction_json"])["instruction"].encode("utf-8")
    report = validate_source_complete(rendered=projection["rendered"], doc=restored_lift,
        instruction_bytes=instruction, source_views=projection["source_views"])
    assert report["all_source_views_raw"] is True
    assert report["native_provider_bytes_identical"] is True
    assert all(report[key] is False for key in CLAIMS)


@pytest.mark.parametrize("task", ["headless-terminal", "llm-inference-batching-scheduler",
                                  "feal-differential-cryptanalysis", "break-filter-js-from-html"])
def test_full_reencoded_tamper_and_promoted_provider_claims_refuse(public_projections, task):
    from packing_faults import packet_fault_controls
    report = packet_fault_controls(authored_variant_task(public_projections[task]["raw"]))
    assert report["positive_byte_exact_variants"] == 3
    assert len(report["controls"]) == 7
    assert all(row["refused"] is True for row in report["controls"])
    assert {row["control"] for row in report["controls"]} == {
        "rechecksummed_promoted_provider_claim", "rechecksummed_changed_decoded_hash",
        "reencoded_changed_lift_slot_hash", "reencoded_changed_full_instruction",
        "reencoded_weakened_native_requiredness", "reencoded_changed_restoration_guidance",
        "caller_context_changed_after_packing"}
    assert report["proof_authority"] is False
    assert report["full_task_satisfaction"] is False


def test_forged_decoder_envelope_checksum_cannot_admit_new_native_bindings(public_projections):
    from packing_faults import _rechecksum_envelope
    from packing_run import restore_variant
    from reference_codec import _envelope, canonical_packet_bytes, decode_reference_packet
    from nested_context import NestedContextError
    sample = authored_variant_task(public_projections["headless-terminal"]["raw"])
    original = sample["projection"]["rendered"]
    lifted = decode_reference_packet(sample["packing"]["variants"]["reference_lifted"]["wire"])
    lifted["context"]["scope"]["head"]["generation"] += 1
    encoded = _envelope(lifted, canonical_packet_bytes(lifted), [])
    assert decode_reference_packet(encoded)["context"]["scope"]["head"]["generation"] == 2
    with pytest.raises(NestedContextError):
        restore_variant("reference_lifted", encoded, original)
    # A transport checksum authenticates neither a head nor task completion.
    envelope = json.loads(encoded)
    envelope["claims"]["proof_authority"] = True
    with pytest.raises(ValueError, match="authority"):
        decode_reference_packet(_rechecksum_envelope(envelope))


@pytest.fixture
def copied_source():
    from packing_io import ROOT
    directory = Path(tempfile.mkdtemp(prefix="authored-source-restore-control-", dir=ROOT))
    path = directory/"source-repository"/"fixture.py"
    path.parent.mkdir()
    raw = b"# Authored restoration fixture; never executed.\nopaque_source = 'literal'\n"
    path.write_bytes(raw)
    try:
        yield path, raw
    finally:
        shutil.rmtree(directory)


def test_owned_source_fault_bytes_remain_changed_until_outer_finally_and_restore(copied_source):
    from packing_faults import MUTATION, owned_source_mutation
    path, original = copied_source
    before = path.stat()
    with owned_source_mutation(path, original) as mutation:
        # Mutation is deliberately applied after a putative callback entry.
        # It must remain visible after the callback returns, until owner exit.
        def authored_callback():
            mutation.apply()
            return {"private_provisional_data": True}
        provisional = authored_callback()
        assert provisional["private_provisional_data"] is True
        assert path.read_bytes() == original + MUTATION
    assert path.read_bytes() == original
    after = path.stat()
    assert (after.st_dev, after.st_ino, after.st_mtime_ns) == (before.st_dev, before.st_ino, before.st_mtime_ns)


def test_owned_source_restores_on_unexpected_exit_error(copied_source):
    from packing_faults import owned_source_mutation
    path, original = copied_source
    with pytest.raises(RuntimeError, match="authored unexpected observer failure"):
        with owned_source_mutation(path, original) as mutation:
            mutation.apply()
            assert path.read_bytes() != original
            raise RuntimeError("authored unexpected observer failure")
    assert path.read_bytes() == original


def test_partial_source_write_failure_still_restores_exact_bytes(copied_source, monkeypatch):
    import packing_faults as faults
    path, original = copied_source
    write = faults.os.write
    calls = 0
    def fail_after_partial_write(descriptor, raw):
        nonlocal calls
        calls += 1
        if calls == 1:
            return write(descriptor, raw[:max(1, len(raw)//2)])
        if calls == 2:
            raise OSError("authored partial write failure")
        return write(descriptor, raw)
    monkeypatch.setattr(faults.os, "write", fail_after_partial_write)
    with pytest.raises(OSError, match="partial write"):
        with faults.owned_source_mutation(path, original) as mutation:
            mutation.apply()
    assert path.read_bytes() == original


def test_source_hash_change_before_fault_refuses_without_mutation(copied_source):
    from packing_faults import PackingFaultError, owned_source_mutation
    path, original = copied_source
    path.write_bytes(original + b"different")
    changed = path.read_bytes()
    with pytest.raises(PackingFaultError):
        with owned_source_mutation(path, original):
            pytest.fail("changed copied source must not be admitted")
    assert path.read_bytes() == changed


def test_symlink_source_and_predecessor_locator_are_refused(copied_source):
    from packing_faults import PackingFaultError, owned_source_mutation
    path, original = copied_source
    link = path.parent/"link.py"; link.symlink_to(path)
    with pytest.raises(PackingFaultError, match="canonical"):
        with owned_source_mutation(link, original):
            pytest.fail("symlink source must not be admitted")
    predecessor = Path("/home/barberb/lift_coding/maintenance/terminal-source-capsules-20261014-01/experiment-04/source-repository/headless-terminal/environment/base_terminal.py")
    with pytest.raises(PackingFaultError, match="successor"):
        with owned_source_mutation(predecessor, original):
            pytest.fail("predecessor source must not be opened for a fault")
    assert path.read_bytes() == original


def test_oversize_source_and_repeated_mutation_refuse(copied_source):
    from packing_faults import MAX_SOURCE_BYTES, PackingFaultError, owned_source_mutation
    path, original = copied_source
    with pytest.raises(PackingFaultError, match="bounded"):
        with owned_source_mutation(path, b"x" * MAX_SOURCE_BYTES):
            pytest.fail("oversize source must not be opened")
    with owned_source_mutation(path, original) as mutation:
        mutation.apply()
        with pytest.raises(PackingFaultError, match="one bounded"):
            mutation.apply()
    assert path.read_bytes() == original


def authored_closed_result():
    """Closed-scope unit fixture only; it grants no native owner qualification."""
    from packing_io import FALSE
    from packing_run import POLICY
    return {"schema": "terminal-reference-packing-experiment@1", "completed": True,
        "policy": deepcopy(POLICY), "native_head": {"authored_fixture": "no owner receipt"},
        "source_count": 5, "task_count": 4, "native_capsule_inventory": {},
        "metadata_original_record_counts": {}, "context_compilations": 4,
        "exact_context_variant_roundtrips": 12, "local_script_pairs": 36,
        "artifact_pins": [], "provider_invocations": 0, "new_optimizer_updates": 0,
        "new_prover_invocations": 0, "source_body_execution": False,
        "planning_requirements_all_unresolved": True, "seconds": 0, "peak_rss_kib": 1, **FALSE}


@pytest.mark.parametrize("damage", ["extra_field", "missing_flag", "provider_bool", "provider_one", "source_counter_bool",
    "script_counter", "flag_zero", "source_execution", "resolved_requirements", "omission_policy", "incomplete"])
def test_closed_result_guards_reject_corruption_before_native_fault_admission(damage):
    from packing_verify import result_check
    result = authored_closed_result()
    result_check(result)
    if damage == "extra_field": result["invented_provider_receipt"] = {"tokens": 1}
    elif damage == "missing_flag": result.pop("proof_authority")
    elif damage == "provider_bool": result["provider_invocations"] = False
    elif damage == "provider_one": result["provider_invocations"] = 1
    elif damage == "source_counter_bool": result["source_count"] = True
    elif damage == "script_counter": result["local_script_pairs"] -= 1
    elif damage == "flag_zero": result["proof_authority"] = 0
    elif damage == "source_execution": result["source_body_execution"] = True
    elif damage == "resolved_requirements": result["planning_requirements_all_unresolved"] = False
    elif damage == "omission_policy": result["policy"]["all_task_sources_required"] = False
    elif damage == "incomplete": result["completed"] = False
    with pytest.raises(ValueError):
        result_check(result)


def test_closed_artifact_guard_rejects_modified_and_unknown_selected_artifacts(copied_source):
    from packing_io import sha
    from packing_run import FILES
    from packing_verify import artifact_check
    source, _ = copied_source
    output = source.parent.parent
    artifacts = []
    for name in sorted(FILES):
        raw = ("authored artifact data " + name).encode()
        (output/name).write_bytes(raw)
        artifacts.append({"relative_path": name, "bytes": len(raw), "sha256": sha(raw)})
    result = {"artifact_pins": artifacts}
    artifact_check(output, result)
    (output/FILES[0]).write_bytes(b"modified artifact")
    with pytest.raises(ValueError, match="changed"):
        artifact_check(output, result)
    result["artifact_pins"][0]["relative_path"] = "../outside.json"
    with pytest.raises(ValueError, match="scope"):
        artifact_check(output, result)
