#!/usr/bin/env python3
"""Accounting tests for AF-007. Compact recipes, not bulk golden envelopes.

These tests check denominator retention, result-kind distinctions, measured-row
admission, and deterministic table regeneration.  They do not run models,
compilers, or native checkers, and they do not treat unrun arms as zeros.
"""
from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import run_benchmark as harness  # noqa: E402


NATIVE_RECEIPT = "a" * 64
ELIGIBLE_IDS = [f"S{index:02d}" for index in range(12)]


def _phase(status: str, score: float | None = None) -> dict:
    return {"status": status, "score": score}


def _native(source_id: str, arm: str = "A") -> dict:
    return harness.make_record(
        source_id=source_id,
        experiment_arm=arm,
        execution_status="measured",
        result_kind="native_checked_proof",
        parse=_phase("success"),
        elaboration=_phase("success"),
        independent_gold_present=True,
        all_facet_match=True,
        ambiguity_status="success",
        source_maps=_phase("success"),
        forward=_phase("success", 1.0),
        cycle=_phase("success", 1.0),
        final=_phase("success", 1.0),
        consistency=_phase("success"),
        useful=True,
        checker_class="native",
        receipt_sha256=NATIVE_RECEIPT,
        checker="lean-kernel-receipt",
        compiler="intent-formalization-compiler/v1",
        elapsed_seconds=1.5,
    )


def _solver(source_id: str, arm: str = "A") -> dict:
    return harness.make_record(
        source_id=source_id,
        experiment_arm=arm,
        execution_status="measured",
        result_kind="solver_local_result",
        parse=_phase("success"),
        elaboration=_phase("success"),
        checker_class="solver_local",
        tool="z3-solver-local",
        elapsed_seconds=0.4,
        notes="solver-local SAT/UNSAT is not a native checked proof",
    )


def _countermodel(source_id: str, arm: str = "A") -> dict:
    return harness.make_record(
        source_id=source_id,
        experiment_arm=arm,
        execution_status="measured",
        result_kind="countermodel",
        parse=_phase("success"),
        elaboration=_phase("success"),
        checker_class="solver_local",
        tool="finite-countermodel",
        elapsed_seconds=0.2,
    )


def _bounded(source_id: str, arm: str = "A") -> dict:
    return harness.make_record(
        source_id=source_id,
        experiment_arm=arm,
        execution_status="measured",
        result_kind="bounded_observation",
        parse=_phase("success"),
        elaboration=_phase("success"),
        elapsed_seconds=0.1,
    )


def _status_record(source_id: str, status: str, kind: str, arm: str = "A", **kwargs) -> dict:
    return harness.make_record(
        source_id=source_id,
        experiment_arm=arm,
        execution_status=status,
        result_kind=kind,
        **kwargs,
    )


def mixed_population(arm: str = "A") -> list[dict]:
    """Twelve eligible sources covering every required status and result kind."""
    return [
        _native(ELIGIBLE_IDS[0], arm),
        _solver(ELIGIBLE_IDS[1], arm),
        _countermodel(ELIGIBLE_IDS[2], arm),
        _bounded(ELIGIBLE_IDS[3], arm),
        _status_record(ELIGIBLE_IDS[4], "failure", "failure", arm),
        _status_record(ELIGIBLE_IDS[5], "no_run", "no_run", arm),
        _status_record(ELIGIBLE_IDS[6], "unavailable", "no_run", arm),
        _status_record(ELIGIBLE_IDS[7], "unsupported", "failure", arm),
        _status_record(ELIGIBLE_IDS[8], "abstained", "failure", arm),
        _status_record(ELIGIBLE_IDS[9], "timeout", "failure", arm),
        _status_record(ELIGIBLE_IDS[10], "invalid", "failure", arm),
        _status_record(ELIGIBLE_IDS[11], "partial", "failure", arm),
    ]


