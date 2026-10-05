import Std
/- Exact Rat statements for all 320 embedded stored binary64 coordinates.
Numeric binding complete file SHA256: 2e4a8aaf11e484b4bb8e7d63c993eb955e4f26a7183c3d5cb32fed6290bd8274
This does not formalize Python Float conversion or prove Float/libm errors. -/
set_option maxRecDepth 8192
namespace OriginalRankerCurvatureArithmetic
noncomputable def differences : List (List Rat) := [[(0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (1 : Rat), (0 : Rat), (-1 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), ((4803839602528529 : Rat) / 72057594037927936), ((1973005551038503 : Rat) / 9007199254740992), ((4721014781795279 : Rat) / 72057594037927936), ((8297541131640187 : Rat) / 144115188075855872), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), ((3234963721715497 : Rat) / 9007199254740992), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), ((8395706907568733 : Rat) / 36028797018963968), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), ((230166756163373 : Rat) / 4503599627370496)],
  [(0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (1 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), ((4803839602528529 : Rat) / 36028797018963968), ((2573485501354569 : Rat) / 9007199254740992), ((3602879701896397 : Rat) / 36028797018963968), ((3275345183542179 : Rat) / 36028797018963968), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), ((-100894948723717 : Rat) / 562949953421312), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), ((-2780997711572603 : Rat) / 36028797018963968), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), ((-2780997711572603 : Rat) / 36028797018963968)],
  [(0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (1 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), ((1385722962267845 : Rat) / 18014398509481984), ((3602879701896397 : Rat) / 18014398509481984), ((4238682002231055 : Rat) / 72057594037927936), ((2001599834386887 : Rat) / 36028797018963968), (0 : Rat), (0 : Rat), (0 : Rat), ((-2807354597998065 : Rat) / 18014398509481984), (0 : Rat), ((100894948723717 : Rat) / 562949953421312), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), ((2780997711572603 : Rat) / 36028797018963968), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), ((2780997711572603 : Rat) / 36028797018963968)],
  [(0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (1 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (-1 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), ((2401919801264265 : Rat) / 18014398509481984), ((1569882223048539 : Rat) / 72057594037927936), ((1429714167419205 : Rat) / 72057594037927936), (0 : Rat), (0 : Rat), (0 : Rat), ((-1441525858802457 : Rat) / 9007199254740992), (0 : Rat), ((4849282901294969 : Rat) / 9007199254740992), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), ((1397088077392667 : Rat) / 4503599627370496), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), (0 : Rat), ((4622331760879587 : Rat) / 36028797018963968)]]
noncomputable def squaredNorms : List Rat := [((46646319711462335500654408216079793 : Rat) / 20769187434139310514121985316880384), ((1507989278949607563828642550842453 : Rat) / 1298074214633706907132624082305024), ((5819461529695142022881884510840989 : Rat) / 5192296858534827628530496329220096), ((6352267595556608209575680854216019 : Rat) / 2596148429267413814265248164610048)]
noncomputable def mu : Rat := ((5764607523034235 : Rat) / 576460752303423488)
noncomputable def eta : Rat := ((1825681634788183 : Rat) / 4503599627370496)
noncomputable def maxSquaredNorm : Rat := ((6352267595556608209575680854216019 : Rat) / 2596148429267413814265248164610048)
noncomputable def meanL : Rat := ((148193205047351780041480481833762829 : Rat) / 332306998946228968225951765070086144)
noncomputable def conservativeL : Rat := ((6456113532727304764308018601938259 : Rat) / 10384593717069655257060992658440192)
def squaredNorm (row : List Rat) : Rat := row.foldl (fun acc x => acc + x*x) 0
theorem original_norms_exact : differences.map squaredNorm = squaredNorms := by
  decide +kernel
theorem original_shape : differences.length = 4 ∧ differences.all (fun row => row.length == 80) = true := by
  decide +kernel
theorem original_positive_scalars : 0 < mu ∧ 0 < eta := by
  decide +kernel
theorem original_mean_bound : meanL = mu + squaredNorms.foldl (fun acc x => acc+x) 0 / 16 := by
  decide +kernel
theorem original_conservative_bound : conservativeL = mu + maxSquaredNorm / 4 ∧
    squaredNorms.all (fun value => decide (value ≤ maxSquaredNorm)) = true := by
  decide +kernel
theorem original_safe_steps : eta * meanL ≤ 1 ∧ eta * conservativeL ≤ 1 := by
  decide +kernel
end OriginalRankerCurvatureArithmetic

#print axioms _root_.OriginalRankerCurvatureArithmetic.original_norms_exact
#print axioms _root_.OriginalRankerCurvatureArithmetic.original_shape
#print axioms _root_.OriginalRankerCurvatureArithmetic.original_positive_scalars
#print axioms _root_.OriginalRankerCurvatureArithmetic.original_mean_bound
#print axioms _root_.OriginalRankerCurvatureArithmetic.original_conservative_bound
#print axioms _root_.OriginalRankerCurvatureArithmetic.original_safe_steps
