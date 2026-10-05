import RealGradient
import Mathlib.Analysis.Convex.Deriv

set_option backward.isDefEq.respectTransparency false

/-!
Taylor upper bound and one exact-real coordinate-gradient descent step, derived
from the actual first and second directional derivatives. The scalar helper
assumes genuine derivatives and their curvature bound, then the ranker theorem
supplies all of them from the established logistic calculus. No desired Taylor
or descent inequality is an assumption. No global contraction or Float theorem.
-/

namespace RankerRealCurvature

noncomputable section

open scoped BigOperators

/-- Upper Taylor bound at unit displacement from twice differentiable calculus. -/
theorem scalar_taylor_unit_upper {f f' f'' : ℝ → ℝ} (C : ℝ)
    (hfirst : ∀ t, HasDerivAt f (f' t) t)
    (hsecond : ∀ t, HasDerivAt f' (f'' t) t)
    (hbound : ∀ t, f'' t ≤ C) :
    f 1 ≤ f 0 + f' 0 + C / 2 := by
  let q : ℝ → ℝ := fun t => (C / 2) * t ^ 2 - f t
  let q' : ℝ → ℝ := fun t => C * t - f' t
  have hpoly : ∀ t : ℝ, HasDerivAt (fun s => (C / 2) * s ^ 2) (C * t) t := by
    intro t
    apply (((hasDerivAt_id' t).pow 2).const_mul (C / 2)).congr_deriv
    norm_num <;> ring
  have hq : ∀ t, HasDerivAt q (q' t) t := by
    intro t
    exact (hpoly t).sub (hfirst t)
  have hqSecond : ∀ t, HasDerivAt q' (C - f'' t) t := by
    intro t
    have hlinear : HasDerivAt (fun s : ℝ => C * s) C t := by
      simpa only [mul_one] using (hasDerivAt_id' t).const_mul C
    exact hlinear.sub (hsecond t)
  have hqDeriv : deriv q = q' := funext (fun t => (hq t).deriv)
  have hqDifferentiable : Differentiable ℝ q := fun t => (hq t).differentiableAt
  have hqDerivDifferentiable : Differentiable ℝ (deriv q) := by
    rw [hqDeriv]
    exact fun t => (hqSecond t).differentiableAt
  have hqSecondNonneg : ∀ t, 0 ≤ (deriv^[2] q) t := by
    intro t
    change 0 ≤ deriv (deriv q) t
    rw [hqDeriv, (hqSecond t).deriv]
    exact sub_nonneg.mpr (hbound t)
  have hconvex : ConvexOn ℝ Set.univ q :=
    convexOn_univ_of_deriv2_nonneg hqDifferentiable hqDerivDifferentiable hqSecondNonneg
  have hslope := hconvex.le_slope_of_hasDerivAt
    (Set.mem_univ (0 : ℝ)) (Set.mem_univ (1 : ℝ)) (by norm_num : (0 : ℝ) < 1) (hq 0)
  have hq0 : q 0 = -f 0 := by dsimp [q]; ring
  have hq1 : q 1 = C / 2 - f 1 := by dsimp [q]; ring
  have hqPrime0 : q' 0 = -f' 0 := by dsimp [q']; ring
  rw [slope_def_field, hq0, hq1, hqPrime0] at hslope
  norm_num at hslope
  linarith

def meanCurvatureBound {n m : ℕ} (mu : ℝ) (differences : Fin n → Fin m → ℝ) : ℝ :=
  mu + (∑ i, squaredEuclideanNorm (differences i)) / (4 * (n : ℝ))

/-- The upper Taylor inequality is derived for the stated real ranker objective. -/
theorem realObjective_taylor_upper {n m : ℕ} (hn : 0 < n) (mu : ℝ)
    (differences : Fin n → Fin m → ℝ) (w v : Fin m → ℝ) :
    realObjective mu differences (lineShift w v 1) ≤ realObjective mu differences w +
      dot (realCoordinateGradient mu differences w) v +
      (meanCurvatureBound mu differences / 2) * squaredEuclideanNorm v := by
  have hbound : ∀ t, candidateHessianQuad mu (lineShift w v t) differences v ≤
      meanCurvatureBound mu differences * squaredEuclideanNorm v := by
    intro t
    exact (candidateHessianQuad_bounds hn mu (lineShift w v t) differences v).2
  have htaylor := scalar_taylor_unit_upper
    (meanCurvatureBound mu differences * squaredEuclideanNorm v)
    (hasDerivAt_realObjectiveLine mu differences w v)
    (hasDerivAt_lineFirstDerivative mu differences w v) hbound
  calc
    _ ≤ realObjective mu differences w + dot (realCoordinateGradient mu differences w) v +
        (meanCurvatureBound mu differences * squaredEuclideanNorm v) / 2 := by
      simpa only [realObjectiveLine, lineShift_zero,
        lineFirstDerivative_zero_eq_dot_gradient] using htaylor
    _ = _ := by ring

def realGradientStep {n m : ℕ} (mu eta : ℝ) (differences : Fin n → Fin m → ℝ)
    (w : Fin m → ℝ) : Fin m → ℝ :=
  fun j => w j - eta * realCoordinateGradient mu differences w j

/-- Exact-real one-step bound. No step-size premise is needed for this formula. -/
theorem realGradientStep_descent {n m : ℕ} (hn : 0 < n) (mu eta : ℝ)
    (differences : Fin n → Fin m → ℝ) (w : Fin m → ℝ) :
    realObjective mu differences (realGradientStep mu eta differences w) ≤
      realObjective mu differences w -
        eta * (1 - eta * meanCurvatureBound mu differences / 2) *
          squaredEuclideanNorm (realCoordinateGradient mu differences w) := by
  let g := realCoordinateGradient mu differences w
  let v : Fin m → ℝ := fun j => (-eta) * g j
  have hpoint : lineShift w v 1 = realGradientStep mu eta differences w := by
    funext j
    dsimp [lineShift, v, realGradientStep, g]
    ring
  have hdot : dot g v = (-eta) * squaredEuclideanNorm g := by
    exact (dot_const_mul_right g g (-eta)).trans
      (congrArg (fun r : ℝ => (-eta) * r) (dot_self_eq_squaredEuclideanNorm g))
  have hnorm : squaredEuclideanNorm v = eta ^ 2 * squaredEuclideanNorm g := by
    dsimp [v]
    rw [squaredEuclideanNorm_const_mul]
    ring
  have htaylor := realObjective_taylor_upper hn mu differences w v
  rw [hpoint] at htaylor
  change realObjective mu differences (realGradientStep mu eta differences w) ≤
    realObjective mu differences w + dot g v +
      (meanCurvatureBound mu differences / 2) * squaredEuclideanNorm v at htaylor
  rw [hdot, hnorm] at htaylor
  calc
    _ ≤ realObjective mu differences w + (-eta) * squaredEuclideanNorm g +
        (meanCurvatureBound mu differences / 2) * (eta ^ 2 * squaredEuclideanNorm g) := htaylor
    _ = _ := by dsimp [g]; ring

theorem meanCurvatureBound_pos {n m : ℕ} (hn : 0 < n) {mu : ℝ} (hmu : 0 < mu)
    (differences : Fin n → Fin m → ℝ) : 0 < meanCurvatureBound mu differences := by
  have hnReal : (0 : ℝ) < (n : ℝ) := Nat.cast_pos.mpr hn
  have hsum : 0 ≤ ∑ i, squaredEuclideanNorm (differences i) :=
    Finset.sum_nonneg (fun i _ => squaredEuclideanNorm_nonneg (differences i))
  have hmean : 0 ≤ (∑ i, squaredEuclideanNorm (differences i)) / (4 * (n : ℝ)) :=
    div_nonneg hsum (mul_pos (by norm_num) hnReal).le
  unfold meanCurvatureBound
  linarith

/-- A positive native-mu embedding and eta <= 1/L give a genuine real decrease. -/
theorem realGradientStep_safe_descent {n m : ℕ} (hn : 0 < n) {mu eta : ℝ}
    (hmu : 0 < mu) (heta : 0 ≤ eta) (differences : Fin n → Fin m → ℝ)
    (hstep : eta ≤ 1 / meanCurvatureBound mu differences) (w : Fin m → ℝ) :
    realObjective mu differences (realGradientStep mu eta differences w) ≤
      realObjective mu differences w - (eta / 2) *
        squaredEuclideanNorm (realCoordinateGradient mu differences w) := by
  have hL := meanCurvatureBound_pos hn hmu differences
  have hetaL : eta * meanCurvatureBound mu differences ≤ 1 :=
    (le_div_iff₀ hL).mp hstep
  have hhalf : (1 / 2 : ℝ) ≤ 1 - eta * meanCurvatureBound mu differences / 2 := by
    linarith
  have hfactor := mul_le_mul_of_nonneg_left hhalf heta
  have hproduct := mul_le_mul_of_nonneg_right hfactor
    (squaredEuclideanNorm_nonneg (realCoordinateGradient mu differences w))
  have hdescent := realGradientStep_descent hn mu eta differences w
  nlinarith

#print axioms scalar_taylor_unit_upper
#print axioms realObjective_taylor_upper
#print axioms realGradientStep_descent
#print axioms realGradientStep_safe_descent

end

end RankerRealCurvature

#print axioms _root_.RankerRealCurvature.scalar_taylor_unit_upper
#print axioms _root_.RankerRealCurvature.realGradientStep_safe_descent
