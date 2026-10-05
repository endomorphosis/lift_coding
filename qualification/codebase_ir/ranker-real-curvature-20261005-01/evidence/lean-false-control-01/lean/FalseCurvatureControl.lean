import LogisticCoefficient
import Mathlib.Tactic.Linarith

namespace RankerRealCurvature

theorem sharp_coefficient_refutes_eighth : ¬ realLogisticCoeff 0 ≤ (1 / 8 : ℝ) := by
  rw [realLogisticCoeff_zero]
  norm_num

-- A deliberately false closed proposition must be rejected by the kernel.
theorem intentional_false_control : False := by
  decide +kernel

end RankerRealCurvature

#print axioms _root_.RankerRealCurvature.sharp_coefficient_refutes_eighth
