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
- Database attempt ID: attempt:cfd590e4e55e40cab3f6bfbcc0c9fe5a
- Database claim ID: claim:924023b9b3584847abec2848b03f0a86
- Database attempt number: 1
- Database lease ID: lease:77cedbd024974acaae18f44ad133562f
- Database owner session ID: embedded-store:1064e05c53cbd2ac02ab2b899971ce20
- Database fencing token: 1
- Database fence epoch: 1
- Database dependency CIDs: 
- Projection authority: false
- Board namespace: intent
- Local planning contract CID: baguqeerampznue4oxr6oboejweqmz7taieis526lfprr3fi5ufjhggwxb65q
- Completion Receipt: {"admitted_from_revision":2,"attempt_execution_phase":"claimed","attempt_execution_revision":1,"attempt_id":"attempt:cfd590e4e55e40cab3f6bfbcc0c9fe5a","attempt_number":1,"claim_id":"claim:924023b9b3584847abec2848b03f0a86","claim_phase_schema":"ipfs_accelerate_py/agent-supervisor/typed-database-attempt-admission@1","claim_process_attestation":{"boot_id":"f4a3b80a-e3df-4702-8d03-86c19f69b2a9","client_id":"database-implementation-daemon:admitted-0898756471974450bdbefa328fbd1779","grant_id":"owner-grant:81e5782e-906f-41d4-a9fa-04b46ef55e61","parent_pid":681881,"pid":682544,"process_birth_id":"birth:f0050d69511060201611cee66a4e7a2a","schema":"ipfs_accelerate_py/agent-supervisor/typed-database-claim-process@1","start_time_ticks":148907640,"uid":1000},"claimed_from_revision":1,"execution_route_binding":{"execution_mode":"grok-codex","plan_root_cid":"baguqeerapeinu3yutr33wlpexm7vuh27cs5ln5aaqigrvqqc272qyeb2xota","policy_id":"baguqeeratcsq3ipkqiufa2yhorqlz5nfh52b7ydlprdn4gfnk2mzabdlkckq","repository_tree_id":"baguqeeradnm3svurcbedwnyu5m6xipuxjbx7kfyxx2sqxdtofadh34srpwlq","schema":"ipfs_accelerate_py/agent-supervisor/task-execution-route-binding@1","source_revision":1,"task_alias":"LOCAL-TASK","task_cid":"baguqeerawg7xd7s7btu45gngmalvmg3lnx46dcshvk2zvzokvi6lfnzhijnq","task_contract_cid":"baguqeeraolc4osnwre6jxrz4noq7ocw7bkiqmiemjweex5lmqzc6f7n7ayda","task_revision":1},"execution_route_origin_revision":1,"execution_route_policy_id":"baguqeeratcsq3ipkqiufa2yhorqlz5nfh52b7ydlprdn4gfnk2mzabdlkckq","fence_epoch":1,"fencing_token":1,"idle_lane_work_stealing":"","lease_id":"lease:77cedbd024974acaae18f44ad133562f","operation":"database_attempt_admitted","owner_session_id":"embedded-store:1064e05c53cbd2ac02ab2b899971ce20","strict_task_sharding":true,"task_prefix":"","task_shard_count":1,"task_shard_index":0}
- Title: Under python-integer-offset-finite@1, calc.py::increment(n) must return an exact int for inputs [-2,-1,0,1,2]. Under python-integer-offset-finite@1, calc.py::increment(n) must return n + 2 for inputs [-2,-1,0,1,2].
