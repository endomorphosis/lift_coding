"""Project an unchanged, four-file JSONL observation bracket into the finite model.

Rows are read only from the bound current artifact bytes.  Observation reports
are replayable data and do not authenticate their author or confer access to a
live repository.  The caller must separately reobserve the files and native
codebase head around this pure projection.
"""
from __future__ import annotations

import copy
import hashlib

import scheduler_constraints as sc
from observed_files import (FILE_PATHS, compare_bundles, decode_file,
                            validate_bundle)
from strict_jsonl import parse_jsonl


SCHEMA = "terminal-jsonl-file-bound-scheduler-model@1"
BUCKET_PATHS = {
    1: {"requests": "input_data/requests_bucket_1.jsonl",
        "plan": "output_data/plan_b1.jsonl"},
    2: {"requests": "input_data/requests_bucket_2.jsonl",
        "plan": "output_data/plan_b2.jsonl"},
}
FALSE_CLAIMS = {
    **sc.FALSE_CLAIMS,
    "artifact_observations_authenticated": False,
    "live_file_custody_verified_by_projection": False,
    "live_codebase_head_verified_by_projection": False,
    "checker_model_equivalence_proved": False,
    "benchmark_harness_executed": False,
    "external_model_invoked": False,
}


class FileModelError(ValueError):
    """The exact observed artifact bracket cannot define this finite model."""


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _canonical(value):
    try:
        return sc.canonical_bytes(value)
    except (ValueError, TypeError, UnicodeError, RecursionError) as exc:
        raise FileModelError("file model inputs must be bounded plain JSON") from exc


def _file_binding(row):
    """The observation's whole-file hash binds the exact base64 payload too."""
    return {"sha256": row["sha256"], "bytes": row["bytes"],
            "identity": copy.deepcopy(row["identity"]),
            "payload_b64_sha256": _sha(row["payload_b64"].encode("ascii"))}


def build_file_model(*, contract: dict, before: dict, after: dict,
                     metrics: dict, case_id: str) -> dict:
    """Derive and check a case; no caller-supplied request or plan rows are accepted.

    ``metrics`` is an explicit two-bucket mapping of supplied exact rational
    inputs.  Missing metric fields and invalid rational domains are passed to
    the existing finite checker and fail its candidate threshold predicates.
    There is no inference from a source function or benchmark runtime.
    """
    _canonical(contract)
    before_raw, after_raw = _canonical(before), _canonical(after)
    metrics_raw = _canonical(metrics)
    if (type(case_id) is not str or not case_id
            or len(case_id.encode("utf-8")) > 512):
        raise FileModelError("case_id must be a nonempty bounded UTF-8 string")
    if (type(metrics) is not dict or set(metrics) != {"1", "2"}
            or any(type(metrics[key]) is not dict for key in ("1", "2"))):
        raise FileModelError("explicit metrics for buckets 1 and 2 are required")
    validate_bundle(before)
    validate_bundle(after)
    expected_paths = {path for paths in BUCKET_PATHS.values() for path in paths.values()}
    if set(FILE_PATHS) != expected_paths:
        raise FileModelError("the owned-file profile is not the fixed two-bucket model")

    projections = {"before": {}, "after": {}}
    decoded = {"before": {}, "after": {}}
    for phase, bundle in (("before", before), ("after", after)):
        for bucket_id in (1, 2):
            for kind in ("requests", "plan"):
                path = BUCKET_PATHS[bucket_id][kind]
                raw = decode_file(bundle, path)
                decoded[phase][path] = raw
                projections[phase][path] = parse_jsonl(raw, kind=kind)

    comparison = compare_bundles(before, after)
    if not all(comparison.get(name) is True for name in (
            "roots_equal", "directory_generations_equal", "inputs_bytes_equal",
            "unchanged_inputs", "same_file_generations")):
        raise FileModelError("all four files must retain their exact observed custody and bytes")
    # Compare original bytes as well as the observer's replayed comparison.
    if any(decoded["before"][path] != decoded["after"][path] for path in expected_paths):
        raise FileModelError("JSONL bytes changed inside the fixed observation bracket")

    buckets, file_bindings = [], {}
    for bucket_id in (1, 2):
        request_path = BUCKET_PATHS[bucket_id]["requests"]
        plan_path = BUCKET_PATHS[bucket_id]["plan"]
        buckets.append({
            "bucket_id": bucket_id,
            "requests": copy.deepcopy(projections["after"][request_path]["rows"]),
            "plan": copy.deepcopy(projections["after"][plan_path]["rows"]),
            "metrics": copy.deepcopy(metrics[str(bucket_id)]),
            "input_before": decoded["before"][request_path].decode("utf-8"),
            "input_after": decoded["after"][request_path].decode("utf-8"),
        })
        for kind in ("requests", "plan"):
            path = BUCKET_PATHS[bucket_id][kind]
            file_bindings[path] = {
                "bucket_id": bucket_id, "kind": kind,
                "before": _file_binding(before["files"][path]),
                "after": _file_binding(after["files"][path]),
                "row_source": "after_raw_utf8_bytes",
            }

    case = {"case_id": case_id, "buckets": buckets}
    # This native predecessor checker revalidates every complete source binding
    # in the contract before evaluating the byte-derived finite case.
    evaluation = sc.evaluate_case(contract, case)
    return {
        "schema": SCHEMA,
        "case_id": case_id,
        "contract_sha256": _sha(_canonical(contract)),
        "head": copy.deepcopy(contract["head"]),
        "head_sha256": _sha(_canonical(contract["head"])),
        "before_observation_sha256": _sha(before_raw),
        "after_observation_sha256": _sha(after_raw),
        "metrics_sha256": _sha(metrics_raw),
        "supplied_metrics": copy.deepcopy(metrics),
        "file_bindings": file_bindings,
        "file_comparison": comparison,
        "projections": projections,
        "case": case,
        "evaluation": evaluation,
        "claims": dict(FALSE_CLAIMS),
    }


def validate_file_model(report, *, contract, before, after, metrics, case_id):
    """Replay exact data bindings; this never restores a live owner capability."""
    expected = build_file_model(contract=contract, before=before, after=after,
                                metrics=metrics, case_id=case_id)
    if _canonical(report) != _canonical(expected):
        raise FileModelError("file model replay differs from the exact observed artifact inputs")
    return True
