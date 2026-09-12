"""Stdlib integrity checks for retained AF029 compiler-contract feedback.

No prover/model calls or native package imports. This binds normal retained
execution evidence; it is not an adversarial receipt-authentication service.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import re
import stat
from typing import Any, Mapping, Sequence

SCHEMA = "af029-source-compiler-feedback/v1"
SCOPE = "native_compiler_structural_contracts_only"
SUPPORTED = {"modal_well_formedness", "provenance_preservation"}
TRAIN_ROWS_SHA256 = "9a367c2ac6625c32d48e8bf1aca0aa73b705701ea2dfc50c96ddd47fd5beaaff"
TRAIN_EXPORT_SHA256 = "4e54b902980cef97ae4cd5c8516f0b038505adf3251bde5a2aedd6d4e2abd532"


def canonical(value: Any) -> bytes:
    return json.dumps(value,sort_keys=True,ensure_ascii=True,separators=(",",":"),allow_nan=False).encode()


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def read_regular(path: Path) -> bytes:
    if path.is_symlink() or not stat.S_ISREG(path.stat().st_mode):
        raise ValueError("feedback evidence is not a regular file")
    return path.read_bytes()


def _row_errors(directory: Path, coverage_row: Mapping[str, Any], listed_receipt: Mapping[str, Any],
                teacher: Mapping[str, Any], expected_id: str) -> list[str]:
    """Check one actually retained row; also exercised by normal fixture tests."""
    errors=[]
    try:
        packet=json.loads(read_regular(directory/'packet.json'))
        receipt=json.loads(read_regular(directory/'receipt.json'))
        source=read_regular(directory/'obligations.lean')
        stdout=read_regular(directory/'stdout.txt')
        stderr=read_regular(directory/'stderr.txt')
        ph=digest({k:v for k,v in packet.items() if k!='packet_sha256'})
        rh=digest({k:v for k,v in receipt.items() if k!='receipt_sha256'})
        if not ph==packet['packet_sha256']==coverage_row['packet_sha256']==receipt['packet_sha256']:
            errors.append('packet hash binding')
        if not rh==receipt['receipt_sha256']==coverage_row['receipt_sha256']:
            errors.append('receipt hash binding')
        if receipt != listed_receipt:
            errors.append('listed receipt differs from retained receipt')
        if packet['record_id'] != expected_id or coverage_row['record_id'] != expected_id or teacher['record_id'] != expected_id:
            errors.append('train row identity')
        if (packet['schema']!=SCHEMA or receipt['schema']!=SCHEMA or packet['split']!='train'
                or teacher.get('split')!='train' or packet['scope']!=SCOPE or receipt['scope']!=SCOPE
                or packet['source_sha256_semantics']!='upstream_document_version_commitment'
                or packet['semantic_fidelity_measured'] is not False or receipt['semantic_fidelity_measured'] is not False):
            errors.append('schema/scope/final-lock')
        if (digest(teacher)!=packet['teacher_sha256'] or teacher['sample_id']!=packet['sample_id']
                or teacher['input_document_sha256']!=packet['source_sha256']
                or teacher['artifact_sha256']!=packet['teacher_artifact_sha256']
                or teacher.get('independent_gold') or teacher.get('source_gold')):
            errors.append('teacher/source binding or human-gold claim')
        if (digest(packet['modal_artifact'])!=packet['modal_artifact_sha256']
                or digest(packet['registry'])!=packet['registry_sha256']):
            errors.append('canonical compiler/registry bytes')
        for key in ('source_sha256','source_text_sha256','source_record_sha256','modal_artifact_sha256','lean_source_sha256'):
            if packet[key]!=receipt[key] or not re.fullmatch('[0-9a-f]{64}',packet[key]):
                errors.append('receipt source/goal binding: '+key)
        if (source!=packet['lean_source'].encode() or hashlib.sha256(source).hexdigest()!=packet['lean_source_sha256']
                or hashlib.sha256(stdout).hexdigest()!=receipt['stdout_sha256']
                or hashlib.sha256(stderr).hexdigest()!=receipt['stderr_sha256']):
            errors.append('checked source or raw checker output bytes')
        obligations=packet['native_obligations']; rows=packet['coverage']
        by_id={o['obligation_id']:o for o in obligations}
        if (len(by_id)!=len(obligations) or len(rows)!=len(obligations)
                or {o['obligation_id'] for o in rows}!=set(by_id)
                or len({o['obligation_id'] for o in rows})!=len(rows)):
            errors.append('full generated-obligation denominator')
        selected=[]
        for row in rows:
            obligation=by_id[row['obligation_id']]
            if (row['obligation_sha256']!=digest(obligation) or row['kind']!=obligation['kind']
                    or row['formula_id']!=obligation['formula_id'] or obligation['sample_id']!=packet['sample_id']):
                errors.append('native obligation identity')
            if row['kind'] in SUPPORTED:
                if row['status']!='awaiting_native_kernel' or row['theorem']!='af029_'+digest(obligation)[:24]:
                    errors.append('supported theorem identity')
                selected.append(row)
            elif row['status']!='unsupported_fragment' or 'theorem' in row:
                errors.append('unsupported obligation promoted')
        if coverage_row['obligations']!=rows:
            errors.append('row coverage differs from packet')
        decoded=source.decode()
        actual_goals=re.findall(r'^theorem (af029_[0-9a-f]{24}) : (.+) := by decide$',decoded,re.M)
        expected_names=[x['theorem'] for x in selected]
        if [name for name,_ in actual_goals]!=expected_names:
            errors.append('actual source theorem inventory')
        if any(hashlib.sha256(goal.encode()).hexdigest()!=row['goal_sha256'] for (_,goal),row in zip(actual_goals,selected)):
            errors.append('actual source theorem goal')
        if (receipt['generated_obligation_count']!=len(obligations) or receipt['supported_obligation_count']!=len(selected)
                or receipt['status']!=coverage_row['status']):
            errors.append('receipt/coverage denominator')
        successful=receipt['status']=='checked'
        if successful:
            if (receipt['exit_code']!=0 or receipt['axiom_free'] is not True or not selected
                    or receipt['checked_theorems']!=expected_names or coverage_row['admitted_records']!=len(selected)
                    or any(f"'{name}' does not depend on any axioms" not in stdout.decode(errors='replace') for name in expected_names)):
                errors.append('actual checked theorem/admitted count')
        elif receipt['checked_theorems'] or coverage_row['admitted_records']!=0:
            errors.append('failed/unsupported check admitted')
        if not selected and (receipt['status']!='unsupported_fragment' or receipt['exit_code'] is not None):
            errors.append('unsupported fragment claims execution')
    except (OSError,ValueError,TypeError,KeyError,UnicodeError) as exc:
        errors.append('malformed/missing retained feedback: '+type(exc).__name__)
    return errors


def feedback_artifact_errors(root: Path, coverage: Mapping[str, Any], receipts: Sequence[Mapping[str, Any]],
                             teacher_rows: Sequence[Mapping[str, Any]], expected_train_ids: Sequence[str]) -> list[str]:
    """root is EVIDENCE_DIR/source_obligation_feedback; require exact69 IDs."""
    errors=[]
    try:
        ids=list(expected_train_ids)
        rows=coverage['rows']
        teachers=[t for t in teacher_rows if t.get('split')=='train']
        by_id={t['record_id']:t for t in teachers}
        if (len(ids)!=69 or len(set(ids))!=69 or len(rows)!=69 or len(receipts)!=69
                or len(teachers)!=69 or set(by_id)!=set(ids) or len({t['sample_id'] for t in teachers})!=69):
            return ['feedback requires exact69 unique train rows, teachers and receipts']
        if (coverage['schema']!=SCHEMA or coverage['scope']!=SCOPE
                or coverage['semantic_fidelity_measured'] is not False
                or coverage['train_rows']!=69 or coverage['selection_rows']!=0 or coverage['final_rows']!=0
                or coverage['frozen_train_rows_sha256']!=TRAIN_ROWS_SHA256
                or coverage['frozen_train_export_sha256']!=TRAIN_EXPORT_SHA256
                or coverage['prior_trivial_checks'].get('admissible') is not False
                or coverage['prior_trivial_checks'].get('count')!=138):
            errors.append('feedback aggregate scope/frozen source binding')
        if root.is_symlink() or not root.is_dir():
            return errors+['feedback root is not a regular directory']
        if {p.name for p in root.glob('row-*')}!={f'row-{i:03d}' for i in range(69)}:
            errors.append('retained row directory inventory')
        retained=json.loads(read_regular(root/'coverage.json'))
        if retained!=coverage:
            errors.append('listed coverage differs from retained aggregate')
        for i, (expected,row,receipt) in enumerate(zip(ids,rows,receipts)):
            directory=root/f'row-{i:03d}'
            if directory.is_symlink() or not directory.is_dir():
                errors.append(f'row-{i:03d}: missing/noncanonical evidence directory')
                continue
            errors.extend(f'row-{i:03d}: '+error for error in _row_errors(directory,row,receipt,by_id[expected],expected))
        if (sum(r['admitted_records'] for r in rows)!=coverage['admitted_records']
                or sum(r['generated_obligation_count'] for r in receipts)!=coverage['all_generated_obligations']
                or sum(r['supported_obligation_count'] for r in receipts)!=coverage['supported_obligations']):
            errors.append('aggregate feedback totals')
        # Native label IDs must point to those exact accepted receipt/obligation
        # pairs. The caller separately checks the trainer's actual use/reload.
        admitted_path=root.parent/'admitted_feedback.json'
        admitted=json.loads(read_regular(admitted_path))
        actual=admitted['records']
        expected_pairs={(o['obligation_id'],'af029-contract-'+r['receipt_sha256']):o
                        for row,r in zip(rows,receipts) if r['status']=='checked'
                        for o in row['obligations'] if o['status']=='awaiting_native_kernel'}
        actual_pairs=[]
        for record in actual:
            kernel=record['kernel_reconstruction']
            actual_pairs.append((record['obligation_id'],kernel['receipt_id']))
            if (kernel.get('verified') is not True or kernel.get('attempted') is not True or kernel.get('checker')!='lean'
                    or record['eligible_for_training'] is not True or record['partition']!='train'
                    or record['deterministic_trusted'] is not False or kernel['receipt_id'] not in record['receipt_ids']):
                errors.append('admitted label lacks actual kernel binding')
            content={k:v for k,v in record.items() if k not in ('record_id','content_hash','eligible_for_training','version_fingerprint')}
            if (digest(content)!=record['content_hash'] or record['record_id']!='legal-ir-proof-feedback-'+record['content_hash']
                    or digest(record['versions'])!=record['version_fingerprint']):
                errors.append('admitted native record content identity')
            expected=expected_pairs.get(actual_pairs[-1])
            if expected is not None and record['obligation_type']!=expected['kind']:
                errors.append('admitted obligation type')
        if (len(actual_pairs)!=len(expected_pairs) or set(actual_pairs)!=set(expected_pairs)
                or admitted['admitted_count']!=len(actual_pairs) or coverage['admitted_records']!=len(actual_pairs)):
            errors.append('admitted native labels differ from exact checked obligations')
    except (OSError,ValueError,TypeError,KeyError) as exc:
        errors.append('malformed/missing feedback aggregate: '+type(exc).__name__)
    return errors
