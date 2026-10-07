"""Independent descriptor mutations with synthetic handles; no neural calls."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "independent_dual_fixture", ROOT / "runtime/tests/test_dual_bank_runtime.py"
)
FIXTURE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FIXTURE)


class IndependentDescriptorFailures(unittest.TestCase):
    def setUp(self):
        self.case = FIXTURE.DualInterfaceContracts()
        self.case.setUp()

    def refused(self, field, value):
        changed = deepcopy(self.case.descriptor)
        changed[field] = value
        FIXTURE.seal(changed, "bank_sha256")
        with self.assertRaises((ValueError, TypeError, KeyError)):
            self.case.dual.estimate_training_work_bytes(changed, max_optimizer_steps=170)
        with self.assertRaises((ValueError, TypeError, KeyError)):
            self.case.dual.prepare_tensor_cache(None, self.case.model, changed,
                codec={}, input_transform={}, seed=1729, deadline=999,
                max_optimizer_steps=170)

    def test_rehashed_qualification_flag_refused(self):
        self.refused("qualified", True)

    def test_rehashed_dimension_refused(self):
        self.refused("dimension", 768)

    def test_rehashed_bank_count_refused(self):
        self.refused("bank_count", 3)

    def test_rehashed_fake_bank_refused(self):
        self.refused("fake_360_row_bank", True)

    def test_rehashed_all_admission_flags_refused(self):
        for flag in FIXTURE.subject.FALSE:
            with self.subTest(flag=flag):
                self.refused(flag, True)

    def test_rehashed_unique_source_count_refused(self):
        self.refused("total_unique_sources", 359)

    def test_rehashed_extra_descriptor_member_refused(self):
        self.refused("implicit_selector_bank", "exposed_v3")

    def test_rehashed_missing_authentic_bank_receipt_refused(self):
        changed = deepcopy(self.case.descriptor["bank_receipts"])
        changed.pop("balanced")
        self.refused("bank_receipts", changed)

    def test_rehashed_altered_authentic_bank_receipt_refused(self):
        changed = deepcopy(self.case.descriptor["bank_receipts"])
        changed["balanced"]["bank_sha256"] = "0" * 64
        self.refused("bank_receipts", changed)

    def test_rehashed_boolean_fixed_counts_refused(self):
        for field in ("dimension", "bank_count", "total_unique_sources"):
            with self.subTest(field=field):
                self.refused(field, True)


if __name__ == "__main__":
    unittest.main()
