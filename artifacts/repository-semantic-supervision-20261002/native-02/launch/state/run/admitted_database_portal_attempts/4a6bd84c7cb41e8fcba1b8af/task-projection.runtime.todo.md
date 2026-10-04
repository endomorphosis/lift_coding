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
- Database attempt ID: attempt:fb46e213b97b43a88ade35e560fb3783
- Database claim ID: claim:07f77c87cc6f40c69240395894a368ec
- Database attempt number: 1
- Database lease ID: lease:6581404755b146eab5546bba0610fdbd
- Database owner session ID: embedded-store:eb90e0a1eb7faacee413c6f169269950
- Database fencing token: 1
- Database fence epoch: 1
- Database dependency CIDs: 
- Projection authority: false
- Board namespace: intent
- Local planning contract CID: baguqeera4aqvhmf2665ev7hmkbb4szu7c2b3zqvqfqdqkkbe42o57nqzfjbq
- Completion Receipt: {"admitted_from_revision":2,"attempt_execution_phase":"claimed","attempt_execution_revision":1,"attempt_id":"attempt:fb46e213b97b43a88ade35e560fb3783","attempt_number":1,"claim_id":"claim:07f77c87cc6f40c69240395894a368ec","claim_phase_schema":"ipfs_accelerate_py/agent-supervisor/typed-database-attempt-admission@1","claim_process_attestation":{"boot_id":"f4a3b80a-e3df-4702-8d03-86c19f69b2a9","client_id":"database-implementation-daemon:admitted-dae3fd78f75642cda6deb485e4d27605","grant_id":"owner-grant:90615b08-5a8a-4de8-8935-d79eff87d7e9","parent_pid":1671687,"pid":1671942,"process_birth_id":"birth:1e20ec2797b55caf4afb9ee7f0312687","schema":"ipfs_accelerate_py/agent-supervisor/typed-database-claim-process@1","start_time_ticks":149166874,"uid":1000},"claimed_from_revision":1,"execution_route_binding":{"execution_mode":"grok-codex","plan_root_cid":"baguqeera3dgbzk2yjybu5xz6wwd77tazkpgert2a5iah32uipohkkyn76ivq","policy_id":"baguqeerajbdyrrmpstrui5b3qhixowle4ljsm5s35wz2mnsoox5aotye32fq","repository_tree_id":"baguqeeraoveohtbvateudyfvaogqhn6irosrehiitcnd7goeifpmriuh2fcq","schema":"ipfs_accelerate_py/agent-supervisor/task-execution-route-binding@1","source_revision":1,"task_alias":"LOCAL-TASK","task_cid":"baguqeerawg7xd7s7btu45gngmalvmg3lnx46dcshvk2zvzokvi6lfnzhijnq","task_contract_cid":"baguqeeraaxmaligkzbsww3hyzeufp2g4ocuiio4w43m5vvdblnxyr3rviqla","task_revision":1},"execution_route_origin_revision":1,"execution_route_policy_id":"baguqeerajbdyrrmpstrui5b3qhixowle4ljsm5s35wz2mnsoox5aotye32fq","fence_epoch":1,"fencing_token":1,"idle_lane_work_stealing":"","lease_id":"lease:6581404755b146eab5546bba0610fdbd","operation":"database_attempt_admitted","owner_session_id":"embedded-store:eb90e0a1eb7faacee413c6f169269950","strict_task_sharding":true,"task_prefix":"","task_shard_count":1,"task_shard_index":0}
- Title: Under python-integer-offset-finite@1, calc.py::increment(n) must return an exact int for inputs [-2,-1,0,1,2]. Under python-integer-offset-finite@1, calc.py::increment(n) must return n + 2 for inputs [-2,-1,0,1,2].
