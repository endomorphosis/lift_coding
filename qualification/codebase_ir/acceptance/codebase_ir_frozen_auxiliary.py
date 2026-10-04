"""Read only explicitly pinned frozen auxiliary bodies; no native execution."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import codebase_ir_advisory_evidence as advisory
from codebase_ir_admission_evidence import AdmissionEvidenceError, cid, exact, need, parse_document

INPUT_SCHEMA = "codebase-ir-frozen-auxiliary-input@1"
SCHEMA = "codebase-ir-frozen-auxiliary-retained-audit@1"
ATTEMPTS = ("02", "05", "06")
LABELS = ("root-frozen", "initial-child-frozen", "successor-frozen")
DIRECTORIES = (
    "root-frozen-context",
    "initial-child-frozen-context",
    "successor-child-frozen-context",
)
BODIES = ("context", "invocation", "inference", "metrics")
METRIC_FIELDS = {
    "before",
    "after",
    "epochs",
    "selected_total_epochs",
    "attempted_epochs",
    "train_coverage",
    "tuning_coverage",
}
FLAGS = (
    "native_execution_performed",
    "training_executed",
    "current_authority_claimed",
    "full_join_qualified",
    "signature_authentication_performed",
    "owner_database_opened",
    "profile_keys_read",
    "numerical_state_replayed",
    "worker_receipt_authenticated",
    "worker_protocol_output_digest_rederived",
)


def role_paths() -> dict[str, str]:
    return {
        label + ":" + body: "native/private/advisory/" + directory + "/" + body + ".json"
        for label, directory in zip(LABELS, DIRECTORIES, strict=True)
        for body in BODIES
    }


def canonical_path(value: Any) -> Path:
    need(type(value) is str, "canonical absolute path string required")
    path = Path(value)
    need(
        path.is_absolute()
        and str(path) == value
        and path.resolve(strict=False) == path
        and not any(parent.is_symlink() for parent in (path, *path.parents)),
        "noncanonical/symlink path",
    )
    return path


def pin_shape(pin: Any, *, absolute: bool) -> None:
    need(
        type(pin) is dict
        and set(pin)
        == ({"path", "sha256", "bytes"} if absolute else {"role", "path", "sha256", "bytes"}),
        "closed raw pin required",
    )
    need(
        advisory.digest(pin["sha256"])
        and advisory.integer(pin["bytes"])
        and pin["bytes"] <= (advisory.MAX_MANIFEST_BYTES if absolute else advisory.MAX_FILE_BYTES),
        "bounded exact raw pin required",
    )
    if absolute:
        canonical_path(pin["path"])


def validate_spec(spec: Any) -> None:
    need(
        type(spec) is dict
        and set(spec) == {"schema", "prior_advisory_manifest", "prior_advisory_report", "attempts"}
        and spec["schema"] == INPUT_SCHEMA,
        "closed supplemental input schema required",
    )
    for name in ("prior_advisory_manifest", "prior_advisory_report"):
        pin_shape(spec[name], absolute=True)
    need(
        spec["prior_advisory_manifest"]["path"] != spec["prior_advisory_report"]["path"],
        "prior input/report alias refused",
    )
    need(
        type(spec["attempts"]) is list
        and [row["id"] for row in spec["attempts"]] == list(ATTEMPTS),
        "complete ordered staged02/05/06 population required",
    )
    selected: set[str] = set()
    for row in spec["attempts"]:
        need(
            type(row) is dict and set(row) == {"id", "root", "files"},
            "closed supplemental attempt required",
        )
        root = canonical_path(row["root"])
        expected = role_paths()
        need(
            type(row["files"]) is list and len(row["files"]) == len(expected),
            "complete selected supplemental bodies required",
        )
        roles = []
        for pin in row["files"]:
            pin_shape(pin, absolute=False)
            need(
                type(pin["role"]) is str
                and pin["role"] in expected
                and pin["path"] == expected[pin["role"]],
                "foreign supplemental selector",
            )
            roles.append(pin["role"])
            path = str(root / pin["path"])
            need(path not in selected, "aliased supplemental file")
            selected.add(path)
        need(
            len(set(roles)) == len(roles) and set(roles) == set(expected),
            "duplicate/missing supplemental roles",
        )
    need(
        sum(pin["bytes"] for row in spec["attempts"] for pin in row["files"]) <= 2 * 1024 * 1024,
        "supplemental body aggregate cap exceeded",
    )


def anchor_roles() -> tuple[str, ...]:
    return (
        ("epochs", "criteria", "selections", "measurements")
        + tuple(
            f"train{number}_{body}"
            for number in range(3)
            for body in (
                "context",
                "checkpoint",
                "record",
                "lineage",
                "invocation",
                "inference",
                "metrics",
            )
        )
        + tuple("preview_" + label for label in LABELS)
    )


def load(spec: dict[str, Any], reader: advisory.PinnedReader) -> dict[str, Any]:
    validate_spec(spec)
    base_pin, report_pin = spec["prior_advisory_manifest"], spec["prior_advisory_report"]
    base = parse_document(reader.read(Path(base_pin["path"]), base_pin, manifest=True))
    advisory.validate_manifest(base)
    prior = parse_document(reader.read(Path(report_pin["path"]), report_pin, manifest=True))
    need(
        prior["schema"] == advisory.SCHEMA
        and prior["status"] == "passed"
        and prior["input_files_unchanged"] is True
        and prior["manifest_sha256"] == base_pin["sha256"],
        "prior retained report/input binding differs",
    )
    for flag in FLAGS[:7]:
        need(prior[flag] is False, "prior audit has unsupported authority/execution scope")
    need(
        prior["frozen_auxiliary_artifact_bodies_verified"] is False,
        "prior explicit auxiliary-body gap scope differs",
    )
    base_by_id = {row["id"]: row for row in base["attempts"]}
    cases = {}
    for row in spec["attempts"]:
        original = base_by_id[row["id"]]
        need(
            row["root"] == original["root"],
            "supplemental attempt detached from prior retained roots",
        )
        root = Path(row["root"])
        need(
            root.is_dir() and root.resolve(strict=True) == root,
            "retained supplemental root missing",
        )
        selected = {pin["role"]: pin for pin in original["files"]}
        records, pins = {}, {}
        for role in anchor_roles():
            pin = selected[role]
            path = root / pin["path"]
            need(
                prior["selected_input_pins"][str(path)]
                == {key: pin[key] for key in ("sha256", "bytes")},
                "prior report selected anchor pin differs",
            )
            records[role] = parse_document(reader.read(path, pin))
            pins[role] = pin
        training = {"records": records, "pins": pins}
        need(
            advisory.assert_training(training, row["id"]) == (48, 0),
            "independent retained training population differs",
        )
        supplemental = {}
        for pin in row["files"]:
            supplemental[pin["role"]] = (parse_document(reader.read(root / pin["path"], pin)), pin)
        models = []
        for number, label in enumerate(LABELS):
            model = {
                "preview_context": records["preview_" + label]["feature_context"],
                "trained_context": records[f"train{number}_context"],
                "checkpoint_report": records[f"train{number}_checkpoint"]["report"],
                "trained_metrics": records[f"train{number}_metrics"],
                "trained_inference": records[f"train{number}_inference"],
                "pins": {},
            }
            for body in BODIES:
                model[body], model["pins"][body] = supplemental[label + ":" + body]
            models.append(model)
        cases[row["id"]] = models
    return cases


def finite_numbers(value: Any) -> None:
    if type(value) in (int, float):
        need(
            math.isfinite(value) and abs(value) <= 1e12, "unbounded/nonfinite numerical observation"
        )
    elif type(value) is dict:
        for item in value.values():
            finite_numbers(item)
    elif type(value) is list:
        for item in value:
            finite_numbers(item)


def assert_auxiliary(model: dict[str, Any]) -> dict[str, Any]:
    context, trained = model["context"], model["trained_context"]
    need(
        exact(context, model["preview_context"]),
        "frozen context body differs from selected preview",
    )
    need(
        context["context_cid"]
        == cid({key: value for key, value in context.items() if key != "context_cid"}),
        "frozen context native content ID differs",
    )
    need(
        context["mode"] == "frozen"
        and context["model_enabled"] is True
        and type(context["actual_training_delta"]) is int
        and context["actual_training_delta"] == 0,
        "frozen selection fitted or mode changed",
    )
    varying = {"mode", "actual_training_delta", "context_cid", "artifacts"}
    need(
        set(context) == set(trained)
        and all(exact(context[key], trained[key]) for key in set(context) - varying),
        "frozen selected source/model/state/optimizer/lineage differs from independent training context",
    )
    need(
        set(context["artifacts"]) == set(trained["artifacts"]),
        "frozen selected artifact population differs",
    )
    for body in BODIES:
        advisory.raw_pin({"pins": model["pins"]}, body, model[body])
        if body == "context":
            continue
        descriptor = context["artifacts"][body]
        pin = model["pins"][body]
        need(
            set(descriptor)
            == {"schema", "role", "relative_path", "sha256", "size_bytes", "blob_cid"}
            and descriptor["schema"] == "supervisor-codebase-feature-blob@1"
            and descriptor["role"] == body
            and descriptor["relative_path"] == body + ".json"
            and descriptor["sha256"] == pin["sha256"]
            and type(descriptor["size_bytes"]) is int
            and descriptor["size_bytes"] == pin["bytes"]
            and descriptor["blob_cid"]
            == cid({key: value for key, value in descriptor.items() if key != "blob_cid"}),
            "frozen auxiliary descriptor/body/raw CID binding differs",
        )
    for body in ("checkpoint", "record", "lineage"):
        need(
            exact(context["artifacts"][body], trained["artifacts"][body]),
            "selected frozen checkpoint/record/lineage descriptor changed",
        )
    invocation = model["invocation"]
    need(
        set(invocation)
        == {
            "schema",
            "configuration",
            "head",
            "mode",
            "operation_id",
            "parent_version_id",
            "selections",
            "version_id",
        }
        and invocation["schema"] == "codebase-feature-context-invocation@1"
        and invocation["configuration"] is None
        and invocation["mode"] == "frozen"
        and invocation["operation_id"] == ""
        and invocation["parent_version_id"] is None
        and exact(invocation["selections"], [])
        and all(exact(invocation[key], context[key]) for key in ("head", "version_id")),
        "frozen invocation body mode/source/model/lineage differs",
    )
    inference, independently_retained = model["inference"], model["trained_inference"]
    need(
        set(inference)
        == {
            "schema",
            "authority",
            "head",
            "inference",
            "training_executed",
            "version_id",
            "worker_receipt",
        }
        and inference["schema"] == "codebase-current-feature-inference@1"
        and all(
            exact(inference[key], independently_retained[key])
            for key in set(inference) - {"worker_receipt"}
        ),
        "frozen inference body differs from independently retained selected inference",
    )
    need(
        set(inference["authority"]) == advisory.NATIVE_FEATURE_FALSE,
        "closed inference authority population differs",
    )
    advisory.false_fields(inference["authority"], advisory.NATIVE_FEATURE_FALSE)
    need(
        inference["training_executed"] is False
        and inference["inference"]["training_executed"] is False
        and exact(inference["head"], context["head"])
        and inference["version_id"] == context["version_id"],
        "inference fitted or detached source/model",
    )
    inner = inference["inference"]
    need(
        inner["schema"] == "native-projection-feature-inference/v1"
        and all(
            inner[key] == context[key]
            for key in ("state_sha256", "feature_space_sha256", "contract_sha256", "representation")
        ),
        "inference checkpoint/profile hashes differ",
    )
    advisory.false_fields(
        inner,
        {
            "admitted",
            "formalized",
            "promotion_performed",
            "qualified",
            "decoded_formulas_generated",
        },
    )
    rows = inner["rows"]
    need(
        type(rows) is list and len(rows) == 4, "complete four-source inference population required"
    )
    for row in rows:
        need(
            set(row) == {"latent", "reconstructed_projection_features", "source_digest"}
            and advisory.digest(row["source_digest"])
            and type(row["latent"]) is list
            and len(row["latent"]) == context["latent_width"]
            and all(type(value) in (int, float) for value in row["latent"]),
            "inference source/latent shape differs",
        )
    finite_numbers(inner)
    receipt = inference["worker_receipt"]
    need(
        set(receipt)
        == {
            "elapsed_ms",
            "executable_sha256",
            "input_sha256",
            "limits",
            "memory_enforcement",
            "output_sha256",
            "returncode",
            "source_execution_attested",
            "worker_sha256",
            "workspace_cleaned",
        },
        "closed retained worker receipt profile required",
    )
    need(
        all(
            advisory.digest(receipt[key])
            for key in ("executable_sha256", "input_sha256", "output_sha256", "worker_sha256")
        )
        and type(receipt["returncode"]) is int
        and receipt["returncode"] == 0
        and advisory.integer(receipt["elapsed_ms"])
        and receipt["elapsed_ms"] <= 90000
        and receipt["source_execution_attested"] is False
        and receipt["workspace_cleaned"] is True
        and receipt["memory_enforcement"] == "sampled_process_tree_rss_with_possible_overshoot"
        and exact(
            receipt["limits"], {"max_output_bytes": 16777216, "resident_memory_bytes": 1073741824}
        ),
        "retained worker receipt widened or invalid; not execution attestation",
    )
    metrics = model["metrics"]
    need(
        set(metrics) == METRIC_FIELDS
        and exact(metrics, model["trained_metrics"])
        and all(exact(metrics[key], model["checkpoint_report"][key]) for key in METRIC_FIELDS),
        "frozen metrics differ from selected checkpoint/native training report",
    )
    need(
        type(metrics["attempted_epochs"]) is int
        and metrics["attempted_epochs"] == 16
        and exact(metrics["selected_total_epochs"], context["selected_total_epochs"])
        and type(metrics["epochs"]) is list
        and len(metrics["epochs"]) == 16,
        "copied prior training metrics misreported as frozen fitting",
    )
    finite_numbers(metrics)
    return {
        key: context[key]
        for key in (
            "context_cid",
            "version_id",
            "parent_version_id",
            "head",
            "state_sha256",
            "feature_space_sha256",
            "contract_sha256",
            "selected_total_epochs",
            "selected_optimizer_steps",
        )
    } | {
        "bodies_verified": list(BODIES),
        "actual_training_delta": 0,
        "invocation_requested_parent_version_id": None,
        "copied_training_metrics_attempted_epochs": 16,
        "inference_source_digests": [row["source_digest"] for row in rows],
    }


def repin_model(model: dict[str, Any]) -> None:
    """Regenerate unsigned descriptor/context pins in inert authored controls."""
    for body in ("invocation", "inference", "metrics"):
        raw = json.dumps(
            model[body], sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
        ).encode()
        model["pins"][body] |= {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
        artifact = model["context"]["artifacts"][body]
        artifact |= {"sha256": model["pins"][body]["sha256"], "size_bytes": len(raw)}
        artifact["blob_cid"] = cid(
            {key: value for key, value in artifact.items() if key != "blob_cid"}
        )
    context = model["context"]
    context["context_cid"] = cid(
        {key: value for key, value in context.items() if key != "context_cid"}
    )
    model["preview_context"] = copy.deepcopy(context)
    raw = json.dumps(
        context, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode()
    model["pins"]["context"] |= {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}


CONTROLS = (
    "invocation_mode",
    "invocation_model",
    "invocation_head",
    "invocation_parent",
    "inference_state",
    "inference_source",
    "inference_latent",
    "inference_training",
    "inference_authority",
    "metrics_epoch",
    "metrics_objective",
    "worker_attestation",
    "boolean_returncode",
    "context_optimizer",
)


def mutate(model: dict[str, Any], name: str) -> None:
    if name == "invocation_mode":
        model["invocation"]["mode"] = "train"
    elif name == "invocation_model":
        model["invocation"]["version_id"] = "sha256:" + "0" * 64
    elif name == "invocation_head":
        model["invocation"]["head"]["generation"] += 1
    elif name == "invocation_parent":
        model["invocation"]["parent_version_id"] = "sha256:" + "0" * 64
    elif name == "inference_state":
        model["inference"]["inference"]["state_sha256"] = "0" * 64
    elif name == "inference_source":
        model["inference"]["inference"]["rows"][0]["source_digest"] = "0" * 64
    elif name == "inference_latent":
        model["inference"]["inference"]["rows"][0]["latent"][0] = 99.0
    elif name == "inference_training":
        model["inference"]["training_executed"] = True
    elif name == "inference_authority":
        model["inference"]["authority"]["qualified"] = True
    elif name == "metrics_epoch":
        model["metrics"]["selected_total_epochs"] += 1
    elif name == "metrics_objective":
        model["metrics"]["after"]["objective"] = 99.0
    elif name == "worker_attestation":
        model["inference"]["worker_receipt"]["source_execution_attested"] = True
    elif name == "boolean_returncode":
        model["inference"]["worker_receipt"]["returncode"] = False
    elif name == "context_optimizer":
        model["context"]["selected_optimizer_steps"][0] += 1
    else:
        raise ValueError("unknown authored auxiliary control")
    repin_model(model)


def controls(cases: dict[str, Any]) -> list[dict[str, Any]]:
    results = []
    for label, baseline in zip(LABELS, cases["06"], strict=True):
        for name in CONTROLS:
            corrupted = copy.deepcopy(baseline)
            mutate(corrupted, name)
            try:
                assert_auxiliary(corrupted)
            except (ValueError, KeyError, TypeError, AdmissionEvidenceError) as error:
                results.append(
                    {"selection": label, "name": name, "refused": True, "error": str(error)}
                )
            else:
                raise AdmissionEvidenceError(
                    "correlated auxiliary corruption accepted: " + label + ":" + name
                )
    return results


def run(manifest: Path, output: Path) -> dict[str, Any]:
    output = output.absolute()
    need(
        not output.exists()
        and output.resolve(strict=False) == output
        and not any(parent.is_symlink() for parent in (output, *output.parents)),
        "fresh canonical nonsymlink output required",
    )
    reader = advisory.PinnedReader()
    manifest = manifest.absolute()
    raw = reader.read(manifest, manifest=True)
    spec = parse_document(raw)
    validate_spec(spec)
    base_pin = spec["prior_advisory_manifest"]
    base = parse_document(reader.read(Path(base_pin["path"]), base_pin, manifest=True))
    advisory.validate_manifest(base)
    need(
        not any(
            output.is_relative_to(Path(row["root"]))
            for row in (*base["attempts"], *spec["attempts"])
        )
        and not any(
            Path(value).is_relative_to(output)
            for value in (str(manifest), base_pin["path"], spec["prior_advisory_report"]["path"])
        ),
        "output overlaps retained input roots or files",
    )
    output.mkdir(parents=True, exist_ok=False)
    report = {
        "schema": SCHEMA,
        "status": "refused",
        "manifest_sha256": hashlib.sha256(raw).hexdigest(),
        "started_at": datetime.now(UTC).isoformat(),
        **dict.fromkeys(FLAGS, False),
        "input_files_unchanged": False,
        "frozen_auxiliary_artifact_bodies_verified": False,
        "prior_advisory_manifest_sha256": base_pin["sha256"],
        "prior_advisory_report_sha256": spec["prior_advisory_report"]["sha256"],
        "limits": {
            "files": advisory.MAX_FILES,
            "file_bytes": advisory.MAX_FILE_BYTES,
            "total_bytes": advisory.MAX_TOTAL_BYTES,
            "manifest_bytes": advisory.MAX_MANIFEST_BYTES,
            "supplemental_bytes": 2 * 1024 * 1024,
        },
        "limitations": [
            "Body bytes and retained structural/numerical consistency only; no numerical state replay, execution provenance authentication or independent numeric correctness.",
            "Metrics are copied prior training observations; their sixteen epochs are not added to frozen fitting or prior attempt accounting.",
            "Worker protocol output digests are retained identifiers; complete native worker protocol input/output envelopes are not selected or rederived.",
            "This supplement does not qualify signatures, current owner state, full archive/runtime closure or current grants.",
        ],
    }
    try:
        cases = load(spec, reader)
        report["selections"] = [
            {"attempt": attempt, "label": label, **assert_auxiliary(model)}
            for attempt, models in cases.items()
            for label, model in zip(LABELS, models, strict=True)
        ]
        results = controls(cases)
        report |= {
            "controls": results,
            "controls_count": len(results),
            "controls_refused": sum(row["refused"] for row in results),
            "controls_scope": "authored inert copies with regenerated unsigned body pins/blob/context CIDs; unchanged independent training anchors",
            "frozen_auxiliary_artifact_bodies_verified": True,
            "selected_auxiliary_body_count": 27,
            "selected_frozen_context_count": 9,
            "additional_attempted_training_epochs": 0,
        }
        report["input_files_unchanged"] = reader.recheck()
        report["status"] = "passed"
    except (
        ValueError,
        OSError,
        KeyError,
        TypeError,
        RecursionError,
        OverflowError,
        AdmissionEvidenceError,
    ) as error:
        report["error"] = type(error).__name__ + ": " + str(error)
        report["frozen_auxiliary_artifact_bodies_verified"] = False
    report |= {
        "read_file_count": len(reader.pins),
        "read_bytes": reader.total,
        "selected_input_pins": reader.pins,
        "finished_at": datetime.now(UTC).isoformat(),
    }
    (output / "frozen_auxiliary_evidence.json").write_text(
        json.dumps(report, sort_keys=True, indent=2, allow_nan=False) + "\n"
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = run(args.manifest, args.output)
    except (
        ValueError,
        OSError,
        KeyError,
        TypeError,
        RecursionError,
        AdmissionEvidenceError,
    ) as error:
        print(
            json.dumps(
                {
                    "status": "refused",
                    "report": None,
                    "error": type(error).__name__ + ": " + str(error),
                },
                allow_nan=False,
            )
        )
        return 3
    print(
        json.dumps(
            {
                "status": report["status"],
                "report": str(args.output / "frozen_auxiliary_evidence.json"),
            },
            allow_nan=False,
        )
    )
    return 0 if report["status"] == "passed" else 3


if __name__ == "__main__":
    raise SystemExit(main())
