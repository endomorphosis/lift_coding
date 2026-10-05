import LogisticCoefficient
import CoordinateGeometry
import Mathlib.Tactic.Linarith

/- Candidate quadratic bounds. Derivative identity and native error are separate obligations. -/
namespace RankerRealCurvature

noncomputable section

open scoped BigOperators

/-- Explicit candidate Hessian quadratic form. No derivative identity assumed. -/
def candidateHessianQuad {n m : ℕ} (mu : ℝ) (w : Fin m → ℝ)
    (differences : Fin n → Fin m → ℝ) (v : Fin m → ℝ) : ℝ :=
  mu * squaredEuclideanNorm v +
    (1 / (n : ℝ)) * ∑ i,
      realLogisticCoeff (dot w (differences i)) * (dot v (differences i)) ^ 2

/-- The mean squared-difference curvature bound for the stated quadratic form. -/
theorem candidateHessianQuad_bounds {n m : ℕ} (hn : 0 < n) (mu : ℝ)
    (w : Fin m → ℝ) (differences : Fin n → Fin m → ℝ) (v : Fin m → ℝ) :
    mu * squaredEuclideanNorm v ≤ candidateHessianQuad mu w differences v ∧
    candidateHessianQuad mu w differences v ≤
      (mu + (∑ i, squaredEuclideanNorm (differences i)) / (4 * (n : ℝ))) *
        squaredEuclideanNorm v := by
  have hnReal : (0 : ℝ) < (n : ℝ) := Nat.cast_pos.mpr hn
  have hmean : 0 ≤ (1 / (n : ℝ)) := (one_div_pos.mpr hnReal).le
  have hsumNonneg : 0 ≤ ∑ i,
      realLogisticCoeff (dot w (differences i)) * (dot v (differences i)) ^ 2 := by
    exact Finset.sum_nonneg (fun i _ =>
      mul_nonneg (realLogisticCoeff_bounds (dot w (differences i))).1 (sq_nonneg _))
  have hterm : ∀ i : Fin n,
      realLogisticCoeff (dot w (differences i)) * (dot v (differences i)) ^ 2 ≤
        (1 / 4 : ℝ) * squaredEuclideanNorm (differences i) * squaredEuclideanNorm v := by
    intro i
    calc
      realLogisticCoeff (dot w (differences i)) * (dot v (differences i)) ^ 2
          ≤ (1 / 4 : ℝ) * (dot v (differences i)) ^ 2 :=
        mul_le_mul_of_nonneg_right (realLogisticCoeff_bounds _).2 (sq_nonneg _)
      _ ≤ (1 / 4 : ℝ) *
          (squaredEuclideanNorm v * squaredEuclideanNorm (differences i)) :=
        mul_le_mul_of_nonneg_left (dot_sq_le v (differences i)) (by norm_num)
      _ = (1 / 4 : ℝ) * squaredEuclideanNorm (differences i) * squaredEuclideanNorm v := by
        ring
  have hsum := Finset.sum_le_sum (s := (Finset.univ : Finset (Fin n)))
    (fun i _ => hterm i)
  have hfactor : (∑ i : Fin n,
      (1 / 4 : ℝ) * squaredEuclideanNorm (differences i) * squaredEuclideanNorm v) =
        (1 / 4 : ℝ) * (∑ i, squaredEuclideanNorm (differences i)) *
          squaredEuclideanNorm v := by
    simp only [Finset.mul_sum, Finset.sum_mul]
  rw [hfactor] at hsum
  constructor
  · unfold candidateHessianQuad
    exact le_add_of_nonneg_right (mul_nonneg hmean hsumNonneg)
  · unfold candidateHessianQuad
    calc
      mu * squaredEuclideanNorm v + (1 / (n : ℝ)) *
          (∑ i, realLogisticCoeff (dot w (differences i)) * (dot v (differences i)) ^ 2)
          ≤ mu * squaredEuclideanNorm v + (1 / (n : ℝ)) *
              ((1 / 4 : ℝ) * (∑ i, squaredEuclideanNorm (differences i)) *
                squaredEuclideanNorm v) :=
        add_le_add le_rfl (mul_le_mul_of_nonneg_left hsum hmean)
      _ = (mu + (∑ i, squaredEuclideanNorm (differences i)) / (4 * (n : ℝ))) *
            squaredEuclideanNorm v := by
        simp only [div_eq_mul_inv, mul_inv_rev]
        ring

/-- Universal specialization to the actual original four-pair, eighty-feature profile. -/
theorem originalFourPairCandidate_bounds (mu : ℝ) (w : Fin 80 → ℝ)
    (differences : Fin 4 → Fin 80 → ℝ) (v : Fin 80 → ℝ) :
    mu * squaredEuclideanNorm v ≤ candidateHessianQuad mu w differences v ∧
    candidateHessianQuad mu w differences v ≤
      (mu + (∑ i, squaredEuclideanNorm (differences i)) / 16) * squaredEuclideanNorm v := by
  have h := candidateHessianQuad_bounds (n := 4) (m := 80) (by norm_num) mu w differences v
  norm_num at h
  exact h

#print axioms candidateHessianQuad_bounds
#print axioms originalFourPairCandidate_bounds

end

end RankerRealCurvature

#print axioms _root_.RankerRealCurvature.candidateHessianQuad_bounds
#print axioms _root_.RankerRealCurvature.originalFourPairCandidate_bounds
