#!/usr/bin/env python3
"""Parse-only tests for LRA draft fan-out. No TypeSafe POST, no Leanstral."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

HARNESS = Path(__file__).resolve().parents[1] / "papers/completion/lean_refactor_arena/harness"

import sys

sys.path.insert(0, str(HARNESS))
import draft_fanout as fanout  # noqa: E402
import splice as lra_splice  # noqa: E402


class DraftFanoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = fanout.self_check()

    def test_self_check_ok(self) -> None:
        self.assertTrue(self.report["ok"], json.dumps(self.report, indent=2)[:2000])
        self.assertIsNone(self.report["arena_score"])
        self.assertFalse(self.report["jev_generated_lean"])

    def test_reference_is_d000_and_under_choice_cap(self) -> None:
        for row in self.report["canaries"]:
            self.assertEqual(row["draft_ids"][0], "d000")
            self.assertLessEqual(row["n_drafts"], fanout.MAX_CHOICE_OPTIONS)
            self.assertGreaterEqual(row["n_drafts"], 6)
            self.assertIn("reference", row["families"])

    def test_case_spans_and_templates(self) -> None:
        _raw, _digest, records = lra_splice.load_warmup_records()
        strata = next(item for item in records if item["name"] == fanout.CANARY_NAMES[0])
        drafts = fanout.enumerate_drafts(strata, records)
        self.assertGreaterEqual(len(fanout.case_spans(fanout.tactic_block(strata))), 3)
        families = {item.family for item in drafts}
        self.assertTrue({"reference", "native_hammer", "aesop"} <= families)
        self.assertTrue(any("replace_case" in item.ops for item in drafts))
        self.assertTrue(any(item.tactics == "simp_all" for item in drafts))

    def test_audit_forbids_generator_and_lock(self) -> None:
        audit = self.report["audit"]
        self.assertEqual(audit["forbidden_imports"], [])
        self.assertFalse(audit["uses_lock_ex"])


if __name__ == "__main__":
    unittest.main()
