import LogisticCurvature

/- Intentional false control. The proved coefficient at zero is 1/4, so this
   stronger 1/8 cap must be rejected by the actual kernel checker. -/
open RankerRealCurvature

example : realLogisticCoeff 0 ≤ (1 / 8 : ℝ) := by
  norm_num [realLogisticCoeff, realLogisticP]
