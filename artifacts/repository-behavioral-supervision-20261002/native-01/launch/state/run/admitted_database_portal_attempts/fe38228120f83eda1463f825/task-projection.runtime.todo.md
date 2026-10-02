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
- Database attempt ID: attempt:7d2f189f185b4e37ae8cbeb8f6a35ea8
- Database claim ID: claim:630380f1ade142f995089da82cb39264
- Database attempt number: 1
- Database lease ID: lease:2d723c31b8434632b665b49a2ca11859
- Database owner session ID: embedded-store:990572707923e9055a701e025f331955
- Database fencing token: 1
- Database fence epoch: 1
- Database dependency CIDs: 
- Projection authority: false
- Board namespace: intent
- Local planning contract CID: baguqeeraxlocvs54xbu4osjoipsrlbwadfyxxrusubklp65ietfxbbn5f54a
- Completion Receipt: {"admitted_from_revision":2,"attempt_execution_phase":"claimed","attempt_execution_revision":1,"attempt_id":"attempt:7d2f189f185b4e37ae8cbeb8f6a35ea8","attempt_number":1,"claim_id":"claim:630380f1ade142f995089da82cb39264","claim_phase_schema":"ipfs_accelerate_py/agent-supervisor/typed-database-attempt-admission@1","claim_process_attestation":{"boot_id":"f4a3b80a-e3df-4702-8d03-86c19f69b2a9","client_id":"database-implementation-daemon:admitted-fcd17af7f6184cd591d12b0d7e87ea36","grant_id":"owner-grant:166850b7-112e-4e4f-8879-e4098ba9884b","parent_pid":3522846,"pid":3522966,"process_birth_id":"birth:21d5a1d79a0127e10271b9913ad05194","schema":"ipfs_accelerate_py/agent-supervisor/typed-database-claim-process@1","start_time_ticks":149724050,"uid":1000},"claimed_from_revision":1,"execution_route_binding":{"execution_mode":"grok-codex","plan_root_cid":"baguqeerace4ovgpxursz624m4supyobzqxgqdutc2maofvabiio33l2b5ija","policy_id":"baguqeera46gklzm374ivwsnlch5ksv734huiux7qinhabpzuqacqyxbtt3ra","repository_tree_id":"baguqeeraoveohtbvateudyfvaogqhn6irosrehiitcnd7goeifpmriuh2fcq","schema":"ipfs_accelerate_py/agent-supervisor/task-execution-route-binding@1","source_revision":1,"task_alias":"LOCAL-TASK","task_cid":"baguqeerawg7xd7s7btu45gngmalvmg3lnx46dcshvk2zvzokvi6lfnzhijnq","task_contract_cid":"baguqeerafbpose4uxm4dcxgy7dquju6rfgqppesepvkwcjrpsgewh6yxlk6a","task_revision":1},"execution_route_origin_revision":1,"execution_route_policy_id":"baguqeera46gklzm374ivwsnlch5ksv734huiux7qinhabpzuqacqyxbtt3ra","fence_epoch":1,"fencing_token":1,"idle_lane_work_stealing":"","lease_id":"lease:2d723c31b8434632b665b49a2ca11859","operation":"database_attempt_admitted","owner_session_id":"embedded-store:990572707923e9055a701e025f331955","strict_task_sharding":true,"task_prefix":"","task_shard_count":1,"task_shard_index":0}
- Title: Under python-integer-offset-finite@1, calc.py::increment(n) must return an exact int for inputs [-2,-1,0,1,2]. Under python-integer-offset-finite@1, calc.py::increment(n) must return n + 2 for inputs [-2,-1,0,1,2].
