#!/usr/bin/env python3
"""Independently join public dispatch evidence; never recreate live authority.

This file imports no supervisor, datasets, budget, database, or worker modules.
The supplied public launch is a trust input. A valid signature proves a binding
to that launch's signer; it does not attest loaded code or a private database.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import stat
import sys

MAX_FILE_BYTES = 8 * 1024 * 1024
MAX_RECORD_BYTES = 262_144
MAX_RECORDS = 64
FALSE_AUTHORITY = {
    "execution_authority": False,
    "proof_authority": False,
    "completion_authority": False,
    "serialized_live_authority": False,
    "loaded_module_code_attested": False,
    "source_to_model_equivalence_proved": False,
    "convergence_proved": False,
    "provider_usage_measured": False,
}


class VerificationError(ValueError):
    """Public evidence is malformed, unauthenticated, or inconsistently joined."""


def need(condition, message):
    if not condition:
        raise VerificationError(message)


def canonical(value, *, signing=False):
    """Profile signatures use ASCII JSON; receipt hashes use canonical UTF-8."""
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=signing, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, UnicodeError, RecursionError) as error:
        raise VerificationError("bounded finite canonical JSON required") from error


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def descriptor(value):
    raw = canonical(value)
    return {"bytes": len(raw), "sha256": digest(raw)}


def stamp(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_uid, info.st_gid,
            info.st_nlink, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def read_bytes(path, *, bound=MAX_FILE_BYTES):
    """Read one explicit public artifact with no link traversal or writes."""
    path = Path(path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        need(stat.S_ISREG(before.st_mode) and 0 <= before.st_size <= bound,
             "public artifact exceeds its regular-file bound")
        parts, total = [], 0
        while total <= bound:
            part = os.read(fd, min(65536, bound + 1 - total))
            if not part:
                break
            parts.append(part)
            total += len(part)
        raw = b"".join(parts)
        need(len(raw) == before.st_size and stamp(before) == stamp(os.fstat(fd))
             == stamp(path.lstat()), "public artifact changed during bounded read")
        return raw
    finally:
        os.close(fd)


def strict_json(raw):
    need(type(raw) is bytes and len(raw) <= MAX_FILE_BYTES,
         "bounded public JSON bytes required")

    def unique(items):
        result = {}
        for key, item in items:
            need(key not in result, "duplicate public JSON field")
            result[key] = item
        return result

    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=unique,
                          parse_constant=lambda _: (_ for _ in ()).throw(
                              VerificationError("nonfinite public JSON")))
    except (UnicodeError, ValueError, RecursionError) as error:
        raise VerificationError("malformed public JSON") from error


def read_json(path, *, bound=MAX_FILE_BYTES):
    return strict_json(read_bytes(path, bound=bound))


def did_public_key(identity):
    need(type(identity) is str and identity.startswith("did:key:z")
         and len(identity) <= 128, "exact Ed25519 did:key identity required")
    alphabet = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    encoded, number = identity[9:], 0
    for character in encoded:
        need(character in alphabet, "invalid base58 did:key identity")
        number = number * 58 + alphabet.index(character)
    raw = number.to_bytes((number.bit_length() + 7) // 8, "big")
    raw = b"\0" * (len(encoded) - len(encoded.lstrip("1"))) + raw
    need(len(raw) == 34 and raw[:2] == b"\xed\x01",
         "Ed25519 public multicodec required")
    return raw[2:]


def verify_signature(payload, signature, *, expected_identity=None,
                     expected_profile=None):
    need(type(signature) is dict and set(signature)
         == {"identity", "signature", "profile_id"}, "closed profile signature required")
    need(type(signature["profile_id"]) is str and signature["profile_id"],
         "profile signature identity missing")
    if expected_identity is not None:
        need(signature["identity"] == expected_identity,
             "dispatch signature uses another launch identity")
    if expected_profile is not None:
        need(signature["profile_id"] == expected_profile,
             "dispatch signature uses another launch profile")
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        from cryptography.exceptions import InvalidSignature
        raw = base64.b64decode(signature["signature"].encode("ascii"), validate=True)
        need(len(raw) == 64, "exact Ed25519 signature required")
        Ed25519PublicKey.from_public_bytes(did_public_key(signature["identity"])).verify(
            raw, canonical(payload, signing=True))
    except (InvalidSignature, UnicodeError, ValueError, TypeError) as error:
        raise VerificationError("Ed25519 public signature rejected") from error


def structured_cid(value):
    """CIDv1 / dag-json / sha2-256 for the public structured identity domain."""
    raw = b"\x01\xa9\x02\x12\x20" + hashlib.sha256(canonical(value)).digest()
    return "b" + base64.b32encode(raw).decode("ascii").lower().rstrip("=")


def verify_cid(value, key):
    need(type(value) is dict and key in value, "structured content identity missing")
    body = {name: item for name, item in value.items() if name != key}
    need(value[key] == structured_cid(body), "public structured content identity differs")


def require_false(value, keys):
    need(type(value) is dict and all(value.get(key) is False for key in keys),
         "public evidence incorrectly declares live or semantic authority")


SCHEMA = "supervisor-checked-dispatch-evidence@1"
PHASES = ("prepared", "wrapper_released", "worker_released", "worker_observed")
MATERIAL_NAMES = {
    "manifest", "manifest_signature", "admission", "claim", "attempt_lease",
    "run_lease", "allocation", "preparation", "snapshot", "native_stdin",
    "broker_identity", "daemon_identity", "wrapper_identity", "sudo_identity",
    "worker_identity", "parent_chain", "observation", "receipt_emitter_identity",
}
AUTHORITY_NAMES = {
    "serialized_live_authority", "execution_authority", "mutation_authority",
    "completion_authority", "proof_authority", "convergence_proved",
    "provider_usage_measured", "full_task_satisfaction", "current_owner_verified",
}
BIRTH_NAMES = {"pid", "uid", "parent_pid", "start_time_ticks", "boot_id", "process_birth_id"}
CLAIM_NAMES = {
    "task_cid", "task_revision", "attempt_id", "claim_id", "attempt_number",
    "lease_id", "owner_session_id", "fencing_token", "fence_epoch", "grant_id",
    "client_id", "store_id", "process_birth_id", "peer_pid", "peer_uid",
    "peer_start_time_ticks", "grant_expires_at_ms",
}
LEASE_NAMES = {"lease_id", "owner_session_id", "fencing_token", "fence_epoch", "expires_at_ms"}
ATTEMPT_NAMES = LEASE_NAMES | {"task_cid", "claim_id", "attempt_id", "attempt_number"}
RUN_NAMES = LEASE_NAMES | {"resource_id"}


def closed(value, keys, label):
    need(type(value) is dict and set(value) == set(keys), "closed " + label + " required")


def exact_integer(value, minimum=1):
    need(type(value) is int and minimum <= value < 2**63, "exact bounded integer required")


def measure(value):
    need(type(value) is str, "literal complete input required")
    raw = value.encode("utf-8")
    need(0 < len(raw) <= 524_288, "complete coding input exceeds bound")
    return {"bytes": len(raw), "sha256": digest(raw)}


def birth(value, *, command=True):
    if value is None:
        return None
    closed(value, BIRTH_NAMES | ({"command"} if command else set()), "kernel birth")
    for key in ("pid", "start_time_ticks"):
        exact_integer(value[key])
    for key in ("uid", "parent_pid"):
        exact_integer(value[key], 0)
    need(type(value["boot_id"]) is str and re.fullmatch(
        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", value["boot_id"]),
        "exact kernel boot UUID required")
    material = f'{value["pid"]}:{value["start_time_ticks"]}:{value["boot_id"]}:{value["parent_pid"]}'.encode()
    need(value["process_birth_id"] == "birth:" + digest(material)[:32], "kernel birth hash differs")
    result = {key: value[key] for key in BIRTH_NAMES}
    if command:
        argv = value["command"]
        need(type(argv) is list and 1 <= len(argv) <= 256 and all(
            type(part) is str and 0 < len(part.encode()) <= 8192
            and not any(c in part for c in ("\0", "\n", "\r")) for part in argv),
            "bounded literal kernel argv required")
        result["command_sha256"] = digest(canonical(argv))
    return result


def path_hash(value):
    need(type(value) is str and value and len(value.encode()) <= 4096
         and not any(c in value for c in ("\0", "\n", "\r")), "literal captured path required")
    path = PurePosixPath(value)
    need(path.is_absolute() and str(path) == value and ".." not in path.parts,
         "canonical captured path required")
    return digest(value.encode())


def verify_record(record, materials, *, launch, launch_signature):
    """Verify the signed projection and recompute every supplied original join."""
    closed(record, {"schema", "record_id", "payload", "binding"}, "signed dispatch record")
    need(record["schema"] == SCHEMA and len(canonical(record)) <= 65_536,
         "bounded dispatch evidence schema required")
    payload = record["payload"]
    closed(payload, {"schema", "phase", "handoff_id", "context_cid", "manifest_id",
        "launch", "task", "attempt_lease", "run_lease", "snapshot", "allocation", "input",
        "kernel", "outcome", "materials"} | AUTHORITY_NAMES, "dispatch payload")
    need(payload["schema"] == SCHEMA and payload["phase"] in PHASES
         and type(payload["handoff_id"]) is str and re.fullmatch(r"[0-9a-f]{32}", payload["handoff_id"]),
         "explicit dispatch phase and nonce required")
    require_false(payload, AUTHORITY_NAMES)
    need(record["record_id"] == "sha256:" + digest(canonical(payload)), "record identity differs")
    verify_signature(payload, record["binding"], expected_identity=launch_signature["identity"],
                     expected_profile=launch_signature["profile_id"])
    closed(materials, MATERIAL_NAMES, "captured material bundle")
    need(materials["manifest"] == launch and materials["manifest_signature"] == launch_signature
         and materials["admission"] == launch["local_admission"], "public protected launch/admission differs")
    need(sum(len(canonical(value)) for value in materials.values()) <= 16 * 1024 * 1024,
         "captured materials exceed total bound")
    need(all(len(canonical(value)) <= 4 * 1024 * 1024 for value in materials.values()),
         "captured material exceeds individual bound")
    need(payload["materials"] == {key: descriptor(value) for key, value in materials.items()},
         "signed original material digest differs")
    m, phase = materials, payload["phase"]
    scope, claim = launch["checked_observer_budget_scope"], m["claim"]
    need(payload["context_cid"] == structured_cid(scope), "signed owner scope context CID differs")
    closed(claim, CLAIM_NAMES, "native claim")
    for key in ("task_revision", "attempt_number", "fencing_token", "fence_epoch", "peer_pid",
                "peer_start_time_ticks", "grant_expires_at_ms"):
        exact_integer(claim[key])
    exact_integer(claim["peer_uid"], 0)
    need(claim["task_cid"] == scope["task_cid"] and claim["client_id"] == launch["bootstrap_client_id"]
         and claim["store_id"] == launch["owner_identity"]["store_id"], "claim launch/task/client/store differs")
    manifest_id = "sha256:" + digest(canonical(launch, signing=True))
    need(payload["manifest_id"] == manifest_id, "native manifest ASCII identity differs")
    need(scope["admission_cid"] == structured_cid(m["admission"]), "native admission CID differs")
    prepared, snapshot = m["preparation"], m["snapshot"]
    need(prepared["schema"] == "checked-observer-budget-dispatch@1"
         and prepared["context_cid"] == payload["context_cid"]
         and snapshot == prepared["preflight"], "original prepared snapshot/context differs")
    environment = launch["environment"]
    need(type(environment) is list and all(type(item) is list and len(item) == 2 for item in environment)
         and len({item[0] for item in environment}) == len(environment), "unique native launch environment required")
    need(dict(environment)["IPFS_ACCELERATE_CHECKED_CONTEXT_DISPATCH_CID"] == payload["context_cid"],
         "signed native launch routing context differs")
    need(snapshot["checked_binding"] == scope["budget_binding"] and snapshot["task_cid"] == claim["task_cid"]
         and snapshot["task_id"] == scope["task_id"] and snapshot["admission_cid"] == scope["admission_cid"],
         "snapshot native task/admission/head differs")
    inner = prepared["preparation"]
    need(inner["schema"] == "terminal-checked-worker-budget-preparation@1", "coding preparation schema differs")
    verify_cid(inner, "preparation_cid")
    basis, event, render = inner["basis"], inner["event"], inner["materialization"]
    need(basis["task_cid"] == claim["task_cid"] and basis["native_prompt"] == m["native_stdin"],
         "actual native stdin task/preparation differs")
    verify_cid(event, "event_cid")
    need(event["binding_cid"] == structured_cid(scope["budget_binding"]), "reserved event budget binding differs")
    exact_integer(event["sequence"])
    native = measure(m["native_stdin"])
    need(snapshot["native_prompt_sha256"] == native["sha256"] and snapshot["native_prompt_bytes"] == native["bytes"],
         "snapshot native input differs")
    new_text = basis["router_prompt"] + basis["checked_suffix"]
    full_text = event["rendered_input"]["text"]
    need(basis["router_prompt"].startswith(m["native_stdin"]) and event["new_content"]["text"] == new_text
         and full_text.endswith(new_text) and len(full_text) > len(new_text), "complete rendered native input differs")
    full, new = measure(full_text), measure(new_text)
    for key, measured in (("new_content", new), ("rendered_input", full)):
        closed(event[key], {"text", "bytes", "sha256", "tokens"}, "coding event input")
        exact_integer(event[key]["tokens"], 0)
        exact_integer(event[key]["bytes"])
        need({name: event[key][name] for name in ("bytes", "sha256")} == measured, "event input bytes/hash differ")
    need(canonical(render["native_prompt"]) == canonical(native) and canonical(render["model_prompt"]) == canonical(full)
         and canonical(render["router_prompt"]) == canonical(new), "complete materialized input differs")
    attempt = {key: m["attempt_lease"][key] for key in ATTEMPT_NAMES}
    run = {key: m["run_lease"][key] for key in RUN_NAMES}
    need(all(attempt[key] == claim[key] for key in ATTEMPT_NAMES - {"expires_at_ms"}), "attempt claim/fence differs")
    need(run["resource_id"] == launch["run_id"] and run["owner_session_id"] == launch_signature["identity"],
         "protected native run lease differs")
    for lease in (attempt, run):
        for key in ("fencing_token", "fence_epoch", "expires_at_ms"):
            exact_integer(lease[key])
    allocation = m["allocation"]
    closed(allocation, {"binding", "portal_identity", "lifecycle"}, "native allocation material")
    binding, portal, life = allocation["binding"], allocation["portal_identity"], allocation["lifecycle"]
    need(all(binding[key] == claim[key] for key in ("task_cid", "task_revision", "attempt_id", "claim_id",
         "lease_id", "fencing_token", "fence_epoch")), "allocation native claim/fence differs")
    need(binding["task_alias"] == portal["task_id"] == life["task_id"] == scope["task_id"]
         and portal["canonical_task_cid"] == life["canonical_task_cid"], "allocation Portal identity differs")
    workspace = basis["worker_workspace"]
    path_hash(workspace); path_hash(launch["worker_worktree_root"]); path_hash(launch["repository_root"])
    need(PurePosixPath(workspace) != PurePosixPath(launch["worker_worktree_root"])
         and PurePosixPath(workspace).is_relative_to(launch["worker_worktree_root"])
         and life["workspace_path"] == workspace and life["repo_root"] == launch["repository_root"]
         and snapshot["worker_binding"]["workspace"] == workspace, "allocated workspace differs")
    prefix = (1 << 52) | (claim["attempt_number"] << 16)
    exact_integer(life["attempt"])
    need(1 <= life["attempt"] - prefix < 1 << 16 and life["state"] == "active"
         and not life["terminal_reason"], "active allocation attempt differs")
    expected_lifecycle = structured_cid({"kind": "worktree-lifecycle-record",
        "canonical_task_cid": life["canonical_task_cid"], "task_id": life["task_id"],
        "attempt": life["attempt"], "workspace_path": workspace})
    need(life["record_id"] == expected_lifecycle, "allocation lifecycle content identity differs")
    kernel = {role: birth(m[role + "_identity"]) for role in ("broker", "daemon", "wrapper", "sudo", "worker")}
    broker, daemon, wrapper, sudo, worker = (kernel[role] for role in ("broker", "daemon", "wrapper", "sudo", "worker"))
    need(broker is not None and daemon is not None, "broker/daemon kernel observations missing")
    seen = [value for value in (broker, daemon, wrapper, sudo, worker) if value is not None]
    need(len({value["pid"] for value in seen}) == len(seen) and len({value["boot_id"] for value in seen}) == 1,
         "dispatch births have reused PID or differing boot")
    need(daemon["pid"] == claim["peer_pid"] and daemon["uid"] == claim["peer_uid"]
         and daemon["start_time_ticks"] == claim["peer_start_time_ticks"]
         and daemon["process_birth_id"] == claim["process_birth_id"], "authenticated daemon birth differs")
    need(broker["uid"] == daemon["uid"] == basis["boundary"]["owner_uid"], "native owner UID differs")
    need(all(life["owner"][key] == daemon[key] for key in ("pid", "parent_pid", "start_time_ticks", "boot_id")),
         "native allocation daemon owner differs")
    signed_owner = strict_json(dict(environment)["IPFS_ACCELERATE_CHECKED_CONTEXT_OWNER_BIRTH"].encode())
    need(signed_owner == {key: broker[key] for key in ("pid", "process_birth_id")}, "signed original broker birth differs")
    chain = [birth(value, command=False) for value in m["parent_chain"]]
    need(len(chain) <= 8 and len({value["pid"] for value in chain}) == len(chain), "bounded acyclic worker chain required")
    if wrapper is not None:
        need(wrapper["parent_pid"] == daemon["pid"] and wrapper["uid"] == broker["uid"], "wrapper parent/UID differs")
        command = prepared["command"]
        argv = m["wrapper_identity"]["command"]
        need(argv.count(command[0]) == 1 and argv[argv.index(command[0]):] == command, "wrapper kernel argv differs")
    if sudo is not None:
        need(wrapper is not None and sudo["parent_pid"] == wrapper["pid"], "sudo wrapper parent differs")
    if worker is not None:
        need(sudo is not None and worker["uid"] == basis["boundary"]["worker_uid"] == 1001
             and 1 <= len(chain) <= 8 and chain[0] == {key: worker[key] for key in BIRTH_NAMES}
             and chain[-1] == {key: sudo[key] for key in BIRTH_NAMES}, "worker/sudo chain endpoints differ")
        need(all(child["parent_pid"] == parent["pid"] and child["boot_id"] == parent["boot_id"]
                 for child, parent in zip(chain, chain[1:])), "worker kernel ancestry differs")
    else:
        need(not chain, "ancestry without worker refused")
    need(phase == "prepared" or wrapper is not None, "wrapper release lacks observed birth")
    need(phase not in ("worker_released", "worker_observed") or worker is not None,
         "worker release lacks observed birth")
    need(m["receipt_emitter_identity"] is None, "log ownership cannot authenticate coding receipt emitter")
    kernel.update(parent_chain=chain, broker_dispatch_emitter=dict(broker), receipt_emitter=None)
    observation = m["observation"]
    need((phase == "worker_observed") == (observation is not None), "explicit coding observation phase differs")
    if observation is not None:
        need(observation["schema"] == "supervisor-model-input-observation@2" and observation["status"] == "observed"
             and observation["workspace"] == workspace and observation["provider_attempted"] is False
             and observation["router_calls"] == 0 and observation["usage"] is None,
             "coding observation route/provider claims differ")
        need(observation["model_prompt_sha256"] == full["sha256"] and observation["model_prompt_bytes"] == full["bytes"]
             and observation["native_prompt_sha256"] == native["sha256"] and observation["native_prompt_bytes"] == native["bytes"]
             and observation["router_prompt_sha256"] == new["sha256"] and observation["router_prompt_bytes"] == new["bytes"],
             "parsed observation complete input join differs")
        require_false(observation, ("execution_authority", "proof_authority", "completion_authority"))
    expected = {
        "schema": SCHEMA, "phase": phase, "handoff_id": payload["handoff_id"], "context_cid": prepared["context_cid"],
        "manifest_id": manifest_id,
        "launch": {key: launch[key] for key in ("repository_id", "baseline_commit", "baseline_tree_id", "run_id")}
            | {"admission_cid": scope["admission_cid"], "signer_identity": launch_signature["identity"],
               "profile_id": launch_signature["profile_id"]},
        "task": {"task_id": scope["task_id"], **claim}, "attempt_lease": attempt, "run_lease": run,
        "snapshot": {"head": snapshot["checked_binding"]["head"], "source_scope_sha256": digest(canonical(snapshot["source_scope"])),
                     "repository_path_sha256": path_hash(launch["repository_root"])},
        "allocation": {key: life[key] for key in ("record_id", "canonical_task_cid", "attempt", "lease_id", "fence")}
            | {"workspace_path_sha256": path_hash(workspace)},
        "input": {"native_stdin": native, "complete_coding_input": full, "new_content": new,
            "preparation_cid": inner["preparation_cid"], "event_cid": event["event_cid"],
            "event_id": event["event_id"], "event_sequence": event["sequence"], "event_sha256": digest(canonical(event))},
        "kernel": kernel,
        "outcome": {"wrapper_birth_observed": wrapper is not None, "worker_birth_observed": worker is not None,
            "wrapper_release_confirmed": phase != "prepared", "worker_release_confirmed": phase in ("worker_released", "worker_observed"),
            "worker_observation_parsed": observation is not None, "receipt_emitter_origin_verified": False,
            "observation_channel": "owner_parsed_native_log" if observation is not None else "none"},
        "materials": {key: descriptor(value) for key, value in m.items()},
        **dict.fromkeys(AUTHORITY_NAMES, False),
    }
    need(canonical(payload) == canonical(expected), "signed payload does not reconstruct from independent originals")
    return payload


def verify_sources(snapshot, admission):
    sources = admission["manifest"]["payload"]["sources"]
    rows, instruction = snapshot["source_scope"], snapshot["signed_instruction"]
    need(type(sources) is dict and type(rows) is list and 1 <= len(rows) <= 256,
         "bounded signed native source inventory required")
    seen = set()
    for row in rows + [instruction]:
        path = row["path"]
        need(type(path) is str and path not in seen and path in sources
             and row["sha256"] == sources[path]["sha256"], "checked/native signed source path/hash differs")
        seen.add(path)
    need(seen == set(sources), "signed native source inventory coverage differs")


def verify_public_artifacts(public, material):
    snapshot, scope = material["snapshot"], material["manifest"]["checked_observer_budget_scope"]
    raw = read_bytes(public / "checked-context-public-artifact.json")
    need(digest(raw) == snapshot["artifact_sha256"] and len(raw) == snapshot["artifact_bytes"],
         "public checked artifact bytes/hash differ from captured original")
    artifact = strict_json(raw)
    need(artifact["schema"] == "supervisor-checked-audit-context@1"
         and artifact["admission"] == material["admission"]
         and artifact["checked_binding"] == scope["budget_binding"]
         and artifact["source_scope"] == snapshot["source_scope"]
         and artifact["signed_instruction"] == snapshot["signed_instruction"],
         "public checked artifact native admission/source bindings differ")
    need(type(artifact["context_packet"]) is str, "literal checked context packet text required")
    context = artifact["context_packet"].encode("utf-8")
    need(len(context) == scope["context_bytes"] == artifact["context_bytes"]
         and digest(context) == scope["context_sha256"] == artifact["context_sha256"],
         "public checked context packet bytes/hash differ")
    require_false(artifact, ("execution_authority", "proof_authority", "completion_authority", "serialized_live_authority"))
    instruction_raw = read_bytes(public / "public-instruction-artifact.json")
    need(digest(instruction_raw) == snapshot["instruction_artifact_sha256"]
         == scope["public_instruction"]["sha256"], "public instruction artifact bytes/hash differ")
    instruction = strict_json(instruction_raw)
    need(instruction["schema"] == "supervisor-public-instruction@1"
         and instruction["manifest"] == material["admission"]["manifest"]
         and instruction["task_id"] == snapshot["task_id"] and instruction["task_cid"] == snapshot["task_cid"]
         and instruction["source_path"] == snapshot["signed_instruction"]["path"]
         and instruction["source_sha256"] == snapshot["signed_instruction"]["sha256"]
         and instruction["source_bytes"] == snapshot["signed_instruction"]["bytes"],
         "public instruction signed native source differs")
    require_false(instruction, ("completion_authority", "publication_authority", "scope_expansion_authority"))


def verify_command(materials, launch):
    argv = launch["argv"]
    need(type(argv) is list and argv.count("--implementation-command") == 1,
         "unique native implementation command required")
    base = shlex.split(argv[argv.index("--implementation-command") + 1])
    flag = "--checked-context-owner-scope-cid"
    need(base.count(flag) == 1 and not any(part.startswith(flag + "=") for part in base),
         "original owner command discriminator differs")
    index = base.index(flag)
    prepared = materials["preparation"]
    need(base[index + 1] == prepared["context_cid"], "native base command context differs")
    command = base[:index] + base[index + 2:] + [
        "--checked-context-artifact", prepared["preflight"]["artifact"],
        "--checked-context-sha256", prepared["preflight"]["artifact_sha256"],
        "--checked-context-task-cid", materials["claim"]["task_cid"],
    ]
    need(prepared["command"] == command, "derived checked command differs from signed native launch")
    expected_worker = str(PurePosixPath(command[0]).parent / "worker-entry")
    if materials["sudo_identity"] is not None:
        expected = ["/usr/bin/sudo", "-n", "-u", "benchmarkworker", "--", expected_worker, *command[1:]]
        need(materials["sudo_identity"]["command"] == expected, "sudo kernel command differs")
    if materials["worker_identity"] is not None:
        actual = materials["worker_identity"]["command"]
        need(actual.count(expected_worker) == 1 and actual[actual.index(expected_worker) + 1:] == command[1:],
             "isolated worker kernel argv differs")


def verify_observation(observation, payload, workspace):
    need(observation["schema"] == "supervisor-model-input-observation@2" and observation["status"] == "observed"
         and observation["workspace"] == workspace and observation["provider_attempted"] is False
         and observation["router_calls"] == 0 and observation["usage"] is None,
         "public coding observation route differs")
    for observed, measured in (("native_prompt", "native_stdin"), ("model_prompt", "complete_coding_input"),
                               ("router_prompt", "new_content")):
        need(observation[observed + "_sha256"] == payload["input"][measured]["sha256"]
             and observation[observed + "_bytes"] == payload["input"][measured]["bytes"],
             "public coding observation signed input differs")
    require_false(observation, ("execution_authority", "proof_authority", "completion_authority"))
    checked = observation["checked_context"]
    need(checked["task_cid"] == payload["task"]["task_cid"] and checked["task_id"] == payload["task"]["task_id"]
         and checked["checked_binding"]["head"] == payload["snapshot"]["head"],
         "public coding observation checked task/head differs")


def verify_public_bundle(public_dir, records, originals, *, allow_incomplete=False):
    """Validate selected public artifacts and all original material overlaps."""
    public = Path(public_dir)
    need(type(records) is list and len(records) <= 16 and type(originals) is list and len(originals) == len(records),
         "bounded matched public record/material inventories required")
    launch = read_json(public / "native-launch-manifest.json")
    signature = read_json(public / "native-launch-signature.json")
    verify_signature(launch, signature)
    admission = launch["local_admission"]["manifest"]
    verify_signature(admission["payload"], admission["binding"], expected_identity=signature["identity"],
                     expected_profile=signature["profile_id"])
    record_ids, nonces, phases, payloads = set(), set(), [], []
    prepared_public = None
    bootstrap = read_json(public / "native-bootstrap-receipts.json")
    need(type(bootstrap) is list and len(bootstrap) <= 16, "bounded public bootstrap receipts required")
    observations = read_json(public / "broker-observations-after-close.json")
    need(type(observations) is list and len(observations) <= 64, "bounded public broker observations required")
    raw_stdin = read_bytes(public / "native-emitted-prompt.txt") if records else None
    whole_input = read_bytes(public / "native-complete-input.txt") if records else None
    previous = None
    for record, original in zip(records, originals):
        closed(original, {"record_id", "materials"}, "per-record captured originals")
        need(original["record_id"] == record["record_id"] and record["record_id"] not in record_ids,
             "duplicate or unmatched signed record ID")
        record_ids.add(record["record_id"])
        material = original["materials"]
        payload = verify_record(record, material, launch=launch, launch_signature=signature)
        verify_sources(material["snapshot"], material["admission"])
        verify_command(material, launch)
        phase = payload["phase"]
        need(payload["handoff_id"] not in nonces, "replayed dispatch handoff nonce")
        nonces.add(payload["handoff_id"])
        need(not phases or PHASES.index(phase) >= PHASES.index(phases[-1]), "dispatch phase order rolled back")
        phases.append(phase)
        need(material["native_stdin"].encode() == raw_stdin
             and material["preparation"]["preparation"]["event"]["rendered_input"]["text"].encode() == whole_input,
             "public native stdin/complete input differs from captured original")
        if prepared_public is None:
            prepared_public = read_json(public / "native-dispatch-prepared-record.json")
        for key in ("preparation", "preflight"):
            need(prepared_public[key] == material["preparation"][key], "existing public prepared record differs")
        if "pregrant" in material["preparation"]:
            need(prepared_public["pregrant"] == material["preparation"]["pregrant"], "existing public pregrant differs")
        claim = payload["task"]
        matches = [value for value in bootstrap if value.get("pid") == claim["peer_pid"]
                   and value.get("process_birth_id") == claim["process_birth_id"]]
        need(len(matches) == 1, "signed dispatch daemon lacks its exact public bootstrap observation")
        b = matches[0]
        need(b["client_id"] == claim["client_id"] and b["store_id"] == claim["store_id"]
             and b["server_id"] == launch["owner_identity"]["server_id"]
             and b["configuration_root"] == payload["manifest_id"]
             and b["route_policy_id"] == launch["execution_route_policy_id"],
             "public daemon bootstrap native launch/client/store differs")
        if previous is not None:
            for key in ("launch", "snapshot", "input"):
                need(previous[key] == payload[key], "signed dispatch immutable join changed between phases")
            need({key: value for key, value in previous["task"].items() if key != "grant_expires_at_ms"}
                 == {key: value for key, value in payload["task"].items() if key != "grant_expires_at_ms"},
                 "signed native claim changed between phases")
            need(payload["task"]["grant_expires_at_ms"] >= previous["task"]["grant_expires_at_ms"],
                 "signed native grant expiry rolled back")
            for key in ("attempt_lease", "run_lease"):
                need({name: value for name, value in previous[key].items() if name != "expires_at_ms"}
                     == {name: value for name, value in payload[key].items() if name != "expires_at_ms"},
                     "signed lease/fence changed between phases")
            for key in ("broker", "daemon"):
                need(previous["kernel"][key] == payload["kernel"][key], "original kernel owner/daemon changed")
            if previous["kernel"]["wrapper"] is not None:
                need(previous["kernel"]["wrapper"] == payload["kernel"]["wrapper"], "registered wrapper changed")
            need({key: value for key, value in previous["allocation"].items() if key != "fence"}
                 == {key: value for key, value in payload["allocation"].items() if key != "fence"}
                 and payload["allocation"]["fence"] >= previous["allocation"]["fence"], "native allocation changed/rolled back")
        previous = payload
        payloads.append(payload)
    complete = "wrapper_released" in phases and "worker_released" in phases
    need(allow_incomplete or complete, "complete signed wrapper and worker releases are missing")
    coding_observation_joined = False
    if complete:
        payload = next(value for value in reversed(payloads) if value["kernel"]["worker"] is not None)
        worker = payload["kernel"]["worker"]
        material = originals[payloads.index(payload)]["materials"]
        verify_public_artifacts(public, material)
        spawned = [row for row in observations if row.get("boundary") == "isolated_worker"
                   and row.get("status") == "spawned" and row.get("worker_pid") == worker["pid"]
                   and row.get("worker_process_birth_id") == worker["process_birth_id"]]
        need(len(spawned) == 1, "public broker worker birth differs from signed kernel birth")
        metadata = spawned[0]["worker_worktree_observation"]
        need(all(metadata[key] == worker[key] for key in BIRTH_NAMES)
             and metadata["command_sha256"] == worker["command_sha256"],
             "public sameUID kernel metadata differs from signed worker")
        observed = read_json(public / "native-observation.json")
        verify_observation(observed, payload, material["preparation"]["preparation"]["basis"]["worker_workspace"])
        coding_observation_joined = True
    return {
        "schema": "independent-public-dispatch-verification@1", "verified": True,
        "signed_records": len(records), "phases": phases,
        "complete_dispatch_join_verified": complete,
        "coding_observation_input_join_verified": coding_observation_joined,
        "broker_dispatch_emitter_signature_verified": bool(records),
        "coding_receipt_emitter_origin_verified": False,
        "coding_observation_channel": "owner_parsed_native_log" if coding_observation_joined else "none",
        "historical_ack_budget_independently_verified": False,
        "transcript_completeness_attested": False,
        "supplied_public_launch_is_trust_input": True,
        **FALSE_AUTHORITY,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--public-dir", type=Path, required=True)
    parser.add_argument("--records", type=Path)
    parser.add_argument("--materials", type=Path)
    parser.add_argument("--allow-incomplete", action="store_true",
                        help="audit captured partial/fault records without claiming a complete dispatch")
    args = parser.parse_args(argv)
    try:
        records = read_json(args.records or args.public_dir / "broker-signed-dispatch-evidence-after-close.json")
        originals = read_json(args.materials or args.public_dir / "broker-dispatch-evidence-materials-after-close.json")
        result = verify_public_bundle(args.public_dir, records, originals, allow_incomplete=args.allow_incomplete)
    except (VerificationError, OSError, KeyError, IndexError, TypeError, UnicodeError) as error:
        print(json.dumps({"schema": "independent-public-dispatch-verification@1", "verified": False,
                          "error_type": type(error).__name__, "reason": str(error), **FALSE_AUTHORITY}, sort_keys=True))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
