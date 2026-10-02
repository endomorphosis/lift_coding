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
- Database attempt ID: attempt:a250ff76defe4e3eafa358ef619366d6
- Database claim ID: claim:327a1314b87c41f386e28263f345d4c6
- Database attempt number: 1
- Database lease ID: lease:d51ade9addb542d0b16e90c9db7ef7cd
- Database owner session ID: embedded-store:b2b34ec8971cd2004f22aa0933811850
- Database fencing token: 1
- Database fence epoch: 1
- Database dependency CIDs: 
- Projection authority: false
- Board namespace: intent
- Local planning contract CID: baguqeerayu63r5ou6fvqj75ejuv4wavdb4fhzbms3zbxpl76okzcpsqtqcaa
- Completion Receipt: {"admitted_from_revision":2,"attempt_execution_phase":"claimed","attempt_execution_revision":1,"attempt_id":"attempt:a250ff76defe4e3eafa358ef619366d6","attempt_number":1,"claim_id":"claim:327a1314b87c41f386e28263f345d4c6","claim_phase_schema":"ipfs_accelerate_py/agent-supervisor/typed-database-attempt-admission@1","claim_process_attestation":{"boot_id":"f4a3b80a-e3df-4702-8d03-86c19f69b2a9","client_id":"database-implementation-daemon:admitted-0c79a488dfdc4bc38efbb30c3dbfd275","grant_id":"owner-grant:16cc4471-7c6f-45b7-b633-c537d934780b","parent_pid":251583,"pid":251760,"process_birth_id":"birth:f152f76376119000ccc7d4f34dce3be4","schema":"ipfs_accelerate_py/agent-supervisor/typed-database-claim-process@1","start_time_ticks":148758829,"uid":1000},"claimed_from_revision":1,"execution_route_binding":{"execution_mode":"grok-codex","plan_root_cid":"baguqeeraz76672ppkwl3tuyjzr7tsn75clary3j4qk5ly34jkrz6cmir6kba","policy_id":"baguqeerames56xxemscfgcqncgofbylrn4jtzce3n3cqsg6ew4xg6z2vofga","repository_tree_id":"baguqeeradnm3svurcbedwnyu5m6xipuxjbx7kfyxx2sqxdtofadh34srpwlq","schema":"ipfs_accelerate_py/agent-supervisor/task-execution-route-binding@1","source_revision":1,"task_alias":"LOCAL-TASK","task_cid":"baguqeerawg7xd7s7btu45gngmalvmg3lnx46dcshvk2zvzokvi6lfnzhijnq","task_contract_cid":"baguqeeramccc4blhzrzb73wuuuapg4s75vmfeb6issihro4feo6ovzgcpmkq","task_revision":1},"execution_route_origin_revision":1,"execution_route_policy_id":"baguqeerames56xxemscfgcqncgofbylrn4jtzce3n3cqsg6ew4xg6z2vofga","fence_epoch":1,"fencing_token":1,"idle_lane_work_stealing":"","lease_id":"lease:d51ade9addb542d0b16e90c9db7ef7cd","operation":"database_attempt_admitted","owner_session_id":"embedded-store:b2b34ec8971cd2004f22aa0933811850","strict_task_sharding":true,"task_prefix":"","task_shard_count":1,"task_shard_index":0}
- Title: Under python-integer-offset-finite@1, calc.py::increment(n) must return an exact int for inputs [-2,-1,0,1,2]. Under python-integer-offset-finite@1, calc.py::increment(n) must return n + 2 for inputs [-2,-1,0,1,2].
