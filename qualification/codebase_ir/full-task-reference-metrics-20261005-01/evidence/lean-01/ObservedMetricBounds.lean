import Std
set_option autoImplicit false
namespace AuthoredReferenceMetricBounds
-- Exact real embeddings of8 observed binary64 metrics and binary64 thresholds.
-- No cost-model semantics theorem, actual benchmark score or optimizer convergence claim.
noncomputable def observed_b1_cost : Rat := ((313580032 : Rat) / 1)
noncomputable def threshold_b1_cost : Rat := ((300000000000 : Rat) / 1)
theorem strict_b1_cost : observed_b1_cost < threshold_b1_cost := by decide +kernel
#print axioms strict_b1_cost
noncomputable def observed_b1_pad_ratio : Rat := ((0 : Rat) / 1)
noncomputable def threshold_b1_pad_ratio : Rat := ((7926335344172073 : Rat) / 144115188075855872)
theorem strict_b1_pad_ratio : observed_b1_pad_ratio < threshold_b1_pad_ratio := by decide +kernel
#print axioms strict_b1_pad_ratio
noncomputable def observed_b1_p95_latency_ms : Rat := ((428451094041985 : Rat) / 68719476736)
noncomputable def threshold_b1_p95_latency_ms : Rat := ((2100000 : Rat) / 1)
theorem strict_b1_p95_latency_ms : observed_b1_p95_latency_ms < threshold_b1_p95_latency_ms := by decide +kernel
#print axioms strict_b1_p95_latency_ms
noncomputable def observed_b1_sequential_timecost : Rat := ((287713605686657 : Rat) / 17179869184)
noncomputable def threshold_b1_sequential_timecost : Rat := ((270000000 : Rat) / 1)
theorem strict_b1_sequential_timecost : observed_b1_sequential_timecost < threshold_b1_sequential_timecost := by decide +kernel
#print axioms strict_b1_sequential_timecost
noncomputable def observed_b2_cost : Rat := ((1548802560 : Rat) / 1)
noncomputable def threshold_b2_cost : Rat := ((48000000000 : Rat) / 1)
theorem strict_b2_cost : observed_b2_cost < threshold_b2_cost := by decide +kernel
#print axioms strict_b2_cost
noncomputable def observed_b2_pad_ratio : Rat := ((0 : Rat) / 1)
noncomputable def threshold_b2_pad_ratio : Rat := ((5404319552844595 : Rat) / 36028797018963968)
theorem strict_b2_pad_ratio : observed_b2_pad_ratio < threshold_b2_pad_ratio := by decide +kernel
#print axioms strict_b2_pad_ratio
noncomputable def observed_b2_p95_latency_ms : Rat := ((7160192123500547 : Rat) / 549755813888)
noncomputable def threshold_b2_p95_latency_ms : Rat := ((210000 : Rat) / 1)
theorem strict_b2_p95_latency_ms : observed_b2_p95_latency_ms < threshold_b2_p95_latency_ms := by decide +kernel
#print axioms strict_b2_p95_latency_ms
noncomputable def observed_b2_sequential_timecost : Rat := ((5688415765275869 : Rat) / 137438953472)
noncomputable def threshold_b2_sequential_timecost : Rat := ((32000000 : Rat) / 1)
theorem strict_b2_sequential_timecost : observed_b2_sequential_timecost < threshold_b2_sequential_timecost := by decide +kernel
#print axioms strict_b2_sequential_timecost
end AuthoredReferenceMetricBounds
