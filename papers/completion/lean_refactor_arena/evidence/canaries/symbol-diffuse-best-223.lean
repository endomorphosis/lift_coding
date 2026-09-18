  intros Hup Hinit
  exists updatedStates σ ks' vs'
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
    refine ⟨rfl, ?_, ?_⟩
    . apply updatedStatesInit Hlen1
      apply UpdateStateNotDefMonotone' _ Hup
      apply UpdateStatesNotDefMonotone' _ Hups
      exact InitStatesNotDefined Hinit
      exact InitStatesNodup Hinit
    . apply UpdateStates.update_some (σ':=updatedStates σ₀ ks' vs')
      . simp [UpdateStateUpdated Hup, updatedStates]
        rw [← updatedStateComm']
        . have Hdef := UpdateStateDefined' Hup
          simp [isDefined, Option.isSome] at Hdef
          split at Hdef <;> simp_all
          next val heq =>
          apply updatedStateUpdate
          apply InitStatesSomeMonotone heq
          exact updatedStatesInit Hlen1
            (UpdateStateNotDefMonotone' (UpdateStatesNotDefMonotone' (InitStatesNotDefined Hinit) Hups) Hup)
            (InitStatesNodup Hinit)
        . rw [List.unzip_zip] <;> simp_all
          have Hnd := InitStatesNotDefined Hinit
          intros Hin
          simp_all [isNotDefined, isDefined]
      . exact (ih Hinit (by simp_all [isDefined]) (by simp_all)).2.2
