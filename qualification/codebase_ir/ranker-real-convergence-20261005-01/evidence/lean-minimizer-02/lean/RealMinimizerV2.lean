import RealStrongLower
import Mathlib.Topology.Order.Compact
import Mathlib.Topology.MetricSpace.Bounded
import Mathlib.Analysis.Calculus.LocalExtr.Basic

set_option backward.isDefEq.respectTransparency false

/-!
Additive candidate for a separate bounded native qualification.
The qualified strong-lower module and sealed curvature qualification are read
dependencies. Continuity and compact sublevels are proved for the actual finite
real objective. Global minimizer existence is a conclusion, never a premise.
This module proves existence; stationarity, uniqueness and convergence are separate obligations.
-/

namespace RankerRealCurvature

noncomputable section

open scoped BigOperators

/-- Finite coordinate dot products are continuous in the function-space topology. -/
theorem realDot_continuous {m : ℕ} (d : Fin m → ℝ) :
    Continuous (fun w : Fin m → ℝ => dot w d) := by
  unfold dot
  exact continuous_finsetSum Finset.univ
    (fun j _ => (continuous_apply j).mul continuous_const)

/-- The explicit Euclidean coordinate square sum is continuous. -/
theorem squaredEuclideanNorm_continuous {m : ℕ} :
    Continuous (squaredEuclideanNorm (m := m)) := by
  unfold squaredEuclideanNorm
  exact continuous_finsetSum Finset.univ
    (fun j _ => (continuous_apply j).pow 2)

/-- Direct log/exp continuity, with a positive logarithm argument at every margin. -/
theorem realPairLoss_continuous : Continuous realPairLoss := by
  unfold realPairLoss
  exact (continuous_const.add
    (Real.continuous_exp.comp continuous_id.neg)).log
    (fun margin => by
      change 1 + Real.exp (-margin) ≠ 0
      exact ne_of_gt (by linarith [Real.exp_pos (-margin)]))

/-- Continuity is derived from the finite coordinate expression of the actual objective. -/
theorem continuous_realObjective {n m : ℕ} (mu : ℝ)
    (differences : Fin n → Fin m → ℝ) :
    Continuous (realObjective mu differences) := by
  have hnorm : Continuous (fun w : Fin m → ℝ => squaredEuclideanNorm w) :=
    squaredEuclideanNorm_continuous
  have hloss : Continuous (fun w : Fin m → ℝ =>
      ∑ i, realPairLoss (dot w (differences i))) := by
    exact continuous_finsetSum Finset.univ
      (fun i _ => realPairLoss_continuous.comp (realDot_continuous (differences i)))
  unfold realObjective
  exact (continuous_const.mul hnorm).add (continuous_const.mul hloss)

