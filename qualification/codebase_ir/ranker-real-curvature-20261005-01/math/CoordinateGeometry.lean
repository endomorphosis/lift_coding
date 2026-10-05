import Mathlib.Algebra.Order.BigOperators.Ring.Finset
import Mathlib.Basic.Real.Basic

/- Explicit finite real Euclidean coordinate geometry; no default function norm. -/
namespace RankerRealCurvature

noncomputable section

open scoped BigOperators

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


#print axioms dot_sq_le

end

end RankerRealCurvature
