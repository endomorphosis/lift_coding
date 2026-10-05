import Mathlib.Analysis.Complex.Exponential
import Mathlib.Algebra.Order.BigOperators.Ring.Finset
import Mathlib.Tactic.Linarith

/-!
Real analytic coefficient and finite-dimensional candidate curvature bounds.

These theorems concern Real.exp and an explicitly stated quadratic form. They
DO NOT identify that form with the derivative/Hessian of a real objective, or
identify real arithmetic with CPython binary64, math.fsum or platform libm.
The original profile has four pairs and eighty coordinates. Its externally
pinned differences may instantiate the universal theorem once the numeric
binding is independently checked; no historical execution origin is asserted.
-/

namespace RankerRealCurvature

noncomputable section

open scoped BigOperators

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

/-- Coordinate dot product. -/
def dot {m : ℕ} (u v : Fin m → ℝ) : ℝ := ∑ j, u j * v j

/-- Squared Euclidean coordinate norm, not the function space's default norm. -/
def squaredEuclideanNorm {m : ℕ} (v : Fin m → ℝ) : ℝ := ∑ j, (v j) ^ 2

theorem squaredEuclideanNorm_nonneg {m : ℕ} (v : Fin m → ℝ) :
    0 ≤ squaredEuclideanNorm v := by
  exact Finset.sum_nonneg (fun j _ => sq_nonneg (v j))

theorem dot_sq_le {m : ℕ} (u v : Fin m → ℝ) :
    (dot u v) ^ 2 ≤ squaredEuclideanNorm u * squaredEuclideanNorm v := by
  simpa [dot, squaredEuclideanNorm] using
    (Finset.sum_mul_sq_le_sq_mul_sq (Finset.univ : Finset (Fin m)) u v)

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
        add_le_add_left (mul_le_mul_of_nonneg_left hsum hmean) _
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

#print axioms realLogisticCoeff_bounds
#print axioms candidateHessianQuad_bounds
#print axioms originalFourPairCandidate_bounds

end

end RankerRealCurvature