def recipe_for(records: list[dict], *, arm: str = "A", count: int | None = None,
               ids: list[str] | None = None) -> dict:
    if count is None:
        count = len(ids) if ids is not None else len(records)
    return {
        "schema": harness.RECIPE_SCHEMA,
        "eligible_basis": {
            "split": "final_test",
            "field": "natural_source_units",
            "count": count,
        },
        "arms": [arm],
        "default_execution_status": "no_run",
        "default_result_kind": "no_run",
        "eligible_source_ids": ids if ids is not None else [record["source_id"] for record in records],
        "records": records,
    }


class SchemaContractTests(unittest.TestCase):
    def test_schema_distinguishes_six_result_kinds(self) -> None:
        schema = harness.load_schema_contract()
        metrics = harness.load_metrics_contract()
        self.assertEqual(tuple(schema["result_kinds"]), harness.RESULT_KINDS)
        self.assertEqual(
            list(schema["result_kinds"]),
            [
                "native_checked_proof",
                "solver_local_result",
                "countermodel",
                "bounded_observation",
                "failure",
                "no_run",
            ],
        )
        self.assertEqual(set(schema["blocked_from_measured_table_rows"]), {"invalid", "no_run", "fixture"})
        self.assertEqual(set(schema["coverage_denominator_statuses"]), set(harness.EXECUTION_STATUSES))
        self.assertEqual(tuple(metrics["result_kinds"]), harness.RESULT_KINDS)
        self.assertTrue(metrics["admission_policy"]["solver_local_is_not_native_checked_proof"])

    def test_kind_status_matrix_rejects_collisions(self) -> None:
        with self.assertRaises(harness.AccountingError):
            harness.validate_record(_status_record("X", "measured", "no_run"))
        with self.assertRaises(harness.AccountingError):
            harness.validate_record(_status_record("X", "no_run", "native_checked_proof",
                                                   checker_class="native", receipt_sha256=NATIVE_RECEIPT,
                                                   checker="lean"))
        with self.assertRaises(harness.AccountingError):
            rec = _solver("X")
            rec["proof"]["checker_class"] = "native"
            rec["artifacts"]["raw_sha256"] = harness.artifact_digest_for_record(rec)
            harness.validate_record(rec)


class DenominatorTests(unittest.TestCase):
    def test_every_eligible_status_remains_in_denominator(self) -> None:
        records = mixed_population()
        tables = harness.regenerate_tables(recipe_for(records))
        arm = tables["arms"]["A"]
        self.assertEqual(arm["eligible"], 12)
        self.assertEqual(sum(arm["coverage_statuses"].values()), 12)
        for status in ("unavailable", "unsupported", "abstained", "timeout", "invalid", "no_run", "failure"):
            self.assertGreaterEqual(arm["coverage_statuses"][status], 1, status)
        self.assertEqual(arm["metrics"]["timeout_rate"]["numerator"], 1)
        self.assertEqual(arm["metrics"]["unavailable_rate"]["numerator"], 1)
        self.assertEqual(arm["metrics"]["unsupported_rate"]["numerator"], 1)
        self.assertEqual(arm["metrics"]["abstention_rate"]["numerator"], 1)
        self.assertEqual(arm["metrics"]["no_run_rate"]["numerator"], 1)
        self.assertTrue(tables["denominator_checks"]["A"]["pass"])
        self.assertEqual(tables["denominator_checks"]["A"]["dropped_eligible"], 0)

    def test_dropping_timeout_from_denominator_fails(self) -> None:
        tables = harness.regenerate_tables(recipe_for(mixed_population()))
        mutated = copy.deepcopy(tables["arms"]["A"])
        mutated["coverage_statuses"]["timeout"] = 0
        check = harness.denominator_check(mutated)
        self.assertFalse(check["pass"])
        self.assertEqual(check["dropped_eligible"], 1)

    def test_reducing_eligible_count_below_frozen_ids_fails(self) -> None:
        records = mixed_population()
        timeout = [record for record in records if record["execution_status"] != "timeout"]
        with self.assertRaises(harness.AccountingError):
            harness.regenerate_tables(recipe_for(timeout, ids=ELIGIBLE_IDS, count=11))


