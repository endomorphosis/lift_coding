from pathlib import Path
import ast, hashlib, json
root=Path(__file__).resolve().parent
prefix=root/'conflict-previews-01/ipfs_datasets_py/optimizers/logic_theorem_optimizer/resource_scheduler.py'
up=Path(str(prefix)+'.upstream').read_text()
local=Path(str(prefix)+'.local-working').read_text()
def replace_once(text,old,new):
    assert text.count(old)==1,repr(old[:100]);return text.replace(old,new)
merged=replace_once(up,'self, *args: object, admission_observation: Optional[Mapping[str, Any]] = None,','self, *args: object, admission_observation: Optional[Mapping[str, Any]] = None,\n        timeout_decision: Optional[Mapping[str, Any]] = None,')
merged=replace_once(merged,'        self.admission_observation = deepcopy(admission_observation)\n','        self.admission_observation = deepcopy(admission_observation)\n        # Final branch evidence is separate from historical pressure refusals.\n        self.timeout_decision = deepcopy(timeout_decision)\n')
merged=replace_once(merged,'        proof_refusal_observation: Optional[Mapping[str, Any]] = None\n','        proof_refusal_observation: Optional[Mapping[str, Any]] = None\n        timeout_decision: Optional[Mapping[str, Any]] = None\n')
start=local.index('                    timeout_decision = {\n')
end=local.index('                    state["waiters"].pop(waiter_id, None)',start)
merged=replace_once(merged,'                    proof_refusal_observation = deepcopy(waiter.get("last_proof_refusal"))\n','                    proof_refusal_observation = deepcopy(waiter.get("last_proof_refusal"))\n'+local[start:end])
merged=replace_once(merged,'            error = LeaseTimeoutError("timed out waiting for a resource lease")','            error = LeaseTimeoutError("timed out waiting for a resource lease",\n                                      timeout_decision=timeout_decision)')
ast.parse(merged)
path=root/'checkout/ipfs_datasets_py/optimizers/logic_theorem_optimizer/resource_scheduler.py'
path.write_text(merged)
test=root/'checkout/tests/unit/optimizers/logic_theorem_optimizer/test_resource_scheduler_timeout_decision.py'
text=test.read_text(); before=text
# Published upstream reserves admission_observation for current generic gate
# diagnostics. Historical refusals consistently live under proof_refusal_observation.
text=text.replace('error.admission_observation','error.proof_refusal_observation').replace('first.admission_observation','first.proof_refusal_observation').replace('second.admission_observation','second.proof_refusal_observation').replace('caught.value.admission_observation','caught.value.proof_refusal_observation')
# Constructor-only compatibility assertions still exercise copied generic diagnostics.
text=text.replace('assert error.proof_refusal_observation == error.timeout_decision == {"nested": [1]}','assert error.admission_observation == error.timeout_decision == {"nested": [1]}').replace('error.proof_refusal_observation["nested"][0] = 3','error.admission_observation["nested"][0] = 3')
ast.parse(text);test.write_text(text)
review={'schema':'datasets-scheduler-conflict-resolution@1','base':'latest origin/main resource_scheduler.py','policy':'Preserve all published resource profiles, proof recovery, admission diagnostics, counters and fairness; transplant only unpublished timeout descriptor. Generic final gate diagnostics remain admission_observation. Historical waiter refusals remain proof_refusal_observation. Tests use the published field contract.','upstream_sha256':hashlib.sha256(up.encode()).hexdigest(),'local_sha256':hashlib.sha256(local.encode()).hexdigest(),'merged_sha256':hashlib.sha256(merged.encode()).hexdigest(),'ast_parse_passed':True,'changes':['optional deepcopy timeout_decision constructor field','waiter-local optional descriptor initialization','descriptor built only in actual terminal timeout branch using existing sampled clocks/predicates','timeout exception receives descriptor; cancellation receives none','unpublished timeout tests updated for historical refusal field name'],'admission_behavior_changed':False,'validation_pending':True}
(root/'scheduler-merge-review-01.json').write_text(json.dumps(review,indent=2)+'\n')
print(json.dumps({'merged_bytes':len(merged.encode()),'timeout_tests_updated':text!=before,'sha256':review['merged_sha256']}))