/-- Positive regularization bounds every sublevel coordinate without any norm identification. -/
theorem realObjective_sublevel_coordinate_abs_le {n m : ℕ} (hn : 0 < n)
    (mu : ℝ) (hmu : 0 < mu) (differences : Fin n → Fin m → ℝ)
    (level : ℝ) (w : Fin m → ℝ)
    (hw : realObjective mu differences w ≤ level) (j : Fin m) :
    |w j| ≤ max 1 (2 * level / mu) := by
  have hregularizer := realObjective_regularizer_lower hn mu differences w
  have hsum : squaredEuclideanNorm w ≤ 2 * level / mu := by
    apply (le_div_iff₀ hmu).mpr
    nlinarith [hregularizer]
  have hcoordinate : (w j) ^ 2 ≤ squaredEuclideanNorm w := by
    unfold squaredEuclideanNorm
    exact Finset.single_le_sum (fun k _ => sq_nonneg (w k)) (Finset.mem_univ j)
  let R : ℝ := max 1 (2 * level / mu)
  have hR_one : 1 ≤ R := le_max_left _ _
  have hR_nonneg : 0 ≤ R := le_trans zero_le_one hR_one
  have hB_le_R : 2 * level / mu ≤ R := le_max_right _ _
  have hR_le_sq : R ≤ R ^ 2 := by
    have hproduct := mul_nonneg hR_nonneg (sub_nonneg.mpr hR_one)
    nlinarith [hproduct]
  have hcoordinate_sq : (w j) ^ 2 ≤ R ^ 2 :=
    hcoordinate.trans (hsum.trans (hB_le_R.trans hR_le_sq))
  exact abs_le.mpr (abs_le_of_sq_le_sq' hcoordinate_sq hR_nonneg)

/-- Each actual sublevel lies inside a compact finite-Pi coordinate interval. -/
theorem realObjective_sublevel_isBounded {n m : ℕ} (hn : 0 < n)
    (mu : ℝ) (hmu : 0 < mu) (differences : Fin n → Fin m → ℝ) (level : ℝ) :
    Bornology.IsBounded {w : Fin m → ℝ | realObjective mu differences w ≤ level} := by
  let R : ℝ := max 1 (2 * level / mu)
  have hsubset : {w : Fin m → ℝ | realObjective mu differences w ≤ level} ⊆
      Set.Icc (fun _ : Fin m => -R) (fun _ => R) := by
    intro w hw
    constructor
    · intro j
      exact (abs_le.mp
        (realObjective_sublevel_coordinate_abs_le hn mu hmu differences level w hw j)).1
    · intro j
      exact (abs_le.mp
        (realObjective_sublevel_coordinate_abs_le hn mu hmu differences level w hw j)).2
  have hbox : IsCompact (Set.Icc (fun _ : Fin m => -R) (fun _ => R)) := isCompact_Icc
  exact hbox.isBounded.subset hsubset

/-- Continuity closes the bounded sublevel, so it is compact in the finite function space. -/
theorem realObjective_sublevel_isCompact {n m : ℕ} (hn : 0 < n)
    (mu : ℝ) (hmu : 0 < mu) (differences : Fin n → Fin m → ℝ) (level : ℝ) :
    IsCompact {w : Fin m → ℝ | realObjective mu differences w ≤ level} := by
  exact Metric.isCompact_of_isClosed_isBounded
    (isClosed_le (continuous_realObjective mu differences) continuous_const)
    (realObjective_sublevel_isBounded hn mu hmu differences level)

/-- The actual positive-regularized finite real objective attains a global minimum. -/
theorem realObjective_exists_global_minimizer {n m : ℕ} (hn : 0 < n)
    (mu : ℝ) (hmu : 0 < mu) (differences : Fin n → Fin m → ℝ) :
    ∃ z : Fin m → ℝ, ∀ w, realObjective mu differences z ≤ realObjective mu differences w := by
  let w0 : Fin m → ℝ := fun _ => 0
  exact (continuous_realObjective mu differences).exists_forall_le_of_isBounded w0
    (realObjective_sublevel_isBounded hn mu hmu differences (realObjective mu differences w0))

/-- Existence specialized to the already bound original 4-pair, 80-coordinate exact-real model. -/
theorem originalReal_exists_global_minimizer :
    ∃ z : Fin 80 → ℝ, ∀ w,
      realObjective originalRealMu originalRealDifferences z ≤
        realObjective originalRealMu originalRealDifferences w := by
  exact realObjective_exists_global_minimizer (by norm_num : 0 < (4 : ℕ))
    originalRealMu originalReal_mu_pos originalRealDifferences

#print axioms realDot_continuous
#print axioms squaredEuclideanNorm_continuous
#print axioms realPairLoss_continuous
#print axioms continuous_realObjective
#print axioms realObjective_sublevel_coordinate_abs_le
#print axioms realObjective_sublevel_isBounded
#print axioms realObjective_sublevel_isCompact
#print axioms realObjective_exists_global_minimizer
#print axioms originalReal_exists_global_minimizer

end

end RankerRealCurvature

#print axioms _root_.RankerRealCurvature.realDot_continuous
#print axioms _root_.RankerRealCurvature.squaredEuclideanNorm_continuous
#print axioms _root_.RankerRealCurvature.realPairLoss_continuous
#print axioms _root_.RankerRealCurvature.continuous_realObjective
#print axioms _root_.RankerRealCurvature.realObjective_sublevel_coordinate_abs_le
#print axioms _root_.RankerRealCurvature.realObjective_sublevel_isBounded
#print axioms _root_.RankerRealCurvature.realObjective_sublevel_isCompact
#print axioms _root_.RankerRealCurvature.realObjective_exists_global_minimizer
#print axioms _root_.RankerRealCurvature.originalReal_exists_global_minimizer
