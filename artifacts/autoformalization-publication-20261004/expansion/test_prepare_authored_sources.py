"""Contract tests use invented source envelopes, never a model or formal target."""
import copy
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

HELPER = Path(__file__).with_name("prepare_authored_sources.py")
SPEC = importlib.util.spec_from_file_location("source_preparation", HELPER)
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


def fixture():
    items, private = [], []
    for actor in range(4):
        for pair in range(4):
            group = f"authored-binding-composition-v1:{actor}:{pair}"
            split = "proposed_train" if (actor - pair) % 4 in (0, 1) else "proposed_development"
            for variant in range(4):
                source = f"Invented source {actor}-{pair}-{variant}."
                context = dict(role="none_required", text="", bindings={},
                               sha256=hashlib.sha256(b"").hexdigest())
                source_sha = hashlib.sha256(source.encode()).hexdigest()
                input_sha = module.digest(dict(source_text=source, context=context))
                item_id = "binding-review-item-" + hashlib.sha256(
                    b"authored-binding-review-v1\0" + bytes.fromhex(input_sha)).hexdigest()[:24]
                items.append(dict(item_id=item_id, source_text=source, context=context,
                                  source_sha256=source_sha, input_sha256=input_sha,
                                  annotation={key: None for key in module.ANNOTATIONS}))
                private.append(dict(item_id=item_id, group_id=group, proposed_split=split,
                                    variant_index=variant, actor_surface="actor", action_surface="action",
                                    object_surface="object", source_sha256=source_sha,
                                    input_sha256=input_sha,
                                    source_origin="programmatically_authored_controlled_English_fixture",
                                    review_status="pending", natural_source=False,
                                    semantic_gold_created=False,
                                    masks={key: 0 for key in module.MASKS}))
    packet = dict(schema="symbol-binding-source-reviewer/v1", items=items,
                  instructions={key: "Source-only instruction" for key in
                                ("task", "context", "normative_rules", "qualifier_scope",
                                 "blank_annotations", "identity", "provenance")})
    organizer = module.seal(dict(schema="symbol-binding-review-organizer/v1", rows=private,
        source_groups=16, original_reviews_completed=0,
        **dict.fromkeys(("semantic_gold_created", "model_candidates_included",
            "source_author_independence_authenticated", "accepted",
            "independent_semantic_review_completed", "source_fidelity_established",
            "qualified", "proof_authority", "training_executed"), False)))
    old = module.seal(dict(schema="source-only-frozen-evaluation-cohort/v1",
                          contains_formal_targets=False,
                          rows=[dict(id="old" + str(i), group_id="old-group" + str(i),
                              source_sha256=hashlib.sha256(f"old-source{i}".encode()).hexdigest(),
                              input_sha256=hashlib.sha256(f"old-input{i}".encode()).hexdigest(),
                              context_role="none_required", split="train") for i in range(34)]))
    return packet, organizer, old


def reseal(value):
    value.pop("content_sha256")
    value.update(module.seal(value))


