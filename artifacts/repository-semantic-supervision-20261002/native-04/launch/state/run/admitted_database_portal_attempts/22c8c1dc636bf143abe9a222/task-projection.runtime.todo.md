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
- Database attempt ID: attempt:01d9ce316f984c7fbd95f5e8e4c09ef4
- Database claim ID: claim:7759f146d0e14857989383a6b5563a1f
- Database attempt number: 1
- Database lease ID: lease:5c8b7d050f63493a9c32fccbaf9adfc8
- Database owner session ID: embedded-store:c15c83539f62ad27e15a1b65c2517995
- Database fencing token: 1
- Database fence epoch: 1
- Database dependency CIDs: 
- Projection authority: false
- Board namespace: intent
- Local planning contract CID: baguqeera3ijur3dujsbtg4g3hk6m77raqah4zvfrmrmblucpqdrrfr7mwvua
- Completion Receipt: {"admitted_from_revision":2,"attempt_execution_phase":"claimed","attempt_execution_revision":1,"attempt_id":"attempt:01d9ce316f984c7fbd95f5e8e4c09ef4","attempt_number":1,"claim_id":"claim:7759f146d0e14857989383a6b5563a1f","claim_phase_schema":"ipfs_accelerate_py/agent-supervisor/typed-database-attempt-admission@1","claim_process_attestation":{"boot_id":"f4a3b80a-e3df-4702-8d03-86c19f69b2a9","client_id":"database-implementation-daemon:admitted-f174f20e66b441eeb969d334da2b2b95","grant_id":"owner-grant:20e11df8-1da9-48ce-8d29-b562e8e048e1","parent_pid":1839895,"pid":1840155,"process_birth_id":"birth:af246a1180f2ec819194f86ab4ed0e59","schema":"ipfs_accelerate_py/agent-supervisor/typed-database-claim-process@1","start_time_ticks":149217020,"uid":1000},"claimed_from_revision":1,"execution_route_binding":{"execution_mode":"grok-codex","plan_root_cid":"baguqeeracbwbn5t4mvvfvdgli4iaxf7vqwxhrftokf5hme4vrwh7neakdv5q","policy_id":"baguqeeraaruq5oqdh6bqscpz73i5nishvbc2yfh4jby6hwlvvnqlxhsdfbzq","repository_tree_id":"baguqeeraoveohtbvateudyfvaogqhn6irosrehiitcnd7goeifpmriuh2fcq","schema":"ipfs_accelerate_py/agent-supervisor/task-execution-route-binding@1","source_revision":1,"task_alias":"LOCAL-TASK","task_cid":"baguqeerawg7xd7s7btu45gngmalvmg3lnx46dcshvk2zvzokvi6lfnzhijnq","task_contract_cid":"baguqeeracv3xsmvgj2c42ilkyx7kuwj4sjulotl3y7obwqe3lxrk3euzqgvq","task_revision":1},"execution_route_origin_revision":1,"execution_route_policy_id":"baguqeeraaruq5oqdh6bqscpz73i5nishvbc2yfh4jby6hwlvvnqlxhsdfbzq","fence_epoch":1,"fencing_token":1,"idle_lane_work_stealing":"","lease_id":"lease:5c8b7d050f63493a9c32fccbaf9adfc8","operation":"database_attempt_admitted","owner_session_id":"embedded-store:c15c83539f62ad27e15a1b65c2517995","strict_task_sharding":true,"task_prefix":"","task_shard_count":1,"task_shard_index":0}
- Title: Under python-integer-offset-finite@1, calc.py::increment(n) must return an exact int for inputs [-2,-1,0,1,2]. Under python-integer-offset-finite@1, calc.py::increment(n) must return n + 2 for inputs [-2,-1,0,1,2].
