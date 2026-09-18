#!/usr/bin/env python3
"""VAE round-trip: Jev is the batch loss; lake admits Lean."""

from __future__ import annotations

import random
import unittest

import nca_autoencoder as lra_ae
import nca_program as lra_prog
import nca_rankers as lra_rank


class NcaAutoencoderTests(unittest.TestCase):
    def test_cosine_milles_identity_and_orthogonal(self) -> None:
        v = [1000, 0, 0, 0]
        self.assertEqual(lra_ae.cosine_milles(v, v), 1000)
        self.assertEqual(lra_ae.cosine_milles(v, [0, 1000, 0, 0]), 0)
        self.assertEqual(lra_ae.ce_milles(v, v), 0)

    def test_jev_picks_shortest_among_variations(self) -> None:
        def jev_fn(payload):
            rows = list(payload.get("variations") or [])
            best = min(rows, key=lambda row: int(row.get("n_tokens") or 10**9))
            return {
                "choice": best["id"],
                "scores": {row["id"]: 1000 - int(row.get("n_tokens") or 0) for row in rows},
                "noul": 0.1,
            }

        mem: dict = {"nca": {}}
        first = lra_ae.teach_roundtrip(
            mem,
            "hello world theorem True",
            problem="P",
            jev_fn=jev_fn,
            rng=random.Random(0),
            n_variations=4,
        )
        self.assertTrue(first["ok"])
        self.assertTrue(first["used_jev"])
        self.assertEqual(first["loss"], "jev_batch")
        self.assertGreaterEqual(len(mem["nca"]["autoencoder"]["batch"]), 1)
        second = lra_ae.teach_roundtrip(
            mem,
            "hello world theorem True again",
            problem="P",
            jev_fn=jev_fn,
            rng=random.Random(1),
            n_variations=4,
        )
        self.assertEqual(second["n_previous"], 1)
        self.assertLessEqual(int(second["n_tokens"]), int(first["n_tokens"]) + 20)

    def test_lake_rejects_keep_next_jev_ok(self) -> None:
        def jev_fn(payload):
            rows = list(payload.get("variations") or [])
            return {
                "choice": rows[0]["id"],
                "scores": {row["id"]: i for i, row in enumerate(reversed(rows))},
                "noul": 0.2,
            }

        n = {"i": 0}

        def compile_fn(lean, **_k):
            n["i"] += 1
            return {"theorem_ok": n["i"] >= 2, "token_count": 5, "errors": []}

        mem: dict = {"nca": {}}
        out = lra_ae.teach_roundtrip(
            mem,
            "case intro simp",
            jev_fn=jev_fn,
            compile_fn=compile_fn,
            rng=random.Random(0),
            n_variations=3,
        )
        self.assertTrue(out["lake_ok"])

    def test_datasets_cosine_is_diagnostic_not_gold(self) -> None:
        row = lra_ae.roundtrip_once("exact True", rng=random.Random(0))
        self.assertIn("datasets", row)
        self.assertFalse((row["datasets"] or {}).get("gold"))

    def test_skill_call_vae_does_not_rewrite_tactics(self) -> None:
        body = "  exact Hin\n"
        mem = {
            "nca": {
                "grid": {},
                "program_state": {
                    "ops": [
                        {"op": "CALL", "ptr": "ptr://skill/port_autoencoder"},
                        {"op": "CALL", "ptr": "ptr://skill/port_vae"},
                        {"op": "KEEP"},
                    ]
                },
            }
        }
        executed = lra_prog.execute_program_ops(mem, tactics=body, problem="P")
        self.assertEqual(executed.get("tactics"), body)
        self.assertTrue(any("autoencoder" in str(op.get("ptr") or "") and op.get("ok") for op in executed["ran"]))
        self.assertTrue(any("vae" in str(op.get("ptr") or "") and op.get("ok") for op in executed["ran"]))
        self.assertFalse(executed.get("called_docker0"))

    def test_call_ranker_dispatches_autoencoder(self) -> None:
        mem: dict = {"nca": {}}
        out = lra_rank.call_ranker("port_vae", memory=mem, tactics="  trivial\n", problem="P")
        self.assertTrue(out["ok"])
        self.assertEqual(out["kind"], "port_vae")
        self.assertFalse(out["writes_lean"])
        self.assertTrue(out["integer"])


if __name__ == "__main__":
    unittest.main()
