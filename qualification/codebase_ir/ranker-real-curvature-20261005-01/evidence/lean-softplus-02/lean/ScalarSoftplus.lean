import LogisticCurvature
import Mathlib.Analysis.SpecialFunctions.Log.Deriv
import Mathlib.Analysis.Calculus.Deriv.Inv
import Mathlib.Tactic.FieldSimp

set_option backward.isDefEq.respectTransparency false

/-!
Actual derivatives of the stated real pair loss. These theorems add a real
calculus identity, not a proof about binary64 exp/log1p/fsum or Python source
semantics. All denominators are proved nonzero from Real.exp positivity.
-/

namespace RankerRealCurvature

noncomputable section

/-- The real pair loss as a function of its signed preferred-minus-baseline margin. -/
def realPairLoss (margin : ℝ) : ℝ := Real.log (1 + Real.exp (-margin))

/-- The native stable branch shape interpreted in exact real arithmetic. -/
def realStablePairLoss (margin : ℝ) : ℝ :=
  max 0 (-margin) + Real.log (1 + Real.exp (-|margin|))

theorem realStablePairLoss_eq (margin : ℝ) :
    realStablePairLoss margin = realPairLoss margin := by
  by_cases hmargin : 0 ≤ margin
  · simp only [realStablePairLoss, realPairLoss, abs_of_nonneg hmargin,
      max_eq_left (neg_nonpos.mpr hmargin), zero_add]
  · have hnonpos : margin ≤ 0 := (lt_of_not_ge hmargin).le
    have hprod : Real.exp (-margin) * Real.exp margin = 1 := by
      rw [← Real.exp_add, neg_add_cancel, Real.exp_zero]
    have harg : 1 + Real.exp (-margin) =
        Real.exp (-margin) * (1 + Real.exp margin) := by
      calc
        1 + Real.exp (-margin) = Real.exp (-margin) + 1 := add_comm _ _
        _ = Real.exp (-margin) * (1 + Real.exp margin) := by
          rw [mul_add, mul_one, hprod]
    have hplus : 0 < 1 + Real.exp margin := by linarith [Real.exp_pos margin]
    unfold realStablePairLoss realPairLoss
    rw [abs_of_nonpos hnonpos, max_eq_right (neg_nonneg.mpr hnonpos)]
    simp only [neg_neg]
    rw [harg, Real.log_mul (ne_of_gt (Real.exp_pos (-margin))) (ne_of_gt hplus),
      Real.log_exp]

/-- Differentiation of the real reciprocal exponential probability. -/
theorem hasDerivAt_realLogisticP (margin : ℝ) :
    HasDerivAt realLogisticP (-realLogisticCoeff margin) margin := by
  have hden : 0 < 1 + Real.exp margin := by linarith [Real.exp_pos margin]
  have hdenNe : 1 + Real.exp margin ≠ 0 := ne_of_gt hden
  have hbase : HasDerivAt (fun x : ℝ => 1 + Real.exp x) (Real.exp margin) margin :=
    (Real.hasDerivAt_exp margin).const_add 1
  have hvalue : -Real.exp margin / (1 + Real.exp margin) ^ 2 =
      -realLogisticCoeff margin := by
    unfold realLogisticCoeff realLogisticP
    field_simp [hdenNe] <;> ring
  have hfunction : realLogisticP = (fun x : ℝ => 1 + Real.exp x)⁻¹ := by
    funext x
    simp only [realLogisticP, one_div, Pi.inv_apply]
  rw [hfunction]
  exact (hbase.inv hdenNe).congr_deriv hvalue

/-- The actual derivative of log (1 + exp (-margin)) is -p. -/
theorem hasDerivAt_realPairLoss (margin : ℝ) :
    HasDerivAt realPairLoss (-realLogisticP margin) margin := by
  have hminus : 0 < 1 + Real.exp (-margin) := by linarith [Real.exp_pos (-margin)]
  have hplus : 0 < 1 + Real.exp margin := by linarith [Real.exp_pos margin]
  have hInvPlus : 1 + (Real.exp margin)⁻¹ ≠ 0 := by
    simpa only [Real.exp_neg] using (ne_of_gt hminus)
  have hexp : HasDerivAt (fun x : ℝ => Real.exp (-x)) (-Real.exp (-margin)) margin := by
    simpa only [Function.comp_def, mul_neg, mul_one] using
      (Real.hasDerivAt_exp (-margin)).comp margin (hasDerivAt_id' margin).neg
  have hlog := (hexp.const_add 1).log (ne_of_gt hminus)
  have hvalue : -Real.exp (-margin) / (1 + Real.exp (-margin)) =
      -realLogisticP margin := by
    rw [Real.exp_neg]
    unfold realLogisticP
    field_simp [ne_of_gt (Real.exp_pos margin), ne_of_gt hplus, hInvPlus] <;> ring
  change HasDerivAt (fun x : ℝ => Real.log (1 + Real.exp (-x)))
    (-realLogisticP margin) margin
  exact hlog.congr_deriv hvalue

/-- The derivative of the actual first-derivative formula is the curvature coefficient. -/
theorem hasDerivAt_negative_realLogisticP (margin : ℝ) :
    HasDerivAt (fun x => -realLogisticP x) (realLogisticCoeff margin) margin := by
  change HasDerivAt (-realLogisticP) (realLogisticCoeff margin) margin
  simpa only [neg_neg] using (hasDerivAt_realLogisticP margin).neg

theorem deriv_realPairLoss (margin : ℝ) :
    deriv realPairLoss margin = -realLogisticP margin :=
  (hasDerivAt_realPairLoss margin).deriv

/-- Genuine second derivative of the explicitly defined real loss. -/
theorem secondDeriv_realPairLoss (margin : ℝ) :
    deriv (deriv realPairLoss) margin = realLogisticCoeff margin := by
  have hfirst : deriv realPairLoss = fun x => -realLogisticP x :=
    funext deriv_realPairLoss
  rw [hfirst]
  exact (hasDerivAt_negative_realLogisticP margin).deriv

#print axioms realStablePairLoss_eq
#print axioms hasDerivAt_realPairLoss
#print axioms secondDeriv_realPairLoss

end

end RankerRealCurvature

#print axioms _root_.RankerRealCurvature.realStablePairLoss_eq
#print axioms _root_.RankerRealCurvature.hasDerivAt_realPairLoss
#print axioms _root_.RankerRealCurvature.secondDeriv_realPairLoss
