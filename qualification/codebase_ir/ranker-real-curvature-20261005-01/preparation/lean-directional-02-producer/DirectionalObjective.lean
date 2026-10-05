import ScalarSoftplus
import Mathlib.Analysis.Calculus.Deriv.Add
import Mathlib.Analysis.Calculus.Deriv.Mul
import Mathlib.Analysis.Calculus.Deriv.Pow

set_option backward.isDefEq.respectTransparency false

/-!
Second directional derivative of the actual stated real finite-pair objective.
This establishes the real quadratic identity by calculus along w + t*v; it does
not assume a Hessian bound/identity, or prove Python/binary64 source semantics.
No operator-valued Frechet Hessian or global iteration theorem is claimed here.
-/

namespace RankerRealCurvature

noncomputable section

open scoped BigOperators

def lineShift {m : ℕ} (w v : Fin m → ℝ) (t : ℝ) : Fin m → ℝ :=
  fun j => w j + t * v j

def realObjective {n m : ℕ} (mu : ℝ) (differences : Fin n → Fin m → ℝ)
    (w : Fin m → ℝ) : ℝ :=
  (mu / 2) * squaredEuclideanNorm w +
    (1 / (n : ℝ)) * ∑ i, realPairLoss (dot w (differences i))

def realStableObjective {n m : ℕ} (mu : ℝ) (differences : Fin n → Fin m → ℝ)
    (w : Fin m → ℝ) : ℝ :=
  (mu / 2) * squaredEuclideanNorm w +
    (1 / (n : ℝ)) * ∑ i, realStablePairLoss (dot w (differences i))

theorem realStableObjective_eq {n m : ℕ} (mu : ℝ)
    (differences : Fin n → Fin m → ℝ) (w : Fin m → ℝ) :
    realStableObjective mu differences w = realObjective mu differences w := by
  simp only [realStableObjective, realObjective, realStablePairLoss_eq]

def realObjectiveLine {n m : ℕ} (mu : ℝ) (differences : Fin n → Fin m → ℝ)
    (w v : Fin m → ℝ) (t : ℝ) : ℝ :=
  realObjective mu differences (lineShift w v t)

def lineFirstDerivative {n m : ℕ} (mu : ℝ) (differences : Fin n → Fin m → ℝ)
    (w v : Fin m → ℝ) (t : ℝ) : ℝ :=
  mu * dot (lineShift w v t) v -
    (1 / (n : ℝ)) * ∑ i,
      realLogisticP (dot (lineShift w v t) (differences i)) * dot v (differences i)

theorem dot_self_eq_squaredEuclideanNorm {m : ℕ} (v : Fin m → ℝ) :
    dot v v = squaredEuclideanNorm v := by
  simp only [dot, squaredEuclideanNorm, pow_two]

