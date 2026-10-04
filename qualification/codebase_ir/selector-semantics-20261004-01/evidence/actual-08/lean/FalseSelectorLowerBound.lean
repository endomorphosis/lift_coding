import Init
set_option autoImplicit false
namespace BatchingSelector
-- None models the IndexError of indexing an empty representative list.
noncomputable def sourceLoop (s : Int) (fallback : Option Int) : List Int → Option Int
  | [] => fallback
  | r :: rs => if s ≤ r then some r else sourceLoop s fallback rs
noncomputable def sourceSemantics (rs : List Int) (s : Int) : Option Int :=
  sourceLoop s rs.getLast? rs
noncomputable def irSemantics (rs : List Int) (s : Int) : Option Int :=
  match rs.find? (fun r => decide (s ≤ r)) with
  | some r => some r
  | none => rs.getLast?
theorem loop_correspondence (rs : List Int) (s : Int) (fallback : Option Int) :
    sourceLoop s fallback rs =
      (match rs.find? (fun r => decide (s ≤ r)) with
       | some r => some r | none => fallback) := by
  induction rs with
  | nil => simp [sourceLoop]
  | cons r rs ih =>
    by_cases h : s ≤ r <;> simp [sourceLoop, List.find?, h, ih]
theorem source_to_ir (rs : List Int) (s : Int) :
    sourceSemantics rs s = irSemantics rs s := by
  exact loop_correspondence rs s rs.getLast?
theorem output_membership (rs : List Int) (s v : Int)
    (h : irSemantics rs s = some v) : v ∈ rs := by
  unfold irSemantics at h
  cases hf : rs.find? (fun r => decide (s ≤ r)) with
  | none => simp only [hf] at h; exact List.mem_of_getLast? h
  | some r =>
    simp only [hf, Option.some.injEq] at h
    subst v
    exact List.mem_of_find?_eq_some hf
theorem first_eligible (rs : List Int) (s v : Int)
    (h : rs.find? (fun r => decide (s ≤ r)) = some v) :
    s ≤ v ∧ ∃ before after, rs = before ++ v :: after ∧
      ∀ r ∈ before, r < s := by
  have result := List.find?_eq_some_iff_append.mp h
  simpa using result
theorem no_eligible_fallback (rs : List Int) (s : Int)
    (h : ∀ r ∈ rs, r < s) : irSemantics rs s = rs.getLast? := by
  have hf : rs.find? (fun r => decide (s ≤ r)) = none := by
    simp only [List.find?_eq_none, Bool.not_eq_true, decide_eq_false_iff_not]
    intro r hr
    exact Int.not_le.mpr (h r hr)
  simp [irSemantics, hf]
theorem empty_index_error (s : Int) : sourceSemantics [] s = none := by
  simp [sourceSemantics, sourceLoop]
-- Deliberately does not assert unconditional coverage: the fallback can be small.
theorem unconditional_coverage_counterexample : sourceSemantics [1] 2 = some 1 := by
  decide +kernel
end BatchingSelector

namespace BatchingSelector
theorem false_unconditional_lower_bound : sourceSemantics [1] 2 = some 1 ∧ (2 : Int) ≤ 1 := by decide
end BatchingSelector
