import OriginalRealProfile
import RealDescent

set_option backward.isDefEq.respectTransparency false

/- Original exact-real safe descent, with explicit verified data/parameter joins. -/
namespace RankerRealCurvature

noncomputable section

open scoped BigOperators

theorem originalReal_meanCurvatureBound_exact :
    meanCurvatureBound originalRealMu originalRealDifferences = originalRealMeanL := by
  simpa only [meanCurvatureBound, Nat.cast_ofNat, show (4 : ℝ) * 4 = 16 by norm_num] using
    originalReal_meanL_exact

/-- The actual original real-coordinate model and its stored eta have safe decrease. -/
theorem originalReal_safe_descent (w : Fin 80 → ℝ) :
    realObjective originalRealMu originalRealDifferences
        (realGradientStep originalRealMu originalRealEta originalRealDifferences w) ≤
      realObjective originalRealMu originalRealDifferences w - (originalRealEta / 2) *
        squaredEuclideanNorm (realCoordinateGradient originalRealMu originalRealDifferences w) := by
  have hstep : originalRealEta ≤ 1 / meanCurvatureBound originalRealMu originalRealDifferences := by
    rw [originalReal_meanCurvatureBound_exact]
    exact originalReal_eta_le_inverse_meanL
  exact realGradientStep_safe_descent (by norm_num : 0 < (4 : ℕ)) originalReal_mu_pos
    originalReal_eta_pos.le originalRealDifferences hstep w

#print axioms originalReal_meanCurvatureBound_exact
#print axioms originalReal_safe_descent

end

end RankerRealCurvature
