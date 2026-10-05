import RealPL
import OriginalRealDescent
import Mathlib.Analysis.SpecificLimits.Basic

set_option backward.isDefEq.respectTransparency false

/-!
Additive candidate for a separate bounded native qualification.
The exact original-model gap contraction is derived from the actual descent
and scaled gradient-domination theorems. The recurrence uses the actual exact-
real gradient step. Limit theorems require a genuine global-minimum property;
they do not assume any contraction, convergence, or existence conclusion.
No convergence of the weight vectors or native Float execution is asserted.
-/

namespace RankerRealCurvature

noncomputable section

open Filter
open scoped BigOperators Topology

def originalRealRho : ℝ := 1 - originalRealEta * originalRealMu

def originalRealGap (w z : Fin 80 → ℝ) : ℝ :=
  realObjective originalRealMu originalRealDifferences w -
    realObjective originalRealMu originalRealDifferences z

/-- The recorded exact mean curvature is mu plus a nonnegative coordinate term. -/
theorem originalReal_mu_le_meanL : originalRealMu ≤ originalRealMeanL := by
  have hsum : 0 ≤ ∑ i : Fin 4, squaredEuclideanNorm (originalRealDifferences i) :=
    Finset.sum_nonneg (fun i _ => squaredEuclideanNorm_nonneg (originalRealDifferences i))
  have hmean : 0 ≤ (∑ i : Fin 4, squaredEuclideanNorm (originalRealDifferences i)) / 16 :=
    div_nonneg hsum (by norm_num)
  have hexact := originalReal_meanL_exact
  linarith

/-- The original positive mu and stored safe eta give an actual geometric ratio. -/
theorem originalReal_rho_bounds : 0 ≤ originalRealRho ∧ originalRealRho < 1 := by
  have hmul := mul_le_mul_of_nonneg_left originalReal_mu_le_meanL originalReal_eta_pos.le
  have hsafe := originalReal_eta_times_meanL_le_one
  have hpositive : 0 < originalRealEta * originalRealMu :=
    mul_pos originalReal_eta_pos originalReal_mu_pos
  unfold originalRealRho
  constructor <;> linarith

/-- Derived gap contraction against every reference z for the exact original step. -/
theorem originalReal_gap_contraction (w z : Fin 80 → ℝ) :
    originalRealGap
        (realGradientStep originalRealMu originalRealEta originalRealDifferences w) z ≤
      originalRealRho * originalRealGap w z := by
  have hdescent := originalReal_safe_descent w
  have hpl := originalReal_scaled_gradient_domination w z
  have hplscaled := mul_le_mul_of_nonneg_left hpl
    (div_nonneg originalReal_eta_pos.le (by norm_num : (0 : ℝ) ≤ 2))
  dsimp only [originalRealGap, originalRealRho]
  nlinarith only [hdescent, hplscaled]

/-- Exact-real gradient descent for the original fixed four-pair coordinate data. -/
def originalRealIterate (w0 : Fin 80 → ℝ) : ℕ → (Fin 80 → ℝ)
  | 0 => w0
  | k + 1 =>
      realGradientStep originalRealMu originalRealEta originalRealDifferences
        (originalRealIterate w0 k)

/-- The actual recurrence inherits a geometric gap upper bound by induction. -/
theorem originalReal_iterate_gap_le (w0 z : Fin 80 → ℝ) (k : ℕ) :
    originalRealGap (originalRealIterate w0 k) z ≤
      originalRealRho ^ k * originalRealGap w0 z := by
  induction k with
  | zero =>
      simp only [originalRealIterate, pow_zero, one_mul, le_refl]
  | succ k ih =>
      have hstep := originalReal_gap_contraction (originalRealIterate w0 k) z
      calc
        _ ≤ originalRealRho * originalRealGap (originalRealIterate w0 k) z := by
          simpa only [originalRealIterate] using hstep
        _ ≤ originalRealRho * (originalRealRho ^ k * originalRealGap w0 z) :=
          mul_le_mul_of_nonneg_left ih originalReal_rho_bounds.1
        _ = originalRealRho ^ (k + 1) * originalRealGap w0 z := by
          rw [pow_succ]
          ring

/-- A true global minimizer supplies the lower gap bound needed by squeeze. -/
theorem originalReal_iterate_gap_tendsto_zero (w0 z : Fin 80 → ℝ)
    (hmin : ∀ w : Fin 80 → ℝ,
      realObjective originalRealMu originalRealDifferences z ≤
        realObjective originalRealMu originalRealDifferences w) :
    Tendsto (fun k => originalRealGap (originalRealIterate w0 k) z) atTop (𝓝 0) := by
  have hpower : Tendsto (fun k : ℕ => originalRealRho ^ k) atTop (𝓝 (0 : ℝ)) :=
    tendsto_pow_atTop_nhds_zero_of_lt_one originalReal_rho_bounds.1
      originalReal_rho_bounds.2
  have hupper : Tendsto
      (fun k : ℕ => originalRealRho ^ k * originalRealGap w0 z) atTop (𝓝 (0 : ℝ)) := by
    simpa only [zero_mul] using hpower.mul_const (originalRealGap w0 z)
  have hzero : Tendsto (fun _ : ℕ => (0 : ℝ)) atTop (𝓝 (0 : ℝ)) :=
    tendsto_const_nhds
  apply tendsto_of_tendsto_of_tendsto_of_le_of_le hzero hupper
  · intro k
    exact sub_nonneg.mpr (hmin (originalRealIterate w0 k))
  · intro k
    exact originalReal_iterate_gap_le w0 z k

/-- Conditional on a true global minimizer, the actual objective values converge. -/
theorem originalReal_iterate_objective_tendsto (w0 z : Fin 80 → ℝ)
    (hmin : ∀ w : Fin 80 → ℝ,
      realObjective originalRealMu originalRealDifferences z ≤
        realObjective originalRealMu originalRealDifferences w) :
    Tendsto
      (fun k => realObjective originalRealMu originalRealDifferences (originalRealIterate w0 k))
      atTop (𝓝 (realObjective originalRealMu originalRealDifferences z)) := by
  have hgap := originalReal_iterate_gap_tendsto_zero w0 z hmin
  simpa only [originalRealGap, sub_add_cancel, zero_add] using
    hgap.add_const (realObjective originalRealMu originalRealDifferences z)

#print axioms originalReal_mu_le_meanL
#print axioms originalReal_rho_bounds
#print axioms originalReal_gap_contraction
#print axioms originalReal_iterate_gap_le
#print axioms originalReal_iterate_gap_tendsto_zero
#print axioms originalReal_iterate_objective_tendsto

end

end RankerRealCurvature

#print axioms _root_.RankerRealCurvature.originalReal_mu_le_meanL
#print axioms _root_.RankerRealCurvature.originalReal_rho_bounds
#print axioms _root_.RankerRealCurvature.originalReal_gap_contraction
#print axioms _root_.RankerRealCurvature.originalReal_iterate_gap_le
#print axioms _root_.RankerRealCurvature.originalReal_iterate_gap_tendsto_zero
#print axioms _root_.RankerRealCurvature.originalReal_iterate_objective_tendsto
