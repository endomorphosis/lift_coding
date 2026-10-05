import Mathlib.Analysis.Complex.Exponential
import Mathlib.Tactic.Linarith

/- Real logistic probability and sharp coefficient bound; no native arithmetic claim. -/
namespace RankerRealCurvature

noncomputable section

/-- Real p for the pair loss log (1 + exp (-margin)). -/
def realLogisticP (margin : ℝ) : ℝ := 1 / (1 + Real.exp margin)

/-- The real analytic logistic curvature coefficient. -/
def realLogisticCoeff (margin : ℝ) : ℝ :=
  realLogisticP margin * (1 - realLogisticP margin)

/-- The underlying real probability is strictly between zero and one. -/
theorem realLogisticP_mem_Ioo (margin : ℝ) :
    0 < realLogisticP margin ∧ realLogisticP margin < 1 := by
  have hexp : 0 < Real.exp margin := Real.exp_pos margin
  have hden : 0 < 1 + Real.exp margin := by linarith
  have hp : 0 < realLogisticP margin := by
    unfold realLogisticP
    exact one_div_pos.mpr hden
  have hprod : realLogisticP margin * (1 + Real.exp margin) = 1 := by
    unfold realLogisticP
    exact div_mul_cancel₀ 1 (ne_of_gt hden)
  have hpositiveProduct : 0 < realLogisticP margin * Real.exp margin :=
    mul_pos hp hexp
  constructor
  · exact hp
  · nlinarith [hprod, hpositiveProduct]

/-- Nonnegative curvature with the exact sharp global cap one quarter. -/
theorem realLogisticCoeff_bounds (margin : ℝ) :
    0 ≤ realLogisticCoeff margin ∧ realLogisticCoeff margin ≤ (1 / 4 : ℝ) := by
  obtain ⟨hp, hpOne⟩ := realLogisticP_mem_Ioo margin
  constructor
  · unfold realLogisticCoeff
    exact mul_nonneg hp.le (sub_nonneg.mpr hpOne.le)
  · unfold realLogisticCoeff
    nlinarith [sq_nonneg (realLogisticP margin - (1 / 2 : ℝ))]

/-- The cap is attained at a concrete real margin; the theorem is nonvacuous. -/
theorem realLogisticCoeff_zero : realLogisticCoeff 0 = (1 / 4 : ℝ) := by
  norm_num [realLogisticCoeff, realLogisticP]


#print axioms realLogisticCoeff_bounds
#print axioms realLogisticCoeff_zero

end

end RankerRealCurvature
