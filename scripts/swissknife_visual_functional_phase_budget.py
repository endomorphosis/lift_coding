"""Durable task/final-visual-review repair admissions, independent of source churn.

admit(root, task, failed_review, source_hashes) spends before dispatch and returns
an admission id; finish records its outcome. close_after_pass only closes an
existing phase on a validated same-task final review joined to the original
successful workflow. Nothing here completes tasks, edits boards or refunds spend.
Historical seeding accepts only independently valid completed repair receipts
whose hash-bound immutable context names a same-task failed final visual review.
Unprovable/failed historical invocations are not guessed; future failures count.
"""
from __future__ import annotations
import contextlib
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import tempfile
import uuid

SCHEMA='swissknife.required-phase-repair-budget.v1'
PHASE='final_visual_review'
LIMIT=6
MAX_BYTES=262144
MAX_HISTORY=128

class PhaseBudgetError(ValueError):
    code='phase_repair_budget_invalid'

class PhaseRepairBudgetExhausted(PhaseBudgetError):
    code='required_phase_repair_budget_exhausted'
    def __init__(self, record):
        self.record=record;self.gap_reference=record['gap_request'];self.spent=record['spent'];self.limit=LIMIT
        super().__init__(f"{record['task_id']}:{PHASE} paid repair budget exhausted {self.spent}/{LIMIT}; "
                         f"gap={self.gap_reference['gap_id']}; admit scoped remediation then rerun original acceptance")

def _require(ok,text):
    if not ok:raise PhaseBudgetError(text)

def _json(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)
def _sha(data):return hashlib.sha256(data).hexdigest()

def _path(root,raw):
    root=Path(root).resolve();p=Path(raw)
    if p.is_absolute():
        try:p=p.relative_to(root)
        except ValueError as exc:raise PhaseBudgetError('phase path escaped checkout') from exc
    _require(p.parts and '..' not in p.parts,'invalid phase path')
    current=root
    for part in p.parts:
        current/=part
        _require(not current.is_symlink(),'symlink phase path refused')
    return current

def _read(root,raw,limit=MAX_BYTES):
    p=_path(root,raw);info=p.stat()
    _require(stat.S_ISREG(info.st_mode) and info.st_size<=limit,'unbounded phase artifact')
    return p.read_bytes()

def _ref(root,path):
    p=_path(root,path);data=_read(root,p,3*1024*1024)
    return {'path':p.relative_to(Path(root).resolve()).as_posix(),'sha256':_sha(data),'bytes':len(data)}

def _artifact(root,value):
    _require(type(value)is dict and {'path','sha256'}<=set(value),'invalid phase artifact reference')
    data=_read(root,value['path'],3*1024*1024)
    _require(_sha(data)==value['sha256'] and ('bytes' not in value or len(data)==value['bytes']),'phase artifact changed')
    return json.loads(data)

def directory(root,task):
    identity=task.get('task_id');_require(re.fullmatch(r'SVF-[A-Z0-9-]{1,64}',str(identity)),'invalid phase task')
    return _path(root,'data/agent_supervisor/swissknife_visual_functional/tasks/'+identity)

def _review(root,task,reference,decision=None):
    from swissknife_visual_functional_llm import validate_model_receipt
    p=_path(root,reference['path']);base=directory(root,task)
    _require(p.is_relative_to(base/'verification') and p.name=='visual-review.json','review is not original final visual phase')
    receipt=_artifact(root,reference)
    validate_model_receipt(root,receipt,task_id=task['task_id'],mode='review',require_visual=True)
    actual=receipt['response']['decision']
    _require(actual in {'pass','needs_changes','blocked'},'invalid final review decision')
    if decision is not None:_require(actual==decision,'final review did not pass')
    else:_require(actual!='pass','passing review cannot authorize repair')
    return receipt

