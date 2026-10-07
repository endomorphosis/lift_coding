"""Read-only two-thread restore and exact source-only output replay."""
from contextlib import ExitStack
from hashlib import sha256
import argparse
import json
import os
from pathlib import Path
import sys
import time
from unittest.mock import patch


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--package-root',type=Path,required=True)
    p.add_argument('--inputs',type=Path,required=True)
    p.add_argument('--results',type=Path,required=True)
    p.add_argument('--receipt',type=Path,required=True)
    p.add_argument('--checkpoint-root',type=Path)
    a=p.parse_args();started=time.monotonic();sys.path.insert(0,str(a.package_root))
    import torch
    from ipfs_datasets_py.logic.formalization.autoencoder import legal_scope_trigger_readout as head
    from ipfs_datasets_py.logic.formalization.autoencoder import legal_scope_span_decoder as donor
    from ipfs_datasets_py.logic.deontic.utils import deontic_parser
    torch.set_num_threads(2);torch.use_deterministic_algorithms(True)
    assert not torch.cuda.is_initialized()
    rows=json.loads(a.inputs.read_text());arms={}
    def pin(path):
        raw=path.read_bytes();return dict(path=str(path.resolve()),bytes=len(raw),sha256=sha256(raw).hexdigest())
    def denied(*args,**kwargs):raise AssertionError('read-only replay reached training or semantic parser')
    for mode in ('global','predicted_trigger'):
        selected=json.loads((a.results/mode/'selected.json').read_text())
        path=a.checkpoint_root/mode/'checkpoint.json' if a.checkpoint_root else Path(selected['checkpoint']['path'])
        raw=path.read_bytes();assert sha256(raw).hexdigest()==selected['checkpoint']['sha256']
        checkpoint=json.loads(raw);rng=torch.random.get_rng_state().clone()
        model,optimizer,steps=head.restore_trigger_readout_checkpoint(checkpoint)
        assert torch.equal(rng,torch.random.get_rng_state()) and steps==selected['completed_updates']
        assert head.save_trigger_readout_checkpoint(model,optimizer,steps=steps)==checkpoint
        expected=json.loads((a.results/mode/'final-predictions.json').read_text())['rows'];actual=[]
        with ExitStack() as stack:
            for owner,names in ((head,('TriggerReadoutExample','train_trigger_readout_step')),
                (donor,('_labels','ScopeSpanExample','train_scope_span_step')),
                (deontic_parser,('extract_normative_elements','analyze_normative_sentence','classify_modal')),
                (optimizer,('step',))):
                for name in names:stack.enter_context(patch.object(owner,name,denied))
            for row in rows:
                result=head.predict_trigger_readout(model,row['source_text'],row['condition_attachment'],expected_source_sha256=row['source_sha256'])
                assert result['formal_output'] is None and not any(result[k] for k in ('source_semantics_verified','accepted','qualified','formalized','proof_ready','proof_authority','target_access'))
                if result['proposal']:assert not any(result['proposal']['masks'].values())
                actual.append(dict(id=row['id'],source_group=row['source_group'],source_sha256=row['source_sha256'],class_logits=result['modality_logits'],prediction=result))
        assert len(actual)==len(expected)==128 and actual==expected
        assert head.save_trigger_readout_checkpoint(model,optimizer,steps=steps)==checkpoint
        assert torch.equal(rng,torch.random.get_rng_state())
        arms[mode]=dict(checkpoint_sha256=sha256(raw).hexdigest(),selected_steps=steps,cases=128,full_output_exact=128,
            adapter_and_full_Adam_unchanged=True,donor_checkpoint_byte_exact=True,mode_and_rng_unchanged=True,
            expected_panel=pin(a.results/mode/'final-predictions.json'),checkpoint=pin(path))
    receipt=dict(schema='trigger-readout-read-only-replay/v1',status='passed',arms=arms,threads=2,device='cpu',
        cuda_initialized=False,additional_optimizer_steps=0,references_opened=False,semantic_parsers_denied=True,
        training_lease_claimed=False,producer_pins=head.producer_pins(),elapsed_seconds=time.monotonic()-started,
        source=pin(Path(__file__)),inputs=pin(a.inputs),receipt_fsync_before_completion=True)
    with a.receipt.open('x') as out:
        json.dump(receipt,out,indent=2);out.write('\n');out.flush();os.fsync(out.fileno())
    fd=os.open(a.receipt.parent,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)
    print(json.dumps(receipt))


if __name__=='__main__':main()
