import OriginalNumericCurvature
import DirectionalObjective
import Mathlib.Data.Rat.Cast.Order

set_option backward.isDefEq.respectTransparency false

/-!
Explicit Rat/List -> Fin 4 x Fin 80 -> Real bridge for the original profile.
OriginalNumericCurvature contains the independently bound literal coordinates;
finite closed facts below prove the exact indexing and norm conversion. This
does not certify binary64 arithmetic or historical execution provenance.
-/

set_option maxRecDepth 8192

namespace RankerRealCurvature

noncomputable section

open scoped BigOperators

def originalRatCoordinates (i : Fin 4) (j : Fin 80) : Rat :=
  ((OriginalRankerCurvatureArithmetic.differences.getD i.val []).getD j.val 0)

/-- No index used by the Real matrix selects a default/missing data entry. -/
theorem originalRat_index_bounds : ∀ i : Fin 4,
    i.val < OriginalRankerCurvatureArithmetic.differences.length ∧
      ∀ j : Fin 80,
        j.val < (OriginalRankerCurvatureArithmetic.differences.getD i.val []).length := by
  decide +kernel

/-- The actual finite-coordinate Rat sum equals the independently recorded norm. -/
theorem originalRat_finite_norms_exact : ∀ i : Fin 4,
    (∑ j : Fin 80, originalRatCoordinates i j * originalRatCoordinates i j) =
      OriginalRankerCurvatureArithmetic.squaredNorms.getD i.val 0 := by
  decide +kernel

/-- This closed fact joins the finite-index mean to the recorded Rat mean L. -/
theorem originalRat_finite_mean_exact :
    OriginalRankerCurvatureArithmetic.mu +
      (∑ i : Fin 4, OriginalRankerCurvatureArithmetic.squaredNorms.getD i.val 0) / 16 =
        OriginalRankerCurvatureArithmetic.meanL := by
  decide +kernel

theorem originalRat_meanL_pos : 0 < OriginalRankerCurvatureArithmetic.meanL := by
  decide +kernel

theorem ratCastFinsetSum {α : Type*} (s : Finset α) (f : α → Rat) :
    ((∑ i ∈ s, f i : Rat) : ℝ) = ∑ i ∈ s, (f i : ℝ) := by
  classical
  induction s using Finset.induction_on with
  | empty => simp only [Finset.sum_empty, Rat.cast_zero]
  | @insert a s ha ih => simp only [Finset.sum_insert ha, Rat.cast_add, ih]

def originalRealDifferences : Fin 4 → Fin 80 → ℝ :=
  fun i j => (originalRatCoordinates i j : ℝ)

def originalRealMu : ℝ := (OriginalRankerCurvatureArithmetic.mu : ℝ)

def originalRealEta : ℝ := (OriginalRankerCurvatureArithmetic.eta : ℝ)

def originalRealMeanL : ℝ := (OriginalRankerCurvatureArithmetic.meanL : ℝ)

/-- Real norms of the exact 4 x 80 coordinate matrix, proved through finite casts. -/
theorem originalReal_norms_exact (i : Fin 4) :
    squaredEuclideanNorm (originalRealDifferences i) =
      (OriginalRankerCurvatureArithmetic.squaredNorms.getD i.val 0 : ℝ) := by
  calc
    _ = ((∑ j : Fin 80, originalRatCoordinates i j * originalRatCoordinates i j : Rat) : ℝ) := by
      rw [ratCastFinsetSum]
      simp only [squaredEuclideanNorm, originalRealDifferences, Rat.cast_mul, pow_two]
    _ = _ := congrArg (fun q : Rat => (q : ℝ)) (originalRat_finite_norms_exact i)

/-- The generic four-pair curvature expression equals the recorded real L. -/
theorem originalReal_meanL_exact :
    originalRealMu + (∑ i : Fin 4, squaredEuclideanNorm (originalRealDifferences i)) / 16 =
      originalRealMeanL := by
  calc
    _ = (OriginalRankerCurvatureArithmetic.mu : ℝ) +
        (∑ i : Fin 4, (OriginalRankerCurvatureArithmetic.squaredNorms.getD i.val 0 : ℝ)) / 16 := by
      simp only [originalRealMu, originalReal_norms_exact]
    _ = ((OriginalRankerCurvatureArithmetic.mu +
        (∑ i : Fin 4, OriginalRankerCurvatureArithmetic.squaredNorms.getD i.val 0) / 16 : Rat) : ℝ) := by
      simp only [Rat.cast_add, Rat.cast_div, Rat.cast_ofNat, ratCastFinsetSum]
    _ = _ := congrArg (fun q : Rat => (q : ℝ)) originalRat_finite_mean_exact

theorem originalReal_mu_pos : 0 < originalRealMu := by
  exact Rat.cast_pos.mpr OriginalRankerCurvatureArithmetic.original_positive_scalars.1

theorem originalReal_eta_pos : 0 < originalRealEta := by
  exact Rat.cast_pos.mpr OriginalRankerCurvatureArithmetic.original_positive_scalars.2

theorem originalReal_meanL_pos : 0 < originalRealMeanL := by
  exact Rat.cast_pos.mpr originalRat_meanL_pos

theorem originalReal_eta_times_meanL_le_one : originalRealEta * originalRealMeanL ≤ 1 := by
  have h : ((OriginalRankerCurvatureArithmetic.eta * OriginalRankerCurvatureArithmetic.meanL : Rat) : ℝ) ≤
      ((1 : Rat) : ℝ) :=
    Rat.cast_le.mpr OriginalRankerCurvatureArithmetic.original_safe_steps.1
  simpa only [originalRealEta, originalRealMeanL, Rat.cast_mul, Rat.cast_one] using h

theorem originalReal_eta_le_inverse_meanL : originalRealEta ≤ 1 / originalRealMeanL :=
  (le_div_iff₀ originalReal_meanL_pos).mpr originalReal_eta_times_meanL_le_one

/-- Generic candidate bound instantiated with actual original coordinates and L. -/
theorem originalReal_candidate_bounds (w v : Fin 80 → ℝ) :
    originalRealMu * squaredEuclideanNorm v ≤
      candidateHessianQuad originalRealMu w originalRealDifferences v ∧
    candidateHessianQuad originalRealMu w originalRealDifferences v ≤
      originalRealMeanL * squaredEuclideanNorm v := by
  have h := originalFourPairCandidate_bounds originalRealMu w originalRealDifferences v
  rw [originalReal_meanL_exact] at h
  exact h

/-- Actual second directional derivative bound for the bound original real model. -/
theorem originalReal_actual_secondDirectional_bounds (w v : Fin 80 → ℝ) :
    originalRealMu * squaredEuclideanNorm v ≤
      deriv (deriv (realObjectiveLine originalRealMu originalRealDifferences w v)) 0 ∧
    deriv (deriv (realObjectiveLine originalRealMu originalRealDifferences w v)) 0 ≤
      originalRealMeanL * squaredEuclideanNorm v := by
  rw [secondDeriv_realObjectiveLine_zero]
  exact originalReal_candidate_bounds w v

#print axioms originalRat_index_bounds
#print axioms originalRat_finite_norms_exact
#print axioms originalReal_meanL_exact
#print axioms originalReal_eta_le_inverse_meanL
#print axioms originalReal_actual_secondDirectional_bounds

end

end RankerRealCurvature

#print axioms _root_.RankerRealCurvature.originalReal_norms_exact
#print axioms _root_.RankerRealCurvature.originalReal_eta_le_inverse_meanL
#print axioms _root_.RankerRealCurvature.originalReal_actual_secondDirectional_bounds