class AdmissionTests(unittest.TestCase):
    def test_invalid_no_run_and_fixture_are_not_measured_rows(self) -> None:
        native = _native("S00")
        invalid = _status_record("S01", "invalid", "failure")
        no_run = _status_record("S02", "no_run", "no_run")
        fixture = harness.make_record(
            source_id="FIX",
            experiment_arm="A",
            execution_status="measured",
            result_kind="bounded_observation",
            eligible=True,
            fixture=True,
            constructed_control=True,
            split="constructed_control",
            parse=_phase("success"),
            forward=_phase("success", 1.0),
            cycle=_phase("success", 1.0),
            final=_phase("success", 1.0),
        )
        self.assertTrue(harness.admission_decision(native)["measured_table_row"])
        for record in (invalid, no_run, fixture):
            decision = harness.admission_decision(record)
            self.assertFalse(decision["measured_table_row"], record["source_id"])
        tables = harness.regenerate_tables(recipe_for(
            [native, invalid, no_run],
            ids=["S00", "S01", "S02"],
        ))
        arm = tables["arms"]["A"]
        self.assertEqual(arm["admitted_measured_rows"], 1)
        self.assertEqual(arm["admitted_record_ids"], [native["record_id"]])
        self.assertGreaterEqual(arm["rejected_from_measured_table"].get("invalid", 0), 1)
        self.assertGreaterEqual(arm["rejected_from_measured_table"].get("no_run", 0), 1)
        fixture_tables = harness.regenerate_tables({
            "schema": harness.RECIPE_SCHEMA,
            "eligible_basis": {"split": "final_test", "field": "natural_source_units", "count": 1},
            "arms": ["A"],
            "default_execution_status": "no_run",
            "default_result_kind": "no_run",
            "eligible_source_ids": ["S00"],
            "records": [fixture],
        })
        self.assertEqual(fixture_tables["arms"]["A"]["admitted_measured_rows"], 0)
        self.assertEqual(fixture_tables["arms"]["A"]["fixture_records"], 1)
        self.assertEqual(fixture_tables["arms"]["A"]["coverage_statuses"]["no_run"], 1)

    def test_self_asserted_admission_is_rejected(self) -> None:
        record = _native("S00")
        record["admission"] = {"measured_table_row": True}
        with self.assertRaises(harness.AccountingError):
            harness.validate_record(record)

    def test_no_run_is_not_a_measured_zero(self) -> None:
        tables = harness.regenerate_tables(recipe_for(
            [_status_record("S00", "no_run", "no_run")],
            ids=["S00"],
        ))
        metric = tables["arms"]["A"]["metrics"]["native_checked_useful_proof_coverage"]
        self.assertEqual(metric["status"], "unrun")
        self.assertIsNone(metric["value"])
        self.assertIsNone(metric["numerator"])
        self.assertEqual(metric["denominator"], 1)


