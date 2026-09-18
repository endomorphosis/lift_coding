  intros Hup Hinit
  exists (updatedStates σ ks' vs')
  have Hk := UpdateStatesDefined Hup
  have Hlen1 := InitStatesLength Hinit
  have Hlen2 := UpdateStatesLength Hup
  induction Hup
  case update_none =>
    simp_all
    constructor
    exact updatedStatesInit Hlen1 (InitStatesNotDefined Hinit) (InitStatesNodup Hinit)
    simp [InitStatesUpdated Hinit]
    constructor
  case update_some σ x v σ₀ xs vs σ₁ Hup Hups ih =>
    have Hnd := InitStatesNotDefined Hinit
    have Hst := updatedStatesInit Hlen1
      (UpdateStateNotDefMonotone' (UpdateStatesNotDefMonotone' Hnd Hups) Hup)
      (InitStatesNodup Hinit)
    refine ⟨rfl, Hst, ?_⟩
    . apply UpdateStates.update_some (σ':=updatedStates σ₀ ks' vs')
      . simp [UpdateStateUpdated Hup, updatedStates]
        rw [← updatedStateComm']
        . have := UpdateStateDefined' Hup
          simp [isDefined, Option.isSome] at this
          split at this <;> simp_all
          next val heq =>
          exact updatedStateUpdate (InitStatesSomeMonotone heq Hst)
        . rw [List.unzip_zip] <;> simp_all
          intros Hin
          simp_all [isNotDefined, isDefined]
      . exact (ih Hinit (by simp_all [isDefined]) (by simp_all)).2.2
