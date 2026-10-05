import RealMinimizerV2
import Mathlib.Analysis.Calculus.LocalExtr.Basic

set_option backward.isDefEq.respectTransparency false

/-!
SOURCE-ONLY DRAFT: never elaborated, compiled, tested, or qualified here.
Actual scalar directional derivatives give stationarity at a true global
minimum. The derived lower Taylor theorem gives quadratic growth, and positive
mu then gives uniqueness. The original unique-existence conclusion joins these
facts to the independently proved actual minimizer existence theorem.
No convergence, contraction, stationarity, or growth conclusion is a premise.
-/

namespace RankerRealCurvature

noncomputable section

open Filter
open scoped BigOperators Topology

/-- A zero coordinate square sum forces every coordinate to vanish. -/
theorem eq_zero_of_squaredEuclideanNorm_eq_zero {m : ℕ} {v : Fin m → ℝ}
    (hzero : squaredEuclideanNorm v = 0) : v = 0 := by
  funext j
  change v j = 0
  have hcoordinate : (v j) ^ 2 ≤ squaredEuclideanNorm v := by
    unfold squaredEuclideanNorm
    exact Finset.single_le_sum (fun k _ => sq_nonneg (v k)) (Finset.mem_univ j)
  rw [hzero] at hcoordinate
  exact sq_eq_zero_iff.mp (le_antisymm hcoordinate (sq_nonneg (v j)))

/-- Fermat on the actual line in the gradient direction proves coordinate stationarity. -/
theorem realCoordinateGradient_eq_zero_of_global_minimum {n m : ℕ} (mu : ℝ)
    (differences : Fin n → Fin m → ℝ) (z : Fin m → ℝ)
    (hmin : ∀ w, realObjective mu differences z ≤ realObjective mu differences w) :
    realCoordinateGradient mu differences z = 0 := by
  let g : Fin m → ℝ := realCoordinateGradient mu differences z
  have hlocal : IsLocalMin (realObjectiveLine mu differences z g) (0 : ℝ) := by
    change ∀ᶠ t in 𝓝 (0 : ℝ),
      realObjectiveLine mu differences z g 0 ≤ realObjectiveLine mu differences z g t
    apply Filter.Eventually.of_forall
    intro t
    simpa only [realObjectiveLine, lineShift_zero] using hmin (lineShift z g t)
  have hderivative := hlocal.hasDerivAt_eq_zero
    (hasDerivAt_realObjectiveLine mu differences z g 0)
  have hdot : dot g g = 0 := by
    simpa only [lineFirstDerivative_zero_eq_dot_gradient] using hderivative
  have hnorm : squaredEuclideanNorm g = 0 := by
    simpa only [dot_self_eq_squaredEuclideanNorm] using hdot
  exact eq_zero_of_squaredEuclideanNorm_eq_zero hnorm

/-- The actual lower Taylor bound and derived stationarity give quadratic growth. -/
theorem realObjective_quadratic_growth_at_minimum {n m : ℕ} (hn : 0 < n) (mu : ℝ)
    (differences : Fin n → Fin m → ℝ) (z w : Fin m → ℝ)
    (hmin : ∀ y, realObjective mu differences z ≤ realObjective mu differences y) :
    (mu / 2) * squaredEuclideanNorm (fun j => w j - z j) ≤
      realObjective mu differences w - realObjective mu differences z := by
  have hgradient := realCoordinateGradient_eq_zero_of_global_minimum mu differences z hmin
  have hdot : dot (realCoordinateGradient mu differences z) (fun j => w j - z j) = 0 := by
    rw [hgradient]
    simp only [dot, Pi.zero_apply, zero_mul, Finset.sum_const_zero]
  have hlower := realObjective_lower_between hn mu differences z w
  rw [hdot] at hlower
  linarith