class KindSeparationTests(unittest.TestCase):
    def test_solver_local_does_not_count_as_native_checked_proof(self) -> None:
        records = [_native("S00"), _solver("S01"), _countermodel("S02"), _bounded("S03")]
        tables = harness.regenerate_tables(recipe_for(records, ids=["S00", "S01", "S02", "S03"]))
        arm = tables["arms"]["A"]
        self.assertEqual(arm["result_kinds"]["native_checked_proof"], 1)
        self.assertEqual(arm["result_kinds"]["solver_local_result"], 1)
        self.assertEqual(arm["result_kinds"]["countermodel"], 1)
        self.assertEqual(arm["result_kinds"]["bounded_observation"], 1)
        self.assertEqual(arm["metrics"]["native_checked_useful_proof_coverage"]["numerator"], 1)
        self.assertEqual(arm["metrics"]["native_checked_useful_proof_coverage"]["denominator"], 4)
        self.assertEqual(arm["metrics"]["solver_local_rate"]["numerator"], 1)
        self.assertEqual(arm["metrics"]["countermodel_rate"]["numerator"], 1)
        self.assertEqual(arm["metrics"]["bounded_observation_rate"]["numerator"], 1)
        self.assertEqual(arm["admitted_measured_rows"], 4)

    def test_timeout_attempt_is_measured_zero_not_unrun(self) -> None:
        records = [_status_record(ELIGIBLE_IDS[0], "timeout", "failure")]
        tables = harness.regenerate_tables(recipe_for(records, ids=[ELIGIBLE_IDS[0]]))
        metric = tables["arms"]["A"]["metrics"]["native_checked_useful_proof_coverage"]
        self.assertEqual(metric["status"], "measured")
        self.assertEqual(metric["numerator"], 0)
        self.assertEqual(metric["value"], 0.0)
        self.assertEqual(tables["arms"]["A"]["admitted_measured_rows"], 0)


class RegenerationTests(unittest.TestCase):
    def test_tables_regenerate_deterministically_with_hashes(self) -> None:
        recipe = recipe_for(mixed_population())
        first = harness.regenerate_tables(recipe)
        second = harness.regenerate_tables(recipe)
        self.assertEqual(harness.canonical_dumps(first), harness.canonical_dumps(second))
        self.assertEqual(first["tables_sha256"], second["tables_sha256"])
        self.assertRegex(first["generated_from"]["metrics_sha256"], r"^[0-9a-f]{64}$")
        self.assertRegex(first["generated_from"]["schema_sha256"], r"^[0-9a-f]{64}$")
        self.assertRegex(first["generated_from"]["records_sha256"], r"^[0-9a-f]{64}$")
        self.assertTrue(all(check["pass"] for check in first["denominator_checks"].values()))
        harness.assert_tables_deterministic(recipe, first)

    def test_artifact_hash_tamper_is_rejected(self) -> None:
        record = _native("S00")
        record["artifacts"]["raw_sha256"] = "b" * 64
        with self.assertRaises(harness.AccountingError):
            harness.validate_record(record)


class AdapterAndFrozenPopulationTests(unittest.TestCase):
    def test_roundtrip_fixture_adapter_cannot_enter_measured_table(self) -> None:
        adapted = harness.adapt_semantic_logic_roundtrip(
            {
                "case_id": "pilot-01",
                "parse_ok": True,
                "scores": {"forward": 1.0, "cycle": 1.0, "final": 1.0},
            },
            experiment_arm="B",
            fixture=True,
        )
        harness.validate_record(adapted)
        self.assertTrue(adapted["fixture"])
        self.assertFalse(adapted["eligible"])
        self.assertFalse(harness.admission_decision(adapted)["measured_table_row"])
        self.assertEqual(adapted["reconstruction"]["forward"]["status"], "success")
        self.assertEqual(adapted["reconstruction"]["cycle"]["status"], "success")
        self.assertEqual(adapted["reconstruction"]["final"]["status"], "success")

    def test_composition_adapter_keeps_solver_local_out_of_native_proof(self) -> None:
        adapted = harness.adapt_semantic_roundtrip_compositions(
            {"case_id": "comp-01", "bridge_transfer": True, "composition_consistency": True},
            experiment_arm="D",
            fixture=False,
        )
        harness.validate_record(adapted)
        self.assertEqual(adapted["result_kind"], "solver_local_result")
        tables = harness.regenerate_tables(recipe_for([adapted], arm="D", ids=["comp-01"]))
        self.assertEqual(tables["arms"]["D"]["metrics"]["native_checked_useful_proof_coverage"]["numerator"], 0)
        self.assertEqual(tables["arms"]["D"]["metrics"]["solver_local_rate"]["numerator"], 1)

    def test_frozen_unrun_population_keeps_1913_and_zero_measured_rows(self) -> None:
        recipe = harness.frozen_unrun_recipe()
        self.assertEqual(recipe["eligible_basis"]["count"], 1913)
        self.assertFalse(recipe["eligible_basis"]["private_final_ids_disclosed"])
        tables = harness.regenerate_tables(recipe)
        self.assertEqual(len(tables["arms"]), 11)
        for arm, body in tables["arms"].items():
            self.assertEqual(body["eligible"], 1913, arm)
            self.assertEqual(body["coverage_statuses"]["no_run"], 1913, arm)
            self.assertEqual(body["result_kinds"]["no_run"], 1913, arm)
            self.assertEqual(body["admitted_measured_rows"], 0, arm)
            native = body["metrics"]["native_checked_useful_proof_coverage"]
            self.assertEqual(native["status"], "unrun", arm)
            self.assertIsNone(native["value"], arm)
            self.assertEqual(native["denominator"], 1913, arm)
            self.assertEqual(body["metrics"]["no_run_rate"]["numerator"], 1913, arm)
            self.assertTrue(tables["denominator_checks"][arm]["pass"], arm)
        self.assertEqual(
            recipe["excluded_populations"]["synthetic_fixture"],
            "excluded_synthetic_fixture",
        )


