from pathlib import Path
import os,sys,json,resource,signal,time
os.environ.update(IPFS_DATASETS_AUTO_INSTALL='false',IPFS_KIT_AUTO_INSTALL_DEPS='0',IPFS_DATASETS_PY_MINIMAL_IMPORTS='1',IPFS_DATASETS_PY_ENABLE_LLM_IMPORTS='0',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',CUDA_VISIBLE_DEVICES='',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1')
resource.setrlimit(resource.RLIMIT_AS,(8*1024**3,)*2);resource.setrlimit(resource.RLIMIT_CPU,(55,)*2);signal.alarm(60)
os.sched_setaffinity(0,set(sorted(os.sched_getaffinity(0))[-2:]))
sys.path.insert(0,str(Path('external/ipfs_datasets').resolve()))
from ipfs_datasets_py.logic.modal.codec import DeterministicModalLogicCodec,ModalLogicCodecConfig
from ipfs_datasets_py.logic.modal.decompiler import decode_modal_ir_document
c=DeterministicModalLogicCodec(ModalLogicCodecConfig(embedding_dimensions=8,use_flogic=False))
t=time.monotonic();r=c.encode('Company A shall submit backup report within 10 days unless emergency.',document_id='development-control',source_embedding=[0.0]*8)
print('seconds',time.monotonic()-t,'keys',list(r.to_dict()))
m=r.modal_ir.to_dict();print(json.dumps(m,indent=2)[:16000])
d=decode_modal_ir_document(r.modal_ir);print('decode',type(d),str(d)[:1200])
