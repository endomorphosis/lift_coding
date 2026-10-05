import OriginalRealProfile
import RealDescent

set_option backward.isDefEq.respectTransparency false

/-!
SOURCE-ONLY DRAFT: never elaborated, compiled, tested, or qualified.
The sealed curvature qualification is only a read dependency.
These candidate proofs add the lower Taylor inequality for the actual objective;
they do not assert minimizer existence, a contraction, or convergence.
-/

namespace RankerRealCurvature

noncomputable section

open scoped BigOperators

/-- Lower Taylor bound obtained by applying the qualified upper bound to `-f`. -/
theorem scalar_taylor_unit_lower {f f' f'' : ℝ → ℝ} (c : ℝ)
    (hfirst : ∀ t, HasDerivAt f (f' t) t)
    (hsecond : ∀ t, HasDerivAt f' (f'' t) t)
    (hbound : ∀ t, c ≤ f'' t) :
    f 0 + f' 0 + c / 2 ≤ f 1 := by
  have hupper := scalar_taylor_unit_upper
    (f := fun t => -f t) (f' := fun t => -f' t) (f'' := fun t => -f'' t)
    (-c) (fun t => (hfirst t).neg) (fun t => (hsecond t).neg)
    (fun t => neg_le_neg (hbound t))
  linarith

/-- Derived from the established second derivative at every line point. -/
theorem realObjective_taylor_lower {n m : ℕ} (hn : 0 < n) (mu : ℝ)
    (differences : Fin n → Fin m → ℝ) (w v : Fin m → ℝ) :
    realObjective mu differences w + dot (realCoordinateGradient mu differences w) v +
        (mu / 2) * squaredEuclideanNorm v ≤
      realObjective mu differences (lineShift w v 1) := by
  have hbound : ∀ t, mu * squaredEuclideanNorm v ≤
      candidateHessianQuad mu (lineShift w v t) differences v := by
    intro t
    exact (candidateHessianQuad_bounds hn mu (lineShift w v t) differences v).1
  have hlower := scalar_taylor_unit_lower (mu * squaredEuclideanNorm v)
    (hasDerivAt_realObjectiveLine mu differences w v)
    (hasDerivAt_lineFirstDerivative mu differences w v) hbound
  calc
    _ = realObjective mu differences w + dot (realCoordinateGradient mu differences w) v +
        (mu * squaredEuclideanNorm v) / 2 := by ring
    _ ≤ _ := by
      simpa only [realObjectiveLine, lineShift_zero,
        lineFirstDerivative_zero_eq_dot_gradient] using hlower

/-- The same actual lower bound for arbitrary endpoints. -/
theorem realObjective_lower_between {n m : ℕ} (hn : 0 < n) (mu : ℝ)
    (differences : Fin n → Fin m → ℝ) (w y : Fin m → ℝ) :
    realObjective mu differences w +
        dot (realCoordinateGradient mu differences w) (fun j => y j - w j) +
        (mu / 2) * squaredEuclideanNorm (fun j => y j - w j) ≤
      realObjective mu differences y := by
  have hpoint : lineShift w (fun j => y j - w j) 1 = y := by
    funext j
    dsimp [lineShift]
    ring
  simpa only [hpoint] using
    realObjective_taylor_lower hn mu differences w (fun j => y j - w j)

/-- The loss is nonnegative by exp positivity and log monotonicity. -/
theorem realPairLoss_nonneg (margin : ℝ) : 0 ≤ realPairLoss margin := by
  unfold realPairLoss
  exact Real.log_nonneg (by linarith [Real.exp_pos (-margin)])

/-- The actual objective controls the coordinate square sum through its regularizer. -/
theorem realObjective_regularizer_lower {n m : ℕ} (hn : 0 < n) (mu : ℝ)
    (differences : Fin n → Fin m → ℝ) (w : Fin m → ℝ) :
    (mu / 2) * squaredEuclideanNorm w ≤ realObjective mu differences w := by
  have hnReal : (0 : ℝ) < (n : ℝ) := Nat.cast_pos.mpr hn
  have hsum : 0 ≤ ∑ i, realPairLoss (dot w (differences i)) :=
    Finset.sum_nonneg (fun i _ => realPairLoss_nonneg _)
  have hmean := mul_nonneg (one_div_pos.mpr hnReal).le hsum
  unfold realObjective
  linarith

/-- Explicit specialization to the already joined original 4 x 80 exact-real model. -/
theorem originalReal_lower_between (w y : Fin 80 → ℝ) :
    realObjective originalRealMu originalRealDifferences w +
        dot (realCoordinateGradient originalRealMu originalRealDifferences w)
          (fun j => y j - w j) +
        (originalRealMu / 2) * squaredEuclideanNorm (fun j => y j - w j) ≤
      realObjective originalRealMu originalRealDifferences y := by
  exact realObjective_lower_between (by norm_num : 0 < (4 : ℕ))
    originalRealMu originalRealDifferences w y

#print axioms scalar_taylor_unit_lower
#print axioms realObjective_taylor_lower
#print axioms realObjective_lower_between
#print axioms realPairLoss_nonneg
#print axioms realObjective_regularizer_lower
#print axioms originalReal_lower_between

end

end RankerRealCurvature