def historical_visual_repairs(root,task):
    """Read-only conservative lower bound, unique native invocation identities."""
    from swissknife_visual_functional_llm import validate_model_receipt
    base=directory(root,task)
    candidates=sorted(p for p in base.glob('**/model-invocations/*.json') if not p.name.endswith('.progress.json')) if base.exists() else []
    _require(len(candidates)<=512,'historical phase receipt bound exceeded')
    found={}
    for p in candidates:
        try:
            r=json.loads(_read(root,p,3*1024*1024))
            if r.get('mode')!='repair' or r.get('task_id')!=task['task_id'] or r.get('success') is not True:continue
            identity=str(uuid.UUID(r['invocation_id']));context=None
            for row in r.get('input_files',[]):
                if '/model-inputs/' in row.get('path','') and row['path'].endswith('/context.json'):
                    raw=_read(root,row['path']);_require(_sha(raw)==row['sha256'],'historical context changed');context=json.loads(raw);break
            if not context:continue
            paths=context.get('task',{}).get('edit_paths',task.get('edit_paths',[]))
            validate_model_receipt(root,r,task_id=task['task_id'],mode='repair',predicted_files=paths)
            refs=[];visual=context.get('latest_execution_failure',{}).get('failure',{}).get('visual_review')
            if visual:refs.append(visual['original'])
            refs.extend(context.get('projected_review_sources',[]))
            for value in context.get('bounded_recovery',{}).get('feedback_inputs',{}).values():
                if value.get('included') is True:
                    failure=_artifact(root,value)
                    if failure.get('task_id')==task['task_id'] and failure.get('visual_review'):refs.append(failure['visual_review']['original'])
            qualified=None
            for ref in refs:
                try:_review(root,task,ref);qualified=ref;break
                except (ValueError,OSError,KeyError,TypeError,AttributeError):continue
            if qualified:
                found[identity]={'admission_id':'historical:'+identity,'origin':'historical_validated_completed',
                    'state':'historical_completed','invocation_id':identity,'repair_receipt':_ref(root,p),
                    'failed_review':qualified,'completion_authority':False}
        except (ValueError,OSError,KeyError,TypeError,AttributeError):continue
    _require(len(found)<=MAX_HISTORY,'historical phase admission bound exceeded')
    return list(found.values())

