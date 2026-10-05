import RealGradient

set_option backward.isDefEq.respectTransparency false

/-!
Exact-real interpretation of the two probability branches in the pinned Python
objective. This does not supply Python, binary64, libm, or fsum semantics.
-/

namespace RankerRealCurvature

noncomputable section

open scoped BigOperators

def realStableLogisticP (margin : ℝ) : ℝ :=
  if 0 ≤ margin then Real.exp (-margin) / (1 + Real.exp (-margin))
  else 1 / (1 + Real.exp margin)

theorem realStableLogisticP_eq (margin : ℝ) :
    realStableLogisticP margin = realLogisticP margin := by
  have hnegativeDen : 1 + Real.exp (-margin) ≠ 0 := by
    exact ne_of_gt (by linarith [Real.exp_pos (-margin)])
  have hpositiveDen : 1 + Real.exp margin ≠ 0 := by
    exact ne_of_gt (by linarith [Real.exp_pos margin])
  have hproduct : Real.exp (-margin) * Real.exp margin = 1 := by
    rw [← Real.exp_add, neg_add_cancel, Real.exp_zero]
  unfold realStableLogisticP realLogisticP
  split_ifs
  · apply (div_eq_div_iff hnegativeDen hpositiveDen).mpr
    rw [mul_add, mul_one, hproduct]
    ring
  · rfl

def realSourceBranchGradient {n m : ℕ} (mu : ℝ)
    (differences : Fin n → Fin m → ℝ) (w : Fin m → ℝ) : Fin m → ℝ :=
  fun j => mu * w j - (1 / (n : ℝ)) * ∑ i,
    realStableLogisticP (dot w (differences i)) * differences i j

theorem realSourceBranchGradient_eq {n m : ℕ} (mu : ℝ)
    (differences : Fin n → Fin m → ℝ) (w : Fin m → ℝ) :
    realSourceBranchGradient mu differences w = realCoordinateGradient mu differences w := by
  funext j
  simp only [realSourceBranchGradient, realCoordinateGradient, realStableLogisticP_eq]

#print axioms realStableLogisticP_eq
#print axioms realSourceBranchGradient_eq

end

end RankerRealCurvature

#print axioms _root_.RankerRealCurvature.realStableLogisticP_eq
#print axioms _root_.RankerRealCurvature.realSourceBranchGradient_eq