theorem hasDerivAt_lineShift_coordinate {m : ℕ} (w v : Fin m → ℝ)
    (j : Fin m) (t : ℝ) :
    HasDerivAt (fun s => lineShift w v s j) (v j) t := by
  simpa only [lineShift, one_mul] using
    ((hasDerivAt_id' t).mul_const (v j)).const_add (w j)

theorem hasDerivAt_dot_lineShift {m : ℕ} (w v d : Fin m → ℝ) (t : ℝ) :
    HasDerivAt (fun s => dot (lineShift w v s) d) (dot v d) t := by
  simpa only [dot] using
    (HasDerivAt.fun_sum (u := (Finset.univ : Finset (Fin m)))
      (fun j _ => (hasDerivAt_lineShift_coordinate w v j t).mul_const (d j)))

theorem hasDerivAt_regularizerLine {m : ℕ} (mu : ℝ) (w v : Fin m → ℝ) (t : ℝ) :
    HasDerivAt (fun s => (mu / 2) * squaredEuclideanNorm (lineShift w v s))
      (mu * dot (lineShift w v t) v) t := by
  have hnorm : HasDerivAt (fun s => squaredEuclideanNorm (lineShift w v s))
      (∑ j, (2 : ℝ) * (lineShift w v t j) * v j) t := by
    simpa only [squaredEuclideanNorm, Pi.pow_apply, Nat.cast_ofNat, Nat.reduceSub, pow_one] using
      (HasDerivAt.fun_sum (u := (Finset.univ : Finset (Fin m)))
        (fun j _ => (hasDerivAt_lineShift_coordinate w v j t).pow 2))
  apply (hnorm.const_mul (mu / 2)).congr_deriv
  simp only [dot, Finset.mul_sum]
  apply Finset.sum_congr rfl
  intro j _
  ring

/-- First derivative established from polynomial and log/exp derivative rules. -/
theorem hasDerivAt_realObjectiveLine {n m : ℕ} (mu : ℝ)
    (differences : Fin n → Fin m → ℝ) (w v : Fin m → ℝ) (t : ℝ) :
    HasDerivAt (realObjectiveLine mu differences w v)
      (lineFirstDerivative mu differences w v t) t := by
  have hsum : HasDerivAt
      (fun s => ∑ i, realPairLoss (dot (lineShift w v s) (differences i)))
      (∑ i, -realLogisticP (dot (lineShift w v t) (differences i)) * dot v (differences i)) t := by
    simpa using
      (HasDerivAt.fun_sum (u := (Finset.univ : Finset (Fin n)))
        (fun i _ => (hasDerivAt_realPairLoss (dot (lineShift w v t) (differences i))).comp t
          (hasDerivAt_dot_lineShift w v (differences i) t)))
  apply ((hasDerivAt_regularizerLine mu w v t).add (hsum.const_mul (1 / (n : ℝ)))).congr_deriv
  unfold lineFirstDerivative
  simp only [neg_mul, Finset.sum_neg_distrib, mul_neg, sub_eq_add_neg]

/-- Derivative of the established first derivative is the stated candidate Q. -/
theorem hasDerivAt_lineFirstDerivative {n m : ℕ} (mu : ℝ)
    (differences : Fin n → Fin m → ℝ) (w v : Fin m → ℝ) (t : ℝ) :
    HasDerivAt (lineFirstDerivative mu differences w v)
      (candidateHessianQuad mu (lineShift w v t) differences v) t := by
  have hreg : HasDerivAt (fun s => mu * dot (lineShift w v s) v)
      (mu * squaredEuclideanNorm v) t := by
    simpa only [dot_self_eq_squaredEuclideanNorm] using
      (hasDerivAt_dot_lineShift w v v t).const_mul mu
  have hsum : HasDerivAt
      (fun s => ∑ i, realLogisticP (dot (lineShift w v s) (differences i)) * dot v (differences i))
      (∑ i, (-realLogisticCoeff (dot (lineShift w v t) (differences i)) *
        dot v (differences i)) * dot v (differences i)) t := by
    simpa using
      (HasDerivAt.fun_sum (u := (Finset.univ : Finset (Fin n)))
        (fun i _ => ((hasDerivAt_realLogisticP (dot (lineShift w v t) (differences i))).comp t
          (hasDerivAt_dot_lineShift w v (differences i) t)).mul_const (dot v (differences i))))
  have hnegative : (∑ i : Fin n,
      (-realLogisticCoeff (dot (lineShift w v t) (differences i)) *
        dot v (differences i)) * dot v (differences i)) =
      -(∑ i, realLogisticCoeff (dot (lineShift w v t) (differences i)) *
        (dot v (differences i)) ^ 2) := by
    simp only [neg_mul, mul_assoc, ← pow_two, Finset.sum_neg_distrib]
  apply (hreg.sub (hsum.const_mul (1 / (n : ℝ)))).congr_deriv
  unfold candidateHessianQuad
  rw [hnegative]
  ring

/-- Actual second derivative of the stated objective along every affine line. -/
theorem secondDeriv_realObjectiveLine {n m : ℕ} (mu : ℝ)
    (differences : Fin n → Fin m → ℝ) (w v : Fin m → ℝ) (t : ℝ) :
    deriv (deriv (realObjectiveLine mu differences w v)) t =
      candidateHessianQuad mu (lineShift w v t) differences v := by
  have hfirst : deriv (realObjectiveLine mu differences w v) =
      lineFirstDerivative mu differences w v :=
    funext (fun s => (hasDerivAt_realObjectiveLine mu differences w v s).deriv)
  rw [hfirst]
  exact (hasDerivAt_lineFirstDerivative mu differences w v t).deriv

theorem secondDeriv_realObjectiveLine_zero {n m : ℕ} (mu : ℝ)
    (differences : Fin n → Fin m → ℝ) (w v : Fin m → ℝ) :
    deriv (deriv (realObjectiveLine mu differences w v)) 0 =
      candidateHessianQuad mu w differences v := by
  have hzero : lineShift w v 0 = w := by
    funext j
    simp only [lineShift, zero_mul, add_zero]
  have h := secondDeriv_realObjectiveLine mu differences w v 0
  rw [hzero] at h
  exact h

/-- Analytic curvature bounds for the actual stated real objective, not a premise. -/
theorem actual_secondDirectional_bounds {n m : ℕ} (hn : 0 < n) (mu : ℝ)
    (differences : Fin n → Fin m → ℝ) (w v : Fin m → ℝ) :
    mu * squaredEuclideanNorm v ≤ deriv (deriv (realObjectiveLine mu differences w v)) 0 ∧
    deriv (deriv (realObjectiveLine mu differences w v)) 0 ≤
      (mu + (∑ i, squaredEuclideanNorm (differences i)) / (4 * (n : ℝ))) *
        squaredEuclideanNorm v := by
  rw [secondDeriv_realObjectiveLine_zero]
  exact candidateHessianQuad_bounds hn mu w differences v

#print axioms secondDeriv_realObjectiveLine
#print axioms actual_secondDirectional_bounds

end

end RankerRealCurvature
