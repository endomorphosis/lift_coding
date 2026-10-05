"""Generate exact Rat obligations from an already qualified numeric binding."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main():
    input_path = ROOT / "evidence/numeric-01/numeric-binding.json"
    raw = input_path.read_bytes(); body = json.loads(raw)
    canon = lambda value: json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    assert hashlib.sha256(canon({key: value for key, value in body.items() if key != "numeric_binding_sha256"})).hexdigest() == body["numeric_binding_sha256"]
    assert body["candidate_curvature_numeric_inequalities_checked"] is True
    assert body["pair_count"] == 4 and body["dimension"] == 80
    def rat(value):
        numerator, denominator = value["numerator"], value["denominator"]
        assert int(denominator) > 0
        if denominator == "1": return "(" + numerator + " : Rat)"
        return "((" + numerator + " : Rat) / " + denominator + ")"
    rows = body["pair_difference_coordinates_exact"]
    assert len(rows) == 4 and all(len(row) == 80 for row in rows)
    matrix = "[" + ",\n  ".join("[" + ", ".join(map(rat, row)) + "]" for row in rows) + "]"
    norms = "[" + ", ".join(map(rat, body["pair_squared_norms_exact"])) + "]"
    source = f'''import Std
/- Exact Rat statements for all 320 embedded stored binary64 coordinates.
Numeric binding complete file SHA256: {hashlib.sha256(raw).hexdigest()}
This does not formalize Python Float conversion or prove Float/libm errors. -/
set_option maxRecDepth 8192
namespace OriginalRankerCurvatureArithmetic
noncomputable def differences : List (List Rat) := {matrix}
noncomputable def squaredNorms : List Rat := {norms}
noncomputable def mu : Rat := {rat(body["native_mu_exact"])}
noncomputable def eta : Rat := {rat(body["native_eta_exact"])}
noncomputable def maxSquaredNorm : Rat := {rat(body["maximum_pair_squared_norm_exact"])}
noncomputable def meanL : Rat := {rat(body["mean_curvature_L_exact"])}
noncomputable def conservativeL : Rat := {rat(body["conservative_curvature_L_exact"])}
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
'''
    output = ROOT / "math/OriginalNumericCurvature.lean"
    with output.open("x") as stream: stream.write(source)
    (ROOT / "math/numeric-source-mapping.json").write_text(json.dumps({
        "schema": "terminal-ranker-exact-numeric-lean-mapping@1",
        "numeric_binding_raw_sha256": hashlib.sha256(raw).hexdigest(),
        "numeric_binding_sha256": body["numeric_binding_sha256"],
        "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
        "matrix_coordinates": 320, "native_fit_calls": 0, "numeric_norm_folds_here": 0,
        "kernel_scope": "Exact Rat matrix norm equalities and scalar inequalities; no Float conversion/error semantics",
        "real_objective_optimizer_convergence": False, "planner_activation": False
    }, indent=2) + "\n")
    print(json.dumps({"source_bytes": len(source.encode()), "source_sha256": hashlib.sha256(source.encode()).hexdigest()}))


if __name__ == "__main__": main()
