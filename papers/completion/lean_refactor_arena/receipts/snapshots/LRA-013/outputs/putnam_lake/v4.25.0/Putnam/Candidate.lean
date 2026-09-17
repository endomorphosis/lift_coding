/-
  LRA Putnam candidate module.

  The compile worker overwrites this file with header + statement +
  tactic block via splice.lake_candidate_source. This is a module in
  the per-tag Mathlib+Aesop lake project, not Tmp.lean, and not
  `lake env lean Tmp.lean` without a lakefile.
-/

theorem lra_putnam_candidate_placeholder : True := by
  trivial
