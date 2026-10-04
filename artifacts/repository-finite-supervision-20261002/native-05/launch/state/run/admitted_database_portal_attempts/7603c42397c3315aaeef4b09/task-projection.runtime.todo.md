# Database attempt projection (non-authoritative)

## LOCAL-TASK Under python-integer-offset-finite@1, calc.py::increment(n) must return an exact int for inputs [-2,-1,0,1,2]. Under python-integer-offset-finite@1, calc.py::increment(n) must return n + 2 for inputs [-2,-1,0,1,2].

- Status: completed
- Completion: auto
- Priority: P2
- Track: implementation
- Depends on:
- Outputs: calc.py
- Validation: python3 -B public_check.py
- Acceptance: Under python-integer-offset-finite@1, calc.py::increment(n) must return an exact int for inputs [-2,-1,0,1,2]. Under python-integer-offset-finite@1, calc.py::increment(n) must return n + 2 for inputs [-2,-1,0,1,2].
- Database task CID: baguqeerawg7xd7s7btu45gngmalvmg3lnx46dcshvk2zvzokvi6lfnzhijnq
- Database attempt ID: attempt:22594806dffa4748a99eb4f9f453f635
- Database claim ID: claim:b42b55f599734a03897d4d1b8bea4bba
- Database attempt number: 1
- Database lease ID: lease:2c1b9e344a22417b9833358c196fe49e
- Database owner session ID: embedded-store:310423f8e0a2d013b4b3d4ee2bba1157
- Database fencing token: 1
- Database fence epoch: 1
- Database dependency CIDs: 
- Projection authority: false
- Board namespace: intent
- Local planning contract CID: baguqeera5erk6mo4ogvsav73ldshzc5noikl27nxwaawadb2wspxsuu4sswq
- Completion Receipt: {"admitted_from_revision":2,"attempt_execution_phase":"claimed","attempt_execution_revision":1,"attempt_id":"attempt:22594806dffa4748a99eb4f9f453f635","attempt_number":1,"claim_id":"claim:b42b55f599734a03897d4d1b8bea4bba","claim_phase_schema":"ipfs_accelerate_py/agent-supervisor/typed-database-attempt-admission@1","claim_process_attestation":{"boot_id":"f4a3b80a-e3df-4702-8d03-86c19f69b2a9","client_id":"database-implementation-daemon:admitted-d8b0c3dd0d674851831b6090d4408e92","grant_id":"owner-grant:48a48e43-0b87-4ad4-8cb7-943cd33bdf42","parent_pid":181717,"pid":182402,"process_birth_id":"birth:70a26b31028dfa2aeb3be4a025e294e9","schema":"ipfs_accelerate_py/agent-supervisor/typed-database-claim-process@1","start_time_ticks":148737223,"uid":1000},"claimed_from_revision":1,"execution_route_binding":{"execution_mode":"grok-codex","plan_root_cid":"baguqeeraywulnxcbofp6d5rwlbqrwsyzvfyphhjae22c4xido4qksfu5bmoq","policy_id":"baguqeeralcinep6274vjya7qqa73t4y57ue52pleox6suv2clgwmdphrepaq","repository_tree_id":"baguqeeradnm3svurcbedwnyu5m6xipuxjbx7kfyxx2sqxdtofadh34srpwlq","schema":"ipfs_accelerate_py/agent-supervisor/task-execution-route-binding@1","source_revision":1,"task_alias":"LOCAL-TASK","task_cid":"baguqeerawg7xd7s7btu45gngmalvmg3lnx46dcshvk2zvzokvi6lfnzhijnq","task_contract_cid":"baguqeerahzefjo4v2uwcwbtava35f3s52362tul4itavx7ct2vapscexlp5a","task_revision":1},"execution_route_origin_revision":1,"execution_route_policy_id":"baguqeeralcinep6274vjya7qqa73t4y57ue52pleox6suv2clgwmdphrepaq","fence_epoch":1,"fencing_token":1,"idle_lane_work_stealing":"","lease_id":"lease:2c1b9e344a22417b9833358c196fe49e","operation":"database_attempt_admitted","owner_session_id":"embedded-store:310423f8e0a2d013b4b3d4ee2bba1157","strict_task_sharding":true,"task_prefix":"","task_shard_count":1,"task_shard_index":0}
- Title: Under python-integer-offset-finite@1, calc.py::increment(n) must return an exact int for inputs [-2,-1,0,1,2]. Under python-integer-offset-finite@1, calc.py::increment(n) must return n + 2 for inputs [-2,-1,0,1,2].
