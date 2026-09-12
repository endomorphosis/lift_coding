# Development scoring trust profile

The host service separates model proposal generation from cold test execution.
The model receives the pinned public development request. Private oracle material
is supplied only to the later scoring process, after the candidate is sealed.
This establishes a boundary between proposal generation and scoring.

It does not establish resistance to malicious candidate interference with the
Python test harness. Source review found that candidate Python executes within a
scoring environment that also contains test metadata and writable observation
outputs. The current mechanism therefore requires a trusted candidate-admission
step; observation hashes alone do not authenticate the meaning of test outcomes.

No adversarial bypass demonstration was executed. Automatic security review
stopped the planned demonstration after flagging a possible cybersecurity risk.
The finding is retained as source-review evidence, with no claimed experimental
attack result or measured false-admission rate.

For the first historical development qualification, the host must seal the
candidate, pause for operator review of its exact source changes, bind that
review to the grant and candidate digest, and only then run the independent cold
scorer. Resuming the scoring stage must not issue another model request. The
operator review is an AI assistant's source inspection; it is not a human
annotation, an independent semantic judgment, or a proof of arbitrary Python
behavior. Its scope and timing must remain explicit in the development receipt.

NS-011 owns cold-versus-reuse qualification, explicit denominators and the
required dependency-mutation cases. Unavailable or unperformed cases cannot count
as safe agreement. NS-016 must freeze the supported trust profile and any claim
exclusions before final outcomes. Neither task may infer adversarial scorer
integrity from this development run, ordinary passing tests, or the protected
proposal-generation boundary. The existing task criteria and final protocol
requirements remain unchanged.
