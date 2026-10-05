"""Extract the 64 exposed authored inputs without reading formal targets.

This stdlib-only preparation declares a separate source-reconstruction policy.
The historical semantic admission masks stay zero. It fits nothing and does not
make the authored development sources an independently reviewed holdout.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

MASKS = ("weak_decoder_fit", "strong_semantic_fit", "contrastive_supervision",
         "proof_supervision", "fidelity_evaluation")
ANNOTATIONS = ("interpretation_status", "ambiguity", "unsupported_meaning", "normative_rules",
               "freeform_qualifier_scope", "notes", "reviewer_id", "reviewed_at_utc")
SCOPE = "exposed_authored_composition_source_reconstruction_only"
MAX_BYTES = 4 * 1024 * 1024


def require(condition, message):
    if not condition:
        raise ValueError(message)


def raw(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def digest(value):
    return hashlib.sha256(raw(value)).hexdigest()


def closed(value, fields, name):
    require(type(value) is dict and set(value) == set(fields), "closed " + name + " required")


def sha(value, name):
    require(type(value) is str and len(value) == 64 and
            all(c in "0123456789abcdef" for c in value), "SHA256 " + name + " required")


def sealed(value):
    require(value.get("content_sha256") == digest({k: v for k, v in value.items()
                                                if k != "content_sha256"}), "content seal differs")


def seal(value):
    return {**value, "content_sha256": digest(value)}


def binding(path):
    path = Path(path).resolve(strict=True)
    data = path.read_bytes()
    return dict(path=str(path), bytes=len(data), sha256=hashlib.sha256(data).hexdigest())


def _pairs(pairs):
    out = {}
    for key, value in pairs:
        require(key not in out, "duplicate JSON key")
        out[key] = value
    return out


def load_bound(path, expected_sha):
    sha(expected_sha, "externally selected file digest")
    path = Path(path).resolve(strict=True)
    require(path.is_file() and path.stat().st_size <= MAX_BYTES, "bounded regular input required")
    data = path.read_bytes()
    require(hashlib.sha256(data).hexdigest() == expected_sha, "external file digest differs")
    value = json.loads(data.decode("utf-8"), object_pairs_hook=_pairs,
                       parse_constant=lambda _: require(False, "finite JSON required"))
    return value, dict(path=str(path), bytes=len(data), sha256=expected_sha)


def validate_and_extract(packet, organizer, old_cohort):
    closed(packet, {"schema", "instructions", "items"}, "reviewer packet")
    require(packet["schema"] == "symbol-binding-source-reviewer/v1", "packet schema differs")
    closed(packet["instructions"], {"task", "context", "normative_rules", "qualifier_scope",
                                   "blank_annotations", "identity", "provenance"},
           "review instructions")
    require(all(type(value) is str and len(value) <= 4096 for value in
                packet["instructions"].values()), "source review instructions must be plain text")
    closed(organizer, {"schema", "rows", "source_groups", "semantic_gold_created",
                     "model_candidates_included", "original_reviews_completed",
                     "source_author_independence_authenticated", "accepted",
                     "independent_semantic_review_completed", "source_fidelity_established",
                     "qualified", "proof_authority", "training_executed", "content_sha256"},
           "organizer manifest")
    sealed(organizer)
    require(organizer["schema"] == "symbol-binding-review-organizer/v1", "organizer schema differs")
    require(organizer["source_groups"] == 16 and organizer["original_reviews_completed"] == 0,
            "unreviewed 16-group packet required")
    for key in ("semantic_gold_created", "model_candidates_included",
                "source_author_independence_authenticated", "accepted",
                "independent_semantic_review_completed", "source_fidelity_established",
                "qualified", "proof_authority", "training_executed"):
        require(organizer[key] is False, "unadmitted organizer status required")
    closed(old_cohort, {"schema", "rows", "contains_formal_targets", "content_sha256"},
           "old target-free cohort")
    sealed(old_cohort)
    require(old_cohort["schema"] == "source-only-frozen-evaluation-cohort/v1" and
            old_cohort["contains_formal_targets"] is False, "old target-free cohort required")
    require(type(old_cohort["rows"]) is list and len(old_cohort["rows"]) == 34,
            "old 34 source metadata rows required")
    for row in old_cohort["rows"]:
        closed(row, {"id", "split", "group_id", "source_sha256", "input_sha256", "context_role"},
               "old cohort row")
        sha(row["source_sha256"], "old source")
        sha(row["input_sha256"], "old input")
    require(type(packet["items"]) is list and len(packet["items"]) == 64,
            "exactly 64 reviewer inputs required")
    require(type(organizer["rows"]) is list and len(organizer["rows"]) == 64,
            "exactly 64 organizer rows required")
    private = {}
    for row in organizer["rows"]:
        closed(row, {"action_surface", "actor_surface", "group_id", "input_sha256", "item_id",
                     "masks", "natural_source", "object_surface", "proposed_split", "review_status",
                     "semantic_gold_created", "source_origin", "source_sha256", "variant_index"},
               "organizer row")
        closed(row["masks"], MASKS, "semantic masks")
        require(all(type(row["masks"][key]) is int and row["masks"][key] == 0 for key in MASKS),
                "all five semantic admission masks must remain zero")
        require(row["natural_source"] is False and row["semantic_gold_created"] is False and
                row["review_status"] == "pending" and
                row["source_origin"] == "programmatically_authored_controlled_English_fixture",
                "pending authored source status required")
        require(all(type(row[key]) is str and len(row[key]) <= 4096 for key in
                    ("actor_surface", "action_surface", "object_surface")),
                "organizer surfaces must remain bounded plain text")
        require(type(row["item_id"]) is str and row["item_id"] not in private,
                "unique organizer item ID required")
        require(type(row["group_id"]) is str and
                row["group_id"].startswith("authored-binding-composition-v1:"),
                "original authored group required")
        require(type(row["variant_index"]) is int and 0 <= row["variant_index"] < 4,
                "variant index required")
        require(row["proposed_split"] in {"proposed_train", "proposed_development"},
                "known proposed split required")
        private[row["item_id"]] = row
    rows = []
    seen = set()
    for item in packet["items"]:
        closed(item, {"annotation", "context", "input_sha256", "item_id", "source_sha256",
                      "source_text"}, "reviewer source item")
        closed(item["annotation"], ANNOTATIONS, "blank annotation")
        require(all(value is None for value in item["annotation"].values()),
                "only original blank source packet admitted")
        item_id = item["item_id"]
        require(type(item_id) is str and item_id in private and item_id not in seen,
                "unique joined reviewer ID required")
        seen.add(item_id)
        source = item["source_text"]
        require(type(source) is str and source.strip() and "\0" not in source and
                len(source.encode("utf-8")) <= 65536, "bounded exact source required")
        context = item["context"]
        closed(context, {"role", "text", "bindings", "sha256"}, "source context")
        require(context == {"role": "none_required", "text": "", "bindings": {},
                            "sha256": hashlib.sha256(b"").hexdigest()},
                "packet requires original none-required empty context")
        request = dict(source_text=source, context=context)
        source_sha = hashlib.sha256(source.encode("utf-8")).hexdigest()
        input_sha = digest(request)
        expected_item = "binding-review-item-" + hashlib.sha256(
            b"authored-binding-review-v1\0" + bytes.fromhex(input_sha)).hexdigest()[:24]
        require(item_id == expected_item and item["source_sha256"] == source_sha and
                item["input_sha256"] == input_sha, "reviewer source identity differs")
        original = private[item_id]
        require(original["source_sha256"] == source_sha and
                original["input_sha256"] == input_sha, "organizer source join differs")
        rows.append(dict(id="sha256:" + input_sha, input=request, input_sha256=input_sha,
                         source_sha256=source_sha, group_id=original["group_id"],
                         split={"proposed_train": "train", "proposed_development": "development"}
                         [original["proposed_split"]], review_item_id=item_id))
    require(len({row["id"] for row in rows}) == len({row["source_sha256"] for row in rows}) == 64,
            "64 unique source/input identities required")
    groups = {}
    for row in rows:
        groups.setdefault(row["group_id"], []).append(row)
    require(len(groups) == 16 and all(len(group) == 4 for group in groups.values()),
            "16 four-variant groups required")
    for group_id, group in groups.items():
        require(len({row["split"] for row in group}) == 1, "group leakage across splits")
        require({private[row["review_item_id"]]["variant_index"] for row in group} == set(range(4)),
                "complete original variants required")
        suffix = group_id.removeprefix("authored-binding-composition-v1:").split(":")
        require(len(suffix) == 2 and all(part in {"0", "1", "2", "3"} for part in suffix),
                "original actor/pair group identity required")
        actor, pair = map(int, suffix)
        split = "train" if (actor - pair) % 4 in (0, 1) else "development"
        require(group[0]["split"] == split, "original pre-annotation group split differs")
    require(Counter(row["split"] for row in rows) == {"train": 32, "development": 32},
            "32/32 source split required")
    overlap = {}
    for key in ("source_sha256", "input_sha256", "id", "group_id"):
        old_values = {row[key] for row in old_cohort["rows"]}
        overlap[key] = len(old_values & {row[key] for row in rows})
        require(overlap[key] == 0, "source cohort exact overlap: " + key)
        train = {row[key] for row in rows if row["split"] == "train"}
        dev = {row[key] for row in rows if row["split"] == "development"}
        require(not train & dev, "TRAIN/DEV overlap: " + key)
    return sorted(rows, key=lambda row: row["id"]), overlap


def save(path, value):
    with path.open("xb") as stream:
        stream.write(raw(value) + b"\n")
    return binding(path)


def prepare(packet_path, packet_sha, organizer_path, organizer_sha,
            old_cohort_path, old_cohort_sha, output_directory):
    source_paths = ((packet_path, packet_sha), (organizer_path, organizer_sha),
                    (old_cohort_path, old_cohort_sha))
    loaded = [load_bound(path, expected) for path, expected in source_paths]
    rows, overlap = validate_and_extract(*(value for value, _ in loaded))
    output = Path(output_directory).resolve()
    require(not output.exists(), "fresh output directory required")
    source_policy = dict(scope=SCOPE, source_reconstruction_fit_authorized=True,
                         semantic_masks={key: 0 for key in MASKS}, semantic_label_admission=False,
                         independent_semantic_review_completed=False, source_fidelity_established=False,
                         natural_sources=False, pristine_holdout=False,
                         reused_exposed_components=True, formal_targets_read=False,
                         proof_authority=False, qualified=False)
    outputs = {}
    output.mkdir(parents=True)
    for name, selected in (("source-inputs.json", rows),
                           ("train-inputs.json", [r for r in rows if r["split"] == "train"]),
                           ("development-inputs.json", [r for r in rows if r["split"] == "development"])):
        outputs[name] = save(output / name, seal(dict(
            schema="source-only-authored-expansion-inputs/v1", rows=selected,
            row_count=len(selected), input_recipe="exact_source_only/v1",
            policy=source_policy, contains_formal_targets=False)))
    metadata = [{key: row[key] for key in ("id", "split", "group_id", "source_sha256", "input_sha256")}
                | {"context_role": row["input"]["context"]["role"]} for row in rows]
    outputs["cohort-metadata.json"] = save(output / "cohort-metadata.json", seal(dict(
        schema="source-only-authored-expansion-cohort/v1", rows=metadata,
        contains_formal_targets=False, policy=source_policy)))
    for (_, prior_binding) in loaded:
        require(binding(prior_binding["path"]) == prior_binding, "source input changed during extraction")
    receipt = seal(dict(schema="source-only-authored-expansion-preparation/v1", status="prepared",
        helper_binding=binding(__file__), reviewer_packet_binding=loaded[0][1],
        organizer_binding=loaded[1][1], prior_cohort_binding=loaded[2][1],
        output_bindings=outputs, rows=64, groups=16, variants_per_group=4,
        train_rows=32, development_rows=32, train_groups=8, development_groups=8,
        group_ids_are_semantic_equivalence_labels=False,
        exact_overlap_with_prior34=overlap, train_development_exact_overlap=0,
        context_roles={"none_required": 64}, semantic_masks={key: 0 for key in MASKS},
        source_only_reconstruction_policy=source_policy,
        formal_targets_read=False, model_calls=0, backbone_calls=0,
        optimizer_updates=0, network_calls=0, prover_calls=0,
        independent_reviews_created=0, semantic_labels_admitted=0,
        source_files_unchanged=True, published=False))
    return save(output / "preparation-receipt.json", receipt)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("reviewer-packet", "organizer", "old-cohort"):
        parser.add_argument("--" + name, required=True)
        parser.add_argument("--" + name + "-sha256", required=True)
    parser.add_argument("--output-directory", required=True)
    args = parser.parse_args()
    result = prepare(args.reviewer_packet, args.reviewer_packet_sha256,
                     args.organizer, args.organizer_sha256, args.old_cohort,
                     args.old_cohort_sha256, args.output_directory)
    print(json.dumps(dict(receipt_binding=result, rows=64, train_rows=32,
                          development_rows=32), sort_keys=True))


if __name__ == "__main__":
    main()
