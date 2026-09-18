#!/usr/bin/env python3
"""Contract tests for RF / Bayes-time / MCMC NCA ranking skills."""

from __future__ import annotations

import random
import unittest

import nca_program as lra_prog
import nca_rankers as lra_rank


class NcaRankerTests(unittest.TestCase):
    def test_bayes_observe_raises_mean_and_decays(self) -> None:
        mem: dict = {"nca": {}}
        first = lra_rank.observe_bayes(mem, "port_trailing_tuple_comma", ok=True)
        self.assertGreater(first["mean"], 0.5)
        second = lra_rank.observe_bayes(mem, "port_trailing_tuple_comma", ok=True)
        self.assertGreater(second["mean"], first["mean"])
        fail = lra_rank.observe_bayes(mem, "port_trailing_tuple_comma", ok=False)
        self.assertLess(fail["mean"], second["mean"])
        self.assertEqual(fail["n"], 3)

    def test_sync_bayes_counts_and_grid(self) -> None:
        mem = {
            "successes": [{"kind": "port_trailing_tuple_comma"}, {"kind": "port_trailing_tuple_comma"}],
            "failures": [{"kind": "port_hoist_repeated_simp"}],
            "nca": {"grid": {}},
        }
        synced = lra_rank.sync_bayes_from_memory(mem)
        self.assertTrue(synced["ok"])
        comma = lra_rank.posterior(mem, "trailing_tuple_comma")
        hoist = lra_rank.posterior(mem, "hoist_repeated_simp")
        self.assertGreater(comma["mean"], hoist["mean"])
        n_cells = lra_rank.apply_bayes_to_grid(mem)
        self.assertGreaterEqual(n_cells, 2)
        self.assertIn("ptr://skill/port_trailing_tuple_comma", mem["nca"]["grid"])

    def test_random_forest_ranks_winner_above_loser(self) -> None:
        mem = {
            "successes": [
                {"kind": "port_trailing_tuple_comma", "tokens": 10, "name": "A"},
                {"kind": "port_trailing_tuple_comma", "tokens": 11, "name": "B"},
                {"kind": "port_trailing_tuple_comma", "tokens": 9, "name": "C"},
            ],
            "failures": [
                {"kind": "port_hoist_repeated_simp", "tokens": 40, "name": "A"},
                {"kind": "port_hoist_repeated_simp", "tokens": 41, "name": "B"},
                {"kind": "port_hoist_repeated_simp", "tokens": 39, "name": "C"},
            ],
            "nca": {},
        }
        trained = lra_rank.train_random_forest(mem, rng=random.Random(0))
        self.assertGreaterEqual(trained["n_trees"], 1)
        drafts = [
            {"kind": "port_hoist_repeated_simp", "token_count": 40},
            {"kind": "port_trailing_tuple_comma", "token_count": 10},
        ]
        ranked = lra_rank.rank_drafts_forest(drafts, memory=mem, name="A")
        self.assertEqual(ranked[0]["kind"], "port_trailing_tuple_comma")

    def test_mcmc_accepts_downhill_and_hard_rejects(self) -> None:
        rng = random.Random(0)

        def energy(state: int) -> float:
            return float(abs(state - 3))

        def propose(state: int, rng_local: random.Random) -> int:
            return state + rng_local.choice((-1, 1))

        ran = lra_rank.metropolis_hastings(
            0, propose=propose, energy=energy, rng=rng, steps=40, temperature=0.2
        )
        self.assertTrue(ran["ok"])
        self.assertLessEqual(int(ran["best_energy"]), 2)
        blocked = lra_rank.metropolis_hastings(
            0,
            propose=lambda s, _r: s + 1,
            energy=energy,
            accept=lambda s: False,
            rng=random.Random(1),
            steps=5,
        )
        self.assertEqual(blocked["n_accept"], 0)
        self.assertEqual(blocked["state"], 0)

    def test_mcmc_pipeline_writes_bias_not_lean(self) -> None:
        mem = {
            "successes": [{"kind": "port_trailing_tuple_comma"}] * 4,
            "failures": [{"kind": "port_grind_only_to_grind"}] * 4,
            "nca": {},
        }
        lra_rank.sync_bayes_from_memory(mem)
        ran = lra_rank.mcmc_pipeline_order(mem, rng=random.Random(0), steps=12)
        self.assertTrue(ran["ok"])
        self.assertFalse(ran["writes_lean"])
        self.assertIn("trailing_tuple_comma", ran.get("stems") or [])
        self.assertEqual(mem["nca"]["pipeline_bias"], ran["stems"])

    def test_skill_call_rankers_do_not_write_lean(self) -> None:
        mem = {
            "nca": {
                "grid": {},
                "program_state": {
                    "ops": [
                        {"op": "CALL", "ptr": "ptr://skill/port_bayes_time"},
                        {"op": "CALL", "ptr": "ptr://skill/port_random_forest"},
                        {"op": "CALL", "ptr": "ptr://skill/port_mcmc"},
                        {"op": "KEEP"},
                    ]
                },
            },
            "successes": [{"kind": "port_trailing_tuple_comma", "tokens": 8}] * 3,
            "failures": [{"kind": "port_hoist_repeated_simp", "tokens": 30}] * 3,
        }
        body = "  exact ⟨a, b,⟩\n"
        executed = lra_prog.execute_program_ops(mem, tactics=body, problem="P")
        self.assertEqual(body, executed.get("tactics") or body)
        kinds = [str((op.get("detail_ok"), op.get("ptr"))) for op in executed.get("ran") or []]
        self.assertTrue(any("bayes_time" in str(op.get("ptr") or "") and op.get("ok") for op in executed["ran"]))
        self.assertTrue(any("random_forest" in str(op.get("ptr") or "") and op.get("ok") for op in executed["ran"]))
        self.assertTrue(any("mcmc" in str(op.get("ptr") or "") and op.get("ok") for op in executed["ran"]))
        self.assertFalse(executed.get("called_docker0"))
        self.assertTrue(kinds)


if __name__ == "__main__":
    unittest.main()