def _validate(value,task):
    _require(type(value)is dict and value.get('schema')==SCHEMA and value.get('task_id')==task['task_id']
        and value.get('phase')==PHASE and value.get('limit')==LIMIT and value.get('completion_authority') is False
        and value.get('work_complete') is False and value.get('state') in {'open','closed','exhausted'},
        'phase budget identity invalid')
    def artifact(row):
        _require(type(row)is dict and set(row)=={'path','sha256','bytes'} and type(row.get('path'))is str
            and not Path(row['path']).is_absolute() and '..' not in Path(row['path']).parts
            and row['path'].startswith('data/agent_supervisor/swissknife_visual_functional/tasks/'+task['task_id']+'/')
            and type(row.get('sha256'))is str and re.fullmatch(r'[0-9a-f]{64}',row['sha256'])
            and type(row.get('bytes'))is int and 0<row['bytes']<=3*1024*1024,'phase artifact reference malformed')
    rows=value.get('history');spent=value.get('spent')
    _require(type(spent)is int and type(rows)is list and 0<=spent<=MAX_HISTORY and len(rows)==spent,'phase spend/history invalid')
    ids=[]
    for row in rows:
        _require(type(row)is dict and type(row.get('admission_id'))is str and row.get('completion_authority') is False,'phase admission invalid')
        _require(row.get('origin') in {'live_before_dispatch','historical_validated_completed'},'phase admission origin invalid')
        artifact(row.get('failed_review'))
        _require('/verification/' in row['failed_review']['path'] and row['failed_review']['path'].endswith('/visual-review.json'),'phase review reference invalid')
        if row['origin']=='live_before_dispatch':
            _require(row.get('state') in {'admitted','failed','proposal_returned'} and type(row.get('source_hashes'))is dict,'live phase admission invalid')
            try:_require(str(uuid.UUID(row['admission_id']))==row['admission_id'],'invalid admission uuid')
            except ValueError as exc:raise PhaseBudgetError('invalid admission uuid')from exc
            for name,digest in row['source_hashes'].items():
                _require(type(name)is str and not Path(name).is_absolute() and '..'not in Path(name).parts
                    and (digest is None or type(digest)is str and re.fullmatch(r'[0-9a-f]{64}',digest)),'phase source identity invalid')
            if 'model_receipt'in row:artifact(row['model_receipt'])
            if 'error_type'in row:_require(type(row['error_type'])is str and 0<len(row['error_type'])<=80,'phase error type invalid')
        else:
            _require(row.get('state')=='historical_completed' and type(row.get('invocation_id'))is str
                and row['admission_id']=='historical:'+row['invocation_id'],'historical phase admission invalid')
            try:_require(str(uuid.UUID(row['invocation_id']))==row['invocation_id'],'invalid historical uuid')
            except ValueError as exc:raise PhaseBudgetError('invalid historical uuid')from exc
            artifact(row.get('repair_receipt'))
        ids.append(row['admission_id'])
    _require(len(set(ids))==len(ids),'duplicate phase admission')
    _require(type(value.get('closures'))is list and len(value['closures'])<=16,'phase closures malformed')
    for closure in value['closures']:
        _require(type(closure)is dict and set(closure)=={'review','workflow','spent','completion_authority'}
            and closure['completion_authority']is False and type(closure['spent'])is int and 0<=closure['spent']<=spent,'phase closure malformed')
        artifact(closure['review']);artifact(closure['workflow'])
    if value['state']=='closed':_require(bool(value['closures']),'closed phase lacks original pass')
    if value['state']=='exhausted':
        gap=value.get('gap_request',{})
        _require(spent>=LIMIT and type(gap)is dict and gap.get('gap_id')==task['task_id']+':'+PHASE
            and gap.get('task_id')==task['task_id'] and gap.get('required_phase')==PHASE and gap.get('spent')==spent
            and gap.get('limit')==LIMIT and gap.get('acceptance_must_remain_unchanged')is True
            and gap.get('completion_authority')is False,'phase exhaustion gap malformed')
    return value

def _save(path,value):
    data=(_json(value)+'\n').encode();_require(len(data)<=MAX_BYTES,'phase journal exceeds bound')
    _require(not path.is_symlink(),'phase journal symlink refused')
    fd,name=tempfile.mkstemp(prefix='.phase-budget-',dir=path.parent)
    try:
        with os.fdopen(fd,'wb')as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())
        os.replace(name,path)
    finally:
        if os.path.exists(name):os.unlink(name)