class SourcePreparationTests(unittest.TestCase):
    def test_complete_cohort_group_split(self):
        rows, overlap = module.validate_and_extract(*fixture())
        self.assertEqual(len(rows), 64)
        self.assertEqual(sum(row["split"] == "train" for row in rows), 32)
        self.assertEqual(len({row["group_id"] for row in rows}), 16)
        self.assertEqual(set(overlap.values()), {0})
        self.assertEqual(rows, sorted(rows, key=lambda row: row["id"]))

    def test_nonzero_semantic_mask_rejected(self):
        packet, organizer, old = fixture()
        organizer["rows"][0]["masks"]["weak_decoder_fit"] = 1
        reseal(organizer)
        with self.assertRaisesRegex(ValueError, "five semantic"):
            module.validate_and_extract(packet, organizer, old)

    def test_bool_mask_rejected(self):
        packet, organizer, old = fixture()
        organizer["rows"][0]["masks"]["weak_decoder_fit"] = False
        reseal(organizer)
        with self.assertRaisesRegex(ValueError, "five semantic"):
            module.validate_and_extract(packet, organizer, old)

    def test_group_leakage_rejected(self):
        packet, organizer, old = fixture()
        organizer["rows"][0]["proposed_split"] = "proposed_development"
        reseal(organizer)
        with self.assertRaisesRegex(ValueError, "group leakage"):
            module.validate_and_extract(packet, organizer, old)

    def test_changed_preannotation_group_split_rejected(self):
        packet, organizer, old = fixture()
        group = organizer["rows"][0]["group_id"]
        for row in organizer["rows"]:
            if row["group_id"] == group:
                row["proposed_split"] = "proposed_development"
        reseal(organizer)
        with self.assertRaisesRegex(ValueError, "pre-annotation"):
            module.validate_and_extract(packet, organizer, old)

    def test_reference_body_rejected(self):
        packet, organizer, old = fixture()
        packet["items"][0]["canonical_ir"] = {"rule": "invented"}
        with self.assertRaisesRegex(ValueError, "closed reviewer"):
            module.validate_and_extract(packet, organizer, old)

    def test_completed_annotation_rejected(self):
        packet, organizer, old = fixture()
        packet["items"][0]["annotation"]["notes"] = "Unadmitted review"
        with self.assertRaisesRegex(ValueError, "blank source"):
            module.validate_and_extract(packet, organizer, old)

    def test_source_edit_rejected(self):
        packet, organizer, old = fixture()
        packet["items"][0]["source_text"] += "changed"
        with self.assertRaisesRegex(ValueError, "identity differs"):
            module.validate_and_extract(packet, organizer, old)

    def test_context_edit_rejected(self):
        packet, organizer, old = fixture()
        packet["items"][0]["context"]["role"] = "required_unavailable"
        with self.assertRaisesRegex(ValueError, "none-required"):
            module.validate_and_extract(packet, organizer, old)

    def test_duplicate_id_rejected(self):
        packet, organizer, old = fixture()
        packet["items"][1] = copy.deepcopy(packet["items"][0])
        with self.assertRaisesRegex(ValueError, "unique joined"):
            module.validate_and_extract(packet, organizer, old)

    def test_earlier_source_overlap_rejected(self):
        packet, organizer, old = fixture()
        old["rows"][0]["source_sha256"] = packet["items"][0]["source_sha256"]
        reseal(old)
        with self.assertRaisesRegex(ValueError, "exact overlap"):
            module.validate_and_extract(packet, organizer, old)

    def test_tampered_seal_rejected(self):
        packet, organizer, old = fixture()
        organizer["qualified"] = True
        with self.assertRaisesRegex(ValueError, "seal differs"):
            module.validate_and_extract(packet, organizer, old)

    def test_external_pins_duplicate_json_keys_and_fresh_output(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            p = path / "duplicate.json"
            p.write_text('{"schema":1,"schema":2}')
            with self.assertRaisesRegex(ValueError, "duplicate"):
                module.load_bound(p, module.binding(p)["sha256"])
            with self.assertRaisesRegex(ValueError, "external file"):
                module.load_bound(p, "0" * 64)
            packet, organizer, old = fixture()
            files = []
            for index, value in enumerate((packet, organizer, old)):
                source_path = path / f"input{index}.json"
                source_path.write_bytes(module.raw(value))
                files.extend([source_path, module.binding(source_path)["sha256"]])
            output = path / "outputs"
            reference = module.prepare(*files, output)
            receipt = json.loads(Path(reference["path"]).read_bytes())
            module.sealed(receipt)
            self.assertEqual(receipt["rows"], 64)
            self.assertEqual(receipt["semantic_masks"], {key: 0 for key in module.MASKS})
            for value in receipt["output_bindings"].values():
                self.assertEqual(module.binding(value["path"]), value)
                result = json.loads(Path(value["path"]).read_bytes())
                module.sealed(result)
                self.assertFalse(result["contains_formal_targets"])
                self.assertFalse(result["policy"]["pristine_holdout"])
            with self.assertRaisesRegex(ValueError, "fresh output"):
                module.prepare(*files, output)


if __name__ == "__main__":
    unittest.main()
