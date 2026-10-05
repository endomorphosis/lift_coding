import RealMinimumGrowth
import RealGapContraction
import Mathlib.Analysis.Real.Sqrt
import Mathlib.Topology.Constructions

set_option backward.isDefEq.respectTransparency false

/-!
Convergence for the stated original exact-real model, with minimizer existence,
uniqueness, stationarity, gap contraction and quadratic growth supplied by
independently checked preceding modules. No native Float convergence or Python
source semantics are supplied by this mathematical projection.
-/

namespace RankerRealCurvature

noncomputable section

open Filter
open scoped BigOperators Topology

theorem originalReal_iterate_squared_distance_rate (w0 z : Fin 80 → ℝ)
    (hmin : ∀ w : Fin 80 → ℝ,
      realObjective originalRealMu originalRealDifferences z ≤
        realObjective originalRealMu originalRealDifferences w) (k : ℕ) :
    squaredEuclideanNorm (fun j => originalRealIterate w0 k j - z j) ≤
      (originalRealRho ^ k * originalRealGap w0 z) / (originalRealMu / 2) := by
  have hcoef : 0 < originalRealMu / 2 := div_pos originalReal_mu_pos (by norm_num)
  have hgrowth := originalReal_quadratic_growth_at_minimum z (originalRealIterate w0 k) hmin
  have hbound : squaredEuclideanNorm (fun j => originalRealIterate w0 k j - z j) ≤
      originalRealGap (originalRealIterate w0 k) z / (originalRealMu / 2) := by
    apply (le_div_iff₀ hcoef).mpr
    simpa only [originalRealGap, mul_comm] using hgrowth
  exact hbound.trans (div_le_div_of_nonneg_right
    (originalReal_iterate_gap_le w0 z k) hcoef.le)

theorem originalReal_iterate_weights_tendsto (w0 z : Fin 80 → ℝ)
    (hmin : ∀ w : Fin 80 → ℝ,
      realObjective originalRealMu originalRealDifferences z ≤
        realObjective originalRealMu originalRealDifferences w) :
    Tendsto (originalRealIterate w0) atTop (𝓝 z) := by
  have hcoef : 0 < originalRealMu / 2 := div_pos originalReal_mu_pos (by norm_num)
  have hgap := originalReal_iterate_gap_tendsto_zero w0 z hmin
  have hupper : Tendsto
      (fun k => originalRealGap (originalRealIterate w0 k) z / (originalRealMu / 2))
      atTop (𝓝 (0 : ℝ)) := by
    simpa only [zero_div] using hgap.div_const (originalRealMu / 2)
  apply tendsto_pi_nhds.mpr
  intro j
  have hzero : Tendsto (fun _ : ℕ => (0 : ℝ)) atTop (𝓝 (0 : ℝ)) :=
    tendsto_const_nhds
  have hsquare : Tendsto (fun k => (originalRealIterate w0 k j - z j) ^ 2)
      atTop (𝓝 (0 : ℝ)) := by
    apply tendsto_of_tendsto_of_tendsto_of_le_of_le hzero hupper
    · intro k
      exact sq_nonneg _
    · intro k
      have hgrowth := originalReal_quadratic_growth_at_minimum z (originalRealIterate w0 k) hmin
      have hbound : squaredEuclideanNorm (fun i => originalRealIterate w0 k i - z i) ≤
          originalRealGap (originalRealIterate w0 k) z / (originalRealMu / 2) := by
        apply (le_div_iff₀ hcoef).mpr
        simpa only [originalRealGap, mul_comm] using hgrowth
      have hcoordinate : (originalRealIterate w0 k j - z j) ^ 2 ≤
          squaredEuclideanNorm (fun i => originalRealIterate w0 k i - z i) := by
        unfold squaredEuclideanNorm
        exact Finset.single_le_sum (fun i _ => sq_nonneg _) (Finset.mem_univ j)
      exact hcoordinate.trans hbound
  have habs : Tendsto (fun k => |originalRealIterate w0 k j - z j|)
      atTop (𝓝 (0 : ℝ)) := by
    simpa only [Real.sqrt_sq_eq_abs, Real.sqrt_zero] using hsquare.sqrt
  have hdelta : Tendsto (fun k => originalRealIterate w0 k j - z j)
      atTop (𝓝 (0 : ℝ)) := by
    apply tendsto_zero_iff_norm_tendsto_zero.mpr
    simpa only [Real.norm_eq_abs] using habs
  simpa only [sub_add_cancel, zero_add] using hdelta.add_const (z j)

/-- No minimizer, contraction, or convergence premise: every initial real vector converges. -/
theorem originalReal_model_converges :
    ∃! z : Fin 80 → ℝ,
      (∀ w : Fin 80 → ℝ,
        realObjective originalRealMu originalRealDifferences z ≤
          realObjective originalRealMu originalRealDifferences w) ∧
      (∀ w0 : Fin 80 → ℝ,
        Tendsto (originalRealIterate w0) atTop (𝓝 z) ∧
        Tendsto
          (fun k => realObjective originalRealMu originalRealDifferences (originalRealIterate w0 k))
          atTop (𝓝 (realObjective originalRealMu originalRealDifferences z))) := by
  obtain ⟨z, hz, hunique⟩ := originalReal_exists_unique_global_minimizer
  refine ⟨z, ?_, ?_⟩
  · refine ⟨hz, ?_⟩
    intro w0
    exact ⟨originalReal_iterate_weights_tendsto w0 z hz,
      originalReal_iterate_objective_tendsto w0 z hz⟩
  · intro y hy
    exact hunique y hy.1

#print axioms originalReal_iterate_squared_distance_rate
#print axioms originalReal_iterate_weights_tendsto
#print axioms originalReal_model_converges

end

end RankerRealCurvature
