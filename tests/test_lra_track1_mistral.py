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

    def test_constrained_beam_pca_prefix_and_fixture_greedy(self) -> None:
        import constrained_beam as beam
        import splice as lra_splice

        report = beam.self_check()
        self.assertTrue(report["ok"], report)
        self.assertEqual(report["hardware_class"], "spark_gb10")
        self.assertFalse(report["called_hosted_mistral"])
        records = lra_splice.load_warmup_records()[2]
        record = next(item for item in records if item["name"] == "Core.InitsUpdatesComm")
        lines = iter(["  case update_none =>", "    simp_all", "STOP"])

        def fake_generate(prompt, **kwargs):
            del prompt, kwargs
            return next(lines, "STOP")

        def fake_prune(record, prefix, candidates, *, ledger, keep):
            del record, prefix, ledger
            kept = [item for item in candidates if item != "STOP"][:keep] or ["STOP"]
            return {"skipped": True, "reason": "fixture", "kept": kept, "jev_generated_lean": False}

        result = beam.run_search(
            record,
            mode="greedy",
            max_steps=3,
            beam=1,
            temperature=0.9,
            generate=fake_generate,
            prune=fake_prune,
        )
        self.assertEqual(result["temperature"], 0.9)
        junk = beam.parse_next_line("<|im_start|>system\n  simp_all\n")
        self.assertEqual(junk.strip(), "simp_all")
        self.assertFalse(result["called_hosted_mistral"])
        self.assertEqual(result["hardware_class"], "spark_gb10")
        self.assertGreaterEqual(len(result["finals"]), 1)
        self.assertIn("induction", result["pca_prefix"])
        self.assertIn("have Hlen1", result["pca_prefix"])
        self.assertNotIn("have Hlen2", result["pca_prefix"])
        self.assertNotIn("have Hk", result["pca_prefix"])
        self.assertEqual(result["ledger"]["mistral_calls"], 0)
        self.assertEqual(result["ledger"]["grok_calls"], 0)

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

    def test_mca_mask_keeps_case_skeleton(self) -> None:
        import mca_mask_replace as mask

        report = mask.self_check()
        self.assertTrue(report["ok"], report)
        self.assertGreaterEqual(report["n_holes"], 2)
        self.assertIn("strength_reduction", report["families"])

    def test_few_shot_examples_have_scored_cuts(self) -> None:
        import mca_mask_replace as mask
        import splice as lra_splice

        records = lra_splice.load_warmup_records()[2]
        rec = next(item for item in records if item["name"] == "CallElimCorrect.substOldPostSubset")
        shot = mask.few_shot_example(rec)
        self.assertLess(shot["ratio"], 1.0)
        self.assertEqual(shot["filled_tokens"], 414)
        self.assertGreater(shot["n_holes"], 0)

    def test_hammer_restores_identifier_and_rewrites_grind(self) -> None:
        import mca_mask_replace as mask

        reference = "  have Hlen1 : ks.length = vs.length := by sorry\n  exact Hlen1\n"
        draft = "  grind\n  exact Hlen1\n"
        errors = [{"data": "Unknown identifier `Hlen1`"}, {"data": "unknown tactic"}]
        out = mask.hammer_repair(draft, reference, errors)
        self.assertIn("have Hlen1", out)
        self.assertNotIn("grind", out)
        self.assertIn("simp_all", out)
        tagged = mask.hammer_repair(
            "  case update_some =>\n    simp_all\n",
            "  induction Hup\n  case update_none =>\n    simp_all\n",
            [{"data": "Case tag `update_some` not found."}],
        )
        self.assertNotIn("update_some", tagged)
        self.assertIn("induction Hup", tagged)

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

    def test_grok_callable_accepts_cli_oauth_without_xai_key(self) -> None:
        import tempfile

        self.assertFalse(lra_t1.grok_key_configured({}))
        with tempfile.TemporaryDirectory() as tmp:
            self.assertFalse(lra_t1.grok_callable({"GROK_HOME": tmp}))
        self.assertTrue(lra_t1.grok_callable({"XAI_API_KEY": "xai-test"}))
        self.assertTrue(
            lra_t1.grok_cli_auth_configured() or lra_t1.grok_key_configured(),
            "live host should have grok CLI OAuth or an xAI key",
        )

    def test_few_shot_prompt_includes_shots_and_inits_target(self) -> None:
        import mca_mask_replace as mask
        import splice as lra_splice

        records = lra_splice.load_warmup_records()[2]
        target = next(item for item in records if item["name"] == "Core.InitsUpdatesComm")
        shots = mask.shot_examples(records, skip_name=target["name"])
        self.assertEqual(
            [shot["name"] for shot in shots],
            ["CallElimCorrect.substOldPostSubset", "CallElimCorrect.extractedOldExprInVars"],
        )
        prompt = mask.few_shot_prompt(target, shots)
        self.assertIn("TARGET: Core.InitsUpdatesComm", prompt)
        self.assertIn("CallElimCorrect.substOldPostSubset", prompt)
        self.assertIn("CallElimCorrect.extractedOldExprInVars", prompt)
        self.assertIn("PCA skeleton", prompt)
        self.assertNotIn("172.17.0.1", prompt)

    def test_kind_needs_hammer_covers_grok_and_leanstral(self) -> None:
        import mca_mask_replace as mask

        self.assertTrue(mask._kind_needs_hammer("grok_few_shot"))
        self.assertTrue(mask._kind_needs_hammer("grok_few_shot_repair"))
        self.assertTrue(mask._kind_needs_hammer("leanstral_few_shot"))
        self.assertTrue(mask._kind_needs_hammer("tactician_drop_simp_all"))
        self.assertTrue(mask._kind_needs_hammer("hybrid_ref_case_update_some"))
        self.assertTrue(mask._kind_needs_hammer("pca_d001_dead_code"))
        self.assertFalse(mask._kind_needs_hammer("reference"))
        self.assertFalse(mask._kind_needs_hammer("mca_template_fill"))

    def test_hammer_drops_no_progress_simp_all_and_hybrids_swap_case(self) -> None:
        import mca_mask_replace as mask

        reference = (
            "  induction Hup\n"
            "  case update_none =>\n"
            "    simp_all\n"
            "  case update_some =>\n"
            "    rw [List.unzip_zip] <;> simp_all\n"
            "    apply (ih Hinit ?_ ?_).2.2\n"
        )
        grok = (
            "  induction Hup\n"
            "  case update_none =>\n"
            "    simp_all\n"
            "  case update_some =>\n"
            "    exact InitStatesNotDefined Hinit\n"
            "    exact ih.2.2\n"
        )
        dropped = mask.hammer_repair(grok, reference, [{"data": "simp_all made no progress"}])
        self.assertNotEqual(dropped, grok)
        self.assertEqual(dropped.count("simp_all"), 0)
        typed = mask.hammer_repair(
            grok,
            reference,
            [{"data": "Type mismatch\n  InitStatesNotDefined Hinit\nhas type\n  isNotDefined"}],
        )
        self.assertIn("unzip_zip", typed)
        self.assertIn("apply (ih Hinit", typed)
        swapped = mask.replace_case_from(grok, reference, "update_some")
        self.assertIn("unzip_zip", swapped)
        self.assertIn("case update_none", swapped)
        variants = mask.grok_tactician_variants(grok, reference)
        kinds = {item["kind"] for item in variants}
        self.assertIn("tactician_drop_simp_all", kinds)
        self.assertTrue(any(kind.startswith("hybrid_") for kind in kinds), kinds)

    def test_grok_file_prompt_and_read_ignore_chat(self) -> None:
        import tempfile

        prompt = lra_t1.grok_file_prompt("TARGET: Core.InitsUpdatesComm\n")
        self.assertIn("tactics.lean", prompt)
        self.assertIn("Do not put the tactics in chat", prompt)
        self.assertIn("write_file", prompt)
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "tactics.lean").write_text(
                "-- REPLACE_THIS_FILE\n  induction Hup\n  simp_all\n",
                encoding="utf-8",
            )
            tactics = lra_t1.read_grok_tactics_file(workspace)
            self.assertIn("induction Hup", tactics)
            self.assertNotIn("REPLACE_THIS_FILE", tactics)
            self.assertNotIn("I'll locate", tactics)
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "tactics.lean").write_text(lra_t1.GROK_FILE_STUB, encoding="utf-8")
            with self.assertRaises(lra_t1.Track1LedgerError):
                lra_t1.read_grok_tactics_file(workspace)

    def test_generate_grok_file_uses_file_not_chat(self) -> None:
        import tempfile

        workspace = Path(tempfile.mkdtemp())
        ledger = lra_t1.ProblemLedger(name="Core.InitsUpdatesComm#grok-file")
        factory = lra_t1.FixtureGrok(text="  induction Hup\n  simp_all\n")
        result = lra_t1.generate_grok_file(
            "I'll locate the theorem in chat",
            ledger,
            workspace=workspace,
            generate=factory,
            fixture=True,
            reset_stub=True,
        )
        self.assertTrue(result.used_file)
        self.assertTrue(result.chat_ignored)
        self.assertIn("induction Hup", result.tactics)
        self.assertNotIn("I'll locate", result.tactics)
        on_disk = (workspace / "tactics.lean").read_text(encoding="utf-8")
        self.assertIn("induction Hup", on_disk)
        self.assertEqual(ledger.grok_calls, 1)

    def test_build_grok_file_command_writes_cwd_file(self) -> None:
        import tempfile

        workspace = Path(tempfile.mkdtemp())
        prompt_path = workspace / "PROMPT.txt"
        prompt_path.write_text("x", encoding="utf-8")
        cmd = lra_t1.build_grok_file_command(workspace, prompt_path)
        self.assertIn("--cwd", cmd)
        self.assertEqual(cmd[cmd.index("--cwd") + 1], str(workspace))
        self.assertNotIn("--sandbox", cmd)
        self.assertEqual(cmd[cmd.index("--tools") + 1], "write_file")
        self.assertIn("run_terminal_cmd,web_search,web_fetch,Agent,read_file,list_dir,grep,search_replace", cmd)
        self.assertIn("Write(tactics.lean)", cmd)
        self.assertIn("--always-approve", cmd)
        self.assertNotEqual(cmd[cmd.index("--leader-socket") + 1], str(Path.home() / ".grok" / "leader.sock"))

    def test_live_grok_kwargs_isolate_leader_socket(self) -> None:
        kwargs = lra_t1._live_grok_kwargs()
        self.assertEqual(kwargs["provider"], "grok")
        self.assertFalse(kwargs["allow_local_fallback"])
        self.assertGreaterEqual(int(kwargs["grok_max_turns"]), 4)
        cmd = kwargs.get("grok_cli_cmd") or []
        self.assertIn("--leader-socket", cmd)
        socket = cmd[cmd.index("--leader-socket") + 1]
        self.assertIn("leader-lra-track1.sock", socket)
        self.assertNotEqual(socket, str(Path.home() / ".grok" / "leader.sock"))

    def test_generate_grok_fixture_is_two_call_capped(self) -> None:
        ledger = lra_t1.ProblemLedger(name="Core.InitsUpdatesComm#grok-few-shot")
        factory = lra_t1.FixtureGrok(text="  simp_all")
        text, identity, line = lra_t1.generate_grok(
            "few-shot",
            ledger,
            max_new_tokens=32,
            timeout=1.0,
            generate=factory,
            get_trace=lra_t1.fixture_trace,
            fixture=True,
        )
        self.assertEqual(text, "  simp_all")
        self.assertFalse(identity.fallback_used)
        self.assertIn(identity.resolved_provider, lra_t1.ALLOWED_RESOLVED_PROVIDERS)
        self.assertEqual(ledger.grok_calls, 1)
        self.assertLess(ledger.spent_usd, 3.0)
        lra_t1.generate_grok(
            "repair",
            ledger,
            max_new_tokens=32,
            timeout=1.0,
            generate=factory,
            get_trace=lra_t1.fixture_trace,
            fixture=True,
        )
        with self.assertRaises(lra_t1.Track1LedgerError) as raised:
            lra_t1.generate_grok(
                "third",
                ledger,
                max_new_tokens=32,
                timeout=1.0,
                generate=factory,
                get_trace=lra_t1.fixture_trace,
                fixture=True,
            )
        self.assertIn("max_grok_calls", str(raised.exception))
        self.assertEqual(ledger.grok_calls, 2)
        self.assertEqual(len(factory.calls), 2)
        self.assertTrue(line.kind == "grok")

    def test_grok_few_shot_flag_refuses_leanstral_combo(self) -> None:
        import mca_mask_replace as mask

        with self.assertRaises(SystemExit):
            mask.main(["--live", "--few-shot", "--grok-few-shot", "--names", "Core.InitsUpdatesComm"])


if __name__ == "__main__":
    unittest.main()
