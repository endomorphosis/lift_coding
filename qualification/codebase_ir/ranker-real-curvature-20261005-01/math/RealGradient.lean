import DirectionalObjective

set_option backward.isDefEq.respectTransparency false

/-!
Coordinate gradient of the stated exact-real objective. Finite sums establish
the first directional derivative identity; no gradient identity is a premise.
This does not identify a binary64 gradient or any native implementation error.
-/

namespace RankerRealCurvature

noncomputable section

open scoped BigOperators

def realCoordinateGradient {n m : ℕ} (mu : ℝ)
    (differences : Fin n → Fin m → ℝ) (w : Fin m → ℝ) : Fin m → ℝ :=
  fun j => mu * w j - (1 / (n : ℝ)) * ∑ i,
    realLogisticP (dot w (differences i)) * differences i j

theorem dot_realCoordinateGradient {n m : ℕ} (mu : ℝ)
    (differences : Fin n → Fin m → ℝ) (w v : Fin m → ℝ) :
    dot (realCoordinateGradient mu differences w) v = mu * dot w v -
      (1 / (n : ℝ)) * ∑ i, realLogisticP (dot w (differences i)) *
        dot v (differences i) := by
  have hdata : (∑ j : Fin m,
      (∑ i : Fin n, realLogisticP (dot w (differences i)) * differences i j) * v j) =
      ∑ i : Fin n, realLogisticP (dot w (differences i)) * dot v (differences i) := by
    simp only [Finset.sum_mul]
    rw [Finset.sum_comm]
    apply Finset.sum_congr rfl
    intro i _
    simp only [dot, Finset.mul_sum]
    apply Finset.sum_congr rfl
    intro j _
    ring
  have hmean : (∑ j : Fin m,
      ((1 / (n : ℝ)) * ∑ i : Fin n,
        realLogisticP (dot w (differences i)) * differences i j) * v j) =
      (1 / (n : ℝ)) * ∑ i : Fin n,
        realLogisticP (dot w (differences i)) * dot v (differences i) := by
    calc
      _ = (1 / (n : ℝ)) * ∑ j : Fin m,
          (∑ i : Fin n, realLogisticP (dot w (differences i)) * differences i j) * v j := by
        rw [Finset.mul_sum]
        apply Finset.sum_congr rfl
        intro j _
        ring
      _ = _ := by rw [hdata]
  have hregularizer : (∑ j : Fin m, (mu * w j) * v j) = mu * dot w v := by
    simp only [dot, Finset.mul_sum]
    apply Finset.sum_congr rfl
    intro j _
    ring
  change (∑ j : Fin m,
      (mu * w j - (1 / (n : ℝ)) * ∑ i : Fin n,
        realLogisticP (dot w (differences i)) * differences i j) * v j) =
    mu * dot w v - (1 / (n : ℝ)) * ∑ i : Fin n,
      realLogisticP (dot w (differences i)) * dot v (differences i)
  simp only [sub_mul, Finset.sum_sub_distrib]
  rw [hregularizer, hmean]

theorem lineShift_zero {m : ℕ} (w v : Fin m → ℝ) : lineShift w v 0 = w := by
  funext j
  simp only [lineShift, zero_mul, add_zero]

theorem lineFirstDerivative_zero_eq_dot_gradient {n m : ℕ} (mu : ℝ)
    (differences : Fin n → Fin m → ℝ) (w v : Fin m → ℝ) :
    lineFirstDerivative mu differences w v 0 =
      dot (realCoordinateGradient mu differences w) v := by
  simp only [lineFirstDerivative, lineShift_zero]
  exact (dot_realCoordinateGradient mu differences w v).symm

theorem dot_const_mul_right {m : ℕ} (u v : Fin m → ℝ) (a : ℝ) :
    dot u (fun j => a * v j) = a * dot u v := by
  simp only [dot, Finset.mul_sum]
  apply Finset.sum_congr rfl
  intro j _
  ring

theorem squaredEuclideanNorm_const_mul {m : ℕ} (v : Fin m → ℝ) (a : ℝ) :
    squaredEuclideanNorm (fun j => a * v j) = a ^ 2 * squaredEuclideanNorm v := by
  simp only [squaredEuclideanNorm, mul_pow, Finset.mul_sum]

#print axioms lineFirstDerivative_zero_eq_dot_gradient

end

end RankerRealCurvature
