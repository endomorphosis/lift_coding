  intros Hup Hinit
  exists updatedStates σ ks' vs'
  have := UpdateStatesDefined Hup
  have Hlen1 := InitStatesLength Hinit
  have Hlen2 := UpdateStatesLength Hup
  induction Hup
  ·
    simp_all [InitStatesUpdated Hinit]
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
        . have := UpdateStateDefined' Hup
          simp_all [isDefined, Option.isSome]
          split at this
          all_goals simp_all
          next val heq =>
          apply updatedStateUpdate
          apply InitStatesSomeMonotone heq
          exact updatedStatesInit Hlen1
            (UpdateStateNotDefMonotone' (UpdateStatesNotDefMonotone' (InitStatesNotDefined Hinit) Hups) Hup)
            $ InitStatesNodup Hinit
        . simp_all [List.unzip_zip]
          have := InitStatesNotDefined Hinit
          intros Hin
          simp_all [isNotDefined, isDefined]
      . exact (ih Hinit (UpdateStatesDefined Hups) $ by simp_all).2.2
