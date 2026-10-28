"""Repair packer reservation regressions; no provider or application execution."""
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

REPO = Path(os.environ.get("SVF_FOUNDATION_REPOSITORY_ROOT", Path(__file__).resolve().parents[1]))
SCRIPTS = Path(os.environ.get("SVF_VPC_CANDIDATE_SCRIPTS", REPO / "scripts"))
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(SCRIPTS))
import swissknife_visual_functional_worker as worker
import swissknife_visual_functional_llm as llm


def cost(path, content):
    return len(json.dumps({"path": path, "content": content}, ensure_ascii=False, separators=(",", ":")).encode())


class RepairInputReservationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir="/dev/shm", prefix="svf-reservations-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.patch = patch.object(worker, "ROOT", self.root)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.context = self.write("model-inputs/context.json", "{}\n")
        self.directory = self.context.parent
        self.task = {"task_id": "SVF-777", "edit_paths": ["app.js"]}
        self.profile = {"llm": {"repairReadPolicy": "inline_only"}}

    def write(self, name, content):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def overhead(self):
        return cost("model-inputs/context.json", self.context.read_text()) + len(json.dumps(json.dumps(self.task, ensure_ascii=False), ensure_ascii=False).encode()) + 4096 + 256 * len(self.task["edit_paths"])

    def pack(self, paths, budget):
        return worker._repair_inputs(self.profile, self.task, paths, self.context, self.directory, budget)

    def test_complete_short_readonly_inputs_use_exact_cost_at_the_budget_boundary(self):
        self.write("app.js", "const complete = true;\n" * 300)
        self.write("failure.txt", "command exit 1: MISSING_OBSERVATION\n")
        self.write("small.json", '{"diagnostic":true}\n')
        paths = ["failure.txt", "app.js", "small.json"]
        budget = self.overhead() + sum(cost(name, (self.root / name).read_text()) for name in paths)
        selected, records, complete = self.pack(paths, budget)
        self.assertEqual(set(selected), set(paths))
        self.assertEqual({r["path"] for r in records}, set(paths))
        self.assertEqual(complete, [worker.artifact(self.root / "app.js")])
        self.assertEqual(list(self.directory.iterdir()), [self.context])

    def test_short_readonly_source_is_retained_while_large_supporting_source_is_projected(self):
        self.write("app.js", "const complete = true;\n" * 300)
        self.write("failure.txt", "actual pointer was absent\n")
        self.write("driver.md", "Known driver rule must remain source bound.\n" * 1000)
        paths = ["failure.txt", "app.js", "driver.md"]
        budget = self.overhead() + cost("app.js", (self.root / "app.js").read_text()) + cost("failure.txt", (self.root / "failure.txt").read_text()) + 2048
        selected, records, complete = self.pack(paths, budget)
        self.assertIn("failure.txt", selected)
        self.assertIn("app.js", selected)
        projected = next(name for name in selected if name not in paths)
        body = json.loads((self.root / projected).read_text())
        self.assertEqual(body["original"], worker.artifact(self.root / "driver.md"))
        self.assertTrue(body["excerpt_only"])
        self.assertEqual(complete, [worker.artifact(self.root / "app.js")])
        self.assertEqual({r["path"] for r in records}, set(paths))
        self.assertLessEqual(self.overhead() + sum(cost(name, (self.root / name).read_text()) for name in selected), budget)

    def test_required_feedback_and_edit_targets_remain_complete(self):
        self.write("app.js", "const complete = true;\n" * 200)
        self.write("required.json", json.dumps({"actual": "native diagnostic" * 300}))
        self.write("short.txt", "readonly witness\n")
        self.task["_required_context_paths"] = ["required.json"]
        paths = ["required.json", "short.txt", "app.js"]
        budget = self.overhead() + sum(cost(name, (self.root / name).read_text()) for name in paths)
        selected, _, complete = self.pack(paths, budget)
        self.assertEqual(set(selected), set(paths))
        self.assertEqual(complete, [worker.artifact(self.root / "app.js")])

    def test_true_mandatory_floor_overflow_fails_before_any_projection_write(self):
        self.write("app.js", "const complete = true;\n" * 200)
        self.write("short.txt", "readonly witness\n")
        paths = ["app.js", "short.txt"]
        floor = self.overhead() + sum(cost(name, (self.root / name).read_text()) for name in paths)
        with self.assertRaises(llm.ModelContextBudgetError) as caught:
            self.pack(paths, floor - 1)
        self.assertEqual(caught.exception.actual_bytes, floor)
        self.assertEqual(list(self.directory.iterdir()), [self.context])
        self.assertEqual((self.root / "app.js").read_text(), "const complete = true;\n" * 200)

    def test_cost_includes_json_escaping_and_utf8_instead_of_raw_length(self):
        self.write("app.js", "const complete = true;\n" * 100)
        self.write("quoted.txt", '"\\雪' * 170)
        self.assertLess((self.root / "quoted.txt").stat().st_size, 2048)
        paths = ["app.js", "quoted.txt"]
        floor = self.overhead() + sum(cost(name, (self.root / name).read_text()) for name in paths)
        self.assertGreater(cost("quoted.txt", (self.root / "quoted.txt").read_text()), (self.root / "quoted.txt").stat().st_size)
        selected, _, _ = self.pack(paths, floor)
        self.assertEqual(set(selected), set(paths))
        with self.assertRaises(llm.ModelContextBudgetError):
            self.pack(paths, floor - 1)

    def test_existing_source_and_mode_caps_do_not_change(self):
        self.write("app.js", "x" * 250001)
        with self.assertRaises(llm.ModelContextBudgetError):
            self.pack(["app.js"], 600000)
        self.assertEqual(llm.REPAIR_MAX_PROMPT_BYTES, 262144)
        self.assertEqual(llm.REVIEW_MAX_PROMPT_BYTES, 32768)
        self.assertEqual(llm.MAX_PROMPT_BYTES, 600000)
        self.assertEqual(llm.MAX_FILE_BYTES, 1048576)


if __name__ == "__main__":
    unittest.main()
