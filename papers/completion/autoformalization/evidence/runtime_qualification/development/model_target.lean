variable (Protected Approved Write : Prop)
theorem AF027_dev_q1
    (guard : Protected → ¬ Approved → ¬ Write)
    (hP : Protected) (hA : ¬ Approved) : ¬ Write :=
  guard hP hA