@contextlib.contextmanager
def _journal(root,task,create=False):
    base=directory(root,task);path=base/'required-phase-repair-budget.json'
    _path(root,path)
    if not create and not path.exists():yield None,None;return
    for p in (base,*base.parents):
        if p==Path(root).resolve():break
        _require(not p.exists() or p.is_dir(),'phase directory malformed')
    base.mkdir(parents=True,exist_ok=True);_path(root,path)
    lock=base/'required-phase-repair-budget.lock';_path(root,lock)
    fd=os.open(lock,os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    try:
        try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError as exc:raise PhaseBudgetError('phase journal is busy; no paid dispatch') from exc
        if path.exists():
            try:value=_validate(json.loads(_read(root,path)),task)
            except (ValueError,OSError,TypeError,KeyError)as exc:raise PhaseBudgetError('phase journal malformed; no paid dispatch') from exc
        else:
            seeds=historical_visual_repairs(root,task)
            value={'schema':SCHEMA,'task_id':task['task_id'],'phase':PHASE,'limit':LIMIT,'spent':len(seeds),
                'history':seeds,'closures':[],'state':'open','completion_authority':False,'work_complete':False}
            _save(path,value) # Persist qualified history even if already exhausted.
        yield path,value
    finally:os.close(fd)

def admit(root,task,failed_review,source_hashes):
    _review(root,task,failed_review)
    with _journal(root,task,create=True)as(path,value):
        if value['spent']>=LIMIT:
            value['gap_request']={'gap_id':task['task_id']+':'+PHASE,'task_id':task['task_id'],'required_phase':PHASE,
                'spent':value['spent'],'limit':LIMIT,'failed_review':failed_review,
                'edit_paths':task.get('edit_paths',[]),'readonly_context_paths':task.get('context_paths',[]),
                'required_action':'Admit a scoped remediation dependency, then rerun original functional/visual/validator checks.',
                'acceptance_must_remain_unchanged':True,'completion_authority':False}
            value['state']='exhausted';_save(path,value);raise PhaseRepairBudgetExhausted(value)
        identity=str(uuid.uuid4());value['history'].append({'admission_id':identity,'origin':'live_before_dispatch','state':'admitted',
            'failed_review':failed_review,'source_hashes':source_hashes,'completion_authority':False})
        value['spent']+=1;value['state']='open';_save(path,value)
        return identity

def finish(root,task,admission_id,*,receipt_path=None,error_type=None):
    with _journal(root,task)as(path,value):
        _require(value is not None,'phase admission missing')
        row=next((r for r in value['history'] if r['admission_id']==admission_id),None)
        _require(row is not None and row['origin']=='live_before_dispatch' and row['state']=='admitted','phase admission unknown or already finished')
        row['state']='failed' if error_type else 'proposal_returned'
        if error_type:row['error_type']=str(error_type)[:80]
        if receipt_path is not None and _path(root,receipt_path).is_file():row['model_receipt']=_ref(root,receipt_path)
        _save(path,value)

def close_after_pass(root,task,review_path,workflow_path,*,profile=None):
    with _journal(root,task)as(path,value):
        if value is None:return None
        reference=_ref(root,review_path);review=_review(root,task,reference,decision='pass');workflow_ref=_ref(root,workflow_path);workflow=_artifact(root,workflow_ref)
        if workflow.get('schema')=='swissknife.visual-functional-workflow.v2':
            from swissknife_visual_functional_final_coverage import validate_dual_workflow,binding,review_join
            from swissknife_visual_functional_worker import validate_observed,validate_backend_observation
            _require(type(profile)is dict,'independent workflow phase closure needs its original profile')
            validated=validate_dual_workflow(Path(root),profile,task,Path(workflow_path),
                observation_validator=validate_observed,backend_validator=validate_backend_observation)
            review_join(Path(root),profile,task,binding(task,validated),Path(review_path))
            value['closures']=[*value['closures'][-15:],{'review':reference,'workflow':workflow_ref,'spent':value['spent'],'completion_authority':False}]
            value['state']='closed';_save(path,value)
            return {'phase_closed':True,'spent':value['spent'],'limit':LIMIT,'work_complete':False,'completion_authority':False}
        _require(workflow.get('schema')=='swissknife.visual-functional-workflow.v1' and workflow.get('passed') is True
            and workflow.get('actual_desktop') is True and workflow.get('app_id')==task.get('app_id'),'original functional workflow did not pass')
        joined=False
        for row in review.get('input_files',[]):
            if '/model-inputs/' in row.get('path','') and row['path'].endswith('.json'):
                raw=_read(root,row['path']);_require(_sha(raw)==row['sha256'],'review input changed')
                data=json.loads(raw)
                if data.get('schema')=='swissknife.visual-functional-review-input.v1' and data.get('original',{}).get('path')==workflow_ref['path'] and data['original'].get('sha256')==workflow_ref['sha256']:joined=True
        _require(joined,'final review does not bind the original passed workflow')
        value['closures']=[*value['closures'][-15:],{'review':reference,'workflow':workflow_ref,'spent':value['spent'],'completion_authority':False}]
        value['state']='closed';_save(path,value)
        return {'phase_closed':True,'spent':value['spent'],'limit':LIMIT,'work_complete':False,'completion_authority':False}
