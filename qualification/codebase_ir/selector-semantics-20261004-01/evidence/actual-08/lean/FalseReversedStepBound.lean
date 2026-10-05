import Std
set_option autoImplicit false
namespace RankerStepPrerequisites
-- Exact rational checks only; no logistic calculus or binary64 convergence theorem.
noncomputable def mu : Rat := ((5764607523034235 : Rat) / 576460752303423488)
noncomputable def eta : Rat := ((1825681634788183 : Rat) / 4503599627370496)
noncomputable def conditionalSmoothness : Rat := ((6456113532727304764308018601938259 : Rat) / 10384593717069655257060992658440192)
noncomputable def q : Rat := ((2585624091180848413821180482165043 : Rat) / 2596148429267413814265248164610048)
theorem exact_positive_safe_step :
    0 < mu ∧ 0 < eta ∧ eta * conditionalSmoothness ≤ 1 ∧
    q = 1 - mu * eta ∧ 0 ≤ q ∧ q < 1 := by decide +kernel
end RankerStepPrerequisites

namespace RankerStepPrerequisites
theorem false_reversed_step_bound : 1 < eta * conditionalSmoothness := by
  change Rat.blt (1 : Rat) (eta * conditionalSmoothness) = true
  have hfalse : Rat.blt (1 : Rat) (eta * conditionalSmoothness) = false :=
    exact_positive_safe_step.2.2.1
  rw [hfalse]
  decide
end RankerStepPrerequisites
