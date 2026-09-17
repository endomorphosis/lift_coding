#!/usr/bin/env python3
"""Parse-only Track 1 Mistral Labs adapter tests. No live POST."""

from __future__ import annotations

import unittest
from pathlib import Path
import sys

HARNESS = Path(__file__).resolve().parents[1] / "papers/completion/lean_refactor_arena/harness"
sys.path.insert(0, str(HARNESS))
import track1_ledger as lra_t1  # noqa: E402
import track1_mistral_leanstral as mistral  # noqa: E402


class Track1MistralTests(unittest.TestCase):
    def test_self_check_refuses_docker0_and_prices_zero(self) -> None:
        report = mistral.self_check()
        self.assertTrue(report["ok"], report)
        self.assertTrue(report["refuses_docker0"])
        self.assertTrue(report["labs_priced_zero"])
        self.assertTrue(report["official_track2_stays_off"])
        self.assertEqual(report["hardware_class"], "mistral_labs_api")
        self.assertIsNone(report["arena_score"])

    def test_usd_for_mistral_is_zero(self) -> None:
        self.assertEqual(float(lra_t1.usd_for("mistral", 2_000_000, 50_000)), 0.0)

    def test_ledger_counts_mistral_separately_from_grok(self) -> None:
        ledger = lra_t1.ProblemLedger(name="x")
        first = ledger.record("mistral", input_tokens=100, output_tokens=10, fixture=True)
        second = ledger.record("mistral", input_tokens=100, output_tokens=10, fixture=True)
        third = ledger.record("mistral", input_tokens=100, output_tokens=10, fixture=True)
        self.assertFalse(first.skipped)
        self.assertFalse(second.skipped)
        self.assertTrue(third.skipped)
        self.assertEqual(third.reason, "max_mistral_calls")
        self.assertEqual(ledger.mistral_calls, 2)
        self.assertEqual(ledger.grok_calls, 0)

    def test_pca_mca_self_check_and_mca_maps_simp_at_to_strength(self) -> None:
        import pca_mca_fanout as pca

        report = pca.self_check()
        self.assertTrue(report["ok"], report.get("audit"))
        self.assertIsNone(report["arena_score"])
        self.assertAlmostEqual(sum(report["pca"]["explained_ratio"]), 1.0, places=5)
        sample = report["sample"]
        self.assertGreaterEqual(sample["n_drafts"], 2)
        self.assertTrue(
            any(fam in {"dead_code", "strength_reduction", "algebraic_simplification"} for fam in sample["families"])
        )
        self.assertIn("algebraic_simplification", pca.FAMILY_FEATURES)
        collapsed = pca.collapse_rw_to_simp("  rw [a]\n  rw [b]\n  exact h\n")
        self.assertIn("simp [a, b]", collapsed)
        self.assertNotIn("rw [a]", collapsed)

    def test_drop_redundant_simp_at_keeps_following_simp_all(self) -> None:
        import draft_fanout as fanout

        body = (
            "    intros x Hin\n"
            "    simp at m\n"
            "    simp at name\n"
            "    simp at ty2\n"
            "\n"
            "    simp_all\n"
        )
        out = fanout.drop_redundant_simp_at(body)
        self.assertNotIn("simp at m", out)
        self.assertEqual(out.count("simp_all"), 1)

    def test_flatten_overindent_aligns_case_lines(self) -> None:
        import track1_keepbest as keepbest

        reference = "  induction post <;> simp [substOld]\n  case fvar =>\n    intros x Hin\n"
        hosted = "  induction post <;> simp [substOld]\n    case fvar =>\n      intros x Hin\n"
        fixed = keepbest.flatten_overindent(reference, hosted)
        self.assertIn("\n  case fvar =>\n", "\n" + fixed)
        self.assertNotIn("\n    case fvar =>\n", "\n" + fixed)

    def test_assert_hosted_url_blocks_spark(self) -> None:
        with self.assertRaises(mistral.Track1MistralError):
            mistral.assert_hosted_url("http://172.17.0.1:8080/v1/chat/completions")
        mistral.assert_hosted_url("https://api.mistral.ai/v1/chat/completions")


if __name__ == "__main__":
    unittest.main()
