# Database attempt projection (non-authoritative)

## LOCAL-TASK the runner must compute result; requires left > 0; ensures result = old(right) * old(left) and returned.

- Status: completed
- Completion: auto
- Priority: P2
- Track: implementation
- Depends on:
- Outputs: source.py
- Validation: python3 -B -c 'from source import derive; observed = [derive(1, -1), derive(1, 0), derive(1, 1)]; assert all(type(value) is int for value in observed); assert observed == [-1, 0, 1], observed'
- Acceptance: the runner must compute result; requires left > 0; ensures result = old(right) * old(left) and returned.
- Database task CID: baguqeerabotsfjzymoxsfw3ti5odameistxb46hgwigecxkxezamareaxv7q
- Database attempt ID: attempt:7b7535f0e5504ef5ba0a7503a6c9c953
- Database claim ID: claim:722ff47793994f5f938033dc38eca771
- Database attempt number: 1
- Database lease ID: lease:4f18f5375c9047708a996409f1b922c4
- Database owner session ID: embedded-store:0f1cd5cb9c5ceb501ba9fcb2deafe6e4
- Database fencing token: 1
- Database fence epoch: 1
- Database dependency CIDs: 
- Projection authority: false
- Board namespace: intent
- Local planning contract CID: baguqeerabrsojhewp6qbeelpahz7tdu2clude2765s5ep5virtffhd2dwcsq
- Completion Receipt: {"admitted_from_revision":2,"attempt_execution_phase":"claimed","attempt_execution_revision":1,"attempt_id":"attempt:7b7535f0e5504ef5ba0a7503a6c9c953","attempt_number":1,"claim_id":"claim:722ff47793994f5f938033dc38eca771","claim_phase_schema":"ipfs_accelerate_py/agent-supervisor/typed-database-attempt-admission@1","claim_process_attestation":{"boot_id":"f4a3b80a-e3df-4702-8d03-86c19f69b2a9","client_id":"database-implementation-daemon:admitted-10f0799ded044f67a9c0ef31c9459893","grant_id":"owner-grant:96fb7f81-483d-4863-aa39-1d2c85c36159","parent_pid":3194124,"pid":3194457,"process_birth_id":"birth:8b94cbdda082c89915c48d6c13b33f61","schema":"ipfs_accelerate_py/agent-supervisor/typed-database-claim-process@1","start_time_ticks":148348928,"uid":1000},"claimed_from_revision":1,"execution_route_binding":{"execution_mode":"grok-codex","plan_root_cid":"baguqeerad7ufpwwvwa4iuvupxe75hhbglbwtpoark7chicrtsnckmzshbaka","policy_id":"baguqeerazatdog2htgg4b55oxkgknhjqdp7dounp3udzdvi5ty3amudabflq","repository_tree_id":"baguqeeradovjytpod5rma4l7hozzr4dvytxilyhdgixgelx2dfnodmeemmiq","schema":"ipfs_accelerate_py/agent-supervisor/task-execution-route-binding@1","source_revision":1,"task_alias":"LOCAL-TASK","task_cid":"baguqeerabotsfjzymoxsfw3ti5odameistxb46hgwigecxkxezamareaxv7q","task_contract_cid":"baguqeera6b34nybhpipkiq6vzvjrc7xwhwiidnml5asipz56flvqiuic65eq","task_revision":1},"execution_route_origin_revision":1,"execution_route_policy_id":"baguqeerazatdog2htgg4b55oxkgknhjqdp7dounp3udzdvi5ty3amudabflq","fence_epoch":1,"fencing_token":1,"idle_lane_work_stealing":"","lease_id":"lease:4f18f5375c9047708a996409f1b922c4","operation":"database_attempt_admitted","owner_session_id":"embedded-store:0f1cd5cb9c5ceb501ba9fcb2deafe6e4","strict_task_sharding":true,"task_prefix":"","task_shard_count":1,"task_shard_index":0}
- Title: the runner must compute result; requires left > 0; ensures result = old(right) * old(left) and returned.