class RemainderAndGoldTests(unittest.TestCase):
    def test_explicit_subset_remainder_stays_in_denominator(self) -> None:
        records = [_native("S00"), _status_record("S01", "timeout", "failure")]
        recipe = recipe_for(records, ids=ELIGIBLE_IDS, count=12)
        tables = harness.regenerate_tables(recipe)
        arm = tables["arms"]["A"]
        self.assertEqual(arm["eligible"], 12)
        self.assertEqual(arm["remainder"], 10)
        self.assertEqual(arm["coverage_statuses"]["no_run"], 10)
        self.assertEqual(arm["coverage_statuses"]["timeout"], 1)
        self.assertEqual(arm["coverage_statuses"]["measured"], 1)
        self.assertEqual(arm["admitted_measured_rows"], 1)
        self.assertEqual(sum(arm["coverage_statuses"].values()), 12)

    def test_fidelity_without_gold_is_unmeasured_not_zero(self) -> None:
        record = _bounded("S00")
        tables = harness.regenerate_tables(recipe_for([record], ids=["S00"]))
        metric = tables["arms"]["A"]["metrics"]["all_facet_source_fidelity"]
        self.assertEqual(metric["status"], "unmeasured_pending_independent_gold")
        self.assertIsNone(metric["value"])


class IndependentAccountingRegressionTests(unittest.TestCase):
    def test_gold_on_one_row_does_not_license_another_rows_match(self):
        reviewed = harness.make_record(source_id='reviewed', experiment_arm='A',
            execution_status='measured', result_kind='bounded_observation',
            independent_gold_present=True, all_facet_match=False)
        unreviewed = harness.make_record(source_id='unreviewed', experiment_arm='A',
            execution_status='measured', result_kind='bounded_observation',
            independent_gold_present=False, all_facet_match=True)
        arm = harness.regenerate_tables(recipe_for([reviewed, unreviewed]))['arms']['A']
        metric = arm['metrics']['all_facet_source_fidelity']
        self.assertIsNone(metric['value'])
        self.assertIsNone(metric['numerator'])
        self.assertEqual(metric['verified_success_lower_bound']['numerator'], 0)
        self.assertEqual(metric['denominator'], 2)
        reviewed['source_facets']['all_facet_match'] = True
        reviewed['artifacts']['raw_sha256'] = harness.artifact_digest_for_record(reviewed)
        arm = harness.regenerate_tables(recipe_for([reviewed, unreviewed]))['arms']['A']
        metric = arm['metrics']['all_facet_source_fidelity']
        self.assertIsNone(metric['value'])
        self.assertEqual(metric['verified_success_lower_bound']['numerator'], 1)
        self.assertEqual(metric['adjudication_coverage']['numerator'], 1)

    def test_control_and_other_split_cannot_enter_natural_final_population(self):
        for split, control in [('constructed_control', True), ('selection', False),
                               ('train', False), ('fixed_canary', False), ('final_test', True)]:
            with self.subTest(split=split, control=control):
                record = harness.make_record(source_id='C', experiment_arm='A',
                    execution_status='measured', result_kind='bounded_observation',
                    split=split, constructed_control=control)
                with self.assertRaises(harness.AccountingError):
                    harness.regenerate_tables(recipe_for([record]))

    def test_separate_control_population_still_supports_accounting(self):
        record = harness.make_record(source_id='C', experiment_arm='A',
            execution_status='measured', result_kind='bounded_observation',
            split='constructed_control', constructed_control=True)
        recipe = recipe_for([record])
        recipe['eligible_basis'].update(split='constructed_control', field='constructed_control_units')
        arm = harness.regenerate_tables(recipe)['arms']['A']
        self.assertEqual(arm['admitted_measured_rows'], 1)
        self.assertEqual(arm['eligible'], 1)

    def test_wall_time_does_not_create_cpu_measurement(self):
        record = harness.make_record(source_id='wall', experiment_arm='A',
            execution_status='measured', result_kind='bounded_observation', elapsed_seconds=12.5)
        self.assertEqual(record['cost']['elapsed_seconds'], 12.5)
        self.assertIsNone(record['cost']['cpu_seconds'])
        explicit = harness.make_record(source_id='cpu', experiment_arm='A',
            execution_status='measured', result_kind='bounded_observation',
            elapsed_seconds=12.5, cpu_seconds=0.2)
        harness.validate_record(explicit)
        self.assertEqual(explicit['cost']['cpu_seconds'], 0.2)

    def test_explicit_bridge_false_is_retained_and_does_not_fall_through_alias(self):
        for extra in [{}, {'transfer':True}, {'transfer':False}]:
            with self.subTest(extra=extra):
                record = harness.adapt_semantic_roundtrip_compositions(
                    {'case_id':'bridge', 'bridge_transfer':False, **extra},
                    experiment_arm='A', fixture=False)
                harness.validate_record(record)
                self.assertEqual(record['execution_status'], 'failure')
                self.assertEqual(record['result_kind'], 'failure')
                self.assertTrue(record['proof']['false_transfer'])
                self.assertFalse(harness.admission_decision(record)['measured_table_row'])

    def test_observed_false_transfer_failure_counts_without_success_admission(self):
        records = [harness.adapt_semantic_roundtrip_compositions(
            {'case_id':'bridge', 'transfer':False}, experiment_arm='A', fixture=False)]
        for index, (status, kind) in enumerate([('invalid','failure'), ('no_run','no_run')]):
            records.append(harness.make_record(source_id=f'excluded{index}', experiment_arm='A',
                execution_status=status, result_kind=kind, false_transfer=True))
        recipe = recipe_for(records)
        fixture = harness.make_record(source_id='fixture', experiment_arm='A',
            execution_status='failure', result_kind='failure', false_transfer=True, fixture=True)
        recipe['records'].append(fixture)
        arm = harness.regenerate_tables(recipe)['arms']['A']
        self.assertEqual(arm['metrics']['false_transfer_rate']['numerator'], 1)
        self.assertEqual(arm['metrics']['false_transfer_rate']['denominator'], 3)
        self.assertEqual(arm['admitted_measured_rows'], 0)
        self.assertEqual(arm['fixture_records'], 1)

    def test_nonfinite_and_negative_costs_are_rejected(self):
        for value in [float('nan'), float('inf'), float('-inf'), -0.01]:
            with self.subTest(value=value):
                with self.assertRaises(harness.AccountingError):
                    record = harness.make_record(source_id='bad-cost', experiment_arm='A',
                        execution_status='measured', result_kind='bounded_observation',
                        elapsed_seconds=value)
                    harness.validate_record(record)

    def test_nonfinite_phase_scores_and_canonical_json_are_rejected(self):
        for value in [float('nan'), float('inf'), float('-inf')]:
            with self.subTest(value=value):
                with self.assertRaises(harness.AccountingError):
                    harness.canonical_dumps({'value':value})
                with self.assertRaises(harness.AccountingError):
                    record = harness.make_record(source_id='bad-score', experiment_arm='A',
                        execution_status='measured', result_kind='bounded_observation',
                        parse={'status':'success','score':value})
                    harness.validate_record(record)


