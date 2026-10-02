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
- Database attempt ID: attempt:3c0f9e410bd342e596c87f81f327dede
- Database claim ID: claim:3d474e551ca14d7e9136f1a908f388a0
- Database attempt number: 1
- Database lease ID: lease:77a95f497e734aa2bdf31e8392a0a70b
- Database owner session ID: embedded-store:d10de175f3c1b6336de1eaf9b7cedc41
- Database fencing token: 1
- Database fence epoch: 1
- Database dependency CIDs: 
- Projection authority: false
- Board namespace: intent
- Local planning contract CID: baguqeera6675v72br6au4brz5ivatj4jampg4z2noy3na566ptgycgeptdtq
- Completion Receipt: {"admitted_from_revision":2,"attempt_execution_phase":"claimed","attempt_execution_revision":1,"attempt_id":"attempt:3c0f9e410bd342e596c87f81f327dede","attempt_number":1,"claim_id":"claim:3d474e551ca14d7e9136f1a908f388a0","claim_phase_schema":"ipfs_accelerate_py/agent-supervisor/typed-database-attempt-admission@1","claim_process_attestation":{"boot_id":"f4a3b80a-e3df-4702-8d03-86c19f69b2a9","client_id":"database-implementation-daemon:admitted-d27dd73174ca496988eb8725383e06ba","grant_id":"owner-grant:5a626cdc-57ac-4448-a96e-ec991c976bd3","parent_pid":1482800,"pid":1483413,"process_birth_id":"birth:9d958dac094429798dcbffbe294cf8b6","schema":"ipfs_accelerate_py/agent-supervisor/typed-database-claim-process@1","start_time_ticks":149121664,"uid":1000},"claimed_from_revision":1,"execution_route_binding":{"execution_mode":"grok-codex","plan_root_cid":"baguqeeranuw4argblc7pyebafdt4sf6h4g3qnnu5tucr6wxn2luyskil7kra","policy_id":"baguqeeragxpldp4agz6hoim5cckmvukepkloae6hr2j2xu4kqg2w5bjr36aq","repository_tree_id":"baguqeeraoveohtbvateudyfvaogqhn6irosrehiitcnd7goeifpmriuh2fcq","schema":"ipfs_accelerate_py/agent-supervisor/task-execution-route-binding@1","source_revision":1,"task_alias":"LOCAL-TASK","task_cid":"baguqeerawg7xd7s7btu45gngmalvmg3lnx46dcshvk2zvzokvi6lfnzhijnq","task_contract_cid":"baguqeeravu3ouoffhjvd5czzzuzlfmghznlj7viwt53mpsemrbrgmthostpa","task_revision":1},"execution_route_origin_revision":1,"execution_route_policy_id":"baguqeeragxpldp4agz6hoim5cckmvukepkloae6hr2j2xu4kqg2w5bjr36aq","fence_epoch":1,"fencing_token":1,"idle_lane_work_stealing":"","lease_id":"lease:77a95f497e734aa2bdf31e8392a0a70b","operation":"database_attempt_admitted","owner_session_id":"embedded-store:d10de175f3c1b6336de1eaf9b7cedc41","strict_task_sharding":true,"task_prefix":"","task_shard_count":1,"task_shard_index":0}
- Title: Under python-integer-offset-finite@1, calc.py::increment(n) must return an exact int for inputs [-2,-1,0,1,2]. Under python-integer-offset-finite@1, calc.py::increment(n) must return n + 2 for inputs [-2,-1,0,1,2].