/-- Two true global minimizers coincide when the proved regularization coefficient is positive. -/
theorem realObjective_minimizer_unique {n m : ℕ} (hn : 0 < n) (mu : ℝ)
    (hmu : 0 < mu) (differences : Fin n → Fin m → ℝ) (z1 z2 : Fin m → ℝ)
    (hmin1 : ∀ w, realObjective mu differences z1 ≤ realObjective mu differences w)
    (hmin2 : ∀ w, realObjective mu differences z2 ≤ realObjective mu differences w) :
    z1 = z2 := by
  have hgrowth := realObjective_quadratic_growth_at_minimum hn mu differences z1 z2 hmin1
  have hvalues : realObjective mu differences z2 - realObjective mu differences z1 = 0 := by
    linarith [hmin1 z2, hmin2 z1]
  rw [hvalues] at hgrowth
  have hnonneg := squaredEuclideanNorm_nonneg (fun j => z2 j - z1 j)
  have hnorm : squaredEuclideanNorm (fun j => z2 j - z1 j) = 0 := by
    nlinarith [hmu]
  have hdisplacement : (fun j => z2 j - z1 j) = (0 : Fin m → ℝ) :=
    eq_zero_of_squaredEuclideanNorm_eq_zero hnorm
  funext j
  have hcoordinate := congrFun hdisplacement j
  change z2 j - z1 j = 0 at hcoordinate
  linarith

/-- Stationarity for any true global minimizer of the bound original exact-real model. -/
theorem originalReal_gradient_eq_zero_of_global_minimum (z : Fin 80 → ℝ)
    (hmin : ∀ w, realObjective originalRealMu originalRealDifferences z ≤
      realObjective originalRealMu originalRealDifferences w) :
    realCoordinateGradient originalRealMu originalRealDifferences z = 0 := by
  exact realCoordinateGradient_eq_zero_of_global_minimum
    originalRealMu originalRealDifferences z hmin

/-- Original-model quadratic growth around any true global minimizer. -/
theorem originalReal_quadratic_growth_at_minimum (z w : Fin 80 → ℝ)
    (hmin : ∀ y, realObjective originalRealMu originalRealDifferences z ≤
      realObjective originalRealMu originalRealDifferences y) :
    (originalRealMu / 2) * squaredEuclideanNorm (fun j => w j - z j) ≤
      realObjective originalRealMu originalRealDifferences w -
        realObjective originalRealMu originalRealDifferences z := by
  exact realObjective_quadratic_growth_at_minimum (by norm_num : 0 < (4 : ℕ))
    originalRealMu originalRealDifferences z w hmin

/-- Uniqueness uses the original positive mu, with no uniqueness premise. -/
theorem originalReal_minimizer_unique (z1 z2 : Fin 80 → ℝ)
    (hmin1 : ∀ w, realObjective originalRealMu originalRealDifferences z1 ≤
      realObjective originalRealMu originalRealDifferences w)
    (hmin2 : ∀ w, realObjective originalRealMu originalRealDifferences z2 ≤
      realObjective originalRealMu originalRealDifferences w) : z1 = z2 := by
  exact realObjective_minimizer_unique (by norm_num : 0 < (4 : ℕ))
    originalRealMu originalReal_mu_pos originalRealDifferences z1 z2 hmin1 hmin2

/-- The independently proved original existence theorem now has an actual unique witness. -/
theorem originalReal_exists_unique_global_minimizer :
    ∃! z : Fin 80 → ℝ, ∀ w,
      realObjective originalRealMu originalRealDifferences z ≤
        realObjective originalRealMu originalRealDifferences w := by
  obtain ⟨z, hz⟩ := originalReal_exists_global_minimizer
  refine ⟨z, hz, ?_⟩
  intro y hy
  exact originalReal_minimizer_unique y z hy hz

#print axioms eq_zero_of_squaredEuclideanNorm_eq_zero
#print axioms realCoordinateGradient_eq_zero_of_global_minimum
#print axioms realObjective_quadratic_growth_at_minimum
#print axioms realObjective_minimizer_unique
#print axioms originalReal_gradient_eq_zero_of_global_minimum
#print axioms originalReal_quadratic_growth_at_minimum
#print axioms originalReal_minimizer_unique
#print axioms originalReal_exists_unique_global_minimizer

end

end RankerRealCurvature