class PopulationAdjudicationRegressionTests(unittest.TestCase):
    def record(self, name, gold, match):
        return harness.make_record(source_id=name, experiment_arm='A', execution_status='measured',
            result_kind='bounded_observation', independent_gold_present=gold, all_facet_match=match)

    def test_partial_gold_never_becomes_primary_measured_fidelity(self):
        rows = [self.record('gold', True, True), self.record('unknown', False, None)]
        metric = harness.regenerate_tables(recipe_for(rows))['arms']['A']['metrics']['all_facet_source_fidelity']
        self.assertIsNone(metric['value'])
        self.assertIsNone(metric['numerator'])
        self.assertNotEqual(metric['status'], 'measured')
        self.assertEqual(metric['denominator'], 2)
        self.assertEqual(metric['missing_adjudicated_units'], 1)
        self.assertEqual(metric['adjudication_coverage']['value'], 0.5)
        self.assertEqual(metric['verified_success_lower_bound']['value'], 0.5)
        self.assertTrue(metric['verified_success_lower_bound']['not_a_primary_estimate'])

    def test_gold_present_without_judgment_remains_pending(self):
        rows = [self.record('judged', True, True), self.record('no-judgment', True, None)]
        metric = harness.regenerate_tables(recipe_for(rows))['arms']['A']['metrics']['all_facet_source_fidelity']
        self.assertIsNone(metric['value'])
        self.assertEqual(metric['missing_adjudicated_units'], 1)
        self.assertEqual(metric['adjudication_coverage']['numerator'], 1)

    def test_complete_independent_judgments_enable_primary_fidelity(self):
        rows = [self.record('match', True, True), self.record('mismatch', True, False)]
        metric = harness.regenerate_tables(recipe_for(rows))['arms']['A']['metrics']['all_facet_source_fidelity']
        self.assertEqual(metric['status'], 'measured')
        self.assertEqual(metric['numerator'], 1)
        self.assertEqual(metric['denominator'], 2)
        self.assertEqual(metric['value'], 0.5)
        self.assertEqual(metric['adjudication_coverage']['value'], 1.0)
        self.assertEqual(metric['missing_adjudicated_units'], 0)

    def test_no_gold_has_zero_review_coverage_but_no_primary_value(self):
        rows = [self.record('claim-only', False, True), self.record('unknown', False, None)]
        metric = harness.regenerate_tables(recipe_for(rows))['arms']['A']['metrics']['all_facet_source_fidelity']
        self.assertIsNone(metric['value'])
        self.assertIsNone(metric['numerator'])
        self.assertEqual(metric['adjudication_coverage']['numerator'], 0)
        self.assertEqual(metric['verified_success_lower_bound']['numerator'], 0)
        self.assertEqual(metric['denominator'], 2)

    def test_unrepresented_eligible_unit_is_still_missing_judgment(self):
        recipe = recipe_for([self.record('known', True, True)], ids=['known','unrun'], count=2)
        metric = harness.regenerate_tables(recipe)['arms']['A']['metrics']['all_facet_source_fidelity']
        self.assertIsNone(metric['value'])
        self.assertEqual(metric['denominator'], 2)
        self.assertEqual(metric['missing_adjudicated_units'], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
