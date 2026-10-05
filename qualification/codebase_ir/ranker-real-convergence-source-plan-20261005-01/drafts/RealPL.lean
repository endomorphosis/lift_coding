import RealStrongLower

set_option backward.isDefEq.respectTransparency false

/-!
SOURCE-ONLY DRAFT: never elaborated, compiled, tested, or qualified here.
Gradient domination is derived for the actual finite-coordinate objective from
the lower Taylor theorem and a sum of coordinate squares. There is no minimizer,
PL inequality, gap contraction, or convergence premise in any declaration.
-/

namespace RankerRealCurvature

noncomputable section

open scoped BigOperators

/-- The square completion uses the coordinate square sum and holds for every mu. -/
theorem squared_gradient_completion_nonneg {m : ℕ} (mu : ℝ)
    (g v : Fin m → ℝ) :
    0 ≤ squaredEuclideanNorm g + 2 * mu * dot g v +
      mu ^ 2 * squaredEuclideanNorm v := by
  have hexpand : squaredEuclideanNorm (fun j => g j + mu * v j) =
      squaredEuclideanNorm g + 2 * mu * dot g v +
        mu ^ 2 * squaredEuclideanNorm v := by
    simp only [squaredEuclideanNorm, dot, Finset.mul_sum, ← Finset.sum_add_distrib]
    apply Finset.sum_congr rfl
    intro j _
    ring
  rw [← hexpand]
  exact squaredEuclideanNorm_nonneg (fun j => g j + mu * v j)

/-- Scaled PL bound against every comparison point; no minimizer is assumed. -/
theorem realObjective_scaled_gradient_domination {n m : ℕ} (hn : 0 < n)
    {mu : ℝ} (hmu : 0 < mu) (differences : Fin n → Fin m → ℝ)
    (w z : Fin m → ℝ) :
    2 * mu * (realObjective mu differences w - realObjective mu differences z) ≤
      squaredEuclideanNorm (realCoordinateGradient mu differences w) := by
  have hmu2 : 0 ≤ 2 * mu := mul_nonneg (by norm_num) hmu.le
  have hscaled := mul_le_mul_of_nonneg_left
    (realObjective_lower_between hn mu differences w z) hmu2
  have hcomplete := squared_gradient_completion_nonneg mu
    (realCoordinateGradient mu differences w) (fun j => z j - w j)
  nlinarith only [hscaled, hcomplete]

/-- Dividing the derived scaled inequality by positive 2*mu gives domination. -/
theorem realObjective_gradient_domination {n m : ℕ} (hn : 0 < n)
    {mu : ℝ} (hmu : 0 < mu) (differences : Fin n → Fin m → ℝ)
    (w z : Fin m → ℝ) :
    realObjective mu differences w - realObjective mu differences z ≤
      squaredEuclideanNorm (realCoordinateGradient mu differences w) / (2 * mu) := by
  apply (le_div_iff₀ (mul_pos (by norm_num : (0 : ℝ) < 2) hmu)).mpr
  rw [mul_comm (realObjective mu differences w - realObjective mu differences z)]
  exact realObjective_scaled_gradient_domination hn hmu differences w z

/-- Exact original-model scaled PL bound, still valid against every z. -/
theorem originalReal_scaled_gradient_domination (w z : Fin 80 → ℝ) :
    2 * originalRealMu *
        (realObjective originalRealMu originalRealDifferences w -
          realObjective originalRealMu originalRealDifferences z) ≤
      squaredEuclideanNorm
        (realCoordinateGradient originalRealMu originalRealDifferences w) := by
  exact realObjective_scaled_gradient_domination (by norm_num : 0 < (4 : ℕ))
    originalReal_mu_pos originalRealDifferences w z

/-- Exact original-model objective domination with the proved positive mu. -/
theorem originalReal_gradient_domination (w z : Fin 80 → ℝ) :
    realObjective originalRealMu originalRealDifferences w -
        realObjective originalRealMu originalRealDifferences z ≤
      squaredEuclideanNorm
          (realCoordinateGradient originalRealMu originalRealDifferences w) /
        (2 * originalRealMu) := by
  exact realObjective_gradient_domination (by norm_num : 0 < (4 : ℕ))
    originalReal_mu_pos originalRealDifferences w z

#print axioms squared_gradient_completion_nonneg
#print axioms realObjective_scaled_gradient_domination
#print axioms realObjective_gradient_domination
#print axioms originalReal_scaled_gradient_domination
#print axioms originalReal_gradient_domination

end

end RankerRealCurvature
